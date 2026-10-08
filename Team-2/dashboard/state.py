import streamlit as st


DEFAULTS = {
    "profile": None,
    "page": "discovery",
    "selected_symbol": None,
    "selected_finding": None,
    "explanation": None,
    "explanation_source": None,
    "explanation_meta": None,
    "comparison_detail": None,
}


def init_state():
    for key, value in DEFAULTS.items():
        if key not in st.session_state:
            st.session_state[key] = value


def open_finding(symbol: str, finding: dict):
    st.session_state.selected_symbol = symbol
    st.session_state.selected_finding = finding
    st.session_state.explanation = None
    st.session_state.explanation_source = None
    st.session_state.explanation_meta = None
    st.session_state.page = "finding"


def open_page(page: str):
    st.session_state.page = page


def profile_id() -> str | None:
    profile = st.session_state.profile

    if not profile:
        return None

    return profile.get("id")