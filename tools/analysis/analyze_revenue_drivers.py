from decimal import Decimal

from db import get_connection

from tools.data.business_metrics import (
    LATE_CONDITION_SQL,
    LATE_DAYS_SQL,
    LATE_FEE_SQL,
    pct,
    to_number,
)


def _fetch_all(query):
    conn = get_connection()
    try:
        with conn.cursor(dictionary=True) as cursor:
            cursor.execute(query)
            return cursor.fetchall()
    finally:
        conn.close()


def analyze_revenue_drivers():
    """
    Late-fee revenue drivers by category, rental duration and rental
    rate, plus the late-days distribution.

    Every dimension returns (same keys as before, plus new ones):
        dimension, transactions, late_fee_revenue, avg_late_fee,
        total_revenue, completed_rentals, late_rentals, late_rate_pct

    FIX:
      - computed in SQL (no Python loops over 16k raw rows)
      - adds late-return rate per dimension, so "why" questions can be
        answered from one tool
      - late_days_distribution now separates on-time rentals from
        rentals that were late by less than one day (both were lumped
        into bucket 0 before, 9,458 rows).
    """

    revenue_sql = """
        SELECT
            {dim} AS dimension,
            COUNT(p.payment_id) AS transactions,
            SUM(p.amount) AS total_revenue,
            SUM({late_fee}) AS late_fee_revenue
        FROM payment p
        JOIN rental r ON p.rental_id = r.rental_id
        JOIN inventory i ON r.inventory_id = i.inventory_id
        JOIN film f ON i.film_id = f.film_id
        JOIN film_category fc ON f.film_id = fc.film_id
        JOIN category c ON fc.category_id = c.category_id
        GROUP BY {dim}
    """

    late_sql = """
        SELECT
            {dim} AS dimension,
            COUNT(*) AS completed_rentals,
            SUM(CASE WHEN {late} THEN 1 ELSE 0 END) AS late_rentals,
            AVG(CASE WHEN {late} THEN {late_days} END) AS avg_late_days
        FROM rental r
        JOIN inventory i ON r.inventory_id = i.inventory_id
        JOIN film f ON i.film_id = f.film_id
        JOIN film_category fc ON f.film_id = fc.film_id
        JOIN category c ON fc.category_id = c.category_id
        WHERE r.return_date IS NOT NULL
        GROUP BY {dim}
    """

    def dimension_stats(dim):
        revenue_rows = _fetch_all(
            revenue_sql.format(dim=dim, late_fee=LATE_FEE_SQL)
        )
        late_rows = _fetch_all(
            late_sql.format(
                dim=dim, late=LATE_CONDITION_SQL, late_days=LATE_DAYS_SQL
            )
        )

        def key(value):
            return float(value) if isinstance(value, Decimal) else value

        late_map = {key(r["dimension"]): r for r in late_rows}

        result = []

        for row in revenue_rows:
            dimension = key(row["dimension"])
            transactions = int(row["transactions"] or 0)
            late_fee = to_number(row["late_fee_revenue"])
            late_row = late_map.get(dimension, {})
            completed = int(late_row.get("completed_rentals") or 0)
            late = int(late_row.get("late_rentals") or 0)

            result.append({
                "dimension": dimension,
                "transactions": transactions,
                "total_revenue": to_number(row["total_revenue"]),
                "late_fee_revenue": late_fee,
                "avg_late_fee": (
                    round(late_fee / transactions, 2)
                    if transactions else 0.0
                ),
                "completed_rentals": completed,
                "late_rentals": late,
                "late_rate_pct": pct(late, completed),
                "avg_late_days_when_late": to_number(
                    late_row.get("avg_late_days")
                ),
            })

        result.sort(key=lambda x: x["late_fee_revenue"], reverse=True)

        return result

    distribution_rows = _fetch_all(
        f"""
        SELECT
            CASE
                WHEN NOT ({LATE_CONDITION_SQL}) THEN 'on_time'
                ELSE CAST(FLOOR({LATE_DAYS_SQL}) AS CHAR)
            END AS bucket,
            COUNT(*) AS rentals
        FROM rental r
        JOIN inventory i ON r.inventory_id = i.inventory_id
        JOIN film f ON i.film_id = f.film_id
        WHERE r.return_date IS NOT NULL
        GROUP BY bucket
        """
    )

    distribution = {"on_time": 0}
    late_buckets = {}

    for row in distribution_rows:
        bucket = str(row["bucket"])
        if bucket == "on_time":
            distribution["on_time"] = int(row["rentals"])
        else:
            days = int(float(bucket))
            label = f"late_{days}_to_{days + 1}_days"
            late_buckets[days] = (label, int(row["rentals"]))

    for days in sorted(late_buckets):
        label, count = late_buckets[days]
        distribution[label] = count

    return {
        "category": dimension_stats("c.name"),
        "rental_duration": dimension_stats("f.rental_duration"),
        "rental_rate": dimension_stats("f.rental_rate"),
        "late_days_distribution": distribution,
        "definitions": {
            "late_fee": "GREATEST(payment.amount - film.rental_rate, 0)",
            "late_rental": (
                "return_date > rental_date + rental_duration days"
            ),
        },
    }


if __name__ == "__main__":
    import json

    result = analyze_revenue_drivers()
    print(json.dumps(result, indent=2)[:4000])
