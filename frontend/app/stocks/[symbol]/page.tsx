import { StockDetailClient } from "@/components/StockDetailClient";
import type { StockDetail } from "@/lib/types";
import { getWorkerStockDetail } from "@/lib/server/kis";

export default async function StockDetailPage({ params, searchParams }: { params: Promise<{ symbol: string }>; searchParams: Promise<{ market?: string }> }) {
  const { symbol } = await params;
  const { market: requestedMarket } = await searchParams;
  const market = requestedMarket === "us" || requestedMarket === "kr" ? requestedMarket : undefined;
  const decodedSymbol = decodeURIComponent(symbol).toUpperCase();
  const apiBaseUrl = process.env.BACKEND_API_BASE_URL ?? "http://127.0.0.1:8000";
  let initialStock: StockDetail | null = null;
  try {
    if (process.env.SUPABASE_URL && (process.env.SUPABASE_SECRET_KEY || process.env.SUPABASE_SERVICE_ROLE_KEY)) {
      initialStock = await getWorkerStockDetail(decodedSymbol, "daily", market);
    } else {
      const response = await fetch(`${apiBaseUrl}/api/stocks/${encodeURIComponent(decodedSymbol)}?interval=daily`, { cache: "no-store" });
      if (response.ok) initialStock = await response.json() as StockDetail;
    }
  } catch {
    // The client request below remains a fallback when server-side loading fails.
  }
  return <StockDetailClient symbol={decodedSymbol} market={market} initialStock={initialStock} />;
}
