from db import get_connection

from tools.data.business_metrics import (
    LATE_FEE_SQL,
    normalize_category,
    normalize_date,
    normalize_store_id,
    pct,
    to_number,
)


ALLOWED_GROUPS = {
    "day",
    "week",
    "month",
    "quarter",
    "year",
    "category",
    "store",
}

_GROUP_ALIASES = {
    "daily": "day",
    "ngay": "day",
    "ngày": "day",
    "weekly": "week",
    "tuan": "week",
    "tuần": "week",
    "monthly": "month",
    "thang": "month",
    "tháng": "month",
    "quarterly": "quarter",
    "quy": "quarter",
    "quý": "quarter",
    "yearly": "year",
    "annual": "year",
    "nam": "year",
    "năm": "year",
    "categories": "category",
    "danh muc": "category",
    "danh mục": "category",
    "stores": "store",
    "store_id": "store",
    "cua hang": "store",
    "cửa hàng": "store",
}


def get_revenue_by_time(
    start_date=None,
    end_date=None,
    group_by="month",
    category=None,
    store_id=None,
):
    """
    Revenue over a selected time range.

    Revenue = payment.amount, time = payment.payment_date.
    Each group also returns the rental / late-fee split
    (late fee = GREATEST(payment.amount - film.rental_rate, 0)).

    Parameters:
        start_date: inclusive. Accepts YYYY-MM-DD, YYYY-MM or YYYY
        end_date:   inclusive. Accepts YYYY-MM-DD, YYYY-MM or YYYY
                    ('2005-07' as end_date means 2005-07-31)
        group_by:   day | week | month | quarter | year | category | store
        category:   optional category filter (case-insensitive)
        store_id:   optional physical store filter (inventory.store_id)

    FIX:
      - end_date given as 'YYYY-MM' used to become NULL in
        DATE_ADD(...) and silently returned $0 revenue.
      - category names are normalised (e.g. 'sports' -> 'Sports').
      - INNER JOINs instead of LEFT JOINs, so every payment is
        attributed to exactly one film/category/store.
      - adds store filter/grouping, rental/late-fee split and the
        dataset coverage so the agent can explain empty periods.
    """

    group_by = str(group_by or "month").strip().lower()
    group_by = _GROUP_ALIASES.get(group_by, group_by)

    if group_by not in ALLOWED_GROUPS:
        raise ValueError(
            f"Invalid group_by '{group_by}'. "
            f"Allowed values: {sorted(ALLOWED_GROUPS)}"
        )

    start_date = normalize_date(start_date)
    end_date = normalize_date(end_date, is_end=True)
    category = normalize_category(category)
    store_id = normalize_store_id(store_id)

    if start_date and end_date and start_date > end_date:
        start_date, end_date = end_date, start_date

    group_expressions = {
        "day": "DATE_FORMAT(p.payment_date, '%Y-%m-%d')",
        "week": "DATE_FORMAT(p.payment_date, '%x-W%v')",
        "month": "DATE_FORMAT(p.payment_date, '%Y-%m')",
        "quarter": (
            "CONCAT(YEAR(p.payment_date), '-Q', QUARTER(p.payment_date))"
        ),
        "year": "CAST(YEAR(p.payment_date) AS CHAR)",
        "category": "c.name",
        "store": "CONCAT('Store ', i.store_id)",
    }

    group_expression = group_expressions[group_by]

    query = f"""
        SELECT
            {group_expression} AS group_name,
            COUNT(p.payment_id) AS transaction_count,
            COALESCE(SUM(p.amount), 0) AS revenue,
            COALESCE(SUM({LATE_FEE_SQL}), 0) AS late_fee_revenue
        FROM payment p
        JOIN rental r ON p.rental_id = r.rental_id
        JOIN inventory i ON r.inventory_id = i.inventory_id
        JOIN film f ON i.film_id = f.film_id
        JOIN film_category fc ON f.film_id = fc.film_id
        JOIN category c ON fc.category_id = c.category_id
        WHERE 1 = 1
    """

    params = []

    if start_date:
        query += " AND p.payment_date >= %s"
        params.append(start_date)

    if end_date:
        query += " AND p.payment_date < DATE_ADD(%s, INTERVAL 1 DAY)"
        params.append(end_date)

    if category:
        query += " AND c.name = %s"
        params.append(category)

    if store_id is not None:
        query += " AND i.store_id = %s"
        params.append(store_id)

    query += f"""
        GROUP BY {group_expression}
        ORDER BY {group_expression}
    """

    coverage_query = """
        SELECT MIN(payment_date) AS first_payment,
               MAX(payment_date) AS last_payment
        FROM payment
    """

    conn = get_connection()

    try:
        with conn.cursor(dictionary=True) as cursor:
            cursor.execute(query, params)
            rows = cursor.fetchall()

            cursor.execute(coverage_query)
            coverage = cursor.fetchone() or {}
    finally:
        conn.close()

    grouped = []

    for row in rows:
        revenue = to_number(row["revenue"])
        late_fee = to_number(row["late_fee_revenue"])

        grouped.append({
            "group": str(row["group_name"]),
            "transaction_count": int(row["transaction_count"]),
            "revenue": revenue,
            "rental_revenue": round(revenue - late_fee, 2),
            "late_fee_revenue": late_fee,
        })

    if group_by in {"category", "store"}:
        grouped.sort(key=lambda x: x["revenue"], reverse=True)

    total_revenue = round(sum(row["revenue"] for row in grouped), 2)
    total_late_fee = round(
        sum(row["late_fee_revenue"] for row in grouped), 2
    )
    total_transactions = sum(row["transaction_count"] for row in grouped)

    for row in grouped:
        row["revenue_share_pct"] = pct(row["revenue"], total_revenue)

    highest_group = (
        max(grouped, key=lambda x: x["revenue"]) if grouped else None
    )
    lowest_group = (
        min(grouped, key=lambda x: x["revenue"]) if grouped else None
    )

    first_payment = coverage.get("first_payment")
    last_payment = coverage.get("last_payment")

    result = {
        "start_date": start_date,
        "end_date": end_date,
        "group_by": group_by,
        "category_filter": category,
        "store_filter": store_id,
        "total_revenue": total_revenue,
        "total_rental_revenue": round(total_revenue - total_late_fee, 2),
        "total_late_fee_revenue": total_late_fee,
        "total_transactions": total_transactions,
        "group_count": len(grouped),
        "grouped_revenue": grouped,
        "highest_revenue_group": highest_group,
        "lowest_revenue_group": lowest_group,
        "dataset_payment_coverage": {
            "first_payment_date": (
                str(first_payment) if first_payment else None
            ),
            "last_payment_date": (
                str(last_payment) if last_payment else None
            ),
            "note": (
                "Sakila has payments only in 2005-05..2005-08 and "
                "2006-02. Months between them have no data."
            ),
        },
        "data_source": "Sakila MySQL database",
        "revenue_definition": "SUM(payment.amount)",
        "time_definition": "payment.payment_date",
    }

    if not grouped:
        result["message"] = (
            "No payments found for the selected filters/time range."
        )

    return result


if __name__ == "__main__":
    import json

    print(json.dumps(get_revenue_by_time(group_by="month"), indent=2))
