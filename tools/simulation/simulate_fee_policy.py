import time

from db import get_connection
from tools.ml.predict_late_probability import predict_late_probability
from tools.ml.predict_expected_late_days import predict_expected_late_days


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


def simulate_fee_policy(
    customer_late_rate,
    category,
    rental_duration,
    rental_rate,
    fee_per_day,
    current_fee_per_day=1.00
):
    """
    Simulate the effect of changing late fee.

    Revenue is evaluated using:
        expected_rental_revenue
        + expected_late_fee_revenue

    The demand response is modeled using a mild
    simulation sensitivity assumption.

    This is a simulation assumption, not an observed
    causal elasticity.
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

    # ---------------------------------------------------------
    # 1-2. Observed baseline volume (cached)
    # ---------------------------------------------------------

    baseline = _load_baseline()

    if baseline["baseline_rentals"] <= 0:
        raise ValueError("No rental data available.")

    # Mild simulation assumption:
    # higher late fees reduce demand slightly.
    # This is NOT an observed causal elasticity.
    sensitivity = 0.10

    baseline_rentals = float(baseline["baseline_rentals"])

    # ---------------------------------------------------------
    # 3. ML predictions
    # ---------------------------------------------------------

    probability_result = predict_late_probability(
        customer_late_rate=customer_late_rate,
        category=category,
        rental_duration=rental_duration,
        rental_rate=rental_rate
    )

    late_days_result = predict_expected_late_days(
        customer_late_rate=customer_late_rate,
        category=category,
        rental_duration=rental_duration,
        rental_rate=rental_rate
    )

    late_probability = float(
        probability_result["late_probability"]
    )

    expected_late_days = float(
        late_days_result["expected_late_days"]
    )

    # ---------------------------------------------------------
    # 4. Demand impact
    # ---------------------------------------------------------

    fee_ratio = (
        fee_per_day /
        current_fee_per_day
    )

    demand_factor = fee_ratio ** (-sensitivity)

    expected_rentals = (
        baseline_rentals *
        demand_factor
    )

    rental_change_pct = (
        demand_factor - 1
    ) * 100

    # ---------------------------------------------------------
    # 5. Rental revenue
    # ---------------------------------------------------------

    expected_rental_revenue = (
        expected_rentals *
        rental_rate
    )

    # ---------------------------------------------------------
    # 6. Late-fee revenue
    # ---------------------------------------------------------

    expected_late_fee_revenue = (
        expected_rentals
        * late_probability
        * expected_late_days
        * fee_per_day
    )

    # ---------------------------------------------------------
    # 7. Total revenue
    # ---------------------------------------------------------

    expected_total_revenue = (
        expected_rental_revenue
        + expected_late_fee_revenue
    )

    # ---------------------------------------------------------
    # 8. Baseline revenue
    # ---------------------------------------------------------

    baseline_rental_revenue = (
        baseline_rentals *
        rental_rate
    )

    baseline_late_fee_revenue = (
        baseline_rentals
        * late_probability
        * expected_late_days
        * current_fee_per_day
    )

    baseline_total_revenue = (
        baseline_rental_revenue
        + baseline_late_fee_revenue
    )

    # ---------------------------------------------------------
    # 9. Revenue change
    # ---------------------------------------------------------

    revenue_change = (
        expected_total_revenue
        - baseline_total_revenue
    )

    revenue_change_pct = (
        revenue_change /
        baseline_total_revenue *
        100
        if baseline_total_revenue > 0
        else 0
    )

    # ---------------------------------------------------------
    # 10. Return
    # ---------------------------------------------------------

    return {
        "fee_per_day": round(
            float(fee_per_day),
            2
        ),

        "current_fee_per_day": round(
            current_fee_per_day,
            2
        ),

        "behavioral_sensitivity": round(
            sensitivity,
            6
        ),

        "late_probability": round(
            late_probability,
            4
        ),

        "late_probability_pct": round(
            late_probability * 100,
            2
        ),

        "expected_late_days": round(
            expected_late_days,
            4
        ),

        "demand_factor": round(
            demand_factor,
            4
        ),

        "expected_rentals": round(
            expected_rentals,
            4
        ),

        "rental_change_pct": round(
            rental_change_pct,
            2
        ),

        "expected_rental_revenue": round(
            expected_rental_revenue,
            2
        ),

        "expected_late_fee_revenue": round(
            expected_late_fee_revenue,
            2
        ),

        "expected_total_revenue": round(
            expected_total_revenue,
            2
        ),

        "baseline_total_revenue": round(
            baseline_total_revenue,
            2
        ),

        "revenue_change": round(
            revenue_change,
            2
        ),

        "revenue_change_pct": round(
            revenue_change_pct,
            2
        ),

        "rental_duration": rental_duration,

        "rental_rate": round(rental_rate, 2),

        "inputs_used": probability_result.get("inputs_used"),

        "warnings": (
            probability_result.get("warnings", [])
        ),

        "scale_note": (
            "Simulated business-level revenue: the observed number of "
            "completed rentals (baseline_rentals) is scaled with the "
            "given customer/category/rate profile. It is a what-if "
            "estimate, not observed revenue."
        ),

        "data_source": {
            "rental_observations": int(baseline_rentals),
            "film_observations": baseline["film_observations"],
        }
    }
