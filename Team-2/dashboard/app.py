import streamlit as st

from dashboard import api_client
from dashboard.state import init_state, open_page
from dashboard.styles import apply_styles
from dashboard.views import assets, discovery, finding, comparison


st.set_page_config(
    page_title="MarketLens",
    page_icon="M",
    layout="wide",
)

init_state()
apply_styles()


def render_sidebar():
    with st.sidebar:
        st.title("MarketLens")
        st.caption("Research Intelligence")

        st.divider()

        if st.button(
            "Discover",
            use_container_width=True,
        ):
            open_page("discovery")
            st.rerun()

        if st.button(
            "My Assets",
            use_container_width=True,
        ):
            open_page("assets")
            st.rerun()

        if st.button("Comparison", use_container_width=True):
            open_page("comparison")
            st.rerun()

        st.divider()

        st.caption("RESEARCH PROFILE")

        sectors = st.multiselect(
            "Sector",
            [
                "Financials",
                "Technology",
                "Infrastructure",
                "Consumer",
                "Energy",
                "Industrials",
            ],
            default=["Financials"],
        )

        focus = st.multiselect(
            "Focus",
            [
                "growth",
                "market_activity",
                "investor_flow",
                "valuation",
                "profitability",
                "income",
            ],
            default=[
                "growth",
                "market_activity",
            ],
            max_selections=3,
        )

        horizon = st.slider(
            "Horizon",
            min_value=2,
            max_value=90,
            value=30,
            step=1,
            format="%d days"
    )

        if st.button(
            "Apply profile",
            type="primary",
            use_container_width=True,
        ):
            save_profile(
                sectors,
                focus,
                horizon,
            )

        st.divider()

        st.caption(
            "Research Relevance reflects alignment "
            "with your research context."
        )


def save_profile(
    sectors: list[str],
    focus: list[str],
    horizon: int,
):
    current = st.session_state.profile

    try:
        if current:
            profile = api_client.update_profile(
                current["id"],
                sectors,
                focus,
                horizon,
            )
        else:
            profile = api_client.create_profile(
                sectors,
                focus,
                horizon,
            )

    except api_client.APIError as exc:
        st.error(str(exc))
        return

    st.session_state.profile = profile
    st.session_state.explanation = None
    st.session_state.explanation_source = None
    st.session_state.explanation_meta = None
    st.session_state.comparison_detail = None
    st.session_state.page = "discovery"
    st.rerun()


render_sidebar()

profile = st.session_state.profile


if not profile:
    st.title("MarketLens")

    st.write(
        "Evidence-based market research organized around "
        "your research context."
    )

    st.caption(
        "Create a research profile from the sidebar to begin."
    )

    st.stop()


page = st.session_state.page


if page == "assets":
    assets.render(profile)

elif page == "comparison":
    comparison.render(profile)

elif page == "finding":
    selected = st.session_state.selected_finding

    if not selected:
        open_page("discovery")
        st.rerun()

    finding.render(
        selected,
        profile,
    )

else:
    discovery.render(profile)
