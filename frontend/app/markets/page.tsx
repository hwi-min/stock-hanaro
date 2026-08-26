import { DetailPage } from "@/components/DetailPage";
import { MarketHeatmap } from "@/components/MarketHeatmap";
import { Section } from "@/components/Section";
import { getDashboard } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function MarketsPage() {
  const data = await getDashboard();
  return <DetailPage eyebrow="S&P 500 CLOSE HEATMAP" title="미국시장 히트맵" description="S&P 500 전 종목의 마지막 정규장 종가를 지수 비중·거래대금·상대 거래량으로 비교합니다. 종목에 마우스를 올리면 핵심 정보가 표시됩니다.">
    <Section title="업종별 종목 성과"><MarketHeatmap items={data.heatmap} /></Section>
    <Section title="히트맵 읽는 방법"><div className="heat-guide"><span className="gain-strong">+2% 이상</span><span className="gain">상승</span><span className="flat">보합</span><span className="loss">하락</span><span className="loss-strong">-2% 이하</span><p>크기 기준을 바꿔 기업 규모와 전일 거래 집중도를 비교할 수 있습니다.</p></div></Section>
  </DetailPage>;
}
