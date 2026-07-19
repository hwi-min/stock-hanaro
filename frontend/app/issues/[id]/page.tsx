import { notFound } from "next/navigation";
import { DetailPage } from "@/components/DetailPage";
import { Section } from "@/components/Section";
import { getDashboard } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function IssuePage({ params }: { params: Promise<{ id: string }> }) {
  const [{ id }, data] = await Promise.all([params, getDashboard()]);
  const issue = data.issues.find(item => item.id === id);
  if (!issue) notFound();

  const method = issue.summary_method === "extractive" ? "기사 기반 자동 발췌" : issue.summary_method === "ai" ? "AI 출처 기반 요약" : "대표 기사 발췌";
  return <DetailPage eyebrow={issue.category} title={issue.title} description={`${method} · 관련 기사 ${issue.article_count}건`}>
    <Section title={method}><p className="prose">{issue.summary}</p><p className="source-note">새로운 사실이나 시장 전망을 생성하지 않고, 아래 출처 기사에 포함된 문장만 선택했습니다.</p></Section>
    <Section title={`참고한 뉴스 ${issue.articles.length}건`}>
      <div className="source-articles">{issue.articles.map(article => <a href={article.url} target="_blank" rel="noreferrer" key={article.id}>
        <div><span>{article.publisher}</span>{article.is_representative && <em>대표 기사</em>}</div>
        <b>{article.title}</b>
        <time>{new Intl.DateTimeFormat("ko-KR", { timeZone: "Asia/Seoul", dateStyle: "medium", timeStyle: "short" }).format(new Date(article.published_at))}</time>
        <i>원문 보기 ↗</i>
      </a>)}</div>
      <p className="source-note">기사 본문은 저장하거나 재배포하지 않으며, 제목·언론사·게시 시각과 원문 링크만 제공합니다.</p>
    </Section>
  </DetailPage>;
}
