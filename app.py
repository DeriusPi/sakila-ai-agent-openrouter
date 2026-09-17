import streamlit as st
import pandas as pd

from llm import ask_claude


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="Sakila AI Analyst",
    layout="wide",
    initial_sidebar_state="expanded"
)


# ============================================================
# SESSION STATE
# ============================================================

if "messages" not in st.session_state:
    st.session_state.messages = []


# ============================================================
# CSS
# ============================================================

st.markdown(
    """
    <style>

    .block-container {
        max-width: 1400px;
        padding-top: 2rem;
        padding-bottom: 3rem;
    }

    .agent-header {
        padding: 1.2rem 0 0.5rem 0;
    }

    .agent-subtitle {
        color: #777;
        font-size: 1rem;
        margin-bottom: 1.5rem;
    }

    .kpi-card {
        border: 1px solid rgba(128,128,128,0.25);
        border-radius: 10px;
        padding: 16px;
        min-height: 120px;
    }

    .kpi-label {
        font-size: 0.85rem;
        color: #777;
        margin-bottom: 8px;
    }

    .kpi-value {
        font-size: 1.7rem;
        font-weight: 600;
    }

    .kpi-description {
        font-size: 0.78rem;
        color: #888;
        margin-top: 6px;
    }

    .insight-box {
        border-left: 4px solid;
        padding: 10px 14px;
        margin: 8px 0;
        background: rgba(128,128,128,0.07);
        border-radius: 4px;
    }

    </style>
    """,
    unsafe_allow_html=True
)


# ============================================================
# HELPERS
# ============================================================

def render_kpis(kpis):

    if not kpis:
        return

    st.markdown("### Key Metrics")

    columns = st.columns(
        min(len(kpis), 4)
    )

    for index, kpi in enumerate(kpis):

        column = columns[
            index % len(columns)
        ]

        with column:

            label = kpi.get(
                "label",
                "Metric"
            )

            value = kpi.get(
                "value",
                "—"
            )

            description = kpi.get(
                "description",
                ""
            )

            st.markdown(
                f"""
                <div class="kpi-card">
                    <div class="kpi-label">
                        {label}
                    </div>
                    <div class="kpi-value">
                        {value}
                    </div>
                    <div class="kpi-description">
                        {description}
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )


def render_visualization(viz):

    if not isinstance(viz, dict):
        return

    chart_type = viz.get(
        "type",
        "bar"
    )

    title = viz.get(
        "title",
        "Visualization"
    )

    description = viz.get(
        "description",
        ""
    )

    data = viz.get(
        "data",
        []
    )

    if not isinstance(data, list) or not data:
        return

    df = pd.DataFrame(data)

    if df.empty:
        return

    st.markdown(
        f"### {title}"
    )

    if description:
        st.caption(description)

    x_key = viz.get(
        "x_key"
    )

    y_key = viz.get(
        "y_key"
    )

    if chart_type == "bar":

        if x_key in df.columns and y_key in df.columns:

            chart_df = df[
                [x_key, y_key]
            ].copy()

            chart_df = chart_df.set_index(
                x_key
            )

            st.bar_chart(
                chart_df
            )

    elif chart_type == "line":

        if x_key in df.columns and y_key in df.columns:

            chart_df = df[
                [x_key, y_key]
            ].copy()

            chart_df = chart_df.set_index(
                x_key
            )

            st.line_chart(
                chart_df
            )

    elif chart_type == "pie":

        if x_key in df.columns and y_key in df.columns:

            pie_df = df[
                [x_key, y_key]
            ].copy()

            st.bar_chart(
                pie_df.set_index(
                    x_key
                )
            )

    else:

        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True
        )


def render_table(table):

    if not isinstance(table, dict):
        return

    title = table.get(
        "title",
        "Data"
    )

    rows = table.get(
        "rows",
        []
    )

    if not rows:
        return

    df = pd.DataFrame(rows)

    if df.empty:
        return

    st.markdown(
        f"### {title}"
    )

    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True
    )


def render_agent_response(result):

    if not isinstance(result, dict):
        st.markdown(str(result))
        return

    answer = result.get(
        "answer",
        ""
    )

    if answer:
        st.markdown(answer)

    kpis = result.get(
        "kpis",
        []
    )

    render_kpis(kpis)

    visualizations = result.get(
        "visualizations",
        []
    )

    for viz in visualizations:
        render_visualization(viz)

    tables = result.get(
        "tables",
        []
    )

    for table in tables:
        render_table(table)

    insights = result.get(
        "insights",
        []
    )

    if insights:

        st.markdown("### Key Findings")

        for insight in insights:

            st.markdown(
                f"""
                <div class="insight-box">
                    {insight}
                </div>
                """,
                unsafe_allow_html=True
            )

    trace = result.get(
        "tool_trace",
        []
    )

    if trace:

        with st.expander(
            "Agent activity"
        ):

            for item in trace:

                tool = item.get(
                    "tool",
                    "unknown"
                )

                status = item.get(
                    "status",
                    "unknown"
                )

                st.write(
                    f"Tool: `{tool}` — "
                    f"Status: **{status}**"
                )


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.markdown(
        "## Sakila AI Analyst"
    )

    st.caption(
        "AI-powered Business Intelligence"
    )

    st.divider()

    st.markdown(
        """
        **How it works**

        Ask a business question.

        The AI automatically:

        1. Understands your question
        2. Selects the required tools
        3. Queries the Sakila data
        4. Runs analysis / ML / simulation
        5. Generates the appropriate BI output
        """
    )

    st.divider()

    if st.button(
        "Clear conversation",
        use_container_width=True
    ):

        st.session_state.messages = []

        st.rerun()

    st.divider()

    st.caption(
        "Data: Sakila MySQL"
    )

    st.caption(
        "Agent: Claude"
    )


# ============================================================
# HEADER
# ============================================================

st.markdown(
    """
    <div class="agent-header">
        <h1>Sakila AI Analyst</h1>
        <div class="agent-subtitle">
            Ask questions about revenue, pricing, rentals,
            late returns, simulation, and policy optimization.
        </div>
    </div>
    """,
    unsafe_allow_html=True
)


# ============================================================
# SUGGESTED QUESTIONS
# ============================================================

st.markdown(
    "### Ask your data"
)

q1, q2, q3, q4 = st.columns(4)

with q1:

    if st.button(
        "Analyze revenue",
        use_container_width=True
    ):
        st.session_state.pending_question = (
            "Analyze the current revenue structure."
        )

with q2:

    if st.button(
        "Compare categories",
        use_container_width=True
    ):
        st.session_state.pending_question = (
            "Which categories generate the most late fee revenue?"
        )

with q3:

    if st.button(
        "Rental pricing",
        use_container_width=True
    ):
        st.session_state.pending_question = (
            "What is the average rental rate by category?"
        )

with q4:

    if st.button(
        "Optimize policy",
        use_container_width=True
    ):
        st.session_state.pending_question = (
            "What policy would maximize expected revenue?"
        )


st.divider()


# ============================================================
# CHAT HISTORY
# ============================================================

for message in st.session_state.messages:

    role = message.get(
        "role",
        "assistant"
    )

    with st.chat_message(role):

        if role == "user":

            st.markdown(
                message.get(
                    "content",
                    ""
                )
            )

        else:

            render_agent_response(
                message.get(
                    "content",
                    {}
                )
            )


# ============================================================
# INPUT
# ============================================================

pending_question = st.session_state.pop(
    "pending_question",
    None
)

question = st.chat_input(
    "Ask your business question..."
)

if pending_question and not question:
    question = pending_question


# ============================================================
# PROCESS QUESTION
# ============================================================

if question:

    st.session_state.messages.append(
        {
            "role": "user",
            "content": question
        }
    )

    with st.chat_message("user"):

        st.markdown(question)

    with st.chat_message("assistant"):

        with st.spinner(
            "Analyzing data..."
        ):

            try:

                result = ask_claude(
                    question
                )

            except Exception as e:

                result = {
                    "answer": (
                        "The agent encountered an error."
                    ),
                    "kpis": [],
                    "visualizations": [],
                    "tables": [],
                    "insights": [
                        str(e)
                    ],
                    "tool_trace": []
                }

        render_agent_response(
            result
        )

    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": result
        }
    )
