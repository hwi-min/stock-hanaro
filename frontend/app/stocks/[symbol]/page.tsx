import { StockDetailClient } from "@/components/StockDetailClient";
import type { StockDetail } from "@/lib/types";

export default async function StockDetailPage({ params }: { params: Promise<{ symbol: string }> }) {
  const { symbol } = await params;
  const decodedSymbol = decodeURIComponent(symbol).toUpperCase();
  const apiBaseUrl = process.env.BACKEND_API_BASE_URL ?? "http://127.0.0.1:8000";
  let initialStock: StockDetail | null = null;
  try {
    const response = await fetch(`${apiBaseUrl}/api/stocks/${encodeURIComponent(decodedSymbol)}?interval=daily`, {
      cache: "no-store",
    });
    if (response.ok) initialStock = await response.json() as StockDetail;
  } catch {
    // The client request below remains a fallback when server-side loading fails.
  }
  return <StockDetailClient symbol={decodedSymbol} initialStock={initialStock} />;
}
