from db import get_connection


def get_revenue_data():
    """
    Retrieve aggregated revenue data only.
    Do not return raw payment rows.
    """

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    query = """
        SELECT
            p.payment_id,
            p.rental_id,
            p.customer_id,
            p.amount,
            f.rental_rate,
            f.rental_duration,
            f.film_id,
            c.name AS category
        FROM payment p
        JOIN rental r
            ON p.rental_id = r.rental_id
        JOIN inventory i
            ON r.inventory_id = i.inventory_id
        JOIN film f
            ON i.film_id = f.film_id
        JOIN film_category fc
            ON f.film_id = fc.film_id
        JOIN category c
            ON fc.category_id = c.category_id
    """

    cursor.execute(query)

    rows = cursor.fetchall()

    cursor.close()
    conn.close()

    return rows
