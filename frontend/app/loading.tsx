export default function Loading() {
  return <main className="dashboard dashboard-loading" aria-live="polite" aria-busy="true">
    <section className="loading-intro">
      <span>MARKET INTELLIGENCE</span>
      <h1>최신 시장 데이터를 불러오는 중입니다</h1>
      <p>먼저 도착한 데이터부터 화면을 준비하고 있습니다.</p>
      <i />
    </section>
    <div className="loading-skeleton wide" />
    <div className="loading-skeleton-grid"><div /><div /><div /></div>
    <div className="loading-skeleton-grid two"><div /><div /></div>
  </main>;
}
