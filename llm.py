# ============================================================
# SAKILA AI AGENT
# LLM (OpenRouter or Anthropic) + Tool Layer + BI Presentation Layer
# ============================================================
#
# What changed in this version (summary)
# --------------------------------------
# - Works with OpenRouter (default, OpenAI-compatible API, same as the
#   deployed Streamlit app) OR Anthropic, chosen by environment/secrets.
# - The API client is created lazily: a missing key no longer crashes
#   `import llm` (which used to take down the whole Streamlit app,
#   including the Overview page).
# - Retries with back-off on 429 / 5xx / timeouts and optional fallback
#   models (free OpenRouter models are frequently rate limited).
# - Tool calls are validated: unknown arguments are dropped, missing
#   required arguments return a clear error to the model, broken JSON
#   arguments are reported instead of silently becoming {}.
# - Tool results are converted to real JSON numbers (Decimal/datetime
#   used to be sent as strings).
# - When the round limit is reached the model is asked for a final
#   answer instead of returning an error.
# - Non-JSON final answers get one repair attempt.
# - If the model answers with numbers without calling any tool, it is
#   asked once to call the tools first (prevents invented figures).
# - Optional chat history for follow-up questions.
# - KPI values are cross-checked against the numbers returned by tools
#   ("data_check" in the result).
# - An "error" activity event is emitted on failure.
# ============================================================

import inspect
import json
import os
import re
import time
from datetime import date, datetime
from decimal import Decimal

from dotenv import load_dotenv

from tools.tool_definitions import (
    TOOL_ALIASES,
    TOOL_DEFINITIONS,
    TOOL_FUNCTIONS,
)


# ============================================================
# 1. CONFIG
# ============================================================

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

DEFAULT_OPENROUTER_MODEL = "nvidia/nemotron-3-super-120b-a12b:free"
DEFAULT_ANTHROPIC_MODEL = "claude-sonnet-4-5"

MAX_TOOL_ROUNDS = 8
MAX_TOOL_RESULT_CHARS = 30000
MAX_HISTORY_TURNS = 6
LLM_MAX_RETRIES = 3
LLM_MAX_TOKENS = 4096


def _setting(name, default=None):
    """Environment variable first, then Streamlit secrets."""

    value = os.getenv(name)

    if value not in (None, ""):
        return value

    try:
        import streamlit as st

        if name in st.secrets:
            return str(st.secrets[name])
    except Exception:
        pass

    return default


def get_provider():
    """
    'openrouter' or 'anthropic'.

    LLM_PROVIDER wins if set; otherwise OpenRouter is used when
    OPENROUTER_API_KEY exists, else Anthropic when ANTHROPIC_API_KEY
    exists.
    """

    provider = (_setting("LLM_PROVIDER") or "").strip().lower()

    if provider in {"openrouter", "anthropic"}:
        return provider

    if _setting("OPENROUTER_API_KEY"):
        return "openrouter"

    if _setting("ANTHROPIC_API_KEY"):
        return "anthropic"

    return "openrouter"


def get_models():
    """Primary model followed by optional fallback models."""

    provider = get_provider()

    if provider == "anthropic":
        primary = _setting("ANTHROPIC_MODEL", DEFAULT_ANTHROPIC_MODEL)
        fallbacks = _setting("ANTHROPIC_FALLBACK_MODELS", "")
    else:
        primary = _setting("OPENROUTER_MODEL", DEFAULT_OPENROUTER_MODEL)
        fallbacks = _setting("OPENROUTER_FALLBACK_MODELS", "")

    models = [primary]

    for model in str(fallbacks or "").split(","):
        model = model.strip()
        if model and model not in models:
            models.append(model)

    return models


def get_model_label():
    """Human readable model name for the UI."""

    return f"{get_models()[0]} ({get_provider()})"


# Kept for backward compatibility with code that imported MODEL.
MODEL = get_models()[0]


# ============================================================
# 2. MODE DETECTION
# ============================================================

def detect_mode(user_question):
    """
    ANALYSIS:     understand existing data
    OPTIMIZATION: policy / decision / recommendation
    BOTH:         analysis followed by optimization
    """

    q = str(user_question or "").lower().strip()

    optimization_keywords = [
        "recommend", "recommendation", "best policy", "optimal",
        "optimize", "optimise", "optimization", "should we",
        "what policy", "which policy", "what fee should",
        "what price should", "maximize", "maximise",
        "nên chọn", "nên áp dụng", "nên đặt", "nên để", "nên dùng",
        "tối ưu", "tối ưu hóa", "đề xuất", "khuyến nghị",
        "chính sách nào", "mức phí nào", "giá nào", "nên tăng",
        "nên giảm", "tối đa hóa",
    ]

    simulation_keywords = [
        "simulate", "simulation", "scenario", "what happens if",
        "what if", "impact of", "change the fee", "change fee",
        "thay đổi phí", "nếu tăng phí", "nếu giảm phí", "nếu phí",
        "mô phỏng", "kịch bản",
    ]

    analysis_keywords = [
        "analyze", "analyse", "analysis", "why", "which", "what is",
        "how much", "how many", "percentage", "average", "revenue",
        "late fee", "late return", "category", "compare",
        "phân tích", "tại sao", "bao nhiêu", "chiếm bao nhiêu",
        "trung bình", "doanh thu", "phí trễ", "trả trễ", "danh mục",
        "so sánh", "thống kê", "tỷ lệ",
    ]

    has_optimization = any(k in q for k in optimization_keywords)
    has_simulation = any(k in q for k in simulation_keywords)
    has_analysis = any(k in q for k in analysis_keywords)

    if has_optimization and (has_analysis or has_simulation):
        return "BOTH"

    if has_optimization:
        return "OPTIMIZATION"

    return "ANALYSIS"


# ============================================================
# 3. MODE INSTRUCTIONS
# ============================================================

def build_mode_instruction(mode):

    if mode == "OPTIMIZATION":
        return """

============================================================
CURRENT MODE: OPTIMIZATION
============================================================

The user is asking for a decision, policy, fee, price,
duration, or recommendation.

Pipeline:

1. Obtain the required actual data (get_business_kpis,
   analyze_average_rental_rate_by_category, get_customer_summary).
2. Call generate_policy_recommendation (it runs scenarios,
   constraints and optimization internally).
3. Explain the result.

- Do not invent a policy or choose one outside the tool result.
- Use the feasible scenarios returned by the tools.
- Clearly separate simulated / expected values from observed
  historical values.
"""

    if mode == "BOTH":
        return """

============================================================
CURRENT MODE: ANALYSIS + OPTIMIZATION
============================================================

1. Analyze the current Sakila data with the data/analysis tools.
2. Identify the relevant business drivers.
3. Call generate_policy_recommendation (or compare_scenarios when
   the user only wants a comparison).
4. Explain the resulting recommendation.

Do not skip the analysis section. Clearly distinguish:
observed facts / interpretation / simulated outcomes /
optimization recommendation. Never invent numerical results.
"""

    return """

============================================================
CURRENT MODE: ANALYSIS
============================================================

Use the most appropriate analytical tools (aggregation tools
first). Return only findings supported by the current tool
results.
"""


# ============================================================
# 4. SYSTEM PROMPT
# ============================================================

SYSTEM_PROMPT = """
You are Sakila AI Analyst, an AI business intelligence agent working
with the Sakila DVD-rental MySQL database.

LANGUAGE RULE
Always answer in natural VIETNAMESE, even if the question or the tool
results are in English. Technical terms (KPI, revenue, simulation,
category...) may be kept when useful.

============================================================
CORE AGENT BEHAVIOR
============================================================
USER QUESTION -> understand intent -> select tool(s) -> execute ->
analyse ACTUAL results -> return a structured BI response.
The user never chooses tools; you do. Call several tools if needed.

============================================================
CORE DATA RULES (VERY IMPORTANT)
============================================================
- Every number in your answer (revenue, counts, percentages,
  probabilities, predictions, prices, chart values, KPI values) MUST
  come from tool results of THIS conversation, or be a simple
  arithmetic derivation of them.
- If the tool results are insufficient: CALL ANOTHER TOOL.
- Never use general knowledge to fabricate Sakila values.
- Use the totals returned by the tools. Do NOT re-add long lists
  yourself when the tool already returns the total.
- Keep the tools' definitions consistent:
    total revenue     = SUM(payment.amount)
    late-fee revenue  = SUM(GREATEST(payment.amount - rental_rate, 0))
    rental revenue    = total revenue - late-fee revenue
    late rental       = returned after rental_date + rental_duration days
    late-return rate  = late rentals / completed (returned) rentals
    store             = physical store of the rented copy (inventory)
- Sakila payments exist only for 2005-05, 2005-06, 2005-07, 2005-08 and
  2006-02. If a period has no data, say so; do not invent values.
- customer_late_rate for ML / simulation / optimization tools is a
  RATIO between 0 and 1 (0.512 means 51.2%).

============================================================
TOOL SELECTION GUIDE
============================================================
Headline KPIs, any "how much / how many / what %" question, or KPIs for
one store / one category / one period
  -> get_business_kpis (filters: category, store_id, start_date, end_date)

Revenue for a time period, trend, month/quarter/year comparison,
"which month has the highest revenue", revenue by category in a period
  -> get_revenue_by_time (start_date, end_date, group_by)
     e.g. "Revenue from May to July 2005" -> start_date=2005-05-01,
     end_date=2005-07-31, group_by=month
     "Which category earned most in May?" -> start 2005-05-01,
     end 2005-05-31, group_by=category
  Do NOT use analyze_revenue_structure for time comparisons.

Revenue structure / rental vs late fee split
  -> analyze_revenue_structure
Average rental rate by category
  -> analyze_average_rental_rate_by_category (all 16 categories)
Late fees by category / which category drives late fees
  -> analyze_late_fee_revenue or analyze_late_fee_contribution
What percentage of rentals are late / late-return rate
  -> get_business_kpis (or analyze_late_fee_revenue for per-category)
Why are rentals late / drivers (duration, rate, category)
  -> analyze_revenue_drivers
Category comparison table (rentals, late rate, revenue)
  -> get_category_data
Store comparison -> get_store_data
Rental behaviour breakdown -> get_rental_summary
Films (top films, catalogue) -> get_film_catalog
Customers (late customers, one customer) -> get_customer_summary
Predict late probability -> predict_late_probability
Predict expected late days -> predict_expected_late_days
What happens if we change the late fee -> simulate_fee_policy
Compare several fee / duration scenarios -> compare_scenarios
What policy / fee / duration should we use -> generate_policy_recommendation

When a profile is needed and the user gave none, use:
- customer_late_rate = overall late_rate_pct / 100 from get_business_kpis
- rental_rate = the category average from
  analyze_average_rental_rate_by_category
- current_rental_duration = 5 unless the user says otherwise
and tell the user which assumptions you used.

============================================================
FACT / INTERPRETATION / RECOMMENDATION
============================================================
FACT: directly supported by tool results.
INTERPRETATION: reasonable conclusion derived from tool results.
RECOMMENDATION: only a decision produced by the optimization tools.
Never present interpretation as fact. Never invent recommendations.

============================================================
SIMULATION LIMITATION
============================================================
Simulations use a demand-sensitivity assumption and hold late-return
behaviour constant across fee scenarios. Do NOT claim that changing
the fee changes customers' lateness unless the tool measures it. Use
"kết quả mô phỏng", "doanh thu kỳ vọng", "theo giả định mô phỏng hiện
tại" for simulated values.

============================================================
BI PRESENTATION
============================================================
The Streamlit app renders KPI cards, charts, tables, insights.
- BAR: category comparisons, rankings, scenario comparisons
- LINE: time series (month, quarter), ordered numeric scenarios
- PIE: only small part-to-whole (e.g. rental vs late-fee revenue)
- TABLE: several metrics, exact values, many rows
- KPI cards: the 1-4 most important numbers
Only visualize data that exists in the tool results. Preserve all rows
when the user asks for a full breakdown (e.g. all 16 categories).

============================================================
FINAL RESPONSE FORMAT
============================================================
Return ONLY one valid JSON object. No markdown fences. No text before or
after the JSON. Structure:

{
  "answer": "Giải thích ngắn gọn bằng tiếng Việt.",
  "kpis": [
    {"label": "Tên KPI", "value": "$0,000.00", "description": "Nguồn / ý nghĩa"}
  ],
  "visualizations": [
    {
      "type": "bar",
      "title": "Tiêu đề biểu đồ",
      "description": "Mô tả ngắn",
      "x_key": "category",
      "y_key": "late_fee_revenue",
      "x_label": "Category",
      "y_label": "Late fee revenue",
      "value_prefix": "$",
      "value_suffix": "",
      "data": [{"category": "<tên>", "late_fee_revenue": 0.0}]
    }
  ],
  "tables": [
    {"title": "Tiêu đề", "columns": ["Cột A", "Cột B"],
     "rows": [{"Cột A": "...", "Cột B": 0.0}]}
  ],
  "insights": ["Nhận định ngắn dựa trên dữ liệu tool."]
}

Rules:
- The example values above are placeholders - never copy them.
- type must be "bar", "line" or "pie"; x_key and y_key must be keys in
  every data row; chart numbers must be JSON numbers (not strings).
- Use [] for sections that add no value.
- "answer" is concise, directly answers the question, mentions the
  key result, distinguishes observed vs simulated values, and does not
  repeat the whole table.
"""


# ============================================================
# 5. JSON-SAFE CONVERSION
# ============================================================

def to_jsonable(value):
    """Decimal -> float, datetime -> ISO string, numpy -> python."""

    if isinstance(value, Decimal):
        return float(value)

    if isinstance(value, (datetime, date)):
        return value.isoformat(sep=" ") if isinstance(value, datetime) \
            else value.isoformat()

    if isinstance(value, dict):
        return {str(k): to_jsonable(v) for k, v in value.items()}

    if isinstance(value, (list, tuple, set)):
        return [to_jsonable(v) for v in value]

    # numpy scalars
    if hasattr(value, "item") and callable(getattr(value, "item")):
        try:
            return value.item()
        except Exception:
            pass

    return value


# ============================================================
# 6. TOOL EXECUTION
# ============================================================

_REQUIRED_BY_TOOL = {
    tool["name"]: list(tool["input_schema"].get("required", []))
    for tool in TOOL_DEFINITIONS
}


def execute_tool(tool_name, tool_input):
    """
    Run a registered tool safely. Always returns a dict or list.
    Errors are returned as {"error": "..."} so the model can react.
    """

    original_name = tool_name
    tool_name = TOOL_ALIASES.get(tool_name, tool_name)

    if tool_name not in TOOL_FUNCTIONS:
        return {
            "error": f"Unknown tool: {original_name}",
            "available_tools": sorted(
                t["name"] for t in TOOL_DEFINITIONS
            ),
        }

    if tool_input is None:
        tool_input = {}

    if not isinstance(tool_input, dict):
        return {
            "error": (
                f"Arguments for '{original_name}' must be a JSON object."
            )
        }

    function = TOOL_FUNCTIONS[tool_name]
    signature = inspect.signature(function)
    accepts_kwargs = any(
        p.kind == inspect.Parameter.VAR_KEYWORD
        for p in signature.parameters.values()
    )

    clean_input = {}
    ignored = []

    for key, value in tool_input.items():
        if accepts_kwargs or key in signature.parameters:
            if value is not None:
                clean_input[key] = value
        else:
            ignored.append(key)

    missing = [
        name
        for name in _REQUIRED_BY_TOOL.get(tool_name, [])
        if name not in clean_input
    ]

    if missing:
        return {
            "error": (
                f"Tool '{original_name}' is missing required argument(s): "
                + ", ".join(missing)
                + ". Obtain them from another tool (e.g. get_business_kpis, "
                "analyze_average_rental_rate_by_category) and call again."
            ),
            "ignored_arguments": ignored,
        }

    try:
        result = function(**clean_input)
    except Exception as exc:  # noqa: BLE001 - report to the model
        return {
            "error": f"Tool '{original_name}' failed: {exc}",
            "arguments_used": to_jsonable(clean_input),
        }

    result = to_jsonable(result)

    if ignored and isinstance(result, dict):
        result = {
            **result,
            "_ignored_arguments": ignored,
        }

    return result


def is_error_result(result):
    return isinstance(result, dict) and "error" in result


# ============================================================
# 7. SERIALIZE TOOL RESULT
# ============================================================

def _compact(value, max_items):
    if isinstance(value, list):
        if len(value) > max_items:
            return {
                "_items": [_compact(v, max_items) for v in value[:max_items]],
                "_truncated": True,
                "_total_items": len(value),
                "_note": (
                    f"Only the first {max_items} of {len(value)} items are "
                    "shown. Do NOT compute totals from this partial list; "
                    "use an aggregated tool instead."
                ),
            }
        return [_compact(v, max_items) for v in value]

    if isinstance(value, dict):
        return {k: _compact(v, max_items) for k, v in value.items()}

    return value


def serialize_tool_result(result):

    try:
        result_json = json.dumps(
            result, ensure_ascii=False, default=str
        )

        if len(result_json) <= MAX_TOOL_RESULT_CHARS:
            return result_json

        print(
            f"[Agent] Tool result too large: {len(result_json):,} chars"
        )

        for max_items in (100, 50, 25, 10):
            compact_json = json.dumps(
                _compact(result, max_items),
                ensure_ascii=False,
                default=str,
            )
            if len(compact_json) <= MAX_TOOL_RESULT_CHARS:
                return compact_json

        return json.dumps(
            {
                "error": (
                    "Tool result is too large to send to the model. "
                    "Use a more aggregated tool or add filters."
                ),
                "size_chars": len(result_json),
            },
            ensure_ascii=False,
        )

    except Exception as exc:  # noqa: BLE001
        return json.dumps(
            {
                "error": "Tool result could not be serialized.",
                "details": str(exc),
            },
            ensure_ascii=False,
        )


# ============================================================
# 8. EXTRACT / NORMALIZE BI RESPONSE
# ============================================================

def extract_json(text):

    if not text:
        return None

    text = str(text).strip()

    # Remove <think>...</think> blocks some reasoning models emit
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()

    try:
        return json.loads(text)
    except Exception:
        pass

    match = re.search(
        r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL | re.IGNORECASE
    )

    if match:
        try:
            return json.loads(match.group(1))
        except Exception:
            pass

    start = text.find("{")

    while start >= 0:
        depth = 0
        in_string = False
        escape = False

        for i in range(start, len(text)):
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
                    candidate = text[start:i + 1]
                    try:
                        parsed = json.loads(candidate)
                        if isinstance(parsed, dict):
                            return parsed
                    except Exception:
                        pass
                    break

        start = text.find("{", start + 1)

    return None


_NUMBER_STRING = re.compile(r"^\s*[-+]?\$?\s*[-+]?[\d,]*\.?\d+\s*%?\s*$")


def _coerce_number(value):
    """'1,707.97' / '$1,707.97' / '51.2%' -> float; else unchanged."""

    if isinstance(value, (int, float)) or value is None:
        return value

    if isinstance(value, str) and _NUMBER_STRING.match(value):
        try:
            return float(
                value.replace("$", "").replace(",", "")
                .replace("%", "").strip()
            )
        except ValueError:
            return value

    return value


def _normalize_visualization(viz):
    if not isinstance(viz, dict):
        return None

    data = viz.get("data")

    if not isinstance(data, list) or not data:
        return None

    rows = [row for row in data if isinstance(row, dict)]

    if not rows:
        return None

    y_key = viz.get("y_key")
    x_key = viz.get("x_key")

    # Guess missing keys from the first row
    keys = list(rows[0].keys())

    if not x_key or x_key not in rows[0]:
        x_key = next(
            (k for k in keys if not isinstance(
                _coerce_number(rows[0][k]), (int, float))),
            keys[0],
        )

    if not y_key or y_key not in rows[0]:
        y_key = next(
            (k for k in keys if k != x_key and isinstance(
                _coerce_number(rows[0][k]), (int, float))),
            None,
        )

    clean_rows = []

    for row in rows:
        clean = dict(row)
        if y_key in clean:
            clean[y_key] = _coerce_number(clean[y_key])
        clean_rows.append(clean)

    chart_type = str(viz.get("type", "bar")).lower()

    if chart_type not in {"bar", "line", "pie"}:
        chart_type = "bar"

    return {
        **viz,
        "type": chart_type,
        "x_key": x_key,
        "y_key": y_key,
        "data": clean_rows,
    }


def _normalize_table(table):
    if not isinstance(table, dict):
        return None

    rows = table.get("rows", [])
    columns = table.get("columns", [])

    if not isinstance(rows, list) or not rows:
        return None

    # rows given as list of lists -> list of dicts
    if all(isinstance(r, (list, tuple)) for r in rows):
        if not columns:
            columns = [f"Col {i + 1}" for i in range(len(rows[0]))]
        rows = [dict(zip(columns, r)) for r in rows]

    rows = [r for r in rows if isinstance(r, dict)]

    if not rows:
        return None

    return {
        "title": table.get("title", "Data"),
        "columns": columns or list(rows[0].keys()),
        "rows": rows,
    }


def _normalize_kpi(kpi):
    if isinstance(kpi, dict):
        return {
            "label": str(kpi.get("label") or kpi.get("name") or "Metric"),
            "value": str(kpi.get("value", "—")),
            "description": str(kpi.get("description") or ""),
        }

    if isinstance(kpi, str) and kpi.strip():
        return {"label": "Metric", "value": kpi, "description": ""}

    return None


def _normalize_insight(insight):
    if isinstance(insight, str):
        return insight.strip() or None

    if isinstance(insight, dict):
        parts = [
            str(insight.get(k))
            for k in ("title", "text", "insight", "description")
            if insight.get(k)
        ]
        return " — ".join(parts) or json.dumps(insight, ensure_ascii=False)

    if insight is None:
        return None

    return str(insight)


def normalize_response(data):

    if not isinstance(data, dict):
        return {
            "answer": str(data or ""),
            "kpis": [],
            "visualizations": [],
            "tables": [],
            "insights": [],
        }

    def as_list(value):
        if value is None:
            return []
        if isinstance(value, list):
            return value
        return [value]

    answer = data.get("answer")

    if answer is None:
        answer = data.get("summary") or ""

    return {
        "answer": str(answer),
        "kpis": [
            k for k in (_normalize_kpi(x) for x in as_list(data.get("kpis")))
            if k
        ],
        "visualizations": [
            v for v in (
                _normalize_visualization(x)
                for x in as_list(data.get("visualizations"))
            )
            if v
        ],
        "tables": [
            t for t in (
                _normalize_table(x) for x in as_list(data.get("tables"))
            )
            if t
        ],
        "insights": [
            i for i in (
                _normalize_insight(x) for x in as_list(data.get("insights"))
            )
            if i
        ],
    }


# ============================================================
# 9. DATA CHECK (KPI values vs tool numbers)
# ============================================================

def _collect_numbers(value, bucket):
    if isinstance(value, bool):
        return
    if isinstance(value, (int, float)):
        bucket.add(round(float(value), 2))
        return
    if isinstance(value, dict):
        for v in value.values():
            _collect_numbers(v, bucket)
    elif isinstance(value, list):
        for v in value:
            _collect_numbers(v, bucket)


def check_kpis_against_tools(kpis, tool_results):
    """
    Returns a list of KPI labels whose numeric value could not be found
    in any tool result (tolerance for rounding / % <-> ratio).
    """

    numbers = set()

    for result in tool_results:
        _collect_numbers(result, numbers)

    if not numbers:
        return []

    unverified = []

    for kpi in kpis:
        raw = str(kpi.get("value", ""))
        found = re.findall(r"[-+]?\d[\d,]*\.?\d*", raw)

        if not found:
            continue

        value = float(found[0].replace(",", ""))
        candidates = {value, value / 100, value * 100}

        # handle "67.4K" / "1.2M" style
        if re.search(r"\d\s*[kK]\b", raw):
            candidates.add(value * 1000)
        if re.search(r"\d\s*[mM]\b", raw):
            candidates.add(value * 1_000_000)

        def matches(c):
            tolerance = max(0.011, abs(c) * 0.0005)
            if re.search(r"\d\s*[kKmM]\b", raw):
                tolerance = max(tolerance, abs(c) * 0.01)
            return any(abs(c - n) <= tolerance for n in numbers)

        if not any(matches(c) for c in candidates):
            unverified.append(kpi.get("label", raw))

    return unverified


# ============================================================
# 10. LLM PROVIDER ADAPTERS
# ============================================================

class LLMError(RuntimeError):
    pass


def _is_retryable(exc):
    status = getattr(exc, "status_code", None) or getattr(
        getattr(exc, "response", None), "status_code", None
    )

    if status in {408, 409, 425, 429, 500, 502, 503, 504, 529}:
        return True

    name = exc.__class__.__name__.lower()
    text = str(exc).lower()

    return any(
        token in name or token in text
        for token in (
            "timeout", "timed out", "connection", "rate limit",
            "ratelimit", "overloaded", "temporarily", "429",
            "502", "503", "504",
        )
    )


class OpenRouterAdapter:
    """OpenAI-compatible chat completions (OpenRouter)."""

    def __init__(self):
        from openai import OpenAI

        api_key = _setting("OPENROUTER_API_KEY")

        if not api_key:
            raise LLMError(
                "OPENROUTER_API_KEY not found. Add it to .env or to the "
                "Streamlit Cloud secrets."
            )

        headers = {}
        site = _setting("OPENROUTER_SITE_URL")
        if site:
            headers["HTTP-Referer"] = site
        headers["X-Title"] = _setting("OPENROUTER_APP_NAME", "Sakila AI Agent")

        self.client = OpenAI(
            api_key=api_key,
            base_url=_setting(
                "OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"
            ),
            default_headers=headers,
            timeout=float(_setting("LLM_TIMEOUT", 120)),
            max_retries=0,
        )

        self.tools = [
            {
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool["description"],
                    "parameters": tool["input_schema"],
                },
            }
            for tool in TOOL_DEFINITIONS
        ]

    def start(self, system_prompt, history, question):
        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(history)
        messages.append({"role": "user", "content": question})
        return messages

    def create(self, model, messages, allow_tools=True):
        kwargs = {
            "model": model,
            "messages": messages,
            "max_tokens": LLM_MAX_TOKENS,
            "temperature": 0.1,
        }

        if allow_tools:
            kwargs["tools"] = self.tools
            kwargs["tool_choice"] = "auto"

        response = self.client.chat.completions.create(**kwargs)

        if not getattr(response, "choices", None):
            error = getattr(response, "error", None)
            raise LLMError(f"Empty response from OpenRouter: {error}")

        return response

    def parse(self, response):
        message = response.choices[0].message
        text = message.content or ""

        calls = []

        for call in message.tool_calls or []:
            raw_args = call.function.arguments or "{}"
            args_error = None

            try:
                args = json.loads(raw_args) if raw_args.strip() else {}
            except Exception as exc:  # noqa: BLE001
                args = None
                args_error = f"Invalid JSON arguments: {exc}: {raw_args[:300]}"

            calls.append({
                "id": call.id,
                "name": call.function.name,
                "input": args,
                "args_error": args_error,
                "raw_args": raw_args,
            })

        return text, calls

    def append_assistant(self, messages, response, calls):
        message = response.choices[0].message
        messages.append({
            "role": "assistant",
            "content": message.content or "",
            "tool_calls": [
                {
                    "id": call["id"],
                    "type": "function",
                    "function": {
                        "name": call["name"],
                        "arguments": call["raw_args"] or "{}",
                    },
                }
                for call in calls
            ],
        })

    def append_tool_results(self, messages, results):
        for call_id, content in results:
            messages.append({
                "role": "tool",
                "tool_call_id": call_id,
                "content": content,
            })

    def append_text_turn(self, messages, assistant_text, user_text):
        if assistant_text:
            messages.append({"role": "assistant", "content": assistant_text})
        messages.append({"role": "user", "content": user_text})


class AnthropicAdapter:
    """Anthropic Messages API."""

    def __init__(self):
        import anthropic

        api_key = _setting("ANTHROPIC_API_KEY")

        if not api_key:
            raise LLMError(
                "ANTHROPIC_API_KEY not found. Add it to .env or to the "
                "Streamlit Cloud secrets."
            )

        self.client = anthropic.Anthropic(
            api_key=api_key,
            timeout=float(_setting("LLM_TIMEOUT", 120)),
            max_retries=0,
        )
        self.tools = TOOL_DEFINITIONS
        self.system_prompt = ""

    def start(self, system_prompt, history, question):
        self.system_prompt = system_prompt
        messages = list(history)
        messages.append({"role": "user", "content": question})
        return messages

    def create(self, model, messages, allow_tools=True):
        kwargs = {
            "model": model,
            "max_tokens": LLM_MAX_TOKENS,
            "system": self.system_prompt,
            "messages": messages,
            "tools": self.tools,
            "temperature": 0.1,
        }

        if not allow_tools:
            kwargs["tool_choice"] = {"type": "none"}

        return self.client.messages.create(**kwargs)

    def parse(self, response):
        text = "\n".join(
            block.text for block in response.content
            if getattr(block, "type", "") == "text"
        )

        calls = [
            {
                "id": block.id,
                "name": block.name,
                "input": block.input,
                "args_error": None,
                "raw_args": None,
            }
            for block in response.content
            if getattr(block, "type", "") == "tool_use"
        ]

        return text, calls

    def append_assistant(self, messages, response, calls):
        messages.append({"role": "assistant", "content": response.content})

    def append_tool_results(self, messages, results):
        messages.append({
            "role": "user",
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": call_id,
                    "content": content,
                }
                for call_id, content in results
            ],
        })

    def append_text_turn(self, messages, assistant_text, user_text):
        if assistant_text:
            messages.append({"role": "assistant", "content": assistant_text})

        last = messages[-1] if messages else None

        # Anthropic expects alternating roles: merge into the last user
        # turn (e.g. after tool_result blocks) instead of adding a
        # second consecutive user message.
        if last is not None and last.get("role") == "user":
            content = last.get("content")
            if isinstance(content, str):
                content = [{"type": "text", "text": content}]
            content = list(content) + [{"type": "text", "text": user_text}]
            last["content"] = content
        else:
            messages.append({"role": "user", "content": user_text})


_ADAPTER = None


def get_adapter():
    """Create the provider client lazily (not at import time)."""

    global _ADAPTER

    provider = get_provider()

    if _ADAPTER is None or _ADAPTER[0] != provider:
        adapter = (
            AnthropicAdapter() if provider == "anthropic"
            else OpenRouterAdapter()
        )
        _ADAPTER = (provider, adapter)

    return _ADAPTER[1]


def call_llm(adapter, messages, allow_tools=True, on_retry=None):
    """
    Call the model with retries and fallback models.
    Returns (response, model_used).
    """

    last_error = None

    for model in get_models():
        for attempt in range(1, LLM_MAX_RETRIES + 1):
            try:
                return adapter.create(model, messages, allow_tools), model

            except Exception as exc:  # noqa: BLE001
                last_error = exc
                retryable = _is_retryable(exc)

                print(
                    f"[Agent] LLM call failed (model={model}, "
                    f"attempt={attempt}): {exc}"
                )

                if on_retry:
                    on_retry(model, attempt, exc, retryable)

                if not retryable:
                    break  # try next model

                if attempt < LLM_MAX_RETRIES:
                    time.sleep(min(2 ** attempt, 10))

    raise LLMError(f"LLM request failed: {last_error}")


# ============================================================
# 11. AGENT LOOP
# ============================================================

def _history_messages(history):
    """
    Convert UI chat history into plain text turns
    (only the answer text of previous assistant messages).
    """

    messages = []

    for item in (history or [])[-MAX_HISTORY_TURNS * 2:]:
        if not isinstance(item, dict):
            continue

        role = item.get("role")
        content = item.get("content")

        if role == "assistant" and isinstance(content, dict):
            content = content.get("answer", "")

        if role not in {"user", "assistant"} or not content:
            continue

        text = str(content)[:1500]

        if messages and messages[-1]["role"] == role:
            messages[-1]["content"] += "\n" + text
        else:
            messages.append({"role": role, "content": text})

    # Must start with a user turn and alternate
    while messages and messages[0]["role"] != "user":
        messages.pop(0)

    if messages and messages[-1]["role"] == "user":
        messages.pop()

    return messages


def _has_data_numbers(text):
    return bool(re.search(r"(\$\s?\d)|(\d[\d,]*\.?\d*\s?%)|(\d{3,})", text))


def _error_response(message, tool_trace=None):
    return {
        "answer": message,
        "kpis": [],
        "visualizations": [],
        "tables": [],
        "insights": [],
        "tool_trace": tool_trace or [],
        "error": True,
    }


def ask_claude(user_question, activity_callback=None, history=None):
    """
    Run the BI agent for one question.

    Name kept as ask_claude() for compatibility with app.py even though
    the provider may be OpenRouter.

    history: optional list of {"role": "user"|"assistant",
             "content": str | result dict} from previous turns.
    """

    def emit_activity(event, **payload):
        if activity_callback is None:
            return
        try:
            activity_callback({"event": event, **payload})
        except Exception as callback_error:  # noqa: BLE001
            print(f"[Agent] Activity callback failed: {callback_error}")

    emit_activity("question_received", question=user_question)

    mode = detect_mode(user_question)
    print(f"\n[Agent] Mode: {mode}")
    emit_activity("mode", mode=mode)

    tool_trace = []
    tool_results_for_check = []

    try:
        adapter = get_adapter()
    except Exception as exc:  # noqa: BLE001
        emit_activity("error", error=str(exc))
        return _error_response(
            f"Không thể khởi tạo mô hình AI: {exc}", tool_trace
        )

    system_prompt = SYSTEM_PROMPT + build_mode_instruction(mode)
    messages = adapter.start(
        system_prompt, _history_messages(history), user_question
    )

    def on_retry(model, attempt, exc, retryable):
        emit_activity(
            "llm_retry",
            model=model,
            attempt=attempt,
            retryable=retryable,
            error=str(exc)[:300],
        )

    tool_round = 0
    round_limit_notice_sent = False
    nudged_for_tools = False
    repaired_json = False
    empty_retries = 0
    result_cache = {}
    model_used = get_models()[0]

    try:
        while True:

            allow_tools = tool_round < MAX_TOOL_ROUNDS

            if not allow_tools:
                emit_activity(
                    "next_step",
                    round=tool_round,
                    tool_count=len(tool_trace),
                    note="Round limit reached - asking for final answer",
                )
                if not round_limit_notice_sent:
                    round_limit_notice_sent = True
                    adapter.append_text_turn(
                        messages,
                        "",
                        "Bạn đã dùng đủ số vòng gọi tool. Hãy trả lời ngay "
                        "bằng JSON BI cuối cùng, chỉ dựa trên các kết quả "
                        "tool đã có.",
                    )

            response, model_used = call_llm(
                adapter, messages, allow_tools=allow_tools, on_retry=on_retry
            )

            text, calls = adapter.parse(response)

            # =================================================
            # TOOL USE
            # =================================================

            if calls and allow_tools:

                tool_round += 1

                emit_activity(
                    "agent_decision",
                    decision="tool_use",
                    round=tool_round,
                    tools=[call["name"] for call in calls],
                )

                adapter.append_assistant(messages, response, calls)

                results = []

                for call in calls:
                    tool_name = call["name"]
                    tool_input = call["input"]

                    print(f"\n[Agent] Calling tool: {tool_name}")
                    print(f"[Agent] Input: {tool_input}")

                    emit_activity(
                        "tool_selected",
                        tool=tool_name,
                        input=tool_input if tool_input is not None
                        else call["raw_args"],
                        round=tool_round,
                    )
                    emit_activity(
                        "tool_call",
                        tool=tool_name,
                        input=tool_input,
                        status="running",
                    )

                    if call["args_error"]:
                        result = {"error": call["args_error"]}
                    else:
                        cache_key = (
                            TOOL_ALIASES.get(tool_name, tool_name),
                            json.dumps(tool_input, sort_keys=True,
                                       default=str),
                        )
                        if cache_key in result_cache:
                            result = result_cache[cache_key]
                        else:
                            result = execute_tool(tool_name, tool_input)
                            result_cache[cache_key] = result

                    tool_status = (
                        "error" if is_error_result(result) else "success"
                    )

                    if tool_status == "success":
                        tool_results_for_check.append(result)

                    tool_trace.append({
                        "tool": tool_name,
                        "input": tool_input,
                        "status": tool_status,
                        **(
                            {"error": result.get("error")}
                            if tool_status == "error" else {}
                        ),
                    })

                    emit_activity(
                        "tool_completed",
                        tool=tool_name,
                        input=tool_input,
                        status=tool_status,
                        error=(
                            result.get("error")
                            if tool_status == "error" else None
                        ),
                    )

                    print("[Agent] Tool completed.")

                    result_json = serialize_tool_result(result)

                    preview = result_json
                    if len(preview) > 900:
                        preview = preview[:900] + "..."

                    emit_activity(
                        "tool_output",
                        tool=tool_name,
                        status=tool_status,
                        output=preview,
                    )

                    results.append((call["id"], result_json))

                adapter.append_tool_results(messages, results)

                emit_activity(
                    "next_step",
                    round=tool_round,
                    tool_count=len(results),
                )

                continue

            # =================================================
            # EMPTY RESPONSE (common with free models)
            # =================================================

            if not text.strip():
                empty_retries += 1

                if empty_retries <= 2:
                    emit_activity(
                        "llm_retry",
                        model=model_used,
                        attempt=empty_retries,
                        retryable=True,
                        error="Empty response from model",
                    )
                    adapter.append_text_turn(
                        messages,
                        "",
                        "Câu trả lời trước bị rỗng. Hãy gọi tool cần thiết "
                        "hoặc trả về JSON BI cuối cùng.",
                    )
                    continue

                raise LLMError("The model returned an empty response.")

            # =================================================
            # NUMBERS WITHOUT ANY TOOL CALL -> ask for tools once
            # =================================================

            if (
                not tool_trace
                and not nudged_for_tools
                and allow_tools
                and _has_data_numbers(text)
            ):
                nudged_for_tools = True

                emit_activity(
                    "next_step",
                    round=tool_round,
                    tool_count=0,
                    note="Answer had numbers without tool calls - "
                         "requesting tool use",
                )

                adapter.append_text_turn(
                    messages,
                    text,
                    "Câu trả lời trên có số liệu nhưng chưa gọi tool nào. "
                    "Hãy gọi các tool phù hợp để lấy số liệu thật từ "
                    "Sakila, rồi trả lời lại bằng JSON BI.",
                )
                continue

            # =================================================
            # FINAL RESPONSE
            # =================================================

            emit_activity(
                "synthesis_started",
                tool_count=len(tool_trace),
                rounds=tool_round,
            )

            parsed = extract_json(text)

            if parsed is None and not repaired_json:
                repaired_json = True

                emit_activity(
                    "llm_retry",
                    model=model_used,
                    attempt=1,
                    retryable=True,
                    error="Final answer was not valid JSON - repairing",
                )

                adapter.append_text_turn(
                    messages,
                    text,
                    "Hãy trả lại ĐÚNG MỘT object JSON hợp lệ theo cấu trúc "
                    "{answer, kpis, visualizations, tables, insights}, "
                    "không có markdown, không có chữ ngoài JSON. Giữ nguyên "
                    "các số liệu từ kết quả tool.",
                )

                response, model_used = call_llm(
                    adapter, messages, allow_tools=False, on_retry=on_retry
                )
                repaired_text, _ = adapter.parse(response)
                parsed = extract_json(repaired_text)

                if parsed is None and repaired_text.strip():
                    text = repaired_text

            if parsed is None:
                parsed = {"answer": text}

            result = normalize_response(parsed)
            result["tool_trace"] = tool_trace
            result["model"] = model_used
            result["mode"] = mode

            unverified = check_kpis_against_tools(
                result["kpis"], tool_results_for_check
            )

            if tool_results_for_check or result["kpis"]:
                result["data_check"] = {
                    "tool_calls": len(tool_trace),
                    "unverified_kpis": unverified,
                    "status": "ok" if not unverified else "warning",
                }

            emit_activity(
                "answer_ready",
                tool_count=len(tool_trace),
                has_kpis=bool(result.get("kpis")),
                has_visualizations=bool(result.get("visualizations")),
                has_tables=bool(result.get("tables")),
                has_insights=bool(result.get("insights")),
            )

            emit_activity(
                "completed",
                status="success",
                tool_count=len(tool_trace),
            )

            return result

    except Exception as exc:  # noqa: BLE001
        print(f"[Agent] Failed: {exc}")
        emit_activity("error", error=str(exc))

        message = str(exc)

        if "429" in message or "rate" in message.lower():
            hint = (
                "Mô hình AI đang bị giới hạn tần suất (rate limit) - thường "
                "gặp với model miễn phí trên OpenRouter. Vui lòng thử lại "
                "sau ít phút hoặc cấu hình OPENROUTER_FALLBACK_MODELS."
            )
        else:
            hint = "Agent không thể hoàn thành yêu cầu."

        return _error_response(f"{hint}\n\nChi tiết: {message}", tool_trace)


# Provider-neutral alias
ask_agent = ask_claude


# ============================================================
# 12. TERMINAL INTERFACE
# ============================================================

def main():

    print("=" * 70)
    print("SAKILA AI AGENT")
    print("=" * 70)
    print(f"\nModel: {get_model_label()}")
    print("Language: Vietnamese")

    question = input("\nAsk Sakila AI Analyst: ")

    result = ask_claude(
        question,
        activity_callback=lambda e: print("[Activity]", e.get("event")),
    )

    print("\n" + "=" * 70)
    print("ANSWER")
    print("=" * 70)
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
