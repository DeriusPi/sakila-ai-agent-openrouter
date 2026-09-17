import joblib
import os
import pandas as pd


MODEL_PATH = "ml/models/late_days.pkl"


def predict_expected_late_days(
    customer_late_rate,
    category,
    rental_duration,
    rental_rate
):
    """
    Predict expected number of late days,
    conditional on the rental being late.
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

    predicted_days = model.predict(
        input_data
    )[0]

    # Prevent impossible negative values
    predicted_days = max(
        float(predicted_days),
        0.0
    )

    return {
        "expected_late_days": round(
            predicted_days,
            4
        )
    }


