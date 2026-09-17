from tools.simulation.simulate_fee_policy import simulate_fee_policy
from tools.simulation.simulate_rental_policy import simulate_rental_policy
from tools.optimization.derive_fee_constraint import derive_fee_constraint


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

    Fee scenarios are evaluated using expected total revenue.

    The feasible fee range is derived from historical
    late-fee observations in the Sakila database.
    """

    # ---------------------------------------------------------
    # 1. Derive fee constraint from historical DB data
    # ---------------------------------------------------------

    fee_constraint = derive_fee_constraint()

    lower_fee = float(
        fee_constraint["lower_bound"]
    )

    upper_fee = float(
        fee_constraint["upper_bound"]
    )

    current_fee = float(
        fee_constraint["current_fee_per_day"]
    )

    # ---------------------------------------------------------
    # 2. Generate fee options
    # ---------------------------------------------------------

    if fee_options is None:
        # Use a small set of policy points inside the
        # historically derived fee range.
        fee_options = [
            lower_fee,
            lower_fee + (upper_fee - lower_fee) * 0.25,
            lower_fee + (upper_fee - lower_fee) * 0.50,
            lower_fee + (upper_fee - lower_fee) * 0.75,
            upper_fee
        ]

        # Round and remove duplicates
        fee_options = sorted(
            set(round(float(fee), 2) for fee in fee_options)
        )

    # ---------------------------------------------------------
    # 3. Rental duration options
    # ---------------------------------------------------------

    if rental_duration_options is None:
        rental_duration_options = [3, 4, 5, 6, 7]

    # ---------------------------------------------------------
    # 4. Fee scenarios
    # ---------------------------------------------------------

    fee_scenarios = []

    for fee in fee_options:

        # Only evaluate fees inside the DB-derived range.
        if fee < lower_fee or fee > upper_fee:
            continue

        result = simulate_fee_policy(
            customer_late_rate=customer_late_rate,
            category=category,
            rental_duration=current_rental_duration,
            rental_rate=rental_rate,
            fee_per_day=fee,
            current_fee_per_day=current_fee
        )

        fee_scenarios.append({
            "policy_type": "fee",
            "policy": f"${fee:.2f}/day",
            "fee_per_day": fee,
            "rental_duration": current_rental_duration,
            "late_probability": result["late_probability"],
            "expected_late_days": result["expected_late_days"],
            "demand_factor": result["demand_factor"],
            "expected_rentals": result["expected_rentals"],
            "expected_rental_revenue": result[
                "expected_rental_revenue"
            ],
            "expected_late_fee_revenue": result[
                "expected_late_fee_revenue"
            ],
            "expected_total_revenue": result[
                "expected_total_revenue"
            ],
            "revenue_change": result[
                "revenue_change"
            ],
            "revenue_change_pct": result[
                "revenue_change_pct"
            ]
        })

    # ---------------------------------------------------------
    # 5. Rental-duration scenarios
    # ---------------------------------------------------------

    rental_duration_scenarios = []

    for duration in rental_duration_options:

        if duration == current_rental_duration:
            continue

        result = simulate_rental_policy(
            customer_late_rate=customer_late_rate,
            category=category,
            current_rental_duration=current_rental_duration,
            rental_rate=rental_rate,
            proposed_rental_duration=duration,
            fee_per_day=current_fee
        )

        proposed = result["proposed_policy"]

        rental_duration_scenarios.append({
            "policy_type": "rental_duration",
            "policy": f"{duration} days",
            "fee_per_day": current_fee,
            "rental_duration": duration,
            "late_probability": proposed[
                "late_probability"
            ],
            "expected_late_days": proposed[
                "expected_late_days"
            ],
            "expected_late_fee_revenue": proposed[
                "expected_late_fee_revenue"
            ],
            "expected_total_revenue": proposed.get(
                "expected_total_revenue",
                proposed["expected_late_fee_revenue"]
            )
        })

    # ---------------------------------------------------------
    # 6. Combine and rank scenarios
    # ---------------------------------------------------------

    all_scenarios = (
        fee_scenarios +
        rental_duration_scenarios
    )

    all_scenarios.sort(
        key=lambda x: x["expected_total_revenue"],
        reverse=True
    )

    for index, scenario in enumerate(
        all_scenarios,
        start=1
    ):
        scenario["rank"] = index

    best_scenario = (
        all_scenarios[0]
        if all_scenarios
        else None
    )

    return {
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
        }
    }
