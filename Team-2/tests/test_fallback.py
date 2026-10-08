from marketlens.engine import analyze_asset
from marketlens.grounding import build_explanation_context
from marketlens.fallback import build_fallback_explanation


def test_fallback_with_no_evidence_does_not_invent_metrics():
    finding = analyze_asset({"symbol": "BBCA"}, {"research_focus": ["growth"]})
    context = build_explanation_context({}, finding)
    result = build_fallback_explanation(context)
    assert result.evidence_summary == []
    assert "No verified evidence" in result.summary
    assert finding["research_relevance"] == 0
    assert all(item in result.limitations for item in finding["limitations"])
