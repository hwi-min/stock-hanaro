import { DetailPage } from "@/components/DetailPage";
import { MarketHeatmap } from "@/components/MarketHeatmap";
import { MacroMonitor } from "@/components/MacroMonitor";
import { Section } from "@/components/Section";
import { getDashboard } from "@/lib/api";
import { getFredMacroData } from "@/lib/server/fred";

export const dynamic = "force-dynamic";

export default async function MarketsPage() {
  const [data, macro] = await Promise.all([getDashboard(), getFredMacroData().catch(() => null)]);
  return <DetailPage eyebrow="GLOBAL MARKET INTELLIGENCE" title="글로벌 시장" description="미국 금리·물가·달러 흐름과 S&P 500 종목 성과를 한 화면에서 확인합니다.">
    <MacroMonitor data={macro} />
    <Section title="업종별 종목 성과"><MarketHeatmap items={data.heatmap} /></Section>
    <Section title="히트맵 읽는 방법"><div className="heat-guide"><span className="gain-strong">+2% 이상</span><span className="gain">상승</span><span className="flat">보합</span><span className="loss">하락</span><span className="loss-strong">-2% 이하</span><p>크기 기준을 바꿔 기업 규모와 전일 거래 집중도를 비교할 수 있습니다.</p></div></Section>
  </DetailPage>;
}
