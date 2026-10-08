from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    sectors_api_key: str | None = None
    sectors_base_url: str = "https://api.sectors.app"
    sectors_timeout_seconds: float = 20.0
    # Confirmed 2026-09-22 straight from the Sectors v2 OpenAPI spec (see SKILL.md §4/§12).
    # Still overridable via .env in case a live call ever shows a mismatch.
    sectors_daily_path: str = "/v2/daily/{symbol}/"
    sectors_foreign_flow_path: str = "/v2/foreign-flow/{symbol}/"
    cache_ttl_seconds: int = 300
    # Reports change less frequently than trading series. This cache is in-process.
    company_report_cache_ttl_seconds: int = Field(default=3600, ge=1)

    model_config = SettingsConfigDict(
        # Resolve relative to this project, even when uvicorn starts elsewhere.
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8-sig",
        env_prefix="",
        extra="ignore",
    )


settings = Settings()
