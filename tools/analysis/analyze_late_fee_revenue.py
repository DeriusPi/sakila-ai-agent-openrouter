from tools.data.business_metrics import get_business_kpis, pct
from tools.data.get_category_data import get_category_data


def analyze_late_fee_revenue():
    """
    Late-return rate and late-fee revenue, overall and by category.

    FIX (this tool is referenced by the agent prompt for
    "What percentage of rentals are late?" but was not registered and
    used definitions that did not match the dashboard):

      - total revenue is SUM(payment.amount) ($67,406.56), not
        SUM(film.rental_rate) ($46,696.39)
      - late-fee revenue is SUM(GREATEST(amount - rental_rate, 0))
        over all payments ($20,262.76), the same definition as
        analyze_revenue_structure
      - category "late_fee_contribution_pct" is now late fee / category
        revenue; the previous value was the category's share of all
        late fees and was mislabelled. That share is now returned as
        "share_of_all_late_fees_pct".
    """

    overall = get_business_kpis()
    categories = get_category_data()

    total_late_fee = overall["late_fee_revenue"]

    rows = []

    for row in categories:
        rows.append({
            "category": row["category"],
            "total_rentals": row["total_rentals"],
            "late_rentals": row["late_rentals"],
            "late_rate_pct": row["late_rate_pct"],
            "total_revenue": row["total_revenue"],
            "rental_revenue": row["rental_revenue"],
            "late_fee_revenue": row["late_fee_revenue"],
            "late_fee_contribution_pct": row["late_fee_contribution_pct"],
            "share_of_all_late_fees_pct": pct(
                row["late_fee_revenue"], total_late_fee
            ),
        })

    rows.sort(key=lambda x: x["late_fee_revenue"], reverse=True)

    return {
        "total_rentals": overall["completed_rentals"],
        "late_rentals": overall["late_rentals"],
        "on_time_rentals": overall["on_time_rentals"],
        "late_rate_pct": overall["late_rate_pct"],
        "total_revenue": overall["total_revenue"],
        "total_rental_revenue": overall["rental_revenue"],
        "observed_late_fee_revenue": overall["late_fee_revenue"],
        "late_fee_contribution_pct": overall["late_fee_contribution_pct"],
        "avg_late_days_when_late": overall["avg_late_days_when_late"],
        "categories": rows,
        "definitions": overall["definitions"],
    }


if __name__ == "__main__":
    import json

    print(json.dumps(analyze_late_fee_revenue(), indent=2)[:3000])
