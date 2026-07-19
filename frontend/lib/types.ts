export type MarketMetric = { symbol: string; label: string; market: "us" | "kr"; value: string; change_pct: number; as_of: string; stale: boolean };
export type HeatmapItem = { symbol: string; name: string; sector: string; industry: string; price: number; change_pct: number; market_cap_weight: number };
export type RelatedArticle = { id: string; title: string; publisher: string; published_at: string; url: string; is_representative: boolean };
export type IssueItem = { id: string; title: string; summary: string; sentiment: "positive" | "neutral" | "negative"; article_count: number; category: string; articles: RelatedArticle[] };
export type ScheduleItem = { id: string; source: "bls" | "bea" | "federal_reserve" | "bok"; country: "US" | "KR"; category: string; title: string; scheduled_at: string; importance: "high" | "medium" | "low"; source_url: string };
export type Dashboard = {
  briefing: { stance: "risk_on" | "neutral" | "risk_off"; headline: string; summary: string; keywords: string[]; source_ids: string[]; as_of: string };
  metrics: MarketMetric[];
  heatmap: HeatmapItem[];
  schedules: ScheduleItem[];
  issues: IssueItem[];
  disclosures: { id: string; company: string; title: string; importance: "high" | "medium" | "low"; filed_at: string }[];
  kcif: { id: string; title: string; summary: string; topic: string; source_url: string; as_of: string }[];
  freshness: { dataset: string; label: string; as_of: string; stale: boolean }[];
};
