# ============================================================
# SAKILA AI AGENT — TOOL DEFINITIONS
# ============================================================


# ============================================================
# DATA TOOLS
# ============================================================

from tools.data.get_rental_data import get_rental_data
from tools.data.get_category_data import get_category_data
from tools.data.get_customer_data import get_customer_data
from tools.data.get_film_data import get_film_data
from tools.data.get_store_data import get_store_data


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

from tools.analysis.analyze_revenue_drivers import (
    analyze_revenue_drivers
)


# ============================================================
# ML TOOLS
# ============================================================

from tools.ml.predict_late_probability import (
    predict_late_probability
)

from tools.ml.predict_expected_late_days import (
    predict_expected_late_days
)


# ============================================================
# SIMULATION TOOLS
# ============================================================

from tools.simulation.simulate_fee_policy import (
    simulate_fee_policy
)

from tools.simulation.simulate_rental_policy import (
    simulate_rental_policy
)

from tools.simulation.compare_scenarios import (
    compare_scenarios
)


# ============================================================
# OPTIMIZATION TOOLS
# ============================================================

from tools.optimization.find_best_policy import (
    find_best_policy
)

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

    # --------------------------------------------------------
    # Data
    # --------------------------------------------------------

    "get_rental_data": get_rental_data,
    "get_category_data": get_category_data,
    "get_customer_data": get_customer_data,
    "get_film_data": get_film_data,
    "get_store_data": get_store_data,

    # --------------------------------------------------------
    # Analysis
    # --------------------------------------------------------

    "analyze_revenue_structure": analyze_revenue_structure,
    "analyze_average_rental_rate_by_category": analyze_average_rental_rate_by_category,
    "analyze_late_fee_contribution": analyze_late_fee_contribution,
    "analyze_late_fee_dependency": analyze_late_fee_dependency,
    "analyze_revenue_drivers": analyze_revenue_drivers,

    # --------------------------------------------------------
    # ML
    # --------------------------------------------------------

    "predict_late_probability": predict_late_probability,
    "predict_expected_late_days": predict_expected_late_days,

    # --------------------------------------------------------
    # Simulation
    # --------------------------------------------------------

    "simulate_fee_policy": simulate_fee_policy,
    "simulate_rental_policy": simulate_rental_policy,
    "compare_scenarios": compare_scenarios,

    # --------------------------------------------------------
    # Optimization
    # --------------------------------------------------------
    

    "find_best_policy": find_best_policy,
    "apply_policy_constraints": apply_policy_constraints,
    "generate_policy_recommendation": generate_policy_recommendation,
}


# ============================================================
# CLAUDE / LLM TOOL SCHEMAS
# ============================================================

TOOL_DEFINITIONS = [
    {
        "name": "analyze_average_rental_rate_by_category",
        "description": (
            "Calculate the average rental rate for ALL 16 Sakila "
            "film categories directly from the MySQL database. "
            "Returns one result for every category. "
            "Use this tool for questions about average rental "
            "rate by category. Do not use raw film-level data."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },


    # ========================================================
    # DATA TOOLS
    # ========================================================

    {
        "name": "get_rental_data",
        "description": (
            "Get rental transaction data including rental "
            "duration, rental rate, return date, customer, "
            "film, and category."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },

    {
        "name": "get_category_data",
        "description": (
            "Get rental and late-return statistics by "
            "film category."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },

    {
        "name": "get_customer_data",
        "description": (
            "Get rental and late-return statistics "
            "for customers."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },

    {
        "name": "get_film_data",
        "description": (
            "Get film information including title, rental "
            "duration, rental rate, and category."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },

    {
        "name": "get_store_data",
        "description": (
            "Get rental and revenue statistics by store."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },


    # ========================================================
    # ANALYSIS TOOLS
    # ========================================================

    {
        "name": "analyze_revenue_structure",
        "description": (
            "Analyze total revenue, rental revenue, "
            "late-fee revenue, and the contribution "
            "of late fees to total revenue."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },

    {
        "name": "analyze_late_fee_contribution",
        "description": (
            "Analyze late-fee revenue contribution "
            "overall and by film category."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },

    {
        "name": "analyze_late_fee_dependency",
        "description": (
            "Measure how dependent total Sakila revenue "
            "is on late-fee revenue and calculate the "
            "overall late-return rate."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },

    {
        "name": "analyze_revenue_drivers",
        "description": (
            "Analyze late-fee revenue drivers by category, "
            "rental duration, rental rate, and late days."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },


    # ========================================================
    # MACHINE LEARNING TOOLS
    # ========================================================

    {
        "name": "predict_late_probability",
        "description": (
            "Predict the probability that a rental will "
            "be returned late using customer late-return "
            "rate, category, rental duration, and rental rate."
        ),
        "input_schema": {
            "type": "object",
            "properties": {

                "customer_late_rate": {
                    "type": "number",
                    "description": (
                        "Historical late-return rate "
                        "of the customer."
                    )
                },

                "category": {
                    "type": "string",
                    "description": "Film category."
                },

                "rental_duration": {
                    "type": "integer",
                    "description": (
                        "Allowed rental duration in days."
                    )
                },

                "rental_rate": {
                    "type": "number",
                    "description": "Rental price."
                }
            },

            "required": [
                "customer_late_rate",
                "category",
                "rental_duration",
                "rental_rate"
            ]
        }
    },

    {
        "name": "predict_expected_late_days",
        "description": (
            "Predict the expected number of late days "
            "for a rental using the trained machine-learning model."
        ),
        "input_schema": {
            "type": "object",
            "properties": {

                "customer_late_rate": {
                    "type": "number",
                    "description": (
                        "Historical late-return rate "
                        "of the customer."
                    )
                },

                "category": {
                    "type": "string",
                    "description": "Film category."
                },

                "rental_duration": {
                    "type": "integer",
                    "description": (
                        "Allowed rental duration in days."
                    )
                },

                "rental_rate": {
                    "type": "number",
                    "description": "Rental price."
                }
            },

            "required": [
                "customer_late_rate",
                "category",
                "rental_duration",
                "rental_rate"
            ]
        }
    },


    # ========================================================
    # SIMULATION TOOLS
    # ========================================================

    {
        "name": "simulate_fee_policy",
        "description": (
            "Simulate expected late-fee revenue under "
            "a specific late-fee-per-day policy."
        ),
        "input_schema": {
            "type": "object",
            "properties": {

                "late_probability": {
                    "type": "number",
                    "description": (
                        "Predicted probability of "
                        "a late return."
                    )
                },

                "expected_late_days": {
                    "type": "number",
                    "description": (
                        "Expected number of late days."
                    )
                },

                "fee_per_day": {
                    "type": "number",
                    "description": (
                        "Late fee charged per late day."
                    )
                }
            },

            "required": [
                "late_probability",
                "expected_late_days",
                "fee_per_day"
            ]
        }
    },

    {
        "name": "simulate_rental_policy",
        "description": (
            "Compare the current rental duration with "
            "a proposed rental duration using predicted "
            "late probability and expected late days."
        ),
        "input_schema": {
            "type": "object",
            "properties": {

                "customer_late_rate": {
                    "type": "number",
                    "description": (
                        "Historical late-return rate "
                        "of the customer."
                    )
                },

                "category": {
                    "type": "string",
                    "description": "Film category."
                },

                "current_rental_duration": {
                    "type": "integer",
                    "description": (
                        "Current rental duration."
                    )
                },

                "rental_rate": {
                    "type": "number",
                    "description": "Rental price."
                },

                "proposed_rental_duration": {
                    "type": "integer",
                    "description": (
                        "Proposed rental duration."
                    )
                },

                "fee_per_day": {
                    "type": "number",
                    "description": (
                        "Late fee per late day."
                    )
                }
            },

            "required": [
                "customer_late_rate",
                "category",
                "current_rental_duration",
                "rental_rate",
                "proposed_rental_duration",
                "fee_per_day"
            ]
        }
    },

    {
        "name": "compare_scenarios",
        "description": (
            "Generate and compare alternative late-fee "
            "and rental-duration policies based on "
            "expected late-fee revenue."
        ),
        "input_schema": {
            "type": "object",
            "properties": {

                "customer_late_rate": {
                    "type": "number"
                },

                "category": {
                    "type": "string"
                },

                "current_rental_duration": {
                    "type": "integer"
                },

                "rental_rate": {
                    "type": "number"
                },

                "fee_options": {
                    "type": "array",
                    "items": {
                        "type": "number"
                    }
                },

                "rental_duration_options": {
                    "type": "array",
                    "items": {
                        "type": "integer"
                    }
                },

                "current_fee_per_day": {
                    "type": "number",
                    "default": 1.00
                }
            },

            "required": [
                "customer_late_rate",
                "category",
                "current_rental_duration",
                "rental_rate"
            ]
        }
    },


    # ========================================================
    # OPTIMIZATION TOOLS
    # ========================================================

    {
        "name": "find_best_policy",
        "description": (
            "Find the policy scenario with the highest "
            "expected late-fee revenue before business constraints."
        ),
        "input_schema": {
            "type": "object",
            "properties": {

                "customer_late_rate": {
                    "type": "number"
                },

                "category": {
                    "type": "string"
                },

                "current_rental_duration": {
                    "type": "integer"
                },

                "rental_rate": {
                    "type": "number"
                },

                "fee_options": {
                    "type": "array",
                    "items": {
                        "type": "number"
                    }
                },

                "rental_duration_options": {
                    "type": "array",
                    "items": {
                        "type": "integer"
                    }
                },

                "current_fee_per_day": {
                    "type": "number",
                    "default": 1.00
                }
            },

            "required": [
                "customer_late_rate",
                "category",
                "current_rental_duration",
                "rental_rate"
            ]
        }
    },

    {
        "name": "apply_policy_constraints",
        "description": (
            "Apply business constraints to policy scenarios "
            "and select the highest expected-revenue feasible policy."
        ),
        "input_schema": {
            "type": "object",
            "properties": {

                "customer_late_rate": {
                    "type": "number"
                },

                "category": {
                    "type": "string"
                },

                "current_rental_duration": {
                    "type": "integer"
                },

                "rental_rate": {
                    "type": "number"
                },

                "min_rental_duration": {
                    "type": "integer",
                    "default": 3
                },

                "max_rental_duration": {
                    "type": "integer",
                    "default": 7
                }
            },

            "required": [
                "customer_late_rate",
                "category",
                "current_rental_duration",
                "rental_rate"
            ]
        }
    },

    {
        "name": "generate_policy_recommendation",
        "description": (
            "Generate the final late-fee policy recommendation "
            "by combining scenario comparison, business constraints, "
            "and expected late-fee revenue."
        ),
        "input_schema": {
            "type": "object",
            "properties": {

                "customer_late_rate": {
                    "type": "number"
                },

                "category": {
                    "type": "string"
                },

                "current_rental_duration": {
                    "type": "integer"
                },

                "rental_rate": {
                    "type": "number"
                },

                "max_fee_per_day": {
                    "type": "number",
                    "default": 2.50
                },

                "min_rental_duration": {
                    "type": "integer",
                    "default": 3
                },

                "max_rental_duration": {
                    "type": "integer",
                    "default": 7
                }
            },

            "required": [
                "customer_late_rate",
                "category",
                "current_rental_duration",
                "rental_rate"
            ]
        }
    }
]


# ============================================================
# CHECK TOOL DEFINITIONS
# ============================================================

if __name__ == "__main__":

    print("=" * 70)
    print("SAKILA AI AGENT — TOOL DEFINITIONS")
    print("=" * 70)

    print(
        f"\nTotal tools: "
        f"{len(TOOL_DEFINITIONS)}"
    )

    print("\nAvailable tools:")

    for i, tool in enumerate(
        TOOL_DEFINITIONS,
        start=1
    ):
        print(
            f"{i}. {tool['name']}"
        )

    print(
        "\nTool definitions loaded successfully."
    )
