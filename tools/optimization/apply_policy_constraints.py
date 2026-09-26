from tools.optimization.find_best_policy import find_best_policy


def apply_policy_constraints(
    customer_late_rate,
    category,
    current_rental_duration,
    rental_rate,
    fee_options=None,
    rental_duration_options=None,
    current_fee_per_day=1.00,
    min_rental_duration=3,
    max_rental_duration=7,
    max_late_probability=None,
    allow_higher_late_rate=False,
    **behavior
):
    """
    Apply business constraints to generated policy scenarios.

    The feasible late-fee range is derived from historical
    late-fee observations in the Sakila database.

    Rental duration is constrained by the specified
    minimum and maximum values.

    NEW service-level constraint: by default a policy may not INCREASE
    the late-return probability above the current policy (otherwise
    "shorter rentals -> more customers late -> more fees" always wins).
    max_late_probability (0-1) sets an explicit ceiling instead;
    allow_higher_late_rate=True switches the constraint off.

    Feasible scenarios are ranked by net policy value.
    """

    result = find_best_policy(
        customer_late_rate=customer_late_rate,
        category=category,
        current_rental_duration=current_rental_duration,
        rental_rate=rental_rate,
        fee_options=fee_options,
        rental_duration_options=rental_duration_options,
        current_fee_per_day=current_fee_per_day,
        **behavior
    )

    all_scenarios = result["all_scenarios"]
    current_scenario = result.get("current_scenario") or {}

    late_ceiling = None
    if max_late_probability not in (None, ""):
        late_ceiling = float(max_late_probability)
        if late_ceiling > 1:
            late_ceiling = late_ceiling / 100.0
    elif not allow_higher_late_rate and current_scenario:
        late_ceiling = float(current_scenario.get("late_probability", 1.0))

    fee_constraint = result.get(
        "fee_constraint",
        {}
    )

    lower_fee = fee_constraint.get(
        "lower_bound"
    )

    upper_fee = fee_constraint.get(
        "upper_bound"
    )

    feasible_scenarios = []
    rejected_scenarios = []

    # ---------------------------------------------------------
    # 1. Apply constraints
    # ---------------------------------------------------------

    for scenario in all_scenarios:

        duration = scenario["rental_duration"]
        fee = scenario.get("fee_per_day")

        violations = []

        # Fee constraint
        if (
            scenario["policy_type"] == "fee"
            and lower_fee is not None
            and fee < lower_fee
        ):
            violations.append(
                f"fee below historical lower bound "
                f"${lower_fee:.2f}/day"
            )

        if (
            scenario["policy_type"] == "fee"
            and upper_fee is not None
            and fee > upper_fee
        ):
            violations.append(
                f"fee exceeds historical upper bound "
                f"${upper_fee:.2f}/day"
            )

        # Service-level constraint (late-return probability)
        if (
            late_ceiling is not None
            and float(scenario.get("late_probability", 0)) > late_ceiling + 1e-6
        ):
            violations.append(
                f"late-return probability "
                f"{float(scenario['late_probability']) * 100:.2f}% is above "
                f"the allowed {late_ceiling * 100:.2f}%"
            )

        # Rental duration constraints
        if duration < min_rental_duration:
            violations.append(
                f"rental duration below minimum "
                f"{min_rental_duration} days"
            )

        if duration > max_rental_duration:
            violations.append(
                f"rental duration exceeds maximum "
                f"{max_rental_duration} days"
            )

        if violations:
            rejected_scenarios.append({
                **scenario,
                "feasible": False,
                "constraint_violations": violations
            })

        else:
            feasible_scenarios.append({
                **scenario,
                "feasible": True,
                "constraint_violations": []
            })

    # ---------------------------------------------------------
    # 2. No feasible scenario
    # ---------------------------------------------------------

    if not feasible_scenarios:
        return {
            "all_scenarios": all_scenarios,
            "feasible_scenarios": [],
            "rejected_scenarios": rejected_scenarios,
            "best_policy": None,
            "constraints": {
                "fee_lower_bound": lower_fee,
                "fee_upper_bound": upper_fee,
                "min_rental_duration": min_rental_duration,
                "max_rental_duration": max_rental_duration,
                "max_late_probability": late_ceiling
            }
        }

    # ---------------------------------------------------------
    # 3. Rank feasible scenarios by total revenue
    # ---------------------------------------------------------

    feasible_scenarios.sort(
        key=lambda x: x.get("net_value", x["expected_total_revenue"]),
        reverse=True
    )

    for index, scenario in enumerate(
        feasible_scenarios,
        start=1
    ):
        scenario["feasible_rank"] = index

    best_policy = feasible_scenarios[0]

    # ---------------------------------------------------------
    # 4. Return
    # ---------------------------------------------------------

    return {
        "all_scenarios": all_scenarios,
        "feasible_scenarios": feasible_scenarios,
        "rejected_scenarios": rejected_scenarios,
        "best_policy": best_policy,
        "constraints": {
            "fee_lower_bound": lower_fee,
            "fee_upper_bound": upper_fee,
            "min_rental_duration": min_rental_duration,
            "max_rental_duration": max_rental_duration,
            "max_late_probability": late_ceiling
        },
        "current_scenario": current_scenario,
        "comparison": result.get("comparison"),
    }
