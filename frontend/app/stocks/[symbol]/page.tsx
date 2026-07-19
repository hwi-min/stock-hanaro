import { notFound } from "next/navigation";
import { DetailPage } from "@/components/DetailPage";
import { Section } from "@/components/Section";
import { StockPriceChart } from "@/components/StockPriceChart";
import { getDashboard } from "@/lib/api";

export default async function StockDetailPage({ params }: { params: Promise<{ symbol: string }> }) {
  const [{ symbol }, data] = await Promise.all([params, getDashboard()]);
  const stock = data.heatmap.find(item => item.symbol === decodeURIComponent(symbol).toUpperCase());
  if (!stock) notFound();
  const positive = stock.change_pct >= 0;
  return <DetailPage eyebrow={`${stock.sector} · ${stock.industry}`} title={`${stock.symbol} · ${stock.name}`} description="KIS 해외주식 데이터를 기반으로 상담 전 확인에 필요한 핵심 시세와 가격 흐름만 제공합니다.">
    <section className="stock-summary">
      <div><span>현재가</span><strong>${stock.price.toLocaleString("en-US", { minimumFractionDigits: 2 })}</strong></div>
      <div><span>전일 대비</span><strong className={positive ? "up" : "down"}>{stock.change_pct > 0 ? "+" : ""}{stock.change_pct.toFixed(2)}%</strong></div>
      <div><span>업종</span><strong>{stock.sector}</strong><small>{stock.industry}</small></div>
      <div><span>데이터 상태</span><strong>정상</strong><small>KIS 기준 시각 표시 예정</small></div>
    </section>
    <Section title="가격 추이"><StockPriceChart positive={positive} /></Section>
    <div className="grid stock-info-grid">
      <Section title="오늘의 핵심"><ul className="stock-points"><li>최근 가격 흐름과 거래량 변화를 함께 확인합니다.</li><li>관련 뉴스·공시가 가격 변화와 연결되는지 확인합니다.</li><li>AI 해석은 사실과 분리해 가능성으로 표시합니다.</li></ul></Section>
      <Section title="연결 정보"><div className="stock-links"><span>관련 뉴스·이슈 <b>3건</b></span><span>최근 공시 <b>1건</b></span><span>데이터 출처 <b>KIS Open API</b></span></div></Section>
    </div>
  </DetailPage>;
}
