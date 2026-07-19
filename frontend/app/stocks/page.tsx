import { DetailPage } from "@/components/DetailPage";
import { Section } from "@/components/Section";
export default function StocksPage() { return <DetailPage eyebrow="STOCK SEARCH" title="종목" description="기업명, 종목코드와 별칭으로 연결된 이슈와 공시를 찾습니다."><Section title="종목 검색 준비 중"><p className="prose">관심종목 저장은 MVP 이후 범위이며, M2부터 종목 마스터와 검색 API를 연결합니다.</p></Section></DetailPage>; }
