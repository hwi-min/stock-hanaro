import Link from "next/link";
import { DetailPage } from "@/components/DetailPage";
import type { ResearchResponse } from "@/lib/types";
import { getWorkerResearch } from "@/lib/server/research-data";

const API_BASE_URL = process.env.BACKEND_API_BASE_URL
  ?? process.env.NEXT_PUBLIC_API_BASE_URL
  ?? "http://127.0.0.1:8000";

type Params = { category?: string; broker?: string; q?: string };

async function getResearch(params: Params): Promise<ResearchResponse> {
  if (process.env.SUPABASE_URL && (process.env.SUPABASE_SECRET_KEY || process.env.SUPABASE_SERVICE_ROLE_KEY)) {
    return getWorkerResearch({ ...params, limit: 200 });
  }
  const query = new URLSearchParams({ limit: "200" });
  if (params.category) query.set("category", params.category);
  if (params.broker) query.set("broker", params.broker);
  if (params.q) query.set("q", params.q);
  const response = await fetch(`${API_BASE_URL}/api/research?${query}`, { cache: "no-store" });
  if (!response.ok) throw new Error(`Research API returned ${response.status}`);
  return response.json() as Promise<ResearchResponse>;
}

function filterHref(params: Params, changes: Partial<Params>) {
  const next = { ...params, ...changes };
  const query = new URLSearchParams();
  if (next.category) query.set("category", next.category);
  if (next.broker) query.set("broker", next.broker);
  if (next.q) query.set("q", next.q);
  return `/research${query.size ? `?${query}` : ""}`;
}

export default async function ResearchPage({ searchParams }: { searchParams: Promise<Params> }) {
  const params = await searchParams;
  const data = await getResearch(params);
  const today = new Date().toLocaleDateString("sv-SE", { timeZone: "Asia/Seoul" });
  const todayCount = data.items.filter(item => item.published_on === today).length;
  return <DetailPage eyebrow="BROKER RESEARCH" title="증권사 리서치"
    description="증권사별 최신 리포트의 공개 메타데이터를 모아 보여주고 원문 제공처로 연결합니다.">
    <section className="research-stats" aria-label="리서치 현황">
      <div><span>검색 결과</span><strong>{data.items.length}</strong><small>건</small></div>
      <div><span>오늘 발간</span><strong>{todayCount}</strong><small>건</small></div>
      <div><span>제공 증권사</span><strong>{data.facets.brokers.length}</strong><small>곳</small></div>
      <div><span>분류</span><strong>{data.facets.categories.length}</strong><small>개</small></div>
    </section>

    <section className="panel research-panel">
      <form className="research-search" action="/research">
        {params.category && <input type="hidden" name="category" value={params.category} />}
        {params.broker && <input type="hidden" name="broker" value={params.broker} />}
        <input name="q" defaultValue={params.q ?? ""} placeholder="종목명, 제목, 증권사, 애널리스트 검색" />
        <button type="submit">검색</button>
      </form>

      <div className="research-filter-row">
        <b>분류</b><Link className={!params.category ? "active" : ""} href={filterHref(params, { category: undefined })}>전체</Link>
        {data.facets.categories.map(item => <Link className={params.category === item.name ? "active" : ""}
          href={filterHref(params, { category: item.name })} key={item.name}>{item.name}<small>{item.count}</small></Link>)}
      </div>
      <div className="research-filter-row broker-row">
        <b>증권사</b><Link className={!params.broker ? "active" : ""} href={filterHref(params, { broker: undefined })}>전체</Link>
        {data.facets.brokers.map(item => <Link className={params.broker === item.name ? "active" : ""}
          href={filterHref(params, { broker: item.name })} key={item.name}>{item.name}<small>{item.count}</small></Link>)}
      </div>

      <div className="research-list">
        {data.items.map(item => <article key={`${item.source}:${item.source_report_id}`}>
          <div className="research-date"><strong>{item.published_on.slice(5).replace("-", ".")}</strong><span>{item.category}</span></div>
          <div className="research-content">
            <div className="research-badges"><b>{item.broker}</b>{item.stock_code && <Link href={`/stocks/${item.stock_code}`}>{item.stock_name} · {item.stock_code}</Link>}</div>
            <a href={item.source_url} target="_blank" rel="noopener noreferrer"><h2>{item.title}</h2></a>
            <p>{item.analyst || "리서치센터"}{item.opinion && ` · ${item.opinion}`}{item.target_price && ` · 목표가 ${item.target_price.toLocaleString("ko-KR")}원`}</p>
          </div>
          <a className="research-open" href={item.source_url} target="_blank" rel="noopener noreferrer" aria-label={`${item.title} 원문 열기`}>원문 보기 ↗</a>
        </article>)}
        {!data.items.length && <div className="empty-state">조건에 맞는 리서치 자료가 없습니다.</div>}
      </div>
      <p className="research-notice">리포트 저작권은 각 작성 증권사와 원 제공처에 있습니다. 본 서비스는 메타데이터만 제공하며 원문을 저장하거나 재배포하지 않습니다.</p>
    </section>
  </DetailPage>;
}
