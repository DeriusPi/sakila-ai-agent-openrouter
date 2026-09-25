"""
Compact, LLM-friendly views of large Sakila tables.

Why this file exists
--------------------
get_rental_data() returns ~15,861 rows (3.5 MB of JSON),
get_film_data() returns 1,000 rows and get_customer_data() 599 rows.
When the agent called these tools, llm.py truncated the result to the
first 100 rows / 30,000 characters and the model then calculated KPIs
from that partial sample -> wrong numbers.

The functions below aggregate in SQL/Python and return small, complete
summaries (plus an optional short list of detail rows), so everything
the model sees is exact.

The original raw functions are kept unchanged for internal Python use
(simulation, ML training, ...).
"""

from decimal import Decimal

from db import get_connection

from tools.data.business_metrics import (
    LATE_CONDITION_SQL,
    LATE_FEE_SQL,
    normalize_category,
    normalize_date,
    normalize_store_id,
    pct,
    to_number,
)
from tools.data.get_customer_data import get_customer_data


MAX_ROWS = 50


def _limit(value, default=10):
    try:
        value = int(value)
    except (TypeError, ValueError):
        value = default
    return max(1, min(value, MAX_ROWS))


def _fetch_all(query, params=None):
    conn = get_connection()
    try:
        with conn.cursor(dictionary=True) as cursor:
            cursor.execute(query, params or [])
            return cursor.fetchall()
    finally:
        conn.close()


# ============================================================
# RENTAL SUMMARY
# ============================================================

def get_rental_summary(
    category=None,
    store_id=None,
    start_date=None,
    end_date=None,
):
    """
    Aggregated rental behaviour (replaces raw get_rental_data for the
    agent). Filters by rental.rental_date, category and physical store.

    Returns totals plus breakdowns by rental_duration, rental_rate and
    month, each with completed rentals, late rentals and late rate.
    """

    category = normalize_category(category)
    store_id = normalize_store_id(store_id)
    start_date = normalize_date(start_date)
    end_date = normalize_date(end_date, is_end=True)

    where = ["1 = 1"]
    params = []

    if category:
        where.append("c.name = %s")
        params.append(category)
    if store_id is not None:
        where.append("i.store_id = %s")
        params.append(store_id)
    if start_date:
        where.append("r.rental_date >= %s")
        params.append(start_date)
    if end_date:
        where.append("r.rental_date < DATE_ADD(%s, INTERVAL 1 DAY)")
        params.append(end_date)

    base = f"""
        FROM rental r
        JOIN inventory i ON r.inventory_id = i.inventory_id
        JOIN film f ON i.film_id = f.film_id
        JOIN film_category fc ON f.film_id = fc.film_id
        JOIN category c ON fc.category_id = c.category_id
        WHERE {" AND ".join(where)}
    """

    metrics = f"""
        COUNT(*) AS all_rentals,
        SUM(r.return_date IS NOT NULL) AS completed_rentals,
        SUM(CASE WHEN r.return_date IS NOT NULL AND {LATE_CONDITION_SQL}
                 THEN 1 ELSE 0 END) AS late_rentals,
        AVG(CASE WHEN r.return_date IS NOT NULL
                 THEN TIMESTAMPDIFF(SECOND, r.rental_date, r.return_date)
                      / 86400.0 END) AS avg_actual_days
    """

    def breakdown(expression, label):
        rows = _fetch_all(
            f"SELECT {expression} AS dim, {metrics} {base} "
            f"GROUP BY {expression} ORDER BY {expression}",
            params,
        )
        out = []
        for row in rows:
            completed = int(row["completed_rentals"] or 0)
            late = int(row["late_rentals"] or 0)
            dim = row["dim"]
            if isinstance(dim, Decimal):
                dim = float(dim)
            out.append({
                label: dim,
                "rentals": int(row["all_rentals"] or 0),
                "completed_rentals": completed,
                "late_rentals": late,
                "late_rate_pct": pct(late, completed),
                "avg_actual_rental_days": to_number(row["avg_actual_days"]),
            })
        return out

    total = _fetch_all(f"SELECT {metrics} {base}", params)[0]
    completed = int(total["completed_rentals"] or 0)
    late = int(total["late_rentals"] or 0)

    return {
        "filters": {
            "category": category,
            "store_id": store_id,
            "start_date": start_date,
            "end_date": end_date,
            "date_field": "rental.rental_date",
        },
        "total_rentals": int(total["all_rentals"] or 0),
        "completed_rentals": completed,
        "open_rentals_not_returned": int(total["all_rentals"] or 0) - completed,
        "late_rentals": late,
        "on_time_rentals": completed - late,
        "late_rate_pct": pct(late, completed),
        "avg_actual_rental_days": to_number(total["avg_actual_days"]),
        "by_rental_duration": breakdown("f.rental_duration", "rental_duration_days"),
        "by_rental_rate": breakdown("f.rental_rate", "rental_rate"),
        "by_month": breakdown("DATE_FORMAT(r.rental_date, '%Y-%m')", "month"),
        "late_definition": (
            "return_date > rental_date + rental_duration days "
            "(exact timestamp)"
        ),
        "note": "Aggregated in SQL - complete data, not a sample.",
    }


# ============================================================
# FILM CATALOG
# ============================================================

_FILM_SORTS = {
    "revenue": "total_revenue DESC",
    "rentals": "rental_count DESC",
    "late_fee": "late_fee_revenue DESC",
    "rental_rate": "f.rental_rate DESC",
    "title": "f.title ASC",
}


def get_film_catalog(
    category=None,
    title_contains=None,
    sort_by="revenue",
    limit=10,
):
    """
    Film catalogue summary (replaces raw get_film_data for the agent).

    Returns catalogue-level statistics (film count, rate/duration
    distribution) for the filter, plus the top N films sorted by
    revenue, rentals, late_fee, rental_rate or title.
    """

    category = normalize_category(category)
    limit = _limit(limit)
    sort_sql = _FILM_SORTS.get(str(sort_by or "revenue").lower(),
                               _FILM_SORTS["revenue"])

    where = ["1 = 1"]
    params = []

    if category:
        where.append("c.name = %s")
        params.append(category)
    if title_contains:
        where.append("f.title LIKE %s")
        params.append(f"%{str(title_contains).strip()}%")

    where_sql = " AND ".join(where)

    stats = _fetch_all(
        f"""
        SELECT
            COUNT(*) AS film_count,
            ROUND(AVG(f.rental_rate), 2) AS avg_rental_rate,
            ROUND(AVG(f.rental_duration), 2) AS avg_rental_duration,
            ROUND(AVG(f.replacement_cost), 2) AS avg_replacement_cost,
            ROUND(AVG(f.length), 1) AS avg_length_minutes
        FROM film f
        JOIN film_category fc ON f.film_id = fc.film_id
        JOIN category c ON fc.category_id = c.category_id
        WHERE {where_sql}
        """,
        params,
    )[0]

    rate_dist = _fetch_all(
        f"""
        SELECT f.rental_rate AS rental_rate, COUNT(*) AS films
        FROM film f
        JOIN film_category fc ON f.film_id = fc.film_id
        JOIN category c ON fc.category_id = c.category_id
        WHERE {where_sql}
        GROUP BY f.rental_rate ORDER BY f.rental_rate
        """,
        params,
    )

    duration_dist = _fetch_all(
        f"""
        SELECT f.rental_duration AS rental_duration, COUNT(*) AS films
        FROM film f
        JOIN film_category fc ON f.film_id = fc.film_id
        JOIN category c ON fc.category_id = c.category_id
        WHERE {where_sql}
        GROUP BY f.rental_duration ORDER BY f.rental_duration
        """,
        params,
    )

    films = _fetch_all(
        f"""
        SELECT
            f.film_id,
            f.title,
            c.name AS category,
            f.rental_rate,
            f.rental_duration,
            f.rating,
            COALESCE(x.rental_count, 0) AS rental_count,
            COALESCE(x.total_revenue, 0) AS total_revenue,
            COALESCE(x.late_fee_revenue, 0) AS late_fee_revenue
        FROM film f
        JOIN film_category fc ON f.film_id = fc.film_id
        JOIN category c ON fc.category_id = c.category_id
        LEFT JOIN (
            SELECT
                i.film_id,
                COUNT(DISTINCT r.rental_id) AS rental_count,
                SUM(p.amount) AS total_revenue,
                SUM({LATE_FEE_SQL}) AS late_fee_revenue
            FROM inventory i
            JOIN film f ON i.film_id = f.film_id
            JOIN rental r ON r.inventory_id = i.inventory_id
            LEFT JOIN payment p ON p.rental_id = r.rental_id
            GROUP BY i.film_id
        ) AS x ON x.film_id = f.film_id
        WHERE {where_sql}
        ORDER BY {sort_sql}, f.film_id
        LIMIT {limit}
        """,
        params,
    )

    return {
        "filters": {
            "category": category,
            "title_contains": title_contains,
            "sort_by": sort_by,
            "limit": limit,
        },
        "film_count": int(stats["film_count"] or 0),
        "avg_rental_rate": to_number(stats["avg_rental_rate"]),
        "avg_rental_duration_days": to_number(stats["avg_rental_duration"]),
        "avg_replacement_cost": to_number(stats["avg_replacement_cost"]),
        "avg_length_minutes": to_number(stats["avg_length_minutes"], 1),
        "rental_rate_distribution": [
            {"rental_rate": to_number(r["rental_rate"]),
             "films": int(r["films"])}
            for r in rate_dist
        ],
        "rental_duration_distribution": [
            {"rental_duration_days": int(r["rental_duration"]),
             "films": int(r["films"])}
            for r in duration_dist
        ],
        "top_films": [
            {
                "film_id": int(r["film_id"]),
                "title": r["title"],
                "category": r["category"],
                "rental_rate": to_number(r["rental_rate"]),
                "rental_duration_days": int(r["rental_duration"]),
                "rating": r["rating"],
                "rental_count": int(r["rental_count"] or 0),
                "total_revenue": to_number(r["total_revenue"]),
                "late_fee_revenue": to_number(r["late_fee_revenue"]),
            }
            for r in films
        ],
        "note": (
            "Statistics cover every matching film; top_films is limited "
            f"to {limit} rows."
        ),
    }


# ============================================================
# CUSTOMER SUMMARY
# ============================================================

_CUSTOMER_SORTS = {
    "late_rate": lambda c: (c["late_rate_pct"], c["total_rentals"]),
    "late_rentals": lambda c: (c["late_rentals"], c["late_rate_pct"]),
    "rentals": lambda c: (c["total_rentals"], c["total_paid"]),
    "revenue": lambda c: (c["total_paid"], c["total_rentals"]),
    "late_fee": lambda c: (c["late_fee_paid"], c["total_paid"]),
}


def get_customer_summary(
    customer_id=None,
    sort_by="late_rate",
    limit=10,
    min_rentals=10,
):
    """
    Customer behaviour summary (replaces raw get_customer_data for the
    agent).

    - customer_id given: returns that customer's full statistics.
    - otherwise: returns distribution statistics for all 599 customers
      and the top N customers sorted by late_rate, late_rentals,
      rentals, revenue or late_fee.
    """

    customers = get_customer_data()

    if customer_id not in (None, ""):
        try:
            cid = int(customer_id)
        except (TypeError, ValueError):
            raise ValueError(f"Invalid customer_id '{customer_id}'.")

        for row in customers:
            if row["customer_id"] == cid:
                return {"customer": row}

        raise ValueError(f"customer_id {cid} not found.")

    limit = _limit(limit)

    try:
        min_rentals = max(0, int(min_rentals))
    except (TypeError, ValueError):
        min_rentals = 10

    sort_key = _CUSTOMER_SORTS.get(
        str(sort_by or "late_rate").lower(),
        _CUSTOMER_SORTS["late_rate"],
    )

    rates = sorted(
        c["late_rate_pct"] for c in customers if c["total_rentals"] > 0
    )

    def percentile(values, q):
        if not values:
            return 0.0
        index = min(len(values) - 1, max(0, round(q * (len(values) - 1))))
        return values[index]

    buckets = [
        ("0-25%", 0, 25),
        ("25-50%", 25, 50),
        ("50-75%", 50, 75),
        ("75-100%", 75, 100.0001),
    ]

    distribution = [
        {
            "late_rate_bucket": label,
            "customers": sum(1 for r in rates if low <= r < high),
        }
        for label, low, high in buckets
    ]

    eligible = [c for c in customers if c["total_rentals"] >= min_rentals]
    top = sorted(eligible, key=sort_key, reverse=True)[:limit]

    total_completed = sum(c["total_rentals"] for c in customers)
    total_late = sum(c["late_rentals"] for c in customers)

    return {
        "customer_count": len(customers),
        "active_customers": sum(1 for c in customers if c["active"]),
        "total_completed_rentals": total_completed,
        "total_late_rentals": total_late,
        "overall_late_rate_pct": pct(total_late, total_completed),
        "customer_late_rate_stats_pct": {
            "min": rates[0] if rates else 0.0,
            "p25": percentile(rates, 0.25),
            "median": percentile(rates, 0.5),
            "average": round(sum(rates) / len(rates), 2) if rates else 0.0,
            "p75": percentile(rates, 0.75),
            "max": rates[-1] if rates else 0.0,
        },
        "late_rate_distribution": distribution,
        "avg_rentals_per_customer": (
            round(total_completed / len(customers), 2) if customers else 0.0
        ),
        "avg_revenue_per_customer": (
            round(sum(c["total_paid"] for c in customers) / len(customers), 2)
            if customers else 0.0
        ),
        "top_customers": {
            "sorted_by": sort_by,
            "min_rentals": min_rentals,
            "rows": top,
        },
        "note": (
            "customer_late_rate for ML tools = late_rate (0-1), "
            "e.g. 0.512, not 51.2."
        ),
    }


if __name__ == "__main__":
    import json

    print(json.dumps(get_rental_summary(), indent=1, default=str)[:2000])
    print(json.dumps(get_film_catalog(limit=3), indent=1, default=str)[:2000])
    print(json.dumps(get_customer_summary(limit=3), indent=1, default=str)[:2000])
