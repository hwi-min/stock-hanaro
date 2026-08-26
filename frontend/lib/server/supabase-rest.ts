import "server-only";

type QueryValue = string | number | boolean | undefined | null;

function config() {
  const url = process.env.SUPABASE_URL;
  const key = process.env.SUPABASE_SECRET_KEY ?? process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!url || !key) throw new Error("SUPABASE_URL and SUPABASE_SECRET_KEY are required");
  return { url: url.replace(/\/$/, ""), key };
}

function headers(key: string): Record<string, string> {
  return key.startsWith("sb_secret_")
    ? { apikey: key }
    : { apikey: key, Authorization: `Bearer ${key}` };
}

export async function supabaseSelect<T>(
  table: string,
  query: Record<string, QueryValue> = {},
): Promise<T[]> {
  const { url, key } = config();
  const params = new URLSearchParams();
  for (const [name, value] of Object.entries(query)) {
    if (value !== undefined && value !== null && value !== "") params.set(name, String(value));
  }
  const response = await fetch(`${url}/rest/v1/${table}?${params}`, {
    headers: headers(key),
    cache: "no-store",
  });
  if (!response.ok) throw new Error(`Supabase ${table} query failed (${response.status}): ${await response.text()}`);
  return response.json() as Promise<T[]>;
}

export async function supabaseUpsert<T extends Record<string, unknown>>(
  table: string,
  value: T,
  onConflict?: string,
): Promise<void> {
  const { url, key } = config();
  const suffix = onConflict ? `?on_conflict=${encodeURIComponent(onConflict)}` : "";
  const response = await fetch(`${url}/rest/v1/${table}${suffix}`, {
    method: "POST",
    headers: {
      ...headers(key),
      "Content-Type": "application/json",
      Prefer: "resolution=merge-duplicates,return=minimal",
    },
    body: JSON.stringify(value),
  });
  if (!response.ok) throw new Error(`Supabase ${table} upsert failed (${response.status}): ${await response.text()}`);
}

export function numeric(value: unknown): number | null {
  if (value === null || value === undefined || value === "") return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}
