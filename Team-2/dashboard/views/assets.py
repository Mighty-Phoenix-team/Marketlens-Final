import streamlit as st

from dashboard import api_client
from dashboard.state import open_finding


def render(profile: dict):
    st.title("My Assets")
    st.caption(
        "Assets you selected for continued research."
    )

    symbol_col, button_col = st.columns(
        [5, 1],
        vertical_alignment="bottom",
    )

    with symbol_col:
        symbol = st.text_input(
            "Add symbol",
            placeholder="BBCA",
            label_visibility="collapsed",
        )

    with button_col:
        add_clicked = st.button(
            "Add asset",
            use_container_width=True,
        )

    if add_clicked and symbol.strip():
        clean_symbol = symbol.strip().upper()

        try:
            api_client.save_asset(
                profile["id"],
                clean_symbol,
            )
        except api_client.APIError as exc:
            st.error(str(exc))
        else:
            st.rerun()

    st.divider()

    try:
        result = api_client.get_assets(profile["id"])
    except api_client.APIError as exc:
        st.error(str(exc))
        return

    findings = result.get("findings", [])

    if not findings:
        st.info("No assets saved yet.")
        return

    header = st.columns([1.2, 4, 1.5, 1.8])

    header[0].caption("SYMBOL")
    header[1].caption("COMPANY")
    header[2].caption("RELEVANCE")
    header[3].caption("")

    st.divider()

    for finding in findings:
        render_asset(profile["id"], finding)


def render_asset(profile_id: str, finding: dict):
    symbol = finding.get("symbol", "—")
    company = (
        finding.get("company")
        or finding.get("company_name")
        or symbol
    )
    relevance = finding.get("research_relevance", 0)

    cols = st.columns(
        [1.2, 4, 1.5, 1.8],
        vertical_alignment="center",
    )

    cols[0].write(f"**{symbol}**")
    cols[1].write(company)
    cols[2].write(f"{relevance:.2f} / 10")

    view, remove = cols[3].columns(2)

    if view.button(
        "View",
        key=f"asset-view-{symbol}",
    ):
        open_finding(symbol, finding)
        st.rerun()

    if remove.button(
        "×",
        key=f"asset-remove-{symbol}",
        help="Remove asset",
    ):
        try:
            api_client.remove_asset(
                profile_id,
                symbol,
            )
        except api_client.APIError as exc:
            st.error(str(exc))
        else:
            st.rerun()

    st.divider()