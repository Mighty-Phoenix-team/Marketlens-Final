"""Income context only: higher yields/payouts do not earn higher scores."""

from .p0 import _number, _year


def build_income_evidence(company, methodology):
    contract = company.get("intelligence")
    if not isinstance(contract, dict) or contract.get("schema_version") != "1.1":
        return [], ["Income unavailable: Team 1 intelligence contract version 1.1 is required."]
    income = contract.get("income")
    if not isinstance(income, dict) or income.get("unit") != "decimal_ratio":
        return [], ["Income unavailable: no normalized dividend ratios."]
    source, retrieved = income.get("source_endpoint"), income.get("retrieved_at")
    if not all(isinstance(v, str) and v for v in (source, retrieved)):
        return [], ["Income unavailable: normalized source provenance is missing."]
    limitations = [s for s in income.get("limitations", []) if isinstance(s, str)]
    evidence = []

    def emit(name, value, period, method, inputs=None):
        value = _number(value)
        if value is None:
            return
        evidence.append({
            "group": "income", "metric": name, "value": round(value, 8),
            "unit": "decimal_ratio", "kind": "observed", "baseline": None,
            "baseline_period": None, "period": period, "method": method,
            "observed_at": None, "source": source, "retrieved_at": retrieved,
            "inputs": inputs or {},
            "strength": methodology["income"]["context_level_strength"],
            "strength_method": "Fixed context-availability strength; neither yield nor payout magnitude is rewarded",
        })

    emit("dividend_yield_ttm", income.get("dividend_yield_ttm"),
         "Trailing twelve months; precise window end unavailable",
         "Provider yield_ttm; historical trailing yield, not expected future return")
    period = _number(income.get("average_period"))
    label = f"{period:g}" if period is not None else "unavailable"
    emit("average_dividend_yield", income.get("average_dividend_yield"),
         f"Provider average period label {label}; units and endpoints unconfirmed",
         "Provider average yield; no TTM comparison is calculated",
         {"provider_period_label": period})
    for name in ("payout_ratio", "cash_payout_ratio"):
        emit(name, income.get(name), "Provider ratio; reporting period unavailable",
             "Provider-supplied decimal ratio; denominator methodology unconfirmed; values above 100% retained")
    latest = income.get("latest")
    if isinstance(latest, dict) and (year := _year(latest)) is not None:
        emit("historical_dividend_yield", latest.get("total_yield"),
             f"Provider-labelled dividend year {year}; completeness unconfirmed",
             "Provider total_yield for latest labelled year; not TTM and not assumed to be a completed annual total",
             {"provider_year": year})
    if not evidence:
        limitations.append("Income evidence unavailable: no usable normalized ratios; missing values were not replaced by zero.")
    else:
        limitations.append("Income levels receive fixed context-availability strength; they do not measure dividend safety, attractiveness or future returns.")
    return evidence, list(dict.fromkeys(limitations))
