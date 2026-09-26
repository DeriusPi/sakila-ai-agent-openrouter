import time

from db import get_connection
from tools.ml.predict_late_probability import predict_late_probability
from tools.ml.predict_expected_late_days import predict_expected_late_days
from tools.simulation.behavior import (
    apply_behavior,
    formula_text,
    late_day_opportunity_cost,
    resolve_behavior,
)


_BASELINE_CACHE = {"value": None, "loaded_at": 0.0}
_BASELINE_TTL_SECONDS = 600


def _load_baseline():
    """
    Observed baseline volume used to scale the per-rental simulation to
    business level. Cached for 10 minutes.

    FIX: previously every call loaded all 15,861 rental rows, all 1,000
    films and re-ran estimate_fee_behavior() only to read
    baseline_rentals. compare_scenarios() calls this function ~10 times,
    which made the policy page and the agent very slow (and time out on
    remote databases). The value is identical: completed rentals.
    """

    now = time.time()

    if (
        _BASELINE_CACHE["value"] is not None
        and now - _BASELINE_CACHE["loaded_at"] < _BASELINE_TTL_SECONDS
    ):
        return _BASELINE_CACHE["value"]

    conn = get_connection()

    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT COUNT(*), "
                "(SELECT COUNT(*) FROM film) "
                "FROM rental WHERE return_date IS NOT NULL"
            )
            rentals, films = cursor.fetchone()
    finally:
        conn.close()

    value = {
        "baseline_rentals": int(rentals or 0),
        "film_observations": int(films or 0),
    }

    _BASELINE_CACHE["value"] = value
    _BASELINE_CACHE["loaded_at"] = now

    return value


def _ml_predictions(customer_late_rate, category, rental_duration, rental_rate):
    probability_result = predict_late_probability(
        customer_late_rate=customer_late_rate,
        category=category,
        rental_duration=rental_duration,
        rental_rate=rental_rate,
    )
    late_days_result = predict_expected_late_days(
        customer_late_rate=customer_late_rate,
        category=category,
        rental_duration=rental_duration,
        rental_rate=rental_rate,
    )
    return probability_result, late_days_result


def _evaluate(n0, rental_rate, p0, d0, fee, current_fee, duration,
              reference_duration, params, cost_per_late_day):
    behaviour = apply_behavior(
        p0, d0, fee, current_fee, duration, reference_duration, params,
    )

    p = behaviour["late_probability"]
    d = behaviour["expected_late_days"]
    rentals = n0 * behaviour["demand_factor"]

    rental_revenue = rentals * rental_rate
    late_returns = rentals * p
    late_days_total = late_returns * d
    late_fee_revenue = late_days_total * fee
    total_revenue = rental_revenue + late_fee_revenue
    opportunity_cost = late_days_total * cost_per_late_day

    return {
        "late_probability": p,
        "expected_late_days": d,
        "demand_factor": behaviour["demand_factor"],
        "expected_rentals": rentals,
        "expected_late_returns": late_returns,
        "expected_late_days_total": late_days_total,
        "expected_rental_revenue": rental_revenue,
        "expected_late_fee_revenue": late_fee_revenue,
        "expected_total_revenue": total_revenue,
        "opportunity_cost": opportunity_cost,
        "net_value": total_revenue - opportunity_cost,
    }


def simulate_fee_policy(
    customer_late_rate,
    category,
    rental_duration,
    rental_rate,
    fee_per_day,
    current_fee_per_day=1.00,
    reference_rental_duration=None,
    late_fee_elasticity=None,
    late_days_elasticity=None,
    demand_fee_elasticity=None,
    demand_duration_elasticity=None,
):
    """
    Simulate a late-fee / rental-duration policy at business level.

    NEW behaviour model (see tools/simulation/behavior.py):
      - a higher fee LOWERS the late-return probability and the number
        of late days (deterrence), and slightly lowers rental volume;
      - a shorter rental period slightly lowers rental volume;
      - policies are evaluated by NET POLICY VALUE =
        rental revenue + late-fee revenue - opportunity cost of copies
        kept late (cost per late day measured in the database).

    The ML models give the late probability / late days at the CURRENT
    fee; the elasticities (assumptions, adjustable) translate them to the
    proposed fee. reference_rental_duration is the current rental period
    (defaults to rental_duration).
    """

    try:
        rental_rate = float(str(rental_rate).replace("$", "").strip())
        fee_per_day = float(fee_per_day)
        current_fee_per_day = float(current_fee_per_day)
    except (TypeError, ValueError):
        raise ValueError(
            "rental_rate, fee_per_day and current_fee_per_day "
            "must be numbers."
        )

    if fee_per_day <= 0:
        raise ValueError("fee_per_day must be greater than 0")

    if current_fee_per_day <= 0:
        raise ValueError(
            "current_fee_per_day must be greater than 0"
        )

    params = resolve_behavior(
        late_fee_elasticity=late_fee_elasticity,
        late_days_elasticity=late_days_elasticity,
        demand_fee_elasticity=demand_fee_elasticity,
        demand_duration_elasticity=demand_duration_elasticity,
    )

    reference_duration = (
        float(reference_rental_duration)
        if reference_rental_duration not in (None, "")
        else float(rental_duration)
    )

    # ---------------------------------------------------------
    # 1. Observed baseline volume (cached)
    # ---------------------------------------------------------

    baseline = _load_baseline()

    if baseline["baseline_rentals"] <= 0:
        raise ValueError("No rental data available.")

    n0 = float(baseline["baseline_rentals"])
    cost = late_day_opportunity_cost()
    c = float(cost["cost_per_late_day"])

    # ---------------------------------------------------------
    # 2. ML predictions at the current fee
    # ---------------------------------------------------------

    probability_result, late_days_result = _ml_predictions(
        customer_late_rate, category, rental_duration, rental_rate,
    )

    p0 = float(probability_result["late_probability"])
    d0 = float(late_days_result["expected_late_days"])

    # ---------------------------------------------------------
    # 3. Proposed policy vs current policy
    # ---------------------------------------------------------

    proposed = _evaluate(
        n0, rental_rate, p0, d0, fee_per_day, current_fee_per_day,
        rental_duration, reference_duration, params, c,
    )

    if abs(reference_duration - float(rental_duration)) < 1e-9:
        base_p0, base_d0 = p0, d0
    else:
        base_prob, base_days = _ml_predictions(
            customer_late_rate, category, reference_duration, rental_rate,
        )
        base_p0 = float(base_prob["late_probability"])
        base_d0 = float(base_days["expected_late_days"])

    current = _evaluate(
        n0, rental_rate, base_p0, base_d0, current_fee_per_day,
        current_fee_per_day, reference_duration, reference_duration,
        params, c,
    )

    def change(key):
        delta = proposed[key] - current[key]
        pct = delta / current[key] * 100 if current[key] else 0.0
        return round(delta, 2), round(pct, 2)

    revenue_change, revenue_change_pct = change("expected_total_revenue")
    net_change, net_change_pct = change("net_value")
    late_change, late_change_pct = change("expected_late_returns")

    warnings = list(probability_result.get("warnings", []))

    return {
        "fee_per_day": round(fee_per_day, 2),
        "current_fee_per_day": round(current_fee_per_day, 2),
        "rental_duration": rental_duration,
        "reference_rental_duration": reference_duration,
        "rental_rate": round(rental_rate, 2),

        # ML at the current fee
        "ml_late_probability": round(p0, 4),
        "ml_expected_late_days": round(d0, 4),

        # after the fee response
        "late_probability": round(proposed["late_probability"], 4),
        "late_probability_pct": round(proposed["late_probability"] * 100, 2),
        "expected_late_days": round(proposed["expected_late_days"], 4),
        "on_time_rate_pct": round(
            (1 - proposed["late_probability"]) * 100, 2
        ),

        "demand_factor": round(proposed["demand_factor"], 4),
        "expected_rentals": round(proposed["expected_rentals"], 4),
        "rental_change_pct": round(
            (proposed["demand_factor"] - 1) * 100, 2
        ),
        "expected_late_returns": round(proposed["expected_late_returns"], 1),
        "late_returns_change": late_change,
        "late_returns_change_pct": late_change_pct,
        "expected_late_days_total": round(
            proposed["expected_late_days_total"], 1
        ),

        "expected_rental_revenue": round(
            proposed["expected_rental_revenue"], 2
        ),
        "expected_late_fee_revenue": round(
            proposed["expected_late_fee_revenue"], 2
        ),
        "expected_total_revenue": round(
            proposed["expected_total_revenue"], 2
        ),
        "opportunity_cost": round(proposed["opportunity_cost"], 2),
        "net_value": round(proposed["net_value"], 2),

        "baseline_total_revenue": round(current["expected_total_revenue"], 2),
        "baseline_net_value": round(current["net_value"], 2),
        "baseline_late_returns": round(current["expected_late_returns"], 1),
        "revenue_change": revenue_change,
        "revenue_change_pct": revenue_change_pct,
        "net_value_change": net_change,
        "net_value_change_pct": net_change_pct,

        "behavior_assumptions": params,
        "cost_per_late_day": c,
        "cost_basis": cost,
        "formula": formula_text(),

        # kept for backward compatibility
        "behavioral_sensitivity": params["demand_fee_elasticity"],

        "inputs_used": probability_result.get("inputs_used"),
        "warnings": warnings,
        "scale_note": (
            "Simulated business-level values: the observed number of "
            "completed rentals is scaled with the given profile. A higher "
            "fee lowers late returns via assumed elasticities (Sakila has "
            "no fee variation to estimate them). What-if estimate, not "
            "observed revenue."
        ),
        "data_source": {
            "rental_observations": int(n0),
            "film_observations": baseline["film_observations"],
        },
    }
