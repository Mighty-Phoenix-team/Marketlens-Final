from pydantic import BaseModel, Field 

class MarketLensExplanation(BaseModel) : 
    summary: str = Field(
        description="Concise evidence-based summary of the finding."
    )

    why_relevant: str = Field(
        description="Why the finding is relevant to the user's research context."
    )

    evidence_summary: list[str] = Field(
        default_factory=list,
        description="Key supporting evidence from the structured finding."
    )

    limitations: list[str] = Field(
        default_factory=list,
        description="Important limitations and unavailable information."
    )

    next_research_questions: list[str] = Field(
        default_factory=list,
        description="Neutral follow-up research questions."
    )

class ComparisonRequest(BaseModel) : 
    symbols : list[str] = Field( 
        min_length=2, 
        max_length=10,
        description="List of stock symbols to compare."
    )

class MetricComparison(BaseModel) : 
    metric: str 
    values: dict[str, float | None] = Field(default_factory=dict)
    missing_symbols: list[str] = Field(default_factory=list)
    group: str | None = None
    evidence_by_symbol: dict[str, dict | None] = Field(default_factory=dict)
    period_status: str = "unconfirmed"

class AssetComparisonSummarize(BaseModel) : 
    symbol:str
    company_name:str 
    research_relevance : float 
    signal_group : list[str] = Field(default_factory=list)  # Legacy alias retained.
    signal_groups: list[str] = Field(default_factory=list)
    methodology_version: str | None = None
    limitations : list[str] = Field(default_factory=list)

class ComparisonResults(BaseModel) : 
    symbols : list[str]
    assets : list[AssetComparisonSummarize] = Field(default_factory=list)
    metrics : list[MetricComparison] = Field(default_factory=list)
    shared_signal_groups : list[str] = Field(default_factory=list) 
    limitations : list[str] = Field(default_factory=list)

class WatchlistDiscoveryItem(BaseModel):
    symbol: str
    company_name: str
    research_relevance: float
    signal_groups: list[str] = Field(default_factory=list)
    relevance_reason: dict | str | None = None
    evidence: list[dict] = Field(default_factory=list)
    methodology_version: str | None = None


class WatchlistDiscoveryComparison(BaseModel):
    watchlist_count: int
    discovery_count: int
    overlap_count: int

    overlap: list[WatchlistDiscoveryItem] = Field(default_factory=list)
    watchlist_only: list[WatchlistDiscoveryItem] = Field(default_factory=list)
    discovery_only: list[WatchlistDiscoveryItem] = Field(default_factory=list)

    limitations: list[str] = Field(default_factory=list)