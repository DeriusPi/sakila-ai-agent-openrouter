from db import get_connection


def get_store_data():
    """
    Retrieve store-level rental and revenue information.
    """

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    query = """
        SELECT
            s.store_id,
            COUNT(r.rental_id) AS total_rentals,
            COALESCE(SUM(p.amount), 0) AS total_revenue
        FROM store s
        LEFT JOIN inventory i
            ON s.store_id = i.store_id
        LEFT JOIN rental r
            ON i.inventory_id = r.inventory_id
        LEFT JOIN payment p
            ON r.rental_id = p.rental_id
        GROUP BY s.store_id
        ORDER BY s.store_id
    """

    cursor.execute(query)
    rows = cursor.fetchall()

    cursor.close()
    conn.close()

    return rows
