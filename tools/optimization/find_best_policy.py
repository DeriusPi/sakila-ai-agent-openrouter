from tools.simulation.compare_scenarios import compare_scenarios


def find_best_policy(
    customer_late_rate,
    category,
    current_rental_duration,
    rental_rate,
    fee_options=None,
    rental_duration_options=None,
    current_fee_per_day=1.00
):
    """
    Find the policy scenario with the highest
    expected total revenue.

    Fee constraints are derived from historical
    late-fee observations in the Sakila database
    and passed through the optimization pipeline.
    """

    comparison = compare_scenarios(
        customer_late_rate=customer_late_rate,
        category=category,
        current_rental_duration=current_rental_duration,
        rental_rate=rental_rate,
        fee_options=fee_options,
        rental_duration_options=rental_duration_options,
        current_fee_per_day=current_fee_per_day
    )

    return {
        "all_scenarios": comparison["all_scenarios"],
        "best_policy": comparison["best_scenario"],

        # Pass DB-derived fee constraint to the next layer
        "fee_constraint": comparison.get(
            "fee_constraint",
            {}
        ),

        "fee_range": comparison.get(
            "fee_range",
            {}
        )
    }
