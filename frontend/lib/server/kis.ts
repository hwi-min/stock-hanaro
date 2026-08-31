import "server-only";

import type { ChartPoint, StockDetail, StockInterval } from "@/lib/types";
import { numeric, supabaseSelect, supabaseUpsert } from "./supabase-rest";

type Json = Record<string, unknown>;
type CacheRow = { cache_key: string; payload_json: string; expires_at: string; updated_at: string };
type TokenRow = { environment: string; access_token: string; expires_at: string; issued_at: string };
type StockMaster = { symbol: string; name: string; market: string };
type UsStockMaster = { symbol: string; kis_symbol: string; name: string; exchange: string; sector: string; industry: string };

const inFlight = new Map<string, Promise<unknown>>();
const DOMESTIC_INDEX_SNAPSHOT_KEY = "kis:kr:index:last-success";
let memoryToken: { value: string; expiresAt: number } | null = null;

function env(name: string) {
  const value = process.env[name];
  if (!value) throw new Error(`${name} is required`);
  return value;
}

function baseUrl() {
  return process.env.KIS_IS_MOCK === "true"
    ? "https://openapivts.koreainvestment.com:29443"
    : "https://openapi.koreainvestment.com:9443";
}

async function token(): Promise<string> {
  const now = Date.now();
  if (memoryToken && now + 5 * 60000 < memoryToken.expiresAt) return memoryToken.value;
  const environment = process.env.KIS_IS_MOCK === "true" ? "mock" : "real";
  const rows = await supabaseSelect<TokenRow>("kis_tokens", { select: "*", environment: `eq.${environment}`, limit: 1 });
  const cached = rows[0];
  if (cached && now + 5 * 60000 < new Date(cached.expires_at).getTime()) {
    memoryToken = { value: cached.access_token, expiresAt: new Date(cached.expires_at).getTime() };
    return cached.access_token;
  }
  const response = await fetch(`${baseUrl()}/oauth2/tokenP`, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ grant_type: "client_credentials", appkey: env("KIS_APP_KEY"), appsecret: env("KIS_APP_SECRET") }),
  });
  if (!response.ok) throw new Error(`KIS token failed (${response.status})`);
  const data = await response.json() as { access_token: string; expires_in?: number };
  const issuedAt = new Date();
  const expiresAt = new Date(issuedAt.getTime() + Math.max((data.expires_in ?? 86400) - 600, 60) * 1000);
  memoryToken = { value: data.access_token, expiresAt: expiresAt.getTime() };
  await supabaseUpsert("kis_tokens", {
    environment, access_token: data.access_token, issued_at: issuedAt.toISOString(), expires_at: expiresAt.toISOString(),
  }, "environment");
  return data.access_token;
}

async function kisGet(path: string, trId: string, params: Record<string, string>): Promise<Json> {
  const query = new URLSearchParams(params);
  const response = await fetch(`${baseUrl()}${path}?${query}`, {
    headers: {
      authorization: `Bearer ${await token()}`, appkey: env("KIS_APP_KEY"), appsecret: env("KIS_APP_SECRET"), tr_id: trId, custtype: "P",
    },
    cache: "no-store",
  });
  if (!response.ok) throw new Error(`KIS ${trId} failed (${response.status})`);
  const data = await response.json() as Json;
  if (data.rt_cd !== undefined && data.rt_cd !== "0") throw new Error(`KIS ${trId}: ${data.msg_cd} ${data.msg1}`);
  return data;
}

async function cached<T>(key: string, ttlSeconds: number, loader: () => Promise<T>): Promise<{ value: T; cachedAt: string; hit: boolean }> {
  const rows = await supabaseSelect<CacheRow>("api_cache", { select: "*", cache_key: `eq.${key}`, limit: 1 });
  const row = rows[0];
  if (row && new Date(row.expires_at).getTime() > Date.now()) {
    return { value: JSON.parse(row.payload_json) as T, cachedAt: row.updated_at, hit: true };
  }
  let pending = inFlight.get(key) as Promise<T> | undefined;
  if (!pending) {
    pending = loader(); inFlight.set(key, pending);
  }
  try {
    const value = await pending;
    const now = new Date();
    await supabaseUpsert("api_cache", {
      cache_key: key, payload_json: JSON.stringify(value), updated_at: now.toISOString(),
      expires_at: new Date(now.getTime() + ttlSeconds * 1000).toISOString(),
    }, "cache_key");
    return { value, cachedAt: now.toISOString(), hit: false };
  } catch (error) {
    if (row) return { value: JSON.parse(row.payload_json) as T, cachedAt: row.updated_at, hit: true };
    throw error;
  } finally {
    inFlight.delete(key);
  }
}

function kstParts(now = new Date()) {
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone: "Asia/Seoul", weekday: "short", hour: "2-digit", minute: "2-digit", second: "2-digit", hourCycle: "h23",
  }).formatToParts(now);
  const get = (type: string) => parts.find((part) => part.type === type)?.value || "0";
  return { weekday: get("weekday"), seconds: Number(get("hour")) * 3600 + Number(get("minute")) * 60 + Number(get("second")) };
}

function marketCode() {
  const { weekday, seconds } = kstParts();
  if (["Sat", "Sun"].includes(weekday)) return "J";
  return (seconds >= 8 * 3600 && seconds < 8 * 3600 + 50 * 60)
    || (seconds >= 9 * 3600 + 30 && seconds < 15 * 3600 + 20 * 60)
    || (seconds >= 15 * 3600 + 40 * 60 && seconds < 20 * 3600) ? "NX" : "J";
}

function quoteTtl() {
  const { weekday, seconds } = kstParts();
  if (["Sat", "Sun"].includes(weekday)) return 43200;
  if (seconds >= 8 * 3600 && seconds < 8 * 3600 + 50 * 60) return 30;
  if (seconds >= 8 * 3600 + 50 * 60 && seconds < 9 * 3600) return 60;
  if (seconds >= 9 * 3600 && seconds < 15 * 3600 + 30 * 60) return 10;
  if (seconds >= 15 * 3600 + 30 * 60 && seconds < 15 * 3600 + 40 * 60) return 30;
  if (seconds >= 15 * 3600 + 40 * 60 && seconds < 20 * 3600) return 30;
  return 43200;
}

function usMarketOpen() {
  const parts = new Intl.DateTimeFormat("en-US", { timeZone: "America/New_York", weekday: "short", hour: "2-digit", minute: "2-digit", hourCycle: "h23" }).formatToParts(new Date());
  const get = (type: string) => parts.find(part => part.type === type)?.value ?? "0";
  const minutes = Number(get("hour")) * 60 + Number(get("minute"));
  return !["Sat", "Sun"].includes(get("weekday")) && minutes >= 4 * 60 && minutes < 20 * 60;
}

function usQuoteTtl() { return usMarketOpen() ? 60 : 43200; }
function usChartTtl() { return usMarketOpen() ? 300 : 43200; }

async function domesticPrice(symbol: string, code: string) {
  const next = code !== "J";
  const data = await kisGet(
    next ? "/uapi/domestic-stock/v1/quotations/inquire-price-2" : "/uapi/domestic-stock/v1/quotations/inquire-price",
    next ? "FHPST01010000" : "FHKST01010100",
    { FID_COND_MRKT_DIV_CODE: code, FID_INPUT_ISCD: symbol },
  );
  const output = (data.output || {}) as Json;
  const price = numeric(output.stck_prpr as string);
  if (!price || price <= 0) throw new Error(`KIS returned no domestic price for ${symbol}`);
  return {
    price, change: numeric(output.prdy_vrss as string), change_pct: numeric(output.prdy_ctrt as string),
    volume: numeric(output.acml_vol as string), market_cap: numeric(output.hts_avls as string), per: numeric(output.per as string),
    pbr: numeric(output.pbr as string), foreign_ownership_pct: numeric(output.hts_frgn_ehrt as string),
    high_52w: numeric(output.d250_hgpr as string), low_52w: numeric(output.d250_lwpr as string),
    name: String(output.hts_kor_isnm || ""), as_of: new Date().toISOString(), market_source: code === "NX" ? "NXT" : "KRX",
  };
}

async function domesticIndex(symbol: string, code: string, name: string) {
  const data = await kisGet("/uapi/domestic-stock/v1/quotations/inquire-index-price", "FHPUP02100000", {
    FID_COND_MRKT_DIV_CODE: "U", FID_INPUT_ISCD: code,
  });
  const output = (data.output || {}) as Json;
  const price = numeric(output.bstp_nmix_prpr);
  if (!price || price <= 0) throw new Error(`KIS returned no index price for ${symbol}`);
  return {
    provider: "kis", market: "kr", asset_type: "index", exchange: "KRX", symbol, name,
    sector: null, industry: null, currency: "KRW", price,
    change: numeric(output.bstp_nmix_prdy_vrss), change_pct: numeric(output.bstp_nmix_prdy_ctrt),
    volume: numeric(output.acml_vol), market_cap: null, as_of: new Date().toISOString(), collected_at: new Date().toISOString(),
  };
}

export async function getFreshDomesticIndices() {
  const ttl = (() => {
    const value = quoteTtl();
    return value === 10 ? 30 : value;
  })();
  const cachePhase = ttl >= 43200 ? "closed" : "live";
  const specs = [["KOSPI", "0001", "KOSPI"], ["KOSDAQ", "1001", "KOSDAQ"], ["KOSPI200", "2001", "KOSPI 200"]] as const;
  const results = await Promise.allSettled(specs.map(([symbol, code, name]) =>
    cached(`kis:kr:index:${cachePhase}:${symbol}`, ttl, () => domesticIndex(symbol, code, name)).then((result) => result.value)
  ));
  const rows = results.flatMap((result) => result.status === "fulfilled" ? [result.value] : []);
  if (rows.length) {
    const now = new Date();
    await supabaseUpsert("api_cache", {
      cache_key: DOMESTIC_INDEX_SNAPSHOT_KEY,
      payload_json: JSON.stringify(rows),
      updated_at: now.toISOString(),
      expires_at: new Date(now.getTime() + 30 * 86400000).toISOString(),
    }, "cache_key", { timeoutMs: 2000 }).catch(() => undefined);
  }
  return rows;
}

type DomesticIndex = Awaited<ReturnType<typeof domesticIndex>>;

export async function getLastCachedDomesticIndices() {
  const snapshot = await supabaseSelect<CacheRow>("api_cache", {
    select: "payload_json,updated_at", cache_key: `eq.${DOMESTIC_INDEX_SNAPSHOT_KEY}`, limit: 1,
  }, { timeoutMs: 2000 }).catch(() => []);
  if (snapshot[0]) return JSON.parse(snapshot[0].payload_json) as DomesticIndex[];

  const symbols = ["KOSPI", "KOSDAQ", "KOSPI200"] as const;
  const results = await Promise.allSettled(symbols.map(async (symbol) => {
    const rows = await supabaseSelect<CacheRow>("api_cache", {
      select: "payload_json,updated_at", cache_key: `eq.kis:kr:index:live:${symbol}`, limit: 1,
    }, { timeoutMs: 2000 });
    return rows[0] ? JSON.parse(rows[0].payload_json) as DomesticIndex : null;
  }));
  return results.flatMap((result) => result.status === "fulfilled" && result.value ? [result.value] : []);
}

function ymd(date: Date) { return date.toISOString().slice(0, 10).replaceAll("-", ""); }

async function domesticChart(symbol: string, interval: StockInterval): Promise<ChartPoint[]> {
  const period = interval === "weekly" ? "W" : interval === "monthly" ? "M" : "D";
  const end = new Date();
  const lookback = period === "D" ? 200 : period === "W" ? 1095 : 3650;
  const start = new Date(end.getTime() - lookback * 86400000);
  const data = await kisGet("/uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice", "FHKST03010100", {
    FID_COND_MRKT_DIV_CODE: "J", FID_INPUT_ISCD: symbol, FID_INPUT_DATE_1: ymd(start), FID_INPUT_DATE_2: ymd(end),
    FID_PERIOD_DIV_CODE: period, FID_ORG_ADJ_PRC: "0",
  });
  const rows = ((data.output2 || []) as Json[]).slice(0, 100);
  return rows.flatMap((row) => {
    const close = numeric(row.stck_clpr as string); if (close === null) return [];
    return [{ time: String(row.stck_bsop_date), open: numeric(row.stck_oprc as string), high: numeric(row.stck_hgpr as string), low: numeric(row.stck_lwpr as string), close, volume: numeric(row.acml_vol as string) }];
  }).reverse();
}

async function overseasPrice(symbol: string, exchange: string) {
  const data = await kisGet("/uapi/overseas-price/v1/quotations/price-detail", "HHDFS76200200", { AUTH: "", EXCD: exchange, SYMB: symbol });
  const output = (data.output || {}) as Json, price = numeric(output.last);
  if (price === null || price <= 0) throw new Error(`KIS returned no overseas price for ${exchange}:${symbol}`);
  const base = numeric(output.base), change = base ? price - base : numeric(output.diff) ?? 0;
  return {
    price, change, change_pct: base ? change / base * 100 : numeric(output.rate) ?? 0,
    volume: numeric(output.tvol), market_cap: numeric(output.tomv), per: numeric(output.perx), pbr: numeric(output.pbrx),
    high_52w: numeric(output.h52p), low_52w: numeric(output.l52p), name: String(output.name || symbol),
    as_of: new Date().toISOString(), market_source: exchange,
  };
}

async function overseasDailyChart(symbol: string, exchange: string): Promise<ChartPoint[]> {
  const data = await kisGet("/uapi/overseas-price/v1/quotations/dailyprice", "HHDFS76240000", { AUTH: "", EXCD: exchange, SYMB: symbol, GUBN: "0", BYMD: "", MODP: "1" });
  return ((data.output2 || []) as Json[]).flatMap(row => { const close = numeric(row.clos); return close === null ? [] : [{ time: String(row.xymd), open: numeric(row.open), high: numeric(row.high), low: numeric(row.low), close, volume: numeric(row.tvol) }]; }).reverse();
}

function aggregateChart(points: ChartPoint[], interval: StockInterval): ChartPoint[] {
  if (interval === "daily") return points;
  const grouped = new Map<string, ChartPoint[]>();
  for (const point of points) {
    const date = new Date(`${point.time.slice(0, 4)}-${point.time.slice(4, 6)}-${point.time.slice(6, 8)}T00:00:00Z`);
    const key = interval === "monthly" ? point.time.slice(0, 6) : `${date.getUTCFullYear()}-${Math.floor((date.getTime() - Date.UTC(date.getUTCFullYear(), 0, 1)) / 604800000)}`;
    grouped.set(key, [...(grouped.get(key) ?? []), point]);
  }
  return [...grouped.values()].map(rows => {
    const highs = rows.flatMap(row => row.high === null ? [] : [row.high]);
    const lows = rows.flatMap(row => row.low === null ? [] : [row.low]);
    return { time: rows.at(-1)!.time, open: rows[0].open, high: highs.length ? Math.max(...highs) : null, low: lows.length ? Math.min(...lows) : null, close: rows.at(-1)!.close, volume: rows.reduce((sum, row) => sum + (row.volume ?? 0), 0) };
  });
}

async function resolveUsStock(symbol: string): Promise<UsStockMaster> {
  const rows = await supabaseSelect<UsStockMaster>("sp500_constituents", { select: "symbol,kis_symbol,name,exchange,sector,industry", symbol: `eq.${symbol}`, active: "eq.true", limit: 1 });
  if (rows[0]) return rows[0];
  for (const exchange of ["NAS", "NYS", "AMS"]) {
    try {
      const result = await cached(`kis:us:quote:${exchange}:${symbol}`, usQuoteTtl(), () => overseasPrice(symbol, exchange));
      return { symbol, kis_symbol: symbol, name: result.value.name || symbol, exchange, sector: "US Equity", industry: "미국 상장주식" };
    } catch { /* Try the next US exchange for direct ticker lookup. */ }
  }
  throw new Error(`KIS에서 미국 종목 ${symbol}을 찾지 못했습니다`);
}

async function valuation(symbol: string) {
  const [invest, wise] = await Promise.allSettled([
    fetch(`https://theinvest.co.kr/compinfo.php?cd=${symbol}`, { headers: { "User-Agent": "Mozilla/5.0 (compatible; StockHanaro/0.1)" } }).then((r) => r.ok ? r.text() : ""),
    fetch(`https://comp.wisereport.co.kr/company/c1010001.aspx?cmp_cd=${symbol}`, { headers: { "User-Agent": "Mozilla/5.0 (compatible; StockHanaro/0.1)" } }).then((r) => r.ok ? r.text() : ""),
  ]);
  const text = (result: PromiseSettledResult<string>) => result.status === "fulfilled" ? result.value.replace(/<[^>]*>/g, " ").replace(/&nbsp;/g, " ") : "";
  const metric = (value: string, label: string) => numeric(value.match(new RegExp(`${label.replace("/", "\\/")}\\s+(-?[\\d,.]+)`, "i"))?.[1]?.replaceAll(",", ""));
  const investText = text(invest), wiseText = text(wise);
  const psr = metric(investText, "PSR"), pcr = metric(investText, "PCR"), ev_ebitda = metric(wiseText, "EV/EBITDA");
  const sources = [...(psr !== null || pcr !== null ? ["더인베스트"] : []), ...(ev_ebitda !== null ? ["WiseReport"] : [])];
  return { psr, pcr, ev_ebitda, basis: sources.length ? "최근 확정실적(TTM/연간)" : null, source: sources.join(" · ") || null };
}

export async function getWorkerStockDetail(symbolValue: string, interval: StockInterval, marketHint?: "kr" | "us"): Promise<StockDetail | null> {
  const symbol = symbolValue.toUpperCase();
  if (marketHint === "us" || (!marketHint && !/^\d{6}$/.test(symbol))) {
    const master = await resolveUsStock(symbol), quoteTtlSeconds = usQuoteTtl();
    const quoteResult = await cached(`kis:us:quote:${master.exchange}:${master.kis_symbol}`, quoteTtlSeconds, () => overseasPrice(master.kis_symbol, master.exchange));
    const chartResult = await cached(`kis:us:chart:${master.exchange}:${master.kis_symbol}:daily`, usChartTtl(), () => overseasDailyChart(master.kis_symbol, master.exchange));
    const chart = aggregateChart(chartResult.value, interval), quote = quoteResult.value;
    const latest = chart.at(-1), previous = chart.at(-2);
    const closeChange = latest && previous ? latest.close - previous.close : quote.change;
    const closeChangePct = latest && previous && previous.close ? closeChange / previous.close * 100 : quote.change_pct;
    return {
      symbol, name: master.name || quote.name || symbol, market: "us", exchange: master.exchange, market_source: master.exchange,
      sector: master.sector || "US Equity", industry: master.industry || "미국 상장주식", currency: "USD",
      price: latest?.close ?? quote.price, change: closeChange, change_pct: closeChangePct, volume: latest?.volume ?? quote.volume,
      market_cap: quote.market_cap, per: quote.per, pbr: quote.pbr, psr: null, pcr: null, ev_ebitda: null,
      valuation_basis: null, valuation_source: null, foreign_ownership_pct: null, high_52w: quote.high_52w, low_52w: quote.low_52w,
      as_of: quote.as_of, cached_at: quoteResult.cachedAt, cache_hit: quoteResult.hit && chartResult.hit, refresh_after_seconds: Math.min(quoteTtlSeconds, usChartTtl()),
      session_date: latest?.time ?? null, basis: "close", interval, chart,
    };
  }
  const masters = await supabaseSelect<StockMaster>("stock_masters", { select: "symbol,name,market", symbol: `eq.${symbol}`, active: "eq.true", limit: 1 });
  const master = masters[0];
  if (!master) return null;
  let code = marketCode();
  const ttl = quoteTtl();
  let quoteResult;
  try {
    quoteResult = await cached(`kis:kr:quote:${code}:${symbol}`, ttl, () => domesticPrice(symbol, code));
  } catch (error) {
    if (code !== "NX") throw error;
    code = "J";
    quoteResult = await cached(`kis:kr:quote:J:${symbol}`, ttl, () => domesticPrice(symbol, "J"));
  }
  const fundamentals = await cached(`kis:kr:fundamentals:v2:${symbol}`, 86400, () => domesticPrice(symbol, "J")).catch(() => null);
  const valuationResult = await cached(`valuation:kr:${symbol}`, 86400, () => valuation(symbol)).catch(() => null);
  const chartResult = await cached(`kis:kr:chart:${symbol}:${interval}`, 300, () => domesticChart(symbol, interval));
  const quote = quoteResult.value;
  const fundamental = fundamentals?.value;
  const extra = valuationResult?.value;
  return {
    symbol, name: master.name || quote.name || symbol, market: "kr", exchange: "KRX", market_source: quote.market_source,
    sector: master.market, industry: "국내 상장주식", currency: "KRW", price: quote.price,
    change: quote.change ?? 0, change_pct: quote.change_pct ?? 0, volume: quote.volume,
    market_cap: fundamental?.market_cap ?? null, per: fundamental?.per ?? null, pbr: fundamental?.pbr ?? null,
    psr: extra?.psr ?? null, pcr: extra?.pcr ?? null, ev_ebitda: extra?.ev_ebitda ?? null,
    valuation_basis: extra?.basis ?? null, valuation_source: extra?.source ?? null,
    foreign_ownership_pct: fundamental?.foreign_ownership_pct ?? null, high_52w: fundamental?.high_52w ?? null, low_52w: fundamental?.low_52w ?? null,
    as_of: quote.as_of, cached_at: quoteResult.cachedAt, cache_hit: quoteResult.hit, refresh_after_seconds: ttl,
    session_date: null, basis: "snapshot", interval, chart: chartResult.value,
  };
}
