import asyncio
import copy
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from marketlens import llm
from marketlens.engine import analyze_asset
from marketlens.grounding import build_explanation_context
from marketlens.schemas import MarketLensExplanation
from marketlens.explanation_service import ExplanationService
from marketlens.evaluation_capture import build_sample, record_generation
from evaluation.dataset import load_samples, validate_sample


def context():
    raw = json.loads((Path(__file__).parent / "fixtures/BBCA_P1_report_only_asset.json").read_text())
    profile = {"sectors": ["Financials"], "research_focus": ["income", "profitability"], "horizon_days": 30}
    return build_explanation_context(profile, analyze_asset(raw, profile))


def answer():
    return MarketLensExplanation(summary="Offline test only: FY2025 ROE was 20.43%.",
                                 why_relevant="Matches income and quality.",
                                 limitations=["TTM precise window end and price basis are unavailable."])


def test_capture_exact_model_input_and_deduplicate(tmp_path, monkeypatch):
    monkeypatch.setenv("MARKETLENS_EVAL_CAPTURE", "1")
    monkeypatch.setenv("MARKETLENS_EVAL_SAMPLES_DIR", str(tmp_path))
    ctx = context()
    args = llm.request_arguments(ctx)
    sample_id = record_generation(ctx, args, answer())
    assert record_generation(ctx, args, answer()) == sample_id
    files = list(tmp_path.glob("*.json"))
    assert len(files) == 1
    sample = validate_sample(json.loads(files[0].read_text()))
    assert sample["retrieved_contexts"][0] == args["contents"].split("\n", 1)[1]
    assert sample["request"]["system_instruction"] == llm.SYSTEM_PROMPT
    assert json.loads(sample["retrieved_contexts"][0])["finding"]["evidence"][0].get("source_ref")
    assert "api_key" not in json.dumps(sample).lower()
    assert "Summary" not in sample["user_input"]
    copy_path = tmp_path / "duplicate.json"
    copy_path.write_text(files[0].read_text())
    samples, invalid, available = load_samples(tmp_path)
    assert len(samples) == available == 1 and not invalid


@pytest.mark.parametrize("field", ["response", "retrieved_contexts", "user_input", "structured_response"])
def test_mismatched_snapshots_are_rejected(field):
    ctx = context()
    sample = build_sample(ctx, llm.request_arguments(ctx), answer())
    sample[field] = {"summary": "changed"} if field == "structured_response" else "changed"
    with pytest.raises((ValueError, TypeError)):
        validate_sample(sample)


def test_capture_failure_does_not_replace_good_answer_with_fallback(tmp_path, monkeypatch):
    monkeypatch.setenv("MARKETLENS_EVAL_CAPTURE", "1")
    blocked = tmp_path / "file-not-directory"
    blocked.write_text("test")
    monkeypatch.setenv("MARKETLENS_EVAL_SAMPLES_DIR", str(blocked))
    client = MagicMock()
    client.models.generate_content.return_value = MagicMock(parsed=answer())
    monkeypatch.setattr(llm, "get_client", lambda: client)
    assert llm.explain_finding(context()) == answer()
    client.close.assert_called_once()


def test_cache_records_one_generation_and_fallback_is_not_a_gemini_sample(tmp_path, monkeypatch):
    monkeypatch.setenv("MARKETLENS_EVAL_CAPTURE", "1")
    monkeypatch.setenv("MARKETLENS_EVAL_SAMPLES_DIR", str(tmp_path))
    client = MagicMock()
    client.aio.models.generate_content = AsyncMock(return_value=MagicMock(parsed=answer()))
    client.aio.aclose = AsyncMock()
    monkeypatch.setattr(llm, "get_client", lambda: client)
    async def run():
        service = ExplanationService()
        first = await service.get(context(), llm.explain_finding_async, namespace="capture-test")
        # Reuse the exact context; timestamps must not be rebuilt in a real call.
        ctx = context()
        await service.get(ctx, llm.explain_finding_async, namespace="shared")
        second = await service.get(ctx, llm.explain_finding_async, namespace="shared")
        assert first["explanation_source"] == "gemini" and second["explanation_meta"]["cache_hit"]
        before = len(list(tmp_path.glob("*.json")))
        async def failed(_): raise RuntimeError("offline provider failure")
        fallback = await service.get(ctx, failed, namespace="failed")
        assert fallback["explanation_source"] == "deterministic_fallback"
        assert len(list(tmp_path.glob("*.json"))) == before
        await service.close()
    asyncio.run(run())
    assert client.aio.models.generate_content.await_count == 2
    assert len(list(tmp_path.glob("*.json"))) in (1, 2)


def test_disabled_capture_and_invalid_file_are_handled(tmp_path, monkeypatch):
    monkeypatch.setenv("MARKETLENS_EVAL_SAMPLES_DIR", str(tmp_path))
    assert record_generation(context(), {}, answer()) is None
    (tmp_path / "corrupt.json").write_text("broken")
    samples, invalid, available = load_samples(tmp_path)
    assert not samples and available == 0 and len(invalid) == 1
