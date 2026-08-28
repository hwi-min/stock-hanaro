import type { StockInterval } from "@/lib/types";
import { getWorkerStockDetail } from "@/lib/server/kis";

const intervals = new Set<StockInterval>(["daily", "weekly", "monthly", "minute"]);

export async function GET(request: Request, context: RouteContext<"/api/stocks/[symbol]">) {
  const { symbol } = await context.params;
  const requested = new URL(request.url).searchParams.get("interval") as StockInterval | null;
  const requestedMarket = new URL(request.url).searchParams.get("market");
  const market = requestedMarket === "us" || requestedMarket === "kr" ? requestedMarket : undefined;
  const interval = requested && intervals.has(requested) ? requested : "daily";
  if (interval === "minute") return Response.json({ detail: "minute chart is not enabled" }, { status: 400 });
  try {
    const result = await getWorkerStockDetail(decodeURIComponent(symbol), interval, market);
    return result ? Response.json(result) : Response.json({ detail: "stock not found" }, { status: 404 });
  } catch (error) {
    return Response.json({ detail: error instanceof Error ? error.message : "stock unavailable" }, { status: 503 });
  }
}
