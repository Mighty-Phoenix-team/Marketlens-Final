"""Interactive dashboard smoke checks with no server/provider requests."""
import copy
import json
from pathlib import Path

from streamlit.testing.v1 import AppTest

from dashboard import api_client
from marketlens.engine import analyze_asset
from marketlens.comparison import compare_findings, compare_watchlist_discovery

ROOT = Path(__file__).resolve().parents[1]
PAYLOAD = json.loads((ROOT / "tests/fixtures/BBCA_P1_report_only_asset.json").read_text())
PROFILE = {"id": "offline-profile", "research_focus": ["valuation", "profitability", "income"],
           "sectors": ["Financials"], "horizon_days": 30}


def finding(symbol):
    data = copy.deepcopy(PAYLOAD)
    data["symbol"] = symbol
    return analyze_asset(data, PROFILE, retrieved_at=data["company"]["retrieved_at"])


def test_comparison_navigation_and_p1_table(monkeypatch):
    first, second = finding("BBCA"), finding("TEST")
    comparison = compare_watchlist_discovery([first], [first, second]).model_dump()
    comparison.update(unavailable_assets=[], universe_size=2, discovery_limit=5)
    monkeypatch.setattr(api_client, "get_discovery", lambda _: {"findings": []})
    monkeypatch.setattr(api_client, "get_comparison", lambda _: comparison)
    monkeypatch.setattr(api_client, "compare_assets", lambda *args: compare_findings([first, second]).model_dump())
    app = AppTest.from_file(str(ROOT / "dashboard/app.py"), default_timeout=10)
    app.session_state["profile"] = PROFILE
    app.run()
    next(b for b in app.button if b.label == "Comparison").click().run()
    next(m for m in app.multiselect if m.label == "Assets to compare").set_value(["BBCA", "TEST"]).run()
    next(b for b in app.button if b.label == "Compare selected evidence").click().run()
    assert not app.exception
    table = app.dataframe[0].value
    assert {"Valuation", "Quality", "Income"}.issubset(set(table["Group"]))
    assert table.loc[table["Metric"] == "Cash payout ratio", "BBCA"].iloc[0] == "112.89%"
    assert any("Periods, methods and sources" == e.label for e in app.expander)


def test_explanation_source_timing_and_updated_finding(monkeypatch):
    before = finding("BBCA")
    after = copy.deepcopy(before)
    after["retrieved_at"] = "2026-10-03T00:00:00Z"
    response = {"finding": after, "explanation": {"summary": "Offline mocked explanation", "why_relevant": "Profile match"},
                "explanation_source": "gemini", "explanation_meta": {"cache_hit": True,
                 "total_seconds": .002, "asset_seconds": .001, "generation_seconds": 1.2}}
    monkeypatch.setattr(api_client, "explain_finding", lambda *args: response)
    app = AppTest.from_file(str(ROOT / "dashboard/app.py"), default_timeout=10)
    app.session_state["profile"] = PROFILE
    app.session_state["page"] = "finding"
    app.session_state["selected_finding"] = before
    app.run()
    next(b for b in app.button if b.label == "Explain finding").click().run()
    assert not app.exception
    assert app.session_state["selected_finding"] == after
    assert any("Explanation source: Gemini" in c.value for c in app.caption)
    assert any("Reused explanation" in c.value for c in app.caption)
    assert any(e.label == "Response timing" for e in app.expander)
