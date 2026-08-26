import "server-only";

import type { ResearchResponse } from "@/lib/types";
import { numeric, supabaseSelect } from "./supabase-rest";

type Row = Record<string, string | number | null>;

export async function getWorkerResearch(params: { category?: string; broker?: string; q?: string; stock_code?: string; limit?: number }): Promise<ResearchResponse> {
  const limit = Math.min(Math.max(params.limit || 100, 1), 200);
  const query: Record<string, string | number> = { select: "*", order: "published_on.desc,id.desc", limit };
  if (params.category) query.category = `eq.${params.category}`;
  if (params.broker) query.broker = `eq.${params.broker}`;
  if (params.stock_code) query.stock_code = `eq.${params.stock_code}`;
  if (params.q) {
    const term = params.q.replace(/[,*()]/g, "");
    query.or = `(title.ilike.*${term}*,stock_name.ilike.*${term}*,broker.ilike.*${term}*,analyst.ilike.*${term}*)`;
  }
  const [rows, facetRows] = await Promise.all([
    supabaseSelect<Row>("research_reports", query),
    supabaseSelect<Row>("research_reports", { select: "broker,category", limit: 1000 }),
  ]);
  const count = (key: "broker" | "category") => Object.entries(facetRows.reduce<Record<string, number>>((acc, row) => {
    const name = String(row[key] || ""); if (name) acc[name] = (acc[name] || 0) + 1; return acc;
  }, {})).sort((a, b) => b[1] - a[1]).map(([name, value]) => ({ name, count: value }));
  return {
    items: rows.map((row) => ({
      id: Number(row.id), source: String(row.source), source_report_id: String(row.source_report_id),
      category: String(row.category), title: String(row.title), broker: String(row.broker),
      analyst: row.analyst ? String(row.analyst) : null, published_on: String(row.published_on),
      stock_code: row.stock_code ? String(row.stock_code) : null, stock_name: row.stock_name ? String(row.stock_name) : null,
      opinion: row.opinion ? String(row.opinion) : null, target_price: numeric(row.target_price),
      previous_target_price: numeric(row.previous_target_price), source_url: String(row.source_url),
    })),
    facets: { brokers: count("broker"), categories: count("category") },
  };
}
