"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { clearRecentStocks, loadRecentStocks, saveRecentStock, type RecentStock } from "@/lib/recent-stocks";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "/backend-api";
type SearchResult = { type: "stock" | "issue"; id: string; symbol?: string; name: string; market: "kr" | "us" | null; label: string };

const featured: RecentStock[] = [
  { symbol: "005930", name: "삼성전자", market: "kr" },
  { symbol: "000660", name: "SK하이닉스", market: "kr" },
  { symbol: "035420", name: "NAVER", market: "kr" },
  { symbol: "005380", name: "현대차", market: "kr" },
  { symbol: "051910", name: "LG화학", market: "kr" },
  { symbol: "373220", name: "LG에너지솔루션", market: "kr" },
];

export function StocksExplorer() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [recent, setRecent] = useState<RecentStock[]>([]);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    const loadTimer = window.setTimeout(() => setRecent(loadRecentStocks()), 0);
    return () => window.clearTimeout(loadTimer);
  }, []);
  useEffect(() => {
    if (timer.current) clearTimeout(timer.current);
    const term = query.trim();
    if (!term) return;
    timer.current = setTimeout(async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/api/search?q=${encodeURIComponent(term)}`, { cache: "no-store" });
        const data = response.ok ? await response.json() as { items: SearchResult[] } : { items: [] };
        setResults(data.items.filter(item => item.type === "stock"));
      } catch {
        setResults([]);
      } finally {
        setLoading(false); setSearched(true);
      }
    }, 180);
    return () => { if (timer.current) clearTimeout(timer.current); };
  }, [query]);

  const updateQuery = (value: string) => {
    const term = value.trim();
    setQuery(value); setLoading(Boolean(term)); setSearched(false);
    if (!term) setResults([]);
  };

  const remember = (stock: RecentStock) => setRecent(saveRecentStock(stock));
  return <>
    <section className="stock-search-panel">
      <label htmlFor="stock-page-search">국내 종목 검색</label>
      <div><input id="stock-page-search" autoComplete="off" autoFocus value={query}
        onChange={event => updateQuery(event.currentTarget.value)} placeholder="기업명 또는 6자리 종목코드 입력" />
        <span>{loading ? "검색 중" : "KOSPI · KOSDAQ 보통주"}</span></div>
      {query.trim() && <div className="stock-search-results" aria-live="polite">
        {results.map(item => <Link href={`/stocks/${encodeURIComponent(item.id)}`} key={item.id}
          onClick={() => remember({ symbol: item.id, name: item.name, market: item.market === "us" ? "us" : "kr" })}>
          <div><strong>{item.name}</strong><small>{item.id}</small></div><span>{item.market === "kr" ? "국내" : "미국"}</span><i>상세 보기 →</i>
        </Link>)}
        {!loading && searched && !results.length && <p>일치하는 종목이 없습니다. 기업명 또는 종목코드를 확인해 주세요.</p>}
      </div>}
    </section>

    {recent.length > 0 && <section className="stock-explorer-section">
      <div className="stock-explorer-heading"><div><span>HISTORY</span><h2>최근 조회 종목</h2></div><button onClick={() => { clearRecentStocks(); setRecent([]); }}>전체 삭제</button></div>
      <div className="stock-shortcuts">{recent.map(stock => <StockShortcut key={stock.symbol} stock={stock} onChoose={remember} />)}</div>
    </section>}

    <section className="stock-explorer-section">
      <div className="stock-explorer-heading"><div><span>QUICK ACCESS</span><h2>주요 국내 종목</h2></div><p>빠른 탐색을 위한 대표 종목입니다.</p></div>
      <div className="stock-shortcuts">{featured.map(stock => <StockShortcut key={stock.symbol} stock={stock} onChoose={remember} />)}</div>
    </section>
  </>;
}

function StockShortcut({ stock, onChoose }: { stock: RecentStock; onChoose: (stock: RecentStock) => void }) {
  return <Link href={`/stocks/${stock.symbol}`} onClick={() => onChoose(stock)}><span>{stock.market === "kr" ? "KRX" : "US"}</span><strong>{stock.name}</strong><small>{stock.symbol}</small><i>→</i></Link>;
}
