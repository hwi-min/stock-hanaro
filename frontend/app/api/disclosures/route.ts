import { getWorkerDisclosures, type DisclosureSort } from "@/lib/server/disclosure-data";

export async function GET(request: Request) {
  const params = new URL(request.url).searchParams;
  return Response.json(await getWorkerDisclosures({
    date: params.get("date") || undefined, reportType: params.get("type") || undefined,
    eventType: params.get("event") || undefined, importance: params.get("importance") || undefined,
    correction: params.get("correction") || undefined, q: params.get("q") || undefined,
    sort: (params.get("sort") || undefined) as DisclosureSort | undefined,
  }));
}
