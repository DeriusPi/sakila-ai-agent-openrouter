import pandas as pd

from tools.ml._inputs import load_model, normalize_ml_inputs


MODEL_FILE = "late_days.pkl"


def predict_expected_late_days(
    customer_late_rate,
    category,
    rental_duration,
    rental_rate
):
    """
    Predict expected number of late days,
    conditional on the rental being late.

    customer_late_rate must be a ratio 0-1 (0.512). Percentages such as
    51.2 are converted automatically; category names are normalised.
    """

    inputs, warnings = normalize_ml_inputs(
        customer_late_rate,
        category,
        rental_duration,
        rental_rate,
    )

    model = load_model(MODEL_FILE)

    input_data = pd.DataFrame([
        {
            "rental_duration": inputs["rental_duration"],
            "rental_rate": inputs["rental_rate"],
            "category": inputs["category"],
            "customer_late_rate": inputs["customer_late_rate"],
        }
    ])

    # Prevent impossible negative values
    predicted_days = max(float(model.predict(input_data)[0]), 0.0)

    result = {
        "expected_late_days": round(predicted_days, 4),
        "definition": "Expected late days given that the rental is late.",
        "inputs_used": inputs,
    }

    if warnings:
        result["warnings"] = warnings

    return result
