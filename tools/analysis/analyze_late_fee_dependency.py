from tools.data.get_rental_data import get_rental_data
from tools.data.get_revenue_data import get_revenue_data


def analyze_late_fee_dependency():
    """
    Measure the business dependency on late-fee revenue.
    """

    rentals = get_rental_data()
    revenue_data = get_revenue_data()

    total_rentals = len(rentals)
    late_rentals = 0

    for row in rentals:

        actual_days = (
            row["return_date"] -
            row["rental_date"]
        ).total_seconds() / 86400

        rental_duration = float(
            row["rental_duration"]
        )

        if actual_days > rental_duration:
            late_rentals += 1

    late_rate_pct = (
        late_rentals / total_rentals * 100
        if total_rentals > 0
        else 0
    )

    rental_revenue = 0.0
    late_fee_revenue = 0.0

    for row in revenue_data:

        amount = float(row["amount"])
        rental_rate = float(row["rental_rate"])

        rental_revenue += rental_rate

        extra = amount - rental_rate

        if extra > 0:
            late_fee_revenue += extra

    total_revenue = (
        rental_revenue +
        late_fee_revenue
    )

    late_fee_dependency_pct = (
        late_fee_revenue /
        total_revenue *
        100
        if total_revenue > 0
        else 0
    )

    return {
        "total_rentals": total_rentals,
        "late_rentals": late_rentals,
        "late_rate_pct": round(
            late_rate_pct, 2
        ),
        "rental_revenue": round(
            rental_revenue, 2
        ),
        "late_fee_revenue": round(
            late_fee_revenue, 2
        ),
        "total_revenue": round(
            total_revenue, 2
        ),
        "late_fee_dependency_pct": round(
            late_fee_dependency_pct, 2
        ),
    }


if __name__ == "__main__":
    result = analyze_late_fee_dependency()

    print("=" * 40)
    print("LATE FEE DEPENDENCY")
    print("=" * 40)

    for key, value in result.items():
        print(f"{key}: {value}")
