import type { Metadata } from "next";
import localFont from "next/font/local";
import { Header } from "@/components/Header";
import "./globals.css";

const hana = localFont({
  src: [
    { path: "./fonts/Hana2-Light.otf", weight: "300", style: "normal" },
    { path: "./fonts/Hana2-Regular.otf", weight: "400", style: "normal" },
    { path: "./fonts/Hana2-Medium.otf", weight: "500", style: "normal" },
    { path: "./fonts/Hana2-Bold.otf", weight: "700", style: "normal" },
    { path: "./fonts/Hana2-Heavy.otf", weight: "900", style: "normal" },
  ],
  variable: "--font-hana",
  display: "swap",
});

const hanaCm = localFont({
  src: "./fonts/Hana2-CM.otf",
  variable: "--font-hana-cm",
  display: "swap",
});

export const metadata: Metadata = { title: "stock-hanaro", description: "글로벌 시장, 뉴스, 공시와 브리핑을 한눈에" };

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="ko" className={`${hana.variable} ${hanaCm.variable}`}><body><Header />{children}<footer>© 2026 stock-hanaro · AI 요약은 출처 기반 참고 정보이며 투자 권유가 아닙니다.</footer></body></html>;
}
