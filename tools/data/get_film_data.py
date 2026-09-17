from db import get_connection


def get_film_data():
    """
    Retrieve film-level rental information.
    """

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    query = """
        SELECT
            f.film_id,
            f.title,
            f.rental_duration,
            f.rental_rate,
            c.name AS category
        FROM film f
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
