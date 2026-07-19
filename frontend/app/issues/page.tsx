import Link from "next/link";
import { DetailPage } from "@/components/DetailPage";
import { getDashboard } from "@/lib/api";
export const dynamic = "force-dynamic";

export default async function IssuesPage() { const data = await getDashboard(); return <DetailPage eyebrow="NEWS & ISSUES" title="뉴스·이슈" description="실제 수집 기사를 사건 단위로 묶고 참고한 원문을 함께 제공합니다."><div className="detail-cards">{data.issues.map(item => <Link href={`/issues/${item.id}`} key={item.id}><span className="topic">{item.category}</span><h2>{item.title}</h2><p>{item.summary}</p><small>{item.summary_method === "extractive" ? "기사 기반 자동 발췌 · " : item.summary_method === "ai" ? "AI 출처 기반 요약 · " : "대표 기사 발췌 · "}관련 기사 {item.article_count}건 · 상세 보기 →</small></Link>)}</div></DetailPage>; }
