"use client";

import { useEffect, useMemo, useState } from "react";
import type { MarketMetric } from "@/lib/types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "/backend-api";
type Quote = { symbol: string; price: number; change_pct: number; as_of: string; basis: "realtime" };
type StreamEvent = { type: string; connected: boolean; item?: Quote; items?: Quote[] };

export function LiveMarketBoard({ initialMetrics }: { initialMetrics: MarketMetric[] }) {
  const [metrics, setMetrics] = useState(initialMetrics);
  const [connected, setConnected] = useState(false);
  useEffect(() => {
    const source = new EventSource(`${API_BASE_URL}/api/market/stream`);
    source.onmessage = event => {
      let payload: StreamEvent;
      try { payload = JSON.parse(event.data) as StreamEvent; }
      catch { return; }
      setConnected(payload.connected);
      const updates = payload.type === "snapshot" ? payload.items ?? [] : payload.item ? [payload.item] : [];
      if (!updates.length) return;
      setMetrics(current => current.map(metric => {
        const update = updates.find(item => item.symbol === metric.symbol);
        return update ? { ...metric, value: update.price.toLocaleString("en-US", { minimumFractionDigits: 2 }), change_pct: update.change_pct, as_of: update.as_of, stale: false, basis: "realtime" } : metric;
      }));
    };
    source.onerror = () => setConnected(false);
    return () => source.close();
  }, []);
  const rows = useMemo(() => [
    { id: "us", label: "US Market", note: "마지막 정규장 종가", metrics: metrics.filter(metric => metric.market === "us") },
    { id: "kr", label: "KR Market", note: connected ? "실시간" : "최근 스냅샷", metrics: metrics.filter(metric => metric.market === "kr") },
  ], [metrics, connected]);
  return <section className="market-board" aria-label="주요 시장 지표">
    {rows.map(row => <div className="market-row" key={row.id}>
      <div className="market-label"><span className="market-signal" aria-hidden="true">◉</span><div><b>{row.label}</b><small>{row.note}</small></div></div>
      <div className="market-tickers">{row.metrics.map(metric => <article key={metric.symbol}>
        <div><span>{metric.label}</span><strong>{metric.value}</strong><em className={metric.change_pct >= 0 ? "up" : "down"}>{metric.change_pct >= 0 ? "+" : ""}{metric.change_pct.toFixed(2)}%</em></div>
        <svg className={metric.change_pct >= 0 ? "sparkline positive-line" : "sparkline negative-line"} viewBox="0 0 78 34" role="img" aria-label={`${metric.label} 미니 추세`}>
          <polyline points={metric.change_pct >= 0 ? "1,28 10,25 18,27 27,18 37,21 46,13 55,16 65,8 77,10" : "1,8 10,12 18,10 27,18 37,15 46,23 55,20 65,28 77,26"} />
        </svg>
      </article>)}</div>
    </div>)}
  </section>;
}
