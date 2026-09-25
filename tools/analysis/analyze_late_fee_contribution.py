from tools.data.get_revenue_data import get_revenue_data


def analyze_late_fee_contribution():
    """
    Analyze late-fee revenue contribution overall and by category.
    """

    data = get_revenue_data()

    total_revenue = 0.0
    total_late_fee_revenue = 0.0
    categories = {}

    for row in data:
        category = row["category"]
        amount = float(row["amount"])
        rental_rate = float(row["rental_rate"])

        late_fee = max(amount - rental_rate, 0)
        rental_revenue = amount - late_fee

        total_revenue += amount
        total_late_fee_revenue += late_fee

        if category not in categories:
            categories[category] = {
                "rental_revenue": 0.0,
                "late_fee_revenue": 0.0,
                "total_revenue": 0.0,
            }

        categories[category]["rental_revenue"] += rental_revenue
        categories[category]["late_fee_revenue"] += late_fee
        categories[category]["total_revenue"] += amount

    total_rental_revenue = (
        total_revenue - total_late_fee_revenue
    )

    category_results = []

    for category, values in categories.items():
        category_total = values["total_revenue"]

        if category_total > 0:
            contribution_pct = (
                values["late_fee_revenue"]
                / category_total
                * 100
            )
        else:
            contribution_pct = 0

        category_results.append({
            "category": category,
            "rental_revenue": round(
                values["rental_revenue"], 2
            ),
            "late_fee_revenue": round(
                values["late_fee_revenue"], 2
            ),
            "total_revenue": round(
                category_total, 2
            ),
            "late_fee_contribution_pct": round(
                contribution_pct, 2
            ),
        })

    category_results.sort(
        key=lambda x: x["late_fee_revenue"],
        reverse=True
    )

    overall_contribution_pct = (
        total_late_fee_revenue / total_revenue * 100
        if total_revenue > 0
        else 0
    )

    return {
        "total_rental_revenue": round(
            total_rental_revenue, 2
        ),
        "total_late_fee_revenue": round(
            total_late_fee_revenue, 2
        ),
        "total_revenue": round(
            total_revenue, 2
        ),
        "late_fee_contribution_pct": round(
            overall_contribution_pct, 2
        ),
        "categories": category_results,
    }


if __name__ == "__main__":
    result = analyze_late_fee_contribution()

    print("=" * 40)
    print("LATE FEE CONTRIBUTION")
    print("=" * 40)

    print(
        f"Total rental revenue: "
        f"${result['total_rental_revenue']}"
    )

    print(
        f"Total late-fee revenue: "
        f"${result['total_late_fee_revenue']}"
    )

    print(
        f"Late-fee contribution: "
        f"{result['late_fee_contribution_pct']}%"
    )

    print("\nTop categories:")

    for category in result["categories"][:5]:
        print(category)
