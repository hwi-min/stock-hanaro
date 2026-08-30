import Link from "next/link";
import type { ReactNode } from "react";

export function Section({ title, href, children, className = "", status }: { title: string; href?: string; children: ReactNode; className?: string; status?: ReactNode }) {
  return <section className={`panel ${className}`}>
    <div className="panel-heading"><h2>{title}</h2><div className="panel-heading-meta">{status}{href && <Link href={href}>자세히 보기 →</Link>}</div></div>
    {children}
  </section>;
}
