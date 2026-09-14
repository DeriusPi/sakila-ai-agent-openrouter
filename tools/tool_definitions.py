# ============================================================
# TOOL DEFINITIONS
# ============================================================

from tools.data_tools import (
    get_elasticity_results,
    get_category_details,
    get_elasticity_summary
)

from tools.analysis_tools import (
    get_significant_categories,
    rank_elasticity,
    compare_categories
)

from tools.revenue.simulate_price_change import (
    simulate_price_change
)

from tools.revenue.simulate_price_scenario import (
    simulate_price_scenario
)

from tools.revenue.rank_revenue_opportunities import (
    rank_revenue_opportunities
)

from tools.pricing.pricing_recommendation import (
    pricing_recommendation
)


# ============================================================
# PYTHON FUNCTIONS
# ============================================================

TOOL_FUNCTIONS = {

    "get_elasticity_results":
        get_elasticity_results,

    "get_category_details":
        get_category_details,

    "get_elasticity_summary":
        get_elasticity_summary,

    "get_significant_categories":
        get_significant_categories,

    "rank_elasticity":
        rank_elasticity,

    "compare_categories":
        compare_categories,

    "simulate_price_change":
        simulate_price_change,

    "simulate_price_scenario":
        simulate_price_scenario,

    "rank_revenue_opportunities":
        rank_revenue_opportunities,

    "pricing_recommendation":
        pricing_recommendation
}


# ============================================================
# CLAUDE TOOL SCHEMAS
# ============================================================

TOOL_DEFINITIONS = [

    # ========================================================
    # TOOL 1
    # ========================================================

    {
        "name": "get_elasticity_results",

        "description":
            "Get elasticity results for all product categories.",

        "input_schema": {
            "type": "object",

            "properties": {},

            "required": []
        }
    },


    # ========================================================
    # TOOL 2
    # ========================================================

    {
        "name": "get_category_details",

        "description":
            "Get detailed elasticity information for one category.",

        "input_schema": {
            "type": "object",

            "properties": {

                "category": {
                    "type": "string",

                    "description":
                        "The category to analyze."
                }
            },

            "required": [
                "category"
            ]
        }
    },


    # ========================================================
    # TOOL 3
    # ========================================================

    {
        "name": "get_elasticity_summary",

        "description":
            "Get a statistical summary of the elasticity dataset.",

        "input_schema": {
            "type": "object",

            "properties": {},

            "required": []
        }
    },


    # ========================================================
    # TOOL 4
    # ========================================================

    {
        "name": "get_significant_categories",

        "description":
            "Find categories whose elasticity estimates are statistically significant.",

        "input_schema": {
            "type": "object",

            "properties": {

                "alpha": {
                    "type": "number",

                    "description":
                        "Significance level, usually 0.05.",

                    "default": 0.05
                }
            },

            "required": []
        }
    },


    # ========================================================
    # TOOL 5
    # ========================================================

    {
        "name": "rank_elasticity",

        "description":
            "Rank categories according to their price elasticity.",

        "input_schema": {
            "type": "object",

            "properties": {

                "ascending": {
                    "type": "boolean",

                    "description":
                        "Whether to rank from lowest to highest elasticity.",

                    "default": True
                }
            },

            "required": []
        }
    },


    # ========================================================
    # TOOL 6
    # ========================================================

    {
        "name": "compare_categories",

        "description":
            "Compare elasticity results between two categories.",

        "input_schema": {
            "type": "object",

            "properties": {

                "category_1": {
                    "type": "string",

                    "description":
                        "First category."
                },

                "category_2": {
                    "type": "string",

                    "description":
                        "Second category."
                }
            },

            "required": [
                "category_1",
                "category_2"
            ]
        }
    },


    # ========================================================
    # TOOL 7
    # ========================================================

    {
        "name": "simulate_price_change",

        "description":
            "Estimate demand and revenue after changing the price of a category.",

        "input_schema": {
            "type": "object",

            "properties": {

                "current_price": {
                    "type": "number",

                    "description":
                        "Current price."
                },

                "current_demand": {
                    "type": "number",

                    "description":
                        "Current demand."
                },

                "new_price": {
                    "type": "number",

                    "description":
                        "New proposed price."
                },

                "elasticity": {
                    "type": "number",

                    "description":
                        "Price elasticity of demand."
                }
            },

            "required": [
                "current_price",
                "current_demand",
                "new_price",
                "elasticity"
            ]
        }
    },


    # ========================================================
    # TOOL 8
    # ========================================================

    {
        "name": "simulate_price_scenario",

        "description":
            "Compare multiple possible prices and estimate demand and revenue for each price.",

        "input_schema": {
            "type": "object",

            "properties": {

                "current_price": {
                    "type": "number",

                    "description":
                        "Current price."
                },

                "current_demand": {
                    "type": "number",

                    "description":
                        "Current demand."
                },

                "elasticity": {
                    "type": "number",

                    "description":
                        "Price elasticity of demand."
                },

                "price_scenarios": {
                    "type": "array",

                    "description":
                        "List of possible prices to evaluate.",

                    "items": {
                        "type": "number"
                    }
                }
            },

            "required": [
                "current_price",
                "current_demand",
                "elasticity",
                "price_scenarios"
            ]
        }
    },


    # ========================================================
    # TOOL 9
    # ========================================================

    {
        "name": "rank_revenue_opportunities",

        "description":
            "Rank categories by estimated revenue opportunity after a proposed price increase. Can filter to statistically significant elasticity estimates.",

        "input_schema": {
            "type": "object",

            "properties": {

                "category_data": {
                    "type": "array",

                    "description":
                        "Category data containing price, demand, elasticity, and p-value.",

                    "items": {
                        "type": "object"
                    }
                },

                "price_increase_pct": {
                    "type": "number",

                    "description":
                        "Percentage increase in price to simulate.",

                    "default": 10
                },

                "significant_only": {
                    "type": "boolean",

                    "description":
                        "Whether to include only statistically significant categories.",

                    "default": True
                }
            },

            "required": [
                "category_data"
            ]
        }
    },


    # ========================================================
    # TOOL 10
    # ========================================================

    {
        "name": "pricing_recommendation",

        "description":
            "Provide a pricing recommendation for a category using elasticity, statistical significance, current price, demand, and proposed price.",

        "input_schema": {
            "type": "object",

            "properties": {

                "category": {
                    "type": "string",

                    "description":
                        "Category being analyzed."
                },

                "current_price": {
                    "type": "number",

                    "description":
                        "Current price."
                },

                "current_demand": {
                    "type": "number",

                    "description":
                        "Current demand."
                },

                "elasticity": {
                    "type": "number",

                    "description":
                        "Price elasticity of demand."
                },

                "p_value": {
                    "type": "number",

                    "description":
                        "P-value of the elasticity estimate."
                },

                "proposed_price": {
                    "type": "number",

                    "description":
                        "Proposed new price."
                }
            },

            "required": [
                "category",
                "current_price",
                "current_demand",
                "elasticity",
                "p_value",
                "proposed_price"
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
        f"\nTotal tools: {len(TOOL_DEFINITIONS)}"
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
