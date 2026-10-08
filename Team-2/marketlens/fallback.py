"""Evidence-only explanation available without a working LLM provider."""

from __future__ import annotations

from .schemas import MarketLensExplanation
from .formatting import format_value


def build_fallback_explanation(context: dict) -> MarketLensExplanation:
    finding = context["finding"]
    facts = []
    for item in finding.get("evidence", []):
        facts.append(
            f"{item['metric']}: {format_value(item)} "
            f"(raw {item['value']}, unit {item.get('unit', 'not supplied')}; {item.get('period') or 'period unavailable'}). "
            f"Method: {item.get('method') or 'not supplied'}. "
            f"Source: {item.get('source') or 'unavailable'}."
            + (f" Baseline: {item['baseline']} ({item.get('baseline_period') or 'see method'})."
               if item.get("baseline") is not None else "")
        )
    matched = finding.get("relevance_reason", {}).get("matched_groups", [])
    reason = (
        "Evidence matches these selected research groups: " + ", ".join(matched) + ". "
        if matched else "No selected research group has a confirmed match in this finding. "
    )
    reason += (
        f"Research Relevance is {finding['research_relevance']}/10, copied from the deterministic engine. "
        "It is not investment quality, expected return, or suitability."
    )
    limitations = list(finding.get("limitations", []))
    limitations.append("AI explanation is unavailable; this summary uses recorded evidence only.")
    return MarketLensExplanation(
        summary=(f"{finding['symbol']} has {len(facts)} recorded evidence metrics."
                 if facts else f"No verified evidence is available for {finding['symbol']}."),
        why_relevant=reason,
        evidence_summary=facts,
        limitations=list(dict.fromkeys(limitations)),
        next_research_questions=[
            "Which missing observations would make this research more complete?",
            "Are the source periods comparable for the selected research focus?",
        ],
    )
