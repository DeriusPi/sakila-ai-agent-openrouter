from db import get_connection

from tools.data.business_metrics import (
    LATE_CONDITION_SQL,
    LATE_FEE_SQL,
    pct,
    to_number,
)


def get_store_data():
    """
    Store-level rental, late-return and revenue statistics.

    Revenue is attributed to the physical store that owned the rented
    copy: store -> inventory -> rental -> payment
    (NOT customer.store_id).

    FIX:
      - numbers returned as int/float instead of Decimal strings
      - rentals counted with COUNT(DISTINCT) so a rental with several
        payments is not double counted
      - adds rental revenue, late-fee revenue, late-return rate and
        store location so the dashboard no longer has to show "—"
        for store-level late fees.
    """

    # Derived tables (no CTE) so the query also runs on MySQL 5.7.
    query = f"""
        SELECT
            s.store_id,
            ci.city,
            co.country,
            COALESCE(rentals.all_rentals, 0) AS total_rentals,
            COALESCE(rentals.completed_rentals, 0) AS completed_rentals,
            COALESCE(rentals.late_rentals, 0) AS late_rentals,
            COALESCE(revenue.payment_count, 0) AS payment_count,
            COALESCE(revenue.total_revenue, 0) AS total_revenue,
            COALESCE(revenue.late_fee_revenue, 0) AS late_fee_revenue,
            COALESCE(stock.inventory_items, 0) AS inventory_items
        FROM store s
        LEFT JOIN address a ON s.address_id = a.address_id
        LEFT JOIN city ci ON a.city_id = ci.city_id
        LEFT JOIN country co ON ci.country_id = co.country_id
        LEFT JOIN (
            SELECT
                i.store_id,
                COUNT(DISTINCT r.rental_id) AS all_rentals,
                SUM(r.return_date IS NOT NULL) AS completed_rentals,
                SUM(
                    CASE WHEN r.return_date IS NOT NULL
                              AND {LATE_CONDITION_SQL}
                         THEN 1 ELSE 0 END
                ) AS late_rentals
            FROM rental r
            JOIN inventory i ON r.inventory_id = i.inventory_id
            JOIN film f ON i.film_id = f.film_id
            GROUP BY i.store_id
        ) AS rentals ON s.store_id = rentals.store_id
        LEFT JOIN (
            SELECT
                i.store_id,
                COUNT(p.payment_id) AS payment_count,
                SUM(p.amount) AS total_revenue,
                SUM({LATE_FEE_SQL}) AS late_fee_revenue
            FROM payment p
            JOIN rental r ON p.rental_id = r.rental_id
            JOIN inventory i ON r.inventory_id = i.inventory_id
            JOIN film f ON i.film_id = f.film_id
            GROUP BY i.store_id
        ) AS revenue ON s.store_id = revenue.store_id
        LEFT JOIN (
            SELECT store_id, COUNT(*) AS inventory_items
            FROM inventory
            GROUP BY store_id
        ) AS stock ON s.store_id = stock.store_id
        ORDER BY s.store_id
    """

    conn = get_connection()

    try:
        with conn.cursor(dictionary=True) as cursor:
            cursor.execute(query)
            rows = cursor.fetchall()
    finally:
        conn.close()

    grand_total = sum(to_number(r["total_revenue"]) for r in rows)

    results = []

    for row in rows:
        total_revenue = to_number(row["total_revenue"])
        late_fee_revenue = to_number(row["late_fee_revenue"])
        completed = int(row["completed_rentals"] or 0)
        late = int(row["late_rentals"] or 0)

        results.append({
            "store_id": int(row["store_id"]),
            "city": row.get("city"),
            "country": row.get("country"),
            "total_rentals": int(row["total_rentals"] or 0),
            "completed_rentals": completed,
            "late_rentals": late,
            "late_rate_pct": pct(late, completed),
            "payment_count": int(row["payment_count"] or 0),
            "total_revenue": total_revenue,
            "rental_revenue": round(total_revenue - late_fee_revenue, 2),
            "late_fee_revenue": late_fee_revenue,
            "late_fee_contribution_pct": pct(late_fee_revenue, total_revenue),
            "revenue_share_pct": pct(total_revenue, grand_total),
            "inventory_items": int(row["inventory_items"] or 0),
        })

    return results


if __name__ == "__main__":
    for item in get_store_data():
        print(item)
