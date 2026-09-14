# ============================================================
# TOOL 9 — RANK REVENUE OPPORTUNITIES
# ============================================================

def rank_revenue_opportunities(
    category_data,
    price_increase_pct=10,
    significant_only=True
):
    """
    Rank categories according to estimated revenue
    opportunity after a price increase.

    Each category_data item should contain:

        category
        current_price
        current_demand
        elasticity
        p_value

    The tool estimates demand and revenue after
    increasing the price by price_increase_pct.
    """

    if not category_data:
        return {
            "error": "Category data cannot be empty."
        }

    if price_increase_pct <= -100:
        return {
            "error": "Price increase percentage must be greater than -100%."
        }

    opportunities = []

    for item in category_data:

        # ----------------------------------------------------
        # Required fields
        # ----------------------------------------------------

        required_fields = [
            "category",
            "current_price",
            "current_demand",
            "elasticity",
            "p_value"
        ]

        missing_fields = [
            field
            for field in required_fields
            if field not in item
        ]

        if missing_fields:
            return {
                "error": (
                    f"Missing fields for category "
                    f"{item.get('category', 'Unknown')}: "
                    f"{missing_fields}"
                )
            }

        category = item["category"]
        current_price = float(item["current_price"])
        current_demand = float(item["current_demand"])
        elasticity = float(item["elasticity"])
        p_value = float(item["p_value"])

        # ----------------------------------------------------
        # Statistical significance filter
        # ----------------------------------------------------

        statistically_significant = (
            p_value < 0.05
        )

        if significant_only and not statistically_significant:
            continue

        # ----------------------------------------------------
        # Validation
        # ----------------------------------------------------

        if current_price <= 0:
            continue

        if current_demand < 0:
            continue

        # ----------------------------------------------------
        # New price
        # ----------------------------------------------------

        new_price = (
            current_price
            * (1 + price_increase_pct / 100)
        )

        # ----------------------------------------------------
        # Estimate new demand
        #
        # Q1 = Q0 × (P1 / P0)^E
        # ----------------------------------------------------

        estimated_demand = (
            current_demand
            * (new_price / current_price)
            ** elasticity
        )

        # ----------------------------------------------------
        # Revenue
        # ----------------------------------------------------

        current_revenue = (
            current_price
            * current_demand
        )

        estimated_revenue = (
            new_price
            * estimated_demand
        )

        revenue_change_pct = (
            (estimated_revenue - current_revenue)
            / current_revenue
            * 100
            if current_revenue != 0
            else 0
        )

        # ----------------------------------------------------
        # Store result
        # ----------------------------------------------------

        opportunities.append({

            "category": category,

            "elasticity": round(
                elasticity, 4
            ),

            "p_value": round(
                p_value, 4
            ),

            "statistically_significant":
                statistically_significant,

            "current_price": round(
                current_price, 2
            ),

            "new_price": round(
                new_price, 2
            ),

            "current_demand": round(
                current_demand, 2
            ),

            "estimated_demand": round(
                estimated_demand, 2
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
        })

    # --------------------------------------------------------
    # No qualifying categories
    # --------------------------------------------------------

    if not opportunities:
        return {
            "message": (
                "No categories met the selected criteria."
            ),
            "price_increase_pct": price_increase_pct,
            "significant_only": significant_only,
            "opportunities": []
        }

    # --------------------------------------------------------
    # Rank by revenue change
    # --------------------------------------------------------

    opportunities.sort(
        key=lambda x: x["revenue_change_pct"],
        reverse=True
    )

    # Add ranking

    for rank, opportunity in enumerate(
        opportunities,
        start=1
    ):
        opportunity["rank"] = rank

    return {

        "price_increase_pct": price_increase_pct,

        "significant_only": significant_only,

        "number_of_categories": len(
            opportunities
        ),

        "ranked_opportunities": opportunities,

        "best_opportunity": opportunities[0]
    }


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    test_data = [

        {
            "category": "Sci-Fi",
            "current_price": 2.99,
            "current_demand": 1000,
            "elasticity": -0.0623,
            "p_value": 0.0325
        },

        {
            "category": "Drama",
            "current_price": 2.99,
            "current_demand": 1200,
            "elasticity": -0.10,
            "p_value": 0.20
        },

        {
            "category": "Action",
            "current_price": 2.99,
            "current_demand": 1500,
            "elasticity": -0.20,
            "p_value": 0.30
        }
    ]

    result = rank_revenue_opportunities(
        category_data=test_data,
        price_increase_pct=10,
        significant_only=True
    )

    print("=" * 70)
    print("TOOL 9 — RANK REVENUE OPPORTUNITIES")
    print("=" * 70)

    print(
        f"\nPrice increase: "
        f"{result['price_increase_pct']}%"
    )

    print(
        f"Categories included: "
        f"{result['number_of_categories']}"
    )

    print("\nRanked opportunities:")
    print("-" * 70)

    for item in result["ranked_opportunities"]:

        print(
            f"#{item['rank']} "
            f"{item['category']} | "
            f"Revenue change: "
            f"{item['revenue_change_pct']}% | "
            f"New revenue: "
            f"${item['estimated_revenue']}"
        )

    print("\nBest opportunity:")

    print(
        result["best_opportunity"]
    )

    print(
        "\nTool 9 test completed successfully."
    )
