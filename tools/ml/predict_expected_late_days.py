import pandas as pd

from tools.ml._inputs import (
    ALL_CATEGORIES,
    category_weights,
    load_model,
    normalize_ml_inputs,
)


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

    category="All" (or None): whole catalogue. Because the value is
    conditional on the rental being late, categories are weighted by
    (share of rentals x late probability).
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

    # Prevent impossible negative values
    days = [max(float(d), 0.0) for d in model.predict(input_data)]

    if len(names) == 1:
        predicted_days = days[0]
    else:
        # E[days | late] over the mix = sum(w * p * d) / sum(w * p)
        late_model = load_model("late_probability.pkl")
        probabilities = late_model.predict_proba(input_data)[:, 1]
        mix = [
            weights[name] * float(p)
            for name, p in zip(names, probabilities)
        ]
        predicted_days = (
            sum(m * d for m, d in zip(mix, days)) / sum(mix)
            if sum(mix) else sum(days) / len(days)
        )

    result = {
        "expected_late_days": round(predicted_days, 4),
        "definition": "Expected late days given that the rental is late.",
        "inputs_used": inputs,
    }

    if warnings:
        result["warnings"] = warnings

    return result
