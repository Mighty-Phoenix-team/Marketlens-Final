from __future__ import annotations

from typing import Any
from .intelligence import finite_number, normalize_intelligence

from .models import (
    AssetData,
    CompanyReport,
    ForeignFlowSnapshot,
    MarketSnapshot,
)


def _first_number(obj: dict[str, Any], *keys: str) -> float | None:
    for key in keys:
        value = finite_number(obj.get(key))
        if value is not None:
            return value
    return None


def _dict_section(payload: dict[str, Any], key: str) -> dict[str, Any] | None:
    value = payload.get(key)
    return value if isinstance(value, dict) else None


def normalize_company_report(
    payload: dict[str, Any],
    source_endpoint: str,
    retrieved_at: str,
    requested_symbol: str,
) -> CompanyReport:
    # Prefer the provider's symbol; the requested symbol is the fallback.
    raw_symbol = payload.get("symbol")
    symbol = (
        str(raw_symbol).upper().replace(".JK", "")
        if raw_symbol
        else requested_symbol.upper().replace(".JK", "")
    )

    peers_raw = payload.get("peers")
    peers = peers_raw if isinstance(peers_raw, list) else None

    return CompanyReport(
        symbol=symbol,
        company_name=payload.get("company_name"),
        overview=_dict_section(payload, "overview"),
        valuation=_dict_section(payload, "valuation"),
        future=_dict_section(payload, "future"),
        peers=peers,
        financials=_dict_section(payload, "financials"),
        dividend=_dict_section(payload, "dividend"),
        management=_dict_section(payload, "management"),
        ownership=_dict_section(payload, "ownership"),
        intelligence=normalize_intelligence(payload, source_endpoint, retrieved_at),
        source_endpoint=source_endpoint,
        retrieved_at=retrieved_at,
    )


def normalize_daily_rows(payload: dict[str, Any] | list[Any]) -> list[MarketSnapshot]:
    rows = payload if isinstance(payload, list) else payload.get("data", [])
    normalized: list[MarketSnapshot] = []

    if not isinstance(rows, list):
        return normalized

    for row in rows:
        if not isinstance(row, dict):
            continue
        normalized.append(
            MarketSnapshot(
                price=_first_number(row, "close", "price", "last_close_price"),
                volume=_first_number(row, "volume", "transaction_volume"),
                market_cap=_first_number(row, "market_cap"),
                observed_at=row.get("date") or row.get("datetime"),
            )
        )
    return normalized


def normalize_foreign_rows(payload: dict[str, Any] | list[Any]) -> list[ForeignFlowSnapshot]:
    rows = payload if isinstance(payload, list) else payload.get("data", [])
    normalized: list[ForeignFlowSnapshot] = []

    if not isinstance(rows, list):
        return normalized

    for row in rows:
        if not isinstance(row, dict):
            continue
        normalized.append(
            ForeignFlowSnapshot(
                net_foreign_inflow=_first_number(row, "net_foreign_inflow"),
                foreign_share=_first_number(row, "foreign_share"),
                foreign_buy_idr=_first_number(row, "foreign_buy_idr"),
                foreign_sell_idr=_first_number(row, "foreign_sell_idr"),
                observed_at=row.get("date") or row.get("datetime"),
            )
        )
    return normalized
