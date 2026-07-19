import Link from "next/link";
import type { ReactNode } from "react";

export function DetailPage({ eyebrow, title, description, children }: { eyebrow: string; title: string; description: string; children: ReactNode }) {
  return <main className="detail-page"><div className="detail-hero"><span className="eyebrow">{eyebrow}</span><h1>{title}</h1><p>{description}</p></div>{children}<Link className="back-link" href="/">← 홈 대시보드로</Link></main>;
}
