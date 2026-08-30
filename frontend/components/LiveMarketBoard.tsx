import type { MarketMetric } from "@/lib/types";

function latestAsOf(metrics: MarketMetric[]): Date | null {
  const timestamps = metrics.map(metric => new Date(metric.as_of).getTime()).filter(Number.isFinite);
  return timestamps.length ? new Date(Math.max(...timestamps)) : null;
}

function parts(value: Date, timeZone: string) {
  const values = new Intl.DateTimeFormat("en-US", {
    timeZone, year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit", hourCycle: "h23",
  }).formatToParts(value);
  return (type: string) => values.find(part => part.type === type)?.value ?? "";
}

function marketTimestamp(market: "us" | "kr", metrics: MarketMetric[]): string {
  const latest = latestAsOf(metrics);
  if (!latest) return "기준시각 확인 중";
  const value = parts(latest, market === "us" ? "America/New_York" : "Asia/Seoul");
  const date = `${value("year")}-${value("month")}-${value("day")}`;
  return market === "us" ? `${date} 종가` : `${date} KST ${value("hour")}:${value("minute")}`;
}

export function LiveMarketBoard({ initialMetrics }: { initialMetrics: MarketMetric[] }) {
  const usMetrics = initialMetrics.filter(metric => metric.market === "us");
  const krMetrics = initialMetrics.filter(metric => metric.market === "kr");
  const rows = [
    { id: "us" as const, label: "US Market", metrics: usMetrics },
    { id: "kr" as const, label: "KR Market", metrics: krMetrics },
  ];

  return <section className="market-board" aria-label="주요 시장 지표">
    {rows.map(row => <div className="market-row" key={row.id}>
      <div className="market-label"><span className="market-signal" aria-hidden="true">●</span><div><b>{row.label}</b><small>{marketTimestamp(row.id, row.metrics)}</small></div></div>
      <div className="market-tickers">{row.metrics.map(metric => <article key={metric.symbol}>
        <div><span>{metric.label}</span><strong>{metric.value}</strong><em className={metric.change_pct >= 0 ? "up" : "down"}>{metric.change_pct >= 0 ? "+" : ""}{metric.change_pct.toFixed(2)}%</em></div>
        <svg className={metric.change_pct >= 0 ? "sparkline positive-line" : "sparkline negative-line"} viewBox="0 0 78 34" role="img" aria-label={`${metric.label} 미니 추세`}>
          <polyline points={metric.change_pct >= 0 ? "1,28 10,25 18,27 27,18 37,21 46,13 55,16 65,8 77,10" : "1,8 10,12 18,10 27,18 37,15 46,23 55,20 65,28 77,26"} />
        </svg>
      </article>)}</div>
    </div>)}
  </section>;
}
