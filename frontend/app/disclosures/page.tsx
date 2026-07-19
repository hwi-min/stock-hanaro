import { DetailPage } from "@/components/DetailPage";
import { Section } from "@/components/Section";
import { getDashboard } from "@/lib/api";
export const dynamic = "force-dynamic";
import { disclosureUrl } from "@/lib/disclosures";
export default async function DisclosuresPage() { const data = await getDashboard(); return <DetailPage eyebrow="OPEN DART" title="중요 공시" description="중요 유형을 구조화하고 해석은 사실과 분리해 표시합니다."><Section title="오늘의 공시"><div className="detail-list">{data.disclosures.map(item => <a className="disclosure-row" href={disclosureUrl(item)} target="_blank" rel="noopener noreferrer" key={item.id} aria-label={`${item.company} ${item.title} DART 원문 열기`}><b>{item.company}</b><strong>{item.title}</strong><span>{item.importance === "high" ? "중요" : "보통"}</span></a>)}</div></Section></DetailPage>; }
