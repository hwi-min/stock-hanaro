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

function DataStateBadge({ data, keys }: { data: DashboardType; keys: string[] }) {
  const states = keys.map(key => data.data_status?.[key]).filter(Boolean);
  if (!states.length || states.every(item => item?.state === "live")) return null;
  const unavailable = states.some(item => item?.state === "unavailable");
  const asOf = states.map(item => item?.as_of).filter(Boolean).sort().at(-1);
  const date = asOf ? new Intl.DateTimeFormat("ko-KR", { timeZone: "Asia/Seoul", month: "numeric", day: "numeric", hour: "2-digit", minute: "2-digit", hour12: false }).format(new Date(asOf)) : null;
  return <span className={`dataset-state ${unavailable ? "unavailable" : "delayed"}`}>{unavailable ? "불러오기 실패" : "지연 데이터"}{date ? ` · ${date}` : ""}</span>;
}

export function Dashboard({ data }: { data: DashboardType }) {
  return <main className="dashboard">
    <section className="briefing-hero">
      <DataStateBadge data={data} keys={["market", "issue_summaries", "news"]} />
      <div><span className="eyebrow">오늘의 30초 브리핑</span><h1>{data.briefing.headline}</h1><p>{data.briefing.summary}</p>
        <div className="chips"><span className="chip stance">위험선호</span>{data.briefing.keywords.map(keyword => <span className="chip" key={keyword}>{keyword}</span>)}</div>
      </div>
      <div className="keyword-box"><span className="eyebrow">오늘의 핵심 키워드</span>{data.briefing.keywords.map((keyword, index) => <div key={keyword}><b>{index + 1}</b>{keyword}</div>)}</div>
    </section>

    <div className="dashboard-dataset"><DataStateBadge data={data} keys={["market"]} /><LiveMarketBoard initialMetrics={data.metrics} /></div>

    <div className="grid main-grid">
      <Section title="미국시장 히트맵 · 마지막 정규장 종가 기준" href="/markets" className="heatmap-panel" status={<DataStateBadge data={data} keys={["sp500_constituents", "sp500_snapshots"]} />}><MarketHeatmap items={data.heatmap} compact /></Section>
      <Section title="이번 주 주요 일정" href="/calendar" status={<DataStateBadge data={data} keys={["calendar"]} />}><div className="list home-scroll">{data.schedules.map(item => <div key={item.id}><time>{formatScheduleTime(item.scheduled_at)}</time><b>{item.title}</b><span className={`badge ${item.importance}`}>{item.importance === "high" ? "중요" : item.importance === "medium" ? "보통" : "낮음"}</span></div>)}</div></Section>
      <Section title="오늘의 주요 이슈" href="/issues" status={<DataStateBadge data={data} keys={["issue_summaries", "news"]} />}><div className="issue-list home-scroll">{data.issues.map(item => <Link key={item.id} href={`/issues/${item.id}`}><div><b>{item.title}</b><p>{item.summary}</p></div><span className={`sentiment ${item.sentiment}`}>{sentimentLabel[item.sentiment]}</span></Link>)}</div></Section>
    </div>

    <div className="grid lower-grid">
      <Section title="국제금융센터 요약" href="/briefings" status={<DataStateBadge data={data} keys={["kcif"]} />}><div className="cards home-scroll">{data.kcif.map(item => <article key={item.id}><span className="topic">{item.topic}</span><h3>{item.title}</h3><p>{item.summary}</p><small>KCIF 원문 기반 요약</small></article>)}</div></Section>
      <Section title="중요 공시" href="/disclosures" status={<DataStateBadge data={data} keys={["disclosures"]} />}><div className="table home-scroll">{data.disclosures.map(item => <a className="disclosure-row" href={disclosureUrl(item)} target="_blank" rel="noopener noreferrer" key={item.id} aria-label={`${item.company} ${item.title} DART 원문 열기`}><b>{item.company}</b><span>{item.title}</span><em className={`badge ${item.importance}`}>{item.importance === "high" ? "중요" : "보통"}</em></a>)}</div></Section>
    </div>

    <Section title="이슈별 뉴스 요약" href="/issues" status={<DataStateBadge data={data} keys={["issue_summaries", "news"]} />}><div className="cards issue-cards">{data.issues.map(item => <Link href={`/issues/${item.id}`} key={item.id}><span className="topic">{item.category}</span><h3>{item.title}</h3><p>{item.summary}</p><small>{item.summary_method === "extractive" ? "기사 기반 자동 발췌 · " : ""}관련 기사 {item.article_count}건</small></Link>)}</div></Section>

    <Section title="최신 증권사 리서치" href="/research" className="home-research-panel" status={<DataStateBadge data={data} keys={["research"]} />}><div className="home-research-list home-scroll">{data.research.map(item => <article key={item.id}>
      <time>{item.published_on.slice(5).replace("-", ".")}</time>
      <div><span>{item.category}</span><b>{item.broker}</b>{item.stock_code && <Link href={`/stocks/${item.stock_code}`}>{item.stock_name} · {item.stock_code}</Link>}</div>
      <a href={item.source_url} target="_blank" rel="noopener noreferrer"><strong>{item.title}</strong><small>{item.analyst || "리서치센터"} · 원문 보기 ↗</small></a>
    </article>)}</div></Section>
  </main>;
}
