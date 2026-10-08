import type { UnavailableAsset } from "./types";
const RATIOS = new Set([
  "revenue_growth",
  "earnings_growth",
  "eps_growth",
  "price_change",
  "volume_change",
  "foreign_imbalance",
]);
export function metricLabel(metric: string) {
  return metric.replaceAll("_", " ").replace(/\b\w/g, (c) => c.toUpperCase());
}
export function metricValue(metric: string, value: number) {
  if (!Number.isFinite(value)) return "Data unavailable";
  return RATIOS.has(metric)
    ? (value > 0 ? "+" : "") + (value * 100).toFixed(2) + "%"
    : value.toLocaleString("id-ID");
}
export function unavailableLabel(item: UnavailableAsset) {
  return typeof item === "string" ? item : item.symbol + ": " + item.error;
}
export function cleanTicker(value: string) {
  return value.trim().toUpperCase().replace(/\.JK$/, "");
}
export function validTicker(value: string) {
  return /^[A-Z0-9]{1,12}$/.test(value);
}
