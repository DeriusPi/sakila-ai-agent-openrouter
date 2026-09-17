from tools.ml.predict_late_probability import predict_late_probability
from tools.ml.predict_expected_late_days import predict_expected_late_days
from tools.data.get_late_fee_data import get_late_fee_data
from tools.data.get_film_data import get_film_data
from tools.analysis.estimate_fee_behavior import estimate_fee_behavior


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

    if fee_per_day <= 0:
        raise ValueError("fee_per_day must be greater than 0")

    if current_fee_per_day <= 0:
        raise ValueError(
            "current_fee_per_day must be greater than 0"
        )

    # ---------------------------------------------------------
    # 1. Load observed data
    # ---------------------------------------------------------

    rental_data = get_late_fee_data()
    film_data = get_film_data()

    if not rental_data:
        raise ValueError("No rental data available.")

    if not film_data:
        raise ValueError("No film data available.")

    # ---------------------------------------------------------
    # 2. Derive behavioral parameters
    # ---------------------------------------------------------

    behavior = estimate_fee_behavior(
        rental_data=rental_data,
        film_data=film_data
    )

    # Mild simulation assumption:
    # higher late fees reduce demand slightly.
    # This is NOT an observed causal elasticity.
    sensitivity = 0.10

    baseline_rentals = float(
        behavior["simulation"]["baseline_rentals"]
    )

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

        "data_source": {
            "rental_observations": len(
                rental_data
            ),

            "film_observations": len(
                film_data
            )
        }
    }
