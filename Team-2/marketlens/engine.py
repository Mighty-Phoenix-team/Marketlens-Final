"""Pure, reproducible analysis of Team 1's unified asset response.

No investment recommendation or causal inference is produced here.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
import json
from pathlib import Path
from typing import Any
from .p0 import build_p0_evidence
from .income import build_income_evidence
from .formatting import format_value, metric_label


GROUPS = ("fundamental", "market_activity", "investor_flow", "valuation", "quality", "income")
FOCUS_ALIASES = {
    "growth": "fundamental",
    "fundamental": "fundamental",
    "market": "market_activity",
    "market_activity": "market_activity",
    "price": "market_activity",
    "flow": "investor_flow",
    "investor_flow": "investor_flow",
    "valuation": "valuation",
    "quality": "quality",
    "profitability": "quality",
    "income": "income",
    "dividend": "income",
}
METHODOLOGY = json.loads((Path(__file__).with_name("methodology.json")).read_text(encoding="utf-8"))
THRESHOLDS = METHODOLOGY["thresholds"]


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    result = float(value)
    return result if result == result and abs(result) != float("inf") else None


def _dated_rows(rows: Any, field: str) -> list[tuple[str, float, dict]]:
    valid = []
    for row in rows if isinstance(rows, list) else []:
        if not isinstance(row, dict):
            continue
        stamp, value = row.get("observed_at"), _number(row.get(field))
        try:
            if not isinstance(stamp, str):
                continue
            date.fromisoformat(stamp)
        except ValueError:
            continue
        if value is not None:
            valid.append((stamp, value, row))
    return sorted(valid, key=lambda item: item[0])


def _metric(group: str, name: str, value: float, *, baseline: float | None,
            period: str, method: str, source: str | None, observed_at: str | None,
            retrieved_at: str) -> dict:
    return {
        "group": group, "metric": name, "value": round(value, 8),
        "baseline": baseline, "period": period, "method": method,
        "source": source, "observed_at": observed_at,
        "retrieved_at": retrieved_at,
        "strength": round(min(abs(value) / THRESHOLDS[name], 1.0), 6),
        "unit": "decimal_ratio", "kind": "observed" if baseline is None else "derived",
    }


def analyze_asset(payload: dict, profile: dict, *, retrieved_at: str | None = None) -> dict:
    """Return a finding from verified fields only; missing history stays missing."""
    if not isinstance(payload, dict) or not isinstance(payload.get("symbol"), str):
        raise ValueError("Unified asset response must contain a symbol")
    symbol = payload["symbol"].strip().upper()
    if not symbol:
        raise ValueError("Asset symbol is empty")
    retrieved_at = retrieved_at or datetime.now(timezone.utc).isoformat()
    company = payload.get("company") or {}
    if not isinstance(company, dict):
        company = {}
    overview = company.get("overview") or {}
    financials = company.get("financials") or {}
    if not isinstance(overview, dict):
        overview = {}
    if not isinstance(financials, dict):
        financials = {}
    endpoints = payload.get("source_endpoints") or []
    endpoints = [x for x in endpoints if isinstance(x, str)] if isinstance(endpoints, list) else []
    sources = {
        "fundamental": company.get("source_endpoint") or next((x for x in endpoints if "/company/report/" in x), None),
        "market_activity": next((x for x in endpoints if "/daily/" in x), None),
        "investor_flow": next((x for x in endpoints if "/foreign-flow/" in x), None),
    }
    evidence: list[dict] = []
    limitations = [str(x) for x in payload.get("limitations", []) if isinstance(x, str)]
    company_retrieved_at = company.get("retrieved_at") or retrieved_at

    for name, field in (("revenue_growth", "yoy_quarter_revenue_growth"),
                        ("earnings_growth", "yoy_quarter_earnings_growth")):
        value = _number(financials.get(field))
        if value is not None:
            evidence.append(_metric("fundamental", name, value, baseline=None,
                period="year-over-year quarter (source supplied)",
                method=f"{field} supplied by company report; decimal ratio",
                source=sources["fundamental"], observed_at=None, retrieved_at=company_retrieved_at))
    eps = financials.get("historical_eps")
    if isinstance(eps, dict):
        years = sorted((str(y), v) for y, v in eps.items() if str(y).isdigit() and isinstance(v, dict))
        for year, item in years[-1:]:
            value = _number(item.get("eps_growth"))
            if value is not None:
                evidence.append(_metric("fundamental", "eps_growth", value, baseline=None,
                    period=year, method="eps_growth supplied by historical_eps; decimal ratio",
                    source=sources["fundamental"], observed_at=year, retrieved_at=company_retrieved_at))

    p0_evidence, p0_limitations = build_p0_evidence(company, METHODOLOGY)
    evidence.extend(p0_evidence)
    limitations.extend(p0_limitations)
    income_evidence, income_limitations = build_income_evidence(company, METHODOLOGY)
    evidence.extend(income_evidence)
    limitations.extend(income_limitations)
    endpoints = list(dict.fromkeys(endpoints + [item["source"] for item in evidence if item.get("source")]))

    prices = _dated_rows(payload.get("market"), "price")
    if len(prices) >= 2:
        first, last = prices[0], prices[-1]
        if first[1] > 0 and first[0] != last[0]:
            evidence.append(_metric("market_activity", "price_change",
                (last[1] - first[1]) / first[1], baseline=first[1],
                period=f"{first[0]} to {last[0]}",
                method="(last price - first price) / first price",
                source=sources["market_activity"], observed_at=last[0], retrieved_at=retrieved_at))
    else:
        limitations.append("Price change unavailable: at least two dated price observations are required.")
    volumes = _dated_rows(payload.get("market"), "volume")
    if len(volumes) >= 2:
        first, last = volumes[0], volumes[-1]
        if first[1] > 0 and first[0] != last[0]:
            evidence.append(_metric("market_activity", "volume_change",
                (last[1] - first[1]) / first[1], baseline=first[1],
                period=f"{first[0]} to {last[0]}",
                method="(last volume - first volume) / first volume",
                source=sources["market_activity"], observed_at=last[0], retrieved_at=retrieved_at))
    else:
        limitations.append("Volume change unavailable: at least two dated volume observations are required.")

    flows = _dated_rows(payload.get("foreign_flow"), "net_foreign_inflow")
    if flows:
        stamp, net, row = flows[-1]
        buy, sell = _number(row.get("foreign_buy_idr")), _number(row.get("foreign_sell_idr"))
        if buy is not None and sell is not None and buy >= 0 and sell >= 0 and buy + sell > 0:
            evidence.append(_metric("investor_flow", "foreign_imbalance",
                net / (buy + sell), baseline=buy + sell, period=stamp,
                method="net_foreign_inflow / (foreign_buy_idr + foreign_sell_idr); observed level, not change",
                source=sources["investor_flow"], observed_at=stamp, retrieved_at=retrieved_at))
        else:
            limitations.append("Foreign imbalance unavailable: valid buy and sell totals are required.")
    else:
        limitations.append("Foreign flow unavailable: no dated observation with a numeric net flow.")

    focus = {FOCUS_ALIASES[str(x).lower()] for x in profile.get("research_focus", [])
             if str(x).lower() in FOCUS_ALIASES}
    sectors = {str(x).casefold() for x in profile.get("sectors", [])}
    sector = str(overview.get("sector") or "")
    sector_factor = (METHODOLOGY["matching_sector_factor"] if not sectors or sector.casefold() in sectors
                     else METHODOLOGY["other_sector_factor"])
    group_strength = {g: max((item["strength"] for item in evidence if item["group"] == g), default=0.0)
                      for g in GROUPS}
    available = [g for g in GROUPS if any(item["group"] == g for item in evidence)]
    focus_weight = {g: (METHODOLOGY["selected_focus_weight"] if not focus or g in focus
                        else METHODOLOGY["other_focus_weight"]) for g in GROUPS}
    weighted = sum(group_strength[g] * focus_weight[g] for g in GROUPS) / sum(focus_weight.values())
    availability = len(available) / len(GROUPS)
    score = round(10 * weighted * availability * sector_factor, 2)
    if not evidence:
        limitations.append("No verified metric available; research relevance is zero.")
    limitations.append("Co-movement does not establish causality or predict future returns.")
    observations = [f"{metric_label(e)}: {format_value(e)} ({e['period']})" for e in evidence]
    return {
        "id": symbol, "symbol": symbol,
        "company_name": company.get("company_name") or symbol,
        "sector": sector or None,
        "research_relevance": score,
        "observation": observations or ["Data unavailable for a measured finding."],
        "evidence": evidence,
        "signal_groups": available,
        "methodology_version": METHODOLOGY["version"],
        "relevance_reason": {
            "selected_focus": sorted(focus), "matched_groups": sorted(focus.intersection(available)),
            "sector_match": sector_factor == 1.0,
            "group_strength": group_strength,
            "availability_factor": round(availability, 6),
            "sector_factor": sector_factor,
            "focus_weights": focus_weight,
            "expected_groups": list(GROUPS),
        },
        "reasoning": "Evidence strength is weighted by research focus, available groups, and sector interest. P0 and Income levels receive a fixed context-availability strength; comparable differences receive direction-neutral salience. Neither is investment quality.",
        "method": "10 × [Σ(max evidence strength per group × focus weight) / Σ(focus weights)] × (available groups/6) × sector factor. P0 and Income levels: fixed 0.25; derived P0 differences and existing metrics: min(abs(value)/threshold, 1). See versioned marketlens/methodology.json.",
        "retrieved_at": retrieved_at,
        "limitations": list(dict.fromkeys(limitations)),
        "source_endpoints": endpoints,
    }


def rank_assets(payloads: list[dict], profile: dict, *, limit: int = 5) -> list[dict]:
    """Same engine as My Assets; deterministic descending relevance order."""
    findings = [analyze_asset(payload, profile, retrieved_at=payload.get("_marketlens_retrieved_at")) for payload in payloads]
    return sorted((f for f in findings if f["evidence"]),
                  key=lambda f: (-f["research_relevance"], f["symbol"]))[:limit]
