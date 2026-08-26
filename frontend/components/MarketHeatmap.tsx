"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useRef, useState, type MouseEvent as ReactMouseEvent } from "react";
import type { HeatmapItem } from "@/lib/types";

type Rect = { x: number; y: number; width: number; height: number };
type Weighted<T> = { value: T; weight: number };
type Positioned<T> = Weighted<T> & { rect: Rect };
type SizeMode = "marketCap" | "dollarVolume" | "relativeVolume";

const ROOT_RECT: Rect = { x: 0, y: 0, width: 100, height: 100 };
const MIN_ZOOM = 1;
const MAX_ZOOM = 3;
const ZOOM_STEP = .25;
const TOOLTIP_WIDTH = 340;
const TOOLTIP_HEIGHT = 190;
const TOOLTIP_GAP = 14;

function layoutWeighted<T>(entries: Weighted<T>[], rect: Rect, aspectRatio = 1): Positioned<T>[] {
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
  // Rect coordinates are percentages, so compare their rendered dimensions.
  // Without the viewport ratio a wide heatmap is laid out as a square and every
  // resulting tile is stretched horizontally by CSS.
  const vertical = rect.width * aspectRatio >= rect.height;
  const firstRect = vertical
    ? { ...rect, width: rect.width * ratio }
    : { ...rect, height: rect.height * ratio };
  const secondRect = vertical
    ? { x: rect.x + firstRect.width, y: rect.y, width: rect.width - firstRect.width, height: rect.height }
    : { x: rect.x, y: rect.y + firstRect.height, width: rect.width, height: rect.height - firstRect.height };

  return [...layoutWeighted(first, firstRect, aspectRatio), ...layoutWeighted(second, secondRect, aspectRatio)];
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
  const [tooltipPosition, setTooltipPosition] = useState({ x: 0, y: 0 });
  const initialZoom = compact ? 1 : 1.5;
  const [zoom, setZoom] = useState(initialZoom);
  const zoomRef = useRef(initialZoom);
  const [sizeMode, setSizeMode] = useState<SizeMode>("marketCap");
  const viewportRef = useRef<HTMLDivElement>(null);
  const [viewportAspect, setViewportAspect] = useState(16 / 9);
  useEffect(() => {
    const viewport = viewportRef.current;
    if (!viewport) return;
    const updateAspect = () => {
      const { width, height } = viewport.getBoundingClientRect();
      if (width > 0 && height > 0) setViewportAspect(width / height);
    };
    updateAspect();
    const observer = new ResizeObserver(updateAspect);
    observer.observe(viewport);
    return () => observer.disconnect();
  }, []);
  useEffect(() => {
    const viewport = viewportRef.current;
    if (!viewport || compact) return;
    const handleWheel = (event: WheelEvent) => {
      event.preventDefault();
      const previous = zoomRef.current;
      const next = Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, previous + (event.deltaY < 0 ? ZOOM_STEP : -ZOOM_STEP)));
      if (next === previous) return;
      const bounds = viewport.getBoundingClientRect();
      const localX = event.clientX - bounds.left;
      const localY = event.clientY - bounds.top;
      const contentX = viewport.scrollLeft + localX;
      const contentY = viewport.scrollTop + localY;
      zoomRef.current = next;
      setZoom(next);
      requestAnimationFrame(() => {
        const scale = next / previous;
        viewport.scrollLeft = contentX * scale - localX;
        viewport.scrollTop = contentY * scale - localY;
      });
    };
    viewport.addEventListener("wheel", handleWheel, { passive: false });
    return () => viewport.removeEventListener("wheel", handleWheel);
  }, [compact]);
  const changeZoom = useCallback((next: number) => {
    const value = Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, next));
    zoomRef.current = value;
    setZoom(value);
  }, []);
  const showTooltip = useCallback((item: HeatmapItem, event: ReactMouseEvent<HTMLElement>) => {
    const right = event.clientX + TOOLTIP_GAP;
    const x = right + TOOLTIP_WIDTH <= window.innerWidth - 12
      ? right
      : Math.max(12, event.clientX - TOOLTIP_WIDTH - TOOLTIP_GAP);
    const y = Math.min(
      Math.max(12, event.clientY - 42),
      Math.max(12, window.innerHeight - TOOLTIP_HEIGHT - 12),
    );
    setTooltipPosition({ x, y });
    setHovered(item);
  }, []);
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
    })), ROOT_RECT, viewportAspect);
  }, [items, viewportAspect, weightOf]);

  return <div className={`heatmap-shell ${compact ? "compact" : "detail"}`}>
    {!compact && <div className="heatmap-toolbar">
      <p><b>시장 전체</b><span>섹터 · 산업군 · 종목</span></p>
      <div className="heatmap-controls"><label>크기 기준<select value={sizeMode} onChange={event => setSizeMode(event.target.value as SizeMode)}><option value="marketCap">지수 비중</option><option value="dollarVolume">거래대금</option><option value="relativeVolume">상대 거래량</option></select></label><button onClick={() => changeZoom(zoom - ZOOM_STEP)} disabled={zoom === MIN_ZOOM} aria-label="히트맵 축소">−</button><strong title="히트맵 위에서 마우스 휠로 확대·축소">{Math.round(zoom * 100)}%</strong><button onClick={() => changeZoom(zoom + ZOOM_STEP)} disabled={zoom === MAX_ZOOM} aria-label="히트맵 확대">＋</button></div>
    </div>}
    <div ref={viewportRef} className="heatmap-viewport" onMouseLeave={() => setHovered(null)}>
      <div className="sector-map" style={{ width: `${zoom * 100}%`, height: `${zoom * 100}%` }}>
        {sectors.map(group => {
          const industries = new Map<string, HeatmapItem[]>();
          for (const item of group.value.items) industries.set(item.industry, [...(industries.get(item.industry) ?? []), item]);
          const industryLayout = layoutWeighted([...industries].map(([industry, industryItems]) => ({
            value: { industry, items: industryItems },
            weight: industryItems.reduce((sum, item) => sum + weightOf(item), 0),
          })), ROOT_RECT, viewportAspect * group.rect.width / Math.max(group.rect.height, .01));
          return <section className="sector-group" key={group.value.sector} style={positionStyle(group.rect)}>
            <h3>{group.value.sector}</h3>
            <div className="industry-map">{industryLayout.map(industry => {
              const groupAspect = viewportAspect * group.rect.width / Math.max(group.rect.height, .01);
              const industryAspect = groupAspect * industry.rect.width / Math.max(industry.rect.height, .01);
              const stockLayout = layoutWeighted(industry.value.items.map(item => ({ value: item, weight: weightOf(item) })), ROOT_RECT, industryAspect);
              return <section className="industry-group" key={industry.value.industry} style={positionStyle(industry.rect)}>
                <h4>{industry.value.industry}</h4>
                <div className="industry-stocks">{stockLayout.map(({ value: item, rect }) => {
                  const area = rect.width * rect.height;
                  return <Link href={`/stocks/${encodeURIComponent(item.symbol)}`} key={item.symbol}
                    className={`heat-stock ${heatClass(item.change_pct)} ${area < 650 ? "small" : "large"}`}
                    style={positionStyle(rect)} onMouseEnter={event => showTooltip(item, event)}
                    aria-label={`${item.name} ${item.change_pct}%`}>
                    <strong>{item.symbol}</strong><span>{item.change_pct > 0 ? "+" : ""}{item.change_pct.toFixed(2)}%</span>
                  </Link>;
                })}</div>
              </section>;
            })}</div>
          </section>;
        })}
      </div>
      {hovered && <aside className="heat-tooltip" style={{ left: tooltipPosition.x, top: tooltipPosition.y }} aria-live="polite">
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
