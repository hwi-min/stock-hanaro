"use client";

import { useEffect, useRef, useState, type PointerEvent, type ReactNode } from "react";
import type { MacroData, MacroMetric, MacroPoint, MacroSeries } from "@/lib/server/fred";

const labels = ["Sep", "Nov", "Jan", "Mar", "May", "Jul", "Aug"];
const points = (values: number[]) => values.map((value, index) => ({ label: labels[index], value }));
const metric = (id: string, label: string, value: string, comparison: string, direction: MacroMetric["direction"] = "up"): MacroMetric => ({ id, fred: id, label, value, comparison, direction, observationDate: "2026-08-27" });
const SAMPLE: MacroData = {
  source: "sample", asOf: "2026-08-27", summary: "미 장기금리는 높은 수준을 유지하고 있으며, 근원물가 둔화가 정체된 가운데 달러 강세가 이어지는 환경입니다.",
  bond: { metrics: [metric("DGS2", "US 2Y", "4.24%", "전 거래일 대비 +2bp"), metric("DGS10", "US 10Y", "4.70%", "전 거래일 대비 +4bp"), metric("DGS30", "US 30Y", "5.23%", "전 거래일 대비 +5bp"), metric("T10Y2Y", "10Y-2Y Spread", "+46bp", "전 거래일 대비 +2bp")], series: [
    { name: "2Y", color: "#118565", points: points([4.86, 4.55, 4.22, 3.98, 4.08, 4.18, 4.24]) }, { name: "10Y", color: "#172521", points: points([4.12, 4.28, 4.42, 4.36, 4.51, 4.63, 4.70]) }, { name: "30Y", color: "#b26a3d", points: points([4.28, 4.48, 4.67, 4.72, 4.93, 5.10, 5.23]) },
  ], curve: ["1M", "3M", "6M", "1Y", "2Y", "3Y", "5Y", "7Y", "10Y", "20Y", "30Y"].map((label, index) => ({ label, value: [4.36, 4.32, 4.22, 4.08, 4.24, 4.31, 4.45, 4.57, 4.70, 5.02, 5.23][index], observationDate: "2026-08-27" })), signal: "장기금리 상승 · Curve Steepening" },
  inflation: { metrics: [metric("CPIAUCSL", "CPI YoY", "2.7%", "직전 발표 2.6% 대비 +0.1%p"), metric("CPILFESL", "Core CPI YoY", "3.1%", "직전 발표 3.0% 대비 +0.1%p"), metric("PCEPILFE", "Core PCE YoY", "2.8%", "직전 발표와 동일", "flat"), metric("T10YIE", "10Y Breakeven", "2.32%", "전 거래일 대비 +1bp")], series: [
    { name: "CPI", color: "#118565", points: points([3.7, 3.3, 3.1, 3.0, 2.8, 2.6, 2.7]) }, { name: "Core CPI", color: "#172521", points: points([4.1, 3.9, 3.7, 3.5, 3.3, 3.0, 3.1]) }, { name: "Core PCE", color: "#b26a3d", points: points([3.5, 3.3, 3.1, 2.9, 2.8, 2.8, 2.8]) },
  ], signal: "STICKY · 근원물가 둔화 속도가 정체되고 있음" },
  fx: { metrics: [metric("DTWEXBGS", "Broad Dollar", "121.4", "전 관측일 대비 +0.3%"), metric("DEXKOUS", "USD/KRW", "1,385.2", "전 관측일 대비 +6.8원"), metric("DEXJPUS", "USD/JPY", "148.3", "전 관측일 대비 +0.7엔"), metric("DEXUSEU", "EUR/USD", "1.0800", "전 관측일 대비 -0.4%", "down")], broad: points([115, 116, 115, 117, 118, 119, 121.4]), krw: points([1324, 1338, 1328, 1350, 1362, 1378, 1385]), signal: "STRONG · 달러 강세가 원화 약세 압력으로 연결" },
  fed: { metrics: [metric("WALCL", "Total Assets", "$6.62T", "연준 총자산", "down"), metric("WALCL-WOW", "전주 대비", "−$8.4B", "직전 발표 대비", "down"), metric("WALCL-3M", "3개월 대비", "−$71.2B", "13주 전 대비", "down"), metric("WALCL-1Y", "1년 대비", "−$284.5B", "52주 전 대비", "down")], series: [{ label: "2007-08-01", value: 870000 }, { label: "2009-01-01", value: 2200000 }, { label: "2014-01-01", value: 4100000 }, { label: "2019-01-01", value: 3800000 }, { label: "2020-06-01", value: 7100000 }, { label: "2022-04-01", value: 8950000 }, { label: "2024-01-01", value: 7700000 }, { label: "2026-08-26", value: 6620000 }], signal: "CONTRACTING · 연준 총자산이 3개월 전보다 감소한 QT 환경" },
};

function dateLabel(value: string) { const date = new Date(`${value}T00:00:00Z`); return Number.isNaN(date.getTime()) ? value : `${date.getUTCMonth() + 1}/${date.getUTCDate()}`; }
function LineChart({ series }: { series: MacroSeries[] }) {
  const [activeIndex, setActiveIndex] = useState<number | null>(null);
  const [tooltipLeft, setTooltipLeft] = useState(0);
  const values = series.flatMap(item => item.points.map(point => point.value));
  const min = Math.min(...values) - .15, max = Math.max(...values) + .15;
  const y = (value: number) => 18 + (max - value) / Math.max(.01, max - min) * 170;
  const axis = [...new Set(series.flatMap(item => item.points.map(point => point.label)))].sort();
  const timestamps = axis.map(label => Date.parse(`${label}T00:00:00Z`));
  const firstTime = timestamps[0] ?? 0, lastTime = timestamps.at(-1) ?? firstTime + 1;
  const xForDate = (label: string) => 42 + (Date.parse(`${label}T00:00:00Z`) - firstTime) / Math.max(1, lastTime - firstTime) * 630;
  const selectPoint = (event: PointerEvent<SVGSVGElement>) => {
    const matrix = event.currentTarget.getScreenCTM();
    if (!matrix || axis.length === 0) return;
    const svgPoint = event.currentTarget.createSVGPoint();
    svgPoint.x = event.clientX; svgPoint.y = event.clientY;
    const svgX = svgPoint.matrixTransform(matrix.inverse()).x;
    const nextIndex = axis.reduce((best, label, index) => Math.abs(xForDate(label) - svgX) < Math.abs(xForDate(axis[best]) - svgX) ? index : best, 0);
    const target = event.currentTarget.createSVGPoint(); target.x = xForDate(axis[nextIndex]); target.y = 0;
    setTooltipLeft(target.matrixTransform(matrix).x - event.currentTarget.getBoundingClientRect().left);
    setActiveIndex(nextIndex);
  };
  const activeDate = activeIndex === null ? "" : axis[activeIndex] ?? "";
  return <div className="macro-chart"><div className="macro-legend">{series.map(item => <span key={item.name}><i style={{ background: item.color }} />{item.name}</span>)}</div><svg viewBox="0 0 720 230" role="img" aria-label={`${series.map(item => item.name).join(", ")} 추이`} onPointerMove={selectPoint} onPointerDown={selectPoint} onPointerLeave={() => setActiveIndex(null)}>
    {[0, 1, 2, 3].map(step => { const value = max - (max - min) * step / 3, py = y(value); return <g key={step}><line x1="42" x2="672" y1={py} y2={py} /><text x="4" y={py + 4}>{value.toFixed(1)}%</text></g>; })}
    {series.map(item => <polyline key={item.name} points={item.points.map(point => `${xForDate(point.label)},${y(point.value)}`).join(" ")} style={{ stroke: item.color }} />)}
    {activeIndex !== null && <g className="macro-hover"><line x1={xForDate(activeDate)} x2={xForDate(activeDate)} y1="18" y2="188" />{series.map(item => { const point = item.points.find(candidate => candidate.label === activeDate); return point && <circle key={item.name} cx={xForDate(point.label)} cy={y(point.value)} r="5" style={{ fill: item.color }} />; })}</g>}
    {axis.map((label, index) => index % Math.max(1, Math.ceil(axis.length / 7)) === 0 && <text key={`${label}-${index}`} x={xForDate(label)} y="218" textAnchor="middle">{dateLabel(label)}</text>)}
  </svg>{activeIndex !== null && <div className={`macro-tooltip ${activeIndex > axis.length / 2 ? "align-left" : ""}`} style={{ left: tooltipLeft }}><strong>{activeDate}</strong>{series.map(item => { const point = item.points.find(candidate => candidate.label === activeDate); return point && <div key={item.name}><span><i style={{ background: item.color }} />{item.name}</span><b>{point.value.toFixed(2)}%</b></div>; })}</div>}</div>;
}
function MetricCard({ item }: { item: MacroMetric }) { return <article className="macro-metric"><div><span>{item.label}</span><small>{item.fred}</small></div><strong>{item.value}</strong><em className={item.direction}>{item.direction === "up" ? "↑" : item.direction === "down" ? "↓" : "→"}</em><p>{item.comparison}</p><time>{item.observationDate} 관측</time></article>; }
function GuideDetails({ children }: { children: ReactNode }) {
  const detailsRef = useRef<HTMLDetailsElement>(null);
  useEffect(() => {
    const closeOutside = (event: globalThis.PointerEvent) => {
      const details = detailsRef.current;
      if (details?.open && !details.contains(event.target as Node)) details.open = false;
    };
    document.addEventListener("pointerdown", closeOutside);
    return () => document.removeEventListener("pointerdown", closeOutside);
  }, []);
  return <details ref={detailsRef}><summary>데이터 기준 및 업데이트 안내</summary>{children}</details>;
}
function BlockTitle({ number, title, description }: { number: string; title: string; description: string }) { const guide = number === "01" ? <BondDataGuide /> : number === "02" ? <InflationDataGuide /> : number === "03" ? <FxDataGuide /> : number === "04" ? <FedDataGuide /> : null; return <><header className="macro-block-title"><b>{number}</b><div><h2>{title}</h2><p>{description}</p></div></header>{guide}</>; }
function BondDataGuide() {
  return <aside className="bond-data-guide" aria-label="미국 국채 금리 데이터 안내">
    <div><strong>FRED 공식 데이터 · 미국 영업일 기준 일간 갱신</strong><span>각 카드의 관측일은 해당 금리가 나타내는 시장 기준일입니다.</span></div>
    <GuideDetails>
      <div className="bond-data-guide-body">
        <p>FRED는 세인트루이스 연방준비은행이 운영하는 경제 데이터 플랫폼입니다. 주말과 미국 공휴일에는 새로운 관측값이 없으며 게시 시각은 달라질 수 있습니다.</p>
        <dl>
          <div><dt>US 2Y · 10Y · 30Y</dt><dd>미 연준 H.15의 Constant Maturity 금리입니다. 미국 영업일마다 산출되며 FRED에는 통상 관측일의 다음 영업일에 반영됩니다.</dd></div>
          <div><dt>10Y–2Y Spread</dt><dd>미국 10년물 금리에서 2년물 금리를 뺀 수익률곡선 지표입니다. 미 재무부 금리를 기반으로 세인트루이스 연은이 산출하며 미국 영업일마다 갱신됩니다.</dd></div>
        </dl>
        <small>Stock Hanaro 반영: 페이지 요청 시 FRED 조회 · 최대 1시간 캐시 후 재확인<br />출처: FRED · Federal Reserve H.15 · Federal Reserve Bank of St. Louis</small>
      </div>
    </GuideDetails>
  </aside>;
}
function InflationDataGuide() {
  return <aside className="bond-data-guide" aria-label="미국 물가 데이터 안내">
    <div><strong>FRED 공식 데이터 · 물가지수 월간 / 기대인플레이션 일간 갱신</strong><span>월간 관측일은 발표일이 아니라 해당 지표가 나타내는 기준월입니다.</span></div>
    <GuideDetails><div className="bond-data-guide-body">
      <p>CPI와 Core CPI, Core PCE는 FRED의 계절조정 원지수를 받아 Stock Hanaro가 전년 동월 대비 상승률(YoY)을 직접 계산합니다.</p>
      <dl>
        <div><dt>CPI · Core CPI</dt><dd>미 노동통계국(BLS)의 월간 소비자물가지수입니다. 최신 지수를 12개월 전 지수와 비교해 YoY를 계산합니다.</dd></div>
        <div><dt>Core PCE</dt><dd>미 경제분석국(BEA)의 월간 근원 개인소비지출 물가지수입니다. 같은 방식으로 YoY를 계산합니다.</dd></div>
        <div><dt>10Y Breakeven</dt><dd>10년 명목 국채금리와 물가연동국채 실질금리의 차이로 계산된 시장 기대인플레이션이며 미국 영업일마다 갱신됩니다.</dd></div>
      </dl>
      <small>Stock Hanaro 반영: 페이지 요청 시 FRED 조회 · 최대 1시간 캐시 후 재확인<br />출처: FRED · BLS · BEA · Federal Reserve Bank of St. Louis</small>
    </div></GuideDetails>
  </aside>;
}
function FxDataGuide() {
  return <aside className="bond-data-guide" aria-label="미국 달러 및 환율 데이터 안내">
    <div><strong>FRED 공식 데이터 · 연준 H.10 일간 관측</strong><span>실시간 환율이 아니며 FRED의 공식 관측·게시 일정에 따라 반영됩니다.</span></div>
    <GuideDetails><div className="bond-data-guide-body">
      <p>네 지표 모두 미 연준 이사회의 H.10 Foreign Exchange Rates를 FRED에서 제공합니다. 시리즈 빈도는 일간이지만 주말·미국 공휴일에는 관측값이 없고 게시가 묶여 반영될 수 있습니다.</p>
      <dl>
        <div><dt>Broad Dollar</dt><dd>미국의 주요 교역상대국 통화를 무역 비중으로 가중한 명목 달러 지수입니다. 값이 오르면 광범위한 달러 강세를 뜻합니다.</dd></div>
        <div><dt>USD/KRW · USD/JPY</dt><dd>뉴욕 기준 공식 관측 환율로 1달러당 원화·엔화 값입니다. 실시간 서울·도쿄 외환시세와 차이가 날 수 있습니다.</dd></div>
        <div><dt>EUR/USD</dt><dd>1유로당 미국 달러 값입니다. 다른 두 환율과 표시 방향이 반대이므로 하락은 유로 약세·달러 강세를 뜻합니다.</dd></div>
      </dl>
      <small>Stock Hanaro 반영: 페이지 요청 시 FRED 조회 · 최대 1시간 캐시 후 재확인<br />출처: FRED · Federal Reserve H.10 Foreign Exchange Rates</small>
    </div></GuideDetails>
  </aside>;
}
function FedDataGuide() {
  return <aside className="bond-data-guide" aria-label="연준 총자산 데이터 안내">
    <div><strong>FRED 공식 데이터 · 매주 수요일 기준</strong><span>연준 H.4.1에서 통상 미국 목요일에 발표하는 주간 총자산입니다.</span></div>
    <GuideDetails><div className="bond-data-guide-body">
      <p>WALCL은 연방준비은행 연결대차대조표의 총자산에서 내부 연결 제거분을 반영한 주간 지표입니다. 관측일은 매주 수요일이며 발표·FRED 반영은 통상 그다음 미국 영업일입니다.</p>
      <dl>
        <div><dt>Total Assets</dt><dd>FRED 원자료 단위는 백만 달러입니다. 화면의 총자산은 조 달러(T), 증감액은 십억 달러(B)로 변환해 표시합니다.</dd></div>
        <div><dt>기간별 증감</dt><dd>전주·13주 전·52주 전 관측값과 최신 관측값의 차이이며 각각 주간·약 3개월·약 1년 변화를 나타냅니다.</dd></div>
      </dl>
      <small>Stock Hanaro 반영: 페이지 요청 시 FRED 조회 · 최대 1시간 캐시 후 재확인<br />출처: FRED WALCL · Federal Reserve H.4.1</small>
    </div></GuideDetails>
  </aside>;
}
function YieldCurve({ data }: { data: MacroPoint[] }) { const [active, setActive] = useState<number | null>(null); const values = data.map(point => point.value); const rawMin = Math.min(...values), rawMax = Math.max(...values); const padding = Math.max(.12, (rawMax - rawMin) * .18); const min = Math.floor((rawMin - padding) * 4) / 4, max = Math.ceil((rawMax + padding) * 4) / 4; const x = (index: number) => 52 + index * 616 / Math.max(1, data.length - 1); const y = (value: number) => 20 + (max - value) / Math.max(.01, max - min) * 145; const coords = data.map((item, index) => ({ x: x(index), y: y(item.value) })); const smoothPath = coords.reduce((path, point, index) => { if (index === 0) return `M ${point.x} ${point.y}`; const previous = coords[index - 1], before = coords[index - 2] ?? previous, after = coords[index + 1] ?? point; const c1x = previous.x + (point.x - before.x) / 6, c1y = previous.y + (point.y - before.y) / 6, c2x = point.x - (after.x - previous.x) / 6, c2y = point.y - (after.y - previous.y) / 6; return `${path} C ${c1x} ${c1y}, ${c2x} ${c2y}, ${point.x} ${point.y}`; }, ""); const select = (event: PointerEvent<SVGSVGElement>) => { const matrix = event.currentTarget.getScreenCTM(); if (!matrix) return; const cursor = event.currentTarget.createSVGPoint(); cursor.x = event.clientX; cursor.y = event.clientY; const svgX = cursor.matrixTransform(matrix.inverse()).x; setActive(data.reduce((best, _, index) => Math.abs(x(index) - svgX) < Math.abs(x(best) - svgX) ? index : best, 0)); }; const point = active === null ? undefined : data[active], curveDate = data[0]?.observationDate; return <div className="yield-curve"><div className="yield-chart"><svg viewBox="0 0 720 215" role="img" aria-label={`미국 국채 수익률곡선 공통 기준일 ${curveDate}`} onPointerMove={select} onPointerDown={select} onPointerLeave={() => setActive(null)}>{[0, 1, 2, 3].map(step => { const value = max - (max - min) * step / 3, py = y(value); return <g key={step}><line x1="52" x2="668" y1={py} y2={py} /><text x="5" y={py + 4}>{value.toFixed(2)}%</text></g>; })}<path className="yield-area" d={`${smoothPath} L 668 165 L 52 165 Z`} /><path className="yield-line" d={smoothPath} />{data.map((item, index) => <g key={item.label}><circle cx={x(index)} cy={y(item.value)} r={active === index ? 5 : 3.5} /><text x={x(index)} y="198" textAnchor="middle">{item.label}</text></g>)}{point && <line className="yield-crosshair" x1={x(active!)} x2={x(active!)} y1="20" y2="165" />}</svg>{point && <div className={`yield-tooltip ${active! > data.length / 2 ? "align-left" : ""}`} style={{ left: `${x(active!) / 720 * 100}%` }}><strong>{point.label} Treasury</strong><b>{point.value.toFixed(2)}%</b><span>공통 기준일 {point.observationDate}</span></div>}</div></div>; }
function MiniChart({ title, data }: { title: string; data: MacroPoint[] }) { const [activeIndex, setActiveIndex] = useState<number | null>(null); const values = data.map(item => item.value), min = Math.min(...values), max = Math.max(...values); const coords = values.map((value, index) => `${index * 100 / Math.max(1, values.length - 1)},${90 - (value - min) / Math.max(1, max - min) * 70}`).join(" "); const change = values.length > 1 ? (values.at(-1)! / values[0] - 1) * 100 : 0; const selectPoint = (event: PointerEvent<SVGSVGElement>) => { const bounds = event.currentTarget.getBoundingClientRect(); setActiveIndex(Math.max(0, Math.min(data.length - 1, Math.round((event.clientX - bounds.left) / bounds.width * Math.max(1, data.length - 1))))); }; const point = activeIndex === null ? undefined : data[activeIndex]; const pointChange = point && values[0] ? (point.value / values[0] - 1) * 100 : 0; return <div className="fx-mini"><header><div><span>{title}</span><small>{dateLabel(data[0]?.label ?? "")} → {dateLabel(data.at(-1)?.label ?? "")}</small></div><strong>{change > 0 ? "+" : ""}{change.toFixed(1)}%</strong></header><div className="fx-chart-wrap"><svg viewBox="0 0 100 100" preserveAspectRatio="none" onPointerMove={selectPoint} onPointerDown={selectPoint} onPointerLeave={() => setActiveIndex(null)}><polygon points={`0,100 ${coords} 100,100`} /><polyline points={coords} />{point && <g className="fx-hover"><line x1={activeIndex! * 100 / Math.max(1, data.length - 1)} x2={activeIndex! * 100 / Math.max(1, data.length - 1)} y1="10" y2="100" /><circle cx={activeIndex! * 100 / Math.max(1, data.length - 1)} cy={90 - (point.value - min) / Math.max(1, max - min) * 70} r="2.5" /></g>}</svg>{point && <div className={`fx-tooltip ${activeIndex! > data.length / 2 ? "align-left" : ""}`} style={{ left: `${activeIndex! * 100 / Math.max(1, data.length - 1)}%` }}><strong>{point.label}</strong><b>{point.value.toLocaleString(undefined, { maximumFractionDigits: 4 })}</b><span>기간 시작 대비 {pointChange >= 0 ? "+" : ""}{pointChange.toFixed(2)}%</span></div>}</div></div>; }

type FedRange = "3M" | "6M" | "YTD" | "1Y" | "ALL";
function FedBalanceChart({ data }: { data: MacroPoint[] }) {
  const [range, setRange] = useState<FedRange>("ALL"), [active, setActive] = useState<number | null>(null), [tooltipLeft, setTooltipLeft] = useState(0);
  const lastDate = new Date(`${data.at(-1)?.label}T00:00:00Z`), cutoff = new Date(lastDate);
  if (range === "3M") cutoff.setUTCMonth(cutoff.getUTCMonth() - 3); else if (range === "6M") cutoff.setUTCMonth(cutoff.getUTCMonth() - 6); else if (range === "1Y") cutoff.setUTCFullYear(cutoff.getUTCFullYear() - 1); else if (range === "YTD") cutoff.setUTCMonth(0, 1); else cutoff.setUTCFullYear(1900);
  const visible = data.filter(point => new Date(`${point.label}T00:00:00Z`) >= cutoff), values = visible.map(point => point.value);
  const min = Math.floor(Math.min(...values) / 500000) * 500000, max = Math.ceil(Math.max(...values) / 500000) * 500000;
  const time = (point: MacroPoint) => Date.parse(`${point.label}T00:00:00Z`), first = time(visible[0]), last = time(visible.at(-1)!);
  const x = (point: MacroPoint) => 70 + (time(point) - first) / Math.max(1, last - first) * 1000, y = (value: number) => 22 + (max - value) / Math.max(1, max - min) * 255;
  const coords = visible.map(point => `${x(point)},${y(point.value)}`).join(" ");
  const select = (event: PointerEvent<SVGSVGElement>) => { const matrix = event.currentTarget.getScreenCTM(); if (!matrix || !visible.length) return; const cursor = event.currentTarget.createSVGPoint(); cursor.x = event.clientX; cursor.y = event.clientY; const svgX = cursor.matrixTransform(matrix.inverse()).x; const index = visible.reduce((best, point, candidate) => Math.abs(x(point) - svgX) < Math.abs(x(visible[best]) - svgX) ? candidate : best, 0); const target = event.currentTarget.createSVGPoint(); target.x = x(visible[index]); target.y = 0; setTooltipLeft(target.matrixTransform(matrix).x - event.currentTarget.getBoundingClientRect().left); setActive(index); };
  const point = active === null ? undefined : visible[active], prior = active && point ? visible[active - 1] : undefined, weeklyChange = point && prior ? (point.value - prior.value) / 1000 : undefined;
  const allValues = data.map(item => item.value), allMin = Math.min(...allValues), allMax = Math.max(...allValues), allCoords = data.map((item, index) => `${index * 1100 / Math.max(1, data.length - 1)},${54 - (item.value - allMin) / Math.max(1, allMax - allMin) * 42}`).join(" ");
  const selectedStart = data.findIndex(item => item.label === visible[0]?.label) / Math.max(1, data.length - 1) * 100;
  const yearly = visible.filter((item, index) => index === 0 || item.label.slice(0, 4) !== visible[index - 1].label.slice(0, 4)), yearStep = Math.max(1, Math.ceil(yearly.length / 8));
  const yearTicks = yearly.filter((_, index) => index % yearStep === 0 || index === yearly.length - 1);
  return <div className="fed-chart"><div className="fed-toolbar"><div><b>Zoom</b>{(["3M", "6M", "YTD", "1Y", "ALL"] as FedRange[]).map(item => <button key={item} className={range === item ? "active" : ""} onClick={() => { setRange(item); setActive(null); }}>{item}</button>)}</div><p><span>From</span> {visible[0]?.label}<i /> <span>To</span> {visible.at(-1)?.label}</p></div><div className="fed-main-chart"><svg viewBox="0 0 1140 330" role="img" aria-label="연준 총자산 변동 추이" onPointerMove={select} onPointerDown={select} onPointerLeave={() => setActive(null)}>{[0, 1, 2, 3].map(step => { const value = max - (max - min) * step / 3, py = y(value); return <g key={step}><line x1="70" x2="1070" y1={py} y2={py} /><text x="12" y={py + 4}>${(value / 1_000_000).toFixed(1)}T</text></g>; })}<polyline points={coords} />{point && <g className="fed-hover"><line x1={x(point)} x2={x(point)} y1="22" y2="277" /><circle cx={x(point)} cy={y(point.value)} r="5" /></g>}{yearTicks.map(item => <g className="fed-year-tick" key={item.label}><line x1={x(item)} x2={x(item)} y1="277" y2="284" /><text x={x(item)} y="310" textAnchor="middle">{item.label.slice(0, 4)}</text></g>)}</svg>{point && <div className={`fed-tooltip ${active! > visible.length / 2 ? "align-left" : ""}`} style={{ left: tooltipLeft }}><strong>Week of {point.label}</strong><b>Total Assets: ${(point.value / 1_000_000).toFixed(3)}T</b>{weeklyChange !== undefined && <span>전주 대비 {weeklyChange >= 0 ? "+" : "−"}${Math.abs(weeklyChange).toFixed(1)}B</span>}<small>단위: 조 달러 · FRED WALCL</small></div>}</div><div className="fed-navigator"><svg viewBox="0 0 1100 62" preserveAspectRatio="none"><polygon points={`0,62 ${allCoords} 1100,62`} /><polyline points={allCoords} /></svg><div className="fed-selection" style={{ left: `${selectedStart}%`, width: `${100 - selectedStart}%` }} /></div></div>;
}

export function MacroMonitor({ data = SAMPLE }: { data?: MacroData | null }) {
  if (data === null) return <section className="macro-unavailable"><span>US MACRO MONITOR</span><h2>FRED 데이터를 불러올 수 없습니다</h2><p>API 호출에 실패했고 저장된 마지막 정상 스냅샷도 없습니다. 임의의 샘플 데이터는 표시하지 않습니다.</p></section>;
  const headline = [data.bond.metrics[1], data.inflation.metrics[0], data.fx.metrics[0], data.fx.metrics[1]];
  const sourceLabel = data.source === "fred" ? `LIVE DATA · FRED · 최신 관측 ${data.asOf}` : data.source === "stale" ? `지연 데이터 · 마지막 정상 데이터 기준일 ${data.asOf}` : "SAMPLE DATA · 개발용 데이터";
  const bondDates = data.bond.series.flatMap(item => item.points.map(point => point.label)).sort();
  const bondStartDate = bondDates[0] ?? "-", bondEndDate = bondDates.at(-1) ?? "-", curveDate = data.bond.curve[0]?.observationDate ?? "-";
  return <div className="macro-monitor">
    <section className="macro-overview"><div className="macro-summary"><span>US MACRO MONITOR</span><h1>금리·물가·달러로 읽는 미국 시장</h1><p>{data.summary}</p><small className={data.source === "stale" ? "stale" : ""}>{sourceLabel}</small></div><div className="macro-headline-metrics">{headline.map(item => <MetricCard key={item.id} item={item} />)}</div></section>
    <section className="macro-block"><BlockTitle number="01" title="BOND" description="미국 금리와 수익률곡선" /><div className="macro-metrics four">{data.bond.metrics.map(item => <MetricCard key={item.id} item={item} />)}</div><div className="macro-visual-grid"><div><div className="macro-chart-heading"><h3>금리 추이 <small>최근 1년</small></h3><strong>표시 기간 {bondStartDate} → {bondEndDate}</strong></div><LineChart series={data.bond.series} /></div><div className="yield-curve-wrap"><div className="macro-chart-heading"><h3>Current Yield Curve</h3><strong>공통 기준일 {curveDate}</strong></div><YieldCurve data={data.bond.curve} /></div></div><div className="macro-signal"><span>Bond</span><strong>{data.bond.signal}</strong><i>판정</i></div></section>
    <section className="macro-block"><BlockTitle number="02" title="INFLATION" description="물가가 다시 오르는가" /><div className="macro-metrics four">{data.inflation.metrics.map(item => <MetricCard key={item.id} item={item} />)}</div><div className="macro-wide-chart"><h3>주요 물가지표 YoY <small>최근 3년</small></h3><LineChart series={data.inflation.series} /></div><div className="macro-signal"><span>Inflation</span><strong>{data.inflation.signal}</strong><i>판정</i></div></section>
    <section className="macro-block"><BlockTitle number="03" title="FX" description="달러 방향과 원화 영향" /><div className="macro-metrics four">{data.fx.metrics.map(item => <MetricCard key={item.id} item={item} />)}</div><div className="fx-mini-grid"><MiniChart title="Broad Dollar Index" data={data.fx.broad} /><MiniChart title="USD/KRW" data={data.fx.krw} /></div><div className="macro-signal"><span>Dollar</span><strong>{data.fx.signal}</strong><i>판정</i></div></section>
    <section className="macro-block"><BlockTitle number="04" title="FED BALANCE SHEET" description="연방준비제도 총자산 변동 추이" /><div className="macro-metrics four fed-metrics">{data.fed.metrics.map(item => <MetricCard key={item.id} item={item} />)}</div><div className="fed-chart-panel"><h3>Total Assets of the Federal Reserve <small>주간 · FRED WALCL</small></h3><FedBalanceChart data={data.fed.series} /></div><div className="macro-signal"><span>Fed Liquidity</span><strong>{data.fed.signal}</strong><i>판정</i></div></section>
  </div>;
}
