from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class MarketSnapshot(BaseModel):
    price: float | None = None
    volume: float | None = None
    market_cap: float | None = None
    observed_at: str | None = None


class ForeignFlowSnapshot(BaseModel):
    net_foreign_inflow: float | None = None
    foreign_share: float | None = None
    # Sectors' /v2/foreign-flow/{symbol}/ also returns these two raw IDR legs,
    # not just the derived inflow/share figures — confirmed in SKILL.md §4.
    foreign_buy_idr: float | None = None
    foreign_sell_idr: float | None = None
    observed_at: str | None = None


class ValuationYear(BaseModel):
    year: int
    pe: float | None = None
    pb: float | None = None
    peg: float | None = None
    pe_peer_avg: float | None = None
    pb_peer_avg: float | None = None


class QualityYear(BaseModel):
    year: int
    roe: float | None = None
    roa: float | None = None
    net_profit_margin: float | None = None
    operating_profit_margin: float | None = None


class ValuationData(BaseModel):
    unit: Literal["multiple"] = "multiple"
    period_basis: str = "Provider-labelled year; trailing/full-year basis not supplied"
    forward_pe: float | None = None
    forward_pe_basis: str = "Provider estimate; forecast horizon not supplied"
    last_close_price: float | None = None
    price_as_of: str | None = None
    latest: ValuationYear | None = None
    history: list[ValuationYear] = Field(default_factory=list)


class QualityData(BaseModel):
    unit: Literal["decimal_ratio"] = "decimal_ratio"
    period_basis: str = "Annual financial ratio, provider-labelled financial year"
    latest: QualityYear | None = None
    history: list[QualityYear] = Field(default_factory=list)


class IncomeYear(BaseModel):
    year: int
    total_yield: float | None = None
    total_dividend: float | None = None


class IncomeData(BaseModel):
    unit: Literal["decimal_ratio"] = "decimal_ratio"
    dividend_yield_ttm: float | None = None
    average_dividend_yield: float | None = None
    average_period: float | None = None
    average_period_unit: str = "Not supplied"
    payout_ratio: float | None = None
    cash_payout_ratio: float | None = None
    dividend_ttm: float | None = None
    nominal_unit: str = "Currency, per-share basis and split adjustments not confirmed"
    last_ex_dividend_date: str | None = None
    latest: IncomeYear | None = None
    history: list[IncomeYear] = Field(default_factory=list)
    source_endpoint: str
    retrieved_at: str
    limitations: list[str] = Field(default_factory=list)


class IntelligenceData(BaseModel):
    schema_version: Literal["1.1"] = "1.1"
    valuation: ValuationData = Field(default_factory=ValuationData)
    quality: QualityData = Field(default_factory=QualityData)
    income: IncomeData | None = None
    source_endpoint: str
    retrieved_at: str
    limitations: list[str] = Field(default_factory=list)


class CompanyReport(BaseModel):
    symbol: str
    company_name: str | None = None
    # All 8 Company Report sections confirmed in SKILL.md §4/§12. Every one is kept here
    # (rather than just the 3 the backend defaults to requesting) so that if a caller asks
    # for e.g. `sections=valuation,dividend`, that already-billed data is never silently
    # dropped on the floor.
    overview: dict[str, Any] | None = None
    valuation: dict[str, Any] | None = None
    future: dict[str, Any] | None = None
    peers: list[dict[str, Any]] | None = None
    financials: dict[str, Any] | None = None
    dividend: dict[str, Any] | None = None
    management: dict[str, Any] | None = None
    ownership: dict[str, Any] | None = None
    # Additive contract for P0 consumers; raw sections above stay available.
    intelligence: IntelligenceData | None = None
    source_endpoint: str
    retrieved_at: str


class AssetData(BaseModel):
    symbol: str
    company: CompanyReport | None = None
    market: list[MarketSnapshot] = Field(default_factory=list)
    foreign_flow: list[ForeignFlowSnapshot] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    source_endpoints: list[str] = Field(default_factory=list)
