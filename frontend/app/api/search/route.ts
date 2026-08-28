import { supabaseSelect } from "@/lib/server/supabase-rest";

type Row = { symbol: string; name: string; market: string };
type UsRow = { symbol: string; name: string; exchange: string };
type SearchItem = { type: "stock"; id: string; symbol: string; name: string; market: "kr" | "us"; exchange: string; label: string };

export async function GET(request: Request) {
  const term = new URL(request.url).searchParams.get("q")?.trim();
  if (!term || term.length > 50) return Response.json({ detail: "q must be 1-50 characters" }, { status: 400 });
  const safe = term.replace(/[,*()]/g, "");
  const [krRows, usRows] = await Promise.all([
    supabaseSelect<Row>("stock_masters", { select: "symbol,name,market", active: "eq.true", or: `(symbol.ilike.*${safe}*,name.ilike.*${safe}*)`, limit: 8 }),
    supabaseSelect<UsRow>("sp500_constituents", { select: "symbol,name,exchange", active: "eq.true", or: `(symbol.ilike.*${safe}*,name.ilike.*${safe}*)`, limit: 8 }),
  ]);
  const items: SearchItem[] = [
    ...krRows.map(row => ({ type: "stock" as const, id: row.symbol, symbol: row.symbol, name: row.name, market: "kr" as const, exchange: row.market, label: `${row.name} · ${row.symbol}` })),
    ...usRows.map(row => ({ type: "stock" as const, id: row.symbol, symbol: row.symbol, name: row.name, market: "us" as const, exchange: row.exchange, label: `${row.name} · ${row.symbol}` })),
  ];
  const ticker = safe.toUpperCase();
  if (/^[A-Z][A-Z0-9.-]{0,9}$/.test(ticker) && !items.some(item => item.market === "us" && item.id === ticker)) items.push({ type: "stock", id: ticker, symbol: ticker, name: `${ticker} 직접 조회`, market: "us", exchange: "AUTO", label: `${ticker} · 미국 거래소 자동 탐색` });
  return Response.json({ items: items.slice(0, 12) });
}
