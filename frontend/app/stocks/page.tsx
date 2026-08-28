import { DetailPage } from "@/components/DetailPage";
import { StocksExplorer } from "@/components/StocksExplorer";

export default function StocksPage() {
  return <DetailPage eyebrow="STOCK DISCOVERY" title="한국·미국 종목 차트" description="종목 목록을 검색한 뒤 선택한 종목만 KIS에서 호출합니다. 조회 결과는 공유 캐시에 저장되어 다음 요청에서 빠르게 최신화됩니다."><StocksExplorer /></DetailPage>;
}
