"""Income mapping verified against the user's dividend-only BBCA capture."""

from .models import IncomeData, IncomeYear


def normalize_income(raw, source_endpoint, retrieved_at):
    # Imported here to share numeric/year rules without a module import cycle.
    from .intelligence import finite_number, _date, _history

    if not isinstance(raw, dict):
        return None
    limitations = []

    def number(value, label):
        result = finite_number(value)
        if value is not None and result is None:
            limitations.append(f"Income {label}: invalid numeric value treated as unavailable.")
        return result

    history = raw.get("historical_dividends")
    rows = [{**value, "year": key} for key, value in history.items()
            if isinstance(value, dict)] if isinstance(history, dict) else None
    points = [IncomeYear(**row) for row in _history(
        rows, ("total_yield", "total_dividend"), "Income", limitations)]
    average = raw.get("dividend_yield_avg")
    average = average if isinstance(average, dict) else {}
    period = number(average.get("period"), "average period")
    if period is not None and period <= 0:
        period = None
        limitations.append("Income average period is non-positive and treated as unavailable.")
    limitations.extend([
        "Dividend yield TTM is trailing, not a forecast; its exact window end and price basis are unavailable.",
        "Average dividend yield has a provider period label; period units, endpoints and averaging method are not confirmed. It is not a like-for-like TTM benchmark.",
        "Payout and cash payout ratios have no confirmed reporting period or denominator methodology; values above 100% are preserved, not an automatic sustainability verdict.",
        "Historical dividend years are provider labels; completeness and split adjustments are unconfirmed. A current-year total is not a completed annual observation.",
        "Nominal dividend amounts have unconfirmed currency and per-share basis; they are retained in the contract but excluded from evidence and scoring.",
        "Last ex-dividend date is an event date, not the observation date of yield or payout ratios.",
    ])
    if raw.get("upcoming_dividends") is None:
        limitations.append("Upcoming dividend data is unavailable; null does not establish that no dividend is scheduled.")
    return IncomeData(
        dividend_yield_ttm=number(raw.get("yield_ttm"), "yield_ttm"),
        average_dividend_yield=number(average.get("avg_yield"), "average yield"),
        average_period=period,
        payout_ratio=number(raw.get("payout_ratio"), "payout_ratio"),
        cash_payout_ratio=number(raw.get("cash_payout_ratio"), "cash_payout_ratio"),
        dividend_ttm=number(raw.get("dividend_ttm"), "dividend_ttm"),
        last_ex_dividend_date=_date(raw.get("last_ex_dividend_date")),
        latest=points[-1] if points else None, history=points,
        source_endpoint=source_endpoint, retrieved_at=retrieved_at,
        limitations=list(dict.fromkeys(limitations)),
    )
