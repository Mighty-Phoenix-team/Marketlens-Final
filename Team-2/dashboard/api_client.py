from __future__ import annotations

import os
from typing import Any

import requests
from marketlens import runtime  # Loads Team-2/.env from a fixed project path.

BASE_URL = os.getenv(
    "MARKETLENS_API_BASE_URL",
    "http://127.0.0.1:8001",
).rstrip("/")

TIMEOUT = 120


class APIError(RuntimeError):
    pass


def request(
    method: str,
    path: str,
    *,
    payload: dict | None = None,
) -> Any:
    timeout = TIMEOUT if path.endswith(("/explanation", "/explain")) else 30
    try:
        response = requests.request(
            method,
            f"{BASE_URL}{path}",
            json=payload,
            timeout=(5, timeout),
        )
    except requests.RequestException as exc:
        raise APIError(
            f"{type(exc).__name__}: {method} {path} gagal. "
            f"Batas waktu: {timeout} detik."
        ) from exc

    if not response.ok:
        try:
            detail = response.json().get("detail")
        except (ValueError, AttributeError):
            detail = response.text

        raise APIError(
            f"Request failed ({response.status_code}): {detail}"
        )

    if not response.content:
        return None

    return response.json()


def create_profile(
    sectors: list[str],
    research_focus: list[str],
    horizon_days: int,
):
    return request(
        "POST",
        "/api/profiles",
        payload={
            "sectors": sectors,
            "research_focus": research_focus,
            "horizon_days": horizon_days,
        },
    )


def update_profile(
    profile_id: str,
    sectors: list[str],
    research_focus: list[str],
    horizon_days: int,
):
    return request(
        "PUT",
        f"/api/profiles/{profile_id}",
        payload={
            "sectors": sectors,
            "research_focus": research_focus,
            "horizon_days": horizon_days,
        },
    )


def get_discovery(profile_id: str):
    return request(
        "GET",
        f"/api/profiles/{profile_id}/discovery",
    )


def get_assets(profile_id: str):
    return request(
        "GET",
        f"/api/profiles/{profile_id}/assets",
    )


def save_asset(profile_id: str, symbol: str):
    return request(
        "PUT",
        f"/api/profiles/{profile_id}/assets/{symbol}",
    )


def remove_asset(profile_id: str, symbol: str):
    return request(
        "DELETE",
        f"/api/profiles/{profile_id}/assets/{symbol}",
    )


def get_finding(profile_id: str, symbol: str):
    return request(
        "GET",
        f"/api/profiles/{profile_id}/assets/{symbol}/finding",
    )


def explain_finding(profile_id: str, symbol: str):
    return request(
        "POST",
        f"/api/profiles/{profile_id}/assets/{symbol}/explanation",
    )

def get_comparison(profile_id: str):
    return request("GET", f"/api/profiles/{profile_id}/comparison")


def compare_assets(profile_id: str, symbols: list[str]):
    return request("POST", f"/api/profiles/{profile_id}/comparison", payload={"symbols": symbols})
