import joblib
import os
import pandas as pd


MODEL_PATH = "ml/models/late_probability.pkl"


def predict_late_probability(
    customer_late_rate,
    category,
    rental_duration,
    rental_rate
):
    """
    Predict probability that a rental will be returned late.
    """

    if not os.path.exists(MODEL_PATH):
        raise FileNotFoundError(
            f"Model not found: {MODEL_PATH}"
        )

    model = joblib.load(MODEL_PATH)

    input_data = pd.DataFrame([
        {
            "rental_duration": float(rental_duration),
            "rental_rate": float(rental_rate),
            "category": category,
            "customer_late_rate": float(
                customer_late_rate
            )
        }
    ])

    probability = model.predict_proba(
        input_data
    )[0][1]

    probability = float(probability)

    if probability >= 0.70:
        risk_level = "HIGH"
    elif probability >= 0.40:
        risk_level = "MEDIUM"
    else:
        risk_level = "LOW"

    return {
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


