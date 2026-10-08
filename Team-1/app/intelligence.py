"""Normalize verified Sectors P0 paths, preserving units and provider periods.

Verified against the user's BBCA capture retrieved 2026-10-01T14:45:07Z.
No provider request, ranking, investment judgment, or missing-value estimation.
"""

from __future__ import annotations

from datetime import date
import math
import re
from typing import Any

from .models import IntelligenceData, QualityData, QualityYear, ValuationData, ValuationYear
from .income import normalize_income


VALUATION_FIELDS = ("pe", "pb", "peg", "pe_peer_avg", "pb_peer_avg")
QUALITY_FIELDS = ("roe", "roa", "net_profit_margin", "operating_profit_margin")


def finite_number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        return None
    if isinstance(value, str) and not re.fullmatch(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?", value.strip()):
        return None
    try:
        number = float(value)
    except (ValueError, OverflowError):
        return None
    return number if math.isfinite(number) else None


def _year(value: Any) -> int | None:
    if isinstance(value, bool) or not isinstance(value, (int, str)):
        return None
    text = str(value).strip()
    return int(text) if re.fullmatch(r"\d{4}", text) and 1900 <= int(text) <= 2100 else None


def _date(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    try:
        return date.fromisoformat(value).isoformat()
    except ValueError:
        return None


def _history(raw: Any, fields: tuple[str, ...], label: str, limitations: list[str], *, nested: str | None = None) -> list[dict]:
    if not isinstance(raw, list):
        limitations.append(f"{label} history unavailable: expected a list of year-labelled rows.")
        return []
    by_year: dict[int, dict] = {}
    conflicts: set[int] = set()
    invalid_rows = False
    for row in raw:
        if not isinstance(row, dict) or (year := _year(row.get("year"))) is None:
            invalid_rows = True
            continue
        values = row.get(nested) if nested else row
        values = values if isinstance(values, dict) else {}
        point = {"year": year, **{key: finite_number(values.get(key)) for key in fields}}
        for key in fields:
            if values.get(key) is not None and point[key] is None:
                limitations.append(f"{label} {year} {key}: invalid numeric value treated as unavailable.")
        if year in by_year and by_year[year] != point:
            conflicts.add(year)
        by_year.setdefault(year, point)
    if invalid_rows:
        limitations.append(f"{label}: ignored malformed rows or invalid/missing years.")
    for year in sorted(conflicts):
        # Keep the year visible; never silently substitute an older year for it.
        by_year[year] = {"year": year, **dict.fromkeys(fields)}
        limitations.append(f"{label} {year}: conflicting duplicate rows; metrics unavailable for this year.")
    return [by_year[year] for year in sorted(by_year)]


def normalize_intelligence(payload: dict, source_endpoint: str, retrieved_at: str) -> IntelligenceData:
    limitations: list[str] = []
    valuation = payload.get("valuation")
    valuation = valuation if isinstance(valuation, dict) else {}
    financials = payload.get("financials")
    financials = financials if isinstance(financials, dict) else {}
    v_history = [ValuationYear(**row) for row in _history(
        valuation.get("historical_valuation"), VALUATION_FIELDS, "Valuation", limitations)]
    q_history = [QualityYear(**row) for row in _history(
        financials.get("historical_financial_ratio"), QUALITY_FIELDS, "Quality", limitations,
        nested="profitability")]
    v_latest = v_history[-1] if v_history else None
    q_latest = q_history[-1] if q_history else None
    for label, point, fields in [("Valuation", v_latest, ("pe", "pb", "peg")),
                                 ("Quality", q_latest, QUALITY_FIELDS)]:
        if point:
            missing = [key for key in fields if getattr(point, key) is None]
            if missing:
                limitations.append(f"{label} {point.year}: unavailable metrics: {', '.join(missing)}; older values were not substituted.")
    if v_latest:
        limitations.append("Historical valuation years are provider labels; the payload does not confirm trailing/full-year calculation basis or a precise observation date for each row.")
    forward = finite_number(valuation.get("forward_pe"))
    if forward is not None:
        limitations.append("Forward PE is an estimate with no supplied forecast horizon; it is not compared with historical PE in scoring.")
    if v_latest and q_latest and v_latest.year != q_latest.year:
        limitations.append(f"Valuation's latest provider year is {v_latest.year}; quality's latest financial year is {q_latest.year}. These are different periods.")
    if any(row.pe_peer_avg is not None or row.pb_peer_avg is not None for row in v_history):
        limitations.append("Peer averages are supplied inside valuation; peer membership, weighting and calculation methodology are not provided in this capture.")
    return IntelligenceData(
        valuation=ValuationData(
            forward_pe=forward,
            last_close_price=finite_number(valuation.get("last_close_price")),
            price_as_of=_date(valuation.get("latest_close_date")),
            latest=v_latest, history=v_history,
        ),
        quality=QualityData(latest=q_latest, history=q_history),
        income=normalize_income(payload.get("dividend"), source_endpoint, retrieved_at),
        source_endpoint=source_endpoint, retrieved_at=retrieved_at,
        limitations=list(dict.fromkeys(limitations)),
    )
