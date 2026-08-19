export type MarketMetric = { symbol: string; label: string; market: "us" | "kr"; value: string; change_pct: number; as_of: string; stale: boolean; basis: "close" | "realtime" | "delayed" };
export type HeatmapItem = { symbol: string; name: string; sector: string; industry: string; price: number; change_pct: number; market_cap_weight: number };
export type ChartPoint = { time: string; open: number | null; high: number | null; low: number | null; close: number; volume: number | null };
export type StockInterval = "daily" | "weekly" | "monthly" | "minute";
export type StockDetail = { symbol: string; name: string; market: "kr" | "us"; exchange: string; sector: string; industry: string; currency: "KRW" | "USD"; price: number; change: number; change_pct: number; volume: number | null; market_cap: number | null; per: number | null; pbr: number | null; psr: number | null; pcr: number | null; ev_ebitda: number | null; valuation_basis: string | null; valuation_source: string | null; foreign_ownership_pct: number | null; high_52w: number | null; low_52w: number | null; as_of: string; session_date: string | null; basis: "realtime" | "snapshot" | "close"; interval: StockInterval; chart: ChartPoint[] };
export type RelatedArticle = { id: string; title: string; publisher: string; published_at: string; url: string; is_representative: boolean };
export type IssueItem = { id: string; title: string; summary: string; sentiment: "positive" | "neutral" | "negative"; article_count: number; category: string; summary_method: "extractive" | "source_excerpt" | "ai"; articles: RelatedArticle[] };
export type ScheduleItem = { id: string; source: "bls" | "bea" | "federal_reserve" | "bok"; country: "US" | "KR"; category: string; title: string; scheduled_at: string; importance: "high" | "medium" | "low"; source_url: string };
export type Dashboard = {
  briefing: { stance: "risk_on" | "neutral" | "risk_off"; headline: string; summary: string; keywords: string[]; source_ids: string[]; as_of: string };
  metrics: MarketMetric[];
  heatmap: HeatmapItem[];
  schedules: ScheduleItem[];
  issues: IssueItem[];
  disclosures: { id: string; company: string; title: string; importance: "high" | "medium" | "low"; filed_at: string; source_url?: string }[];
  kcif: { id: string; title: string; summary: string; topic: string; source_url: string; as_of: string }[];
  freshness: { dataset: string; label: string; as_of: string; stale: boolean }[];
};
