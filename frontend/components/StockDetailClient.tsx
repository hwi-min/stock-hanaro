"use client";

import { useEffect, useState } from "react";
import { DetailPage } from "./DetailPage";
import { Section } from "./Section";
import { StockPriceChart } from "./StockPriceChart";
import type { StockDetail, StockInterval } from "@/lib/types";
import { saveRecentStock } from "@/lib/recent-stocks";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "/backend-api";
type LiveQuote = { type: string; item?: { symbol: string; price: number; change: number; change_pct: number; as_of: string } };

export function StockDetailClient({ symbol }: { symbol: string }) {
  const [interval, setInterval] = useState<StockInterval>("daily");
  const [stock, setStock] = useState<StockDetail | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    setError("");
    fetch(`${API_BASE_URL}/api/stocks/${encodeURIComponent(symbol)}?interval=${interval}`, { cache: "no-store" })
      .then(async response => { if (!response.ok) throw new Error(response.status === 404 ? "지원하는 종목을 찾지 못했습니다." : "시세를 불러오지 못했습니다."); return response.json() as Promise<StockDetail>; })
      .then(setStock).catch(reason => setError(reason.message));
  }, [symbol, interval]);
  useEffect(() => {
    if (stock) saveRecentStock({ symbol: stock.symbol, name: stock.name, market: stock.market });
  }, [stock?.symbol, stock?.name, stock?.market]);
  useEffect(() => {
    const source = new EventSource(`${API_BASE_URL}/api/market/stream`);
    source.onmessage = event => {
      try {
        const payload = JSON.parse(event.data) as LiveQuote;
        if (payload.type !== "quote" || payload.item?.symbol !== symbol) return;
        setStock(current => current ? { ...current, price: payload.item!.price, change: payload.item!.change,
          change_pct: payload.item!.change_pct, as_of: payload.item!.as_of, basis: "realtime",
          chart: current.chart.length ? current.chart.map((point, index) => index === current.chart.length - 1 ? { ...point, close: payload.item!.price } : point) : current.chart } : current);
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
      <Metric label="외국인" value={stock.foreign_ownership_pct == null ? "-" : `${stock.foreign_ownership_pct.toFixed(2)}%`} />
      <Metric label="52주 최고" value={stock.high_52w == null ? "-" : `${money.format(stock.high_52w)}원`} />
      <Metric label="52주 최저" value={stock.low_52w == null ? "-" : `${money.format(stock.low_52w)}원`} />
    </section>}
    <Section title="가격 추이"><div className="chart-toolbar">
      {(["daily", "weekly", "monthly"] as StockInterval[]).map(value => <button key={value} className={interval === value ? "active" : ""} onClick={() => setInterval(value)}>{value === "daily" ? "일봉" : value === "weekly" ? "주봉" : "월봉"}</button>)}
    </div><StockPriceChart points={stock.chart} interval={stock.interval} currency={stock.currency} /></Section>
  </DetailPage>;
}

function Metric({ label, value }: { label: string; value: string }) {
  return <div><span>{label}</span><strong>{value}</strong></div>;
}
