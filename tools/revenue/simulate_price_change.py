def simulate_price_change(
    current_price,
    current_demand,
    new_price,
    elasticity
):
    """
    Simulate the effect of a price change
    on demand and revenue.
    """

    if current_price <= 0:
        return {
            "error": "Current price must be greater than 0."
        }

    if current_demand < 0:
        return {
            "error": "Current demand cannot be negative."
        }

    if new_price <= 0:
        return {
            "error": "New price must be greater than 0."
        }

    # Price change
    price_change_pct = (
        (new_price - current_price)
        / current_price
        * 100
    )

    # Constant elasticity demand model
    estimated_demand = (
        current_demand
        * (new_price / current_price)
        ** elasticity
    )

    # Revenue
    current_revenue = (
        current_price * current_demand
    )

    estimated_revenue = (
        new_price * estimated_demand
    )

    # Demand change
    demand_change_pct = (
        (estimated_demand - current_demand)
        / current_demand
        * 100
        if current_demand != 0
        else 0
    )

    # Revenue change
    revenue_change_pct = (
        (estimated_revenue - current_revenue)
        / current_revenue
        * 100
        if current_revenue != 0
        else 0
    )

    return {
        "current_price": round(
            current_price, 4
        ),

        "new_price": round(
            new_price, 4
        ),

        "price_change_pct": round(
            price_change_pct, 2
        ),

        "elasticity": round(
            elasticity, 4
        ),

        "current_demand": round(
            current_demand, 2
        ),

        "estimated_demand": round(
            estimated_demand, 2
        ),

        "demand_change_pct": round(
            demand_change_pct, 2
        ),

        "current_revenue": round(
            current_revenue, 2
        ),

        "estimated_revenue": round(
            estimated_revenue, 2
        ),

        "revenue_change_pct": round(
            revenue_change_pct, 2
        )
    }


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    result = simulate_price_change(
        current_price=2.99,
        current_demand=1000,
        new_price=3.49,
        elasticity=-0.0623
    )

    print("=" * 70)
    print("TOOL 7 — SIMULATE PRICE CHANGE")
    print("=" * 70)

    for key, value in result.items():
        print(f"{key}: {value}")

    print("\nTool 7 test completed successfully.")
