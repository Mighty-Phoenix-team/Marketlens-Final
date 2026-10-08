from app.normalization import (
    normalize_company_report,
    normalize_daily_rows,
    normalize_foreign_rows,
)


def test_normalize_company_report():
    payload = {
        "symbol": "BBCA.JK",
        "company_name": "PT Bank Central Asia Tbk.",
        "overview": {"sector": "Financials"},
        "financials": {
            "yoy_quarter_revenue_growth": 0.11,
            "yoy_quarter_earnings_growth": 0.04,
        },
        "peers": [{"symbol": "BBCA.JK"}],
    }

    result = normalize_company_report(
        payload,
        "https://api.sectors.app/v2/company/report/BBCA/?sections=overview,financials,peers",
        "2026-09-22T00:00:00+00:00",
        requested_symbol="BBCA",
    )

    assert result.symbol == "BBCA"
    assert result.company_name == "PT Bank Central Asia Tbk."
    assert result.financials["yoy_quarter_revenue_growth"] == 0.11
    assert len(result.peers) == 1
    # Sections that weren't in this payload stay explicitly None, never dropped/guessed.
    assert result.valuation is None
    assert result.dividend is None


def test_normalize_company_report_keeps_non_default_sections():
    # If a caller requests sections beyond the app's default (overview/financials/peers),
    # that already-billed data must not be silently discarded.
    payload = {
        "symbol": "BBCA.JK",
        "valuation": {"pe_ratio": 24.1},
        "dividend": {"dividend_yield": 0.02},
    }

    result = normalize_company_report(
        payload,
        "https://api.sectors.app/v2/company/report/BBCA/?sections=valuation,dividend",
        "2026-09-22T00:00:00+00:00",
        requested_symbol="BBCA",
    )

    assert result.valuation["pe_ratio"] == 24.1
    assert result.dividend["dividend_yield"] == 0.02


def test_normalize_company_report_falls_back_to_requested_symbol():
    # payload["symbol"] shape is still unverified against a live call — never end up
    # with an empty symbol just because the field is missing from the response.
    payload = {"overview": {"sector": "Financials"}}

    result = normalize_company_report(
        payload,
        "https://api.sectors.app/v2/company/report/BBCA/?sections=overview",
        "2026-09-22T00:00:00+00:00",
        requested_symbol="BBCA.JK",
    )

    assert result.symbol == "BBCA"


def test_normalize_daily_rows():
    payload = {
        "data": [
            {"date": "2026-09-22", "close": 9450, "volume": 5000000, "market_cap": 1000000000}
        ]
    }

    rows = normalize_daily_rows(payload)

    assert rows[0].price == 9450
    assert rows[0].volume == 5000000
    assert rows[0].market_cap == 1000000000


def test_normalize_foreign_rows():
    payload = {
        "data": [
            {"date": "2026-09-22", "net_foreign_inflow": 1200000000, "foreign_share": 0.18}
        ]
    }

    rows = normalize_foreign_rows(payload)

    assert rows[0].net_foreign_inflow == 1200000000
    assert rows[0].foreign_share == 0.18


def test_normalize_foreign_rows_keeps_raw_idr_legs():
    payload = {
        "data": [
            {
                "date": "2026-09-22",
                "net_foreign_inflow": 1200000000,
                "foreign_share": 0.18,
                "foreign_buy_idr": 5000000000,
                "foreign_sell_idr": 3800000000,
            }
        ]
    }

    rows = normalize_foreign_rows(payload)

    assert rows[0].foreign_buy_idr == 5000000000
    assert rows[0].foreign_sell_idr == 3800000000
