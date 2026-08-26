import type { Dashboard } from "./types";
import { fallbackDashboard } from "./fallback-data";
import { getWorkerDashboard } from "./server/dashboard-data";

const API_BASE_URL = process.env.BACKEND_API_BASE_URL
  ?? process.env.NEXT_PUBLIC_API_BASE_URL
  ?? "http://127.0.0.1:8000";

export async function getDashboard(): Promise<Dashboard> {
  try {
    if (process.env.SUPABASE_URL && (process.env.SUPABASE_SECRET_KEY || process.env.SUPABASE_SERVICE_ROLE_KEY)) return await getWorkerDashboard();
    const response = await fetch(`${API_BASE_URL}/api/dashboard/home`, { cache: "no-store" });
    if (!response.ok) throw new Error(`Dashboard API returned ${response.status}`);
    return response.json() as Promise<Dashboard>;
  } catch (error) {
    if (process.env.ALLOW_DASHBOARD_FALLBACK === "true") return fallbackDashboard;
    const message = error instanceof Error ? error.message : "unknown dashboard error";
    throw new Error(`실제 대시보드 데이터를 불러오지 못했습니다: ${message}`);
  }
}
