"""
Shared input normalisation for the ML prediction tools.

Why: the LLM frequently passed customer_late_rate as a percentage
(51.2 instead of 0.512) or a category in lower case / Vietnamese.
The logistic model then returned a late probability of 100% for every
scenario, which propagated into the simulation and optimisation tools.
"""

import os
from functools import lru_cache

import joblib

from tools.data.business_metrics import normalize_category


PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)

TRAINED_DURATION_RANGE = (3, 7)
TRAINED_RATES = (0.99, 2.99, 4.99)


def model_path(file_name):
    """Absolute path to ml/models/<file_name> (independent of CWD)."""

    return os.path.join(PROJECT_ROOT, "ml", "models", file_name)


@lru_cache(maxsize=8)
def load_model(file_name):
    path = model_path(file_name)

    if not os.path.exists(path):
        raise FileNotFoundError(
            f"Model not found: {path}. Run the training scripts in ml/ "
            "or commit ml/models/*.pkl to the repository."
        )

    return joblib.load(path)


def normalize_ml_inputs(
    customer_late_rate,
    category,
    rental_duration,
    rental_rate,
):
    """
    Returns (clean_inputs_dict, warnings_list).
    """

    warnings = []

    # ---------------- customer_late_rate ----------------
    try:
        rate = float(str(customer_late_rate).replace("%", "").strip())
    except (TypeError, ValueError):
        raise ValueError(
            "customer_late_rate must be a number between 0 and 1 "
            "(e.g. 0.512)."
        )

    if 1.0 < rate <= 100.0:
        warnings.append(
            f"customer_late_rate={rate} looked like a percentage and "
            f"was converted to {rate / 100:.4f}."
        )
        rate = rate / 100.0

    if rate < 0 or rate > 1:
        raise ValueError(
            "customer_late_rate must be between 0 and 1 (e.g. 0.512)."
        )

    # ---------------- category ----------------
    clean_category = normalize_category(category, required=True)

    # ---------------- rental_duration ----------------
    try:
        duration = float(rental_duration)
    except (TypeError, ValueError):
        raise ValueError("rental_duration must be a number of days.")

    if duration <= 0:
        raise ValueError("rental_duration must be greater than 0.")

    low, high = TRAINED_DURATION_RANGE
    if duration < low or duration > high:
        warnings.append(
            f"rental_duration={duration:g} is outside the trained range "
            f"{low}-{high} days; prediction is an extrapolation."
        )

    # ---------------- rental_rate ----------------
    try:
        rate_value = float(str(rental_rate).replace("$", "").strip())
    except (TypeError, ValueError):
        raise ValueError("rental_rate must be a number (e.g. 2.99).")

    if rate_value <= 0:
        raise ValueError("rental_rate must be greater than 0.")

    if rate_value < min(TRAINED_RATES) or rate_value > max(TRAINED_RATES):
        warnings.append(
            f"rental_rate={rate_value} is outside the observed Sakila "
            "range 0.99-4.99; prediction is an extrapolation."
        )

    return (
        {
            "customer_late_rate": rate,
            "category": clean_category,
            "rental_duration": duration,
            "rental_rate": rate_value,
        },
        warnings,
    )
