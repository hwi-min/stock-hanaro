export type RecentStock = { symbol: string; name: string; market: "kr" | "us" };

const KEY = "stock-hanaro:recent-stocks";

export function loadRecentStocks(): RecentStock[] {
  if (typeof window === "undefined") return [];
  try {
    const parsed = JSON.parse(window.localStorage.getItem(KEY) ?? "[]") as RecentStock[];
    return parsed.filter(item => item?.symbol && item?.name).slice(0, 6);
  } catch {
    return [];
  }
}

export function saveRecentStock(stock: RecentStock): RecentStock[] {
  if (typeof window === "undefined") return [];
  const next = [stock, ...loadRecentStocks().filter(item => item.symbol !== stock.symbol)].slice(0, 6);
  window.localStorage.setItem(KEY, JSON.stringify(next));
  return next;
}

export function clearRecentStocks() {
  if (typeof window !== "undefined") window.localStorage.removeItem(KEY);
}
