import { StockDetailClient } from "@/components/StockDetailClient";

export default async function StockDetailPage({ params }: { params: Promise<{ symbol: string }> }) {
  const { symbol } = await params;
  return <StockDetailClient symbol={decodeURIComponent(symbol).toUpperCase()} />;
}
