import { notFound } from "next/navigation";
import { DetailPage } from "@/components/DetailPage";
import { Section } from "@/components/Section";
import { getDashboard } from "@/lib/api";

export default async function IssuePage({ params }: { params: Promise<{ id: string }> }) {
  const [{ id }, data] = await Promise.all([params, getDashboard()]);
  const issue = data.issues.find(item => item.id === id);
  if (!issue) notFound();

  return <DetailPage eyebrow={issue.category} title={issue.title} description={issue.summary}>
    <div className="grid detail-grid">
      <Section title="확인된 핵심 사실"><p className="prose">대표 기사와 여러 출처에서 공통으로 확인되는 내용을 최대 3개로 정리합니다.</p></Section>
      <Section title="국내시장 예상 영향"><p className="prose">관련 산업에 우호적 또는 부정적으로 작용할 가능성을 근거와 함께 표시합니다.</p></Section>
      <Section title="반대 위험 요인"><p className="prose">예상과 다르게 전개될 조건을 함께 제시해 단정적인 해석을 피합니다.</p></Section>
    </div>
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
