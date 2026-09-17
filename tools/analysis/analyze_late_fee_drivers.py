from tools.data.get_late_fee_data import get_late_fee_data


def analyze_late_fee_drivers():
    """
    Analyze factors associated with late returns.

    This tool is descriptive analysis only.
    It does NOT make predictions or recommendations.

    It compares late vs on-time rentals across:
    - rental duration
    - rental rate
    - category
    - late frequency
    """

    data = get_late_fee_data()

    if not data:
        return {
            "total_rentals": 0,
            "late_rentals": 0,
            "on_time_rentals": 0,
            "overall_late_rate_pct": 0.0,
            "duration_analysis": {},
            "rate_analysis": {},
            "category_analysis": [],
            "customer_analysis": []
        }

    # --------------------------------------------------
    # Overall
    # --------------------------------------------------

    total_rentals = len(data)

    late_records = [
        row for row in data
        if row["is_late"]
    ]

    on_time_records = [
        row for row in data
        if not row["is_late"]
    ]

    late_rentals = len(late_records)
    on_time_rentals = len(on_time_records)

    overall_late_rate_pct = (
        late_rentals / total_rentals * 100
        if total_rentals > 0
        else 0.0
    )

    # --------------------------------------------------
    # Rental duration analysis
    # --------------------------------------------------

    duration_groups = {}

    for row in data:

        duration = row["rental_duration"]

        if duration not in duration_groups:
            duration_groups[duration] = {
                "rental_duration": duration,
                "total_rentals": 0,
                "late_rentals": 0
            }

        duration_groups[duration]["total_rentals"] += 1

        if row["is_late"]:
            duration_groups[duration]["late_rentals"] += 1

    duration_analysis = {}

    for duration, values in duration_groups.items():

        total = values["total_rentals"]
        late = values["late_rentals"]

        late_rate = (
            late / total * 100
            if total > 0
            else 0.0
        )

        duration_analysis[duration] = {
            "total_rentals": total,
            "late_rentals": late,
            "late_rate_pct": round(late_rate, 2)
        }

    # --------------------------------------------------
    # Rental rate analysis
    # --------------------------------------------------

    rate_groups = {}

    for row in data:

        rate = row["rental_rate"]

        if rate not in rate_groups:
            rate_groups[rate] = {
                "rental_rate": rate,
                "total_rentals": 0,
                "late_rentals": 0
            }

        rate_groups[rate]["total_rentals"] += 1

        if row["is_late"]:
            rate_groups[rate]["late_rentals"] += 1

    rate_analysis = {}

    for rate, values in rate_groups.items():

        total = values["total_rentals"]
        late = values["late_rentals"]

        late_rate = (
            late / total * 100
            if total > 0
            else 0.0
        )

        rate_analysis[rate] = {
            "total_rentals": total,
            "late_rentals": late,
            "late_rate_pct": round(late_rate, 2)
        }

    # --------------------------------------------------
    # Category analysis
    # --------------------------------------------------

    category_groups = {}

    for row in data:

        category = row["category"]

        if category not in category_groups:
            category_groups[category] = {
                "category": category,
                "total_rentals": 0,
                "late_rentals": 0,
                "total_late_days": 0.0,
                "late_fee_revenue": 0.0
            }

        category_groups[category]["total_rentals"] += 1

        if row["is_late"]:

            category_groups[category]["late_rentals"] += 1

            category_groups[category]["total_late_days"] += (
                row["late_days"]
            )

            extra_payment = (
                row["payment_amount"]
                - row["rental_rate"]
            )

            if extra_payment > 0:
                category_groups[category]["late_fee_revenue"] += (
                    extra_payment
                )

    category_analysis = []

    for category, values in category_groups.items():

        total = values["total_rentals"]
        late = values["late_rentals"]

        late_rate = (
            late / total * 100
            if total > 0
            else 0.0
        )

        avg_late_days = (
            values["total_late_days"] / late
            if late > 0
            else 0.0
        )

        avg_late_fee = (
            values["late_fee_revenue"] / late
            if late > 0
            else 0.0
        )

        category_analysis.append({
            "category": category,
            "total_rentals": total,
            "late_rentals": late,
            "late_rate_pct": round(late_rate, 2),
            "avg_late_days": round(avg_late_days, 2),
            "avg_late_fee": round(avg_late_fee, 2),
            "late_fee_revenue": round(
                values["late_fee_revenue"],
                2
            )
        })

    # Highest late rate first
    category_analysis.sort(
        key=lambda x: x["late_rate_pct"],
        reverse=True
    )

    # --------------------------------------------------
    # Customer behavior analysis
    # --------------------------------------------------

    customer_groups = {}

    for row in data:

        customer_id = row["customer_id"]

        if customer_id not in customer_groups:
            customer_groups[customer_id] = {
                "customer_id": customer_id,
                "total_rentals": 0,
                "late_rentals": 0
            }

        customer_groups[customer_id]["total_rentals"] += 1

        if row["is_late"]:
            customer_groups[customer_id]["late_rentals"] += 1

    customer_analysis = []

    for customer_id, values in customer_groups.items():

        total = values["total_rentals"]
        late = values["late_rentals"]

        late_rate = (
            late / total * 100
            if total > 0
            else 0.0
        )

        customer_analysis.append({
            "customer_id": customer_id,
            "total_rentals": total,
            "late_rentals": late,
            "late_rate_pct": round(late_rate, 2)
        })

    # Customers with highest late frequency first
    customer_analysis.sort(
        key=lambda x: (
            x["late_rate_pct"],
            x["total_rentals"]
        ),
        reverse=True
    )

    return {
        "total_rentals": total_rentals,
        "late_rentals": late_rentals,
        "on_time_rentals": on_time_rentals,
        "overall_late_rate_pct": round(
            overall_late_rate_pct,
            2
        ),
        "duration_analysis": duration_analysis,
        "rate_analysis": rate_analysis,
        "category_analysis": category_analysis,
        "customer_analysis": customer_analysis
    }
