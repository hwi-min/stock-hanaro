"use client";

import { useEffect, useRef, useState } from "react";
import { DetailPage } from "./DetailPage";
import { Section } from "./Section";
import { StockPriceChart } from "./StockPriceChart";
import type { StockDetail, StockInterval } from "@/lib/types";
import { saveRecentStock } from "@/lib/recent-stocks";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "/backend-api";
type Quote = { symbol: string; price: number; change: number; change_pct: number; as_of: string };
type LiveQuote = { type: string; item?: Quote; items?: Quote[] };

export function StockDetailClient({ symbol, initialStock = null }: { symbol: string; initialStock?: StockDetail | null }) {
  const [interval, setInterval] = useState<StockInterval>("daily");
  const [stock, setStock] = useState<StockDetail | null>(initialStock);
  const initialRequestKey = useRef(initialStock ? `${symbol}:${initialStock.interval}` : null);
  const [requestError, setRequestError] = useState<{ key: string; message: string } | null>(null);
  const requestKey = `${symbol}:${interval}`;
  useEffect(() => {
    const key = `${symbol}:${interval}`;
    if (initialRequestKey.current === key) {
      initialRequestKey.current = null;
      return;
    }
    fetch(`${API_BASE_URL}/api/stocks/${encodeURIComponent(symbol)}?interval=${interval}`, { cache: "no-store" })
      .then(async response => { if (!response.ok) throw new Error(response.status === 404 ? "지원하는 종목을 찾지 못했습니다." : "시세를 불러오지 못했습니다."); return response.json() as Promise<StockDetail>; })
      .then(value => { setStock(value); setRequestError(null); })
      .catch(reason => setRequestError({ key, message: reason.message }));
  }, [symbol, interval]);
  const recentSymbol = stock?.symbol, recentName = stock?.name, recentMarket = stock?.market;
  useEffect(() => {
    if (recentSymbol && recentName && recentMarket) saveRecentStock({ symbol: recentSymbol, name: recentName, market: recentMarket });
  }, [recentSymbol, recentName, recentMarket]);
  useEffect(() => {
    const source = new EventSource(`${API_BASE_URL}/api/market/stream`);
    source.onmessage = event => {
      try {
        const payload = JSON.parse(event.data) as LiveQuote;
        const quote = (payload.items ?? (payload.item ? [payload.item] : [])).find(item => item.symbol === symbol);
        if (payload.type !== "quote" || !quote) return;
        setStock(current => current ? { ...current, price: quote.price, change: quote.change,
          change_pct: quote.change_pct, as_of: quote.as_of, basis: "realtime",
          chart: current.chart.length ? current.chart.map((point, index) => index === current.chart.length - 1 ? { ...point, close: quote.price } : point) : current.chart } : current);
      } catch { return; }
    };
    return () => source.close();
  }, [symbol]);
  useEffect(() => {
    if (stock?.market !== "kr") return;
    const url = `${API_BASE_URL}/api/market/subscriptions/${encodeURIComponent(symbol)}`;
    fetch(url, { method: "POST" }).catch(() => undefined);
    return () => { fetch(url, { method: "DELETE", keepalive: true }).catch(() => undefined); };
  }, [stock?.market, symbol]);
  const error = requestError?.key === requestKey ? requestError.message : "";
  if (error) return <main className="detail-page"><div className="error-card">{error}</div></main>;
  if (!stock) return <main className="detail-page"><div className="loading-card">KIS 시세와 차트를 불러오는 중입니다.</div></main>;
  const positive = stock.change_pct >= 0;
  const money = new Intl.NumberFormat(stock.market === "kr" ? "ko-KR" : "en-US", { maximumFractionDigits: stock.market === "kr" ? 0 : 2, minimumFractionDigits: stock.market === "kr" ? 0 : 2 });
  return <DetailPage eyebrow={`${stock.sector} · ${stock.industry}`} title={`${stock.symbol} · ${stock.name}`}
    description={stock.market === "kr" ? "KIS 국내주식 시세와 실시간 체결을 결합해 핵심 가격 흐름을 제공합니다." : "KIS 해외주식 마지막 정규장 종가와 일봉 가격 흐름을 제공합니다."}>
    <section className="stock-summary stock-summary-primary">
      <div><span>{stock.market === "kr" ? "현재가" : "마지막 종가"}</span><strong>{stock.currency === "USD" ? "$" : "₩"}{money.format(stock.price)}</strong></div>
      <div><span>전일 대비</span><strong className={positive ? "up" : "down"}>{stock.change >= 0 ? "+" : ""}{money.format(stock.change)} · {stock.change_pct >= 0 ? "+" : ""}{stock.change_pct.toFixed(2)}%</strong></div>
      <div><span>거래량</span><strong>{stock.volume == null ? "-" : stock.volume.toLocaleString()}</strong><small>{stock.exchange}</small></div>
      <div><span>데이터 상태</span><strong>{stock.basis === "realtime" ? "실시간" : stock.basis === "close" ? "정규장 종가" : "최근 시세"}</strong><small>{stock.session_date ? `${stock.session_date.slice(0, 4)}.${stock.session_date.slice(4, 6)}.${stock.session_date.slice(6, 8)} 기준` : new Date(stock.as_of).toLocaleString("ko-KR")}</small></div>
    </section>
    {stock.market === "kr" && <section className="investment-metrics" aria-label="투자 지표">
      <Metric label="시가총액" value={stock.market_cap == null ? "-" : `${(stock.market_cap / 10_000).toLocaleString("ko-KR", { maximumFractionDigits: 1 })}조`} />
      <Metric label="PER" value={stock.per == null ? "-" : `${stock.per.toLocaleString("ko-KR", { maximumFractionDigits: 2 })}배`} />
      <Metric label="PBR" value={stock.pbr == null ? "-" : `${stock.pbr.toLocaleString("ko-KR", { maximumFractionDigits: 2 })}배`} />
      <Metric label="PSR" value={stock.psr == null ? "-" : `${stock.psr.toLocaleString("ko-KR", { maximumFractionDigits: 2 })}배`} />
      <Metric label="PCR" value={stock.pcr == null ? "-" : `${stock.pcr.toLocaleString("ko-KR", { maximumFractionDigits: 2 })}배`} />
      <Metric label="EV/EBITDA" value={stock.ev_ebitda == null ? "-" : `${stock.ev_ebitda.toLocaleString("ko-KR", { maximumFractionDigits: 2 })}배`} />
      <Metric label="외국인" value={stock.foreign_ownership_pct == null ? "-" : `${stock.foreign_ownership_pct.toFixed(2)}%`} />
      <Metric label="52주 최고" value={stock.high_52w == null ? "-" : `${money.format(stock.high_52w)}원`} />
      <Metric label="52주 최저" value={stock.low_52w == null ? "-" : `${money.format(stock.low_52w)}원`} />
    </section>}
    {stock.market === "kr" && stock.valuation_source && <p className="valuation-source">
      추가 투자지표: {stock.valuation_source} · {stock.valuation_basis}
    </p>}
    <Section title="가격 추이"><div className="chart-toolbar">
      {(["daily", "weekly", "monthly"] as StockInterval[]).map(value => <button key={value} className={interval === value ? "active" : ""} onClick={() => setInterval(value)}>{value === "daily" ? "일봉" : value === "weekly" ? "주봉" : "월봉"}</button>)}
    </div><StockPriceChart points={stock.chart} interval={stock.interval} currency={stock.currency} /></Section>
  </DetailPage>;
}

function Metric({ label, value }: { label: string; value: string }) {
  return <div><span>{label}</span><strong>{value}</strong></div>;
}
