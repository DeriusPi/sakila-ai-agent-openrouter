"""
No-LLM regression test: checks that every backend tool returns the
validated Sakila figures and that all tools agree with each other.

Run from the project root (needs the Sakila MySQL database):

    python test_data_consistency.py
"""

from tools.analysis.analyze_late_fee_contribution import (
    analyze_late_fee_contribution,
)
from tools.analysis.analyze_late_fee_dependency import (
    analyze_late_fee_dependency,
)
from tools.analysis.analyze_late_fee_revenue import analyze_late_fee_revenue
from tools.analysis.analyze_revenue_drivers import analyze_revenue_drivers
from tools.analysis.analyze_revenue_structure import analyze_revenue_structure
from tools.data.business_metrics import get_business_kpis
from tools.data.get_category_data import get_category_data
from tools.data.get_customer_data import get_customer_data
from tools.data.get_revenue_by_time import get_revenue_by_time
from tools.data.get_store_data import get_store_data
from tools.data.llm_views import get_rental_summary
from tools.ml.predict_late_probability import predict_late_probability
from tools.simulation.compare_scenarios import compare_scenarios
from tools.simulation.simulate_fee_policy import simulate_fee_policy
from tools.optimization.generate_policy_recommendation import (
    generate_policy_recommendation,
)
from tools.tool_definitions import validate_tool_registry


EXPECTED = {
    "total_revenue": 67406.56,
    "rental_revenue": 47143.80,
    "late_fee_revenue": 20262.76,
    "late_fee_contribution_pct": 30.06,
    "payments": 16044,
    "completed_rentals": 15861,
    "late_rentals": 8121,
    "late_rate_pct": 51.20,
}


def close(a, b, tol=0.01):
    return abs(float(a) - float(b)) <= tol


def check(name, condition):
    if not condition:
        raise AssertionError(f"FAIL: {name}")
    print(f"PASS: {name}")


def main():
    print("=" * 70)
    print("SAKILA DATA CONSISTENCY TEST (no LLM)")
    print("=" * 70)

    check("tool schemas match Python functions", validate_tool_registry() == [])

    k = get_business_kpis()
    check("total revenue", close(k["total_revenue"], EXPECTED["total_revenue"]))
    check("rental revenue", close(k["rental_revenue"], EXPECTED["rental_revenue"]))
    check("late-fee revenue", close(k["late_fee_revenue"], EXPECTED["late_fee_revenue"]))
    check("late-fee contribution", close(k["late_fee_contribution_pct"], EXPECTED["late_fee_contribution_pct"]))
    check("payment rows", k["payment_count"] == EXPECTED["payments"])
    check("completed rentals", k["completed_rentals"] == EXPECTED["completed_rentals"])
    check("late rentals", k["late_rentals"] == EXPECTED["late_rentals"])
    check("late rate", close(k["late_rate_pct"], EXPECTED["late_rate_pct"]))

    s = analyze_revenue_structure()
    check("analyze_revenue_structure = KPIs",
          close(s["total_revenue"], k["total_revenue"])
          and close(s["late_fee_revenue"], k["late_fee_revenue"]))

    d = analyze_late_fee_dependency()
    check("analyze_late_fee_dependency = KPIs",
          d["late_rentals"] == k["late_rentals"]
          and d["total_rentals"] == k["completed_rentals"])

    c = analyze_late_fee_contribution()
    check("analyze_late_fee_contribution = KPIs",
          close(c["total_late_fee_revenue"], k["late_fee_revenue"]))

    lr = analyze_late_fee_revenue()
    check("analyze_late_fee_revenue = KPIs",
          close(lr["total_revenue"], k["total_revenue"])
          and lr["late_rentals"] == k["late_rentals"])

    cats = get_category_data()
    check("16 categories", len(cats) == 16)
    check("category late rentals sum to 8,121",
          sum(r["late_rentals"] for r in cats) == EXPECTED["late_rentals"])
    check("category revenue sums to total",
          close(sum(r["total_revenue"] for r in cats), EXPECTED["total_revenue"]))
    check("category late fees sum to total",
          close(sum(r["late_fee_revenue"] for r in cats), EXPECTED["late_fee_revenue"]))

    stores = get_store_data()
    check("store revenue sums to total",
          close(sum(r["total_revenue"] for r in stores), EXPECTED["total_revenue"]))
    check("store late fees sum to total",
          close(sum(r["late_fee_revenue"] for r in stores), EXPECTED["late_fee_revenue"]))
    check("store late rentals sum to 8,121",
          sum(r["late_rentals"] for r in stores) == EXPECTED["late_rentals"])

    for store in stores:
        sk = get_business_kpis(store_id=store["store_id"])
        check(f"store {store['store_id']} KPIs = get_store_data",
              close(sk["total_revenue"], store["total_revenue"])
              and sk["late_rentals"] == store["late_rentals"])

    customers = get_customer_data()
    check("599 customers", len(customers) == 599)
    check("customer late rentals sum to 8,121",
          sum(r["late_rentals"] for r in customers) == EXPECTED["late_rentals"])

    t = get_revenue_by_time(group_by="month")
    check("monthly revenue sums to total",
          close(t["total_revenue"], EXPECTED["total_revenue"]))
    t2 = get_revenue_by_time(start_date="2005-05", end_date="2005-07")
    check("YYYY-MM end_date works (May-Jul = 42,822.24)",
          close(t2["total_revenue"], 42822.24))

    rs = get_rental_summary()
    check("rental summary late rentals = 8,121",
          rs["late_rentals"] == EXPECTED["late_rentals"])

    dr = analyze_revenue_drivers()
    check("drivers late-day buckets sum to completed rentals",
          sum(dr["late_days_distribution"].values()) == EXPECTED["completed_rentals"])

    p1 = predict_late_probability(0.512, "Sports", 5, 2.99)
    p2 = predict_late_probability(51.2, "sports", 5, 2.99)
    check("ML accepts % and lower-case category",
          p1["late_probability"] == p2["late_probability"] < 0.99)

    sc = compare_scenarios(0.512, "Sports", 5, 2.99)
    totals = [x["expected_total_revenue"] for x in sc["all_scenarios"]]
    check("scenarios on the same scale",
          min(totals) > 1000 and any(
              x["policy_type"] == "rental_duration" for x in sc["all_scenarios"]
          ))

    low = simulate_fee_policy(0.512, "All", 5, 2.98, 1.00, 1.00)
    high = simulate_fee_policy(0.512, "All", 5, 2.98, 1.50, 1.00)
    check("higher fee -> lower late probability and fewer late returns",
          high["late_probability"] < low["late_probability"]
          and high["expected_late_returns"] < low["expected_late_returns"])

    rec = generate_policy_recommendation(0.512, "All", 5, 2.98)
    best = rec["best_policy"]
    check("recommended policy does not increase late returns",
          best is not None
          and best["late_probability"]
          <= rec["current_scenario"]["late_probability"] + 1e-9)

    print("=" * 70)
    print("ALL DATA CONSISTENCY TESTS PASSED")
    print("=" * 70)


if __name__ == "__main__":
    main()
