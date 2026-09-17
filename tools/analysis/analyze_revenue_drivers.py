from tools.data.get_revenue_data import get_revenue_data
from tools.data.get_rental_data import get_rental_data


def analyze_revenue_drivers():
    """
    Analyze factors associated with late-fee revenue.

    Dimensions:
        - category
        - rental duration
        - rental rate
    """

    revenue_data = get_revenue_data()
    rental_data = get_rental_data()

    category_stats = {}
    duration_stats = {}
    rate_stats = {}

    # -------------------------
    # Revenue drivers
    # -------------------------

    for row in revenue_data:

        category = row["category"]
        duration = int(row["rental_duration"])
        rate = float(row["rental_rate"])

        amount = float(row["amount"])
        rental_rate = float(row["rental_rate"])

        late_fee = max(
            amount - rental_rate,
            0
        )

        # Category
        if category not in category_stats:
            category_stats[category] = {
                "transactions": 0,
                "late_fee_revenue": 0.0,
            }

        category_stats[category]["transactions"] += 1
        category_stats[category][
            "late_fee_revenue"
        ] += late_fee

        # Duration
        if duration not in duration_stats:
            duration_stats[duration] = {
                "transactions": 0,
                "late_fee_revenue": 0.0,
            }

        duration_stats[duration]["transactions"] += 1
        duration_stats[duration][
            "late_fee_revenue"
        ] += late_fee

        # Rental rate
        if rate not in rate_stats:
            rate_stats[rate] = {
                "transactions": 0,
                "late_fee_revenue": 0.0,
            }

        rate_stats[rate]["transactions"] += 1
        rate_stats[rate][
            "late_fee_revenue"
        ] += late_fee

    # -------------------------
    # Late-return behavior
    # -------------------------

    late_days_distribution = {}

    for row in rental_data:

        actual_days = (
            row["return_date"] -
            row["rental_date"]
        ).total_seconds() / 86400

        duration = float(
            row["rental_duration"]
        )

        late_days = max(
            actual_days - duration,
            0
        )

        late_day_bucket = int(late_days)

        if late_day_bucket not in late_days_distribution:
            late_days_distribution[
                late_day_bucket
            ] = 0

        late_days_distribution[
            late_day_bucket
        ] += 1

    def sort_stats(stats):

        result = []

        for key, values in stats.items():

            result.append({
                "dimension": key,
                "transactions": values["transactions"],
                "late_fee_revenue": round(
                    values["late_fee_revenue"],
                    2
                ),
                "avg_late_fee": round(
                    values["late_fee_revenue"]
                    / values["transactions"],
                    2
                )
            })

        result.sort(
            key=lambda x: x["late_fee_revenue"],
            reverse=True
        )

        return result

    return {
        "category": sort_stats(category_stats),
        "rental_duration": sort_stats(
            duration_stats
        ),
        "rental_rate": sort_stats(rate_stats),
        "late_days_distribution": dict(
            sorted(late_days_distribution.items())
        ),
    }


if __name__ == "__main__":

    result = analyze_revenue_drivers()

    print("=" * 40)
    print("REVENUE DRIVERS")
    print("=" * 40)

    print("\nCategory:")
    for x in result["category"][:5]:
        print(x)

    print("\nRental duration:")
    for x in result["rental_duration"]:
        print(x)

    print("\nRental rate:")
    for x in result["rental_rate"]:
        print(x)

    print("\nLate days distribution:")
    print(result["late_days_distribution"])
