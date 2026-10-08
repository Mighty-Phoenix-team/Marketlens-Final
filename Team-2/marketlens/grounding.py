"""Structured, source-bound input for an optional explanation layer."""

from __future__ import annotations
import copy


def build_explanation_context(profile: dict, finding: dict) -> dict:
    """Expose measured facts and boundaries without producing an AI answer."""
    return {
        "research_profile": {
            "sectors": profile.get("sectors", []),
            "research_focus": profile.get("research_focus", []),
            "horizon_days": profile.get("horizon_days"),
        },
        "finding": {
            "symbol": finding["symbol"],
            "company_name": finding["company_name"],
            "sector": finding["sector"],
            "research_relevance": finding["research_relevance"],
            "methodology_version": finding.get("methodology_version"),
            "signal_groups": finding.get("signal_groups", []),
            "relevance_reason": finding["relevance_reason"],
            "observation": finding["observation"],
            "evidence": finding["evidence"],
            "reasoning": finding["reasoning"],
            "method": finding["method"],
            "source_endpoints": finding["source_endpoints"],
            "retrieved_at": finding["retrieved_at"],
            "limitations": finding["limitations"],
        },
        "evidence_boundary": {
            "scope": "Measured market and company-report evidence in this finding only.",
            "causal_explanation_available": False,
            "document_context_available": False,
            "instructions": [
                "Use only the supplied evidence for numerical claims and cite its source and period.",
                "Respect each metric's unit: decimal_ratio × 100 is percent; decimal_ratio_change × 100 is percentage points (pp); multiple is shown as ×.",
                "Keep financial years, provider-labelled valuation years, and retrieval dates distinct. Do not describe older annual ratios as today's profitability.",
                "Forward PE is a provider estimate with an unspecified horizon. Do not treat it as realized earnings or compare it to historical PE as if their bases were identical.",
                "Historical and same-year peer gaps are descriptive; peer membership and calculation basis may be unavailable. Do not infer undervaluation, overvaluation or a winner.",
                "Explain research relevance as a match to the profile, not investment quality.",
                "Income yields use separate TTM, provider-average and year-labelled periods. Do not equate them, annualize a partial year, or infer future yield or dividend safety.",
                "Payout ratios have unspecified periods and denominator methods. A value above 100% is not by itself proof of an unsustainable dividend.",
                "Ex-dividend dates and retrieval timestamps are not observation dates for income ratios. Null upcoming dividends means unavailable data, not no scheduled dividends.",
                "If asked why a market metric moved, say that these measurements do not establish its cause.",
                "State unavailable metrics and limitations explicitly; do not fill gaps with invented facts.",
                "Do not give buy, sell or hold instructions, price targets, or return predictions.",
            ],
        },
    }


def compact_explanation_context(context: dict) -> dict:
    """Remove duplicated display text and intern repeated source metadata.

    The public context endpoint remains unchanged. No measured metric, unit,
    period, baseline or limitation is dropped from the model input.
    """
    result = copy.deepcopy(context)
    finding = result.get("finding", {})
    finding.pop("observation", None)  # Same numbers already present in evidence.
    sources = {}
    for item in finding.get("evidence", []):
        item.pop("strength", None)
        item.pop("strength_method", None)
        if item.get("source"):
            source = {"source": item.pop("source"), "retrieved_at": item.pop("retrieved_at", None)}
            ref = next((k for k, v in sources.items() if v == source), None)
            if ref is None:
                ref = f"S{len(sources) + 1}"
                sources[ref] = source
            item["source_ref"] = ref
    result["evidence_sources"] = sources
    return result
