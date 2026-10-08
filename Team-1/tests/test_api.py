from fastapi.testclient import TestClient

from app import main


def test_p0_defaults_preserve_raw_contract(monkeypatch):
    requests = []

    async def report(symbol, sections):
        requests.append((symbol, sections))
        return ({
            "symbol": symbol,
            "company_name": "Test company",
            "overview": {"sector": "Financials"},
            "financials": {"historical_financial_ratio": []},
            "valuation": {"forward_pe": None, "historical_valuation": []},
        }, "https://api.sectors.app/v2/company/report/BBCA/", "2026-10-01T00:00:00Z")

    async def series(*args, **kwargs):
        return [], "https://api.sectors.app/v2/daily/BBCA/"

    monkeypatch.setattr(main.sectors, "get_company_report", report)
    monkeypatch.setattr(main.sectors, "get_configured_series", series)
    with TestClient(main.app) as client:
        response = client.get("/api/assets/bbca.jk")
        standalone = client.get("/api/assets/BBCA/company-report")
    assert response.status_code == standalone.status_code == 200
    assert all(sections == ["overview", "financials", "valuation", "dividend"] for _, sections in requests)
    assert response.json()["symbol"] == "BBCA"
    assert response.json()["company"]["valuation"]["forward_pe"] is None
    assert response.json()["company"]["dividend"] is None
    assert set(response.json()) == {"symbol", "company", "market", "foreign_flow", "limitations", "source_endpoints"}


def test_invalid_input_does_not_call_upstream(monkeypatch):
    async def forbidden(*args, **kwargs):
        raise AssertionError("Invalid input reached a billable provider")

    monkeypatch.setattr(main.sectors, "get_company_report", forbidden)
    monkeypatch.setattr(main.sectors, "get_configured_series", forbidden)
    with TestClient(main.app) as client:
        for path in ["/api/assets/BB", "/api/assets/BBCA/company-report?sections=",
                     "/api/assets/BBCA/company-report?sections=unsupported"]:
            assert client.get(path).status_code == 400
