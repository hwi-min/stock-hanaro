"use client";

import { useState, type MouseEvent } from "react";
import type { ChartPoint, StockInterval } from "@/lib/types";

const intervalLabel = (interval: StockInterval) => interval === "daily" ? "일봉" : interval === "weekly" ? "주봉" : interval === "monthly" ? "월봉" : "분봉";

export function StockPriceChart({ points, interval, currency, market }: { points: ChartPoint[]; interval: StockInterval; currency: "KRW" | "USD"; market: "kr" | "us" }) {
  const [hovered, setHovered] = useState<number | null>(null);
  if (!points.length) return <div className="stock-chart empty-chart">표시할 가격 데이터가 없습니다.</div>;
  const visible = points.slice(-80);
  const lows = visible.map(point => point.low ?? point.close);
  const highs = visible.map(point => point.high ?? point.close);
  const volumes = visible.map(point => point.volume ?? 0);
  const min = Math.min(...lows), max = Math.max(...highs), range = Math.max(max - min, 1);
  const maxVolume = Math.max(...volumes, 1);
  const left = 26, right = 840, priceTop = 20, priceBottom = 220, volumeTop = 240, volumeBottom = 292;
  const step = (right - left) / Math.max(visible.length, 1);
  const candleWidth = Math.max(2, Math.min(9, step * 0.62));
  const x = (index: number) => left + step * index + step / 2;
  const y = (value: number) => priceBottom - ((value - min) / range) * (priceBottom - priceTop);
  const volumeY = (value: number) => volumeBottom - (value / maxVolume) * (volumeBottom - volumeTop);
  const labels = [visible[0], visible[Math.floor(visible.length / 2)], visible.at(-1)!];
  const active = hovered == null ? null : visible[hovered];
  const previous = hovered == null || hovered === 0 ? null : visible[hovered - 1];
  const activeChange = active && previous ? active.close - previous.close : null;
  const activeChangePct = activeChange != null && previous?.close ? activeChange / previous.close * 100 : null;
  const money = new Intl.NumberFormat(currency === "KRW" ? "ko-KR" : "en-US", { maximumFractionDigits: currency === "KRW" ? 0 : 2 });
  const formatDate = (time: string) => interval === "minute" ? `${time.slice(0, 2)}:${time.slice(2, 4)}` : `${time.slice(0, 4)}.${time.slice(4, 6)}.${time.slice(6, 8)}`;
  const kstParts = new Intl.DateTimeFormat("en-US", { timeZone: "Asia/Seoul", year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit", hourCycle: "h23" }).formatToParts(new Date());
  const kst = (type: string) => kstParts.find(part => part.type === type)?.value ?? "0";
  const kstDate = `${kst("year")}${kst("month")}${kst("day")}`;
  const kstMinutes = Number(kst("hour")) * 60 + Number(kst("minute"));
  const closeLabel = active && market === "kr" && interval === "daily" && active.time === kstDate && kstMinutes >= 9 * 60 && kstMinutes < 15 * 60 + 30 ? "현재가" : "종가";
  const move = (event: MouseEvent<SVGSVGElement>) => {
    const bounds = event.currentTarget.getBoundingClientRect();
    const viewX = ((event.clientX - bounds.left) / bounds.width) * 900;
    setHovered(Math.max(0, Math.min(visible.length - 1, Math.floor((viewX - left) / step))));
  };

  return <div className="stock-chart" role="img" aria-label={`최근 ${intervalLabel(interval)} 캔들 및 거래량 차트`}>
    <div className="chart-legend"><span>{intervalLabel(interval)}</span><i className="up-candle-dot" />상승<i className="down-candle-dot" />하락<i className="volume-dot" />거래량</div>
    <div className="chart-canvas">
      <svg viewBox="0 0 900 310" preserveAspectRatio="none" onMouseMove={move} onMouseLeave={() => setHovered(null)}>
        {[priceTop, 70, 120, 170, priceBottom, volumeBottom].map(gridY => <line key={gridY} x1={left} x2={right} y1={gridY} y2={gridY} className="grid-line" />)}
        {visible.map((point, index) => {
          const open = point.open ?? point.close;
          const up = point.close >= open;
          return <g key={`${point.time}:${index}`} className={up ? "candle-up" : "candle-down"}>
            <line x1={x(index)} x2={x(index)} y1={y(point.high ?? point.close)} y2={y(point.low ?? point.close)} />
            <rect x={x(index) - candleWidth / 2} y={Math.min(y(open), y(point.close))} width={candleWidth} height={Math.max(1.5, Math.abs(y(open) - y(point.close)))} />
            <rect className="volume-bar" x={x(index) - candleWidth / 2} y={volumeY(point.volume ?? 0)} width={candleWidth} height={volumeBottom - volumeY(point.volume ?? 0)} />
          </g>;
        })}
        {hovered != null && <g className="chart-crosshair"><line x1={x(hovered)} x2={x(hovered)} y1={priceTop} y2={volumeBottom} /><circle cx={x(hovered)} cy={y(visible[hovered].close)} r="3.5" /></g>}
      </svg>
      {active && <div className={`chart-tooltip ${hovered != null && hovered > visible.length * .66 ? "align-left" : ""}`} style={{ left: `${(x(hovered!) / 900) * 100}%` }}>
        <strong>{formatDate(active.time)}</strong>
        <dl>
          <dt>시가</dt><dd>{money.format(active.open ?? active.close)}</dd>
          <dt>고가</dt><dd>{money.format(active.high ?? active.close)}</dd>
          <dt>저가</dt><dd>{money.format(active.low ?? active.close)}</dd>
          <dt>{closeLabel}</dt><dd>{money.format(active.close)}</dd>
          <dt>전 봉 대비</dt><dd>{activeChange == null ? "-" : `${activeChange >= 0 ? "+" : ""}${money.format(activeChange)}`}</dd>
          <dt>등락률</dt><dd>{activeChangePct == null ? "-" : `${activeChangePct >= 0 ? "+" : ""}${activeChangePct.toFixed(2)}%`}</dd>
          <dt>거래량</dt><dd>{active.volume == null ? "-" : active.volume.toLocaleString()}</dd>
        </dl>
      </div>}
    </div>
    <div className="chart-axis">{labels.map((point, index) => <span key={`${point.time}:${index}`}>{formatDate(point.time)}</span>)}</div>
  </div>;
}
