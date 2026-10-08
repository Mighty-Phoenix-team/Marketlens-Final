import copy
import json
from pathlib import Path

import pytest
from app.normalization import normalize_company_report

CAPTURE = json.loads((Path(__file__).parent / "fixtures/live_dividend_BBCA.json").read_text())


def normalize(raw=None):
    raw = CAPTURE if raw is None else raw
    return normalize_company_report(raw, CAPTURE["source_endpoint"], CAPTURE["retrieved_at"], "BBCA")


def test_capture_maps_income_without_changing_raw_or_units():
    report = normalize()
    income = report.intelligence.income
    assert report.dividend == CAPTURE["dividend"]
    assert income.dividend_yield_ttm == .0635
    assert income.average_dividend_yield == pytest.approx(.0283050412777811)
    assert income.average_period == 5
    assert income.payout_ratio == pytest.approx(.801491566752531)
    assert income.cash_payout_ratio == pytest.approx(1.12888987895419)
    assert income.dividend_ttm == 381
    assert income.latest.year == 2026
    assert income.latest.total_dividend == 326  # Distinct from TTM 381.
    assert income.last_ex_dividend_date == "2026-08-31"
    assert income.source_endpoint == CAPTURE["source_endpoint"]
    assert income.retrieved_at == CAPTURE["retrieved_at"]
    assert len(income.history) == 7
    assert any("null does not" in s for s in income.limitations)


@pytest.mark.parametrize("value", [None, True, "NaN", float("inf"), "6.35%", {}])
def test_missing_or_invalid_values_are_not_zero(value):
    raw = copy.deepcopy(CAPTURE)
    raw["dividend"]["yield_ttm"] = value
    assert normalize(raw).intelligence.income.dividend_yield_ttm is None


def test_zero_negative_and_over_100_ratios_survive():
    raw = copy.deepcopy(CAPTURE)
    raw["dividend"].update(yield_ttm=0, payout_ratio=-.5, cash_payout_ratio=1.25)
    income = normalize(raw).intelligence.income
    assert (income.dividend_yield_ttm, income.payout_ratio, income.cash_payout_ratio) == (0, -.5, 1.25)


def test_missing_section_and_latest_null_do_not_inherit_history():
    assert normalize({"symbol": "BBCA"}).intelligence.income is None
    raw = copy.deepcopy(CAPTURE)
    raw["dividend"]["historical_dividends"]["2027"] = {"total_yield": None}
    raw["dividend"]["last_ex_dividend_date"] = "not a date"
    income = normalize(raw).intelligence.income
    assert income.latest.year == 2027 and income.latest.total_yield is None
    assert income.last_ex_dividend_date is None
