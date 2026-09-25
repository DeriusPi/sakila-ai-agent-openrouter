from tools.optimization.apply_policy_constraints import (
    apply_policy_constraints
)


def generate_policy_recommendation(
    customer_late_rate,
    category,
    current_rental_duration,
    rental_rate,
    fee_options=None,
    rental_duration_options=None,
    current_fee_per_day=1.00,
    min_rental_duration=3,
    max_rental_duration=7
):
    """
    Generate the final business policy recommendation.

    Pipeline:
        compare_scenarios
            ↓
        find_best_policy
            ↓
        apply_policy_constraints
            ↓
        generate recommendation
    """

    result = apply_policy_constraints(
        customer_late_rate=customer_late_rate,
        category=category,
        current_rental_duration=current_rental_duration,
        rental_rate=rental_rate,
        fee_options=fee_options,
        rental_duration_options=rental_duration_options,
        current_fee_per_day=current_fee_per_day,
        min_rental_duration=min_rental_duration,
        max_rental_duration=max_rental_duration
    )

    best_policy = result["best_policy"]

    if best_policy is None:
        return {
            "recommendation": None,
            "reason": (
                "No feasible policy was found "
                "under the specified business constraints."
            ),
            "best_policy": None,
            "feasible_scenarios": result["feasible_scenarios"],
            "rejected_scenarios": result["rejected_scenarios"],
            "constraints": result["constraints"]
        }

    recommendation = best_policy["policy"]

    if best_policy.get("policy_type") == "current":
        reason = (
            "Keeping the current policy gives the highest expected total "
            "revenue among feasible scenarios under the current "
            "simulation assumptions."
        )
    else:
        reason = (
            f"{recommendation} provides the highest expected total "
            f"revenue among feasible policy scenarios "
            f"(simulated change vs current policy: "
            f"{best_policy.get('revenue_change_pct', 0):+.2f}%)."
        )

    return {
        "recommendation": recommendation,
        "reason": reason,
        "best_policy": best_policy,
        "feasible_scenarios": result["feasible_scenarios"],
        "rejected_scenarios": result["rejected_scenarios"],
        "constraints": result["constraints"],
        "customer_late_rate": customer_late_rate,
        "category": category,
        "current_rental_duration": current_rental_duration,
        "rental_rate": rental_rate,
        "scale_note": (
            "Expected revenues are simulated business-level values "
            "under the current simulation assumptions, not observed "
            "revenue."
        )
    }


if __name__ == "__main__":
    result = generate_policy_recommendation(
        customer_late_rate=0.5,
        category="Family",
        current_rental_duration=5,
        rental_rate=2.99
    )

    print("Recommendation:", result["recommendation"])
    print("Reason:", result["reason"])
    print("Best policy:", result["best_policy"])
