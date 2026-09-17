from tools.data.get_late_fee_data import get_late_fee_data


def analyze_late_fee_revenue():
    """
    Analyze revenue associated with late rentals.

    Observed late-fee revenue is defined as:

        payment_amount - rental_rate

    for rentals classified as late.

    This is an observed extra-payment measure based on the
    Sakila dataset, not a dedicated late_fee field.
    """

    data = get_late_fee_data()

    if not data:
        return {
            "total_rentals": 0,
            "late_rentals": 0,
            "late_rate_pct": 0.0,
            "total_rental_revenue": 0.0,
            "observed_late_fee_revenue": 0.0,
            "late_fee_contribution_pct": 0.0,
            "categories": []
        }

    total_rentals = len(data)

    late_rentals = [
        row for row in data
        if row["is_late"]
    ]

    late_rental_count = len(late_rentals)

    late_rate_pct = (
        late_rental_count / total_rentals * 100
        if total_rentals > 0
        else 0.0
    )

    total_rental_revenue = sum(
        row["rental_rate"]
        for row in data
    )

    observed_late_fee_revenue = 0.0

    for row in late_rentals:
        extra_payment = (
            row["payment_amount"]
            - row["rental_rate"]
        )

        # Only count positive extra payment
        # as observed late-fee / extra revenue.
        if extra_payment > 0:
            observed_late_fee_revenue += extra_payment

    total_revenue = (
        total_rental_revenue
        + observed_late_fee_revenue
    )

    late_fee_contribution_pct = (
        observed_late_fee_revenue
        / total_revenue
        * 100
        if total_revenue > 0
        else 0.0
    )

    # --------------------------------------------------
    # Category-level analysis
    # --------------------------------------------------

    category_data = {}

    for row in data:

        category = row["category"]

        if category not in category_data:
            category_data[category] = {
                "category": category,
                "total_rentals": 0,
                "late_rentals": 0,
                "rental_revenue": 0.0,
                "observed_late_fee_revenue": 0.0
            }

        category_data[category]["total_rentals"] += 1

        category_data[category]["rental_revenue"] += (
            row["rental_rate"]
        )

        if row["is_late"]:

            category_data[category]["late_rentals"] += 1

            extra_payment = (
                row["payment_amount"]
                - row["rental_rate"]
            )

            if extra_payment > 0:
                category_data[category][
                    "observed_late_fee_revenue"
                ] += extra_payment

    categories = []

    for category, values in category_data.items():

        total = values["total_rentals"]
        late = values["late_rentals"]

        late_rate = (
            late / total * 100
            if total > 0
            else 0.0
        )

        category_late_fee = values[
            "observed_late_fee_revenue"
        ]

        category_total_revenue = (
            values["rental_revenue"]
            + category_late_fee
        )

        contribution = (
            category_late_fee
            / observed_late_fee_revenue
            * 100
            if observed_late_fee_revenue > 0
            else 0.0
        )

        categories.append({
            "category": category,
            "total_rentals": total,
            "late_rentals": late,
            "late_rate_pct": round(late_rate, 2),
            "rental_revenue": round(
                values["rental_revenue"], 2
            ),
            "observed_late_fee_revenue": round(
                category_late_fee, 2
            ),
            "total_revenue": round(
                category_total_revenue, 2
            ),
            "late_fee_contribution_pct": round(
                contribution, 2
            )
        })

    # Highest late-fee revenue first
    categories.sort(
        key=lambda x: x["observed_late_fee_revenue"],
        reverse=True
    )

    return {
        "total_rentals": total_rentals,
        "late_rentals": late_rental_count,
        "late_rate_pct": round(late_rate_pct, 2),
        "total_rental_revenue": round(
            total_rental_revenue, 2
        ),
        "observed_late_fee_revenue": round(
            observed_late_fee_revenue, 2
        ),
        "total_revenue": round(
            total_revenue, 2
        ),
        "late_fee_contribution_pct": round(
            late_fee_contribution_pct, 2
        ),
        "categories": categories
    }
