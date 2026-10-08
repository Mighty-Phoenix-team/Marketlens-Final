import copy
import json
from pathlib import Path

from fastapi.testclient import TestClient

from marketlens import api
from marketlens.schemas import MarketLensExplanation


SAMPLE = json.loads((Path(__file__).resolve().parents[1] / "sample_payload_BBCA.json").read_text())


def test_profile_assets_and_shared_engine(tmp_path, monkeypatch):
    monkeypatch.setenv("MARKETLENS_DB_PATH", str(tmp_path / "profiles.sqlite3"))
    monkeypatch.setenv("MARKETLENS_DISCOVERY_UNIVERSE", "BBCA")

    async def fake_fetch(symbol, horizon_days):
        payload = copy.deepcopy(SAMPLE)
        payload["_marketlens_retrieved_at"] = "2026-09-23T00:00:00Z"
        return payload

    monkeypatch.setattr(api, "fetch_asset", fake_fetch)
    client = TestClient(api.app)
    profile = client.post("/api/profiles", json={"sectors": ["Financials"], "research_focus": ["growth"], "horizon_days": 30}).json()
    profile_id = profile["id"]
    assert client.put(f"/api/profiles/{profile_id}/assets/BBCA").status_code == 200
    discovery = client.get(f"/api/profiles/{profile_id}/discovery").json()["findings"][0]
    assets = client.get(f"/api/profiles/{profile_id}/assets").json()["findings"][0]
    assert discovery == assets
    assert client.get(f"/api/profiles/{profile_id}").json()["saved_assets"] == ["BBCA"]
    assert client.delete(f"/api/profiles/{profile_id}/assets/BBCA").json()["saved_assets"] == []


def test_profile_horizon_respects_team1_series_limit(tmp_path, monkeypatch):
    monkeypatch.setenv("MARKETLENS_DB_PATH", str(tmp_path / "profiles.sqlite3"))
    client = TestClient(api.app)
    body = {"sectors": [], "research_focus": [], "horizon_days": 91}
    assert client.post("/api/profiles", json=body).status_code == 422
    body["horizon_days"] = 90
    assert client.post("/api/profiles", json=body).status_code == 201


def test_explanation_context_uses_only_structured_finding(tmp_path, monkeypatch):
    monkeypatch.setenv("MARKETLENS_DB_PATH", str(tmp_path / "profiles.sqlite3"))

    async def fake_fetch(symbol, horizon_days):
        payload = copy.deepcopy(SAMPLE)
        payload["_marketlens_retrieved_at"] = "2026-09-23T00:00:00Z"
        return payload

    monkeypatch.setattr(api, "fetch_asset", fake_fetch)
    client = TestClient(api.app)
    profile = client.post("/api/profiles", json={"sectors": ["Financials"], "research_focus": ["growth"], "horizon_days": 30}).json()
    path = f"/api/profiles/{profile['id']}/assets/BBCA"
    finding = client.get(f"{path}/finding").json()
    context = client.get(f"{path}/explanation-context").json()
    assert context["finding"]["evidence"] == finding["evidence"]
    assert context["finding"]["limitations"] == finding["limitations"]
    assert context["evidence_boundary"]["causal_explanation_available"] is False
    assert context["evidence_boundary"]["document_context_available"] is False
    assert "api_key" not in str(context).lower()


def test_explanation_failure_returns_grounded_fallback_without_changing_finding(tmp_path, monkeypatch):
    monkeypatch.setenv("MARKETLENS_DB_PATH", str(tmp_path / "profiles.sqlite3"))

    async def fake_fetch(symbol, horizon_days):
        payload = copy.deepcopy(SAMPLE)
        payload["_marketlens_retrieved_at"] = "2026-09-23T00:00:00Z"
        return payload

    def unavailable(context):
        raise RuntimeError("mock provider failure; must not be exposed")

    monkeypatch.setattr(api, "fetch_asset", fake_fetch)
    monkeypatch.setattr(api, "explain_finding", unavailable)
    with TestClient(api.app) as client:
        profile = client.post("/api/profiles", json={"research_focus": ["growth"]}).json()
        path = f"/api/profiles/{profile['id']}/assets/BBCA"
        finding = client.get(f"{path}/finding").json()
        for suffix in ["explanation", "explain"]:
            response = client.post(f"{path}/{suffix}")
            assert response.status_code == 200
            body = response.json()
            assert body["finding"] == finding
            assert body["explanation_source"] == "deterministic_fallback"
            assert body["explanation"] == body["ai_explanation"]
            assert "mock provider failure" not in response.text
            for metric, text in zip(finding["evidence"], body["explanation"]["evidence_summary"], strict=True):
                assert metric["metric"] in text
                assert str(metric["value"]) in text
                assert metric["source"] in text
                assert metric["period"] in text


def test_successful_explanation_uses_existing_response_contract(tmp_path, monkeypatch):
    monkeypatch.setenv("MARKETLENS_DB_PATH", str(tmp_path / "profiles.sqlite3"))

    async def fake_fetch(symbol, horizon_days):
        return copy.deepcopy(SAMPLE)

    def explanation(context):
        assert context["finding"]["evidence"]
        return MarketLensExplanation(summary="Evidence-based summary", why_relevant="Matches research focus")

    monkeypatch.setattr(api, "fetch_asset", fake_fetch)
    monkeypatch.setattr(api, "explain_finding", explanation)
    with TestClient(api.app) as client:
        profile = client.post("/api/profiles", json={"research_focus": ["growth"]}).json()
        response = client.post(f"/api/profiles/{profile['id']}/assets/BBCA/explanation")
    assert response.status_code == 200
    assert response.json()["explanation_source"] == "gemini"
    assert response.json()["explanation"]["summary"] == "Evidence-based summary"
