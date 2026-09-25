from tools.data.get_revenue_data import get_revenue_data


def analyze_revenue_structure():
    """
    Analyze the overall revenue structure.

    Returns:
        dict containing:
        - total_revenue
        - rental_revenue
        - late_fee_revenue
        - late_fee_contribution_pct
        - rental_revenue_contribution_pct
    """

    data = get_revenue_data()

    total_revenue = 0.0
    late_fee_revenue = 0.0

    for row in data:
        amount = float(row["amount"])
        rental_rate = float(row["rental_rate"])

        total_revenue += amount

        extra = amount - rental_rate
        if extra > 0:
            late_fee_revenue += extra

    rental_revenue = total_revenue - late_fee_revenue

    if total_revenue > 0:
        late_fee_contribution_pct = (
            late_fee_revenue / total_revenue * 100
        )
        rental_revenue_contribution_pct = (
            rental_revenue / total_revenue * 100
        )
    else:
        late_fee_contribution_pct = 0
        rental_revenue_contribution_pct = 0

    return {
        "total_revenue": round(total_revenue, 2),
        "rental_revenue": round(rental_revenue, 2),
        "late_fee_revenue": round(late_fee_revenue, 2),
        "late_fee_contribution_pct": round(
            late_fee_contribution_pct, 2
        ),
        "rental_revenue_contribution_pct": round(
            rental_revenue_contribution_pct, 2
        ),
    }


if __name__ == "__main__":
    result = analyze_revenue_structure()

    print("=" * 40)
    print("REVENUE STRUCTURE")
    print("=" * 40)

    for key, value in result.items():
        print(f"{key}: {value}")
