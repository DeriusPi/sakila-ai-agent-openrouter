# ============================================================
# SAKILA AI AGENT
# Claude + Tool Layer + BI Presentation Layer
# ============================================================

import os
import json
import re
from openai import OpenAI
from dotenv import load_dotenv
from tools.tool_definitions import (
    TOOL_DEFINITIONS,
    TOOL_FUNCTIONS
)


# ============================================================
# 1. CONFIG
# ============================================================

load_dotenv()

API_KEY = os.getenv("OPENROUTER_API_KEY")

if not API_KEY:
    raise RuntimeError("OPENROUTER_API_KEY not found.")

client = OpenAI(
    api_key=API_KEY,
    base_url="https://openrouter.ai/api/v1"
)

MODEL = "nvidia/nemotron-3-super-120b-a12b:free"

def convert_tools_to_openai_format(tools):
    return [
        {
            "type": "function",
            "function": {
                "name": tool["name"],
                "description": tool["description"],
                "parameters": tool["input_schema"]
            }
        }
        for tool in tools
    ]


OPENAI_TOOL_DEFINITIONS = convert_tools_to_openai_format(
    TOOL_DEFINITIONS
)

# ============================================================
# 2. MODE DETECTION
# ============================================================

def detect_mode(user_question):
    """
    Automatically determine the main task type.

    ANALYSIS:
        User wants to understand existing data.

    OPTIMIZATION:
        User wants a policy / decision / recommendation.

    BOTH:
        User wants analysis followed by optimization.
    """

    q = user_question.lower().strip()

    optimization_keywords = [
        "recommend",
        "recommendation",
        "best policy",
        "optimal",
        "optimize",
        "optimization",
        "should we",
        "what policy",
        "which policy",
        "what fee should",
        "what price should",
        "nên chọn",
        "nên áp dụng",
        "nên đặt",
        "nên để",
        "nên dùng",
        "tối ưu",
        "tối ưu hóa",
        "đề xuất",
        "khuyến nghị",
        "chính sách nào",
        "mức phí nào",
        "giá nào",
        "nên tăng",
        "nên giảm"
    ]

    simulation_keywords = [
        "simulate",
        "simulation",
        "scenario",
        "what happens if",
        "what if",
        "impact of",
        "change the fee",
        "change fee",
        "thay đổi phí",
        "nếu tăng phí",
        "nếu giảm phí",
        "nếu phí",
        "mô phỏng",
        "kịch bản"
    ]

    analysis_keywords = [
        "analyze",
        "analysis",
        "why",
        "which",
        "what is",
        "how much",
        "how many",
        "percentage",
        "average",
        "revenue",
        "late fee",
        "late return",
        "category",
        "compare",
        "phân tích",
        "tại sao",
        "bao nhiêu",
        "chiếm bao nhiêu",
        "trung bình",
        "doanh thu",
        "phí trễ",
        "trả trễ",
        "danh mục",
        "so sánh",
        "thống kê"
    ]

    has_optimization = any(
        keyword in q
        for keyword in optimization_keywords
    )

    has_simulation = any(
        keyword in q
        for keyword in simulation_keywords
    )

    has_analysis = any(
        keyword in q
        for keyword in analysis_keywords
    )

    if has_optimization and (
        has_analysis
        or has_simulation
    ):
        return "BOTH"

    if has_optimization:
        return "OPTIMIZATION"

    return "ANALYSIS"


# ============================================================
# 3. MODE INSTRUCTIONS
# ============================================================

def build_mode_instruction(mode):
    """
    Add task-specific instructions without removing
    the main BI agent behavior.
    """

    if mode == "OPTIMIZATION":
        return """

============================================================
CURRENT MODE: OPTIMIZATION
============================================================

The user is asking for a decision, policy, fee, price,
duration, or recommendation.

Follow this pipeline:

1. Obtain the required actual data.
2. Generate predictions if necessary.
3. Simulate relevant scenarios.
4. Apply business constraints.
5. Compare feasible scenarios.
6. Use the optimization result.
7. Explain why the selected result is produced by
   the optimization pipeline.

IMPORTANT:

- Do not invent a policy.
- Do not manually choose a policy outside the optimization
  result.
- Do not replace the optimization objective with your own.
- Use the actual feasible scenarios returned by the tools.
- Clearly distinguish simulated / expected values from
  observed historical values.

For the final answer:

- Explain the analysis briefly.
- Explain the optimization result.
- State the recommendation only when it is explicitly
  supported by the optimization tool.

"""

    if mode == "BOTH":
        return """

============================================================
CURRENT MODE: ANALYSIS + OPTIMIZATION
============================================================

The user needs both business analysis and a decision.

First:

1. Analyze the current Sakila data.
2. Identify the relevant business drivers.
3. Obtain predictions if necessary.
4. Simulate policy scenarios.
5. Apply constraints.
6. Compare feasible scenarios.
7. Use the optimization pipeline.
8. Explain the resulting recommendation.

Do not skip the analysis section.

The final BI response should clearly distinguish:

- observed historical facts
- analytical interpretation
- simulated outcomes
- optimization recommendation

Never invent numerical results.

"""

    return """

============================================================
CURRENT MODE: ANALYSIS
============================================================

The user is asking to understand Sakila data.

Use the most appropriate analytical tools.

Prioritize:

- direct aggregation tools
- dedicated analysis tools
- prediction tools when prediction is explicitly requested

Do not use raw data when a dedicated aggregation tool exists.

Return only findings supported by the current tool results.

"""


# ============================================================
# 4. SYSTEM PROMPT
# ============================================================

SYSTEM_PROMPT = """

You are Sakila AI Analyst.

You are an AI business intelligence agent working with
the Sakila rental database.

IMPORTANT LANGUAGE RULE:

Always answer the user in VIETNAMESE.

Even if:

- the user asks in English
- database fields are in English
- tool results are in English

your final answer must be written in natural Vietnamese.

Keep technical terms such as KPI, revenue, simulation,
optimization, prediction, category when useful, but explain
them naturally in Vietnamese.

============================================================
CORE AGENT BEHAVIOR
============================================================

You are NOT simply a chatbot.

You operate as an autonomous BI analyst:

USER QUESTION
    ↓
UNDERSTAND INTENT
    ↓
SELECT APPROPRIATE TOOL(S)
    ↓
EXECUTE TOOL(S)
    ↓
ANALYZE ACTUAL RESULTS
    ↓
DECIDE WHAT BI ELEMENTS ARE USEFUL
    ↓
RETURN STRUCTURED BI RESPONSE

The user should NOT have to choose a tool or analysis page.

You decide which tools are necessary.

You may call multiple tools when necessary.

============================================================
CORE DATA RULES
============================================================

Always use actual tool results when the question requires
Sakila data.

Never invent:

- revenue
- rental counts
- percentages
- probabilities
- predictions
- prices
- policy outcomes
- chart values
- KPI values

Every numerical claim must be supported by tool results
obtained during the current agent process.

If the available tool results are insufficient:

CALL ANOTHER APPROPRIATE TOOL.

Never pretend that missing data exists.

Never use your general knowledge to fabricate Sakila values.

============================================================
DEDICATED AGGREGATION RULE
============================================================

For:

"What is the average rental rate by category?"

or equivalent questions such as:

- average rental rate for each category
- rental rate trung bình theo category
- giá thuê trung bình theo danh mục
- category nào có rental rate trung bình cao nhất

MUST call:

analyze_average_rental_rate_by_category

Do NOT use:

- get_film_data
- get_category_data
- raw film records

when the dedicated aggregation tool is available.

Use the actual aggregation result directly.

============================================================
AUTOMATIC TOOL SELECTION
============================================================

Examples:

"How much revenue do we make?"

→ analyze_revenue_structure

"Which category generates the most late fee revenue?"

→ analyze_revenue_drivers

"What is the average rental rate by category?"

→ analyze_average_rental_rate_by_category

"What percentage of rentals are late?"

→ analyze_late_fee_revenue

"Predict late return probability."

→ predict_late_probability

"Predict expected late days."

→ predict_expected_late_days

"What happens if we change the late fee?"

→ simulate_fee_policy

"When comparing several fee scenarios"

→ compare_scenarios

"What policy should we use?"

→ generate_policy_recommendation

"Apply business constraints."

→ apply_policy_constraints

Use multiple tools when the question requires them.

============================================================
FACT / INTERPRETATION / RECOMMENDATION
============================================================

FACT:

A statement directly supported by tool results.

INTERPRETATION:

A reasonable conclusion derived from the tool results.

RECOMMENDATION:

A decision explicitly produced by the optimization
pipeline.

Do not present interpretation as fact.

Do not invent recommendations.

============================================================
BI PRESENTATION
============================================================

The final answer must be designed for a BI dashboard UI.

You may provide:

1. KPI cards
2. Charts
3. Tables
4. Narrative explanation
5. Key insights

The Streamlit application will render these structures.

Do NOT describe imaginary visualizations in prose.

Instead, provide structured visualization data.

============================================================
VISUALIZATION SELECTION
============================================================

Use BAR charts for:

- category comparisons
- rankings
- revenue by category
- late fee revenue by category
- average rental rate by category
- fee scenario comparisons

Use LINE charts for:

- ordered numeric scenarios
- rental duration progression
- fee progression

Use PIE charts only for small part-to-whole comparisons.

Use TABLES when:

- multiple metrics need to be shown
- exact values matter
- there are many categories
- scenario details matter

Use KPI cards for the most important 1-4 numbers.

Do not create a chart when it adds no value.

============================================================
VISUALIZATION DATA INTEGRITY
============================================================

Only visualize data that actually exists in the tool results.

Never create:

- fake rows
- illustrative values
- estimated chart values
- manually invented percentages

Numbers inside visualization data MUST come directly from
tool results or calculations that are mathematically derived
from values returned by the current tools.

Preserve all relevant rows when the user asks for a full
breakdown.

For example, if a tool returns 16 categories and the user
asks for all categories, return all 16 categories.

============================================================
OPTIMIZATION RULES
============================================================

When the user asks what policy, fee, price, or duration
should be selected:

1. Obtain required data.
2. Generate predictions if necessary.
3. Simulate scenarios.
4. Apply business constraints.
5. Compare feasible scenarios.
6. Use the optimization result.
7. Explain the result.

Do NOT manually create an optimization objective.

Do NOT hardcode fee constraints.

Use constraints returned by the actual optimization tools.

If the tool says the feasible fee range is $0.96-$1.52/day,
use that result rather than inventing another range.

============================================================
SIMULATION LIMITATION
============================================================

The simulation may model demand response using a sensitivity
assumption.

The current simulation may hold late-return behavior constant
across fee scenarios while demand changes with the fee.

Therefore:

Do NOT claim that changing the fee causes customers to become
more or less likely to return late unless the simulation
explicitly models and measures that behavioral effect.

Use language such as:

- "the simulated result"
- "expected revenue"
- "under the current simulation assumptions"

when discussing simulation output.

============================================================
NUMERICAL INTEGRITY
============================================================

Do not mix values from different tools if they represent
different definitions of the same KPI without explaining the
difference.

For example, if two tools return different total revenue
values because they use different revenue definitions,
choose the tool appropriate to the user's question and use
its values consistently.

Do not silently combine incompatible datasets.

============================================================
FINAL RESPONSE FORMAT
============================================================

Return ONLY valid JSON.

Do not use markdown fences.

Do not write anything before or after the JSON.

Use exactly this top-level structure:

{
  "answer": "Giải thích ngắn gọn bằng tiếng Việt.",
  "kpis": [],
  "visualizations": [],
  "tables": [],
  "insights": []
}

============================================================
KPI FORMAT
============================================================

Example:

{
  "label": "Tổng doanh thu",
  "value": "$67,474.32",
  "description": "Tổng doanh thu theo kết quả phân tích."
}

The KPI "value" may be a string for display.

============================================================
VISUALIZATION FORMAT
============================================================

Example:

{
  "type": "bar",
  "title": "Doanh thu phí trả trễ theo category",
  "description": "So sánh doanh thu phí trả trễ giữa các category.",
  "x_key": "category",
  "y_key": "late_fee_revenue",
  "x_label": "Category",
  "y_label": "Late fee revenue",
  "value_prefix": "$",
  "value_suffix": "",
  "data": [
    {
      "category": "Sports",
      "late_fee_revenue": 1707.97
    }
  ]
}

Rules:

- type must be "bar", "line", or "pie"
- x_key and y_key must match keys in data
- numbers must remain numbers
- do not convert numerical chart data into strings

============================================================
TABLE FORMAT
============================================================

Example:

{
  "title": "Doanh thu theo category",
  "columns": [
    "Category",
    "Late fee revenue",
    "Average late fee"
  ],
  "rows": [
    {
      "Category": "Sports",
      "Late fee revenue": 1707.97,
      "Average late fee": 1.45
    }
  ]
}

============================================================
INSIGHTS
============================================================

Insights must be supported by tool results.

Good:

"Sports tạo ra $1,707.97 doanh thu phí trả trễ."

Bad:

"Sports chắc chắn có khách hàng trung thành hơn."

unless the available data explicitly supports that claim.

============================================================
EMPTY SECTIONS
============================================================

If a section is not useful:

"visualizations": []

or

"tables": []

or

"kpis": []

or

"insights": []

Do not fill sections with meaningless content.

============================================================
ANSWER STYLE
============================================================

The "answer" field should:

- be concise
- be natural Vietnamese
- directly answer the question
- mention the most important result
- distinguish observed vs simulated results
- not repeat the entire table

============================================================
CURRENT TASK
============================================================

Analyze the user's question using the available tools.

Automatically select and execute the necessary tools.

Use actual tool results.

Then return the BI response JSON.

"""


# ============================================================
# 5. TOOL EXECUTION
# ============================================================

def execute_tool(tool_name, tool_input):

    if tool_name not in TOOL_FUNCTIONS:
        return {
            "error": f"Unknown tool: {tool_name}"
        }

    function = TOOL_FUNCTIONS[tool_name]

    try:
        result = function(**tool_input)
        return result

    except Exception as e:
        return {
            "error": (
                f"Tool '{tool_name}' failed: "
                f"{str(e)}"
            )
        }


# ============================================================
# 6. SERIALIZE TOOL RESULT
# ============================================================

def serialize_tool_result(result):

    try:

        result_json = json.dumps(
            result,
            ensure_ascii=False,
            default=str
        )

        MAX_CHARS = 30000

        if len(result_json) <= MAX_CHARS:
            return result_json

        print(
            f"[Agent] Tool result too large: "
            f"{len(result_json):,} characters"
        )

        if isinstance(result, dict):

            compact = {}

            for key, value in result.items():

                if isinstance(value, list):

                    if len(value) > 100:

                        compact[key] = value[:100]

                        compact[
                            f"{key}_truncated"
                        ] = True

                    else:

                        compact[key] = value

                else:

                    compact[key] = value

            return json.dumps(
                compact,
                ensure_ascii=False,
                default=str
            )[:MAX_CHARS]

        return result_json[:MAX_CHARS]

    except Exception as e:

        return json.dumps(
            {
                "error": (
                    "Tool result could not be serialized."
                ),
                "details": str(e)
            },
            ensure_ascii=False
        )


# ============================================================
# 7. EXTRACT JSON
# ============================================================

def extract_json(text):

    if not text:
        return None

    text = text.strip()

    # --------------------------------------------------------
    # Direct JSON
    # --------------------------------------------------------

    try:
        return json.loads(text)

    except Exception:
        pass

    # --------------------------------------------------------
    # Markdown JSON fence
    # --------------------------------------------------------

    match = re.search(
        r"```(?:json)?\s*(.*?)\s*```",
        text,
        re.DOTALL | re.IGNORECASE
    )

    if match:

        try:
            return json.loads(
                match.group(1)
            )

        except Exception:
            pass

    # --------------------------------------------------------
    # Find first JSON object
    # --------------------------------------------------------

    start = text.find("{")

    if start >= 0:

        depth = 0
        in_string = False
        escape = False

        for i in range(
            start,
            len(text)
        ):

            char = text[i]

            if escape:

                escape = False
                continue

            if char == "\\" and in_string:

                escape = True
                continue

            if char == '"':

                in_string = not in_string
                continue

            if in_string:
                continue

            if char == "{":

                depth += 1

            elif char == "}":

                depth -= 1

                if depth == 0:

                    candidate = text[
                        start:i + 1
                    ]

                    try:

                        return json.loads(
                            candidate
                        )

                    except Exception:

                        break

    return None


# ============================================================
# 8. NORMALIZE BI RESPONSE
# ============================================================

def normalize_response(data):

    if not isinstance(data, dict):

        return {
            "answer": str(data),
            "kpis": [],
            "visualizations": [],
            "tables": [],
            "insights": []
        }

    answer = data.get(
        "answer",
        ""
    )

    if answer is None:
        answer = ""

    kpis = data.get(
        "kpis",
        []
    )

    visualizations = data.get(
        "visualizations",
        []
    )

    tables = data.get(
        "tables",
        []
    )

    insights = data.get(
        "insights",
        []
    )

    return {
        "answer": str(answer),

        "kpis": (
            kpis
            if isinstance(kpis, list)
            else []
        ),

        "visualizations": (
            visualizations
            if isinstance(
                visualizations,
                list
            )
            else []
        ),

        "tables": (
            tables
            if isinstance(tables, list)
            else []
        ),

        "insights": (
            insights
            if isinstance(insights, list)
            else []
        )
    }


# ============================================================
# 9. CLAUDE AGENT LOOP
# ============================================================

def ask_claude(user_question):

    mode = detect_mode(user_question)

    print(
        f"\n[Agent] Mode: {mode}"
    )

    system_prompt = (
        SYSTEM_PROMPT
        + build_mode_instruction(mode)
    )

    messages = [
        {
            "role": "system",
            "content": system_prompt
        },
        {
            "role": "user",
            "content": user_question
        }
    ]

    tool_trace = []

    MAX_TOOL_ROUNDS = 12
    tool_round = 0

    while True:

        if tool_round >= MAX_TOOL_ROUNDS:

            return {
                "answer": (
                    "Agent đã thực hiện quá nhiều bước "
                    "phân tích liên tiếp. Vui lòng thử "
                    "câu hỏi cụ thể hơn."
                ),
                "kpis": [],
                "visualizations": [],
                "tables": [],
                "insights": [],
                "tool_trace": tool_trace
            }

        response = client.chat.completions.create(

            model=MODEL,

            messages=messages,

            max_tokens=4096,

            tools=OPENAI_TOOL_DEFINITIONS,

            tool_choice="auto"
        )

        message = response.choices[0].message
        # ====================================================
        # TOOL USE
        # ====================================================

        if message.tool_calls:

            tool_round += 1

            # Preserve assistant tool-call message
            messages.append(
                {
                    "role": "assistant",
                    "content": message.content,
                    "tool_calls": [
                        {
                            "id": tool_call.id,
                            "type": "function",
                            "function": {
                                "name": tool_call.function.name,
                                "arguments": tool_call.function.arguments
                            }
                        }
                        for tool_call in message.tool_calls
                    ]
                }
            )

            for tool_call in message.tool_calls:

                tool_name = tool_call.function.name

                try:
                    tool_input = json.loads(
                        tool_call.function.arguments
                    )
                except Exception:

                    tool_input = {}

                print(
                    f"\n[Agent] Calling tool: "
                    f"{tool_name}"
                )

                print(
                    f"[Agent] Input: "
                    f"{tool_input}"
                )

                result = execute_tool(
                    tool_name,
                    tool_input
                )

                tool_trace.append(
                    {
                        "tool": tool_name,
                        "input": tool_input,
                        "status": (
                            "error"
                            if (
                                isinstance(result, dict)
                                and "error" in result
                            )
                            else "success"
                        )
                    }
                )

                print(
                    "[Agent] Tool completed."
                )

                result_json = serialize_tool_result(
                    result
                )

                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": result_json
                    }
                )

            continue

        # ====================================================
        # FINAL RESPONSE
        # ====================================================

        raw_answer = (
            message.content or ""
        ).strip()

        parsed = extract_json(
            raw_answer
        )

        if parsed is None:

            parsed = {
                "answer": raw_answer,
                "kpis": [],
                "visualizations": [],
                "tables": [],
                "insights": []
            }

        result = normalize_response(
            parsed
        )

        result["tool_trace"] = tool_trace

        return result
        # ----------------------------------------------------
        # Claude failed to return JSON
        # ----------------------------------------------------

        if parsed is None:

            parsed = {
                "answer": raw_answer,
                "kpis": [],
                "visualizations": [],
                "tables": [],
                "insights": []
            }

        result = normalize_response(
            parsed
        )

        result["tool_trace"] = tool_trace

        return result


# ============================================================
# 10. TERMINAL INTERFACE
# ============================================================

def main():

    print("=" * 70)
    print("SAKILA AI AGENT")
    print("=" * 70)

    print(
        "\nMode: Automatic"
    )

    print(
        "Language: Vietnamese"
    )

    question = input(
        "\nAsk Sakila AI Analyst: "
    )

    result = ask_claude(
        question
    )

    print(
        "\n" + "=" * 70
    )

    print(
        "ANSWER"
    )

    print(
        "=" * 70
    )

    print(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2
        )
    )


# ============================================================
# 11. ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()

