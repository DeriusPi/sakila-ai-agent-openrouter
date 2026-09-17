from tools.data.get_late_fee_data import get_late_fee_data


def get_late_return_summary():
    """
    Calculate system-wide late-return statistics
    from actual Sakila rental data.
    """

    data = get_late_fee_data()

    if not data:
        return {
            "total_rentals": 0,
            "late_rentals": 0,
            "on_time_rentals": 0,
            "late_rate": 0.0,
            "late_rate_pct": 0.0
        }

    total_rentals = len(data)

    late_rentals = sum(
        1
        for row in data
        if row["is_late"]
    )

    on_time_rentals = total_rentals - late_rentals

    late_rate = late_rentals / total_rentals

    return {
        "total_rentals": total_rentals,
        "late_rentals": late_rentals,
        "on_time_rentals": on_time_rentals,
        "late_rate": round(late_rate, 4),
        "late_rate_pct": round(late_rate * 100, 2)
    }


if __name__ == "__main__":
    result = get_late_return_summary()

    print("\n==============================")
    print("LATE RETURN SUMMARY")
    print("==============================")

    for key, value in result.items():
        print(f"{key}: {value}")
