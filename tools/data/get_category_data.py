from db import get_connection


def get_category_data():
    """
    Retrieve category-level rental and late-return information.
    """

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    query = """
        SELECT
            c.category_id,
            c.name AS category,
            COUNT(r.rental_id) AS total_rentals,
            SUM(
                CASE
                    WHEN TIMESTAMPDIFF(
                        DAY,
                        r.rental_date,
                        r.return_date
                    ) > f.rental_duration
                    THEN 1
                    ELSE 0
                END
            ) AS late_rentals
        FROM category c
        JOIN film_category fc
            ON c.category_id = fc.category_id
        JOIN film f
            ON fc.film_id = f.film_id
        JOIN inventory i
            ON f.film_id = i.film_id
        JOIN rental r
            ON i.inventory_id = r.inventory_id
        WHERE r.return_date IS NOT NULL
        GROUP BY
            c.category_id,
            c.name
        ORDER BY total_rentals DESC
    """

    cursor.execute(query)
    rows = cursor.fetchall()

    cursor.close()
    conn.close()

    return rows
