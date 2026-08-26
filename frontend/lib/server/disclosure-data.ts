import "server-only";

import { classifyDisclosure, disclosureTypeLabels, isCorrectionTitle } from "../disclosure-classification";
import { refreshDisclosuresIfStale } from "./dart";
import { supabaseSelect } from "./supabase-rest";

type Row = Record<string, string | number | boolean | null>;
export type DisclosureSort = "impact" | "latest" | "company" | "type";
export type DisclosureQuery = { date?: string; reportType?: string; eventType?: string; importance?: string; correction?: string; q?: string; sort?: DisclosureSort };
export type DisclosureViewItem = {
  id: string; receiptNo: string; company: string; stockCode: string | null; title: string; receiptDate: string;
  reportType: string; reportTypeLabel: string; eventType: string; eventLabel: string; eventGroup: string;
  eventPriority: number; importance: "high" | "medium" | "low"; isCorrection: boolean; sourceUrl: string;
};

const importanceRank = { high: 3, medium: 2, low: 1 };

export async function getWorkerDisclosures(query: DisclosureQuery = {}) {
  const refresh = await refreshDisclosuresIfStale();
  const rows = await supabaseSelect<Row>("disclosures", { select: "*", order: "receipt_date.desc,receipt_no.desc", limit: 1000 });
  const allItems: DisclosureViewItem[] = rows.map((row) => {
    const title = String(row.title || ""), reportType = String(row.report_type || "");
    const event = classifyDisclosure(title, reportType);
    const importance = (["high", "medium", "low"].includes(String(row.importance)) ? String(row.importance) : "low") as DisclosureViewItem["importance"];
    return {
      id: String(row.id), receiptNo: String(row.receipt_no), company: String(row.corp_name), stockCode: row.stock_code ? String(row.stock_code) : null,
      title, receiptDate: String(row.receipt_date), reportType, reportTypeLabel: disclosureTypeLabels[reportType] || String(row.category || "기타공시"),
      eventType: event.type, eventLabel: event.label, eventGroup: event.group, eventPriority: event.priority, importance,
      isCorrection: Boolean(row.is_correction) || isCorrectionTitle(title), sourceUrl: String(row.source_url),
    };
  });
  const availableDates = [...new Set(allItems.map((item) => item.receiptDate))].sort().reverse();
  const selectedDate = query.date && availableDates.includes(query.date) ? query.date : availableDates[0] || "";
  const dateItems = allItems.filter((item) => item.receiptDate === selectedDate);
  const count = (values: string[]) => Object.entries(values.reduce<Record<string, number>>((acc, value) => {
    acc[value] = (acc[value] || 0) + 1; return acc;
  }, {})).map(([name, value]) => ({ name, count: value })).sort((a, b) => b.count - a.count || a.name.localeCompare(b.name, "ko"));
  const typeFacets = count(dateItems.map((item) => item.reportType)).map((facet) => ({ ...facet, label: disclosureTypeLabels[facet.name] || "기타공시" }));
  const eventFacets = count(dateItems.map((item) => item.eventType)).map((facet) => ({ ...facet, label: dateItems.find((item) => item.eventType === facet.name)?.eventLabel || facet.name }));
  const term = (query.q || "").trim().toLocaleLowerCase("ko");
  const filtered = dateItems.filter((item) => {
    if (query.reportType && item.reportType !== query.reportType) return false;
    if (query.eventType && item.eventType !== query.eventType) return false;
    if (query.importance && item.importance !== query.importance) return false;
    if (query.correction === "only" && !item.isCorrection) return false;
    if (query.correction === "exclude" && item.isCorrection) return false;
    return !term || `${item.company} ${item.stockCode || ""} ${item.title} ${item.eventLabel}`.toLocaleLowerCase("ko").includes(term);
  });
  const sort = query.sort || "impact";
  filtered.sort((left, right) => {
    if (sort === "latest") return right.receiptNo.localeCompare(left.receiptNo);
    if (sort === "company") return left.company.localeCompare(right.company, "ko") || right.receiptNo.localeCompare(left.receiptNo);
    if (sort === "type") return left.reportType.localeCompare(right.reportType) || right.eventPriority - left.eventPriority || right.receiptNo.localeCompare(left.receiptNo);
    return importanceRank[right.importance] - importanceRank[left.importance] || right.eventPriority - left.eventPriority || right.receiptNo.localeCompare(left.receiptNo);
  });
  return {
    selectedDate, availableDates, items: filtered, refresh,
    summary: { total: dateItems.length, important: dateItems.filter((item) => item.importance === "high").length,
      actionable: dateItems.filter((item) => item.eventPriority >= 70).length, corrections: dateItems.filter((item) => item.isCorrection).length },
    facets: { types: typeFacets, events: eventFacets },
  };
}
