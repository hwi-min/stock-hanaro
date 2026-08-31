import "server-only";

import type { Dashboard, IssueItem, MarketMetric } from "@/lib/types";
import { numeric, supabaseSelect, supabaseUpsert } from "./supabase-rest";
import { getFreshDomesticIndices, getLastCachedDomesticIndices } from "./kis";

type Row = Record<string, string | number | boolean | null>;
type DatasetResult = { rows: Row[]; live: boolean };
type DashboardCacheRow = { payload_json: string; updated_at: string };

const DASHBOARD_SNAPSHOT_KEY = "dashboard:home:last-success:v1";

async function loadRows(table: string, query: Record<string, string | number | boolean>): Promise<DatasetResult> {
  try {
    return { rows: await supabaseSelect<Row>(table, query, { timeoutMs: 1800 }), live: true };
  } catch {
    try {
      return { rows: await supabaseSelect<Row>(table, query, { timeoutMs: 1000 }), live: true };
    } catch {
      return { rows: [], live: false };
    }
  }
}

async function readDashboardSnapshot(): Promise<Dashboard | null> {
  try {
    const rows = await supabaseSelect<DashboardCacheRow>("api_cache", {
      select: "payload_json,updated_at", cache_key: `eq.${DASHBOARD_SNAPSHOT_KEY}`, limit: 1,
    }, { timeoutMs: 1200 });
    return rows[0] ? JSON.parse(rows[0].payload_json) as Dashboard : null;
  } catch {
    return null;
  }
}

async function writeDashboardSnapshot(value: Dashboard): Promise<void> {
  const now = new Date();
  await supabaseUpsert("api_cache", {
    cache_key: DASHBOARD_SNAPSHOT_KEY,
    payload_json: JSON.stringify(value),
    updated_at: now.toISOString(),
    expires_at: new Date(now.getTime() + 30 * 86400000).toISOString(),
  }, "cache_key", { timeoutMs: 1200 });
}

const metricOrder = ["SPX", "DOW30", "NASDAQ", "RUSSELL2000", "VIX", "GOLD", "KOSPI", "KOSDAQ", "KOSPI200", "USDKRW", "KTB3Y"];
const labels: Record<string, string> = {
  SPX: "S&P 500", DOW30: "Dow 30", NASDAQ: "NASDAQ", RUSSELL2000: "Russell 2000",
  VIX: "VIX", GOLD: "Gold", KOSPI: "KOSPI", KOSDAQ: "KOSDAQ", KOSPI200: "KOSPI 200",
  USDKRW: "USD/KRW", KTB3Y: "국고채 3년",
};

function mondayBounds(now = new Date()) {
  const kst = new Date(now.getTime() + 9 * 60 * 60 * 1000);
  const day = kst.getUTCDay() || 7;
  const start = new Date(Date.UTC(kst.getUTCFullYear(), kst.getUTCMonth(), kst.getUTCDate() - day + 1) - 9 * 60 * 60 * 1000);
  return [start.toISOString(), new Date(start.getTime() + 7 * 86400000).toISOString()] as const;
}

function stale(value: unknown, thresholdMs: number) {
  return !value || Date.now() - new Date(String(value)).getTime() > thresholdMs;
}

export async function getWorkerDashboard(): Promise<Dashboard> {
  const [weekStart, weekEnd] = mondayBounds();
  const snapshotPromise = readDashboardSnapshot();
  const cachedDomesticPromise = process.env.KIS_APP_KEY && process.env.KIS_APP_SECRET
    ? getLastCachedDomesticIndices().catch(() => [])
    : Promise.resolve([]);
  const freshDomesticPromise = process.env.KIS_APP_KEY && process.env.KIS_APP_SECRET
    ? Promise.race([
      getFreshDomesticIndices().then((rows) => ({ rows, timedOut: false })),
      new Promise<{ rows: Awaited<ReturnType<typeof getFreshDomesticIndices>>; timedOut: boolean }>((resolve) =>
        setTimeout(() => resolve({ rows: [], timedOut: true }), 1200)),
    ])
    : Promise.resolve({ rows: [], timedOut: false });
  const minimumLoadingTime = new Promise<void>((resolve) => setTimeout(resolve, 600));
  const [results] = await Promise.all([Promise.all([
    loadRows("market_quotes", { select: "*", order: "market_cap.desc.nullslast" }),
    loadRows("economic_events", { select: "*", scheduled_at_utc: `gte.${weekStart}`, and: `(scheduled_at_utc.lt.${weekEnd})`, order: "scheduled_at_utc.asc" }),
    loadRows("issue_summaries", { select: "*", order: "generated_at.desc", limit: 6 }),
    loadRows("news_articles", { select: "*", order: "published_at.desc.nullslast,collected_at.desc", limit: 60 }),
    loadRows("disclosures", { select: "*", order: "receipt_date.desc,importance.desc,receipt_no.desc", limit: 30 }),
    loadRows("kcif_reports", { select: "*", order: "report_date.desc", limit: 3 }),
    loadRows("research_reports", { select: "*", order: "published_on.desc,id.desc", limit: 12 }),
    loadRows("sp500_constituents", { select: "*", active: "eq.true", limit: 600 }),
    loadRows("sp500_daily_snapshots", { select: "*", order: "trading_date.desc,index_weight.desc", limit: 1200 }),
  ]), minimumLoadingTime]);
  const [marketResult, eventResult, summaryResult, newsResult, disclosureResult, kcifResult, researchResult, constituentResult, snapshotResult] = results;
  const [storedQuotes, events, summaries, news, disclosures, kcif, research, sp500Constituents, sp500Snapshots] = results.map(result => result.rows);
  const previous = await snapshotPromise;
  const domesticResult = await freshDomesticPromise;
  const cachedDomestic = await cachedDomesticPromise;
  const freshDomestic = domesticResult.rows.length ? domesticResult.rows : cachedDomestic;
  const freshBySymbol = new Map(freshDomestic.map((row) => [row.symbol, row]));
  const quotes = storedQuotes.map((row) => freshBySymbol.get(String(row.symbol)) || row);

  const quoteBySymbol = new Map(quotes.map((row) => [String(row.symbol), row]));
  let metrics: MarketMetric[] = metricOrder.flatMap((symbol) => {
    const row = quoteBySymbol.get(symbol);
    const price = numeric(row?.price);
    if (!row || !price || price <= 0) return [];
    return [{
      symbol, label: labels[symbol], market: row.market === "us" || row.market === "global" ? "us" as const : "kr" as const,
      value: `${price.toLocaleString("en-US", { minimumFractionDigits: symbol === "KTB3Y" ? 3 : 2, maximumFractionDigits: symbol === "KTB3Y" ? 3 : 2 })}${symbol === "KTB3Y" ? "%" : ""}`,
      change_pct: numeric(row.change_pct) ?? 0, as_of: String(row.as_of), stale: stale(row.collected_at, 30 * 60 * 1000),
      basis: row.market === "us" || row.market === "global" ? "close" as const : "delayed" as const,
    }];
  });

  const constituentBySymbol = new Map(sp500Constituents.map((row) => [String(row.symbol), row]));
  const snapshotCounts = sp500Snapshots.reduce<Record<string, number>>((counts, row) => {
    const value = String(row.trading_date); counts[value] = (counts[value] || 0) + 1; return counts;
  }, {});
  const minimumSnapshotRows = Math.max(1, Math.floor(sp500Constituents.length * .98));
  const snapshotDate = Object.keys(snapshotCounts).sort().reverse().find((value) => snapshotCounts[value] >= minimumSnapshotRows) || null;
  const completeSnapshots = snapshotDate ? sp500Snapshots.filter((row) => String(row.trading_date) === snapshotDate) : [];
  const equities = quotes.filter((row) => row.market === "us" && row.asset_type === "equity");
  const maxCap = Math.max(...equities.map((row) => numeric(row.market_cap) ?? 0), 1);
  const heatmap = completeSnapshots.length >= minimumSnapshotRows
    ? completeSnapshots.flatMap((row) => {
      const constituent = constituentBySymbol.get(String(row.symbol));
      if (!constituent) return [];
      return [{
        symbol: String(row.symbol), name: String(constituent.name || row.symbol), sector: String(constituent.sector || "Other"),
        industry: String(constituent.industry || "Other"), price: numeric(row.close) ?? 0,
        change_pct: numeric(row.change_pct) ?? 0, market_cap_weight: numeric(row.index_weight) ?? 0.01,
        volume: numeric(row.volume), dollar_volume: numeric(row.dollar_volume), relative_volume: numeric(row.relative_volume),
        trading_date: snapshotDate,
      }];
    })
    : equities.map((row) => ({
      symbol: String(row.symbol), name: String(row.name || row.symbol), sector: String(row.sector || "기타"),
      industry: String(row.industry || "기타"), price: numeric(row.price) ?? 0,
      change_pct: numeric(row.change_pct) ?? 0,
      market_cap_weight: row.market_cap ? Math.max(1, (numeric(row.market_cap) ?? 0) / maxCap * 24) : 1,
      volume: numeric(row.volume), dollar_volume: (numeric(row.price) ?? 0) * (numeric(row.volume) ?? 0) || null,
      relative_volume: null, trading_date: null,
    }));

  const newsById = new Map(news.map((row) => [Number(row.id), row]));
  const issues: IssueItem[] = summaries.flatMap((row) => {
    let ids: number[] = [];
    try { ids = JSON.parse(String(row.article_ids_json)); } catch { return []; }
    const articles = ids.map((id) => newsById.get(id)).filter(Boolean) as Row[];
    if (!articles.length) return [];
    return [{
      id: String(row.issue_key), title: String(row.title), summary: String(row.summary),
      sentiment: String(row.sentiment) as IssueItem["sentiment"], article_count: articles.length,
      category: String(row.category), summary_method: row.model === "rule-based-extractive" ? "extractive" as const : "ai" as const,
      articles: articles.map((article, index) => ({
        id: String(article.id), title: String(article.title), publisher: String(article.publisher || article.source),
        published_at: String(article.published_at || article.collected_at), url: String(article.canonical_url), is_representative: index === 0,
      })),
    }];
  });
  const displayIssues: IssueItem[] = issues.length ? issues : news.slice(0, 6).map((article) => ({
    id: `news-${article.id}`,
    title: String(article.title),
    summary: String(article.summary || article.title),
    sentiment: "neutral",
    article_count: 1,
    category: "주요 뉴스",
    summary_method: "source_excerpt",
    articles: [{
      id: String(article.id), title: String(article.title), publisher: String(article.publisher || article.source),
      published_at: String(article.published_at || article.collected_at), url: String(article.canonical_url), is_representative: true,
    }],
  }));

  const latestReceiptDate = disclosures[0]?.receipt_date;
  const latestDisclosures = disclosures.filter((row) => row.receipt_date === latestReceiptDate && ["high", "medium"].includes(String(row.importance))).slice(0, 10);
  const nasdaq = metrics.find((item) => item.symbol === "NASDAQ");
  const stance = !nasdaq ? "neutral" : nasdaq.change_pct > 0.3 ? "risk_on" : nasdaq.change_pct < -0.3 ? "risk_off" : "neutral";
  const direction = stance === "risk_on" ? "강세" : stance === "risk_off" ? "약세" : "혼조";
  const freshest = (rows: Row[]) => rows.reduce<string | null>((best, row) => {
    const value = String(row.collected_at || row.updated_at || row.generated_at || row.published_at
      || row.scheduled_at_kst || row.receipt_date || row.report_date || row.source_date || row.trading_date || "");
    return !best || value > best ? value : best;
  }, null);
  const freshnessSpecs: Array<[string, string, Row[], number]> = [
    ["market", "시장 데이터", quotes, 30 * 60 * 1000], ["news", "뉴스·이슈", news, 6 * 3600000],
    ["disclosure", "공시", disclosures, 36 * 3600000], ["calendar", "주요 일정", events, 36 * 3600000],
    ["kcif", "KCIF", kcif, 36 * 3600000],
  ];

  const status = (key: string, result: DatasetResult, rows: Row[]) => ({
    state: result.live ? "live" as const : previous ? "delayed" as const : "unavailable" as const,
    as_of: result.live ? freshest(rows) : previous?.data_status?.[key]?.as_of || previous?.briefing.as_of || null,
  });

  // Never let a delayed source move an index backward in time. Once a newer
  // observation was displayed, it remains until an even newer one replaces it.
  if (previous) {
    const previousDomestic = new Map(previous.metrics
      .filter((item) => ["KOSPI", "KOSDAQ", "KOSPI200"].includes(item.symbol))
      .map((item) => [item.symbol, item]));
    metrics = metrics.map((item) => {
      const olderCandidate = previousDomestic.get(item.symbol);
      if (!olderCandidate) return item;
      return new Date(olderCandidate.as_of).getTime() > new Date(item.as_of).getTime()
        ? olderCandidate
        : item;
    });
  }
  const dashboard: Dashboard = {
    briefing: {
      stance,
      headline: nasdaq ? `미국 기술주 흐름은 ${direction}, 환율과 금리를 함께 확인하세요` : "시장 데이터를 준비하고 있습니다",
      summary: displayIssues[0]?.summary || "수집 작업이 완료되면 최신 시장·뉴스 데이터를 바탕으로 브리핑을 제공합니다.",
      keywords: [...new Set(displayIssues.slice(0, 3).map((item) => item.category))].length ? [...new Set(displayIssues.slice(0, 3).map((item) => item.category))] : ["데이터 수집 대기"],
      source_ids: [...(nasdaq ? ["market:NASDAQ"] : []), ...displayIssues.slice(0, 2).map((item) => `news:${item.id}`)],
      as_of: nasdaq?.as_of || new Date().toISOString(),
    },
    metrics, heatmap,
    schedules: events.map((row) => ({
      id: `${row.source}:${row.source_event_id}`, source: String(row.source) as Dashboard["schedules"][number]["source"],
      country: String(row.country) as "US" | "KR", category: String(row.category), title: String(row.title),
      scheduled_at: String(row.scheduled_at_kst), importance: String(row.importance) as "high" | "medium" | "low", source_url: String(row.source_url),
    })),
    issues: displayIssues,
    disclosures: latestDisclosures.map((row) => ({
      id: String(row.receipt_no), company: String(row.corp_name), title: String(row.title).trim(),
      importance: String(row.importance) as "high" | "medium" | "low", filed_at: `${row.receipt_date}T00:00:00Z`, source_url: String(row.source_url),
    })),
    kcif: kcif.map((row) => ({
      id: String(row.report_no), title: String(row.title), summary: String(row.ai_summary || row.extracted_text || "").replace(/\s+/g, " ").slice(0, 240),
      topic: String(row.ai_topic || "국제금융"), source_url: String(row.source_url), as_of: String(row.ai_summarized_at || row.collected_at),
    })),
    research: research.map((row) => ({
      id: Number(row.id), category: String(row.category), title: String(row.title), broker: String(row.broker),
      analyst: row.analyst ? String(row.analyst) : null, published_on: String(row.published_on),
      stock_code: row.stock_code ? String(row.stock_code) : null, stock_name: row.stock_name ? String(row.stock_name) : null, source_url: String(row.source_url),
    })),
    freshness: freshnessSpecs.flatMap(([dataset, label, rows, threshold]) => {
      const asOf = freshest(rows);
      return asOf ? [{ dataset, label, as_of: asOf, stale: stale(asOf, threshold) }] : [];
    }),
    data_status: {
      market: status("market", marketResult, storedQuotes),
      calendar: status("calendar", eventResult, events),
      issue_summaries: status("issue_summaries", summaryResult, summaries),
      news: status("news", newsResult, news),
      disclosures: status("disclosures", disclosureResult, disclosures),
      kcif: status("kcif", kcifResult, kcif),
      research: status("research", researchResult, research),
      sp500_constituents: status("sp500_constituents", constituentResult, sp500Constituents),
      sp500_snapshots: status("sp500_snapshots", snapshotResult, sp500Snapshots),
    },
  };

  if (previous) {
    if (!marketResult.live) {
      dashboard.metrics = previous.metrics;
      dashboard.briefing = previous.briefing;
    }
    if (!eventResult.live) dashboard.schedules = previous.schedules;
    if (!summaryResult.live || !newsResult.live) {
      dashboard.issues = previous.issues;
      dashboard.briefing = previous.briefing;
    }
    if (!disclosureResult.live) dashboard.disclosures = previous.disclosures;
    if (!kcifResult.live) dashboard.kcif = previous.kcif;
    if (!researchResult.live) dashboard.research = previous.research;
    if (!constituentResult.live || !snapshotResult.live) dashboard.heatmap = previous.heatmap;
  }

  if (results.every(result => result.live) && !domesticResult.timedOut) {
    await writeDashboardSnapshot(dashboard).catch(() => undefined);
  }
  return dashboard;
}
