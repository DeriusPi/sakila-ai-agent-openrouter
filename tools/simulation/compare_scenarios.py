import time

from tools.simulation.simulate_fee_policy import simulate_fee_policy
from tools.optimization.derive_fee_constraint import derive_fee_constraint


_FEE_CONSTRAINT_CACHE = {"value": None, "loaded_at": 0.0}
_FEE_CONSTRAINT_TTL_SECONDS = 600


def _cached_fee_constraint():
    """derive_fee_constraint() scans all rentals - cache it for 10 min."""

    now = time.time()

    if (
        _FEE_CONSTRAINT_CACHE["value"] is not None
        and now - _FEE_CONSTRAINT_CACHE["loaded_at"]
        < _FEE_CONSTRAINT_TTL_SECONDS
    ):
        return _FEE_CONSTRAINT_CACHE["value"]

    value = derive_fee_constraint()
    _FEE_CONSTRAINT_CACHE["value"] = value
    _FEE_CONSTRAINT_CACHE["loaded_at"] = now

    return value


def _to_number_list(values, cast=float):
    if values is None:
        return None

    if not isinstance(values, (list, tuple)):
        values = [values]

    out = []

    for value in values:
        try:
            out.append(cast(float(str(value).replace("$", "").strip())))
        except (TypeError, ValueError):
            continue

    return out or None


def _scenario_row(policy_type, policy, fee, duration, sim, baseline_total):
    revenue_change = sim["expected_total_revenue"] - baseline_total

    return {
        "policy_type": policy_type,
        "policy": policy,
        "fee_per_day": round(float(fee), 2),
        "rental_duration": int(duration),
        "late_probability": sim["late_probability"],
        "expected_late_days": sim["expected_late_days"],
        "demand_factor": sim["demand_factor"],
        "expected_rentals": sim["expected_rentals"],
        "expected_rental_revenue": sim["expected_rental_revenue"],
        "expected_late_fee_revenue": sim["expected_late_fee_revenue"],
        "expected_total_revenue": sim["expected_total_revenue"],
        "revenue_change": round(revenue_change, 2),
        "revenue_change_pct": (
            round(revenue_change / baseline_total * 100, 2)
            if baseline_total > 0
            else 0.0
        ),
    }


def compare_scenarios(
    customer_late_rate,
    category,
    current_rental_duration,
    rental_rate,
    fee_options=None,
    rental_duration_options=None,
    current_fee_per_day=1.00
):
    """
    Compare fee-policy and rental-duration scenarios.

    All scenarios are evaluated with the SAME business-level
    simulation (simulate_fee_policy), so their expected_total_revenue
    values are directly comparable and can be ranked together.

    FIX: rental-duration scenarios used to come from
    simulate_rental_policy(), which returns a per-rental late-fee value
    (about $1), while fee scenarios were business-level totals
    (about $70,000). Both were sorted in one list, so duration policies
    could never win and the comparison was meaningless.

    A "current" scenario (current fee + current duration) is included as
    the baseline, so the optimiser can also conclude that keeping the
    current policy is best.

    The feasible fee range is derived from historical late-fee
    observations in the Sakila database.
    """

    try:
        current_rental_duration = int(float(current_rental_duration))
    except (TypeError, ValueError):
        raise ValueError("current_rental_duration must be a number of days.")

    # ---------------------------------------------------------
    # 1. Derive fee constraint from historical DB data
    # ---------------------------------------------------------

    fee_constraint = _cached_fee_constraint()

    lower_fee = float(fee_constraint["lower_bound"])
    upper_fee = float(fee_constraint["upper_bound"])
    current_fee = float(fee_constraint["current_fee_per_day"])

    # ---------------------------------------------------------
    # 2. Fee options
    # ---------------------------------------------------------

    fee_options = _to_number_list(fee_options, float)

    if fee_options is None:
        fee_options = [
            lower_fee,
            lower_fee + (upper_fee - lower_fee) * 0.25,
            lower_fee + (upper_fee - lower_fee) * 0.50,
            lower_fee + (upper_fee - lower_fee) * 0.75,
            upper_fee,
        ]

    fee_options = sorted(set(round(float(fee), 2) for fee in fee_options))

    # ---------------------------------------------------------
    # 3. Rental duration options
    # ---------------------------------------------------------

    rental_duration_options = _to_number_list(rental_duration_options, int)

    if rental_duration_options is None:
        rental_duration_options = [3, 4, 5, 6, 7]

    rental_duration_options = sorted(set(rental_duration_options))

    # ---------------------------------------------------------
    # 4. Baseline = current fee + current duration
    # ---------------------------------------------------------

    baseline_sim = simulate_fee_policy(
        customer_late_rate=customer_late_rate,
        category=category,
        rental_duration=current_rental_duration,
        rental_rate=rental_rate,
        fee_per_day=current_fee,
        current_fee_per_day=current_fee,
    )

    baseline_total = float(baseline_sim["expected_total_revenue"])

    current_scenario = _scenario_row(
        "current",
        (
            f"Keep current (${current_fee:.2f}/day, "
            f"{current_rental_duration} days)"
        ),
        current_fee,
        current_rental_duration,
        baseline_sim,
        baseline_total,
    )

    # ---------------------------------------------------------
    # 5. Fee scenarios (duration unchanged)
    # ---------------------------------------------------------

    fee_scenarios = []
    skipped_fee_options = []

    for fee in fee_options:

        # Only evaluate fees inside the DB-derived range.
        if fee < lower_fee or fee > upper_fee:
            skipped_fee_options.append(fee)
            continue

        if abs(fee - current_fee) < 1e-9:
            continue

        sim = simulate_fee_policy(
            customer_late_rate=customer_late_rate,
            category=category,
            rental_duration=current_rental_duration,
            rental_rate=rental_rate,
            fee_per_day=fee,
            current_fee_per_day=current_fee,
        )

        fee_scenarios.append(
            _scenario_row(
                "fee",
                f"${fee:.2f}/day",
                fee,
                current_rental_duration,
                sim,
                baseline_total,
            )
        )

    # ---------------------------------------------------------
    # 6. Rental-duration scenarios (fee unchanged, same scale)
    # ---------------------------------------------------------

    rental_duration_scenarios = []

    for duration in rental_duration_options:

        if duration == current_rental_duration or duration <= 0:
            continue

        sim = simulate_fee_policy(
            customer_late_rate=customer_late_rate,
            category=category,
            rental_duration=duration,
            rental_rate=rental_rate,
            fee_per_day=current_fee,
            current_fee_per_day=current_fee,
        )

        rental_duration_scenarios.append(
            _scenario_row(
                "rental_duration",
                f"{duration} days",
                current_fee,
                duration,
                sim,
                baseline_total,
            )
        )

    # ---------------------------------------------------------
    # 7. Combine and rank scenarios
    # ---------------------------------------------------------

    all_scenarios = (
        [current_scenario]
        + fee_scenarios
        + rental_duration_scenarios
    )

    all_scenarios.sort(
        key=lambda x: x["expected_total_revenue"],
        reverse=True
    )

    for index, scenario in enumerate(all_scenarios, start=1):
        scenario["rank"] = index

    best_scenario = all_scenarios[0] if all_scenarios else None

    result = {
        "current_scenario": current_scenario,
        "fee_scenarios": fee_scenarios,
        "rental_duration_scenarios": rental_duration_scenarios,
        "all_scenarios": all_scenarios,
        "best_scenario": best_scenario,

        # DB-derived fee constraint
        "fee_constraint": fee_constraint,

        "fee_range": {
            "lower_bound": lower_fee,
            "upper_bound": upper_fee,
            "current_fee_per_day": current_fee
        },

        "inputs_used": baseline_sim.get("inputs_used"),
        "scale_note": baseline_sim.get("scale_note"),
        "assumptions": [
            "Fee scenarios: demand factor = (fee / current_fee) ^ -0.10 "
            "(simulation assumption, not an observed elasticity).",
            "Rental-duration scenarios: demand is held constant; only "
            "late probability and expected late days change via the ML "
            "models.",
            "Late-return behaviour is not modelled as reacting to the fee.",
        ],
    }

    warnings = list(baseline_sim.get("warnings") or [])

    if skipped_fee_options:
        warnings.append(
            "Fee options outside the DB-derived range "
            f"${lower_fee:.2f}-${upper_fee:.2f}/day were skipped: "
            + ", ".join(f"${fee:.2f}" for fee in skipped_fee_options)
        )

    if warnings:
        result["warnings"] = warnings

    return result
