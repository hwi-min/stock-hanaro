"use client";

import Link from "next/link";
import { useCallback, useMemo, useState } from "react";
import type { HeatmapItem } from "@/lib/types";

type Rect = { x: number; y: number; width: number; height: number };
type Weighted<T> = { value: T; weight: number };
type Positioned<T> = Weighted<T> & { rect: Rect };
type SizeMode = "marketCap" | "dollarVolume" | "relativeVolume";

const ROOT_RECT: Rect = { x: 0, y: 0, width: 100, height: 100 };

function layoutWeighted<T>(entries: Weighted<T>[], rect: Rect): Positioned<T>[] {
  if (!entries.length) return [];
  if (entries.length === 1) return [{ ...entries[0], rect }];

  const sorted = [...entries].sort((a, b) => b.weight - a.weight);
  const total = sorted.reduce((sum, entry) => sum + entry.weight, 0);
  let splitAt = 1;
  let running = sorted[0].weight;
  for (let index = 1; index < sorted.length; index += 1) {
    if (Math.abs(total / 2 - running) < Math.abs(total / 2 - (running + sorted[index].weight))) break;
    running += sorted[index].weight;
    splitAt = index + 1;
  }

  const first = sorted.slice(0, splitAt);
  const second = sorted.slice(splitAt);
  const ratio = first.reduce((sum, entry) => sum + entry.weight, 0) / total;
  const vertical = rect.width >= rect.height;
  const firstRect = vertical
    ? { ...rect, width: rect.width * ratio }
    : { ...rect, height: rect.height * ratio };
  const secondRect = vertical
    ? { x: rect.x + firstRect.width, y: rect.y, width: rect.width - firstRect.width, height: rect.height }
    : { x: rect.x, y: rect.y + firstRect.height, width: rect.width, height: rect.height - firstRect.height };

  return [...layoutWeighted(first, firstRect), ...layoutWeighted(second, secondRect)];
}

function heatClass(change: number) {
  if (change >= 3) return "gain-max";
  if (change >= 2) return "gain-strong";
  if (change >= 1) return "gain";
  if (change <= -3) return "loss-max";
  if (change <= -2) return "loss-strong";
  if (change <= -1) return "loss";
  return "flat";
}

function positionStyle(rect: Rect) {
  return { left: `${rect.x}%`, top: `${rect.y}%`, width: `${rect.width}%`, height: `${rect.height}%` };
}

export function MarketHeatmap({ items, compact = false }: { items: HeatmapItem[]; compact?: boolean }) {
  const [hovered, setHovered] = useState<HeatmapItem | null>(null);
  const [zoom, setZoom] = useState(1);
  const [sizeMode, setSizeMode] = useState<SizeMode>("marketCap");
  const weightOf = useCallback((item: HeatmapItem) => {
    if (sizeMode === "dollarVolume") return Math.sqrt(Math.max(item.dollar_volume ?? 0, 1));
    if (sizeMode === "relativeVolume") return Math.sqrt(Math.max(item.relative_volume ?? 0, .05));
    return Math.max(item.market_cap_weight, .01);
  }, [sizeMode]);
  const sectors = useMemo(() => {
    const grouped = new Map<string, HeatmapItem[]>();
    for (const item of items) grouped.set(item.sector, [...(grouped.get(item.sector) ?? []), item]);
    return layoutWeighted([...grouped].map(([sector, sectorItems]) => ({
      value: { sector, items: sectorItems },
      weight: sectorItems.reduce((sum, item) => sum + weightOf(item), 0),
    })), ROOT_RECT);
  }, [items, weightOf]);

  return <div className={`heatmap-shell ${compact ? "compact" : "detail"}`}>
    {!compact && <div className="heatmap-toolbar">
      <p><b>시장 전체</b><span>섹터 · 산업군 · 종목</span></p>
      <div className="heatmap-controls"><label>크기 기준<select value={sizeMode} onChange={event => setSizeMode(event.target.value as SizeMode)}><option value="marketCap">지수 비중</option><option value="dollarVolume">거래대금</option><option value="relativeVolume">상대 거래량</option></select></label><button onClick={() => setZoom(value => Math.max(1, value - .25))} disabled={zoom === 1} aria-label="히트맵 축소">−</button><strong>{Math.round(zoom * 100)}%</strong><button onClick={() => setZoom(value => Math.min(2, value + .25))} disabled={zoom === 2} aria-label="히트맵 확대">＋</button></div>
    </div>}
    <div className="heatmap-viewport" onMouseLeave={() => setHovered(null)}>
      <div className="sector-map" style={{ width: `${zoom * 100}%`, height: `${zoom * 100}%` }}>
        {sectors.map(group => {
          const industries = new Map<string, HeatmapItem[]>();
          for (const item of group.value.items) industries.set(item.industry, [...(industries.get(item.industry) ?? []), item]);
          const industryLayout = layoutWeighted([...industries].map(([industry, industryItems]) => ({
            value: { industry, items: industryItems },
            weight: industryItems.reduce((sum, item) => sum + weightOf(item), 0),
          })), ROOT_RECT);
          return <section className="sector-group" key={group.value.sector} style={positionStyle(group.rect)}>
            <h3>{group.value.sector}</h3>
            <div className="industry-map">{industryLayout.map(industry => {
              const stockLayout = layoutWeighted(industry.value.items.map(item => ({ value: item, weight: weightOf(item) })), ROOT_RECT);
              return <section className="industry-group" key={industry.value.industry} style={positionStyle(industry.rect)}>
                <h4>{industry.value.industry}</h4>
                <div className="industry-stocks">{stockLayout.map(({ value: item, rect }) => {
                  const area = rect.width * rect.height;
                  return <Link href={`/stocks/${encodeURIComponent(item.symbol)}`} key={item.symbol}
                    className={`heat-stock ${heatClass(item.change_pct)} ${area < 650 ? "small" : "large"}`}
                    style={positionStyle(rect)} onMouseEnter={() => setHovered(item)}
                    title={`${item.name} · ${item.change_pct > 0 ? "+" : ""}${item.change_pct.toFixed(2)}%`}
                    aria-label={`${item.name} ${item.change_pct}%`}>
                    <strong>{item.symbol}</strong><span>{item.change_pct > 0 ? "+" : ""}{item.change_pct.toFixed(2)}%</span>
                  </Link>;
                })}</div>
              </section>;
            })}</div>
          </section>;
        })}
      </div>
      {hovered && <aside className="heat-tooltip" aria-live="polite">
        <div><span>{hovered.sector} · {hovered.industry}</span><b>{hovered.symbol}</b><small>{hovered.name}</small></div>
        <div className="tooltip-price"><strong>${hovered.price.toLocaleString("en-US", { minimumFractionDigits: 2 })}</strong><em className={hovered.change_pct >= 0 ? "up" : "down"}>{hovered.change_pct > 0 ? "+" : ""}{hovered.change_pct.toFixed(2)}%</em></div>
        <p>{hovered.trading_date ? `${hovered.trading_date} 정규장 종가` : "최근 수집 시세"} · 거래량 {(hovered.volume ?? 0).toLocaleString("en-US")}</p>
      </aside>}
    </div>
    <div className="heatmap-legend" aria-label="등락률 색상 범례">
      <span className="loss-max">-3%</span><span className="loss-strong">-2%</span><span className="loss">-1%</span><span className="flat">0%</span><span className="gain">+1%</span><span className="gain-strong">+2%</span><span className="gain-max">+3%</span>
      <p>사각형 크기는 {sizeMode === "marketCap" ? "S&P 500 지수 비중" : sizeMode === "dollarVolume" ? "종가×거래량" : "20일 평균 대비 거래량"}, 색상은 전일 대비 등락률입니다.</p>
    </div>
  </div>;
}
