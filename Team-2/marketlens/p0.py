"""Deterministic P0 evidence from Team 1's versioned intelligence contract.

No access to Sectors raw sections. Levels supply context; deviations supply
direction-neutral research salience, never a good/bad investment verdict.
"""

from __future__ import annotations

import math
from statistics import median
from typing import Any


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    value = float(value)
    return value if math.isfinite(value) else None


def _year(row: dict) -> int | None:
    value = row.get("year")
    return value if type(value) is int and 1900 <= value <= 2100 else None


def build_p0_evidence(company: dict, methodology: dict) -> tuple[list[dict], list[str]]:
    evidence: list[dict] = []
    limitations: list[str] = []
    contract = company.get("intelligence")
    if not isinstance(contract, dict) or contract.get("schema_version") not in {"1.0", "1.1"}:
        return [], ["Valuation and quality unavailable: Team 1 intelligence contract version 1.0 or 1.1 is required."]
    source, retrieved = contract.get("source_endpoint"), contract.get("retrieved_at")
    if not isinstance(source, str) or not source or not isinstance(retrieved, str) or not retrieved:
        return [], ["Valuation and quality unavailable: normalized evidence provenance is missing."]
    if isinstance(contract.get("limitations"), list):
        limitations.extend(item for item in contract["limitations"] if isinstance(item, str))
    policy = methodology["p0"]

    def emit(group, name, value, *, period, unit, method, observed=None,
             baseline=None, baseline_period=None, threshold=None, inputs=None, kind="observed"):
        value = _number(value)
        if value is None:
            return
        strength = policy["context_level_strength"]
        strength_method = "Fixed context-availability strength; the magnitude of the level is not rewarded"
        if threshold is not None:
            strength = min(abs(value) / threshold, 1.0)
            strength_method = f"min(abs(derived difference) / {threshold}, 1); direction-neutral"
        evidence.append({
            "group": group, "metric": name, "value": round(value, 8),
            "baseline": baseline, "period": period, "method": method,
            "source": source, "observed_at": observed, "retrieved_at": retrieved,
            "strength": round(strength, 6), "unit": unit, "kind": kind,
            "baseline_period": baseline_period, "inputs": inputs or {},
            "strength_method": strength_method,
        })

    valuation = contract.get("valuation")
    valuation = valuation if isinstance(valuation, dict) else {}
    if valuation.get("unit") == "multiple":
        forward = _number(valuation.get("forward_pe"))
        if forward is not None:
            emit("valuation", "forward_pe", forward, period="Provider estimate; forecast horizon unavailable",
                 unit="multiple", method="Provider-supplied forward PE; estimate, not a historical observation",
                 kind="estimate", inputs={"associated_close_date": valuation.get("price_as_of")})
        latest = valuation.get("latest")
        if isinstance(latest, dict) and (year := _year(latest)) is not None:
            period = f"Provider-labelled valuation year {year}; calculation basis not supplied"
            for name in ("pe", "pb", "peg"):
                value = _number(latest.get(name))
                if value is None:
                    continue
                emit("valuation", name, value, period=period, unit="multiple",
                     method=f"Provider-supplied {name.upper()} for labelled year {year}; not assumed to be a current TTM ratio",
                     observed=str(year))
                # PEG and forward PE are context only: the available payload does
                # not establish a comparable forecast/growth basis for a gap.
                if name not in {"pe", "pb"}:
                    continue
                if value <= 0:
                    limitations.append(f"{name.upper()} context gaps unavailable: latest multiple is non-positive.")
                    continue
                rows = valuation.get("history")
                older = [(row["year"], _number(row.get(name))) for row in rows
                         if isinstance(row, dict) and _year(row) is not None and row["year"] < year
                         and _number(row.get(name)) is not None and _number(row.get(name)) > 0] if isinstance(rows, list) else []
                if len({item[0] for item in older}) >= policy["min_history_observations"]:
                    older.sort()
                    reference = median(item[1] for item in older)
                    if _number(reference) is not None and reference > 0:
                        baseline_period = ", ".join(str(y) for y, _ in older)
                        emit("valuation", f"{name}_vs_history", value / reference - 1,
                             period=period, unit="decimal_ratio", baseline=reference,
                             baseline_period=f"Median of positive multiples from provider years {baseline_period}",
                             method="(latest labelled-year multiple / median of positive prior-year multiples) - 1; descriptive series difference, not fair value",
                             observed=str(year), threshold=policy["valuation_gap_threshold"],
                             inputs={"latest_multiple": value, "prior_years": [y for y, _ in older]}, kind="derived")
                else:
                    limitations.append(f"{name.upper()} historical context unavailable: at least {policy['min_history_observations']} positive prior-year observations are required.")
                peer = _number(latest.get(f"{name}_peer_avg"))
                if peer is not None and peer > 0:
                    emit("valuation", f"{name}_vs_peer", value / peer - 1,
                         period=period, unit="decimal_ratio", baseline=peer,
                         baseline_period=f"Provider peer average, same labelled year {year}",
                         method="(company multiple / provider peer average in the same labelled year) - 1; descriptive difference, not a valuation verdict",
                         observed=str(year), threshold=policy["valuation_gap_threshold"],
                         inputs={"company_multiple": value}, kind="derived")
                else:
                    limitations.append(f"{name.upper()} peer context unavailable: a positive same-year provider peer average is required.")
    else:
        limitations.append("Valuation unavailable: normalized unit must be multiple.")

    quality = contract.get("quality")
    quality = quality if isinstance(quality, dict) else {}
    latest = quality.get("latest")
    if quality.get("unit") == "decimal_ratio" and isinstance(latest, dict) and (year := _year(latest)) is not None:
        history = quality.get("history")
        previous = next((row for row in history if isinstance(row, dict) and _year(row) == year - 1), None) if isinstance(history, list) else None
        for name, threshold in policy["quality_change_thresholds"].items():
            value = _number(latest.get(name))
            if value is None:
                continue
            emit("quality", name, value, period=f"Annual financial ratio, {year}",
                 unit="decimal_ratio", method="Provider-supplied profitability ratio; decimal fraction (multiply by 100 only for display)",
                 observed=str(year))
            baseline = _number(previous.get(name)) if previous else None
            if baseline is not None:
                emit("quality", f"{name}_change", value - baseline,
                     period=f"Financial year {year - 1} to {year}", unit="decimal_ratio_change",
                     method="Latest annual ratio minus the immediately preceding year's ratio; display as percentage-point change, not percent growth",
                     baseline=baseline, baseline_period=str(year - 1), observed=str(year),
                     threshold=threshold, inputs={"latest_ratio": value}, kind="derived")
            else:
                limitations.append(f"{name} annual change unavailable: no numeric observation for financial year {year - 1}.")
    elif quality.get("unit") != "decimal_ratio":
        limitations.append("Quality unavailable: normalized unit must be decimal_ratio.")

    for group in ("valuation", "quality"):
        if not any(item["group"] == group for item in evidence):
            limitations.append(f"{group.title()} evidence unavailable: no usable normalized metrics in the latest source period.")
    if evidence:
        limitations.extend([
            "Company-report years are independent of the selected market-data horizon; source years and report retrieval time must remain visible.",
            "P0 salience thresholds and the context-availability floor are MVP methodology choices, not calibrated investment-quality scores.",
        ])
    return evidence, list(dict.fromkeys(limitations))
