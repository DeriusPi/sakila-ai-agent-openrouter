import pandas as pd

from tools.ml._inputs import load_model, normalize_ml_inputs


MODEL_FILE = "late_probability.pkl"


def predict_late_probability(
    customer_late_rate,
    category,
    rental_duration,
    rental_rate
):
    """
    Predict probability that a rental will be returned late.

    customer_late_rate must be a ratio 0-1 (0.512). Percentages such as
    51.2 are converted automatically; category names are normalised
    ('sports' -> 'Sports').
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

    probability = float(model.predict_proba(input_data)[0][1])

    if probability >= 0.70:
        risk_level = "HIGH"
    elif probability >= 0.40:
        risk_level = "MEDIUM"
    else:
        risk_level = "LOW"

    result = {
        "late_probability": round(probability, 4),
        "late_probability_pct": round(probability * 100, 2),
        "risk_level": risk_level,
        "inputs_used": inputs,
    }

    if warnings:
        result["warnings"] = warnings

    return result
