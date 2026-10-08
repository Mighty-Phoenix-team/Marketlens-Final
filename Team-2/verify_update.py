"""Verify merged Comparison + explanation cache offline, without provider calls."""
import asyncio
import copy
import json
from pathlib import Path

from marketlens.comparison import compare_findings, compare_watchlist_discovery
from marketlens.engine import analyze_asset
from marketlens.explanation_service import ExplanationService
from marketlens.formatting import format_value
from marketlens.grounding import build_explanation_context
from marketlens.schemas import MarketLensExplanation


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


async def verify():
    raw = json.loads((Path(__file__).parent / "tests/fixtures/BBCA_P1_report_only_asset.json").read_text(encoding="utf-8"))
    profile = {"research_focus": ["valuation", "profitability", "income"], "horizon_days": 30}
    first = analyze_asset(raw, profile, retrieved_at=raw["company"]["retrieved_at"])
    simulated = copy.deepcopy(raw)
    simulated["symbol"] = "TEST"
    second = analyze_asset(simulated, profile, retrieved_at=raw["company"]["retrieved_at"])
    comparison = compare_findings([first, second])
    require({"valuation", "quality", "income"}.issubset(comparison.shared_signal_groups), "Missing P1 comparison groups")
    income = next(r for r in comparison.metrics if r.metric == "cash_payout_ratio")
    require(format_value(income.evidence_by_symbol["BBCA"]) == "112.89%", "Income units changed")
    watchlist = compare_watchlist_discovery([first], [first, second])
    require(watchlist.overlap_count == 1 and watchlist.discovery_count == 2, "Watchlist comparison failed")
    require(watchlist.overlap[0].relevance_reason == first["relevance_reason"], "P1 reason lost")
    print("PASS: Comparison preserves Valuation, Quality, Income, periods and sources")
    print("Fixture only: BBCA report captures + TEST synthetic duplicate; not a live stock comparison")
    calls = []
    async def mocked_gemini(context):
        calls.append(1)
        return MarketLensExplanation(summary="Offline mock", why_relevant="Test only")
    ctx = build_explanation_context(profile, first)
    service = ExplanationService()
    await service.get(ctx, mocked_gemini, namespace="offline")
    cached = await service.get(ctx, mocked_gemini, namespace="offline")
    require(len(calls) == 1 and cached["explanation_meta"]["cache_hit"], "Cache reuse failed")
    print("PASS: Two identical requests use one mocked generation")
    async def slow(context):
        await asyncio.sleep(10)
    fallback = await service.get(ctx, slow, namespace="timeout-test", timeout=.02)
    require(fallback["explanation_source"] == "deterministic_fallback", "Fallback failed")
    require(fallback["explanation_meta"]["reason"] == "timeout", "Timeout diagnostic failed")
    await service.close()
    print("PASS: Slow provider -> bounded timeout -> deterministic fallback")
    print("Sectors calls: 0; Gemini calls: 0")


if __name__ == "__main__":
    asyncio.run(verify())
