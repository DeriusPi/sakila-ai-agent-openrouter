# ============================================================
# TOOL 8 — SIMULATE PRICE SCENARIO
# ============================================================

def simulate_price_scenario(
    current_price,
    current_demand,
    elasticity,
    price_scenarios
):
    """
    Simulate demand and revenue under multiple
    possible rental prices.

    Parameters
    ----------
    current_price : float
        Current rental price.

    current_demand : float
        Current rental demand.

    elasticity : float
        Price elasticity of demand.

    price_scenarios : list
        List of possible new prices.

    Returns
    -------
    dict
        Current situation, all price scenarios,
        and the scenario with the highest estimated revenue.
    """

    # ========================================================
    # VALIDATION
    # ========================================================

    if current_price <= 0:
        return {
            "error": "Current price must be greater than 0."
        }

    if current_demand < 0:
        return {
            "error": "Current demand cannot be negative."
        }

    if not price_scenarios:
        return {
            "error": "Price scenarios cannot be empty."
        }

    # ========================================================
    # CURRENT REVENUE
    # ========================================================

    current_revenue = (
        current_price * current_demand
    )

    scenarios = []

    # ========================================================
    # SIMULATE EACH PRICE
    # ========================================================

    for new_price in price_scenarios:

        if new_price <= 0:
            continue

        # Constant elasticity demand model:
        #
        # Q1 = Q0 × (P1 / P0)^E

        estimated_demand = (
            current_demand
            * (new_price / current_price)
            ** elasticity
        )

        # Estimated revenue

        estimated_revenue = (
            new_price * estimated_demand
        )

        # Demand percentage change

        if current_demand != 0:

            demand_change_pct = (
                (estimated_demand - current_demand)
                / current_demand
                * 100
            )

        else:

            demand_change_pct = 0

        # Revenue percentage change

        if current_revenue != 0:

            revenue_change_pct = (
                (estimated_revenue - current_revenue)
                / current_revenue
                * 100
            )

        else:

            revenue_change_pct = 0

        # Price percentage change

        price_change_pct = (
            (new_price - current_price)
            / current_price
            * 100
        )

        scenarios.append({

            "price": round(
                new_price, 2
            ),

            "price_change_pct": round(
                price_change_pct, 2
            ),

            "estimated_demand": round(
                estimated_demand, 2
            ),

            "demand_change_pct": round(
                demand_change_pct, 2
            ),

            "estimated_revenue": round(
                estimated_revenue, 2
            ),

            "revenue_change_pct": round(
                revenue_change_pct, 2
            )
        })

    # ========================================================
    # CHECK VALID SCENARIOS
    # ========================================================

    if not scenarios:
        return {
            "error": "No valid price scenarios were provided."
        }

    # ========================================================
    # FIND BEST REVENUE SCENARIO
    # ========================================================

    best_scenario = max(
        scenarios,
        key=lambda x: x["estimated_revenue"]
    )

    # ========================================================
    # RETURN RESULT
    # ========================================================

    return {

        "current_price": round(
            current_price, 2
        ),

        "current_demand": round(
            current_demand, 2
        ),

        "current_revenue": round(
            current_revenue, 2
        ),

        "elasticity": round(
            elasticity, 4
        ),

        "number_of_scenarios": len(
            scenarios
        ),

        "scenarios": scenarios,

        "best_revenue_scenario": best_scenario
    }


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    result = simulate_price_scenario(

        current_price=2.99,

        current_demand=1000,

        elasticity=-0.0623,

        price_scenarios=[
            2.49,
            2.99,
            3.49,
            3.99,
            4.49
        ]
    )

    print("=" * 70)
    print("TOOL 8 — SIMULATE PRICE SCENARIO")
    print("=" * 70)

    print(
        f"\nCurrent price: "
        f"${result['current_price']}"
    )

    print(
        f"Current demand: "
        f"{result['current_demand']}"
    )

    print(
        f"Current revenue: "
        f"${result['current_revenue']}"
    )

    print(
        f"Elasticity: "
        f"{result['elasticity']}"
    )

    print("\nPrice scenarios:")
    print("-" * 70)

    for scenario in result["scenarios"]:

        print(
            f"Price: ${scenario['price']:.2f} | "
            f"Demand: {scenario['estimated_demand']:.2f} | "
            f"Revenue: ${scenario['estimated_revenue']:.2f} | "
            f"Revenue change: "
            f"{scenario['revenue_change_pct']:.2f}%"
        )

    print("\nBest revenue scenario:")
    print(
        result["best_revenue_scenario"]
    )

    print("\nTool 8 test completed successfully.")
