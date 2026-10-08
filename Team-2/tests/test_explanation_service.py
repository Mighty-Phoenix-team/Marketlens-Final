import asyncio
import copy
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
from fastapi.testclient import TestClient

from marketlens import api, llm
from marketlens.engine import analyze_asset
from marketlens.grounding import build_explanation_context, compact_explanation_context
from marketlens.explanation_service import ExplanationService
from marketlens.schemas import MarketLensExplanation

PAYLOAD = json.loads((Path(__file__).parent / "fixtures/BBCA_P1_report_only_asset.json").read_text())
PROFILE = {"research_focus": ["valuation", "profitability", "income"], "sectors": ["Financials"], "horizon_days": 30}


def context():
    finding = analyze_asset(PAYLOAD, PROFILE, retrieved_at=PAYLOAD["company"]["retrieved_at"])
    return build_explanation_context(PROFILE, finding)


def answer():
    return MarketLensExplanation(summary="Recorded evidence", why_relevant="Matches the profile")


def test_cache_coalesces_calls_invalidates_changes_and_expires():
    async def run():
        now = [100.0]
        service = ExplanationService(clock=lambda: now[0])
        calls = []
        async def generate(data):
            calls.append(data)
            await asyncio.sleep(0.01)
            return answer()
        ctx = context()
        results = await asyncio.gather(*(service.get(ctx, generate, namespace="test") for _ in range(3)))
        assert len(calls) == 1
        assert sum(r["explanation_meta"]["coalesced"] for r in results) == 2
        second = await service.get(ctx, generate, namespace="test")
        assert second["explanation_meta"]["cache_hit"] and len(calls) == 1
        second["explanation"]["summary"] = "mutated caller copy"
        assert (await service.get(ctx, generate, namespace="test"))["explanation"]["summary"] == "Recorded evidence"
        for changed in ["profile", "evidence", "period", "source", "timestamp", "methodology"]:
            other = copy.deepcopy(ctx)
            if changed == "profile": other["research_profile"]["research_focus"] = ["income"]
            elif changed == "methodology": other["finding"]["methodology_version"] = "new-version"
            else:
                field = {"evidence": "value", "period": "period", "source": "source", "timestamp": "retrieved_at"}[changed]
                other["finding"]["evidence"][0][field] = 123 if field == "value" else "changed"
            result = await service.get(other, generate, namespace="test")
            assert not result["explanation_meta"]["cache_hit"]
        await service.get(ctx, generate, namespace="new-prompt-or-model")
        assert len(calls) == 8
        now[0] += 3601
        await service.get(ctx, generate, namespace="test")
        assert len(calls) == 9
        await service.close()
    asyncio.run(run())


def test_timeout_cancels_async_provider_and_cools_down():
    async def run():
        now = [100.0]
        service = ExplanationService(clock=lambda: now[0])
        cancelled = asyncio.Event()
        calls = []
        async def never(data):
            calls.append(1)
            try:
                await asyncio.sleep(10)
            finally:
                cancelled.set()
        ctx = context()
        result = await service.get(ctx, never, namespace="test", timeout=.02)
        assert cancelled.is_set()
        assert result["explanation_source"] == "deterministic_fallback"
        assert result["explanation_meta"]["reason"] == "timeout"
        assert service.inflight == {}
        assert (await service.get(ctx, never, namespace="test"))["explanation_meta"]["cache_hit"]
        assert len(calls) == 1
        now[0] += 31
        async def success(data): return answer()
        assert (await service.get(ctx, success, namespace="test"))["explanation_source"] == "gemini"
    asyncio.run(run())


def test_disconnected_waiter_does_not_cancel_shared_job():
    async def run():
        service = ExplanationService()
        ready = asyncio.Event()
        async def generate(data):
            await ready.wait()
            return answer()
        first = asyncio.create_task(service.get(context(), generate, namespace="test"))
        second = asyncio.create_task(service.get(context(), generate, namespace="test"))
        await asyncio.sleep(0)
        first.cancel()
        with pytest.raises(asyncio.CancelledError): await first
        ready.set()
        assert (await second)["explanation_source"] == "gemini"
        assert not service.inflight
    asyncio.run(run())


def test_compact_context_preserves_all_facts_and_resolvable_sources():
    original = context()
    before = copy.deepcopy(original)
    compact = compact_explanation_context(original)
    for old, new in zip(original["finding"]["evidence"], compact["finding"]["evidence"], strict=True):
        reconstructed = dict(new)
        if "source_ref" in reconstructed:
            reconstructed.update(compact["evidence_sources"][reconstructed.pop("source_ref")])
        for key, value in old.items():
            if key not in {"strength", "strength_method"}:
                assert reconstructed[key] == value
    assert compact["finding"]["limitations"] == original["finding"]["limitations"]
    assert original == before
    assert len(json.dumps(compact)) < len(json.dumps(original))


def test_api_cache_diagnostics_and_score_unchanged(tmp_path, monkeypatch):
    monkeypatch.setenv("MARKETLENS_DB_PATH", str(tmp_path / "profiles.sqlite3"))
    monkeypatch.setattr(api, "explanations", ExplanationService())
    calls = []
    async def fetch(symbol, horizon):
        data = copy.deepcopy(PAYLOAD)
        data["_marketlens_retrieved_at"] = PAYLOAD["company"]["retrieved_at"]
        return data
    async def generate(ctx):
        calls.append(ctx)
        return answer()
    monkeypatch.setattr(api, "fetch_asset", fetch)
    monkeypatch.setattr(api, "explain_finding", generate)
    with TestClient(api.app) as client:
        profile = client.post("/api/profiles", json=PROFILE).json()
        path = f"/api/profiles/{profile['id']}/assets/BBCA"
        finding = client.get(path + "/finding").json()
        first = client.post(path + "/explanation").json()
        second = client.post(path + "/explain").json()
        assert len(calls) == 1
        assert first["finding"] == second["finding"] == finding
        assert second["explanation_meta"]["cache_hit"]
        assert all(k in first["explanation_meta"] for k in ["asset_seconds", "total_seconds", "generation_seconds"])


def test_provider_rate_limit_is_classified_without_exposing_secret_details():
    class Limited(Exception):
        code = 429
    async def run():
        service = ExplanationService()
        async def generate(ctx): raise Limited("PRIVATE request details")
        result = await service.get(context(), generate, namespace="test")
        assert result["explanation_meta"]["reason"] == "rate_limited"
        assert result["explanation_meta"]["provider_status"] == 429
        assert "PRIVATE" not in json.dumps(result)
    asyncio.run(run())


def test_sdk_async_path_closes_client_and_uses_same_schema(monkeypatch):
    client = MagicMock()
    client.aio.models.generate_content = AsyncMock(return_value=MagicMock(parsed=answer()))
    client.aio.aclose = AsyncMock()
    monkeypatch.setattr(llm, "get_client", lambda: client)
    assert asyncio.run(llm.explain_finding_async(context())) == answer()
    client.aio.aclose.assert_awaited_once()
    client.close.assert_called_once()
    assert client.aio.models.generate_content.call_args.kwargs["config"].response_schema is MarketLensExplanation


def test_sdk_timeout_and_single_attempt_are_explicit(monkeypatch):
    constructor = MagicMock()
    monkeypatch.setenv("GEMINI_API_KEY", "test-only-not-a-real-key")
    monkeypatch.setenv("MARKETLENS_EXPLANATION_TIMEOUT_SECONDS", "60")
    monkeypatch.setattr(llm.genai, "Client", constructor)
    llm.get_client()
    options = constructor.call_args.kwargs["http_options"]
    assert options.timeout == 60000
    assert options.retry_options.attempts == 1
