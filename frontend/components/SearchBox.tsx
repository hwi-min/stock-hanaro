"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "/backend-api";
type Result = { type: "stock" | "issue"; id: string; symbol?: string; name: string; market: "kr" | "us" | null; label: string };

export function SearchBox() {
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [items, setItems] = useState<Result[]>([]);
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(0);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (timer.current) clearTimeout(timer.current);
    if (!query.trim()) { setItems([]); setOpen(false); return; }
    timer.current = setTimeout(async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/api/search?q=${encodeURIComponent(query.trim())}`);
        const data = response.ok ? await response.json() as { items: Result[] } : { items: [] };
        setItems(data.items); setActive(0); setOpen(true);
      } catch { setItems([]); setOpen(true); }
    }, 180);
    return () => { if (timer.current) clearTimeout(timer.current); };
  }, [query]);

  const choose = (item: Result) => {
    setOpen(false); setQuery("");
    router.push(item.type === "stock" ? `/stocks/${encodeURIComponent(item.id)}` : `/issues/${encodeURIComponent(item.id)}`);
  };
  return <div className="global-search">
    <input aria-label="종목·이슈 검색" placeholder="종목·이슈 검색" value={query}
      onFocus={() => query && setOpen(true)} onChange={event => setQuery(event.currentTarget.value)}
      onInput={event => setQuery(event.currentTarget.value)} onKeyUp={event => setQuery(event.currentTarget.value)}
      onKeyDown={event => {
        if (!open || !items.length) return;
        if (event.key === "ArrowDown") { event.preventDefault(); setActive(value => (value + 1) % items.length); }
        if (event.key === "ArrowUp") { event.preventDefault(); setActive(value => (value - 1 + items.length) % items.length); }
        if (event.key === "Enter") { event.preventDefault(); choose(items[active]); }
        if (event.key === "Escape") setOpen(false);
      }} />
    {open && <div className="search-results" role="listbox">
      {items.length ? items.map((item, index) => <button type="button" key={`${item.type}:${item.id}`}
        className={index === active ? "active" : ""} onMouseDown={() => choose(item)}>
        <span>{item.label}</span><small>{item.type === "stock" ? (item.market === "kr" ? "국내 종목" : "미국 종목") : "뉴스·이슈"}</small>
      </button>) : <p>일치하는 검색 결과가 없습니다.</p>}
    </div>}
  </div>;
}
