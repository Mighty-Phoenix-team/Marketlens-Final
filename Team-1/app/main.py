from __future__ import annotations

from fastapi import FastAPI, HTTPException, Query

from .cache import TTLCache
from .config import settings
from .models import AssetData
from .normalization import (
    normalize_company_report,
    normalize_daily_rows,
    normalize_foreign_rows,
)
from .sectors_client import SectorsAPIError, SectorsClient, clean_symbol


# P1 adds dividend to the existing report request; unused peers remain excluded.
DEFAULT_COMPANY_SECTIONS = ("overview", "financials", "valuation", "dividend")


def validated_symbol(symbol: str) -> str:
    try:
        return clean_symbol(symbol)
    except SectorsAPIError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


app = FastAPI(
    title="MarketLens Team 1 Backend",
    version="0.3.0",
    description="Backend adapter for Sectors Financial API v2.",
)

cache = TTLCache()
sectors = SectorsClient(settings, cache)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/assets/{symbol}/company-report")
async def company_report(
    symbol: str,
    sections: str = Query(
        default=",".join(DEFAULT_COMPANY_SECTIONS),
        description="Comma-separated Sectors v2 Company Report sections.",
    ),
):
    symbol = validated_symbol(symbol)
    requested = [s.strip().lower() for s in sections.split(",") if s.strip()]

    allowed = {
        "overview",
        "valuation",
        "future",
        "peers",
        "financials",
        "dividend",
        "management",
        "ownership",
    }
    unknown = sorted(set(requested) - allowed)
    if unknown:
        raise HTTPException(
            status_code=400,
            detail={"error": "Unknown Company Report sections", "sections": unknown},
        )

    if not requested:
        raise HTTPException(status_code=400, detail="At least one section is required")

    try:
        payload, source, retrieved_at = await sectors.get_company_report(symbol, requested)
        return normalize_company_report(payload, source, retrieved_at, requested_symbol=symbol)
    except SectorsAPIError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@app.get("/api/assets/{symbol}")
async def asset_data(
    symbol: str,
    start: str | None = None,
    end: str | None = None,
):
    symbol = validated_symbol(symbol)
    limitations: list[str] = []
    source_endpoints: list[str] = []
    asset = AssetData(symbol=symbol)

    # Request only the four sections used by the P0 + Income upgrade.
    try:
        payload, source, retrieved_at = await sectors.get_company_report(
            symbol,
            list(DEFAULT_COMPANY_SECTIONS),
        )
        asset.company = normalize_company_report(payload, source, retrieved_at, requested_symbol=symbol)
        source_endpoints.append(source)
    except SectorsAPIError as exc:
        limitations.append(f"Company Report unavailable: {exc.message}")

    # Daily Transaction — v2 path confirmed (SKILL.md §4/§12): GET /v2/daily/{symbol}/
    try:
        params = {k: v for k, v in {"start": start, "end": end}.items() if v}
        payload, source = await sectors.get_configured_series(
            settings.sectors_daily_path,
            symbol,
            params=params,
            cache_namespace="daily",
        )
        asset.market = normalize_daily_rows(payload)
        source_endpoints.append(source)
    except SectorsAPIError as exc:
        limitations.append(f"Daily Transaction unavailable: {exc.message}")

    # Foreign Flow — v2 path confirmed (SKILL.md §4/§12): GET /v2/foreign-flow/{symbol}/
    try:
        params = {k: v for k, v in {"start": start, "end": end}.items() if v}
        payload, source = await sectors.get_configured_series(
            settings.sectors_foreign_flow_path,
            symbol,
            params=params,
            cache_namespace="foreign-flow",
        )
        asset.foreign_flow = normalize_foreign_rows(payload)
        source_endpoints.append(source)
    except SectorsAPIError as exc:
        limitations.append(f"Foreign Flow unavailable: {exc.message}")

    asset.limitations = limitations
    asset.source_endpoints = source_endpoints
    return asset
