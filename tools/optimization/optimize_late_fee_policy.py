# tools/optimization/optimize_late_fee_policy.py

from collections import Counter

from tools.ml.predict_late_return import predict_late_return
from tools.data.get_late_fee_data import get_late_fee_data
from tools.optimization.derive_fee_constraint import derive_fee_constraint
from tools.simulation.simulate_fee_policy import simulate_fee_policy


def get_late_days_distribution(category=None):
    data = get_late_fee_data()

    if category:
        data = [
            row for row in data
            if row["category"] == category
        ]

    if not data:
        return {}

    late_days = [int(row["late_days"]) for row in data]

    counts = Counter(late_days)
    total = len(late_days)

    return {
        days: count / total
        for days, count in sorted(counts.items())
    }


def generate_candidate_fees(
    lower_bound,
    upper_bound,
    benchmark,
    step=0.01
):
    if upper_bound < lower_bound:
        return [round(lower_bound, 2)]

    fees = []
    current = lower_bound

    while current <= upper_bound + 0.000001:
        fees.append(round(current, 2))
        current += step

    fees.append(round(lower_bound, 2))
    fees.append(round(benchmark, 2))
    fees.append(round(upper_bound, 2))

    return sorted(set(fees))


def optimize_late_fee_policy(
    customer_id,
    film_id,
    category,
    rental_duration,
    rental_rate,
    current_late_fee=None
):

    # STEP 1 — ML prediction

    prediction = predict_late_return(
        customer_id=customer_id,
        film_id=film_id
    )

    late_probability = float(
        prediction["late_probability"]
    )

    # STEP 2 — Historical late-day distribution

    distribution = get_late_days_distribution(
        category=category
    )

    # STEP 3 — Data-derived fee constraint

    fee_constraint = derive_fee_constraint()

    lower_bound = float(
        fee_constraint["lower_bound"]
    )

    upper_bound = float(
        fee_constraint["upper_bound"]
    )

    benchmark = float(
        fee_constraint["benchmark"]
    )

    actual_current_fee = float(
        fee_constraint["current_fee_per_day"]
    )

    if current_late_fee is not None:
        actual_current_fee = float(
            current_late_fee
        )

    # STEP 4 — Generate candidate fees

    candidate_fees = generate_candidate_fees(
        lower_bound=lower_bound,
        upper_bound=upper_bound,
        benchmark=benchmark
    )

    # STEP 5 — Simulate each fee

    results = []

    customer_late_rate = float(
        prediction.get(
            "customer_late_rate",
            late_probability
        )
    )

    for fee in candidate_fees:

        simulation = simulate_fee_policy(
            customer_late_rate=customer_late_rate,
            category=category,
            rental_duration=rental_duration,
            rental_rate=rental_rate,
            fee_per_day=fee
        )

        if abs(fee - actual_current_fee) < 0.005:
            policy_name = "Current fee"

        elif abs(fee - benchmark) < 0.005:
            policy_name = "Data-derived benchmark"

        elif abs(fee - upper_bound) < 0.005:
            policy_name = "Upper constraint"

        elif abs(fee - lower_bound) < 0.005:
            policy_name = "Lower constraint"

        else:
            policy_name = "Candidate fee"

        results.append({
            "policy": policy_name,
            "late_fee_per_day": round(fee, 2),
            "late_probability": simulation["late_probability"],
            "demand_factor": simulation["demand_factor"],
            "expected_rentals": simulation["expected_rentals"],
            "rental_change_pct": simulation["rental_change_pct"],
            "expected_rental_revenue": simulation[
                "expected_rental_revenue"
            ],
            "expected_late_fee_revenue": simulation[
                "expected_late_fee_revenue"
            ],
            "expected_total_revenue": simulation[
                "expected_total_revenue"
            ],
            "revenue_change": simulation["revenue_change"],
            "revenue_change_pct": simulation[
                "revenue_change_pct"
            ]
        })

    # STEP 6 — Find highest total revenue

    best_policy = max(
        results,
        key=lambda x: x["expected_total_revenue"]
    )

    # STEP 7 — Return result

    return {
        "prediction": prediction,
        "late_days_distribution": distribution,
        "fee_constraint": fee_constraint,
        "candidate_fee_count": len(candidate_fees),
        "policies": results,
        "recommended_policy": best_policy
    }
