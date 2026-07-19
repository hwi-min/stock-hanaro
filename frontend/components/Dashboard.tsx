import Link from "next/link";
import type { Dashboard as DashboardType } from "@/lib/types";
import { MarketHeatmap } from "./MarketHeatmap";
import { Section } from "./Section";

const sentimentLabel = { positive: "긍정", neutral: "중립", negative: "부정" };
const formatScheduleTime = (value: string) => new Intl.DateTimeFormat("ko-KR", { timeZone: "Asia/Seoul", hour: "2-digit", minute: "2-digit", hour12: false }).format(new Date(value));

export function Dashboard({ data }: { data: DashboardType }) {
  const marketRows = [
    { id: "us", label: "US Market", metrics: data.metrics.filter(metric => metric.market === "us") },
    { id: "kr", label: "KR Market", metrics: data.metrics.filter(metric => metric.market === "kr") },
  ] as const;

  return <main className="dashboard">
    <section className="briefing-hero">
      <div><span className="eyebrow">오늘의 30초 브리핑</span><h1>{data.briefing.headline}</h1><p>{data.briefing.summary}</p>
        <div className="chips"><span className="chip stance">위험선호</span>{data.briefing.keywords.map(keyword => <span className="chip" key={keyword}>{keyword}</span>)}</div>
      </div>
      <div className="keyword-box"><span className="eyebrow">오늘의 핵심 키워드</span>{data.briefing.keywords.map((keyword, index) => <div key={keyword}><b>{index + 1}</b>{keyword}</div>)}</div>
    </section>

    <section className="market-board" aria-label="주요 시장 지표">
      {marketRows.map(row => <div className="market-row" key={row.id}>
        <div className="market-label"><span className="market-signal" aria-hidden="true">◉</span><b>{row.label}</b></div>
        <div className="market-tickers">{row.metrics.map(metric => <article key={metric.symbol}>
          <div><span>{metric.label}</span><strong>{metric.value}</strong><em className={metric.change_pct >= 0 ? "up" : "down"}>{metric.change_pct >= 0 ? "+" : ""}{metric.change_pct.toFixed(2)}%</em></div>
          <svg className={metric.change_pct >= 0 ? "sparkline positive-line" : "sparkline negative-line"} viewBox="0 0 78 34" role="img" aria-label={`${metric.label} 미니 추세`}>
            <polyline points={metric.change_pct >= 0 ? "1,28 10,25 18,27 27,18 37,21 46,13 55,16 65,8 77,10" : "1,8 10,12 18,10 27,18 37,15 46,23 55,20 65,28 77,26"} />
          </svg>
        </article>)}</div>
      </div>)}
    </section>

    <div className="grid main-grid">
      <Section title="미국시장 히트맵" href="/markets" className="heatmap-panel"><MarketHeatmap items={data.heatmap} compact /></Section>
      <Section title="오늘의 주요 일정" href="/calendar"><div className="list">{data.schedules.map(item => <div key={item.id}><time>{formatScheduleTime(item.scheduled_at)}</time><b>{item.title}</b><span className={`badge ${item.importance}`}>{item.importance === "high" ? "중요" : item.importance === "medium" ? "보통" : "낮음"}</span></div>)}</div></Section>
      <Section title="오늘의 주요 이슈" href="/issues"><div className="issue-list">{data.issues.map(item => <Link key={item.id} href={`/issues/${item.id}`}><div><b>{item.title}</b><p>{item.summary}</p></div><span className={`sentiment ${item.sentiment}`}>{sentimentLabel[item.sentiment]}</span></Link>)}</div></Section>
    </div>

    <div className="grid lower-grid">
      <Section title="국제금융센터 요약" href="/briefings"><div className="cards">{data.kcif.map(item => <article key={item.id}><span className="topic">{item.topic}</span><h3>{item.title}</h3><p>{item.summary}</p><small>KCIF 원문 기반 요약</small></article>)}</div></Section>
      <Section title="중요 공시" href="/disclosures"><div className="table">{data.disclosures.map(item => <div key={item.id}><b>{item.company}</b><span>{item.title}</span><em className={`badge ${item.importance}`}>{item.importance === "high" ? "중요" : "보통"}</em></div>)}</div></Section>
    </div>

    <Section title="이슈별 뉴스 요약" href="/issues"><div className="cards issue-cards">{data.issues.map(item => <Link href={`/issues/${item.id}`} key={item.id}><span className="topic">{item.category}</span><h3>{item.title}</h3><p>{item.summary}</p><small>관련 기사 {item.article_count}건</small></Link>)}</div></Section>
  </main>;
}
