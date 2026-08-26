import { supabaseSelect } from "@/lib/server/supabase-rest";

type Row = { symbol: string; name: string; market: string };

export async function GET(request: Request) {
  const term = new URL(request.url).searchParams.get("q")?.trim();
  if (!term || term.length > 50) return Response.json({ detail: "q must be 1-50 characters" }, { status: 400 });
  const safe = term.replace(/[,*()]/g, "");
  const rows = await supabaseSelect<Row>("stock_masters", {
    select: "symbol,name,market", active: "eq.true", or: `(symbol.ilike.*${safe}*,name.ilike.*${safe}*)`, limit: 10,
  });
  return Response.json({ items: rows.map((row) => ({
    type: "stock", id: row.symbol, symbol: row.symbol, name: row.name, market: "kr", label: `${row.name} · ${row.symbol}`,
  })) });
}
