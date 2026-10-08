from __future__ import annotations

import asyncio
import re
from datetime import datetime, timezone
from typing import Any
from urllib.parse import quote

import httpx

from .cache import TTLCache
from .config import Settings


class SectorsAPIError(RuntimeError):
    def __init__(self, status_code: int, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.message = message


REPORT_SECTIONS = frozenset({
    "overview", "financials", "valuation", "dividend", "peers",
    "future", "management", "ownership",
})


def clean_symbol(symbol: str) -> str:
    cleaned = symbol.strip().upper().removesuffix(".JK")
    if not re.fullmatch(r"[A-Z]{4}", cleaned):
        raise SectorsAPIError(400, "IDX symbol must be four letters, optionally followed by .JK")
    return cleaned


class SectorsClient:
    def __init__(self, settings: Settings, cache: TTLCache | None = None) -> None:
        self.settings = settings
        self.cache = cache or TTLCache()
        self._locks: dict[str, asyncio.Lock] = {}

    def _headers(self) -> dict[str, str]:
        if not self.settings.sectors_api_key:
            raise SectorsAPIError(503, "SECTORS_API_KEY is not configured")
        return {
            "Authorization": self.settings.sectors_api_key,
            "Accept": "application/json",
        }

    async def _get_json(
        self,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        cache_key: str | None = None,
        ttl_seconds: int | None = None,
    ) -> tuple[dict[str, Any] | list[Any], str]:
        # Two simultaneous dashboard requests must not spend two sets of credits.
        if cache_key:
            lock = self._locks.setdefault(cache_key, asyncio.Lock())
            async with lock:
                return await self._request_json(path, params=params, cache_key=cache_key,
                                                ttl_seconds=ttl_seconds)
        return await self._request_json(path, params=params, ttl_seconds=ttl_seconds)

    async def _request_json(
        self,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        cache_key: str | None = None,
        ttl_seconds: int | None = None,
    ) -> tuple[dict[str, Any] | list[Any], str]:
        ttl = self.settings.cache_ttl_seconds if ttl_seconds is None else ttl_seconds
        if cache_key:
            cached = self.cache.get(cache_key)
            if cached is not None:
                # Negative result cached from a prior billable 404 — replay the error
                # without spending another credit on the same lookup.
                if cached.get("status") == "not_found":
                    raise SectorsAPIError(404, cached["message"])
                return cached["payload"], cached["source"]

        url = f"{self.settings.sectors_base_url.rstrip('/')}/{path.lstrip('/')}"

        async with httpx.AsyncClient(
            timeout=self.settings.sectors_timeout_seconds,
            headers=self._headers(),
        ) as client:
            try:
                response = await client.get(url, params=params)
            except httpx.HTTPError as exc:
                raise SectorsAPIError(503, f"Sectors API request failed: {exc}") from exc

        # Credit behavior from Sectors docs (SKILL.md §4):
        # 2xx and 404 are billable; 400/401/403/429/5xx are not.
        if response.status_code >= 400:
            try:
                payload = response.json()
            except ValueError:
                payload = {"error": response.text}

            message = (payload.get("message") or payload.get("error") or response.text
                       if isinstance(payload, dict) else response.text)

            if response.status_code == 404:
                # 404 still cost a credit, so cache the negative result — otherwise every
                # repeat request for an invalid/delisted symbol keeps re-billing.
                message = f"Resource not found (billable lookup): {message}"
                if cache_key:
                    self.cache.set(
                        cache_key,
                        {"status": "not_found", "message": str(message)},
                        ttl,
                    )
                raise SectorsAPIError(404, str(message))
            if response.status_code in {400, 401, 403, 429}:
                # Free responses — nothing to cache, a retry might legitimately succeed.
                raise SectorsAPIError(response.status_code, str(message))
            if response.status_code >= 500:
                raise SectorsAPIError(502, f"Sectors server error: {message}")

            raise SectorsAPIError(response.status_code, str(message))

        try:
            payload = response.json()
        except ValueError as exc:
            raise SectorsAPIError(502, "Sectors API returned invalid JSON") from exc

        # Include the requested sections/date window in the evidence source.
        source = str(response.request.url)
        if cache_key:
            self.cache.set(
                cache_key,
                {
                    "status": "ok",
                    "payload": payload,
                    "source": source,
                    "retrieved_at": datetime.now(timezone.utc).isoformat(),
                },
                ttl,
            )

        return payload, source

    async def get_company_report(
        self,
        symbol: str,
        sections: list[str],
    ) -> tuple[dict[str, Any], str, str]:
        cleaned = clean_symbol(symbol)
        encoded_symbol = quote(cleaned, safe="")
        selected = sorted({s.strip().lower() for s in sections if s.strip()})
        if not selected or set(selected) - REPORT_SECTIONS:
            raise SectorsAPIError(400, "At least one valid Company Report section is required")
        section_list = ",".join(selected)

        path = f"/v2/company/report/{encoded_symbol}/"
        cache_key = f"company-report:{cleaned}:{section_list}"

        payload, source = await self._get_json(
            path,
            params={"sections": section_list},
            cache_key=cache_key,
            ttl_seconds=self.settings.company_report_cache_ttl_seconds,
        )
        if not isinstance(payload, dict):
            raise SectorsAPIError(502, "Sectors Company Report must be a JSON object")
        cached = self.cache.get(cache_key) or {}
        retrieved_at = cached.get("retrieved_at") or datetime.now(timezone.utc).isoformat()
        return payload, source, retrieved_at

    async def get_configured_series(
        self,
        path_template: str,
        symbol: str,
        *,
        params: dict[str, Any] | None = None,
        cache_namespace: str,
    ) -> tuple[dict[str, Any] | list[Any], str]:
        cleaned = clean_symbol(symbol)
        path = path_template.format(symbol=quote(cleaned, safe=""))
        cache_key = f"{cache_namespace}:{cleaned}:{sorted((params or {}).items())}"
        return await self._get_json(path, params=params, cache_key=cache_key)
