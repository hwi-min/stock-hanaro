import Link from "next/link";
import { DetailPage } from "@/components/DetailPage";
import { getWorkerDisclosures, type DisclosureQuery, type DisclosureSort } from "@/lib/server/disclosure-data";

export const dynamic = "force-dynamic";
type Params = { date?: string; type?: string; event?: string; importance?: string; correction?: string; q?: string; sort?: string };

function href(params: Params, changes: Partial<Params>) {
  const next = { ...params, ...changes };
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(next)) if (value) query.set(key, value);
  return `/disclosures${query.size ? `?${query}` : ""}`;
}

const importanceLabel = { high: "중요", medium: "주목", low: "일반" };

function formatCheckedAt(value: string | null) {
  if (!value) return "확인 대기";
  return new Intl.DateTimeFormat("ko-KR", { timeZone: "Asia/Seoul", hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: false }).format(new Date(value));
}

export default async function DisclosuresPage({ searchParams }: { searchParams: Promise<Params> }) {
  const params = await searchParams;
  const query: DisclosureQuery = {
    date: params.date, reportType: params.type, eventType: params.event, importance: params.importance,
    correction: params.correction, q: params.q,
    sort: (["impact", "latest", "company", "type"].includes(params.sort || "") ? params.sort : "impact") as DisclosureSort,
  };
  const data = await getWorkerDisclosures(query);
  const displayDate = data.selectedDate ? data.selectedDate.replaceAll("-", ".") : "수집 대기";
  const refreshText = data.refresh.status === "failed" ? "갱신 지연"
    : data.refresh.status === "disabled" ? "자동 갱신 꺼짐"
    : data.refresh.newCount > 0 ? `새 공시 ${data.refresh.newCount}건 반영`
    : "최신 내역 확인 완료";
  return <DetailPage eyebrow="OPEN DART DISCLOSURE DESK" title="공시 현황"
    description="오늘 어떤 공시가 있었는지 유형별 건수와 시장 영향도를 먼저 확인하고 DART 원문으로 이동합니다.">
    <section className="disclosure-overview" aria-label="공시 요약">
      <div className="disclosure-date"><span>집계 기준일</span><strong>{displayDate}</strong><small>OpenDART 최근 수집일</small></div>
      <div><span>전체 공시</span><strong>{data.summary.total}</strong><small>건</small></div>
      <div><span>중요 공시</span><strong>{data.summary.important}</strong><small>건</small></div>
      <div><span>핵심 이벤트</span><strong>{data.summary.actionable}</strong><small>건</small></div>
      <div><span>정정 공시</span><strong>{data.summary.corrections}</strong><small>건</small></div>
    </section>

    <div className={`disclosure-refresh-status ${data.refresh.status}`}>
      <span><i />OpenDART 기준 · 마지막 확인 {formatCheckedAt(data.refresh.lastSuccessAt)}</span>
      <b>{refreshText}</b><small>장중 3분 단위 공유 캐시</small>
    </div>

    <section className="panel disclosure-panel">
      <div className="disclosure-panel-head">
        <div><span className="eyebrow">DISCLOSURE BREAKDOWN</span><h2>유형별 공시 건수</h2></div>
        <div className="disclosure-date-links">{data.availableDates.slice(0, 5).map((date) =>
          <Link className={data.selectedDate === date ? "active" : ""} href={href(params, { date })} key={date}>{date.slice(5).replace("-", ".")}</Link>)}</div>
      </div>
      <div className="disclosure-type-grid">
        <Link className={!params.type ? "active" : ""} href={href(params, { type: undefined })}><span>전체</span><strong>{data.summary.total}</strong></Link>
        {data.facets.types.map((item) => <Link className={params.type === item.name ? "active" : ""}
          href={href(params, { type: item.name })} key={item.name}><span>{item.label}</span><strong>{item.count}</strong><small>{item.name}</small></Link>)}
      </div>
      <div className="disclosure-event-row">
        <b>핵심 이벤트</b><Link className={!params.event ? "active" : ""} href={href(params, { event: undefined })}>전체</Link>
        {data.facets.events.filter((item) => !item.name.startsWith("TYPE_")).slice(0, 14).map((item) =>
          <Link className={params.event === item.name ? "active" : ""} href={href(params, { event: item.name })} key={item.name}>{item.label}<small>{item.count}</small></Link>)}
      </div>
    </section>

    <section className="panel disclosure-list-panel">
      <form className="disclosure-toolbar" action="/disclosures">
        {params.date && <input type="hidden" name="date" value={params.date} />}
        {params.type && <input type="hidden" name="type" value={params.type} />}
        {params.event && <input type="hidden" name="event" value={params.event} />}
        <input name="q" defaultValue={params.q || ""} placeholder="회사명, 종목코드, 공시명 검색" />
        <select name="importance" defaultValue={params.importance || ""} aria-label="중요도">
          <option value="">전체 중요도</option><option value="high">중요</option><option value="medium">주목</option><option value="low">일반</option>
        </select>
        <select name="correction" defaultValue={params.correction || ""} aria-label="정정공시">
          <option value="">정정 포함</option><option value="exclude">정정 제외</option><option value="only">정정만</option>
        </select>
        <select name="sort" defaultValue={query.sort} aria-label="정렬">
          <option value="impact">중요도순</option><option value="latest">최신순</option><option value="company">회사명순</option><option value="type">유형별</option>
        </select>
        <button type="submit">적용</button>
      </form>
      <div className="disclosure-result-head"><b>{data.items.length}건</b><span>중요도와 이벤트 우선순위는 공시명 기반 규칙 분류입니다.</span></div>
      <div className="disclosure-list">
        {data.items.map((item) => <article key={item.receiptNo}>
          <div className="disclosure-company"><strong>{item.company}</strong>{item.stockCode && <Link href={`/stocks/${item.stockCode}`}>{item.stockCode}</Link>}</div>
          <div className="disclosure-main">
            <div><span className={`disclosure-importance ${item.importance}`}>{importanceLabel[item.importance]}</span><span className="disclosure-event">{item.eventLabel}</span>{item.isCorrection && <span className="correction-tag">정정</span>}</div>
            <a href={item.sourceUrl} target="_blank" rel="noopener noreferrer"><h2>{item.title}</h2></a>
            <p>{item.reportTypeLabel} · 접수번호 {item.receiptNo}</p>
          </div>
          <div className="disclosure-open"><span>{item.receiptDate.slice(5).replace("-", ".")}</span><a href={item.sourceUrl} target="_blank" rel="noopener noreferrer">DART 원문 ↗</a></div>
        </article>)}
        {!data.items.length && <div className="empty-state">선택한 조건에 해당하는 공시가 없습니다.</div>}
      </div>
      <p className="research-notice">공시 분류와 중요도는 빠른 탐색을 위한 보조 정보입니다. 투자 판단 전 반드시 DART 원문과 정정 여부를 확인하세요.</p>
    </section>
  </DetailPage>;
}
