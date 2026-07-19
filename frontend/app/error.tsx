"use client";
export default function ErrorPage({ reset }: { reset: () => void }) { return <main className="dashboard"><div className="error-card"><h1>데이터를 불러오지 못했습니다</h1><p>기존 데이터가 있으면 마지막 정상 결과를 표시합니다.</p><button onClick={reset}>다시 시도</button></div></main>; }
