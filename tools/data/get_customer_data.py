from db import get_connection


def get_customer_data():
    """
    Retrieve customer rental behavior.
    """

    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    query = """
        SELECT
            r.customer_id,
            COUNT(*) AS total_rentals,
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
        FROM rental r
        JOIN inventory i
            ON r.inventory_id = i.inventory_id
        JOIN film f
            ON i.film_id = f.film_id
        WHERE r.return_date IS NOT NULL
        GROUP BY r.customer_id
    """

    cursor.execute(query)
    rows = cursor.fetchall()

    cursor.close()
    conn.close()

    return rows
