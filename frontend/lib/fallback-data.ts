import type { Dashboard } from "./types";

const asOf = "2026-07-17T08:10:00+09:00";

export const fallbackDashboard: Dashboard = {
  briefing: {
    stance: "risk_on",
    headline: "기술주 강세가 이어졌지만 금리와 환율을 함께 확인하세요",
    summary: "미국 기술주 상승이 국내 반도체 투자심리에 우호적일 가능성이 있습니다. 다만 미국 국채금리와 원·달러 환율의 방향이 장중 변동성을 키울 수 있습니다.",
    keywords: ["미국 기술주", "반도체", "원·달러 환율"],
    source_ids: ["market:nasdaq", "issue:semiconductor"],
    as_of: asOf,
  },
  metrics: [
    ["SPX", "S&P 500", "us", "5,321.41", 0.78], ["DJI", "Dow 30", "us", "39,872.99", 0.32],
    ["IXIC", "NASDAQ", "us", "16,832.62", 1.24], ["RUT", "Russell 2000", "us", "2,103.77", -0.18],
    ["VIX", "VIX", "us", "13.82", -2.12], ["GOLD", "Gold", "us", "2,332.10", 0.41],
    ["KOSPI", "KOSPI", "kr", "2,678.35", 0.45], ["KOSDAQ", "KOSDAQ", "kr", "865.43", 0.72],
    ["KOSPI200", "KOSPI 200", "kr", "365.82", 0.49], ["USDKRW", "USD/KRW", "kr", "1,356.40", -0.32],
    ["KR3Y", "국고채 3년", "kr", "3.21%", -0.04],
  ].map(([symbol, label, market, value, change_pct]) => ({ symbol: String(symbol), label: String(label), market: market as "us" | "kr", value: String(value), change_pct: Number(change_pct), as_of: asOf, stale: false, basis: market === "us" ? "close" as const : "delayed" as const })),
  heatmap: [
    ["NVDA","NVIDIA","기술","반도체",171.38,-2.21,24], ["AAPL","Apple","기술","소비자 전자제품",210.02,0.14,23],
    ["MSFT","Microsoft","기술","소프트웨어",510.05,-1.81,22], ["AVGO","Broadcom","기술","반도체",274.31,-0.97,15],
    ["AMD","AMD","기술","반도체",155.61,-1.03,10], ["ORCL","Oracle","기술","소프트웨어",244.17,1.77,9],
    ["GOOGL","Alphabet","커뮤니케이션","인터넷 콘텐츠",184.92,-2.17,22], ["META","Meta Platforms","커뮤니케이션","인터넷 콘텐츠",702.18,-2.79,14],
    ["NFLX","Netflix","커뮤니케이션","엔터테인먼트",1189.32,-1.26,8], ["AMZN","Amazon","경기소비재","인터넷 소매",223.88,-1.06,18],
    ["TSLA","Tesla","경기소비재","자동차",319.41,-2.61,12], ["HD","Home Depot","경기소비재","주택개선 소매",338.87,-2.63,8],
    ["JPM","JPMorgan Chase","금융","종합은행",289.91,-0.60,12], ["BRK-B","Berkshire Hathaway","금융","보험",472.61,-0.45,13],
    ["V","Visa","금융","결제서비스",349.27,-1.80,10], ["LLY","Eli Lilly","헬스케어","제약",779.27,0.85,12],
    ["JNJ","Johnson & Johnson","헬스케어","제약",166.41,1.23,9], ["WMT","Walmart","필수소비재","할인점",95.38,-0.62,11],
    ["KO","Coca-Cola","필수소비재","음료",69.71,-3.96,8], ["XOM","Exxon Mobil","에너지","통합 석유·가스",113.27,0.97,11],
    ["GE","GE Aerospace","산업재","항공우주",258.21,0.90,9],
  ].map(([symbol,name,sector,industry,price,change_pct,market_cap_weight]) => ({ symbol:String(symbol), name:String(name), sector:String(sector), industry:String(industry), price:Number(price), change_pct:Number(change_pct), market_cap_weight:Number(market_cap_weight), volume:null, dollar_volume:null, relative_volume:null, trading_date:null })),
  schedules: [
    { id: "bls-cpi", source: "bls", country: "US", category: "물가", title: "미국 소비자물가지수(CPI)", scheduled_at: "2026-07-19T21:30:00+09:00", importance: "high", source_url: "https://www.bls.gov/schedule/news_release/cpi.htm" },
    { id: "fed-speech", source: "federal_reserve", country: "US", category: "통화정책", title: "연준 위원 연설", scheduled_at: "2026-07-19T23:00:00+09:00", importance: "high", source_url: "https://www.federalreserve.gov/newsevents/calendar.htm" },
    { id: "bok-ppi", source: "bok", country: "KR", category: "물가", title: "한국 생산자물가지수", scheduled_at: "2026-07-20T06:00:00+09:00", importance: "medium", source_url: "https://www.bok.or.kr/portal/submain/submain/sts.do?menuNo=200094&viewType=SUBMAIN" },
  ],
  issues: [
    { id: "cpi", title: "미국 물가 둔화 기대", summary: "인플레이션 둔화 흐름이 금리 인하 기대를 지지하고 있습니다.", sentiment: "positive", article_count: 24, category: "거시·금리", summary_method: "source_excerpt", articles: [
      { id:"cpi-1", title:"미국 소비자물가 둔화, 금리 경로에 관심", publisher:"연합뉴스", published_at:asOf, url:"https://finance.naver.com/news/", is_representative:true },
      { id:"cpi-2", title:"인플레이션 압력 완화에 미국 증시 상승", publisher:"한국경제", published_at:asOf, url:"https://finance.naver.com/news/", is_representative:false },
      { id:"cpi-3", title:"시장 예상과 부합한 CPI, 연준 판단은", publisher:"매일경제", published_at:asOf, url:"https://finance.naver.com/news/", is_representative:false },
    ] },
    { id: "hbm", title: "HBM 수요 기대", summary: "AI 가속기 수요가 국내 반도체 공급망에 우호적으로 작용할 가능성이 있습니다.", sentiment: "positive", article_count: 18, category: "반도체", summary_method: "source_excerpt", articles: [
      { id:"hbm-1", title:"AI 서버 투자 확대에 HBM 수요 지속", publisher:"전자신문", published_at:asOf, url:"https://finance.naver.com/news/", is_representative:true },
      { id:"hbm-2", title:"국내 반도체 공급망, 차세대 HBM 대응", publisher:"서울경제", published_at:asOf, url:"https://finance.naver.com/news/", is_representative:false },
      { id:"hbm-3", title:"글로벌 AI 투자와 메모리 업황 전망", publisher:"이데일리", published_at:asOf, url:"https://finance.naver.com/news/", is_representative:false },
    ] },
    { id: "oil", title: "국제유가 상승", summary: "공급 불확실성으로 운송·화학 업종 비용 부담이 커질 수 있습니다.", sentiment: "negative", article_count: 15, category: "에너지", summary_method: "source_excerpt", articles: [
      { id:"oil-1", title:"공급 우려에 국제유가 상승세", publisher:"아시아경제", published_at:asOf, url:"https://finance.naver.com/news/", is_representative:true },
      { id:"oil-2", title:"유가 상승이 운송·화학 업종에 미칠 영향", publisher:"머니투데이", published_at:asOf, url:"https://finance.naver.com/news/", is_representative:false },
      { id:"oil-3", title:"지정학적 긴장과 원유 공급 전망", publisher:"뉴스1", published_at:asOf, url:"https://finance.naver.com/news/", is_representative:false },
    ] },
  ],
  disclosures: [
    { id: "dart-1", company: "삼성전자", title: "기업설명회 개최", importance: "medium", filed_at: asOf, source_url: "https://dart.fss.or.kr/" },
    { id: "dart-2", company: "SK하이닉스", title: "신규 시설투자", importance: "high", filed_at: asOf, source_url: "https://dart.fss.or.kr/" },
  ],
  kcif: [
    { id: "kcif-rates", title: "미국 국채금리 방향 전환", summary: "장기 금리 하락은 성장주 가치평가 부담을 일부 낮출 수 있습니다.", topic: "금리", source_url: "https://www.kcif.or.kr/annual/newsflashList", as_of: asOf },
    { id: "kcif-oil", title: "WTI 가격 상승", summary: "지정학적 불확실성과 공급 우려가 유가에 반영되고 있습니다.", topic: "원자재", source_url: "https://www.kcif.or.kr/annual/newsflashList", as_of: asOf },
  ],
  research: [],
  freshness: ["시장 데이터", "뉴스·이슈", "공시", "KCIF"].map((label, index) => ({ dataset: `source-${index}`, label, as_of: asOf, stale: false })),
};
