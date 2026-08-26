import { getWorkerResearch } from "@/lib/server/research-data";

export async function GET(request: Request) {
  const params = new URL(request.url).searchParams;
  return Response.json(await getWorkerResearch({
    category: params.get("category") || undefined, broker: params.get("broker") || undefined,
    stock_code: params.get("stock_code") || undefined, q: params.get("q") || undefined,
    limit: Number(params.get("limit") || 100),
  }));
}
