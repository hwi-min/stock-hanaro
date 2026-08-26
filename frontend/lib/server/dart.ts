import "server-only";

import { classifyDisclosure, disclosureTypeLabels, isCorrectionTitle } from "../disclosure-classification";
import { supabaseDelete, supabaseSelect, supabaseUpsert } from "./supabase-rest";

type CacheRow = { payload_json: string; expires_at: string; updated_at: string };
type StoredDisclosure = { receipt_no: string; corp_cls: string };
type DartRow = {
  corp_cls?: string; corp_name?: string; corp_code?: string; stock_code?: string;
  report_nm?: string; rcept_no?: string; flr_nm?: string; rcept_dt?: string; rm?: string;
};
type DartResponse = { status?: string; message?: string; total_page?: number; list?: DartRow[] };

export type DisclosureRefresh = {
  status: "fresh" | "refreshed" | "failed" | "disabled";
  checkedAt: string | null;
  lastSuccessAt: string | null;
  newCount: number;
  retryAfterSeconds: number;
  message?: string;
};

const CACHE_KEY = "dart:disclosures:latest";
const REFRESH_SECONDS = 120;
const MAX_PAGES = 20;
let refreshPromise: Promise<DisclosureRefresh> | null = null;

function kstParts(now = new Date()) {
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone: "Asia/Seoul", year: "numeric", month: "2-digit", day: "2-digit",
    weekday: "short", hour: "2-digit", minute: "2-digit", hourCycle: "h23",
  }).formatToParts(now).reduce<Record<string, string>>((acc, part) => { acc[part.type] = part.value; return acc; }, {});
  return { date: `${parts.year}${parts.month}${parts.day}`, weekday: parts.weekday, minutes: Number(parts.hour) * 60 + Number(parts.minute) };
}

function retentionCutoff(now = new Date()) {
  const { date } = kstParts(now);
  const kstMidnightUtc = new Date(`${date.slice(0, 4)}-${date.slice(4, 6)}-${date.slice(6, 8)}T00:00:00+09:00`);
  kstMidnightUtc.setUTCDate(kstMidnightUtc.getUTCDate() - 1);
  return new Intl.DateTimeFormat("en-CA", {
    timeZone: "Asia/Seoul", year: "numeric", month: "2-digit", day: "2-digit",
  }).format(kstMidnightUtc);
}

function inferReportType(title: string, remarks = "") {
  const compact = title.replace(/\s+/g, "");
  if (/사업보고서|반기보고서|분기보고서|결산서류/.test(compact)) return "A";
  if (/주요사항보고서/.test(compact)) return "B";
  if (/증권신고서|소액공모|투자설명서|발행실적보고서/.test(compact)) return "C";
  if (/대량보유|임원.*주요주주|의결권대리행사|공개매수/.test(compact)) return "D";
  if (/감사보고서|감사전재무제표/.test(compact)) return "F";
  if (remarks.includes("공")) return "J";
  if (/[유코넥채]/.test(remarks)) return "I";
  return "E";
}

function importance(title: string, reportType: string) {
  const event = classifyDisclosure(title, reportType);
  if (event.priority >= 88) return "high";
  if (event.priority >= 70 || ["B", "C", "I"].includes(reportType)) return "medium";
  return "low";
}

function normalize(row: DartRow) {
  const title = String(row.report_nm || ""), reportType = inferReportType(title, String(row.rm || ""));
  const receiptNo = String(row.rcept_no || ""), receiptDate = String(row.rcept_dt || "");
  return {
    receipt_no: receiptNo, corp_code: String(row.corp_code || ""), corp_name: String(row.corp_name || ""),
    stock_code: row.stock_code?.trim() || null, title,
    receipt_date: `${receiptDate.slice(0, 4)}-${receiptDate.slice(4, 6)}-${receiptDate.slice(6, 8)}`,
    report_type: reportType, submitter: row.flr_nm || null, remarks: row.rm || null,
    source_url: `https://dart.fss.or.kr/dsaf001/main.do?rcpNo=${receiptNo}`,
    corp_cls: String(row.corp_cls || "E"), category: disclosureTypeLabels[reportType] || "기타공시",
    importance: importance(title, reportType), is_correction: isCorrectionTitle(title),
  };
}

async function cacheRow() {
  const rows = await supabaseSelect<CacheRow>("api_cache", { select: "payload_json,expires_at,updated_at", cache_key: `eq.${CACHE_KEY}`, limit: 1 });
  return rows[0] || null;
}

function parseStatus(row: CacheRow | null): DisclosureRefresh | null {
  if (!row) return null;
  try { return JSON.parse(row.payload_json) as DisclosureRefresh; } catch { return null; }
}

async function writeStatus(status: DisclosureRefresh, seconds: number) {
  const now = new Date();
  await supabaseUpsert("api_cache", {
    cache_key: CACHE_KEY, payload_json: JSON.stringify(status), updated_at: now.toISOString(),
    expires_at: new Date(now.getTime() + seconds * 1000).toISOString(),
  }, "cache_key");
}

async function fetchLatest(date: string, known: Set<string>) {
  const found: DartRow[] = [];
  for (let page = 1; page <= MAX_PAGES; page += 1) {
    const params = new URLSearchParams({ crtfc_key: process.env.DART_API_KEY || "", bgn_de: date, end_de: date,
      sort: "date", sort_mth: "desc", page_no: String(page), page_count: "100" });
    const response = await fetch(`https://opendart.fss.or.kr/api/list.json?${params}`, { cache: "no-store" });
    if (!response.ok) throw new Error(`OpenDART HTTP ${response.status}`);
    const data = await response.json() as DartResponse;
    if (data.status === "013") return found;
    if (data.status !== "000") throw new Error(`OpenDART ${data.status}: ${data.message || "request failed"}`);
    const items = (data.list || []).filter((item) => ["Y", "K", "N"].includes(String(item.corp_cls || "")));
    const existingIndex = items.findIndex((item) => known.has(String(item.rcept_no || "")));
    found.push(...(existingIndex >= 0 ? items.slice(0, existingIndex) : items));
    if (existingIndex >= 0 || page >= Number(data.total_page || 1)) return found;
  }
  throw new Error("OpenDART pagination limit exceeded");
}

async function refresh(previous: DisclosureRefresh | null): Promise<DisclosureRefresh> {
  const now = new Date();
  if (!process.env.DART_API_KEY) return { status: "disabled", checkedAt: null, lastSuccessAt: previous?.lastSuccessAt || null, newCount: 0, retryAfterSeconds: REFRESH_SECONDS };
  try {
    // Claim the shared refresh window before calling OpenDART so other isolates serve stored data.
    await writeStatus({ status: "fresh", checkedAt: now.toISOString(), lastSuccessAt: previous?.lastSuccessAt || null,
      newCount: 0, retryAfterSeconds: REFRESH_SECONDS }, REFRESH_SECONDS);
    const { date } = kstParts(now);
    const isoDate = `${date.slice(0, 4)}-${date.slice(4, 6)}-${date.slice(6, 8)}`;
    const stored = await supabaseSelect<StoredDisclosure>("disclosures", { select: "receipt_no,corp_cls", receipt_date: `eq.${isoDate}`, limit: 1000 });
    const known = new Set(stored.map((item) => item.receipt_no));
    const latest = await fetchLatest(date, known);
    const unique = [...new Map(latest.filter((item) => item.rcept_no && !known.has(String(item.rcept_no))).map((item) => [item.rcept_no, item])).values()];
    if (unique.length) await supabaseUpsert("disclosures", unique.map(normalize), "receipt_no");
    await supabaseDelete("disclosures", { receipt_date: `lt.${retentionCutoff(now)}` });
    const result: DisclosureRefresh = { status: "refreshed", checkedAt: now.toISOString(), lastSuccessAt: now.toISOString(), newCount: unique.length, retryAfterSeconds: REFRESH_SECONDS };
    await writeStatus(result, REFRESH_SECONDS);
    return result;
  } catch (error) {
    const result: DisclosureRefresh = { status: "failed", checkedAt: now.toISOString(), lastSuccessAt: previous?.lastSuccessAt || null,
      newCount: 0, retryAfterSeconds: REFRESH_SECONDS, message: error instanceof Error ? error.message.slice(0, 180) : "OpenDART refresh failed" };
    await writeStatus(result, REFRESH_SECONDS).catch(() => undefined);
    return result;
  }
}

export async function refreshDisclosuresIfStale(): Promise<DisclosureRefresh> {
  const row = await cacheRow();
  const previous = parseStatus(row);
  if (row && Date.now() < new Date(row.expires_at).getTime()) return { ...(previous || {
    status: "fresh", checkedAt: row.updated_at, lastSuccessAt: row.updated_at, newCount: 0, retryAfterSeconds: REFRESH_SECONDS,
  }), status: previous?.status === "failed" ? "failed" : "fresh" };
  if (!refreshPromise) refreshPromise = refresh(previous).finally(() => { refreshPromise = null; });
  return refreshPromise;
}
