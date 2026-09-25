"""
Canonical Sakila business metric definitions.

Every tool that reports revenue or late-return figures should use the
definitions in this module so the dashboard, the AI agent and the
analysis tools always return the same numbers.

Definitions (validated against the original Sakila data):

    total revenue      = SUM(payment.amount)                       -> $67,406.56
    late-fee revenue   = SUM(GREATEST(payment.amount
                                      - film.rental_rate, 0))      -> $20,262.76
    rental revenue     = total revenue - late-fee revenue          -> $47,143.80
    completed rentals  = rental.return_date IS NOT NULL            -> 15,861
    late rental        = return_date > rental_date
                         + INTERVAL film.rental_duration DAY       -> 8,121
                         (exact timestamp comparison, NOT DATEDIFF;
                          DATEDIFF gives 7,269 and is inconsistent)
    late-return rate   = late rentals / completed rentals          -> 51.20%
    store attribution  = inventory.store_id (physical copy rented),
                         NOT customer.store_id
"""

import re
from datetime import date, datetime, timedelta
from decimal import Decimal

from db import get_connection


# ============================================================
# SQL FRAGMENTS
# ============================================================

LATE_CONDITION_SQL = (
    "r.return_date > DATE_ADD("
    "r.rental_date, INTERVAL f.rental_duration DAY)"
)

LATE_FEE_SQL = "GREATEST(p.amount - f.rental_rate, 0)"

LATE_DAYS_SQL = (
    "GREATEST(TIMESTAMPDIFF(SECOND, r.rental_date, r.return_date)"
    " / 86400.0 - f.rental_duration, 0)"
)

METRIC_DEFINITIONS = {
    "total_revenue": "SUM(payment.amount)",
    "late_fee_revenue": "SUM(GREATEST(payment.amount - film.rental_rate, 0))",
    "rental_revenue": "total_revenue - late_fee_revenue",
    "completed_rentals": "rental.return_date IS NOT NULL",
    "late_rental": (
        "return_date > rental_date + rental_duration days "
        "(exact timestamp comparison)"
    ),
    "late_rate_pct": "late_rentals / completed_rentals * 100",
    "store_attribution": "inventory.store_id",
}


# ============================================================
# INPUT NORMALISATION HELPERS
# ============================================================

_CATEGORY_ALIASES = {
    # Vietnamese / common aliases -> Sakila category names
    "hanh dong": "Action",
    "hành động": "Action",
    "hoat hinh": "Animation",
    "hoạt hình": "Animation",
    "tre em": "Children",
    "trẻ em": "Children",
    "thieu nhi": "Children",
    "thiếu nhi": "Children",
    "kinh dien": "Classics",
    "kinh điển": "Classics",
    "classic": "Classics",
    "hai": "Comedy",
    "hài": "Comedy",
    "hai huoc": "Comedy",
    "hài hước": "Comedy",
    "tai lieu": "Documentary",
    "tài liệu": "Documentary",
    "chinh kich": "Drama",
    "chính kịch": "Drama",
    "gia dinh": "Family",
    "gia đình": "Family",
    "nuoc ngoai": "Foreign",
    "nước ngoài": "Foreign",
    "tro choi": "Games",
    "trò chơi": "Games",
    "game": "Games",
    "kinh di": "Horror",
    "kinh dị": "Horror",
    "am nhac": "Music",
    "âm nhạc": "Music",
    "moi": "New",
    "mới": "New",
    "khoa hoc vien tuong": "Sci-Fi",
    "khoa học viễn tưởng": "Sci-Fi",
    "scifi": "Sci-Fi",
    "sci fi": "Sci-Fi",
    "science fiction": "Sci-Fi",
    "the thao": "Sports",
    "thể thao": "Sports",
    "sport": "Sports",
    "du lich": "Travel",
    "du lịch": "Travel",
}

_category_cache = None

# The 16 standard Sakila categories - used only if the DB lookup fails.
SAKILA_CATEGORIES = [
    "Action", "Animation", "Children", "Classics", "Comedy",
    "Documentary", "Drama", "Family", "Foreign", "Games", "Horror",
    "Music", "New", "Sci-Fi", "Sports", "Travel",
]


def get_category_names():
    """Return the Sakila category names (cached, DB first)."""

    global _category_cache

    if _category_cache:
        return list(_category_cache)

    try:
        conn = get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT name FROM category ORDER BY name")
                names = [row[0] for row in cursor.fetchall()]
        finally:
            conn.close()
    except Exception:
        return list(SAKILA_CATEGORIES)

    _category_cache = names or list(SAKILA_CATEGORIES)

    return list(_category_cache)


def normalize_category(category, required=False):
    """
    Map free-text category input (any case, Vietnamese alias)
    to the exact Sakila category name.

    Returns None when category is empty and not required.
    Raises ValueError with the list of valid names otherwise.
    """

    if category is None or str(category).strip() == "":
        if required:
            raise ValueError(
                "category is required. Valid categories: "
                + ", ".join(get_category_names())
            )
        return None

    text = str(category).strip()

    if text.lower() in {"all", "tat ca", "tất cả", "all categories",
                        "all film categories"}:
        return None

    names = get_category_names()

    for name in names:
        if name.lower() == text.lower():
            return name

    alias = _CATEGORY_ALIASES.get(text.lower())

    if alias:
        return alias

    compact = re.sub(r"[^a-z]", "", text.lower())

    for name in names:
        if re.sub(r"[^a-z]", "", name.lower()) == compact:
            return name

    raise ValueError(
        f"Unknown category '{category}'. Valid categories: "
        + ", ".join(names)
    )


def normalize_store_id(store_id):
    """Accept 1, '1', 'Store 1', 'Store #1'."""

    if store_id is None or str(store_id).strip() == "":
        return None

    text = str(store_id).strip().lower()

    if text in {"all", "all stores", "tat ca", "tất cả"}:
        return None

    match = re.search(r"\d+", text)

    if not match:
        raise ValueError(
            f"Invalid store_id '{store_id}'. Use 1 or 2."
        )

    return int(match.group(0))


def _last_day_of_month(year, month):
    if month == 12:
        return date(year, 12, 31)
    return date(year, month + 1, 1) - timedelta(days=1)


def normalize_date(value, is_end=False):
    """
    Accept YYYY-MM-DD, YYYY-MM, YYYY, YYYY/MM/DD, DD/MM/YYYY
    and datetime/date objects. Returns 'YYYY-MM-DD' or None.

    For partial dates:
        start: first day of month/year
        end:   last day of month/year
    """

    if value is None:
        return None

    if isinstance(value, datetime):
        return value.date().isoformat()

    if isinstance(value, date):
        return value.isoformat()

    text = str(value).strip()

    if not text or text.lower() in {"none", "null"}:
        return None

    text = text.replace("/", "-").replace(".", "-")

    # YYYY-MM-DD (optionally with time)
    match = re.match(r"^(\d{4})-(\d{1,2})-(\d{1,2})", text)
    if match:
        y, m, d = (int(x) for x in match.groups())
        return date(y, m, d).isoformat()

    # DD-MM-YYYY
    match = re.match(r"^(\d{1,2})-(\d{1,2})-(\d{4})$", text)
    if match:
        d, m, y = (int(x) for x in match.groups())
        return date(y, m, d).isoformat()

    # YYYY-MM
    match = re.match(r"^(\d{4})-(\d{1,2})$", text)
    if match:
        y, m = (int(x) for x in match.groups())
        if is_end:
            return _last_day_of_month(y, m).isoformat()
        return date(y, m, 1).isoformat()

    # YYYY
    match = re.match(r"^(\d{4})$", text)
    if match:
        y = int(match.group(1))
        return (
            date(y, 12, 31) if is_end else date(y, 1, 1)
        ).isoformat()

    raise ValueError(
        f"Invalid date '{value}'. Use YYYY-MM-DD (for example 2005-07-01)."
    )


def to_number(value, digits=2):
    """Convert DB Decimal / None to a rounded float."""

    if value is None:
        return 0.0

    if isinstance(value, Decimal):
        value = float(value)

    return round(float(value), digits)


def pct(numerator, denominator, digits=2):
    if not denominator:
        return 0.0
    return round(float(numerator) / float(denominator) * 100, digits)


# ============================================================
# SCOPE FILTERS
# ============================================================

def build_scope_filters(
    category=None,
    store_id=None,
    start_date=None,
    end_date=None,
    date_column="p.payment_date",
):
    """
    Build SQL WHERE fragments and params.

    Expects the query to expose aliases:
        r (rental), i (inventory), f (film), c (category)
    and the chosen date column.
    """

    clauses = []
    params = []

    if category:
        clauses.append("c.name = %s")
        params.append(category)

    if store_id is not None:
        clauses.append("i.store_id = %s")
        params.append(store_id)

    if start_date:
        clauses.append(f"{date_column} >= %s")
        params.append(start_date)

    if end_date:
        clauses.append(
            f"{date_column} < DATE_ADD(%s, INTERVAL 1 DAY)"
        )
        params.append(end_date)

    return clauses, params


# ============================================================
# MAIN KPI TOOL
# ============================================================

def get_business_kpis(
    category=None,
    store_id=None,
    start_date=None,
    end_date=None,
):
    """
    Return the headline Sakila KPIs for any scope
    (all data, one category, one store, a date range,
    or any combination).

    Revenue KPIs are filtered by payment.payment_date.
    Rental / late-return KPIs are filtered by rental.rental_date.
    """

    category = normalize_category(category)
    store_id = normalize_store_id(store_id)
    start_date = normalize_date(start_date)
    end_date = normalize_date(end_date, is_end=True)

    # ---------------- revenue ----------------

    rev_clauses, rev_params = build_scope_filters(
        category, store_id, start_date, end_date,
        date_column="p.payment_date",
    )

    revenue_sql = f"""
        SELECT
            COUNT(p.payment_id) AS payment_count,
            COALESCE(SUM(p.amount), 0) AS total_revenue,
            COALESCE(SUM({LATE_FEE_SQL}), 0) AS late_fee_revenue,
            COUNT(DISTINCT p.customer_id) AS paying_customers
        FROM payment p
        JOIN rental r ON p.rental_id = r.rental_id
        JOIN inventory i ON r.inventory_id = i.inventory_id
        JOIN film f ON i.film_id = f.film_id
        JOIN film_category fc ON f.film_id = fc.film_id
        JOIN category c ON fc.category_id = c.category_id
        {"WHERE " + " AND ".join(rev_clauses) if rev_clauses else ""}
    """

    # ---------------- rentals ----------------

    rent_clauses, rent_params = build_scope_filters(
        category, store_id, start_date, end_date,
        date_column="r.rental_date",
    )

    rental_sql = f"""
        SELECT
            COUNT(*) AS total_rentals,
            SUM(r.return_date IS NOT NULL) AS completed_rentals,
            SUM(r.return_date IS NULL) AS open_rentals,
            SUM(
                CASE WHEN r.return_date IS NOT NULL
                          AND {LATE_CONDITION_SQL}
                     THEN 1 ELSE 0 END
            ) AS late_rentals,
            AVG(
                CASE WHEN r.return_date IS NOT NULL
                          AND {LATE_CONDITION_SQL}
                     THEN {LATE_DAYS_SQL} END
            ) AS avg_late_days_when_late,
            COUNT(DISTINCT r.customer_id) AS renting_customers
        FROM rental r
        JOIN inventory i ON r.inventory_id = i.inventory_id
        JOIN film f ON i.film_id = f.film_id
        JOIN film_category fc ON f.film_id = fc.film_id
        JOIN category c ON fc.category_id = c.category_id
        {"WHERE " + " AND ".join(rent_clauses) if rent_clauses else ""}
    """

    conn = get_connection()

    try:
        with conn.cursor(dictionary=True) as cursor:
            cursor.execute(revenue_sql, rev_params)
            rev = cursor.fetchone() or {}

            cursor.execute(rental_sql, rent_params)
            rent = cursor.fetchone() or {}
    finally:
        conn.close()

    total_revenue = to_number(rev.get("total_revenue"))
    late_fee_revenue = to_number(rev.get("late_fee_revenue"))
    rental_revenue = round(total_revenue - late_fee_revenue, 2)
    payment_count = int(rev.get("payment_count") or 0)

    total_rentals = int(rent.get("total_rentals") or 0)
    completed = int(rent.get("completed_rentals") or 0)
    open_rentals = int(rent.get("open_rentals") or 0)
    late = int(rent.get("late_rentals") or 0)

    return {
        "scope": {
            "category": category or "All categories",
            "store_id": store_id if store_id is not None else "All stores",
            "start_date": start_date,
            "end_date": end_date,
        },
        "total_revenue": total_revenue,
        "rental_revenue": rental_revenue,
        "late_fee_revenue": late_fee_revenue,
        "late_fee_contribution_pct": pct(late_fee_revenue, total_revenue),
        "rental_revenue_contribution_pct": pct(rental_revenue, total_revenue),
        "payment_count": payment_count,
        "average_payment": (
            round(total_revenue / payment_count, 2)
            if payment_count else 0.0
        ),
        "paying_customers": int(rev.get("paying_customers") or 0),
        "total_rentals": total_rentals,
        "completed_rentals": completed,
        "open_rentals_not_returned": open_rentals,
        "late_rentals": late,
        "on_time_rentals": completed - late,
        "late_rate_pct": pct(late, completed),
        "avg_late_days_when_late": to_number(
            rent.get("avg_late_days_when_late"), 2
        ),
        "renting_customers": int(rent.get("renting_customers") or 0),
        "definitions": METRIC_DEFINITIONS,
        "data_source": "Sakila MySQL database",
    }


if __name__ == "__main__":
    import json

    print(json.dumps(get_business_kpis(), indent=2, default=str))
