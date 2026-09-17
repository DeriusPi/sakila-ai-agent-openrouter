from db import get_connection


def get_rental_context(customer_id, film_id):
    """
    Retrieve all data required for late-return prediction
    and policy simulation.

    Inputs:
        customer_id : customer identifier
        film_id     : film identifier

    Returns:
        {
            customer_id,
            film_id,
            category,
            rental_duration,
            rental_rate,
            customer_late_rate
        }
    """

    conn = get_connection()

    try:
        with conn.cursor(dictionary=True) as cursor:

            # -----------------------------------------
            # 1. Get film information
            # -----------------------------------------

            film_query = """
                SELECT
                    f.film_id,
                    f.rental_duration,
                    f.rental_rate,
                    c.name AS category
                FROM film f
                JOIN film_category fc
                    ON f.film_id = fc.film_id
                JOIN category c
                    ON fc.category_id = c.category_id
                WHERE f.film_id = %s
            """

            cursor.execute(
                film_query,
                (film_id,)
            )

            film = cursor.fetchone()

            if film is None:
                raise ValueError(
                    f"Film {film_id} not found."
                )

            # -----------------------------------------
            # 2. Calculate customer's historical
            #    late-return rate
            # -----------------------------------------

            customer_query = """
                SELECT
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
                WHERE r.customer_id = %s
                  AND r.return_date IS NOT NULL
            """

            cursor.execute(
                customer_query,
                (customer_id,)
            )

            customer = cursor.fetchone()

            if customer is None:
                raise ValueError(
                    f"Customer {customer_id} not found."
                )

            total_rentals = int(
                customer["total_rentals"] or 0
            )

            late_rentals = int(
                customer["late_rentals"] or 0
            )

            if total_rentals == 0:
                customer_late_rate = 0.0
            else:
                customer_late_rate = (
                    late_rentals / total_rentals
                )

            # -----------------------------------------
            # 3. Return unified context
            # -----------------------------------------

            return {
                "customer_id": int(customer_id),
                "film_id": int(film_id),
                "category": film["category"],
                "rental_duration": int(
                    film["rental_duration"]
                ),
                "rental_rate": float(
                    film["rental_rate"]
                ),
                "customer_late_rate": round(
                    customer_late_rate,
                    4
                ),
                "total_customer_rentals": total_rentals,
                "customer_late_rentals": late_rentals
            }

    finally:
        conn.close()


if __name__ == "__main__":

    result = get_rental_context(
        customer_id=321,
        film_id=19
    )

    print("\n==============================")
    print("RENTAL CONTEXT")
    print("==============================")

    for key, value in result.items():
        print(f"{key}: {value}")

