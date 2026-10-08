from __future__ import annotations 
import math

from marketlens.schemas import AssetComparisonSummarize, MetricComparison, ComparisonResults, WatchlistDiscoveryComparison, WatchlistDiscoveryItem 

def _evidence_map(finding: dict) -> dict[str, float] : 
    result : dict[str, float] = {}

    for evidence in finding.get("evidence", []) : 
        if not isinstance(evidence, dict) : 
            continue 
        metric = evidence.get("metric")
        value = evidence.get("value")

        if(isinstance(metric, str) and isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)) : 
            result[metric] = float(value)
    return result 


def compare_findings(findings: list[dict]) -> ComparisonResults : 
    if len(findings) < 2:
        raise ValueError("At least two findings are required for comparison.")
    
    findings = [{**f, "symbol": str(f["symbol"]).strip().upper()} for f in findings]
    symbols = [f["symbol"] for f in findings]
    if len(symbols) != len(set(symbols)) :
        raise ValueError("Comparison symbols must be unique.")
    
    assets = [ 
        AssetComparisonSummarize( 
            symbol = finding["symbol"], 
            company_name= finding.get("company_name", finding["symbol"]), 
            research_relevance = float(finding.get("research_relevance", 0.0)),
            signal_group = list(finding.get("signal_groups", [])),
            signal_groups = list(finding.get("signal_groups", [])),
            methodology_version=finding.get("methodology_version"),
            limitations = list(finding.get("limitations", [])),
        ) for finding in findings
    ]

    evidence_by_symbol = { finding["symbol"]: _evidence_map(finding) for finding in findings}

    all_metrics : set[str] = set()

    for evidence in evidence_by_symbol.values() : 
        all_metrics.update(evidence)
    
    metrics_comparison: list[MetricComparison] = []

    for metric in sorted(all_metrics) : 
        values : dict[str, float | None] = {}
        missing: list[str] = []

        for symbol in symbols : 
            value = evidence_by_symbol[symbol].get(metric)
            values[symbol] = value

            if value is None : 
                missing.append(symbol)
        
        details = {f["symbol"]: next((dict(e) for e in f.get("evidence", [])
                    if isinstance(e, dict) and e.get("metric") == metric
                    and values[f["symbol"]] is not None), None) for f in findings}
        rows = [e for e in details.values() if e is not None]
        periods = {e.get("period") for e in rows}
        units = {e.get("unit") for e in rows}
        status = "unconfirmed"
        if missing:
            status = "missing_data"
        elif len(units) > 1:
            status = "different_units"
        elif len(periods) > 1:
            status = "different_periods"
        elif None not in periods and None not in units:
            status = "matching_labels_only"
        metrics_comparison.append(
            MetricComparison(
                metric=metric,
                values=values,
                missing_symbols=missing,
                group=rows[0].get("group") if rows else None,
                evidence_by_symbol=details, period_status=status,
            )
        )
    
    signal_sets = [set(finding.get("signal_groups", [])) for finding in findings]

    shared_signal_groups = (sorted(set.intersection(*signal_sets))if signal_sets else [])

    limitations: list[str] = []

    if any(metric.missing_symbols for metric in metrics_comparison):
        limitations.append("Some metrics are unavailable for one or more compared assets.")

    limitations.append("Matching period labels do not establish identical calculation bases. Units, periods and source methods must be checked per asset; no winner or cross-asset ratio gap is calculated.")
    if len({f.get("methodology_version") for f in findings}) > 1:
        limitations.append("Research Relevance scores use different methodology versions and must not be compared directly.")
    limitations.append(
        "Comparison describes measured evidence and research relevance only; "
        "it does not indicate investment quality or expected return."
    )

    return ComparisonResults(
        symbols=symbols,
        assets=assets,
        metrics=metrics_comparison,
        shared_signal_groups=shared_signal_groups,
        limitations=limitations,
    )
def _to_comparison_item(finding: dict) -> WatchlistDiscoveryItem:
    return WatchlistDiscoveryItem(
        symbol=str(finding["symbol"]).upper(),
        company_name=finding.get("company_name", finding["symbol"]),
        research_relevance=float(finding.get("research_relevance", 0.0)),
        signal_groups=list(finding.get("signal_groups", [])),
        relevance_reason=finding.get("relevance_reason"),
        evidence=list(finding.get("evidence", [])),
        methodology_version=finding.get("methodology_version"),
    )


def compare_watchlist_discovery(
    watchlist_findings: list[dict],
    discovery_findings: list[dict],
) -> WatchlistDiscoveryComparison:
    watchlist = {
        str(finding["symbol"]).upper(): finding
        for finding in watchlist_findings
    }

    discovery = {
        str(finding["symbol"]).upper(): finding
        for finding in discovery_findings
    }

    watchlist_symbols = set(watchlist)
    discovery_symbols = set(discovery)

    overlap_symbols = sorted(watchlist_symbols & discovery_symbols)
    watchlist_only_symbols = sorted(watchlist_symbols - discovery_symbols)
    discovery_only_symbols = sorted(discovery_symbols - watchlist_symbols)

    overlap = [
        _to_comparison_item(discovery[symbol])
        for symbol in overlap_symbols
    ]

    watchlist_only = [
        _to_comparison_item(watchlist[symbol])
        for symbol in watchlist_only_symbols
    ]

    discovery_only = [
        _to_comparison_item(discovery[symbol])
        for symbol in discovery_only_symbols
    ]

    return WatchlistDiscoveryComparison(
        watchlist_count=len(watchlist_symbols),
        discovery_count=len(discovery_symbols),
        overlap_count=len(overlap_symbols),
        overlap=overlap,
        watchlist_only=watchlist_only,
        discovery_only=discovery_only,
        limitations=[
            "Comparison depends on the current research profile and available evidence.",
            "Research relevance does not represent investment quality or expected return.",
        ],
    )