export const disclosureTypeLabels: Record<string, string> = {
  A: "정기공시", B: "주요사항", C: "발행공시", D: "지분공시", E: "기타공시",
  F: "외부감사", G: "펀드공시", H: "자산유동화", I: "거래소공시", J: "공정위공시",
};

export type DisclosureEvent = {
  type: string;
  label: string;
  group: "capital" | "shareholder" | "restructure" | "risk" | "business" | "ownership" | "periodic" | "other";
  priority: number;
};

const eventRules: Array<[RegExp, DisclosureEvent]> = [
  [/유무상증자/, { type: "PAID_BONUS_ISSUE", label: "유·무상증자", group: "capital", priority: 95 }],
  [/유상증자/, { type: "RIGHTS_ISSUE", label: "유상증자", group: "capital", priority: 94 }],
  [/무상증자/, { type: "BONUS_ISSUE", label: "무상증자", group: "capital", priority: 88 }],
  [/감자/, { type: "CAPITAL_REDUCTION", label: "감자", group: "capital", priority: 96 }],
  [/전환사채|전환사채권/, { type: "CB", label: "전환사채", group: "capital", priority: 86 }],
  [/신주인수권부사채|신주인수권부사채권/, { type: "BW", label: "신주인수권부사채", group: "capital", priority: 85 }],
  [/교환사채|교환사채권/, { type: "EB", label: "교환사채", group: "capital", priority: 84 }],
  [/자기주식.*취득|자사주.*취득/, { type: "TREASURY_ACQUIRE", label: "자기주식 취득", group: "shareholder", priority: 82 }],
  [/자기주식.*처분|자사주.*처분/, { type: "TREASURY_DISPOSE", label: "자기주식 처분", group: "shareholder", priority: 78 }],
  [/분할합병/, { type: "SPLIT_MERGER", label: "분할합병", group: "restructure", priority: 92 }],
  [/합병/, { type: "MERGER", label: "합병", group: "restructure", priority: 93 }],
  [/회사분할|분할결정/, { type: "SPLIT", label: "회사분할", group: "restructure", priority: 91 }],
  [/주식교환|주식이전/, { type: "SHARE_SWAP", label: "주식교환·이전", group: "restructure", priority: 89 }],
  [/부도/, { type: "DEFAULT", label: "부도", group: "risk", priority: 100 }],
  [/회생절차/, { type: "REHABILITATION", label: "회생절차", group: "risk", priority: 99 }],
  [/영업정지/, { type: "SUSPENSION", label: "영업정지", group: "risk", priority: 98 }],
  [/상장폐지/, { type: "DELISTING", label: "상장폐지", group: "risk", priority: 97 }],
  [/공급계약|판매계약|수주/, { type: "SUPPLY_CONTRACT", label: "공급·수주", group: "business", priority: 80 }],
  [/영업양수|영업양도|영업양수도/, { type: "BUSINESS_TRANSFER", label: "영업양수도", group: "business", priority: 87 }],
  [/타법인.*주식.*취득|출자증권.*취득/, { type: "OTHER_COMPANY_ACQUIRE", label: "타법인주식 취득", group: "business", priority: 75 }],
  [/최대주주.*변경/, { type: "CONTROLLING_OWNER_CHANGE", label: "최대주주 변경", group: "ownership", priority: 90 }],
  [/대량보유|주식등의대량보유/, { type: "LARGE_HOLDING", label: "대량보유", group: "ownership", priority: 70 }],
  [/임원.*주요주주.*소유/, { type: "INSIDER_HOLDING", label: "임원·주요주주", group: "ownership", priority: 65 }],
  [/사업보고서/, { type: "ANNUAL_REPORT", label: "사업보고서", group: "periodic", priority: 45 }],
  [/반기보고서/, { type: "SEMIANNUAL_REPORT", label: "반기보고서", group: "periodic", priority: 42 }],
  [/분기보고서/, { type: "QUARTERLY_REPORT", label: "분기보고서", group: "periodic", priority: 40 }],
];

export function classifyDisclosure(title: string, reportType?: string | null): DisclosureEvent {
  const normalized = title.replace(/\s+/g, "");
  const matched = eventRules.find(([pattern]) => pattern.test(normalized));
  if (matched) return matched[1];
  return {
    type: reportType ? `TYPE_${reportType}` : "OTHER",
    label: disclosureTypeLabels[reportType || ""] || "기타",
    group: "other",
    priority: reportType === "B" || reportType === "C" || reportType === "I" ? 35 : 10,
  };
}

export function isCorrectionTitle(title: string) {
  return /^\s*\[(기재정정|첨부정정|정정)\]|^\s*정정/.test(title);
}
