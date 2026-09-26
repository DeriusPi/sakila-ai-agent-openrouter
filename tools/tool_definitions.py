# ============================================================
# SAKILA AI AGENT — TOOL DEFINITIONS
# ============================================================
#
# FIXES in this version
# ---------------------
# 1. simulate_fee_policy: the schema declared late_probability /
#    expected_late_days, but the Python function expects
#    customer_late_rate / category / rental_duration / rental_rate.
#    Every agent call failed with "unexpected keyword argument".
# 2. generate_policy_recommendation: the schema exposed
#    max_fee_per_day, which the function does not accept.
# 3. get_rental_data / get_film_data / get_customer_data returned
#    thousands of raw rows that llm.py truncated to 100 rows, so the
#    model computed KPIs from a partial sample. The agent now gets
#    SQL-aggregated summaries (get_rental_summary, get_film_catalog,
#    get_customer_summary). The old names are kept as aliases.
# 4. analyze_late_fee_revenue was referenced by the system prompt but
#    was not registered ("Unknown tool").
# 5. New get_business_kpis tool: one consistent source for revenue,
#    late-fee and late-return KPIs with category/store/date filters.
# ============================================================


# ============================================================
# DATA TOOLS
# ============================================================

from tools.data.business_metrics import get_business_kpis
from tools.data.get_category_data import get_category_data
from tools.data.get_store_data import get_store_data
from tools.data.get_revenue_by_time import get_revenue_by_time
from tools.data.llm_views import (
    get_customer_summary,
    get_film_catalog,
    get_rental_summary,
)


# ============================================================
# ANALYSIS TOOLS
# ============================================================

from tools.analysis.analyze_average_rental_rate_by_category import (
    analyze_average_rental_rate_by_category
)
from tools.analysis.analyze_revenue_structure import (
    analyze_revenue_structure
)
from tools.analysis.analyze_late_fee_contribution import (
    analyze_late_fee_contribution
)
from tools.analysis.analyze_late_fee_dependency import (
    analyze_late_fee_dependency
)
from tools.analysis.analyze_late_fee_revenue import (
    analyze_late_fee_revenue
)
from tools.analysis.analyze_revenue_drivers import (
    analyze_revenue_drivers
)


# ============================================================
# ML TOOLS
# ============================================================

from tools.ml.predict_late_probability import predict_late_probability
from tools.ml.predict_expected_late_days import predict_expected_late_days


# ============================================================
# SIMULATION TOOLS
# ============================================================

from tools.simulation.simulate_fee_policy import simulate_fee_policy
from tools.simulation.simulate_rental_policy import simulate_rental_policy
from tools.simulation.compare_scenarios import compare_scenarios


# ============================================================
# OPTIMIZATION TOOLS
# ============================================================

from tools.optimization.find_best_policy import find_best_policy
from tools.optimization.apply_policy_constraints import (
    apply_policy_constraints
)
from tools.optimization.generate_policy_recommendation import (
    generate_policy_recommendation
)


# ============================================================
# PYTHON FUNCTION REGISTRY
# ============================================================

TOOL_FUNCTIONS = {

    # Data
    "get_business_kpis": get_business_kpis,
    "get_revenue_by_time": get_revenue_by_time,
    "get_category_data": get_category_data,
    "get_store_data": get_store_data,
    "get_rental_summary": get_rental_summary,
    "get_film_catalog": get_film_catalog,
    "get_customer_summary": get_customer_summary,

    # Analysis
    "analyze_revenue_structure": analyze_revenue_structure,
    "analyze_average_rental_rate_by_category": (
        analyze_average_rental_rate_by_category
    ),
    "analyze_late_fee_contribution": analyze_late_fee_contribution,
    "analyze_late_fee_dependency": analyze_late_fee_dependency,
    "analyze_late_fee_revenue": analyze_late_fee_revenue,
    "analyze_revenue_drivers": analyze_revenue_drivers,

    # ML
    "predict_late_probability": predict_late_probability,
    "predict_expected_late_days": predict_expected_late_days,

    # Simulation
    "simulate_fee_policy": simulate_fee_policy,
    "simulate_rental_policy": simulate_rental_policy,
    "compare_scenarios": compare_scenarios,

    # Optimization
    "find_best_policy": find_best_policy,
    "apply_policy_constraints": apply_policy_constraints,
    "generate_policy_recommendation": generate_policy_recommendation,
}

# Backward-compatible aliases: if the model calls an old tool name,
# route it to the aggregated (non-truncated) version.
TOOL_ALIASES = {
    "get_rental_data": "get_rental_summary",
    "get_film_data": "get_film_catalog",
    "get_customer_data": "get_customer_summary",
    "get_revenue_data": "analyze_revenue_structure",
    "get_late_return_summary": "get_business_kpis",
}

for _alias, _target in TOOL_ALIASES.items():
    TOOL_FUNCTIONS[_alias] = TOOL_FUNCTIONS[_target]


# ============================================================
# REUSABLE SCHEMA PARTS
# ============================================================

_CATEGORY_NAMES = (
    "Action, Animation, Children, Classics, Comedy, Documentary, "
    "Drama, Family, Foreign, Games, Horror, Music, New, Sci-Fi, "
    "Sports, Travel"
)

_PROFILE_PROPERTIES = {
    "customer_late_rate": {
        "type": "number",
        "description": (
            "Customer historical late-return rate as a RATIO 0-1 "
            "(e.g. 0.512 for 51.2%). If no customer is specified use "
            "the overall rate: get_business_kpis.late_rate_pct / 100."
        ),
    },
    "category": {
        "type": "string",
        "description": (
            f"Film category. One of: {_CATEGORY_NAMES}. Use \"All\" for "
            "the whole catalogue (rental-weighted average over all "
            "categories) when the user does not name a category."
        ),
    },
    "rental_rate": {
        "type": "number",
        "description": (
            "Rental price in USD (Sakila uses 0.99, 2.99 or 4.99; the "
            "category average from "
            "analyze_average_rental_rate_by_category is also fine)."
        ),
    },
}

_CURRENT_DURATION = {
    "type": "integer",
    "description": "Current allowed rental duration in days (3-7).",
}

_POLICY_PROPERTIES = {
    **_PROFILE_PROPERTIES,
    "current_rental_duration": _CURRENT_DURATION,
    "fee_options": {
        "type": "array",
        "items": {"type": "number"},
        "description": (
            "Optional late fees per day to test. Default: 5 points inside "
            "the DB-derived feasible range."
        ),
    },
    "rental_duration_options": {
        "type": "array",
        "items": {"type": "integer"},
        "description": "Optional rental durations to test. Default 3-7.",
    },
    "current_fee_per_day": {
        "type": "number",
        "description": "Current late fee per day. Default 1.00.",
    },
}

_POLICY_REQUIRED = [
    "customer_late_rate",
    "category",
    "current_rental_duration",
    "rental_rate",
]

_FILTER_PROPERTIES = {
    "category": {
        "type": "string",
        "description": f"Optional category filter. One of: {_CATEGORY_NAMES}.",
    },
    "store_id": {
        "type": "integer",
        "description": "Optional physical store filter: 1 or 2.",
    },
    "start_date": {
        "type": "string",
        "description": "Optional start date YYYY-MM-DD (inclusive).",
    },
    "end_date": {
        "type": "string",
        "description": "Optional end date YYYY-MM-DD (inclusive).",
    },
}


def _no_args():
    return {"type": "object", "properties": {}, "required": []}


# ============================================================
# LLM TOOL SCHEMAS
# ============================================================

TOOL_DEFINITIONS = [

    # ========================================================
    # DATA TOOLS
    # ========================================================

    {
        "name": "get_business_kpis",
        "description": (
            "PRIMARY KPI TOOL. Exact headline KPIs from SQL: total revenue, "
            "rental revenue, late-fee revenue, late-fee contribution %, "
            "payment count, completed rentals, late rentals, late-return "
            "rate %, open (unreturned) rentals, average late days. "
            "Optional filters: category, store_id, start_date, end_date. "
            "Use it for any 'how much / how many / what percentage' "
            "question and for scoped KPIs (one store, one category, "
            "one period)."
        ),
        "input_schema": {
            "type": "object",
            "properties": dict(_FILTER_PROPERTIES),
            "required": [],
        },
    },

    {
        "name": "get_revenue_by_time",
        "description": (
            "Revenue (SUM(payment.amount)) by payment.payment_date over a "
            "date range, grouped by day, week, month, quarter, year, "
            "category or store. Each group includes rental revenue, "
            "late-fee revenue and revenue share. Optional category and "
            "store filters. Use for any time-period or trend question."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "start_date": {
                    "type": "string",
                    "description": (
                        "Start date YYYY-MM-DD, inclusive "
                        "(YYYY-MM is also accepted)."
                    ),
                },
                "end_date": {
                    "type": "string",
                    "description": (
                        "End date YYYY-MM-DD, inclusive "
                        "(YYYY-MM means the last day of that month)."
                    ),
                },
                "group_by": {
                    "type": "string",
                    "enum": [
                        "day", "week", "month", "quarter",
                        "year", "category", "store",
                    ],
                    "description": "How revenue is grouped. Default month.",
                },
                "category": _FILTER_PROPERTIES["category"],
                "store_id": _FILTER_PROPERTIES["store_id"],
            },
            "required": [],
        },
    },

    {
        "name": "get_category_data",
        "description": (
            "All 16 categories with completed rentals, late rentals, "
            "late-return rate %, total revenue, rental revenue, late-fee "
            "revenue and late-fee contribution %. Optional store_id and "
            "start_date / end_date filters (revenue by payment date, "
            "rentals by rental date)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "store_id": _FILTER_PROPERTIES["store_id"],
                "start_date": _FILTER_PROPERTIES["start_date"],
                "end_date": _FILTER_PROPERTIES["end_date"],
            },
            "required": [],
        },
    },

    {
        "name": "get_store_data",
        "description": (
            "Both stores (physical store of the rented copy): city, "
            "rentals, late rentals, late-return rate, total/rental/"
            "late-fee revenue, revenue share and inventory size. Optional "
            "category and start_date / end_date filters."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "category": _FILTER_PROPERTIES["category"],
                "start_date": _FILTER_PROPERTIES["start_date"],
                "end_date": _FILTER_PROPERTIES["end_date"],
            },
            "required": [],
        },
    },

    {
        "name": "get_rental_summary",
        "description": (
            "Aggregated rental behaviour (complete data, not a sample): "
            "totals plus breakdowns by rental duration, rental rate and "
            "month with late rentals, late rate and average actual rental "
            "days. Filters by rental_date, category and store."
        ),
        "input_schema": {
            "type": "object",
            "properties": dict(_FILTER_PROPERTIES),
            "required": [],
        },
    },

    {
        "name": "get_film_catalog",
        "description": (
            "Film catalogue statistics (film count, average rate/duration, "
            "rate and duration distribution) plus the top N films sorted "
            "by revenue, rentals, late_fee, rental_rate or title. "
            "Optional category and title search."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "category": _FILTER_PROPERTIES["category"],
                "title_contains": {
                    "type": "string",
                    "description": "Optional part of a film title.",
                },
                "sort_by": {
                    "type": "string",
                    "enum": [
                        "revenue", "rentals", "late_fee",
                        "rental_rate", "title",
                    ],
                    "description": "Sort order for top_films. Default revenue.",
                },
                "limit": {
                    "type": "integer",
                    "description": "Number of films to list (1-50). Default 10.",
                },
            },
            "required": [],
        },
    },

    {
        "name": "get_customer_summary",
        "description": (
            "Customer behaviour: distribution of customer late-return "
            "rates for all 599 customers and the top N customers sorted "
            "by late_rate, late_rentals, rentals, revenue or late_fee. "
            "Pass customer_id to get one customer's statistics "
            "(its late_rate 0-1 can be used as customer_late_rate)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "customer_id": {
                    "type": "integer",
                    "description": "Optional single customer id.",
                },
                "sort_by": {
                    "type": "string",
                    "enum": [
                        "late_rate", "late_rentals", "rentals",
                        "revenue", "late_fee",
                    ],
                },
                "limit": {
                    "type": "integer",
                    "description": "Number of customers to list (1-50).",
                },
                "min_rentals": {
                    "type": "integer",
                    "description": (
                        "Only rank customers with at least this many "
                        "completed rentals. Default 10."
                    ),
                },
            },
            "required": [],
        },
    },

    # ========================================================
    # ANALYSIS TOOLS
    # ========================================================

    {
        "name": "analyze_revenue_structure",
        "description": (
            "Total revenue, rental revenue, late-fee revenue and the "
            "late-fee contribution to total revenue (whole dataset)."
        ),
        "input_schema": _no_args(),
    },

    {
        "name": "analyze_average_rental_rate_by_category",
        "description": (
            "Average rental rate and film count for ALL 16 categories. "
            "Use this for any average-rental-rate-by-category question."
        ),
        "input_schema": _no_args(),
    },

    {
        "name": "analyze_late_fee_contribution",
        "description": (
            "Late-fee revenue contribution overall and by category "
            "(rental revenue, late-fee revenue, total revenue, "
            "contribution %)."
        ),
        "input_schema": _no_args(),
    },

    {
        "name": "analyze_late_fee_dependency",
        "description": (
            "How dependent total revenue is on late fees, plus the overall "
            "late-return rate."
        ),
        "input_schema": _no_args(),
    },

    {
        "name": "analyze_late_fee_revenue",
        "description": (
            "Late-return rate and late-fee revenue overall and for every "
            "category (late rentals, late rate %, late-fee revenue, "
            "contribution %, share of all late fees)."
        ),
        "input_schema": _no_args(),
    },

    {
        "name": "analyze_revenue_drivers",
        "description": (
            "Late-fee revenue drivers by category, rental duration and "
            "rental rate (revenue, late-fee revenue, late rate %, average "
            "late days) and the distribution of late days. Use for 'why' "
            "and 'what drives late fees' questions."
        ),
        "input_schema": _no_args(),
    },

    # ========================================================
    # MACHINE LEARNING TOOLS
    # ========================================================

    {
        "name": "predict_late_probability",
        "description": (
            "Predict the probability that a rental is returned late for a "
            "profile (customer late rate, category, rental duration, "
            "rental rate)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                **_PROFILE_PROPERTIES,
                "rental_duration": {
                    "type": "integer",
                    "description": "Allowed rental duration in days (3-7).",
                },
            },
            "required": [
                "customer_late_rate", "category",
                "rental_duration", "rental_rate",
            ],
        },
    },

    {
        "name": "predict_expected_late_days",
        "description": (
            "Predict the expected number of late days (given the rental is "
            "late) for a profile."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                **_PROFILE_PROPERTIES,
                "rental_duration": {
                    "type": "integer",
                    "description": "Allowed rental duration in days (3-7).",
                },
            },
            "required": [
                "customer_late_rate", "category",
                "rental_duration", "rental_rate",
            ],
        },
    },

    # ========================================================
    # SIMULATION TOOLS
    # ========================================================

    {
        "name": "simulate_fee_policy",
        "description": (
            "Simulate business-level expected rental revenue, late-fee "
            "revenue and total revenue for ONE late-fee-per-day value, "
            "compared with the current fee. Late probability and late "
            "days are predicted internally by the ML models."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                **_PROFILE_PROPERTIES,
                "rental_duration": {
                    "type": "integer",
                    "description": "Allowed rental duration in days (3-7).",
                },
                "fee_per_day": {
                    "type": "number",
                    "description": "Late fee per late day to simulate.",
                },
                "current_fee_per_day": {
                    "type": "number",
                    "description": "Current late fee per day. Default 1.00.",
                },
            },
            "required": [
                "customer_late_rate", "category", "rental_duration",
                "rental_rate", "fee_per_day",
            ],
        },
    },

    {
        "name": "simulate_rental_policy",
        "description": (
            "Compare the current and a proposed rental duration for ONE "
            "rental profile (per-rental expected late-fee revenue). For "
            "business-level comparisons use compare_scenarios."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                **_PROFILE_PROPERTIES,
                "current_rental_duration": _CURRENT_DURATION,
                "proposed_rental_duration": {
                    "type": "integer",
                    "description": "Proposed rental duration in days.",
                },
                "fee_per_day": {
                    "type": "number",
                    "description": "Late fee per late day. Default 1.00.",
                },
            },
            "required": [
                "customer_late_rate", "category",
                "current_rental_duration", "rental_rate",
                "proposed_rental_duration",
            ],
        },
    },

    {
        "name": "compare_scenarios",
        "description": (
            "Generate and rank the current policy, late-fee scenarios and "
            "rental-duration scenarios on the same business-level expected "
            "total revenue scale."
        ),
        "input_schema": {
            "type": "object",
            "properties": dict(_POLICY_PROPERTIES),
            "required": list(_POLICY_REQUIRED),
        },
    },

    # ========================================================
    # OPTIMIZATION TOOLS
    # ========================================================

    {
        "name": "find_best_policy",
        "description": (
            "Scenario with the highest expected total revenue BEFORE "
            "business constraints."
        ),
        "input_schema": {
            "type": "object",
            "properties": dict(_POLICY_PROPERTIES),
            "required": list(_POLICY_REQUIRED),
        },
    },

    {
        "name": "apply_policy_constraints",
        "description": (
            "Apply business constraints (DB-derived fee range, min/max "
            "rental duration) and return feasible and rejected scenarios "
            "with the best feasible policy."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                **_POLICY_PROPERTIES,
                "min_rental_duration": {
                    "type": "integer",
                    "description": "Minimum allowed duration. Default 3.",
                },
                "max_rental_duration": {
                    "type": "integer",
                    "description": "Maximum allowed duration. Default 7.",
                },
            },
            "required": list(_POLICY_REQUIRED),
        },
    },

    {
        "name": "generate_policy_recommendation",
        "description": (
            "FINAL POLICY TOOL. Runs the full pipeline (scenarios -> "
            "constraints -> best feasible policy) and returns the "
            "recommendation with its reason. Use for 'what policy / fee / "
            "duration should we use?' questions."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                **_POLICY_PROPERTIES,
                "min_rental_duration": {
                    "type": "integer",
                    "description": "Minimum allowed duration. Default 3.",
                },
                "max_rental_duration": {
                    "type": "integer",
                    "description": "Maximum allowed duration. Default 7.",
                },
            },
            "required": list(_POLICY_REQUIRED),
        },
    },
]


# ============================================================
# SELF-CHECK
# ============================================================

def validate_tool_registry():
    """
    Check that every schema has a Python function and that every schema
    parameter exists in the function signature.
    Returns a list of problems (empty list = OK).
    """

    import inspect

    problems = []

    for tool in TOOL_DEFINITIONS:
        name = tool["name"]
        func = TOOL_FUNCTIONS.get(name)

        if func is None:
            problems.append(f"{name}: no Python function registered")
            continue

        signature = inspect.signature(func)
        params = signature.parameters

        for prop in tool["input_schema"].get("properties", {}):
            if prop not in params:
                problems.append(
                    f"{name}: schema parameter '{prop}' is not accepted "
                    "by the Python function"
                )

        for req in tool["input_schema"].get("required", []):
            if req not in tool["input_schema"].get("properties", {}):
                problems.append(
                    f"{name}: required '{req}' missing from properties"
                )

    return problems


if __name__ == "__main__":

    print("=" * 70)
    print("SAKILA AI AGENT — TOOL DEFINITIONS")
    print("=" * 70)

    print(f"\nTotal tools: {len(TOOL_DEFINITIONS)}")

    for i, tool in enumerate(TOOL_DEFINITIONS, start=1):
        print(f"{i}. {tool['name']}")

    issues = validate_tool_registry()

    if issues:
        print("\nPROBLEMS:")
        for issue in issues:
            print(" -", issue)
    else:
        print("\nAll schemas match their Python functions.")
