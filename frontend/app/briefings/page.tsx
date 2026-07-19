import { DetailPage } from "@/components/DetailPage";
import { Section } from "@/components/Section";
import { getDashboard } from "@/lib/api";
export default async function BriefingsPage() { const data = await getDashboard(); return <DetailPage eyebrow="30 SECOND BRIEFING" title="아침 브리핑" description="간밤 흐름, 국내 변수와 우선 확인 업종을 출처와 함께 설명합니다."><Section title={data.briefing.headline}><p className="prose">{data.briefing.summary}</p><div className="chips">{data.briefing.source_ids.map(id => <span className="chip" key={id}>근거: {id}</span>)}</div></Section><Section title="KCIF 요약"><div className="detail-cards">{data.kcif.map(item => <a href={item.source_url} key={item.id}><span className="topic">{item.topic}</span><h2>{item.title}</h2><p>{item.summary}</p></a>)}</div></Section></DetailPage>; }
