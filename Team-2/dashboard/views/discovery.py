import streamlit as st

from dashboard import api_client
from dashboard.state import open_finding


def render(profile: dict):
    st.title("Market Discovery")
    st.caption(
        "Research findings matched to your current research profile."
    )

    focus = profile.get("research_focus", [])
    sectors = profile.get("sectors", [])
    horizon = profile.get("horizon_days")

    context = " · ".join(
        [
            ", ".join(sectors) if sectors else "All sectors",
            ", ".join(item.replace("_", " ").title() for item in focus)
            if focus
            else "All research areas",
            f"{horizon} days",
        ]
    )

    st.markdown(f"**{context}**")
    st.divider()

    try:
        result = api_client.get_discovery(profile["id"])
    except api_client.APIError as exc:
        st.error(str(exc))
        return

    findings = result.get("findings", [])

    if not findings:
        st.info("No findings are available for this research profile.")
        return

    for finding in findings:
        render_row(profile["id"], finding)


def render_row(profile_id: str, finding: dict):
    symbol = finding.get("symbol", "—")
    company = (
        finding.get("company")
        or finding.get("company_name")
        or symbol
    )
    sector = finding.get("sector", "Sector unavailable")
    relevance = finding.get("research_relevance", 0)
    groups = finding.get("signal_groups", [])

    main, score, action = st.columns(
        [6, 2, 1.4],
        vertical_alignment="center",
    )

    with main:
        st.markdown(f"### {symbol}")
        st.write(company)

        group_text = " · ".join(
            group.replace("_", " ").title()
            for group in groups
        )

        st.caption(
            f"{sector}"
            + (f"  ·  {group_text}" if group_text else "")
        )

    with score:
        st.caption("Research relevance")
        st.markdown(
            f"<div class='score'>{relevance:.2f}</div>",
            unsafe_allow_html=True,
        )
        st.caption("out of 10")

    with action:
        if st.button(
            "View",
            key=f"view-{symbol}",
            use_container_width=True,
        ):
            try:
                detail = api_client.get_finding(
                    profile_id,
                    symbol,
                )
            except api_client.APIError as exc:
                st.error(str(exc))
            else:
                open_finding(symbol, detail)
                st.rerun()

        if st.button(
            "Save",
            key=f"save-{symbol}",
            use_container_width=True,
        ):
            try:
                api_client.save_asset(
                    profile_id,
                    symbol,
                )
            except api_client.APIError as exc:
                st.error(str(exc))
            else:
                st.toast(f"{symbol} saved")

    st.divider()