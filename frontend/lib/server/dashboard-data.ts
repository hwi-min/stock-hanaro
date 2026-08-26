import "server-only";

import type { Dashboard, IssueItem } from "@/lib/types";
import { numeric, supabaseSelect } from "./supabase-rest";
import { getFreshDomesticIndices } from "./kis";

type Row = Record<string, string | number | boolean | null>;

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
  const [storedQuotes, events, summaries, news, disclosures, kcif, research] = await Promise.all([
    supabaseSelect<Row>("market_quotes", { select: "*", order: "market_cap.desc.nullslast" }),
    supabaseSelect<Row>("economic_events", { select: "*", scheduled_at_utc: `gte.${weekStart}`, and: `(scheduled_at_utc.lt.${weekEnd})`, order: "scheduled_at_utc.asc" }),
    supabaseSelect<Row>("issue_summaries", { select: "*", order: "generated_at.desc", limit: 6 }),
    supabaseSelect<Row>("news_articles", { select: "*", order: "published_at.desc.nullslast,collected_at.desc", limit: 60 }),
    supabaseSelect<Row>("disclosures", { select: "*", order: "receipt_date.desc,importance.desc,receipt_no.desc", limit: 30 }),
    supabaseSelect<Row>("kcif_reports", { select: "*", order: "report_date.desc", limit: 3 }),
    supabaseSelect<Row>("research_reports", { select: "*", order: "published_on.desc,id.desc", limit: 12 }),
  ]);
  const freshDomestic = process.env.KIS_APP_KEY && process.env.KIS_APP_SECRET ? await getFreshDomesticIndices() : [];
  const freshBySymbol = new Map(freshDomestic.map((row) => [row.symbol, row]));
  const quotes = storedQuotes.map((row) => freshBySymbol.get(String(row.symbol)) || row);

  const quoteBySymbol = new Map(quotes.map((row) => [String(row.symbol), row]));
  const metrics = metricOrder.flatMap((symbol) => {
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

  const equities = quotes.filter((row) => row.market === "us" && row.asset_type === "equity");
  const maxCap = Math.max(...equities.map((row) => numeric(row.market_cap) ?? 0), 1);
  const heatmap = equities.map((row) => ({
    symbol: String(row.symbol), name: String(row.name || row.symbol), sector: String(row.sector || "기타"),
    industry: String(row.industry || "기타"), price: numeric(row.price) ?? 0,
    change_pct: numeric(row.change_pct) ?? 0,
    market_cap_weight: row.market_cap ? Math.max(1, (numeric(row.market_cap) ?? 0) / maxCap * 24) : 1,
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
    const value = String(row.collected_at || "");
    return !best || value > best ? value : best;
  }, null);
  const freshnessSpecs: Array<[string, string, Row[], number]> = [
    ["market", "시장 데이터", quotes, 30 * 60 * 1000], ["news", "뉴스·이슈", news, 6 * 3600000],
    ["disclosure", "공시", disclosures, 36 * 3600000], ["calendar", "주요 일정", events, 36 * 3600000],
    ["kcif", "KCIF", kcif, 36 * 3600000],
  ];

  return {
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
  };
}
