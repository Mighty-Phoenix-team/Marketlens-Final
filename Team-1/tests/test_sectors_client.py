import httpx
import asyncio
import pytest

from app.cache import TTLCache
from app.config import Settings
from app.sectors_client import SectorsAPIError, SectorsClient


def _settings() -> Settings:
    return Settings(sectors_api_key="test_key", _env_file=None)


@pytest.mark.asyncio
async def test_404_is_billable_once_then_served_from_cache(monkeypatch):
    """404 responses cost a credit, so a second lookup of the same invalid symbol
    must never hit the network again — it should replay the cached error instead."""
    call_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        return httpx.Response(404, json={"message": "symbol not found"})

    transport = httpx.MockTransport(handler)

    class PatchedAsyncClient(httpx.AsyncClient):
        def __init__(self, *args, **kwargs):
            kwargs["transport"] = transport
            super().__init__(*args, **kwargs)

    monkeypatch.setattr("app.sectors_client.httpx.AsyncClient", PatchedAsyncClient)

    client = SectorsClient(_settings(), TTLCache())

    with pytest.raises(SectorsAPIError) as first:
        await client._get_json("/v2/company/report/NOPE/", cache_key="report:NOPE")
    assert first.value.status_code == 404

    with pytest.raises(SectorsAPIError) as second:
        await client._get_json("/v2/company/report/NOPE/", cache_key="report:NOPE")
    assert second.value.status_code == 404

    # Only one real HTTP call — the second 404 came from cache, not another billed request.
    assert call_count == 1


@pytest.mark.asyncio
async def test_company_cache_is_shared_by_section_order_and_concurrent_requests(monkeypatch):
    calls = []

    async def handler(request):
        calls.append(request)
        await asyncio.sleep(0)  # Let the second request arrive before this one completes.
        return httpx.Response(200, json={"symbol": "BBCA", "valuation": {"forward_pe": None}})

    transport = httpx.MockTransport(handler)
    original = httpx.AsyncClient

    class MockClient(original):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs, transport=transport)

    monkeypatch.setattr("app.sectors_client.httpx.AsyncClient", MockClient)
    client = SectorsClient(_settings(), TTLCache())
    first, second = await asyncio.gather(
        client.get_company_report("bbca.jk", ["overview", "valuation", "financials"]),
        client.get_company_report("BBCA", ["financials", "overview", "valuation", "overview"]),
    )
    assert len(calls) == 1
    assert calls[0].url.params["sections"] == "financials,overview,valuation"
    assert first == second  # Includes original retrieval timestamp on cache hit.
    assert "sections=" in first[1]
    # A different section set is a different resource, never silently served from cache.
    await client.get_company_report("BBCA", ["dividend"])
    assert len(calls) == 2


@pytest.mark.asyncio
async def test_invalid_symbol_and_sections_are_rejected_before_http():
    client = SectorsClient(_settings(), TTLCache())
    for symbol, sections in [("B", ["overview"]), ("BBCA", []), ("BBCA", ["typo"])]:
        with pytest.raises(SectorsAPIError) as error:
            await client.get_company_report(symbol, sections)
        assert error.value.status_code == 400


@pytest.mark.asyncio
async def test_success_is_cached(monkeypatch):
    call_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        return httpx.Response(200, json={"symbol": "BBCA"})

    transport = httpx.MockTransport(handler)

    class PatchedAsyncClient(httpx.AsyncClient):
        def __init__(self, *args, **kwargs):
            kwargs["transport"] = transport
            super().__init__(*args, **kwargs)

    monkeypatch.setattr("app.sectors_client.httpx.AsyncClient", PatchedAsyncClient)

    client = SectorsClient(_settings(), TTLCache())

    payload1, _ = await client._get_json("/v2/company/report/BBCA/", cache_key="report:BBCA")
    payload2, _ = await client._get_json("/v2/company/report/BBCA/", cache_key="report:BBCA")

    assert payload1 == payload2 == {"symbol": "BBCA"}
    assert call_count == 1
