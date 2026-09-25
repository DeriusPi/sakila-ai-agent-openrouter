from tools.ml.predict_late_probability import predict_late_probability
from tools.ml.predict_expected_late_days import predict_expected_late_days


def simulate_rental_policy(
    customer_late_rate,
    category,
    current_rental_duration,
    rental_rate,
    proposed_rental_duration,
    fee_per_day=1.00
):
    """
    Simulate the effect of changing rental duration.

    The proposed rental duration is used as the input to the ML models
    to estimate how the customer's late-return behavior may change.
    """

    fee_per_day = float(fee_per_day)
    current_rental_duration = int(float(current_rental_duration))
    proposed_rental_duration = int(float(proposed_rental_duration))

    # -----------------------------
    # 1. Current policy prediction
    # -----------------------------

    current_probability = predict_late_probability(
        customer_late_rate=customer_late_rate,
        category=category,
        rental_duration=current_rental_duration,
        rental_rate=rental_rate
    )

    current_late_days = predict_expected_late_days(
        customer_late_rate=customer_late_rate,
        category=category,
        rental_duration=current_rental_duration,
        rental_rate=rental_rate
    )

    # -----------------------------
    # 2. Proposed policy prediction
    # -----------------------------

    proposed_probability = predict_late_probability(
        customer_late_rate=customer_late_rate,
        category=category,
        rental_duration=proposed_rental_duration,
        rental_rate=rental_rate
    )

    proposed_late_days = predict_expected_late_days(
        customer_late_rate=customer_late_rate,
        category=category,
        rental_duration=proposed_rental_duration,
        rental_rate=rental_rate
    )

    # -----------------------------
    # 3. Expected late-fee revenue
    # -----------------------------

    current_expected_revenue = (
        current_probability["late_probability"]
        * current_late_days["expected_late_days"]
        * fee_per_day
    )

    proposed_expected_revenue = (
        proposed_probability["late_probability"]
        * proposed_late_days["expected_late_days"]
        * fee_per_day
    )

    revenue_change = (
        proposed_expected_revenue
        - current_expected_revenue
    )

    # -----------------------------
    # 4. Return result
    # -----------------------------

    return {
        "current_policy": {
            "rental_duration": current_rental_duration,
            "late_probability": round(
                current_probability["late_probability"],
                4
            ),
            "expected_late_days": round(
                current_late_days["expected_late_days"],
                4
            ),
            "expected_late_fee_revenue": round(
                current_expected_revenue,
                2
            )
        },

        "proposed_policy": {
            "rental_duration": proposed_rental_duration,
            "late_probability": round(
                proposed_probability["late_probability"],
                4
            ),
            "expected_late_days": round(
                proposed_late_days["expected_late_days"],
                4
            ),
            "expected_late_fee_revenue": round(
                proposed_expected_revenue,
                2
            )
        },

        "revenue_change": round(
            revenue_change,
            2
        ),

        # FIX: the old text always said "Increase rental duration",
        # even when the proposed duration was shorter.
        "recommendation": (
            (
                "Increase rental duration"
                if proposed_rental_duration > current_rental_duration
                else "Shorten rental duration"
            )
            + f" to {proposed_rental_duration} days"
            if revenue_change > 0
            else "Keep current rental duration"
        ),

        "unit": (
            "Expected late-fee revenue PER RENTAL for this profile "
            "(late_probability x expected_late_days x fee_per_day). "
            "Use compare_scenarios for business-level revenue."
        ),

        "inputs_used": current_probability.get("inputs_used"),
        "warnings": current_probability.get("warnings", []),
    }
