# ============================================================
# TOOL 10 — PRICING RECOMMENDATION
# ============================================================

def pricing_recommendation(
    category,
    current_price,
    current_demand,
    elasticity,
    p_value,
    proposed_price
):
    """
    Provide a pricing recommendation based on:

    - price elasticity
    - statistical significance
    - current price
    - current demand
    - proposed price
    - estimated revenue impact
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

    if proposed_price <= 0:
        return {
            "error": "Proposed price must be greater than 0."
        }

    # ========================================================
    # STATISTICAL SIGNIFICANCE
    # ========================================================

    significant = p_value < 0.05

    # ========================================================
    # ELASTICITY CLASSIFICATION
    # ========================================================

    absolute_elasticity = abs(elasticity)

    if absolute_elasticity > 1:

        elasticity_type = "Elastic"

    elif absolute_elasticity < 1:

        elasticity_type = "Inelastic"

    else:

        elasticity_type = "Unit Elastic"

    # ========================================================
    # PRICE CHANGE
    # ========================================================

    price_change_pct = (
        (proposed_price - current_price)
        / current_price
        * 100
    )

    # ========================================================
    # DEMAND ESTIMATION
    # ========================================================

    estimated_demand = (
        current_demand
        * (proposed_price / current_price)
        ** elasticity
    )

    # ========================================================
    # REVENUE
    # ========================================================

    current_revenue = (
        current_price * current_demand
    )

    estimated_revenue = (
        proposed_price * estimated_demand
    )

    revenue_change_pct = (
        (estimated_revenue - current_revenue)
        / current_revenue
        * 100
        if current_revenue != 0
        else 0
    )

    demand_change_pct = (
        (estimated_demand - current_demand)
        / current_demand
        * 100
        if current_demand != 0
        else 0
    )

    # ========================================================
    # RECOMMENDATION LOGIC
    # ========================================================

    if not significant:

        recommendation = (
            "INSUFFICIENT EVIDENCE"
        )

        reason = (
            "The estimated price elasticity is "
            "not statistically significant. "
            "The model does not provide enough "
            "evidence to confidently recommend "
            "a price change."
        )

    else:

        if revenue_change_pct > 0:

            recommendation = (
                "CONSIDER PRICE INCREASE"
            )

            reason = (
                "The elasticity estimate is "
                "statistically significant and "
                "the proposed price produces "
                "higher estimated revenue."
            )

        elif revenue_change_pct < 0:

            recommendation = (
                "DO NOT INCREASE PRICE"
            )

            reason = (
                "Although the elasticity estimate "
                "is statistically significant, "
                "the proposed price produces "
                "lower estimated revenue."
            )

        else:

            recommendation = (
                "NO CLEAR REVENUE BENEFIT"
            )

            reason = (
                "The proposed price produces "
                "approximately the same estimated "
                "revenue as the current price."
            )

    # ========================================================
    # RETURN RESULT
    # ========================================================

    return {

        "category": category,

        "current_price": round(
            current_price, 2
        ),

        "proposed_price": round(
            proposed_price, 2
        ),

        "price_change_pct": round(
            price_change_pct, 2
        ),

        "elasticity": round(
            elasticity, 4
        ),

        "elasticity_type": elasticity_type,

        "p_value": round(
            p_value, 4
        ),

        "statistically_significant":
            significant,

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
        ),

        "recommendation": recommendation,

        "reason": reason
    }


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    result = pricing_recommendation(

        category="Sci-Fi",

        current_price=2.99,

        current_demand=1000,

        elasticity=-0.0623,

        p_value=0.0325,

        proposed_price=3.49
    )

    print("=" * 70)
    print("TOOL 10 — PRICING RECOMMENDATION")
    print("=" * 70)

    for key, value in result.items():

        print(
            f"{key}: {value}"
        )

    print(
        "\nTool 10 test completed successfully."
    )
