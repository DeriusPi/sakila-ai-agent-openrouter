from db import get_connection


def analyze_average_rental_rate_by_category():
    """
    Calculate average rental rate for all film categories
    directly from the Sakila MySQL database.
    """

    conn = get_connection()
    cursor = conn.cursor()

    query = """
        SELECT
            c.category_id,
            c.name AS category,
            ROUND(AVG(f.rental_rate), 2) AS average_rental_rate,
            COUNT(f.film_id) AS film_count
        FROM category c
        LEFT JOIN film_category fc
            ON c.category_id = fc.category_id
        LEFT JOIN film f
            ON fc.film_id = f.film_id
        GROUP BY
            c.category_id,
            c.name
        ORDER BY
            c.name;
    """

    try:
        cursor.execute(query)
        rows = cursor.fetchall()

        categories = []

        for row in rows:
            categories.append({
                "category_id": row[0],
                "category": row[1],
                "average_rental_rate": (
                    round(float(row[2]), 2)
                    if row[2] is not None
                    else None
                ),
                "film_count": int(row[3])
            })

        return {
            "total_categories": len(categories),
            "categories": categories,
            "data_source": "Sakila MySQL database",
            "method": (
                "AVG(film.rental_rate) grouped by film category "
                "directly in MySQL."
            )
        }

    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    result = analyze_average_rental_rate_by_category()

    print("=" * 70)
    print("AVERAGE RENTAL RATE BY CATEGORY")
    print("=" * 70)

    print("Total categories:", result["total_categories"])

    for row in result["categories"]:
        print(
            f"{row['category']:<15} "
            f"${row['average_rental_rate']:.2f} "
            f"({row['film_count']} films)"
        )
