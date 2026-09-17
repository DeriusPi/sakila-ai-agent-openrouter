from statistics import median

from tools.data.get_late_fee_data import get_late_fee_data


def derive_fee_constraint():

    data = get_late_fee_data()

    if not data:
        raise ValueError("No late-fee data available.")

    fee_per_day_values = []

    for row in data:

        late_days = row.get("late_days")
        rental_rate = row.get("rental_rate")
        payment_amount = row.get("payment_amount")

        if (
            late_days is None
            or rental_rate is None
            or payment_amount is None
        ):
            continue

        try:
            late_days = float(late_days)
            rental_rate = float(rental_rate)
            payment_amount = float(payment_amount)
        except (TypeError, ValueError):
            continue

        if late_days <= 0:
            continue

        late_fee = payment_amount - rental_rate

        if late_fee <= 0:
            continue

        fee_per_day = late_fee / late_days

        if fee_per_day > 0:
            fee_per_day_values.append(fee_per_day)

    if not fee_per_day_values:
        raise ValueError(
            "Could not derive late fee per day from data."
        )

    fee_per_day_values.sort()

    n = len(fee_per_day_values)

    current_fee = median(fee_per_day_values)

    q25 = fee_per_day_values[
        int(0.25 * (n - 1))
    ]

    q75 = fee_per_day_values[
        int(0.75 * (n - 1))
    ]

    total_rentals = len(data)

    late_rentals = sum(
        1
        for row in data
        if row.get("is_late")
    )

    late_rate = (
        late_rentals / total_rentals
        if total_rentals > 0
        else 0
    )

    upper_bound = current_fee * (
        1 + late_rate
    )

    upper_bound = max(
        upper_bound,
        current_fee
    )

    benchmark = current_fee * (
        1 + late_rate / 2
    )

    return {
        "current_fee_per_day": round(
            current_fee,
            2
        ),

        "lower_bound": round(
            q25,
            2
        ),

        "upper_bound": round(
            upper_bound,
            2
        ),

        "benchmark": round(
            benchmark,
            2
        ),

        "observed_fee_per_day": {
            "min": round(
                min(fee_per_day_values),
                2
            ),
            "q25": round(
                q25,
                2
            ),
            "median": round(
                current_fee,
                2
            ),
            "q75": round(
                q75,
                2
            ),
            "max": round(
                max(fee_per_day_values),
                2
            )
        },

        "behavior": {
            "late_rate": round(
                late_rate,
                4
            ),
            "total_rentals": total_rentals,
            "late_rentals": late_rentals
        },

        "data_source": {
            "rental_observations": total_rentals,
            "late_fee_observations": len(
                fee_per_day_values
            )
        },

        "method": (
            "Late-fee constraint derived from "
            "observed payment differences and "
            "late-return behavior."
        )
    }
