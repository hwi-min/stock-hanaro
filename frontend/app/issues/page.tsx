import Link from "next/link";
import { DetailPage } from "@/components/DetailPage";
import { getDashboard } from "@/lib/api";
export const dynamic = "force-dynamic";

export default async function IssuesPage() { const data = await getDashboard(); return <DetailPage eyebrow="NEWS & ISSUES" title="뉴스·이슈" description="반복 보도를 사건 단위로 묶고 사실, 국내 영향과 반대 위험을 분리합니다."><div className="detail-cards">{data.issues.map(item => <Link href={`/issues/${item.id}`} key={item.id}><span className="topic">{item.category}</span><h2>{item.title}</h2><p>{item.summary}</p><small>관련 기사 {item.article_count}건 · 상세 보기 →</small></Link>)}</div></DetailPage>; }
