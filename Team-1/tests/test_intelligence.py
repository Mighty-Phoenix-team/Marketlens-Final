import copy
import importlib.util
import json
from pathlib import Path
import shutil

import pytest

from app.intelligence import finite_number, normalize_intelligence
from app.normalization import normalize_company_report


CAPTURE = json.loads((Path(__file__).parent / "fixtures/live_BBCA_company_report.json").read_text())
SOURCE, STAMP = CAPTURE["source_endpoint"], CAPTURE["retrieved_at"]


def normalize(payload):
    return normalize_intelligence(payload, SOURCE, STAMP)


def test_real_capture_keeps_raw_fields_and_normalizes_actual_periods():
    report = normalize_company_report(CAPTURE, SOURCE, STAMP, "BBCA")
    for key in ["overview", "financials", "valuation", "dividend", "peers"]:
        assert getattr(report, key) == CAPTURE[key]
    data = report.intelligence
    assert data.schema_version == "1.1"
    assert data.valuation.latest.year == 2026
    assert data.valuation.latest.pe == pytest.approx(12.757326518681)
    assert data.valuation.latest.pb == pytest.approx(2.74150904211735)
    assert data.valuation.forward_pe == pytest.approx(12.5911952032602)
    assert data.valuation.price_as_of == "2026-09-30"
    assert data.quality.latest.year == 2025
    assert data.quality.latest.roe == pytest.approx(0.20425924389879418)
    assert data.quality.latest.roa == pytest.approx(0.036259263437167184)
    assert data.quality.unit == "decimal_ratio"
    assert data.retrieved_at == STAMP
    assert len(data.quality.history) == 8


def test_unsorted_history_and_identical_duplicates_do_not_change_results():
    payload = copy.deepcopy(CAPTURE)
    for section, key in [("valuation", "historical_valuation"), ("financials", "historical_financial_ratio")]:
        rows = payload[section][key]
        rows.reverse()
        rows.append(copy.deepcopy(rows[0]))
    assert normalize(payload) == normalize(CAPTURE)


def test_latest_missing_ratios_are_not_filled_with_older_years():
    payload = copy.deepcopy(CAPTURE)
    payload["financials"]["historical_financial_ratio"].append({"year": "2026", "profitability": None})
    data = normalize(payload)
    assert data.quality.latest.year == 2026
    assert data.quality.latest.roe is None
    assert data.quality.history[-2].roe is not None


def test_conflicting_duplicates_are_unavailable_and_order_independent():
    payload = copy.deepcopy(CAPTURE)
    other = copy.deepcopy(payload["valuation"]["historical_valuation"][-1])
    other["pe"] = 99
    payload["valuation"]["historical_valuation"].append(other)
    data = normalize(payload)
    assert data.valuation.latest.year == 2026
    assert data.valuation.latest.pe is None
    assert any("conflicting duplicate" in text for text in data.limitations)
    payload["valuation"]["historical_valuation"].reverse()
    assert normalize(payload) == data


@pytest.mark.parametrize("value,expected", [
    (0, 0.0), (-0.1, -0.1), ("0.204", 0.204), (None, None),
    (True, None), (False, None), (float("nan"), None), (float("inf"), None),
    ("20.4%", None), ("N/A", None), ({}, None), ([], None),
])
def test_numeric_inputs_preserve_zero_and_reject_ambiguous_units(value, expected):
    assert finite_number(value) == expected


def test_empty_and_malformed_sections_have_no_invented_values():
    for payload in [{}, {"financials": None, "valuation": []},
                    {"financials": {"historical_financial_ratio": [{"year": True}, {"year": "2025 Q1"}, None]}}]:
        data = normalize(payload)
        assert data.quality.latest is None
        assert data.valuation.latest is None
        assert data.valuation.forward_pe is None
        assert data.limitations


def test_env_location_is_independent_of_terminal_directory(tmp_path, monkeypatch):
    root = tmp_path / "project"
    (root / "app").mkdir(parents=True)
    config = root / "app/config.py"
    shutil.copyfile(Path(__file__).parents[1] / "app/config.py", config)
    (root / ".env").write_text("SECTORS_API_KEY=unit-test-only\n", encoding="utf-8-sig")
    monkeypatch.delenv("SECTORS_API_KEY", raising=False)
    monkeypatch.chdir(tmp_path)
    spec = importlib.util.spec_from_file_location("test_project_settings", config)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.settings.sectors_api_key == "unit-test-only"
