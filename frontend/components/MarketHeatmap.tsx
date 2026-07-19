"use client";

import Link from "next/link";
import { useState } from "react";
import type { HeatmapItem } from "@/lib/types";

const sectorOrder = ["기술", "커뮤니케이션", "경기소비재", "금융", "헬스케어", "필수소비재", "에너지", "산업재"];

function heatClass(change: number) {
  if (change >= 2) return "gain-strong";
  if (change > 0) return "gain";
  if (change <= -2) return "loss-strong";
  if (change < 0) return "loss";
  return "flat";
}

export function MarketHeatmap({ items, compact = false }: { items: HeatmapItem[]; compact?: boolean }) {
  const [hovered, setHovered] = useState<HeatmapItem | null>(null);
  const sectors = sectorOrder
    .map(sector => ({ sector, items: items.filter(item => item.sector === sector) }))
    .filter(group => group.items.length);

  return <div className={`sector-map ${compact ? "compact" : "detail"}`} onMouseLeave={() => setHovered(null)}>
    {sectors.map(group => <section className="sector-group" key={group.sector} style={{ flexGrow: group.items.reduce((sum, item) => sum + item.market_cap_weight, 0) }}>
      <h3>{group.sector}</h3>
      <div className="sector-stocks">{group.items.map(item => <Link
        href={`/stocks/${encodeURIComponent(item.symbol)}`}
        key={item.symbol}
        className={`heat-stock ${heatClass(item.change_pct)}`}
        style={{ flexGrow: item.market_cap_weight, flexBasis: compact ? `${Math.max(item.market_cap_weight * 1.8, 22)}%` : `${Math.max(item.market_cap_weight * 1.5, 18)}%` }}
        onMouseEnter={() => setHovered(item)}
        aria-label={`${item.name} ${item.change_pct}%`}
      ><strong>{item.symbol}</strong><span>{item.change_pct > 0 ? "+" : ""}{item.change_pct.toFixed(2)}%</span>{!compact && <small>{item.industry}</small>}</Link>)}</div>
    </section>)}

    {!compact && hovered && <aside className="heat-tooltip" aria-live="polite">
      <div><span>{hovered.sector} · {hovered.industry}</span><b>{hovered.symbol}</b><small>{hovered.name}</small></div>
      <div className="tooltip-price"><strong>${hovered.price.toLocaleString("en-US", { minimumFractionDigits: 2 })}</strong><em className={hovered.change_pct >= 0 ? "up" : "down"}>{hovered.change_pct > 0 ? "+" : ""}{hovered.change_pct.toFixed(2)}%</em></div>
      <div className="tooltip-chart" aria-hidden="true"><i /><i /><i /><i /><i /><i /><i /></div>
      <p>클릭하면 종목 상세 정보를 확인할 수 있습니다.</p>
    </aside>}
  </div>;
}
