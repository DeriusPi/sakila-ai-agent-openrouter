from db import get_connection


def get_late_fee_data():
    """
    Get rental records and calculate late-return information.

    actual_rental_days:
        Actual rental duration in days, including fractional days.

    late_days:
        Number of days beyond the allowed rental duration.

    is_late:
        True if actual rental duration exceeds the allowed duration.
    """

    conn = get_connection()

    query = """
        SELECT
            r.rental_id,
            r.customer_id,
            r.inventory_id,

            i.film_id,

            fc.category_id,
            cat.name AS category,

            r.rental_date,
            r.return_date,

            f.rental_duration,
            f.rental_rate,

            p.amount AS payment_amount,

            (
                TIMESTAMPDIFF(
                    SECOND,
                    r.rental_date,
                    r.return_date
                ) / 86400.0
            ) AS actual_rental_days,

            GREATEST(
                (
                    TIMESTAMPDIFF(
                        SECOND,
                        r.rental_date,
                        r.return_date
                    ) / 86400.0
                ) - f.rental_duration,
                0
            ) AS late_days

        FROM rental r

        JOIN inventory i
            ON r.inventory_id = i.inventory_id

        JOIN film f
            ON i.film_id = f.film_id

        JOIN film_category fc
            ON f.film_id = fc.film_id

        JOIN category cat
            ON fc.category_id = cat.category_id

        LEFT JOIN payment p
            ON r.rental_id = p.rental_id

        WHERE r.return_date IS NOT NULL

        ORDER BY r.rental_id;
    """

    try:
        with conn.cursor(dictionary=True) as cursor:
            cursor.execute(query)
            rows = cursor.fetchall()

        results = []

        for row in rows:

            actual_days = float(row["actual_rental_days"])
            late_days = float(row["late_days"])

            results.append({
                "rental_id": row["rental_id"],
                "customer_id": row["customer_id"],
                "inventory_id": row["inventory_id"],
                "film_id": row["film_id"],
                "category_id": row["category_id"],
                "category": row["category"],

                "rental_date": row["rental_date"],
                "return_date": row["return_date"],

                "rental_duration": row["rental_duration"],
                "rental_rate": float(row["rental_rate"]),

                "payment_amount": (
                    float(row["payment_amount"])
                    if row["payment_amount"] is not None
                    else 0.0
                ),

                "actual_rental_days": round(actual_days, 4),
                "late_days": round(late_days, 4),
                "is_late": actual_days > row["rental_duration"]
            })

        return results

    finally:
        conn.close()
