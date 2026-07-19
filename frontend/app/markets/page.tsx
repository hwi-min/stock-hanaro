import { DetailPage } from "@/components/DetailPage";
import { MarketHeatmap } from "@/components/MarketHeatmap";
import { Section } from "@/components/Section";
import { getDashboard } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function MarketsPage() {
  const data = await getDashboard();
  return <DetailPage eyebrow="US MARKET HEATMAP" title="미국시장 히트맵" description="시가총액 비중과 등락률로 미국 주요 종목의 흐름을 확인합니다. 종목에 마우스를 올리면 핵심 정보가 표시되고, 클릭하면 종목 상세 화면으로 이동합니다.">
    <Section title="업종별 종목 성과"><MarketHeatmap items={data.heatmap} /></Section>
    <Section title="히트맵 읽는 방법"><div className="heat-guide"><span className="gain-strong">+2% 이상</span><span className="gain">상승</span><span className="flat">보합</span><span className="loss">하락</span><span className="loss-strong">-2% 이하</span><p>사각형 크기는 시가총액 비중, 색상은 전일 대비 등락률을 의미합니다.</p></div></Section>
  </DetailPage>;
}
