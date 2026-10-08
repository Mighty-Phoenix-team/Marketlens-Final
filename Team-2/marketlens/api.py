"""Standalone FastAPI facade for Team 2, consuming Team 1's unified endpoint."""

from __future__ import annotations

import asyncio
import json
import os
import re
import sqlite3
import uuid
import time
import logging
from contextlib import contextmanager, asynccontextmanager
from datetime import date, timedelta
from pathlib import Path

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator

from .engine import analyze_asset, rank_assets, FOCUS_ALIASES
from .grounding import build_explanation_context
from .llm import explain_finding_async as explain_finding, explanation_namespace
from .explanation_service import ExplanationService
from .fallback import build_fallback_explanation
from .comparison import compare_findings, compare_watchlist_discovery
from .schemas import ComparisonRequest
from datetime import datetime, timezone


SYMBOL = re.compile(r"^[A-Z0-9]{1,12}$")
explanations = ExplanationService()
logger = logging.getLogger("uvicorn.error")


@asynccontextmanager
async def lifespan(app):
    yield
    await explanations.close()


app = FastAPI(title="MarketLens Team 2", version="0.4.0", lifespan=lifespan)
_cache: dict[tuple, tuple[float, dict]] = {}
app.add_middleware(
    CORSMiddleware,
    allow_origins=[s.strip() for s in os.getenv("MARKETLENS_CORS_ORIGINS",
                   "http://localhost:3000,http://127.0.0.1:3000,http://192.168.1.6:3000").split(",") if s.strip()],
    allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)


class ProfileInput(BaseModel):
    sectors: list[str] = Field(default_factory=list, max_length=20)
    research_focus: list[str] = Field(default_factory=list, max_length=3)
    horizon_days: int = Field(default=30, ge=2, le=90)

    @field_validator("research_focus")
    @classmethod
    def valid_focus(cls, values: list[str]) -> list[str]:
        if any(value.lower() not in FOCUS_ALIASES for value in values):
            raise ValueError(f"Use focus names from: {', '.join(sorted(FOCUS_ALIASES))}")
        return values


@contextmanager
def db():
    path = Path(os.getenv("MARKETLENS_DB_PATH", "marketlens.sqlite3"))
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("CREATE TABLE IF NOT EXISTS profiles (id TEXT PRIMARY KEY, sectors TEXT NOT NULL, research_focus TEXT NOT NULL, horizon_days INTEGER NOT NULL, created_at TEXT NOT NULL)")
    connection.execute("CREATE TABLE IF NOT EXISTS saved_assets (profile_id TEXT NOT NULL, symbol TEXT NOT NULL, saved_at TEXT NOT NULL, PRIMARY KEY(profile_id, symbol), FOREIGN KEY(profile_id) REFERENCES profiles(id))")
    try:
        yield connection
        connection.commit()
    finally:
        connection.close()


def profile_for(profile_id: str) -> dict:
    with db() as connection:
        row = connection.execute("SELECT * FROM profiles WHERE id=?", (profile_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Research profile not found")
        assets = [r[0] for r in connection.execute("SELECT symbol FROM saved_assets WHERE profile_id=? ORDER BY saved_at, symbol", (profile_id,))]
    return {"id": row["id"], "sectors": json.loads(row["sectors"]),
            "research_focus": json.loads(row["research_focus"]),
            "horizon_days": row["horizon_days"], "created_at": row["created_at"],
            "saved_assets": assets}


def clean_symbol(value: str) -> str:
    symbol = value.strip().upper()
    if not SYMBOL.fullmatch(symbol):
        raise HTTPException(422, "Ticker must be 1-12 letters or digits")
    return symbol


async def fetch_asset(symbol: str, horizon_days: int) -> dict:
    """Fixed upstream origin; only the validated ticker and date range vary."""
    base = os.getenv("MARKETLENS_ASSET_API_BASE_URL", "").rstrip("/")
    if not base:
        raise HTTPException(503, "Set MARKETLENS_ASSET_API_BASE_URL to the Team 1 backend origin")
    if not base.startswith(("http://", "https://")):
        raise HTTPException(500, "Invalid upstream base URL")
    key = (base, symbol, horizon_days, date.today().isoformat())
    cached = _cache.get(key)
    if cached and cached[0] > time.monotonic():
        return cached[1]
    end = date.today()
    start = end - timedelta(days=horizon_days)
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await asyncio.wait_for(client.get(f"{base}/api/assets/{symbol}", params={"start": start.isoformat(), "end": end.isoformat()}), 20)
            response.raise_for_status()
            payload = response.json()
    except (httpx.HTTPError, ValueError, TimeoutError) as error:
        raise HTTPException(502, f"Team 1 asset API unavailable for {symbol}: {type(error).__name__}") from error
    if not isinstance(payload, dict) or payload.get("symbol", "").upper() != symbol:
        raise HTTPException(502, "Team 1 asset API returned an invalid asset response")
    payload["_marketlens_retrieved_at"] = datetime.now(timezone.utc).isoformat()
    ttl = max(0, int(os.getenv("MARKETLENS_CACHE_TTL_SECONDS", "300")))
    _cache[key] = (time.monotonic() + ttl, payload)
    return payload


@app.post("/api/profiles", status_code=201)
def create_profile(body: ProfileInput):
    profile_id = str(uuid.uuid4())
    with db() as connection:
        connection.execute("INSERT INTO profiles VALUES (?, ?, ?, ?, datetime('now'))",
                           (profile_id, json.dumps(body.sectors), json.dumps(body.research_focus), body.horizon_days))
    return profile_for(profile_id)


@app.get("/api/profiles/{profile_id}")
def get_profile(profile_id: str):
    return profile_for(profile_id)


@app.put("/api/profiles/{profile_id}")
def update_profile(profile_id: str, body: ProfileInput):
    profile_for(profile_id)
    with db() as connection:
        connection.execute("UPDATE profiles SET sectors=?, research_focus=?, horizon_days=? WHERE id=?",
                           (json.dumps(body.sectors), json.dumps(body.research_focus), body.horizon_days, profile_id))
    return profile_for(profile_id)


@app.put("/api/profiles/{profile_id}/assets/{symbol}")
def save_asset(profile_id: str, symbol: str):
    profile_for(profile_id)
    symbol = clean_symbol(symbol)
    with db() as connection:
        connection.execute("INSERT OR IGNORE INTO saved_assets VALUES (?, ?, datetime('now'))", (profile_id, symbol))
    return profile_for(profile_id)


@app.delete("/api/profiles/{profile_id}/assets/{symbol}")
def remove_asset(profile_id: str, symbol: str):
    profile_for(profile_id)
    with db() as connection:
        connection.execute("DELETE FROM saved_assets WHERE profile_id=? AND symbol=?", (profile_id, clean_symbol(symbol)))
    return profile_for(profile_id)


@app.get("/api/profiles/{profile_id}/discovery")
async def discovery(profile_id: str, limit: int = 5):
    profile = profile_for(profile_id)
    if not 1 <= limit <= 20:
        raise HTTPException(422, "limit must be between 1 and 20")
    raw = os.getenv("MARKETLENS_DISCOVERY_UNIVERSE", "")
    symbols = list(dict.fromkeys(clean_symbol(part) for part in raw.split(",") if part.strip()))
    if not symbols:
        raise HTTPException(503, "Set MARKETLENS_DISCOVERY_UNIVERSE to verified supported tickers")
    results = await asyncio.gather(*(fetch_asset(s, profile["horizon_days"]) for s in symbols), return_exceptions=True)
    payloads = [result for result in results if isinstance(result, dict)]
    errors = [{"symbol": symbol, "error": str(result.detail) if isinstance(result, HTTPException) else type(result).__name__}
              for symbol, result in zip(symbols, results) if isinstance(result, Exception)]
    return {"title": "Your Relevance Findings", "findings": rank_assets(payloads, profile, limit=limit),
            "unavailable_assets": errors, "universe_size": len(symbols)}


@app.get("/api/profiles/{profile_id}/assets")
async def my_assets(profile_id: str):
    profile = profile_for(profile_id)
    symbols = profile["saved_assets"]
    results = await asyncio.gather(*(fetch_asset(s, profile["horizon_days"]) for s in symbols), return_exceptions=True)
    findings = [analyze_asset(result, profile, retrieved_at=result.get("_marketlens_retrieved_at")) for result in results if isinstance(result, dict)]
    errors = [{"symbol": symbol, "error": str(result.detail) if isinstance(result, HTTPException) else type(result).__name__}
              for symbol, result in zip(symbols, results) if isinstance(result, Exception)]
    return {"findings": findings, "unavailable_assets": errors}


@app.get("/api/profiles/{profile_id}/assets/{symbol}/finding")
async def finding_detail(profile_id: str, symbol: str):
    profile = profile_for(profile_id)
    payload = await fetch_asset(clean_symbol(symbol), profile["horizon_days"])
    return analyze_asset(payload, profile, retrieved_at=payload.get("_marketlens_retrieved_at"))


@app.get("/api/profiles/{profile_id}/assets/{symbol}/explanation-context")
async def explanation_context(profile_id: str, symbol: str):
    profile = profile_for(profile_id)
    payload = await fetch_asset(clean_symbol(symbol), profile["horizon_days"])
    finding = analyze_asset(payload, profile, retrieved_at=payload.get("_marketlens_retrieved_at"))
    return build_explanation_context(profile, finding)


@app.get("/api/profiles/{profile_id}/comparison")
async def get_comparison(profile_id: str, limit: int = 5):
    profile = profile_for(profile_id)
    if not 1 <= limit <= 20:
        raise HTTPException(422, "limit must be between 1 and 20")
    universe = list(dict.fromkeys(clean_symbol(s) for s in
        os.getenv("MARKETLENS_DISCOVERY_UNIVERSE", "").split(",") if s.strip()))
    if not universe:
        raise HTTPException(503, "Set MARKETLENS_DISCOVERY_UNIVERSE to verified supported tickers")
    saved = profile["saved_assets"]
    symbols = sorted(set(saved) | set(universe))
    results = await asyncio.gather(*(fetch_asset(s, profile["horizon_days"]) for s in symbols),
                                   return_exceptions=True)
    assets = {s: r for s, r in zip(symbols, results) if isinstance(r, dict)}
    errors = [{"symbol": s, "error": str(r.detail) if isinstance(r, HTTPException) else type(r).__name__}
              for s, r in zip(symbols, results) if isinstance(r, Exception)]
    watchlist = [analyze_asset(assets[s], profile, retrieved_at=assets[s].get("_marketlens_retrieved_at"))
                 for s in saved if s in assets]
    discovery = rank_assets([assets[s] for s in universe if s in assets], profile, limit=limit)
    result = compare_watchlist_discovery(watchlist, discovery).model_dump()
    result.update(unavailable_assets=errors, saved_asset_count=len(saved),
                  universe_size=len(universe), discovery_limit=limit)
    if errors:
        result["limitations"].append("Counts cover successfully loaded assets; unavailable assets are listed separately.")
    return result


@app.post("/api/profiles/{profile_id}/comparison")
async def compare_assets(profile_id: str, body: ComparisonRequest):
    profile = profile_for(profile_id)
    symbols = [clean_symbol(s) for s in body.symbols]
    if len(set(symbols)) != len(symbols):
        raise HTTPException(422, "Comparison symbols must be unique")
    # Fail the request on missing assets instead of silently comparing a subset.
    payloads = await asyncio.gather(*(fetch_asset(s, profile["horizon_days"]) for s in symbols))
    findings = [analyze_asset(p, profile, retrieved_at=p.get("_marketlens_retrieved_at")) for p in payloads]
    return compare_findings(findings).model_dump()

@app.post("/api/profiles/{profile_id}/assets/{symbol}/explain", include_in_schema=False)
@app.post("/api/profiles/{profile_id}/assets/{symbol}/explanation")
async def explain_asset(profile_id: str, symbol: str):
    started = time.monotonic()
    profile = profile_for(profile_id)
    payload = await fetch_asset(clean_symbol(symbol), profile["horizon_days"])
    asset_seconds = time.monotonic() - started
    finding = analyze_asset(payload, profile, retrieved_at=payload.get("_marketlens_retrieved_at"))
    context = build_explanation_context(profile, finding)
    result = await explanations.get(context, explain_finding, namespace=explanation_namespace())
    total = time.monotonic() - started
    result["explanation_meta"].update(asset_seconds=round(asset_seconds, 3), total_seconds=round(total, 3))
    logger.info("MarketLens explanation: symbol=%s source=%s cache=%s asset_s=%.3f generation_s=%.3f total_s=%.3f",
                finding["symbol"], result["explanation_source"], result["explanation_meta"]["cache_hit"],
                asset_seconds, result["explanation_meta"]["generation_seconds"], total)
    return {"finding": finding, **result, "ai_explanation": result["explanation"]}
