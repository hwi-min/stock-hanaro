import { DetailPage } from "@/components/DetailPage";
import { Section } from "@/components/Section";
import { getDashboard } from "@/lib/api";
export default async function StatusPage() { const data = await getDashboard(); return <DetailPage eyebrow="OPERATIONS" title="데이터 운영 상태" description="오래된 데이터가 최신처럼 보이지 않도록 소스별 기준 시각과 지연 여부를 표시합니다."><Section title="신선도"><div className="detail-list">{data.freshness.map(item => <div key={item.dataset}><b>{item.label}</b><strong>{new Date(item.as_of).toLocaleString("ko-KR")}</strong><span className={item.stale ? "down" : "up"}>{item.stale ? "지연" : "정상"}</span></div>)}</div></Section></DetailPage>; }
