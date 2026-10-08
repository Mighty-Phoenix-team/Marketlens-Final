"""Exercise REAL pinned Ragas metric classes with controlled, offline model replies."""
import asyncio
import csv
import json
import os
import importlib.util
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

os.environ["RAGAS_DO_NOT_TRACK"] = "true"
os.environ["LANGCHAIN_TRACING_V2"] = "false"
os.environ["LANGSMITH_TRACING"] = "false"
if importlib.util.find_spec("ragas") is None:
    pytest.skip("Optional evaluator environment is not installed", allow_module_level=True)
import ragas

from evaluation.judge import GeminiJudge, make_metrics
from evaluation.run import score_sample, error_label
from evaluation.report import write_reports, summaries
from marketlens.evaluation_capture import build_sample
from marketlens.llm import request_arguments
from marketlens.schemas import MarketLensExplanation


def sample():
    context = {"research_profile": {"research_focus": ["income"]}, "finding": {
        "symbol": "TEST", "research_relevance": 4.17,
        "relevance_reason": {"matched_groups": ["income"]},
        "evidence": [{"metric": "dividend_yield_ttm", "value": 0.0625, "unit": "decimal_ratio"}],
        "limitations": ["TTM window end and price basis are unavailable."]}}
    answer = MarketLensExplanation(summary="The test asset has TTM yield 6.25%.", why_relevant="Matches income.")
    return build_sample(context, request_arguments(context), answer)


def judge_with_outputs(outputs, *, max_calls=30):
    client = MagicMock()
    async def generate(**kwargs):
        value = outputs.pop(0)
        if isinstance(value, BaseException):
            raise value
        return SimpleNamespace(text=json.dumps(value), model_version="offline-mock-judge",
                               candidates=[SimpleNamespace(finish_reason="STOP")])
    client.aio.models.generate_content = AsyncMock(side_effect=generate)
    client.aio.aclose = AsyncMock()
    return GeminiJudge("test-only", "offline-test-model", client=client, max_calls=max_calls)


def replies():
    return [
        {"statements": ["The test asset has TTM yield 6.25%.", "The asset matches income."]},
        {"statements": [
            {"statement": "The test asset has TTM yield 6.25%.", "reason": "In context.", "verdict": 1},
            {"statement": "The asset matches income.", "reason": "In matched groups.", "verdict": 1}]},
        {"reason": "Both mandatory TTM caveats were omitted.", "verdict": 0},
        {"reason": "Income is a matched group.", "verdict": 1},
    ]


def test_real_ragas_metrics_and_cached_rerun(tmp_path):
    judge = judge_with_outputs(replies())
    metrics = make_metrics(judge)
    async def run():
        first, stop = await score_sample(sample(), metrics, judge, model=judge.model, version="0.4.3",
                                         cache_dir=tmp_path, timeout=10)
        assert not stop
        assert {n: c["score"] for n, c in first["metrics"].items()} == {
            "faithfulness": 1.0, "limitation_retention": 0, "profile_alignment": 1}
        assert judge.calls == 4
        second, stop = await score_sample(sample(), metrics, judge, model=judge.model, version="0.4.3",
                                          cache_dir=tmp_path, timeout=10)
        assert judge.calls == 4 and all(c["cached"] for c in second["metrics"].values())
        assert first["metrics"]["limitation_retention"]["trace"][0]["output"]["verdict"] == 0
        await judge.close()
    asyncio.run(run())


def test_unsupported_claim_changes_real_faithfulness_score(tmp_path):
    outputs = replies()
    outputs[1]["statements"][1]["verdict"] = 0
    outputs[1]["statements"][1]["reason"] = "Controlled unsupported claim."
    judge = judge_with_outputs(outputs)
    async def run():
        row, _ = await score_sample(sample(), make_metrics(judge), judge, model=judge.model, version="0.4.3",
                                    cache_dir=tmp_path, timeout=10)
        assert row["metrics"]["faithfulness"]["score"] == .5
        await judge.close()
    asyncio.run(run())


def test_zero_claims_are_unscored_not_perfect(tmp_path):
    judge = judge_with_outputs([{"statements": []}])
    async def run():
        metrics = {"faithfulness": make_metrics(judge)["faithfulness"]}
        row, _ = await score_sample(sample(), metrics, judge, model=judge.model, version="0.4.3",
                                    cache_dir=tmp_path, timeout=10)
        assert row["metrics"]["faithfulness"]["score"] is None
        assert row["metrics"]["faithfulness"]["status"] == "unscored"
        await judge.close()
    asyncio.run(run())


def test_call_budget_and_timeout_do_not_become_zero_scores(tmp_path):
    judge = judge_with_outputs(replies(), max_calls=1)
    async def run():
        row, stop = await score_sample(sample(), make_metrics(judge), judge, model=judge.model, version="0.4.3",
                                       cache_dir=tmp_path, timeout=10)
        assert stop and judge.calls == 1
        assert row["metrics"]["faithfulness"]["score"] is None
        assert row["metrics"]["limitation_retention"]["status"] == "not_run"
        await judge.close()
    asyncio.run(run())
    assert error_label(TimeoutError()) == "timeout"


def test_rate_limit_stops_and_is_not_automatically_retried(tmp_path):
    class Limited(RuntimeError):
        code = 429
    judge = judge_with_outputs([Limited("SECRET error text must not appear in reports")])
    async def run():
        row, stop = await score_sample(sample(), make_metrics(judge), judge, model=judge.model, version="0.4.3",
                                       cache_dir=tmp_path, timeout=10)
        assert stop and judge.calls == 1
        assert row["metrics"]["faithfulness"]["error"] == "rate_limited"
        assert "SECRET" not in json.dumps(row)
        again, stop = await score_sample(sample(), make_metrics(judge), judge, model=judge.model, version="0.4.3",
                                         cache_dir=tmp_path, timeout=10)
        assert stop and judge.calls == 1
        assert again["metrics"]["faithfulness"]["cached"]
        await judge.close()
    asyncio.run(run())


def test_report_excludes_errors_from_means_and_escapes_content(tmp_path):
    row = {**sample(), "evaluation_model": "offline-test-model", "metrics": {
        "faithfulness": {"score": 0.5, "status": "ok"},
        "limitation_retention": {"score": None, "status": "error", "error": "timeout"}}}
    row["response"] = "<script>alert(1)</script>"
    metrics = ["faithfulness", "limitation_retention"]
    summary = summaries([row], metrics)
    assert summary["limitation_retention"]["mean"] is None
    run = {"created_at": "offline-test", "evaluation_model": "offline-test-model", "ragas_version": "0.4.3",
           "criteria_version": "test", "metrics": metrics, "api_calls": 0, "max_calls": 30,
           "available_samples": 1, "invalid_files": []}
    report = write_reports(tmp_path, run, [row])
    text = report.read_text()
    assert "<script>" not in text and "&lt;script&gt;" in text
    assert "0 scored / 1 unscored" in text
    with (tmp_path / "results.csv").open(encoding="utf-8-sig") as f:
        result = next(csv.DictReader(f))
    assert result["faithfulness"] == "0.5" and result["limitation_retention"] == ""
