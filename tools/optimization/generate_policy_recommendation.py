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
    max_rental_duration=7,
    max_late_probability=None,
    allow_higher_late_rate=False,
    late_fee_elasticity=None,
    late_days_elasticity=None,
    demand_fee_elasticity=None,
    demand_duration_elasticity=None,
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
        max_rental_duration=max_rental_duration,
        max_late_probability=max_late_probability,
        allow_higher_late_rate=allow_higher_late_rate,
        late_fee_elasticity=late_fee_elasticity,
        late_days_elasticity=late_days_elasticity,
        demand_fee_elasticity=demand_fee_elasticity,
        demand_duration_elasticity=demand_duration_elasticity,
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
            "Keeping the current policy gives the highest net policy "
            "value among feasible scenarios (no alternative raises value "
            "without increasing late returns)."
        )
    else:
        reason = (
            f"{recommendation} gives the highest net policy value among "
            f"feasible scenarios: net value "
            f"{best_policy.get('net_value_change_pct', 0):+.2f}%, total "
            f"revenue {best_policy.get('revenue_change_pct', 0):+.2f}%, "
            f"late returns {best_policy.get('late_returns_change_pct', 0):+.2f}% "
            f"vs the current policy."
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
        "ranking_metric": "net_value",
        "current_scenario": result.get("current_scenario"),
        "all_scenarios": result.get("all_scenarios"),
        "formula": (result.get("comparison") or {}).get("formula"),
        "behavior_assumptions": (result.get("comparison") or {}).get(
            "behavior_assumptions"
        ),
        "cost_basis": (result.get("comparison") or {}).get("cost_basis"),
        "scale_note": (
            "Net policy value = rental revenue + late-fee revenue - "
            "opportunity cost of copies kept late. Simulated business-level "
            "values under the stated behaviour assumptions, not observed "
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
