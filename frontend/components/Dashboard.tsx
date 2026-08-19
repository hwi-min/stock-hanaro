import Link from "next/link";
import type { Dashboard as DashboardType } from "@/lib/types";
import { MarketHeatmap } from "./MarketHeatmap";
import { Section } from "./Section";
import { LiveMarketBoard } from "./LiveMarketBoard";
import { disclosureUrl } from "@/lib/disclosures";

const sentimentLabel = { positive: "긍정", neutral: "중립", negative: "부정" };
const formatScheduleTime = (value: string) => new Intl.DateTimeFormat("ko-KR", {
  timeZone: "Asia/Seoul", month: "numeric", day: "numeric", weekday: "short",
  hour: "2-digit", minute: "2-digit", hour12: false,
}).format(new Date(value));

export function Dashboard({ data }: { data: DashboardType }) {
  return <main className="dashboard">
    <section className="briefing-hero">
      <div><span className="eyebrow">오늘의 30초 브리핑</span><h1>{data.briefing.headline}</h1><p>{data.briefing.summary}</p>
        <div className="chips"><span className="chip stance">위험선호</span>{data.briefing.keywords.map(keyword => <span className="chip" key={keyword}>{keyword}</span>)}</div>
      </div>
      <div className="keyword-box"><span className="eyebrow">오늘의 핵심 키워드</span>{data.briefing.keywords.map((keyword, index) => <div key={keyword}><b>{index + 1}</b>{keyword}</div>)}</div>
    </section>

    <LiveMarketBoard initialMetrics={data.metrics} />

    <div className="grid main-grid">
      <Section title="미국시장 히트맵 · 마지막 정규장 종가 기준" href="/markets" className="heatmap-panel"><MarketHeatmap items={data.heatmap} compact /></Section>
      <Section title="이번 주 주요 일정" href="/calendar"><div className="list">{data.schedules.map(item => <div key={item.id}><time>{formatScheduleTime(item.scheduled_at)}</time><b>{item.title}</b><span className={`badge ${item.importance}`}>{item.importance === "high" ? "중요" : item.importance === "medium" ? "보통" : "낮음"}</span></div>)}</div></Section>
      <Section title="오늘의 주요 이슈" href="/issues"><div className="issue-list">{data.issues.map(item => <Link key={item.id} href={`/issues/${item.id}`}><div><b>{item.title}</b><p>{item.summary}</p></div><span className={`sentiment ${item.sentiment}`}>{sentimentLabel[item.sentiment]}</span></Link>)}</div></Section>
    </div>

    <div className="grid lower-grid">
      <Section title="국제금융센터 요약" href="/briefings"><div className="cards">{data.kcif.map(item => <article key={item.id}><span className="topic">{item.topic}</span><h3>{item.title}</h3><p>{item.summary}</p><small>KCIF 원문 기반 요약</small></article>)}</div></Section>
      <Section title="중요 공시" href="/disclosures"><div className="table">{data.disclosures.map(item => <a className="disclosure-row" href={disclosureUrl(item)} target="_blank" rel="noopener noreferrer" key={item.id} aria-label={`${item.company} ${item.title} DART 원문 열기`}><b>{item.company}</b><span>{item.title}</span><em className={`badge ${item.importance}`}>{item.importance === "high" ? "중요" : "보통"}</em></a>)}</div></Section>
    </div>

    <Section title="이슈별 뉴스 요약" href="/issues"><div className="cards issue-cards">{data.issues.map(item => <Link href={`/issues/${item.id}`} key={item.id}><span className="topic">{item.category}</span><h3>{item.title}</h3><p>{item.summary}</p><small>{item.summary_method === "extractive" ? "기사 기반 자동 발췌 · " : ""}관련 기사 {item.article_count}건</small></Link>)}</div></Section>
  </main>;
}
