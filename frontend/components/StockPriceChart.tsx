export function StockPriceChart({ positive }: { positive: boolean }) {
  const candles = [62,58,66,54,49,57,61,53,47,45,50,43,38,41,36,33,39,44,48,46,51,56,59,55,61,64,60,66,70,68,73,77,74,79,76,82];
  const points = candles.map((value, index) => `${24 + index * 24},${245 - value * 2.2}`).join(" ");
  const ma20 = candles.map((_, index) => `${24 + index * 24},${138 + Math.sin(index / 5) * 20}`).join(" ");
  const ma50 = candles.map((_, index) => `${24 + index * 24},${170 + Math.sin(index / 8) * 12}`).join(" ");
  return <div className="stock-chart" role="img" aria-label="최근 6개월 일봉 가격 차트">
    <div className="chart-legend"><span>일봉</span><i className="price-dot" />종가<i className="ma20-dot" />20일선<i className="ma50-dot" />50일선</div>
    <svg viewBox="0 0 900 310" preserveAspectRatio="none">
      {[50,100,150,200,250].map(y => <line key={y} x1="20" x2="880" y1={y} y2={y} className="grid-line" />)}
      <polyline points={ma50} className="ma-line ma50" />
      <polyline points={ma20} className="ma-line ma20" />
      <polyline points={points} className={`price-line ${positive ? "positive-price" : "negative-price"}`} />
      {candles.map((value, index) => { const x = 24 + index * 24; const up = index === 0 || value >= candles[index - 1]; return <g key={x} className={up ? "candle-up" : "candle-down"}><line x1={x} x2={x} y1={235-value*2.2} y2={255-value*2.2}/><rect x={x-4} y={up ? 242-value*2.2 : 238-value*2.2} width="8" height="10" /></g>; })}
    </svg>
    <div className="chart-axis"><span>2월</span><span>3월</span><span>4월</span><span>5월</span><span>6월</span><span>7월</span></div>
  </div>;
}
