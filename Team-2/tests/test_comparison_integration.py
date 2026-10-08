import copy
import json
from pathlib import Path

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from marketlens import api
from marketlens.engine import analyze_asset
from marketlens.comparison import compare_findings
from marketlens.formatting import format_value

PAYLOAD = json.loads((Path(__file__).parent / "fixtures/BBCA_P1_report_only_asset.json").read_text())
PROFILE = {"research_focus": ["valuation", "profitability", "income"], "sectors": ["Financials"]}


def make_finding(symbol):
    data = copy.deepcopy(PAYLOAD)
    data["symbol"] = symbol  # TEST is a synthetic fixture, never a live company claim.
    return analyze_asset(data, PROFILE, retrieved_at=PAYLOAD["company"]["retrieved_at"])


def test_p1_comparison_retains_units_periods_sources_and_groups():
    a, b = make_finding("BBCA"), make_finding("TEST")
    b["evidence"] = [e for e in b["evidence"] if e["metric"] != "payout_ratio"]
    next(e for e in b["evidence"] if e["metric"] == "roe")["period"] = "Annual financial ratio, 2024"
    result = compare_findings([a, b]).model_dump()
    assert {"valuation", "quality", "income"}.issubset(result["shared_signal_groups"])
    assert result["assets"][0]["signal_groups"] == a["signal_groups"]
    assert result["assets"][0]["signal_group"] == a["signal_groups"]
    rows = {r["metric"]: r for r in result["metrics"]}
    assert rows["roe"]["period_status"] == "different_periods"
    assert rows["payout_ratio"]["values"]["TEST"] is None
    assert rows["payout_ratio"]["missing_symbols"] == ["TEST"]
    assert format_value(rows["cash_payout_ratio"]["evidence_by_symbol"]["BBCA"]) == "112.89%"
    for row in result["metrics"]:
        for symbol, evidence in row["evidence_by_symbol"].items():
            if evidence: assert evidence["source"] and evidence["period"] and evidence["retrieved_at"]


def test_nonfinite_missing_values_and_normalized_symbols():
    a, b = make_finding("bbca"), make_finding("TEST")
    a["evidence"][0]["value"] = float("nan")
    a["evidence"][1]["value"] = True
    result = compare_findings([a, b])
    assert result.symbols == ["BBCA", "TEST"]
    assert next(r for r in result.metrics if r.metric == "revenue_growth").values["BBCA"] is None


def test_watchlist_comparison_api_shares_engine_and_reports_unavailable(tmp_path, monkeypatch):
    monkeypatch.setenv("MARKETLENS_DB_PATH", str(tmp_path / "profiles.sqlite3"))
    monkeypatch.setenv("MARKETLENS_DISCOVERY_UNIVERSE", "BBCA,TEST,BAD,B BCA")
    calls = []
    async def fetch(symbol, horizon):
        calls.append(symbol)
        if symbol == "BAD": raise HTTPException(502, "Fixture upstream unavailable")
        data = copy.deepcopy(PAYLOAD)
        data["symbol"] = symbol
        data["_marketlens_retrieved_at"] = PAYLOAD["company"]["retrieved_at"]
        return data
    monkeypatch.setattr(api, "fetch_asset", fetch)
    with TestClient(api.app) as client:
        profile = client.post("/api/profiles", json=PROFILE).json()
        root = f"/api/profiles/{profile['id']}"
        client.put(root + "/assets/BBCA")
        client.put(root + "/assets/BAD")
        assert client.get(root + "/comparison").status_code == 422
        assert calls == []
        monkeypatch.setenv("MARKETLENS_DISCOVERY_UNIVERSE", "BBCA,TEST,BBCA,BAD")
        result = client.get(root + "/comparison").json()
        assert calls == ["BAD", "BBCA", "TEST"]
        assert result["saved_asset_count"] == 2 and result["watchlist_count"] == 1
        assert result["overlap_count"] == 1
        assert result["unavailable_assets"][0]["symbol"] == "BAD"
        overlap = result["overlap"][0]
        finding = client.get(root + "/assets/BBCA/finding").json()
        assert overlap["relevance_reason"] == finding["relevance_reason"]
        assert overlap["evidence"] == finding["evidence"]
        assert overlap["research_relevance"] == finding["research_relevance"]
        matrix = client.post(root + "/comparison", json={"symbols": ["BBCA", "TEST"]}).json()
        assert matrix["assets"][0]["research_relevance"] == finding["research_relevance"]
        before = len(calls)
        assert client.post(root + "/comparison", json={"symbols": ["BBCA", "bbca"]}).status_code == 422
        assert len(calls) == before
