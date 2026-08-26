import { getWorkerDashboard } from "@/lib/server/dashboard-data";

export async function GET() {
  try {
    return Response.json(await getWorkerDashboard());
  } catch (error) {
    return Response.json({ detail: error instanceof Error ? error.message : "dashboard unavailable" }, { status: 503 });
  }
}
