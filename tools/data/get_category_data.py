from db import get_connection

from tools.data.business_metrics import (
    LATE_CONDITION_SQL,
    LATE_FEE_SQL,
    build_scope_filters,
    normalize_date,
    normalize_store_id,
    pct,
    to_number,
)


def get_category_data(store_id=None, start_date=None, end_date=None):
    """
    Category-level rental, late-return and revenue statistics.

    FIX: late returns now use the exact timestamp rule
    (return_date > rental_date + rental_duration days), the same rule
    used by the overall KPIs (8,121 late / 15,861 completed = 51.20%).
    The previous DATEDIFF rule only found 7,269 late rentals, so
    category late rates did not reconcile with the overall rate.

    Numbers are returned as int/float (not Decimal strings).

    Optional filters: store_id, start_date, end_date (YYYY-MM-DD,
    YYYY-MM or YYYY). As in get_business_kpis, revenue is filtered by
    payment.payment_date and rentals / late returns by rental.rental_date.

    Returns one row per category (16 rows), sorted by total_rentals.
    """

    store_id = normalize_store_id(store_id)
    start_date = normalize_date(start_date)
    end_date = normalize_date(end_date, is_end=True)

    rent_clauses, rent_params = build_scope_filters(
        None, store_id, start_date, end_date, date_column="r.rental_date",
    )
    rev_clauses, rev_params = build_scope_filters(
        None, store_id, start_date, end_date, date_column="p.payment_date",
    )

    rental_filter = (
        "WHERE " + " AND ".join(rent_clauses) if rent_clauses else ""
    )
    revenue_filter = (
        "WHERE " + " AND ".join(rev_clauses) if rev_clauses else ""
    )
    params = rent_params + rev_params

    # Derived tables (no CTE) so the query also runs on MySQL 5.7.
    query = f"""
        SELECT
            cat.category_id,
            cat.name AS category,
            COALESCE(rentals.all_rentals, 0) AS all_rentals,
            COALESCE(rentals.total_rentals, 0) AS total_rentals,
            COALESCE(rentals.late_rentals, 0) AS late_rentals,
            COALESCE(revenue.payment_count, 0) AS payment_count,
            COALESCE(revenue.total_revenue, 0) AS total_revenue,
            COALESCE(revenue.late_fee_revenue, 0) AS late_fee_revenue
        FROM category cat
        LEFT JOIN (
            SELECT
                c.category_id,
                COUNT(*) AS all_rentals,
                SUM(r.return_date IS NOT NULL) AS total_rentals,
                SUM(
                    CASE WHEN r.return_date IS NOT NULL
                              AND {LATE_CONDITION_SQL}
                         THEN 1 ELSE 0 END
                ) AS late_rentals
            FROM category c
            JOIN film_category fc ON c.category_id = fc.category_id
            JOIN film f ON fc.film_id = f.film_id
            JOIN inventory i ON f.film_id = i.film_id
            JOIN rental r ON i.inventory_id = r.inventory_id
            {rental_filter}
            GROUP BY c.category_id
        ) AS rentals ON cat.category_id = rentals.category_id
        LEFT JOIN (
            SELECT
                fc.category_id,
                COUNT(p.payment_id) AS payment_count,
                SUM(p.amount) AS total_revenue,
                SUM({LATE_FEE_SQL}) AS late_fee_revenue
            FROM payment p
            JOIN rental r ON p.rental_id = r.rental_id
            JOIN inventory i ON r.inventory_id = i.inventory_id
            JOIN film f ON i.film_id = f.film_id
            JOIN film_category fc ON f.film_id = fc.film_id
            {revenue_filter}
            GROUP BY fc.category_id
        ) AS revenue ON cat.category_id = revenue.category_id
        ORDER BY total_rentals DESC, category
    """

    conn = get_connection()

    try:
        with conn.cursor(dictionary=True) as cursor:
            cursor.execute(query, params)
            rows = cursor.fetchall()
    finally:
        conn.close()

    results = []

    for row in rows:
        completed = int(row["total_rentals"] or 0)
        late = int(row["late_rentals"] or 0)
        total_revenue = to_number(row["total_revenue"])
        late_fee_revenue = to_number(row["late_fee_revenue"])

        results.append({
            "category_id": int(row["category_id"]),
            "category": row["category"],
            # completed (returned) rentals - denominator of late rate
            "total_rentals": completed,
            "late_rentals": late,
            "on_time_rentals": completed - late,
            "late_rate_pct": pct(late, completed),
            "all_rentals_including_open": int(row["all_rentals"] or 0),
            "payment_count": int(row["payment_count"] or 0),
            "total_revenue": total_revenue,
            "rental_revenue": round(total_revenue - late_fee_revenue, 2),
            "late_fee_revenue": late_fee_revenue,
            "late_fee_contribution_pct": pct(late_fee_revenue, total_revenue),
        })

    return results


if __name__ == "__main__":
    for item in get_category_data():
        print(item)
