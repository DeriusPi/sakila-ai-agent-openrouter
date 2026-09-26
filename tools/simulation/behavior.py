"""
Behavioural response of customers to the late-fee policy, and the
policy evaluation formula (net value).

WHY: the ML models only know category, rental duration, rental rate and
the customer's history - they have no "late fee" input, because in Sakila
the late fee is practically constant (about $1/day). The previous
simulation therefore assumed that a higher fee does NOT change how often
or how long customers return late, which is not realistic: a higher fee
should deter late returns.

Because Sakila has no variation in the fee, these responses cannot be
estimated from the data. They are transparent, adjustable assumptions
(constant-elasticity model), applied on top of the ML predictions that
are made at the current fee:

    f  = proposed late fee per day,  f0 = current fee (DB-derived median)
    D  = proposed rental duration,   D0 = current rental duration
    p0 = ML late probability,        d0 = ML expected late days (if late)

    Late probability   p(f) = min(0.99, p0 * (f0 / f) ^ e_p)
    Late days          d(f) = d0 * (f0 / f) ^ e_d
    Rental volume      N    = N0 * (f0 / f) ^ e_n * (D / D0) ^ e_D

    Rental revenue     = N * rental_rate
    Late-fee revenue   = N * p(f) * d(f) * f
    Total revenue      = rental revenue + late-fee revenue

    Opportunity cost   = N * p(f) * d(f) * c
        c = revenue a copy would earn per day if it were back on the
            shelf = inventory utilisation * AVG(rental_rate / duration),
            both measured in the Sakila database.

    NET POLICY VALUE   = total revenue - opportunity cost of late days

The recommended policy is the feasible scenario with the highest net
policy value.
"""

import time


# Default elasticities (simulation assumptions, adjustable in the UI).
DEFAULT_BEHAVIOR = {
    # +10% fee -> about -3% late returns
    "late_fee_elasticity": 0.30,
    # +10% fee -> late customers return about 2% sooner
    "late_days_elasticity": 0.20,
    # +10% fee -> about -1% rentals (customers avoid strict stores)
    "demand_fee_elasticity": 0.10,
    # -10% rental days -> about -2% rentals (shorter rentals less attractive)
    "demand_duration_elasticity": 0.20,
}

BEHAVIOR_DESCRIPTIONS = {
    "late_fee_elasticity": "Độ nhạy của xác suất trả trễ theo phí trễ",
    "late_days_elasticity": "Độ nhạy của số ngày trễ theo phí trễ",
    "demand_fee_elasticity": "Độ nhạy của lượng thuê theo phí trễ",
    "demand_duration_elasticity": "Độ nhạy của lượng thuê theo số ngày thuê",
}

MAX_LATE_PROBABILITY = 0.99

_COST_CACHE = {"value": None, "loaded_at": 0.0}
_COST_TTL_SECONDS = 600


def resolve_behavior(**overrides):
    """Default elasticities, overridden by any non-None value given."""

    params = dict(DEFAULT_BEHAVIOR)

    for key, value in overrides.items():
        if key in params and value is not None:
            try:
                value = float(value)
            except (TypeError, ValueError):
                raise ValueError(f"{key} must be a number.")
            if value < 0 or value > 3:
                raise ValueError(f"{key} must be between 0 and 3.")
            params[key] = value

    return params


def apply_behavior(
    late_probability,
    late_days,
    fee_per_day,
    current_fee_per_day,
    rental_duration,
    reference_duration,
    params,
):
    """
    Adjust the ML predictions (made at the current fee) for the proposed
    fee and duration. Returns p, d and the demand factor.
    """

    fee_ratio = float(current_fee_per_day) / float(fee_per_day)

    p = min(
        MAX_LATE_PROBABILITY,
        float(late_probability) * fee_ratio ** params["late_fee_elasticity"],
    )
    d = float(late_days) * fee_ratio ** params["late_days_elasticity"]

    demand = fee_ratio ** params["demand_fee_elasticity"]

    if reference_duration and float(reference_duration) > 0:
        demand *= (
            float(rental_duration) / float(reference_duration)
        ) ** params["demand_duration_elasticity"]

    return {
        "late_probability": p,
        "expected_late_days": d,
        "demand_factor": demand,
    }


def late_day_opportunity_cost():
    """
    c = inventory utilisation * average revenue per rental day,
    measured in the Sakila database (cached 10 minutes).

    utilisation = total rented copy-days /
                  (inventory copies * days between first rental and
                   last return)
    """

    now = time.time()

    if (
        _COST_CACHE["value"] is not None
        and now - _COST_CACHE["loaded_at"] < _COST_TTL_SECONDS
    ):
        return _COST_CACHE["value"]

    value = {
        "cost_per_late_day": 0.11,
        "utilization": 0.17,
        "revenue_per_rental_day": 0.65,
        "source": "fallback (database not reachable)",
    }

    try:
        from db import get_connection

        conn = get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT
                        SUM(TIMESTAMPDIFF(SECOND, r.rental_date,
                                          r.return_date)) / 86400,
                        TIMESTAMPDIFF(SECOND, MIN(r.rental_date),
                                      MAX(r.return_date)) / 86400,
                        AVG(f.rental_rate / f.rental_duration),
                        (SELECT COUNT(*) FROM inventory)
                    FROM rental r
                    JOIN inventory i ON r.inventory_id = i.inventory_id
                    JOIN film f ON i.film_id = f.film_id
                    WHERE r.return_date IS NOT NULL
                    """
                )
                rented_days, window_days, per_day, copies = cursor.fetchone()
        finally:
            conn.close()

        rented_days = float(rented_days or 0)
        window_days = float(window_days or 0)
        per_day = float(per_day or 0)
        copies = float(copies or 0)

        if rented_days > 0 and window_days > 0 and copies > 0:
            utilization = min(1.0, rented_days / (copies * window_days))
            value = {
                "cost_per_late_day": round(utilization * per_day, 4),
                "utilization": round(utilization, 4),
                "revenue_per_rental_day": round(per_day, 4),
                "source": "Sakila database",
            }
    except Exception:  # noqa: BLE001
        pass

    _COST_CACHE["value"] = value
    _COST_CACHE["loaded_at"] = now

    return value


def formula_text():
    return (
        "p(f) = p0·(f0/f)^e_p ; d(f) = d0·(f0/f)^e_d ; "
        "N = N0·(f0/f)^e_n·(D/D0)^e_D ; "
        "Net value = N·rate + N·p·d·f − N·p·d·c"
    )
