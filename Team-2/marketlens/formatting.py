"""Unit-aware presentation shared by observations, fallback and dashboard."""

from __future__ import annotations

import math


LABELS = {
    "dividend_yield_ttm": "Dividend yield (TTM)",
    "average_dividend_yield": "Average dividend yield (provider)",
    "payout_ratio": "Payout ratio",
    "cash_payout_ratio": "Cash payout ratio",
    "historical_dividend_yield": "Dividend yield (latest labelled year)",
    "pe": "PE", "pb": "PB", "peg": "PEG", "forward_pe": "Forward PE (estimate)",
    "roe": "ROE", "roa": "ROA", "net_profit_margin": "Net profit margin",
    "operating_profit_margin": "Operating profit margin",
    "pe_vs_history": "PE vs historical median", "pb_vs_history": "PB vs historical median",
    "pe_vs_peer": "PE vs provider peer average", "pb_vs_peer": "PB vs provider peer average",
    "roe_change": "ROE annual change", "roa_change": "ROA annual change",
    "net_profit_margin_change": "Net profit margin annual change",
    "operating_profit_margin_change": "Operating profit margin annual change",
}


def metric_label(item: dict) -> str:
    name = item.get("metric", "")
    return LABELS.get(name, name.replace("_", " ").capitalize())


def format_value(item: dict) -> str:
    value = item.get("value")
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        return "Unavailable"
    if item.get("unit") == "multiple":
        return f"{value:.2f}×"
    if item.get("unit") == "decimal_ratio_change":
        return f"{value * 100:+.2f} pp"
    if item.get("unit") == "decimal_ratio":
        return f"{value * 100:.2f}%"
    return f"{value:+.4f}"
