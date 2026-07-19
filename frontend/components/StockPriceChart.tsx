import type { ChartPoint } from "@/lib/types";

const movingAverage = (values: number[], window: number) => values.map((_, index) => {
  const slice = values.slice(Math.max(0, index - window + 1), index + 1);
  return slice.reduce((sum, value) => sum + value, 0) / slice.length;
});

export function StockPriceChart({ points, positive, interval }: { points: ChartPoint[]; positive: boolean; interval: "daily" | "minute" }) {
  if (!points.length) return <div className="stock-chart empty-chart">표시할 가격 데이터가 없습니다.</div>;
  const visible = points.slice(-100);
  const values = visible.map(point => point.close);
  const lows = visible.map(point => point.low ?? point.close);
  const highs = visible.map(point => point.high ?? point.close);
  const min = Math.min(...lows), max = Math.max(...highs), range = Math.max(max - min, 1);
  const x = (index: number) => 28 + index * (844 / Math.max(visible.length - 1, 1));
  const y = (value: number) => 270 - ((value - min) / range) * 220;
  const line = (series: number[]) => series.map((value, index) => `${x(index)},${y(value)}`).join(" ");
  const ma20 = movingAverage(values, 20), ma50 = movingAverage(values, 50);
  const labels = [visible[0], visible[Math.floor(visible.length / 2)], visible.at(-1)!];
  return <div className="stock-chart" role="img" aria-label={interval === "daily" ? "최근 일봉 가격 차트" : "당일 분봉 가격 차트"}>
    <div className="chart-legend"><span>{interval === "daily" ? "일봉" : "분봉"}</span><i className="price-dot" />종가<i className="ma20-dot" />20선<i className="ma50-dot" />50선</div>
    <svg viewBox="0 0 900 310" preserveAspectRatio="none">
      {[50,105,160,215,270].map(gridY => <line key={gridY} x1="20" x2="880" y1={gridY} y2={gridY} className="grid-line" />)}
      <polyline points={line(ma50)} className="ma-line ma50" />
      <polyline points={line(ma20)} className="ma-line ma20" />
      <polyline points={line(values)} className={`price-line ${positive ? "positive-price" : "negative-price"}`} />
      {visible.map((point, index) => <g key={`${point.time}:${index}`} className={(point.close >= (point.open ?? point.close)) ? "candle-up" : "candle-down"}>
        <line x1={x(index)} x2={x(index)} y1={y(point.high ?? point.close)} y2={y(point.low ?? point.close)} />
        <rect x={x(index) - 2} y={Math.min(y(point.open ?? point.close), y(point.close))} width="4" height={Math.max(2, Math.abs(y(point.open ?? point.close) - y(point.close)))} />
      </g>)}
    </svg>
    <div className="chart-axis">{labels.map((point, index) => <span key={`${point.time}:${index}`}>{interval === "daily" ? `${point.time.slice(4, 6)}.${point.time.slice(6, 8)}` : `${point.time.slice(0, 2)}:${point.time.slice(2, 4)}`}</span>)}</div>
  </div>;
}
