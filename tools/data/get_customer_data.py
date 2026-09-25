from db import get_connection

from tools.data.business_metrics import (
    LATE_CONDITION_SQL,
    LATE_FEE_SQL,
    pct,
    to_number,
)


def get_customer_data():
    """
    Customer-level rental, late-return and payment statistics
    (one row per customer, 599 rows).

    FIX:
      - late returns use the exact timestamp rule (same as the overall
        KPI: 8,121 late rentals). The old DATEDIFF rule undercounted
        late rentals (7,269).
      - numbers are returned as int/float instead of Decimal strings.
      - adds customer name, late rate and payment totals.

    NOTE: this raw function is for Python code. The AI agent uses
    get_customer_summary() (tools/data/llm_views.py) because 599 rows
    are too large for the LLM context and were being truncated.
    """

    query = f"""
        SELECT
            cu.customer_id,
            CONCAT(cu.first_name, ' ', cu.last_name) AS customer_name,
            cu.store_id AS home_store_id,
            cu.active,
            COALESCE(rs.all_rentals, 0) AS all_rentals,
            COALESCE(rs.total_rentals, 0) AS total_rentals,
            COALESCE(rs.late_rentals, 0) AS late_rentals,
            COALESCE(ps.payment_count, 0) AS payment_count,
            COALESCE(ps.total_paid, 0) AS total_paid,
            COALESCE(ps.late_fee_paid, 0) AS late_fee_paid
        FROM customer cu
        LEFT JOIN (
            SELECT
                r.customer_id,
                COUNT(*) AS all_rentals,
                SUM(r.return_date IS NOT NULL) AS total_rentals,
                SUM(
                    CASE WHEN r.return_date IS NOT NULL
                              AND {LATE_CONDITION_SQL}
                         THEN 1 ELSE 0 END
                ) AS late_rentals
            FROM rental r
            JOIN inventory i ON r.inventory_id = i.inventory_id
            JOIN film f ON i.film_id = f.film_id
            GROUP BY r.customer_id
        ) AS rs ON cu.customer_id = rs.customer_id
        LEFT JOIN (
            SELECT
                p.customer_id,
                COUNT(*) AS payment_count,
                SUM(p.amount) AS total_paid,
                SUM({LATE_FEE_SQL}) AS late_fee_paid
            FROM payment p
            JOIN rental r ON p.rental_id = r.rental_id
            JOIN inventory i ON r.inventory_id = i.inventory_id
            JOIN film f ON i.film_id = f.film_id
            GROUP BY p.customer_id
        ) AS ps ON cu.customer_id = ps.customer_id
        ORDER BY cu.customer_id
    """

    conn = get_connection()

    try:
        with conn.cursor(dictionary=True) as cursor:
            cursor.execute(query)
            rows = cursor.fetchall()
    finally:
        conn.close()

    results = []

    for row in rows:
        completed = int(row["total_rentals"] or 0)
        late = int(row["late_rentals"] or 0)

        results.append({
            "customer_id": int(row["customer_id"]),
            "customer_name": row["customer_name"],
            "home_store_id": int(row["home_store_id"]),
            "active": bool(row["active"]),
            # completed (returned) rentals - denominator of late rate
            "total_rentals": completed,
            "late_rentals": late,
            "late_rate": round(late / completed, 4) if completed else 0.0,
            "late_rate_pct": pct(late, completed),
            "all_rentals_including_open": int(row["all_rentals"] or 0),
            "payment_count": int(row["payment_count"] or 0),
            "total_paid": to_number(row["total_paid"]),
            "late_fee_paid": to_number(row["late_fee_paid"]),
        })

    return results


if __name__ == "__main__":
    data = get_customer_data()
    print(len(data))
    for item in data[:5]:
        print(item)
