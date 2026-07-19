import type { Dashboard } from "./types";
import { fallbackDashboard } from "./fallback-data";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export async function getDashboard(): Promise<Dashboard> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/dashboard/home`, { next: { revalidate: 60 } });
    if (!response.ok) throw new Error(`Dashboard API returned ${response.status}`);
    return response.json() as Promise<Dashboard>;
  } catch {
    return fallbackDashboard;
  }
}
