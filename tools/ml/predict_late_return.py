import os
import pickle
import pandas as pd

from tools.data.get_rental_context import get_rental_context


MODEL_PATH = "ml/models/late_return_model.pkl"


def predict_late_return(customer_id, film_id):
    """
    Predict probability that a rental will be returned late.

    All rental and customer features are retrieved dynamically
    from the Sakila database using customer_id and film_id.

    Parameters
    ----------
    customer_id : int
        Customer identifier.

    film_id : int
        Film identifier.

    Returns
    -------
    dict
        Prediction result including database-derived features.
    """

    # -----------------------------------------
    # 1. Check model
    # -----------------------------------------

    if not os.path.exists(MODEL_PATH):
        raise FileNotFoundError(
            f"Model not found: {MODEL_PATH}"
        )

    # -----------------------------------------
    # 2. Retrieve data from database
    # -----------------------------------------

    context = get_rental_context(
        customer_id=customer_id,
        film_id=film_id
    )

    # -----------------------------------------
    # 3. Load trained model
    # -----------------------------------------

    with open(MODEL_PATH, "rb") as f:
        model = pickle.load(f)

    # -----------------------------------------
    # 4. Build ML input
    # -----------------------------------------

    input_data = pd.DataFrame([
        {
            "rental_duration": context["rental_duration"],
            "rental_rate": context["rental_rate"],
            "category": context["category"],
            "customer_late_rate": context["customer_late_rate"]
        }
    ])

    # -----------------------------------------
    # 5. Predict probability
    # -----------------------------------------

    probability = model.predict_proba(
        input_data
    )[0][1]

    probability = float(probability)

    # -----------------------------------------
    # 6. Risk classification
    # -----------------------------------------

    if probability >= 0.70:
        risk_level = "HIGH"
    elif probability >= 0.40:
        risk_level = "MEDIUM"
    else:
        risk_level = "LOW"

    # -----------------------------------------
    # 7. Return result
    # -----------------------------------------

    return {
        "customer_id": context["customer_id"],
        "film_id": context["film_id"],
        "category": context["category"],
        "rental_duration": context["rental_duration"],
        "rental_rate": context["rental_rate"],
        "customer_late_rate": context["customer_late_rate"],
        "total_customer_rentals": context[
            "total_customer_rentals"
        ],
        "customer_late_rentals": context[
            "customer_late_rentals"
        ],
        "late_probability": round(
            probability,
            4
        ),
        "late_probability_pct": round(
            probability * 100,
            2
        ),
        "risk_level": risk_level
    }


