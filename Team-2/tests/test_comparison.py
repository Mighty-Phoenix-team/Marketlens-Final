import pytest

from marketlens.comparison import compare_findings


def make_finding(
    symbol: str,
    *,
    company_name: str | None = None,
    research_relevance: float = 5.0,
    evidence: list[dict] | None = None,
    signal_groups: list[str] | None = None,
    limitations: list[str] | None = None,
) -> dict:
  

    return {
        "symbol": symbol,
        "company_name": company_name or symbol,
        "research_relevance": research_relevance,
        "evidence": evidence or [],
        "signal_groups": signal_groups or [],
        "limitations": limitations or [],
    }


def test_compare_two_findings():
    bbca = make_finding(
        "BBCA",
        company_name="Bank Central Asia",
        research_relevance=7.4,
        evidence=[
            {
                "group": "fundamental",
                "metric": "revenue_growth",
                "value": 0.18,
            },
            {
                "group": "market_activity",
                "metric": "price_change",
                "value": 0.05,
            },
        ],
        signal_groups=[
            "fundamental",
            "market_activity",
        ],
    )

    bbri = make_finding(
        "BBRI",
        company_name="Bank Rakyat Indonesia",
        research_relevance=6.8,
        evidence=[
            {
                "group": "fundamental",
                "metric": "revenue_growth",
                "value": 0.14,
            },
            {
                "group": "market_activity",
                "metric": "price_change",
                "value": 0.03,
            },
        ],
        signal_groups=[
            "fundamental",
            "market_activity",
        ],
    )

    result = compare_findings([bbca, bbri])

    assert result.symbols == ["BBCA", "BBRI"]
    assert len(result.assets) == 2

    assert result.assets[0].symbol == "BBCA"
    assert result.assets[0].research_relevance == 7.4

    assert result.assets[1].symbol == "BBRI"
    assert result.assets[1].research_relevance == 6.8

    assert result.shared_signal_groups == [
        "fundamental",
        "market_activity",
    ]


def test_compare_metric_values():
    bbca = make_finding(
        "BBCA",
        evidence=[
            {
                "group": "fundamental",
                "metric": "revenue_growth",
                "value": 0.18,
            }
        ],
        signal_groups=["fundamental"],
    )

    bbri = make_finding(
        "BBRI",
        evidence=[
            {
                "group": "fundamental",
                "metric": "revenue_growth",
                "value": 0.14,
            }
        ],
        signal_groups=["fundamental"],
    )

    result = compare_findings([bbca, bbri])

    assert len(result.metrics) == 1

    metric = result.metrics[0]

    assert metric.metric == "revenue_growth"
    assert metric.values["BBCA"] == pytest.approx(0.18)
    assert metric.values["BBRI"] == pytest.approx(0.14)

    assert metric.missing_symbols == []


def test_missing_metric_is_reported():
    bbca = make_finding(
        "BBCA",
        evidence=[
            {
                "group": "fundamental",
                "metric": "revenue_growth",
                "value": 0.18,
            },
            {
                "group": "investor_flow",
                "metric": "foreign_imbalance",
                "value": -0.12,
            },
        ],
        signal_groups=[
            "fundamental",
            "investor_flow",
        ],
    )

    bbri = make_finding(
        "BBRI",
        evidence=[
            {
                "group": "fundamental",
                "metric": "revenue_growth",
                "value": 0.14,
            }
        ],
        signal_groups=["fundamental"],
    )

    result = compare_findings([bbca, bbri])

    metrics = {
        metric.metric: metric
        for metric in result.metrics
    }

    foreign_flow = metrics["foreign_imbalance"]

    assert foreign_flow.values["BBCA"] == pytest.approx(-0.12)
    assert foreign_flow.values["BBRI"] is None

    assert foreign_flow.missing_symbols == ["BBRI"]

    assert (
        "Some metrics are unavailable for one or more compared assets."
        in result.limitations
    )


def test_shared_signal_groups_only_contains_common_groups():
    bbca = make_finding(
        "BBCA",
        signal_groups=[
            "fundamental",
            "market_activity",
            "investor_flow",
        ],
    )

    bbri = make_finding(
        "BBRI",
        signal_groups=[
            "fundamental",
            "market_activity",
        ],
    )

    result = compare_findings([bbca, bbri])

    assert result.shared_signal_groups == [
        "fundamental",
        "market_activity",
    ]


def test_duplicate_symbols_are_rejected():
    finding_a = make_finding("BBCA")
    finding_b = make_finding("BBCA")

    with pytest.raises(
        ValueError,
        match="Comparison symbols must be unique",
    ):
        compare_findings([
            finding_a,
            finding_b,
        ])


def test_comparison_requires_at_least_two_findings():
    bbca = make_finding("BBCA")

    with pytest.raises(
        ValueError,
        match="At least two findings are required",
    ):
        compare_findings([bbca])


def test_comparison_does_not_rank_assets():
    bbca = make_finding(
        "BBCA",
        research_relevance=3.0,
    )

    bbri = make_finding(
        "BBRI",
        research_relevance=9.0,
    )

    result = compare_findings([
        bbca,
        bbri,
    ])


    assert result.symbols == [
        "BBCA",
        "BBRI",
    ]

    assert result.assets[0].symbol == "BBCA"
    assert result.assets[1].symbol == "BBRI"