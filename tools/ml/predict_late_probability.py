import pandas as pd

from tools.ml._inputs import (
    ALL_CATEGORIES,
    category_weights,
    load_model,
    normalize_ml_inputs,
)


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

    category="All" (or None) predicts for the whole catalogue: the
    probability is averaged over the 16 categories, weighted by each
    category's share of completed rentals.
    """

    inputs, warnings = normalize_ml_inputs(
        customer_late_rate,
        category,
        rental_duration,
        rental_rate,
    )

    model = load_model(MODEL_FILE)

    if inputs["category"] == ALL_CATEGORIES:
        weights = category_weights()
        names = list(weights)
    else:
        weights = {inputs["category"]: 1.0}
        names = [inputs["category"]]

    input_data = pd.DataFrame([
        {
            "rental_duration": inputs["rental_duration"],
            "rental_rate": inputs["rental_rate"],
            "category": name,
            "customer_late_rate": inputs["customer_late_rate"],
        }
        for name in names
    ])

    probabilities = model.predict_proba(input_data)[:, 1]
    total_weight = sum(weights[name] for name in names)
    probability = float(
        sum(float(p) * weights[name] for p, name in zip(probabilities, names))
        / total_weight
    )

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
