import "server-only";

import { supabaseSelect, supabaseUpsert } from "./supabase-rest";

export type MacroPoint = { label: string; value: number; observationDate?: string };
export type MacroMetric = {
  id: string; label: string; fred: string; value: string; direction: "up" | "down" | "flat";
  comparison: string; observationDate: string;
};
export type MacroSeries = { name: string; color: string; points: MacroPoint[] };
export type MacroData = {
  source: "fred" | "stale" | "sample"; asOf: string; snapshotAt?: string; summary: string;
  bond: { metrics: MacroMetric[]; series: MacroSeries[]; curve: MacroPoint[]; signal: string };
  inflation: { metrics: MacroMetric[]; series: MacroSeries[]; signal: string };
  fx: { metrics: MacroMetric[]; broad: MacroPoint[]; krw: MacroPoint[]; signal: string };
  fed: { metrics: MacroMetric[]; series: MacroPoint[]; signal: string };
};

type Observation = { date: string; value: number };
type SnapshotRow = { payload_json: string; updated_at: string };
const API = "https://api.stlouisfed.org/fred/series/observations";
const SNAPSHOT_KEY = "fred:us-macro-monitor:v1";
const colors = ["#118565", "#172521", "#b26a3d"];
let memorySnapshot: MacroData | null = null;

function sample(points: Observation[], count: number): MacroPoint[] {
  const ordered = [...points].reverse();
  if (ordered.length <= count) return ordered.map(item => ({ label: item.date, value: item.value }));
  const step = (ordered.length - 1) / (count - 1);
  return Array.from({ length: count }, (_, index) => ordered[Math.round(index * step)])
    .map(item => ({ label: item.date, value: item.value }));
}

async function observations(seriesId: string, limit: number): Promise<Observation[]> {
  const apiKey = process.env.FRED_API_KEY;
  if (!apiKey) throw new Error("FRED_API_KEY is not configured");
  const params = new URLSearchParams({ series_id: seriesId, api_key: apiKey, file_type: "json", sort_order: "desc", limit: String(limit) });
  const response = await fetch(`${API}?${params}`, { next: { revalidate: 3600 } });
  if (!response.ok) throw new Error(`FRED ${seriesId} returned ${response.status}`);
  const payload = await response.json() as { observations?: Array<{ date: string; value: string }> };
  return (payload.observations ?? []).flatMap(item => {
    const value = Number(item.value);
    return Number.isFinite(value) ? [{ date: item.date, value }] : [];
  });
}

function direction(change: number, epsilon = .00001): "up" | "down" | "flat" {
  return change > epsilon ? "up" : change < -epsilon ? "down" : "flat";
}
function signed(value: number, digits = 2) { return `${value > 0 ? "+" : ""}${value.toFixed(digits)}`; }
function dailyMetric(id: string, label: string, rows: Observation[], format: (value: number) => string, unit: string, multiplier = 1): MacroMetric {
  const latest = rows[0], previous = rows[1] ?? latest;
  const change = (latest.value - previous.value) * multiplier;
  return { id, label, fred: id, value: format(latest.value), direction: direction(change), comparison: `전 관측일(${previous.date}) 대비 ${signed(change)}${unit}`, observationDate: latest.date };
}
function yoyMetric(id: string, label: string, rows: Observation[]): MacroMetric {
  if (rows.length < 14) throw new Error(`${id} needs at least 14 monthly observations`);
  const yoy = (rows[0].value / rows[12].value - 1) * 100;
  const priorYoy = (rows[1].value / rows[13].value - 1) * 100;
  const change = yoy - priorYoy;
  return { id, label, fred: id, value: `${yoy.toFixed(1)}%`, direction: direction(change, .049), comparison: `직전 발표 ${priorYoy.toFixed(1)}% 대비 ${signed(change, 1)}%p`, observationDate: rows[0].date };
}
function yoySeries(rows: Observation[], count = 36): MacroPoint[] {
  return rows.slice(0, Math.min(count, rows.length - 12)).map((row, index) => ({ label: row.date, value: (row.value / rows[index + 12].value - 1) * 100 })).reverse();
}

async function fetchFredMacroData(): Promise<MacroData> {
  const ids = ["DGS1MO", "DGS3MO", "DGS6MO", "DGS1", "DGS2", "DGS3", "DGS5", "DGS7", "DGS10", "DGS20", "DGS30", "T10Y2Y", "CPIAUCSL", "CPILFESL", "PCEPILFE", "T10YIE", "DTWEXBGS", "DEXKOUS", "DEXJPUS", "DEXUSEU", "WALCL"] as const;
  const result = await Promise.all(ids.map(id => observations(id, id === "WALCL" ? 1200 : ["CPIAUCSL", "CPILFESL", "PCEPILFE"].includes(id) ? 50 : 370)));
  const rows = Object.fromEntries(ids.map((id, index) => [id, result[index]])) as Record<(typeof ids)[number], Observation[]>;
  const bondMetrics = [
    dailyMetric("DGS2", "US 2Y", rows.DGS2, value => `${value.toFixed(2)}%`, "bp", 100),
    dailyMetric("DGS10", "US 10Y", rows.DGS10, value => `${value.toFixed(2)}%`, "bp", 100),
    dailyMetric("DGS30", "US 30Y", rows.DGS30, value => `${value.toFixed(2)}%`, "bp", 100),
    dailyMetric("T10Y2Y", "10Y–2Y Spread", rows.T10Y2Y, value => `${signed(value * 100, 0)}bp`, "bp", 100),
  ];
  const inflationMetrics = [
    yoyMetric("CPIAUCSL", "CPI YoY", rows.CPIAUCSL), yoyMetric("CPILFESL", "Core CPI YoY", rows.CPILFESL),
    yoyMetric("PCEPILFE", "Core PCE YoY", rows.PCEPILFE), dailyMetric("T10YIE", "10Y Breakeven", rows.T10YIE, value => `${value.toFixed(2)}%`, "bp", 100),
  ];
  const fxMetrics = [
    dailyMetric("DTWEXBGS", "Broad Dollar", rows.DTWEXBGS, value => value.toFixed(2), "%", 100 / rows.DTWEXBGS[1].value),
    dailyMetric("DEXKOUS", "USD/KRW", rows.DEXKOUS, value => value.toLocaleString("en-US", { maximumFractionDigits: 2 }), "원"),
    dailyMetric("DEXJPUS", "USD/JPY", rows.DEXJPUS, value => value.toFixed(2), "엔"),
    dailyMetric("DEXUSEU", "EUR/USD", rows.DEXUSEU, value => value.toFixed(4), "%", 100 / rows.DEXUSEU[1].value),
  ];
  const sticky = inflationMetrics.slice(0, 3).filter(item => item.direction !== "down").length >= 2;
  const strongDollar = fxMetrics[0].direction === "up" && fxMetrics[1].direction === "up";
  const longRateUp = bondMetrics[1].direction === "up" || bondMetrics[2].direction === "up";
  const summary = `${longRateUp ? "미 장기금리가 상승하고" : "미 장기금리가 안정되고"}, ${sticky ? "근원물가 둔화가 정체된 가운데" : "물가 둔화가 이어지는 가운데"} 달러는 ${strongDollar ? "강세" : "혼조"}를 보이고 있습니다.`;
  const allDates = [...bondMetrics, ...inflationMetrics, ...fxMetrics].map(item => item.observationDate).sort();
  const curveIds = [["1M", "DGS1MO"], ["3M", "DGS3MO"], ["6M", "DGS6MO"], ["1Y", "DGS1"], ["2Y", "DGS2"], ["3Y", "DGS3"], ["5Y", "DGS5"], ["7Y", "DGS7"], ["10Y", "DGS10"], ["20Y", "DGS20"], ["30Y", "DGS30"]] as const;
  const curveDate = rows[curveIds[0][1]].find(candidate => curveIds.every(([, id]) => rows[id].some(item => item.date === candidate.date)))?.date;
  if (!curveDate) throw new Error("No common observation date exists for the Treasury yield curve");
  const fed = rows.WALCL, fedLatest = fed[0];
  const fedChangeMetric = (id: string, label: string, comparisonIndex: number): MacroMetric => { const previous = fed[Math.min(comparisonIndex, fed.length - 1)], change = fedLatest.value - previous.value; return { id, fred: "WALCL", label, value: `${change >= 0 ? "+" : "−"}$${Math.abs(change / 1000).toFixed(1)}B`, direction: direction(change), comparison: `${previous.date} 대비`, observationDate: fedLatest.date }; };
  const fedMetrics: MacroMetric[] = [{ id: "WALCL", fred: "WALCL", label: "Total Assets", value: `$${(fedLatest.value / 1_000_000).toFixed(2)}T`, direction: direction(fedLatest.value - fed[1].value), comparison: "연준 총자산", observationDate: fedLatest.date }, fedChangeMetric("WALCL-WOW", "전주 대비", 1), fedChangeMetric("WALCL-3M", "3개월 대비", 13), fedChangeMetric("WALCL-1Y", "1년 대비", 52)];
  return {
    source: "fred", asOf: allDates.at(-1) ?? "", snapshotAt: new Date().toISOString(), summary,
    bond: { metrics: bondMetrics, series: ["DGS2", "DGS10", "DGS30"].map((id, index) => ({ name: id.replace("DGS", "") + "Y", color: colors[index], points: sample(rows[id as "DGS2"], 24) })), curve: curveIds.map(([label, id]) => { const observation = rows[id].find(item => item.date === curveDate)!; return { label, value: observation.value, observationDate: curveDate }; }), signal: longRateUp ? "장기금리 상승 · Curve Steepening" : "장기금리 안정" },
    inflation: { metrics: inflationMetrics, series: [["CPI", rows.CPIAUCSL], ["Core CPI", rows.CPILFESL], ["Core PCE", rows.PCEPILFE]].map(([name, values], index) => ({ name: String(name), color: colors[index], points: yoySeries(values as Observation[]) })), signal: sticky ? "STICKY · 근원물가 둔화 속도가 정체되고 있음" : "COOLING · 물가 둔화가 이어지고 있음" },
    fx: { metrics: fxMetrics, broad: sample(rows.DTWEXBGS, 24), krw: sample(rows.DEXKOUS, 24), signal: strongDollar ? "STRONG · 달러 강세가 원화 약세 압력으로 연결" : "MIXED · 달러 방향성이 엇갈림" },
    fed: { metrics: fedMetrics, series: [...fed].reverse().map(item => ({ label: item.date, value: item.value })), signal: fedLatest.value < fed[13].value ? "CONTRACTING · 연준 총자산이 3개월 전보다 감소한 QT 환경" : "EXPANDING · 연준 총자산이 3개월 전보다 증가" },
  };
}

async function persistedSnapshot(): Promise<MacroData | null> {
  const rows = await supabaseSelect<SnapshotRow>("api_cache", { select: "payload_json,updated_at", cache_key: `eq.${SNAPSHOT_KEY}`, limit: 1 });
  if (!rows[0]) return null;
  const value = JSON.parse(rows[0].payload_json) as MacroData;
  return { ...value, source: "stale", snapshotAt: rows[0].updated_at };
}

export async function getFredMacroData(): Promise<MacroData> {
  try {
    const value = await fetchFredMacroData();
    memorySnapshot = value;
    const now = new Date();
    await supabaseUpsert("api_cache", {
      cache_key: SNAPSHOT_KEY, payload_json: JSON.stringify(value), updated_at: now.toISOString(),
      expires_at: new Date(now.getTime() + 3600_000).toISOString(),
    }, "cache_key").catch(() => undefined);
    return value;
  } catch (error) {
    const snapshot = await persistedSnapshot().catch(() => null) ?? memorySnapshot;
    if (snapshot) return { ...snapshot, source: "stale" };
    throw error;
  }
}
