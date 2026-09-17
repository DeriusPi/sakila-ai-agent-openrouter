# tools/recommendation/late_fee_recommendation.py

from tools.optimization.optimize_late_fee_policy import (
    optimize_late_fee_policy
)


def recommend_late_fee(
    customer_id,
    film_id,
    category,
    rental_duration,
    rental_rate
):
    """
    Generate a concise late-fee recommendation
    from the optimization result.

    This function does not perform a new simulation.
    It only converts the optimization output into
    a simpler recommendation structure.
    """

    result = optimize_late_fee_policy(
        customer_id=customer_id,
        film_id=film_id,
        category=category,
        rental_duration=rental_duration,
        rental_rate=rental_rate
    )

    prediction = result["prediction"]
    recommended = result["recommended_policy"]

    return {
        "customer_id": customer_id,
        "film_id": film_id,
        "category": category,

        "risk": {
            "late_probability": prediction[
                "late_probability"
            ],
            "late_probability_pct": prediction[
                "late_probability_pct"
            ],
            "risk_level": prediction[
                "risk_level"
            ]
        },

        "recommendation": {
            "late_fee_per_day": recommended[
                "late_fee_per_day"
            ],
            "expected_total_revenue": recommended[
                "expected_total_revenue"
            ],
            "revenue_change": recommended[
                "revenue_change"
            ],
            "revenue_change_pct": recommended[
                "revenue_change_pct"
            ],
            "expected_rentals": recommended[
                "expected_rentals"
            ],
            "rental_change_pct": recommended[
                "rental_change_pct"
            ]
        },

        "policy": recommended["policy"],

        "optimization": {
            "candidate_fee_count": result[
                "candidate_fee_count"
            ]
        }
    }
