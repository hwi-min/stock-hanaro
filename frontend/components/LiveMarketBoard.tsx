import type { MarketMetric } from "@/lib/types";

export function LiveMarketBoard({ initialMetrics }: { initialMetrics: MarketMetric[] }) {
  const rows = [
    { id: "us", label: "US Market", note: "최근 정규장 종가", metrics: initialMetrics.filter(metric => metric.market === "us") },
    { id: "kr", label: "KR Market", note: "KIS 기준 · 최근 시세", metrics: initialMetrics.filter(metric => metric.market === "kr") },
  ];

  return <section className="market-board" aria-label="주요 시장 지표">
    {rows.map(row => <div className="market-row" key={row.id}>
      <div className="market-label"><span className="market-signal" aria-hidden="true">●</span><div><b>{row.label}</b><small>{row.note}</small></div></div>
      <div className="market-tickers">{row.metrics.map(metric => <article key={metric.symbol}>
        <div><span>{metric.label}</span><strong>{metric.value}</strong><em className={metric.change_pct >= 0 ? "up" : "down"}>{metric.change_pct >= 0 ? "+" : ""}{metric.change_pct.toFixed(2)}%</em></div>
        <svg className={metric.change_pct >= 0 ? "sparkline positive-line" : "sparkline negative-line"} viewBox="0 0 78 34" role="img" aria-label={`${metric.label} 미니 추세`}>
          <polyline points={metric.change_pct >= 0 ? "1,28 10,25 18,27 27,18 37,21 46,13 55,16 65,8 77,10" : "1,8 10,12 18,10 27,18 37,15 46,23 55,20 65,28 77,26"} />
        </svg>
      </article>)}</div>
    </div>)}
  </section>;
}
