import Link from "next/link";

const links = [
  ["/", "홈"], ["/markets", "글로벌 시장"], ["/issues", "뉴스·이슈"],
  ["/calendar", "주요 일정"], ["/disclosures", "공시"], ["/stocks", "종목"], ["/briefings", "브리핑"],
];

export function Header() {
  return <header className="site-header">
    <Link className="brand" href="/"><span>stock</span> hanaro<small>MARKET INTELLIGENCE</small></Link>
    <nav>{links.map(([href, label]) => <Link key={href} href={href}>{label}</Link>)}</nav>
    <div className="header-meta"><span className="search">종목·이슈 검색</span><Link className="data-status" href="/status"><i />데이터 정상</Link></div>
  </header>;
}
