import copy
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from marketlens import api, llm
from marketlens.engine import analyze_asset, rank_assets
from marketlens.grounding import build_explanation_context
from marketlens.fallback import build_fallback_explanation
from marketlens.formatting import format_value


PAYLOAD = json.loads((Path(__file__).parent / "fixtures/BBCA_report_only_asset.json").read_text())
PROFILE = {"sectors": ["Financials"], "research_focus": ["valuation", "profitability"], "horizon_days": 30}
STAMP = PAYLOAD["company"]["retrieved_at"]


def finding(payload=None, profile=None):
    return analyze_asset(payload or PAYLOAD, profile or PROFILE, retrieved_at=STAMP)


def metrics(result):
    return {item["metric"]: item for item in result["evidence"]}


def test_real_payload_produces_p0_evidence_with_correct_units_and_years():
    result = finding()
    data = metrics(result)
    assert result["signal_groups"] == ["fundamental", "valuation", "quality"]
    assert data["pe"]["value"] == pytest.approx(12.757326518681)
    assert data["pe"]["observed_at"] == "2026"
    assert data["roe"]["observed_at"] == "2025"
    assert format_value(data["roe"]) == "20.43%"
    assert format_value(data["roa"]) == "3.63%"
    assert format_value(data["roe_change"]) == "+0.26 pp"
    assert data["roe_change"]["value"] == pytest.approx(0.20425924389879418 - 0.2016795292003015, abs=1e-8)
    assert data["forward_pe"]["kind"] == "estimate"
    assert data["forward_pe"]["observed_at"] is None
    assert data["pe_vs_history"]["baseline"] == pytest.approx((23.5858451556753 + 21.5324363605918) / 2)
    assert data["pe_vs_peer"]["baseline"] == pytest.approx(8.72390054311121)
    assert not any(item["group"] == "market_activity" for item in result["evidence"])
    assert result["methodology_version"] == "2.1-income"
    assert result["relevance_reason"]["availability_factor"] == 3 / 6


def test_p0_only_reads_normalized_contract_and_keeps_source_retrieval_time():
    payload = copy.deepcopy(PAYLOAD)
    payload["company"]["valuation"] = {"pe": 99999999}
    payload["company"]["financials"] = {"roe": 99999999}
    result = analyze_asset(payload, PROFILE, retrieved_at="2030-01-01T00:00:00Z")
    p0 = [e for e in result["evidence"] if e["group"] in {"valuation", "quality"}]
    assert next(e["value"] for e in p0 if e["metric"] == "roe") == pytest.approx(0.20425924)
    assert all(e["retrieved_at"] == STAMP for e in p0)
    assert all(e["source"] == PAYLOAD["company"]["source_endpoint"] for e in p0)


def test_profitability_and_valuation_focus_affect_score_without_changing_evidence():
    quality = finding(profile={"research_focus": ["profitability"]})
    valuation = finding(profile={"research_focus": ["valuation"]})
    assert quality["evidence"] == valuation["evidence"]
    assert quality["research_relevance"] != valuation["research_relevance"]
    assert quality["relevance_reason"]["matched_groups"] == ["quality"]
    assert finding(profile={"research_focus": ["quality"]}) == quality
    timestamped = {**PAYLOAD, "_marketlens_retrieved_at": STAMP}
    assert rank_assets([timestamped], PROFILE) == rank_assets([timestamped], PROFILE)


def test_nonpositive_multiples_stay_visible_but_cannot_create_ratio_gaps():
    payload = copy.deepcopy(PAYLOAD)
    latest = payload["company"]["intelligence"]["valuation"]["latest"]
    latest.update(pe=-5, pb=0, pe_peer_avg=0, pb_peer_avg=-1)
    data = metrics(finding(payload))
    assert data["pe"]["value"] == -5
    assert data["pb"]["value"] == 0
    assert data["pe"]["strength"] == data["pb"]["strength"] == 0.25
    assert all(name not in data for name in ["pe_vs_history", "pe_vs_peer", "pb_vs_history", "pb_vs_peer"])


def test_missing_and_nonfinite_ratios_do_not_become_zero_or_inherit_older_values():
    payload = copy.deepcopy(PAYLOAD)
    quality = payload["company"]["intelligence"]["quality"]
    quality["latest"].update(roe=None, roa=float("nan"), net_profit_margin=True, operating_profit_margin=0)
    data = metrics(finding(payload))
    assert all(name not in data for name in ["roe", "roe_change", "roa", "roa_change", "net_profit_margin"])
    assert data["operating_profit_margin"]["value"] == 0
    quality["history"] = [row for row in quality["history"] if row["year"] != 2024]
    assert "operating_profit_margin_change" not in metrics(finding(payload))


def test_old_contract_is_accepted_without_inventing_p0_or_dropping_old_fields():
    payload = copy.deepcopy(PAYLOAD)
    del payload["company"]["intelligence"]
    result = finding(payload)
    assert result["signal_groups"] == ["fundamental"]
    assert "revenue_growth" in metrics(result)
    assert any("contract version 1.0" in s for s in result["limitations"])
    assert all(field in result for field in ["id", "symbol", "research_relevance", "evidence", "observation", "relevance_reason", "source_endpoints"])


def test_grounding_and_fallback_preserve_p0_facts_and_boundaries():
    result = finding()
    context = build_explanation_context(PROFILE, result)
    assert context["finding"]["evidence"] == result["evidence"]
    assert context["finding"]["methodology_version"] == "2.1-income"
    assert "percentage points" in " ".join(context["evidence_boundary"]["instructions"])
    fallback = build_fallback_explanation(context)
    text = " ".join(fallback.evidence_summary)
    assert "roe: 20.43%" in text and "2025" in text
    assert "roe_change: +0.26 pp" in text
    assert "forward_pe: 12.59×" in text
    assert all(item in fallback.limitations for item in result["limitations"])


def test_new_profile_api_and_explanation_are_consistent_with_engine(tmp_path, monkeypatch):
    monkeypatch.setenv("MARKETLENS_DB_PATH", str(tmp_path / "profiles.sqlite3"))

    async def fetch(symbol, horizon):
        payload = copy.deepcopy(PAYLOAD)
        payload["_marketlens_retrieved_at"] = STAMP
        return payload

    def no_llm(context):
        assert {"valuation", "quality"}.issubset(context["finding"]["signal_groups"])
        raise RuntimeError("offline LLM unavailable")

    monkeypatch.setattr(api, "fetch_asset", fetch)
    monkeypatch.setattr(api, "explain_finding", no_llm)
    with TestClient(api.app) as client:
        response = client.post("/api/profiles", json=PROFILE)
        assert response.status_code == 201
        root = f"/api/profiles/{response.json()['id']}/assets/BBCA"
        detail = client.get(root + "/finding").json()
        result = client.post(root + "/explanation").json()
        assert detail == result["finding"] == finding()
        assert result["explanation_source"] == "deterministic_fallback"
        assert "20.43%" in " ".join(result["explanation"]["evidence_summary"])


def test_gemini_request_is_grounded_in_new_evidence_and_never_changes_score(monkeypatch):
    from unittest.mock import MagicMock
    client = MagicMock()
    response = MagicMock()
    response.parsed = {"summary": "Recorded valuation and quality context", "why_relevant": "Matches selected research focus"}
    client.models.generate_content.return_value = response
    monkeypatch.setattr(llm, "get_client", lambda: client)
    result = finding()
    before = copy.deepcopy(result)
    context = build_explanation_context(PROFILE, result)
    llm.explain_finding(context)
    prompt = client.models.generate_content.call_args.kwargs["contents"]
    for term in ["roe", "forward_pe", "2025", "2026", "percentage points", "2.1-income"]:
        assert term in prompt
    assert result == before
