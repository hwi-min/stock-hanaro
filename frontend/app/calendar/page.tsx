import { DetailPage } from "@/components/DetailPage";
import { Section } from "@/components/Section";
import { getDashboard } from "@/lib/api";

export const dynamic = "force-dynamic";

const sourceLabels = { bls: "미국 노동통계국", bea: "미국 경제분석국", federal_reserve: "미 연방준비제도", bok: "한국은행" };
const importanceLabels = { high: "중요", medium: "보통", low: "낮음" };

export default async function CalendarPage() {
  const data = await getDashboard();
  const schedules = [...data.schedules].sort((a, b) => new Date(a.scheduled_at).getTime() - new Date(b.scheduled_at).getTime());
  return <DetailPage eyebrow="OFFICIAL ECONOMIC CALENDAR" title="주요 경제 일정" description="BLS, BEA, 미 연방준비제도와 한국은행의 공식 발표 일정을 한국시간으로 통합합니다.">
    <div className="calendar-filters" aria-label="일정 필터"><span className="active">전체</span><span>미국</span><span>한국</span><span>중요 일정</span></div>
    <Section title="향후 24시간"><div className="calendar-list">{schedules.map(item => {
      const scheduled = new Date(item.scheduled_at);
      return <article key={item.id}>
        <time><strong>{new Intl.DateTimeFormat("ko-KR", { timeZone: "Asia/Seoul", hour: "2-digit", minute: "2-digit", hour12: false }).format(scheduled)}</strong><small>{new Intl.DateTimeFormat("ko-KR", { timeZone: "Asia/Seoul", month: "2-digit", day: "2-digit" }).format(scheduled)}</small></time>
        <span className={`country-flag ${item.country.toLowerCase()}`}>{item.country}</span>
        <div><small>{item.category} · 출처: {sourceLabels[item.source]}</small><b>{item.title}</b></div>
        <em className={`badge ${item.importance}`}>{importanceLabels[item.importance]}</em>
      </article>;
    })}</div></Section>
    <Section title="데이터 안내"><p className="prose">일정은 매일 05:50에 갱신하고 실패 시 06:10에 한 번 재시도합니다. 공식 원천이 예상치 또는 실제치를 제공하지 않으면 빈 값으로 유지하며 임의 수치를 생성하지 않습니다.</p></Section>
  </DetailPage>;
}
