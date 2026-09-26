"""
Revenue by ANY relationship in the Sakila schema.

NEW: the agent could only analyse revenue by category, store, time, film
and customer. These tools cover every relationship in the database:

    film      -> category, actor (film_actor), language, rating,
                 release year, length, rental duration, rental rate,
                 replacement cost, special features
    payment   -> staff (who took the payment), payment month / weekday /
                 hour
    rental    -> inventory -> store
    customer  -> address -> city -> country, active flag, home store
    actor     -> actor PAIRS (actors who appear in the same films)

get_revenue_breakdown()  : revenue by one or two dimensions from the
                           whitelist below (safe - no free SQL).
get_actor_pair_revenue() : revenue of films shared by two actors.

Attribution rules
-----------------
* Revenue = SUM(payment.amount); late-fee revenue =
  SUM(GREATEST(amount - film.rental_rate, 0)); late rental = returned
  after rental_date + rental_duration days (same as get_business_kpis).
* Single-valued dimensions (category, rating, store, country, ...) are
  ADDITIVE: the groups sum to the total revenue.
* Multi-valued dimensions (actor, special_feature, actor pairs) are NOT
  additive: a film with 5 actors counts fully for each of them. For
  actors, "shared_revenue" splits each payment equally between the
  film's actors, and that column IS additive.
"""

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


MAX_TOP_N = 100
SPECIAL_FEATURES = [
    "Trailers", "Commentaries", "Deleted Scenes", "Behind the Scenes",
]

# ------------------------------------------------------------------
# JOIN fragments (added only when a dimension / filter needs them)
# ------------------------------------------------------------------

_JOINS = {
    "category": (
        "JOIN film_category fc ON fc.film_id = f.film_id "
        "JOIN category c ON c.category_id = fc.category_id"
    ),
    "language": "JOIN language l ON l.language_id = f.language_id",
    "customer": "JOIN customer cu ON cu.customer_id = p.customer_id",
    "geo": (
        "JOIN address ca ON ca.address_id = cu.address_id "
        "JOIN city ci ON ci.city_id = ca.city_id "
        "JOIN country co ON co.country_id = ci.country_id"
    ),
    "staff": "JOIN staff s ON s.staff_id = p.staff_id",
    "actor": (
        "JOIN film_actor fa ON fa.film_id = f.film_id "
        "JOIN actor a ON a.actor_id = fa.actor_id "
        "JOIN (SELECT film_id, COUNT(*) AS n_actors FROM film_actor "
        "GROUP BY film_id) fac ON fac.film_id = f.film_id"
    ),
    "feature": (
        "JOIN (" + " UNION ALL ".join(
            f"SELECT '{name}' AS feature" for name in SPECIAL_FEATURES
        ) + ") sf ON FIND_IN_SET(sf.feature, f.special_features) > 0"
    ),
}
_JOIN_ORDER = ["category", "language", "customer", "geo", "staff",
               "actor", "feature"]

# ------------------------------------------------------------------
# Dimension whitelist: key -> (label SQL, sort SQL, joins, multi-valued,
#                              description)
# ------------------------------------------------------------------

DIMENSIONS = {
    "category": ("c.name", "c.name", {"category"}, False,
                 "Film category"),
    "film": ("f.title", "f.title", set(), False, "Film title"),
    "actor": ("CONCAT(a.first_name, ' ', a.last_name)",
              "CONCAT(a.first_name, ' ', a.last_name)", {"actor"}, True,
              "Actor (films the actor appears in)"),
    "rating": ("f.rating", "FIELD(f.rating, 'G','PG','PG-13','R','NC-17')",
               set(), False, "MPAA rating"),
    "language": ("l.name", "l.name", {"language"}, False, "Film language"),
    "release_year": ("CAST(f.release_year AS CHAR)", "f.release_year",
                     set(), False, "Release year"),
    "rental_duration": ("CONCAT(f.rental_duration, ' days')",
                        "f.rental_duration", set(), False,
                        "Allowed rental duration"),
    "rental_rate": ("CONCAT('$', f.rental_rate)", "f.rental_rate", set(),
                    False, "Rental price"),
    "replacement_cost": (
        "CASE WHEN f.replacement_cost < 15 THEN '$9.99-14.99' "
        "WHEN f.replacement_cost < 20 THEN '$15-19.99' "
        "WHEN f.replacement_cost < 25 THEN '$20-24.99' "
        "ELSE '$25-29.99' END",
        "CASE WHEN f.replacement_cost < 15 THEN 1 "
        "WHEN f.replacement_cost < 20 THEN 2 "
        "WHEN f.replacement_cost < 25 THEN 3 ELSE 4 END",
        set(), False, "Replacement cost band"),
    "length": (
        "CASE WHEN f.length < 60 THEN '< 60 min' "
        "WHEN f.length < 90 THEN '60-89 min' "
        "WHEN f.length < 120 THEN '90-119 min' "
        "WHEN f.length < 150 THEN '120-149 min' ELSE '150+ min' END",
        "CASE WHEN f.length < 60 THEN 1 WHEN f.length < 90 THEN 2 "
        "WHEN f.length < 120 THEN 3 WHEN f.length < 150 THEN 4 ELSE 5 END",
        set(), False, "Film length band"),
    "special_feature": ("sf.feature", "sf.feature", {"feature"}, True,
                        "Special feature on the film"),
    "store": ("CONCAT('Store #', i.store_id)", "i.store_id", set(), False,
              "Store that owns the rented copy"),
    "staff": ("CONCAT(s.first_name, ' ', s.last_name)", "s.staff_id",
              {"staff"}, False, "Staff member who took the payment"),
    "customer": ("CONCAT(cu.first_name, ' ', cu.last_name, ' (#', "
                 "cu.customer_id, ')')", "cu.customer_id", {"customer"},
                 False, "Customer"),
    "customer_country": ("co.country", "co.country", {"customer", "geo"},
                         False, "Customer country"),
    "customer_city": ("CONCAT(ci.city, ', ', co.country)", "ci.city",
                      {"customer", "geo"}, False, "Customer city"),
    "customer_active": ("CASE WHEN cu.active = 1 THEN 'Active' "
                        "ELSE 'Inactive' END", "cu.active", {"customer"},
                        False, "Customer active flag"),
    "customer_home_store": ("CONCAT('Store #', cu.store_id)", "cu.store_id",
                            {"customer"}, False,
                            "Customer's home store"),
    "month": ("DATE_FORMAT(p.payment_date, '%Y-%m')",
              "DATE_FORMAT(p.payment_date, '%Y-%m')", set(), False,
              "Payment month"),
    "weekday": ("DAYNAME(p.payment_date)", "WEEKDAY(p.payment_date)",
                set(), False, "Payment weekday"),
    "hour": ("LPAD(HOUR(p.payment_date), 2, '0')", "HOUR(p.payment_date)",
             set(), False, "Payment hour of day"),
}

DIMENSION_ALIASES = {
    "actors": "actor", "dien vien": "actor", "diễn viên": "actor",
    "categories": "category", "the loai": "category", "thể loại": "category",
    "films": "film", "movie": "film", "phim": "film",
    "country": "customer_country", "quoc gia": "customer_country",
    "quốc gia": "customer_country", "city": "customer_city",
    "thanh pho": "customer_city", "thành phố": "customer_city",
    "feature": "special_feature", "special_features": "special_feature",
    "duration": "rental_duration", "price": "rental_rate",
    "rate": "rental_rate", "employee": "staff", "nhan vien": "staff",
    "nhân viên": "staff", "customers": "customer", "khach hang": "customer",
    "khách hàng": "customer", "day_of_week": "weekday", "year": "release_year",
    "mpaa": "rating", "length_band": "length",
    "actor_pair": "actor_pair", "actor_pairs": "actor_pair",
    "cap dien vien": "actor_pair", "cặp diễn viên": "actor_pair",
}

SORT_KEYS = {
    "total_revenue", "rentals", "late_fee_revenue", "late_rate_pct",
    "avg_revenue_per_rental", "shared_revenue", "rental_revenue",
    "late_fee_contribution_pct", "films", "customers", "label",
}


def _dimension(value, required=True):
    if value in (None, ""):
        if required:
            raise ValueError("dimension is required.")
        return None
    key = str(value).strip().lower()
    key = DIMENSION_ALIASES.get(key, key)
    if key == "actor_pair":
        return key
    if key not in DIMENSIONS:
        raise ValueError(
            f"Unknown dimension '{value}'. Use one of: "
            + ", ".join(sorted(DIMENSIONS)) + ", actor_pair."
        )
    return key


def _clean_top_n(top_n, default=15):
    try:
        top_n = int(top_n)
    except (TypeError, ValueError):
        top_n = default
    return max(1, min(MAX_TOP_N, top_n))


def _filters(category=None, store_id=None, start_date=None, end_date=None,
             actor=None, film=None, rating=None, customer_country=None):
    """WHERE fragments (all parameterised) and the joins they need."""

    clauses, params, joins = [], [], set()

    category = normalize_category(category)
    store_id = normalize_store_id(store_id)
    start_date = normalize_date(start_date)
    end_date = normalize_date(end_date, is_end=True)

    if category:
        # Sub-query: never multiplies rows.
        clauses.append(
            "f.film_id IN (SELECT fc2.film_id FROM film_category fc2 "
            "JOIN category c2 ON c2.category_id = fc2.category_id "
            "WHERE c2.name = %s)"
        )
        params.append(category)
    if store_id is not None:
        clauses.append("i.store_id = %s")
        params.append(store_id)
    if start_date:
        clauses.append("p.payment_date >= %s")
        params.append(start_date)
    if end_date:
        clauses.append("p.payment_date < DATE_ADD(%s, INTERVAL 1 DAY)")
        params.append(end_date)
    if actor:
        clauses.append(
            "f.film_id IN (SELECT fa2.film_id FROM film_actor fa2 "
            "JOIN actor a2 ON a2.actor_id = fa2.actor_id "
            "WHERE CONCAT(a2.first_name, ' ', a2.last_name) LIKE %s)"
        )
        params.append(f"%{str(actor).strip()}%")
    if film:
        clauses.append("f.title LIKE %s")
        params.append(f"%{str(film).strip()}%")
    if rating:
        clauses.append("f.rating = %s")
        params.append(str(rating).strip().upper())
    if customer_country:
        joins |= {"customer", "geo"}
        clauses.append("co.country LIKE %s")
        params.append(f"%{str(customer_country).strip()}%")

    return clauses, params, joins, {
        "category": category, "store_id": store_id,
        "start_date": start_date, "end_date": end_date, "actor": actor,
        "film": film, "rating": rating,
        "customer_country": customer_country,
    }


def _run(query, params):
    conn = get_connection()
    try:
        with conn.cursor(dictionary=True) as cursor:
            cursor.execute(query, params)
            return cursor.fetchall()
    finally:
        conn.close()


def _metrics_sql(shared):
    shared_sql = (
        "SUM(p.amount / fac.n_actors) AS shared_revenue,"
        if shared else ""
    )
    return f"""
        COUNT(DISTINCT r.rental_id) AS rentals,
        SUM(p.amount) AS total_revenue,
        SUM({LATE_FEE_SQL}) AS late_fee_revenue,
        {shared_sql}
        SUM(r.return_date IS NOT NULL) AS completed_rentals,
        SUM(CASE WHEN r.return_date IS NOT NULL AND {LATE_CONDITION_SQL}
                 THEN 1 ELSE 0 END) AS late_rentals,
        COUNT(DISTINCT f.film_id) AS films,
        COUNT(DISTINCT p.customer_id) AS customers
    """


def _row(raw, total_revenue, additive):
    revenue = to_number(raw["total_revenue"])
    late_fee = to_number(raw["late_fee_revenue"])
    rentals = int(raw["rentals"] or 0)
    completed = int(raw["completed_rentals"] or 0)
    late = int(raw["late_rentals"] or 0)

    row = {
        "rentals": rentals,
        "total_revenue": revenue,
        "rental_revenue": round(revenue - late_fee, 2),
        "late_fee_revenue": late_fee,
        "late_fee_contribution_pct": pct(late_fee, revenue),
        "late_rentals": late,
        "late_rate_pct": pct(late, completed),
        "avg_revenue_per_rental": round(revenue / rentals, 2) if rentals else 0.0,
        "films": int(raw["films"] or 0),
        "customers": int(raw["customers"] or 0),
    }

    if "shared_revenue" in raw and raw["shared_revenue"] is not None:
        row["shared_revenue"] = to_number(raw["shared_revenue"])

    key = "revenue_share_pct" if additive else "share_of_total_revenue_pct"
    row[key] = pct(revenue, total_revenue)

    return row


def _overall_total(clauses, params, joins):
    join_sql = " ".join(_JOINS[j] for j in _JOIN_ORDER if j in joins)
    where = "WHERE " + " AND ".join(clauses) if clauses else ""
    rows = _run(
        f"""
        SELECT SUM(p.amount) AS total_revenue,
               SUM({LATE_FEE_SQL}) AS late_fee_revenue,
               COUNT(*) AS rentals
        FROM payment p
        JOIN rental r ON r.rental_id = p.rental_id
        JOIN inventory i ON i.inventory_id = r.inventory_id
        JOIN film f ON f.film_id = i.film_id
        {join_sql}
        {where}
        """,
        params,
    )
    raw = rows[0] if rows else {}
    return {
        "total_revenue": to_number(raw.get("total_revenue")),
        "late_fee_revenue": to_number(raw.get("late_fee_revenue")),
        "rentals": int(raw.get("rentals") or 0),
    }


def get_revenue_breakdown(
    dimension,
    dimension2=None,
    category=None,
    store_id=None,
    start_date=None,
    end_date=None,
    actor=None,
    film=None,
    rating=None,
    customer_country=None,
    sort_by="total_revenue",
    order="desc",
    top_n=15,
    min_rentals=None,
):
    """
    Revenue, late fees, rentals and late-return rate grouped by any
    relationship in the Sakila database (one or two dimensions).

    dimension / dimension2: see DIMENSIONS (category, film, actor, rating,
    language, release_year, rental_duration, rental_rate,
    replacement_cost, length, special_feature, store, staff, customer,
    customer_country, customer_city, customer_active,
    customer_home_store, month, weekday, hour) or "actor_pair".
    Filters: category, store_id, start_date, end_date (payment date),
    actor (name contains), film (title contains), rating,
    customer_country.
    """

    dim1 = _dimension(dimension)
    dim2 = _dimension(dimension2, required=False)

    if "actor_pair" in (dim1, dim2):
        if dim2 and dim1 != dim2:
            raise ValueError(
                "actor_pair cannot be combined with a second dimension; "
                "use get_actor_pair_revenue with filters instead."
            )
        return get_actor_pair_revenue(
            top_n=top_n, category=category, store_id=store_id,
            start_date=start_date, end_date=end_date, actor=actor,
            sort_by=sort_by,
        )

    if dim2 == dim1:
        dim2 = None

    sort_by = str(sort_by or "total_revenue").strip().lower()
    if sort_by not in SORT_KEYS:
        sort_by = "total_revenue"
    descending = str(order or "desc").strip().lower() != "asc"
    top_n = _clean_top_n(top_n)

    dims = [d for d in (dim1, dim2) if d]

    # When grouping BY actor, an actor filter selects those actors
    # (instead of "all actors in the films of that actor").
    actor_as_group = "actor" in dims and actor
    clauses, params, joins, filters_used = _filters(
        category, store_id, start_date, end_date,
        None if actor_as_group else actor, film, rating, customer_country,
    )
    if actor_as_group:
        clauses.append("CONCAT(a.first_name, ' ', a.last_name) LIKE %s")
        params.append(f"%{str(actor).strip()}%")
        filters_used["actor"] = actor
    for d in dims:
        joins |= DIMENSIONS[d][2]

    multi = any(DIMENSIONS[d][3] for d in dims)
    additive = not multi
    shared = "actor" in dims and len(dims) == 1

    join_sql = " ".join(_JOINS[j] for j in _JOIN_ORDER if j in joins)
    where = "WHERE " + " AND ".join(clauses) if clauses else ""

    select_labels = ", ".join(
        f"{DIMENSIONS[d][0]} AS dim{n}, {DIMENSIONS[d][1]} AS sort{n}"
        for n, d in enumerate(dims, start=1)
    )
    group_by = ", ".join(
        f"dim{n}, sort{n}" for n in range(1, len(dims) + 1)
    )

    query = f"""
        SELECT {select_labels},
               {_metrics_sql(shared)}
        FROM payment p
        JOIN rental r ON r.rental_id = p.rental_id
        JOIN inventory i ON i.inventory_id = r.inventory_id
        JOIN film f ON f.film_id = i.film_id
        {join_sql}
        {where}
        GROUP BY {group_by}
    """

    raw_rows = _run(query, params)

    base_clauses, base_params, base_joins, _ = _filters(
        category, store_id, start_date, end_date, actor, film, rating,
        customer_country,
    )
    overall = _overall_total(base_clauses, base_params, base_joins)

    rows = []
    for raw in raw_rows:
        row = {dim1: raw["dim1"]}
        if dim2:
            row[dim2] = raw["dim2"]
        row.update(_row(raw, overall["total_revenue"], additive))
        row["_sort"] = (raw.get("sort1"), raw.get("sort2"))
        rows.append(row)

    if min_rentals not in (None, ""):
        try:
            minimum = int(min_rentals)
            rows = [r for r in rows if r["rentals"] >= minimum]
        except (TypeError, ValueError):
            pass

    group_count = len(rows)
    attributed_total = round(sum(r["total_revenue"] for r in rows), 2)
    shared_total = (
        round(sum(r.get("shared_revenue", 0) for r in rows), 2)
        if shared else None
    )

    if sort_by == "label":
        rows.sort(key=lambda r: tuple(
            (x is None, x) for x in r["_sort"]
        ), reverse=descending)
    else:
        rows.sort(key=lambda r: r.get(sort_by, 0) or 0, reverse=descending)

    for r in rows:
        r.pop("_sort", None)

    result = {
        "dimension": dim1,
        "dimension2": dim2,
        "dimension_description": DIMENSIONS[dim1][4]
        + (f" x {DIMENSIONS[dim2][4]}" if dim2 else ""),
        "filters": {k: v for k, v in filters_used.items() if v not in (None, "")},
        "sort_by": sort_by,
        "order": "desc" if descending else "asc",
        "group_count": group_count,
        "rows_returned": min(top_n, group_count),
        "rows": rows[:top_n],
        "overall_total_revenue": overall["total_revenue"],
        "overall_late_fee_revenue": overall["late_fee_revenue"],
        "overall_rentals": overall["rentals"],
        "additive": additive,
        "sum_of_group_revenue": attributed_total,
        **(
            {"sum_of_shared_revenue": shared_total,
             "revenue_of_films_without_actors": round(
                 overall["total_revenue"] - shared_total, 2)}
            if shared and not actor_as_group else {}
        ),
        "attribution_note": (
            "Groups are additive: they sum to the overall total."
            if additive else
            "Multi-valued dimension: a film is counted fully for EACH "
            "actor / feature it has, so group revenues sum to more than "
            "the total. Use shared_revenue (actor revenue split equally "
            "between a film's actors) for an additive view."
        ),
        "definitions": {
            "total_revenue": "SUM(payment.amount)",
            "late_fee_revenue": "SUM(GREATEST(amount - film.rental_rate, 0))",
            "late_rate_pct": "late rentals / returned rentals",
        },
        "data_source": "Sakila MySQL database",
    }

    return result


def get_actor_pair_revenue(
    top_n=15,
    category=None,
    store_id=None,
    start_date=None,
    end_date=None,
    actor=None,
    min_shared_films=1,
    sort_by="total_revenue",
):
    """
    Revenue of the films two actors appear in TOGETHER (actor pairs /
    co-stars). Optional filters: category, store_id, start/end date
    (payment date), actor (only pairs that include this actor).
    """

    top_n = _clean_top_n(top_n)
    try:
        min_shared_films = max(1, int(min_shared_films))
    except (TypeError, ValueError):
        min_shared_films = 1

    sort_by = str(sort_by or "total_revenue").strip().lower()
    sort_sql = {
        "total_revenue": "total_revenue",
        "rentals": "rentals",
        "late_fee_revenue": "late_fee_revenue",
        "shared_films": "shared_films",
        "avg_revenue_per_film": "total_revenue / shared_films",
    }.get(sort_by, "total_revenue")

    clauses, params, _joins, filters_used = _filters(
        category, store_id, start_date, end_date,
    )
    where = "WHERE " + " AND ".join(clauses) if clauses else ""

    pair_clauses, pair_params = [], []
    if actor:
        pair_clauses.append(
            "(CONCAT(a1.first_name, ' ', a1.last_name) LIKE %s "
            "OR CONCAT(a2.first_name, ' ', a2.last_name) LIKE %s)"
        )
        pair_params += [f"%{str(actor).strip()}%"] * 2
        filters_used["actor"] = actor
    pair_where = "WHERE " + " AND ".join(pair_clauses) if pair_clauses else ""

    query = f"""
        SELECT
            a1.actor_id AS actor1_id,
            CONCAT(a1.first_name, ' ', a1.last_name) AS actor_1,
            a2.actor_id AS actor2_id,
            CONCAT(a2.first_name, ' ', a2.last_name) AS actor_2,
            COUNT(*) AS shared_films,
            SUM(fr.rentals) AS rentals,
            SUM(fr.total_revenue) AS total_revenue,
            SUM(fr.late_fee_revenue) AS late_fee_revenue,
            SUM(fr.completed) AS completed_rentals,
            SUM(fr.late_rentals) AS late_rentals,
            GROUP_CONCAT(fr.title ORDER BY fr.total_revenue DESC
                         SEPARATOR ' | ') AS films
        FROM film_actor fa1
        JOIN film_actor fa2
          ON fa2.film_id = fa1.film_id AND fa1.actor_id < fa2.actor_id
        JOIN (
            SELECT f.film_id, f.title,
                   COUNT(*) AS rentals,
                   SUM(p.amount) AS total_revenue,
                   SUM({LATE_FEE_SQL}) AS late_fee_revenue,
                   SUM(r.return_date IS NOT NULL) AS completed,
                   SUM(CASE WHEN r.return_date IS NOT NULL
                             AND {LATE_CONDITION_SQL} THEN 1 ELSE 0 END)
                       AS late_rentals
            FROM payment p
            JOIN rental r ON r.rental_id = p.rental_id
            JOIN inventory i ON i.inventory_id = r.inventory_id
            JOIN film f ON f.film_id = i.film_id
            {where}
            GROUP BY f.film_id, f.title
        ) fr ON fr.film_id = fa1.film_id
        JOIN actor a1 ON a1.actor_id = fa1.actor_id
        JOIN actor a2 ON a2.actor_id = fa2.actor_id
        {pair_where}
        GROUP BY a1.actor_id, actor_1, a2.actor_id, actor_2
        HAVING COUNT(*) >= %s
        ORDER BY {sort_sql} DESC, shared_films DESC
    """

    raw_rows = _run(query, params + pair_params + [min_shared_films])

    rows = []
    for raw in raw_rows:
        revenue = to_number(raw["total_revenue"])
        late_fee = to_number(raw["late_fee_revenue"])
        completed = int(raw["completed_rentals"] or 0)
        late = int(raw["late_rentals"] or 0)
        shared = int(raw["shared_films"] or 0)
        titles = [t for t in str(raw["films"] or "").split(" | ") if t]
        rows.append({
            "actor_pair": f"{raw['actor_1']} & {raw['actor_2']}",
            "actor_1": raw["actor_1"],
            "actor_2": raw["actor_2"],
            "shared_films": shared,
            "rentals": int(raw["rentals"] or 0),
            "total_revenue": revenue,
            "late_fee_revenue": late_fee,
            "late_rate_pct": pct(late, completed),
            "avg_revenue_per_shared_film": round(revenue / shared, 2)
            if shared else 0.0,
            "top_films": titles[:5],
        })

    return {
        "dimension": "actor_pair",
        "filters": {k: v for k, v in filters_used.items() if v not in (None, "")},
        "min_shared_films": min_shared_films,
        "sort_by": sort_by,
        "pair_count": len(rows),
        "rows_returned": min(top_n, len(rows)),
        "rows": rows[:top_n],
        "additive": False,
        "attribution_note": (
            "Revenue of a pair = revenue of the films BOTH actors appear "
            "in (counted fully for every pair in the film), so pair "
            "revenues are not additive."
        ),
        "data_source": "Sakila MySQL database",
    }
