import streamlit as st

from dashboard import api_client
from dashboard.state import open_page
from marketlens.formatting import format_value, metric_label


def label(value: str) -> str:
    return value.replace("_", " ").title()


def render(finding: dict, profile: dict):
    symbol = finding.get("symbol", "—")
    company = (
        finding.get("company")
        or finding.get("company_name")
        or symbol
    )
    sector = finding.get("sector", "Sector unavailable")

    if st.button("← Back"):
        open_page("discovery")
        st.rerun()

    st.caption(f"Market Discovery / {symbol}")

    title, score = st.columns(
        [5, 1.5],
        vertical_alignment="bottom",
    )

    with title:
        st.title(symbol)
        st.write(company)
        st.caption(sector)

    with score:
        st.caption("Research relevance")
        st.markdown(
            f"<div class='score'>"
            f"{finding.get('research_relevance', 0):.2f} / 10"
            f"</div>",
            unsafe_allow_html=True,
        )

    st.divider()

    render_observations(finding)
    render_evidence(finding)
    render_relevance(finding, profile)
    render_explanation(finding, profile)
    render_metadata(finding)


def render_observations(finding: dict):
    st.subheader("Observation")

    observations = finding.get("observation", [])

    if not observations:
        st.caption("No observations available.")
        return

    for observation in observations:
        st.write(observation)

    st.divider()


def render_evidence(finding: dict):
    st.subheader("Evidence")

    evidence = finding.get("evidence", [])

    if not evidence:
        st.caption("No measured evidence available.")
        st.divider()
        return

    for item in evidence:
        group = label(item.get("group", "Evidence"))
        metric = metric_label(item)

        st.markdown(f"**{group}**")

        metric_col, value_col = st.columns([4, 2])

        metric_col.write(metric)

        value_col.write(format_value(item))

        details = []

        if item.get("period"):
            details.append(str(item["period"]))

        if item.get("method"):
            details.append(str(item["method"]))

        if details:
            st.caption(" · ".join(details))

        if item.get("baseline") is not None:
            # A ratio-gap baseline is a multiple; a ratio-change baseline is a ratio.
            baseline_unit = ("multiple" if item.get("group") == "valuation" else
                             "decimal_ratio" if item.get("group") == "quality" else None)
            baseline = format_value({"value": item["baseline"], "unit": baseline_unit})
            st.caption(f"Reference: {baseline} · {item.get('baseline_period') or 'See method'}")

        source = (
            item.get("source")
            or item.get("source_endpoint")
        )

        if source:
            st.caption(f"Source: {source}")
        if item.get("retrieved_at"):
            st.caption(f"Source retrieved: {item['retrieved_at']}")

        st.write("")

    st.divider()


def render_relevance(
    finding: dict,
    profile: dict,
):
    st.subheader("Why this finding appears")

    focus = profile.get("research_focus", [])

    if focus:
        formatted_focus = ", ".join(
            label(item)
            for item in focus
        )

        st.write(
            f"Your current research profile prioritizes "
            f"{formatted_focus}."
        )

    reason = finding.get("relevance_reason")

    if isinstance(reason, str):
        st.write(reason)

    elif isinstance(reason, dict):
        matched = reason.get("matched_groups", [])

        if matched:
            st.write(
                "Measured evidence is available in "
                + ", ".join(label(item) for item in matched)
                + "."
            )

    st.caption(
        "Research Relevance measures alignment with your "
        "research context. It does not represent investment "
        "quality, expected return, or suitability."
    )

    st.divider()


def render_explanation(
    finding: dict,
    profile: dict,
):
    st.subheader("Explanation")

    explanation = st.session_state.get("explanation")

    if not explanation:
        if st.button(
            "Explain finding",
            type="primary",
        ):
            try:
                with st.spinner("Preparing explanation…"):
                    result = api_client.explain_finding(profile["id"], finding["symbol"])
            except api_client.APIError as exc:
                st.error(str(exc))
                return

            st.session_state.explanation_source = result.get("explanation_source")
            st.session_state.explanation_meta = result.get("explanation_meta", {})
            st.session_state.selected_finding = result.get("finding") or finding
            st.session_state.explanation = result.get(
                "explanation"
            ) or result.get("ai_explanation")
            st.rerun()

        st.caption(
            "Uses the evidence above to explain the finding. "
            "It does not recalculate Research Relevance."
        )
        return

    source = st.session_state.get("explanation_source")
    st.caption({"gemini": "Explanation source: Gemini",
                "deterministic_fallback": "Explanation source: deterministic fallback"}.get(source, "Explanation source: unavailable"))
    meta = st.session_state.get("explanation_meta") or {}
    if meta.get("cache_hit"):
        st.caption("Reused explanation for the same evidence and research profile.")
    if source == "deterministic_fallback":
        reasons = {"missing_api_key": "The Gemini API key is not configured.",
                   "timeout": "Gemini did not finish within the time limit.",
                   "rate_limited": "Gemini temporarily limited the request or its quota was reached.",
                   "authentication": "Gemini authentication or access failed.",
                   "invalid_response": "Gemini returned an explanation that could not be processed.",
                   "connection_error": "The Gemini connection failed.",
                   "model_unavailable": "The configured Gemini model was unavailable.",
                   "busy": "Other explanations are being prepared. Please try again shortly."}
        st.info(reasons.get(meta.get("reason"), "Gemini could not complete this explanation.")
                + " Recorded evidence remains available below.")
        if st.button("Retry explanation", help="A new provider attempt is allowed after a short cooldown."):
            st.session_state.explanation = None
            st.rerun()
    if meta:
        with st.expander("Response timing"):
            st.caption(f"This request: {meta.get('total_seconds', 0):.2f}s · "
                       f"Asset data: {meta.get('asset_seconds', 0):.2f}s · "
                       f"Original explanation generation: {meta.get('generation_seconds', 0):.2f}s")
    st.write(explanation.get("summary", ""))

    why = explanation.get("why_relevant")

    if why:
        st.markdown("**Why it is relevant**")
        st.write(why)

    evidence = explanation.get(
        "evidence_summary",
        [],
    )

    if evidence:
        st.markdown("**Evidence used**")

        for item in evidence:
            st.write(f"— {item}")

    limitations = explanation.get(
        "limitations",
        [],
    )

    if limitations:
        st.markdown("**Limitations**")

        for item in limitations:
            st.write(f"— {item}")

    questions = explanation.get(
        "next_research_questions",
        [],
    )

    if questions:
        st.markdown("**Further research**")

        for question in questions:
            st.write(f"→ {question}")

    st.divider()


def render_metadata(finding: dict):
    with st.expander("Methodology"):
        if finding.get("methodology_version"):
            st.caption(f"Methodology version: {finding['methodology_version']}")
        st.write(
            finding.get(
                "reasoning",
                "No methodology description available.",
            )
        )

        method = finding.get("method")

        if method:
            st.code(method)

    with st.expander("Limitations"):
        limitations = finding.get(
            "limitations",
            [],
        )

        if not limitations:
            st.write("No additional limitations supplied.")
        else:
            for item in limitations:
                st.write(f"— {item}")

    with st.expander("Sources"):
        sources = finding.get(
            "source_endpoints",
            [],
        )

        if not sources:
            st.write("No source endpoints supplied.")
        else:
            for source in sources:
                st.code(source)

        retrieved_at = finding.get("retrieved_at")

        if retrieved_at:
            st.caption(
                f"Retrieved at {retrieved_at}"
            )
