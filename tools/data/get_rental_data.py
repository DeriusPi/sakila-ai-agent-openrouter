from db import get_connection


def get_rental_data():
    """
    Retrieve rental behavior data.
    """

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    query = """
        SELECT
            r.rental_id,
            r.rental_date,
            r.return_date,
            r.inventory_id,
            r.customer_id,
            i.film_id,
            f.rental_duration,
            f.rental_rate,
            c.name AS category
        FROM rental r
        JOIN inventory i
            ON r.inventory_id = i.inventory_id
        JOIN film f
            ON i.film_id = f.film_id
        JOIN film_category fc
            ON f.film_id = fc.film_id
        JOIN category c
            ON fc.category_id = c.category_id
        WHERE r.return_date IS NOT NULL
    """

    cursor.execute(query)
    rows = cursor.fetchall()

    cursor.close()
    conn.close()

    return rows
