import streamlit as st

from dashboard import api_client
from dashboard.state import open_finding
from marketlens.formatting import format_value, metric_label


def render(profile: dict):
    st.title("Watchlist vs Market Intelligence")
    st.caption(
        "Compare a saved asset with findings from Market Discovery using the same research profile."
    )

    try:
        result = api_client.get_comparison(profile["id"])
    except api_client.APIError as exc:
        st.error(str(exc))
        return

    render_summary(result)
    if result.get("unavailable_assets"):
        st.warning("Some assets could not be loaded: " + ", ".join(
            item["symbol"] for item in result["unavailable_assets"]))
    st.caption(f"Discovery uses up to {result.get('discovery_limit', 5)} findings from "
               f"{result.get('universe_size', 0)} configured tickers. Counts include loaded assets only.")
    render_metric_comparison(profile, result)

    st.divider()

    render_overlap(
        profile["id"],
        result.get("overlap", []),
    )

    st.divider()

    left, right = st.columns(2, gap="large")

    with left:
        render_group(
            "Watchlist Only",
            result.get("watchlist_only", []),
        )

    with right:
        render_group(
            "Market Intelligence Only",
            result.get("discovery_only", []),
        )

    render_limitations(result)


def render_summary(result: dict):
    watchlist, discovery, overlap = st.columns(3)

    watchlist.metric(
        "Watchlist",
        result.get("watchlist_count", 0),
    )

    discovery.metric(
        "Market Intelligence",
        result.get("discovery_count", 0),
    )

    overlap.metric(
        "In Both",
        result.get("overlap_count", 0),
    )


def render_overlap(profile_id: str, items: list[dict]):
    st.subheader("In Both")
    st.caption(
        "Assets in your watchlist that also appear in current Discovery."
    )

    if not items:
        st.write("No overlapping assets.")
        return

    for item in items:
        render_row(profile_id, item)


def render_group(title: str, items: list[dict]):
    st.subheader(title)

    if not items:
        st.caption("No assets.")
        return

    for item in items:
        symbol = item.get("symbol", "—")
        company = item.get("company_name") or symbol
        relevance = item.get("research_relevance", 0)
        groups = item.get("signal_groups", [])

        st.markdown(f"**{symbol}**")
        st.write(company)
        st.caption(f"Research relevance · {relevance:.2f}")

        if groups:
            group_text = " · ".join(
                group.replace("_", " ").title()
                for group in groups
            )
            st.caption(group_text)

        st.write("")


def render_row(profile_id: str, item: dict):
    symbol = item.get("symbol", "—")
    company = item.get("company_name") or symbol
    relevance = item.get("research_relevance", 0)
    groups = item.get("signal_groups", [])

    main, score, action = st.columns(
        [6, 2, 1.4],
        vertical_alignment="center",
    )

    with main:
        st.markdown(f"### {symbol}")
        st.write(company)

        if groups:
            group_text = " · ".join(
                group.replace("_", " ").title()
                for group in groups
            )
            st.caption(group_text)

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
            key=f"comparison-view-{symbol}",
            use_container_width=True,
        ):
            try:
                finding = api_client.get_finding(
                    profile_id,
                    symbol,
                )
            except api_client.APIError as exc:
                st.error(str(exc))
            else:
                open_finding(symbol, finding)
                st.rerun()

    st.divider()


def render_limitations(result: dict):
    limitations = result.get("limitations", [])

    if not limitations:
        return

    with st.expander("Limitations"):
        for item in limitations:
            st.write(f"— {item}")

def render_metric_comparison(profile, result):
    st.subheader("Compare evidence")
    overlap = result.get("overlap", [])
    watchlist = sorted({item["symbol"] for item in overlap + result.get("watchlist_only", [])})
    discovery = sorted({item["symbol"] for item in overlap + result.get("discovery_only", [])})
    if not watchlist:
        st.info("Save a stock in My Assets to choose it from your Watchlist here.")
        return
    if not discovery:
        st.info("No Market Intelligence findings are available for comparison.")
        return
    st.caption("Choose one Watchlist stock and up to three Market Intelligence stocks.")
    left, right = st.columns(2, gap="large")
    watchlist_key = f"comparison_watchlist_{profile['id']}"
    discovery_key = f"comparison_discovery_{profile['id']}"
    if st.session_state.get(watchlist_key) not in watchlist:
        st.session_state[watchlist_key] = watchlist[0]
    with left:
        anchor = st.selectbox("From Watchlist", watchlist, key=watchlist_key)
        st.caption("Stocks you saved in My Assets.")
    available = [symbol for symbol in discovery if symbol != anchor]
    previous = st.session_state.get(discovery_key, [])
    retained = [symbol for symbol in previous if symbol in available][:3]
    if previous != retained:
        st.session_state[discovery_key] = retained
    with right:
        selected = st.multiselect(
            "From Market Intelligence", available, max_selections=3,
            key=discovery_key, disabled=not available,
            format_func=lambda symbol: f"{symbol} · Already in Watchlist" if symbol in watchlist else symbol,
        )
        st.caption(f"{len(discovery)} Discovery findings · {len(available)} available to compare with {anchor}.")
        if anchor in discovery:
            st.caption(f"{anchor} is also in Discovery (Already in Watchlist). It stays in the results, "
                       "but cannot be selected on both sides.")
    if not available:
        st.info("Discovery has no other stock to compare with this Watchlist selection. "
                "Choose another Watchlist stock or expand the configured Discovery universe.")
    chosen = [anchor, *selected]
    if st.button("Compare selected evidence", disabled=not selected):
        try:
            with st.spinner("Loading recorded evidence…"):
                comparison = api_client.compare_assets(profile["id"], chosen)
            st.session_state.comparison_detail = {"profile_id": profile["id"], "result": comparison}
        except api_client.APIError as exc:
            st.error(str(exc))
    saved = st.session_state.get("comparison_detail")
    if not saved or saved["profile_id"] != profile["id"]:
        return
    comparison = saved["result"]
    if comparison["symbols"] != chosen:
        st.caption("Selection changed. Click Compare selected evidence to show the new comparison.")
        return
    st.caption("Showing: " + ", ".join(comparison["symbols"]) + ". No investment winner is assigned.")
    rows = []
    for metric in comparison.get("metrics", []):
        row = {"Group": (metric.get("group") or "").replace("_", " ").title(),
               "Metric": metric_label(metric)}
        for symbol in comparison["symbols"]:
            evidence = metric.get("evidence_by_symbol", {}).get(symbol)
            row[symbol] = format_value(evidence) if evidence else "Unavailable"
        row["Period check"] = metric.get("period_status", "unconfirmed").replace("_", " ")
        rows.append(row)
    st.dataframe(rows, hide_index=True, use_container_width=True)
    with st.expander("Periods, methods and sources"):
        for metric in comparison.get("metrics", []):
            st.markdown("**" + metric_label(metric) + "**")
            for symbol in comparison["symbols"]:
                evidence = metric.get("evidence_by_symbol", {}).get(symbol)
                if evidence:
                    st.caption(f"{symbol}: {evidence.get('period', 'Period unavailable')} · "
                               f"{evidence.get('method', 'Method unavailable')}")
                    st.caption(f"Source: {evidence.get('source') or 'Unavailable'} · "
                               f"Retrieved: {evidence.get('retrieved_at') or 'Unavailable'}")
                    if evidence.get("baseline") is not None:
                        baseline_unit = "multiple" if evidence.get("group") == "valuation" else "decimal_ratio" if evidence.get("group") == "quality" else None
                        reference = format_value({"value": evidence["baseline"], "unit": baseline_unit})
                        st.caption(f"Reference: {reference} · {evidence.get('baseline_period') or 'See method'}")
    for limitation in comparison.get("limitations", []):
        st.caption(limitation)
