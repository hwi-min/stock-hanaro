"use client";

import { useEffect, useState } from "react";
import { DetailPage } from "./DetailPage";
import { Section } from "./Section";
import { StockPriceChart } from "./StockPriceChart";
import type { StockDetail } from "@/lib/types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "/backend-api";
type LiveQuote = { type: string; item?: { symbol: string; price: number; change: number; change_pct: number; as_of: string } };

export function StockDetailClient({ symbol }: { symbol: string }) {
  const [interval, setInterval] = useState<"daily" | "minute">("daily");
  const [stock, setStock] = useState<StockDetail | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    setError("");
    fetch(`${API_BASE_URL}/api/stocks/${encodeURIComponent(symbol)}?interval=${interval}`, { cache: "no-store" })
      .then(async response => { if (!response.ok) throw new Error(response.status === 404 ? "지원하는 종목을 찾지 못했습니다." : "시세를 불러오지 못했습니다."); return response.json() as Promise<StockDetail>; })
      .then(setStock).catch(reason => setError(reason.message));
  }, [symbol, interval]);
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
  if (error) return <main className="detail-page"><div className="error-card">{error}</div></main>;
  if (!stock) return <main className="detail-page"><div className="loading-card">KIS 시세와 차트를 불러오는 중입니다.</div></main>;
  const positive = stock.change_pct >= 0;
  const money = new Intl.NumberFormat(stock.market === "kr" ? "ko-KR" : "en-US", { maximumFractionDigits: stock.market === "kr" ? 0 : 2, minimumFractionDigits: stock.market === "kr" ? 0 : 2 });
  return <DetailPage eyebrow={`${stock.sector} · ${stock.industry}`} title={`${stock.symbol} · ${stock.name}`}
    description={stock.market === "kr" ? "KIS 국내주식 시세와 실시간 체결을 결합해 핵심 가격 흐름을 제공합니다." : "KIS 해외주식 마지막 정규장 종가와 일봉 가격 흐름을 제공합니다."}>
    <section className="stock-summary">
      <div><span>{stock.market === "kr" ? "현재가" : "마지막 종가"}</span><strong>{stock.currency === "USD" ? "$" : "₩"}{money.format(stock.price)}</strong></div>
      <div><span>전일 대비</span><strong className={positive ? "up" : "down"}>{stock.change >= 0 ? "+" : ""}{money.format(stock.change)} · {stock.change_pct >= 0 ? "+" : ""}{stock.change_pct.toFixed(2)}%</strong></div>
      <div><span>거래량</span><strong>{stock.volume == null ? "-" : stock.volume.toLocaleString()}</strong><small>{stock.exchange}</small></div>
      <div><span>데이터 상태</span><strong>{stock.basis === "realtime" ? "실시간" : stock.basis === "close" ? "정규장 종가" : "최근 시세"}</strong><small>{stock.session_date ? `${stock.session_date.slice(0, 4)}.${stock.session_date.slice(4, 6)}.${stock.session_date.slice(6, 8)} 기준` : new Date(stock.as_of).toLocaleString("ko-KR")}</small></div>
    </section>
    <Section title="가격 추이"><div className="chart-toolbar"><button className={interval === "daily" ? "active" : ""} onClick={() => setInterval("daily")}>일봉</button>{stock.market === "kr" && <button className={interval === "minute" ? "active" : ""} onClick={() => setInterval("minute")}>당일 분봉</button>}</div><StockPriceChart points={stock.chart} positive={positive} interval={stock.interval} /></Section>
  </DetailPage>;
}
