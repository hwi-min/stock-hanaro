import { DetailPage } from "@/components/DetailPage";
import { StocksExplorer } from "@/components/StocksExplorer";

export default function StocksPage() {
  return <DetailPage eyebrow="STOCK DISCOVERY" title="종목 찾기" description="KOSPI·KOSDAQ 전체 보통주를 기업명이나 종목코드로 검색하고 핵심 시세와 차트를 확인합니다."><StocksExplorer /></DetailPage>;
}
