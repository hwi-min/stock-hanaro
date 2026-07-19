import type { Dashboard } from "./types";

export type Disclosure = Dashboard["disclosures"][number];

export function disclosureUrl(item: Disclosure): string {
  if (item.source_url) return item.source_url;
  if (/^\d{14}$/.test(item.id)) {
    return `https://dart.fss.or.kr/dsaf001/main.do?rcpNo=${encodeURIComponent(item.id)}`;
  }
  return "https://dart.fss.or.kr/";
}
