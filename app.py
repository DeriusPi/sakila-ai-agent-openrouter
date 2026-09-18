import html
from datetime import datetime

import altair as alt
import pandas as pd
import streamlit as st

from llm import ask_claude

from tools.analysis.analyze_average_rental_rate_by_category import (
    analyze_average_rental_rate_by_category,
)
from tools.analysis.analyze_late_fee_contribution import (
    analyze_late_fee_contribution,
)
from tools.analysis.analyze_late_fee_dependency import (
    analyze_late_fee_dependency,
)
from tools.analysis.analyze_revenue_structure import analyze_revenue_structure
from tools.data.get_store_data import get_store_data
from tools.data.get_rental_data import get_rental_data

from tools.data.get_category_data import get_category_data
from tools.optimization.derive_fee_constraint import derive_fee_constraint
from tools.ml.predict_expected_late_days import predict_expected_late_days
from tools.ml.predict_late_probability import predict_late_probability
from tools.optimization.generate_policy_recommendation import (
    generate_policy_recommendation,
)
from tools.simulation.compare_scenarios import compare_scenarios
from tools.simulation.simulate_fee_policy import simulate_fee_policy


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="Sakila AI",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# SESSION STATE
# ============================================================

if "messages" not in st.session_state:
    st.session_state.messages = []

if "prediction_result" not in st.session_state:
    st.session_state.prediction_result = None

if "policy_result" not in st.session_state:
    st.session_state.policy_result = None

if "scenario_result" not in st.session_state:
    st.session_state.scenario_result = None

if "pred_category" not in st.session_state:
    st.session_state.pred_category = "Sci-Fi"

if "pred_late_rate" not in st.session_state:
    st.session_state.pred_late_rate = 28.5

if "pred_duration" not in st.session_state:
    st.session_state.pred_duration = 3

if "pred_rental_rate" not in st.session_state:
    st.session_state.pred_rental_rate = 2.99

if "pred_fee" not in st.session_state:
    st.session_state.pred_fee = 1.00


# ============================================================
# THEME / CSS
# ============================================================

st.markdown(
    '''
<style>
    @import 
url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;600&family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=swap');

    :root {
        --primary: #312E81;
        --primary-600: #4338CA;
        --primary-50: #EEF2FF;
        --primary-100: #E0E7FF;
        --slate-50: #F8FAFC;
        --slate-100: #F1F5F9;
        --slate-200: #E2E8F0;
        --slate-300: #CBD5E1;
        --slate-400: #94A3B8;
        --slate-500: #64748B;
        --slate-600: #475569;
        --slate-700: #334155;
        --slate-800: #1E293B;
        --slate-900: #0F172A;
    }

    html, body, [class*="css"] {
        font-family: "Inter", sans-serif;
    }

    .stApp {
        background: var(--slate-50);
        color: var(--slate-900);
    }

    #MainMenu, footer {
        visibility: hidden;
    }

    [data-testid="stHeader"] {
        background: transparent;
    }

    [data-testid="stToolbar"] {
        display: none;
    }

    [data-testid="stSidebar"] {
        width: 240px !important;
        min-width: 240px !important;
        background: #FFFFFF;
        border-right: 1px solid var(--slate-200);
    }

    [data-testid="stSidebar"] > div:first-child {
        padding: 0;
    }

    [data-testid="stSidebarContent"] {
        padding: 0 !important;
    }

    .block-container {
        max-width: 1440px;
        padding: 0 32px 40px 32px;
    }

    .material-symbols-outlined {
        font-family: "Material Symbols Outlined";
        font-weight: normal;
        font-style: normal;
        font-size: 19px;
        line-height: 1;
        letter-spacing: normal;
        text-transform: none;
        display: inline-block;
        white-space: nowrap;
        word-wrap: normal;
        direction: ltr;
        -webkit-font-feature-settings: "liga";
        -webkit-font-smoothing: antialiased;
    }

    .mono {
        font-family: "JetBrains Mono", monospace;
        font-variant-numeric: tabular-nums;
    }

    .sidebar-wrap {
        min-height: 100vh;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        padding: 0;
        background: #FFFFFF;
    }

    .brand-row {
        height: 64px;
        padding: 0 20px;
        display: flex;
        align-items: center;
        gap: 12px;
        border-bottom: 1px solid var(--slate-100);
    }

    .brand-logo-fallback {
            width: 32px;
            height: 32px;
            border-radius: 8px;
            background: #312E81;
            color: #FFFFFF;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 16px;
            font-weight: 600;
            flex-shrink: 0;
}

        .nav-section-title {
            padding: 16px 24px 8px 24px;
            font-family: "JetBrains Mono", monospace;
            font-size: 10px;
            font-weight: 500;
            color: #94A3B8;
            text-transform: uppercase;
            letter-spacing: .08em;
}

        .profile-avatar-fallback {
            width: 32px;
            height: 32px;
            border-radius: 50%;
            background: #E0E7FF;
            color: #4338CA;
            display: flex;
            align-items: center;
            justify-content: center;
            font-family: "JetBrains Mono", monospace;
            font-size: 10px;
            font-weight: 600;
            flex-shrink: 0;
}
}
    .brand-name {
        font-size: 14px;
        font-weight: 600;
        color: var(--slate-900);
        line-height: 1.05;
        letter-spacing: -0.02em;
    }

    .brand-badge {
        display: inline-block;
        margin-top: 4px;
        padding: 3px 6px;
        border-radius: 4px;
        background: var(--primary-50);
        border: 1px solid var(--primary-100);
        color: var(--primary-600);
        font-family: "JetBrains Mono", monospace;
        font-size: 9px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        line-height: 1;
    }

    .nav-section {
        padding: 16px 12px;
    }

    .nav-label {
        padding: 0 12px 8px 12px;
        font-family: "JetBrains Mono", monospace;
        font-size: 10px;
        font-weight: 500;
        color: var(--slate-400);
        text-transform: uppercase;
        letter-spacing: 0.08em;
    }

    .nav-link {
        display: flex;
        align-items: center;
        gap: 11px;
        padding: 9px 12px;
        margin-bottom: 2px;
        border-radius: 6px;
        color: var(--slate-600);
        text-decoration: none !important;
        font-size: 13px;
        font-weight: 500;
        transition: 0.15s ease;
    }

    .nav-link:hover {
        background: var(--slate-50);
        color: var(--slate-900);
    }

    .nav-link.active {
        background: var(--primary-50);
        color: var(--primary-600);
        font-weight: 600;
        border-left: 2px solid var(--primary-600);
    }

    .nav-link .material-symbols-outlined {
        color: var(--slate-400);
    }

    .nav-link.active .material-symbols-outlined {
        color: var(--primary-600);
    }

    .sidebar-bottom {
        border-top: 1px solid var(--slate-100);
        padding: 12px;
    }

    .activity-nav {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 9px 12px;
        border-radius: 6px;
        color: var(--slate-600);
        text-decoration: none !important;
        font-size: 13px;
        font-weight: 500;
    }

    .activity-nav:hover {
        background: var(--slate-50);
    }

    .activity-left {
        display: flex;
        align-items: center;
        gap: 11px;
    }

    .activity-dot {
        width: 7px;
        height: 7px;
        border-radius: 50%;
        background: var(--primary-600);
    }

    .profile-card {
        display: flex;
        align-items: center;
        gap: 10px;
        margin-top: 10px;
        padding: 9px 8px;
        border: 1px solid var(--slate-200);
        border-radius: 6px;
        background: #FFFFFF;
    }

    .profile-avatar {
        width: 32px;
        height: 32px;
        border-radius: 50%;
        object-fit: cover;
        ring: 1px solid var(--slate-200);
    }

    .profile-name {
        font-size: 12px;
        font-weight: 600;
        color: var(--slate-900);
        line-height: 1.1;
    }

    .profile-role {
        font-size: 11px;
        color: var(--slate-400);
        margin-top: 2px;
    }

    .top-header {
        position: sticky;
        top: 0;
        z-index: 99;
        height: 64px;
        margin: 0 -32px;
        padding: 0 32px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        background: rgba(255,255,255,0.96);
        border-bottom: 1px solid rgba(226,232,240,0.9);
        backdrop-filter: blur(10px);
    }

    .system-badge {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        padding: 6px 10px;
        background: rgba(241,245,249,.75);
        border: 1px solid rgba(226,232,240,.9);
        border-radius: 999px;
        color: var(--slate-600);
        font-size: 11px;
    }

    .status-dot {
        width: 6px;
        height: 6px;
        border-radius: 50%;
        background: var(--primary-600);
    }

    .header-actions {
        display: flex;
        align-items: center;
        gap: 8px;
        flex-wrap: wrap;
        justify-content: flex-end;
    }

    .filter-chip {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 7px 11px;
        border-radius: 6px;
        border: 1px solid var(--slate-200);
        background: #FFFFFF;
        color: var(--slate-700);
        font-size: 12px;
        font-weight: 500;
        box-shadow: 0 1px 2px rgba(15,23,42,.02);
    }

    .page-shell {
        padding-top: 0;
    }

    .page-title {
        font-size: 22px;
        line-height: 30px;
        font-weight: 600;
        color: var(--slate-900);
        letter-spacing: -0.02em;
        margin: 0;
    }

    .page-subtitle {
        margin-top: 4px;
        color: var(--slate-500);
        font-size: 13px;
        line-height: 20px;
    }

    .eyebrow {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 3px 7px;
        border-radius: 4px;
        background: var(--primary-50);
        border: 1px solid var(--primary-100);
        color: var(--primary-600);
        font-family: "JetBrains Mono", monospace;
        font-size: 10px;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 0.07em;
    }

    .model-note {
        margin-left: 8px;
        font-family: "JetBrains Mono", monospace;
        font-size: 11px;
        color: var(--slate-400);
    }

    .section-card {
        background: #FFFFFF;
        border: 1px solid var(--slate-200);
        border-radius: 8px;
        box-shadow: 0 1px 3px rgba(15,23,42,.03);
    }

    .metric-card {
        min-height: 122px;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        padding: 16px;
        background: #FFFFFF;
        border: 1px solid var(--slate-200);
        border-radius: 8px;
        box-shadow: 0 1px 3px rgba(15,23,42,.03);
    }

    .metric-label {
        font-family: "JetBrains Mono", monospace;
        font-size: 10px;
        font-weight: 600;
        letter-spacing: .08em;
        color: var(--slate-400);
        text-transform: uppercase;
    }

    .metric-value {
        margin-top: 7px;
        font-family: "JetBrains Mono", monospace;
        font-size: 25px;
        line-height: 1;
        font-weight: 600;
        color: var(--slate-900);
        font-variant-numeric: tabular-nums;
    }

    .metric-badge {
        display: inline-flex;
        align-items: center;
        gap: 4px;
        padding: 3px 7px;
        border-radius: 4px;
        background: var(--slate-100);
        border: 1px solid var(--slate-200);
        color: var(--slate-700);
        font-family: "JetBrains Mono", monospace;
        font-size: 10px;
        line-height: 1.2;
    }

    .metric-badge.primary {
        background: var(--primary-50);
        border-color: var(--primary-100);
        color: var(--primary-600);
    }

    .metric-note {
        margin-top: 9px;
        padding-top: 8px;
        border-top: 1px solid var(--slate-100);
        color: var(--slate-400);
        font-size: 11px;
        line-height: 1.35;
    }

    .card-title {
        font-size: 14px;
        font-weight: 600;
        color: var(--slate-900);
        line-height: 1.25;
    }

    .card-subtitle {
        margin-top: 3px;
        color: var(--slate-400);
        font-size: 11px;
        line-height: 1.45;
    }

    .card-header {
        padding: 16px 16px 10px 16px;
    }

    .card-body {
        padding: 0 16px 16px 16px;
    }

    .empty-state {
        padding: 28px 16px;
        border: 1px dashed var(--slate-300);
        border-radius: 6px;
        background: var(--slate-50);
        text-align: center;
        color: var(--slate-400);
        font-size: 12px;
        line-height: 1.5;
    }

    .mini-bar-row {
        margin-bottom: 10px;
    }

    .mini-bar-label {
        display: flex;
        justify-content: space-between;
        gap: 10px;
        margin-bottom: 5px;
        color: var(--slate-700);
        font-size: 12px;
    }

    .mini-bar-value {
        font-family: "JetBrains Mono", monospace;
        font-size: 11px;
        color: var(--slate-600);
    }

    .mini-bar-track {
        width: 100%;
        height: 8px;
        border-radius: 4px;
        background: var(--slate-100);
        overflow: hidden;
    }

    .mini-bar-fill {
        height: 100%;
        background: var(--primary-600);
        border-radius: 4px;
    }

    .mini-bar-fill.light {
        background: rgba(49,46,129,.45);
    }

    .donut-wrap {
        display: flex;
        align-items: center;
        gap: 20px;
        padding: 8px 0 4px 0;
    }

    .donut {
        width: 132px;
        height: 132px;
        border-radius: 50%;
        position: relative;
        flex-shrink: 0;
    }

    .donut-hole {
        position: absolute;
        width: 80px;
        height: 80px;
        top: 26px;
        left: 26px;
        border-radius: 50%;
        background: #FFFFFF;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
    }

    .donut-total {
        font-family: "JetBrains Mono", monospace;
        font-size: 20px;
        font-weight: 600;
        color: var(--slate-900);
    }

    .donut-caption {
        margin-top: 3px;
        font-family: "JetBrains Mono", monospace;
        font-size: 8px;
        color: var(--slate-400);
        text-transform: uppercase;
        letter-spacing: .08em;
    }

    .legend-row {
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 8px;
        font-size: 11px;
        color: var(--slate-600);
    }

    .legend-dot {
        width: 7px;
        height: 7px;
        border-radius: 50%;
        background: var(--primary-600);
    }

    .legend-dot.neutral {
        background: var(--slate-300);
    }

    .insight-card {
        min-height: 106px;
        padding: 14px;
        background: #FFFFFF;
        border: 1px solid var(--slate-200);
        border-top: 2px solid var(--primary-600);
        border-radius: 8px;
        box-shadow: 0 1px 3px rgba(15,23,42,.03);
    }

    .insight-title {
        font-size: 12px;
        font-weight: 600;
        color: var(--slate-900);
    }

    .insight-text {
        margin-top: 7px;
        color: var(--slate-500);
        font-size: 11px;
        line-height: 1.5;
    }

    .workspace-card {
        background: #FFFFFF;
        border: 1px solid var(--slate-200);
        border-radius: 8px;
        box-shadow: 0 1px 3px rgba(15,23,42,.03);
    }

    .workspace-header {
        padding: 16px;
        border-bottom: 1px solid var(--slate-100);
        display: flex;
        align-items: center;
        justify-content: space-between;
    }

    .workspace-heading {
        display: flex;
        gap: 10px;
        align-items: center;
    }

    .icon-box {
        width: 28px;
        height: 28px;
        border-radius: 6px;
        background: var(--slate-100);
        display: flex;
        align-items: center;
        justify-content: center;
        color: var(--slate-700);
        flex-shrink: 0;
    }

    .what-if-badge {
        padding: 3px 7px;
        border-radius: 4px;
        background: var(--slate-100);
        color: var(--slate-600);
        font-family: "JetBrains Mono", monospace;
        font-size: 10px;
        font-weight: 500;
    }

    .control-label {
        color: var(--slate-700);
        font-size: 12px;
        font-weight: 500;
        margin-bottom: 6px;
    }

    .result-panel {
        padding: 18px;
        background: #FFFFFF;
        border: 1px solid var(--primary-100);
        border-radius: 8px;
        box-shadow: 0 1px 3px rgba(15,23,42,.03);
    }

    .result-badge {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 4px 8px;
        border-radius: 4px;
        background: var(--primary-600);
        color: #FFFFFF;
        font-family: "JetBrains Mono", monospace;
        font-size: 10px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: .05em;
    }

    .policy-value {
        margin-top: 10px;
        font-family: "JetBrains Mono", monospace;
        font-size: 22px;
        color: var(--primary);
        font-weight: 600;
        font-variant-numeric: tabular-nums;
    }

    .policy-reason {
        margin-top: 8px;
        color: var(--slate-500);
        font-size: 12px;
        line-height: 1.55;
    }

    .scenario-table,
    .data-table {
        width: 100%;
        border-collapse: collapse;
        font-size: 11px;
    }

    .scenario-table th,
    .data-table th {
        padding: 9px 10px;
        text-align: left;
        background: var(--slate-50);
        border-bottom: 1px solid var(--slate-200);
        color: var(--slate-600);
        font-family: "JetBrains Mono", monospace;
        font-size: 9px;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: .05em;
    }

    .scenario-table td,
    .data-table td {
        padding: 9px 10px;
        color: var(--slate-800);
        border-bottom: 1px solid var(--slate-100);
    }

    .scenario-table td.number,
    .data-table td.number {
        font-family: "JetBrains Mono", monospace;
        text-align: right;
        font-variant-numeric: tabular-nums;
    }

    .scenario-highlight {
        color: var(--primary-600);
        font-weight: 600;
    }

    .status-chip {
        display: inline-flex;
        padding: 3px 6px;
        border-radius: 4px;
        background: var(--slate-100);
        border: 1px solid var(--slate-200);
        color: var(--slate-600);
        font-family: "JetBrains Mono", monospace;
        font-size: 9px;
    }

    .status-chip.best {
        background: var(--primary-50);
        border-color: var(--primary-100);
        color: var(--primary-600);
    }

    .chat-user-row {
        display: flex;
        justify-content: flex-end;
        margin-bottom: 18px;
    }

    .chat-user-inner {
        max-width: 82%;
        display: flex;
        align-items: flex-start;
        gap: 10px;
    }

    .chat-user-meta {
        display: flex;
        align-items: center;
        justify-content: flex-end;
        gap: 8px;
        margin-bottom: 5px;
    }

    .chat-user-name {
        font-family: "JetBrains Mono", monospace;
        font-size: 10px;
        font-weight: 600;
        color: var(--slate-700);
    }

    .chat-time {
        font-family: "JetBrains Mono", monospace;
        font-size: 10px;
        color: var(--slate-400);
    }

    .chat-user-bubble {
        background: var(--primary-600);
        color: #FFFFFF;
        padding: 12px 14px;
        border-radius: 14px 4px 14px 14px;
        font-size: 13px;
        line-height: 1.55;
        box-shadow: 0 1px 2px rgba(49,46,129,.12);
    }

    .chat-avatar {
        width: 32px;
        height: 32px;
        margin-top: 22px;
        border-radius: 50%;
        object-fit: cover;
        border: 1px solid var(--slate-200);
        flex-shrink: 0;
    }

    .assistant-card {
        padding: 16px;
        margin-bottom: 18px;
        background: #FFFFFF;
        border: 1px solid var(--slate-200);
        border-radius: 8px;
        box-shadow: 0 1px 3px rgba(15,23,42,.03);
    }

    .assistant-head {
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 10px;
    }

    .assistant-mark {
        width: 28px;
        height: 28px;
        border-radius: 6px;
        background: var(--slate-900);
        color: #FFFFFF;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 13px;
        font-weight: 600;
        flex-shrink: 0;
    }

    .assistant-name {
        font-family: "JetBrains Mono", monospace;
        font-size: 10px;
        font-weight: 600;
        color: var(--slate-800);
        text-transform: uppercase;
        letter-spacing: .05em;
    }

    .assistant-status {
        font-family: "JetBrains Mono", monospace;
        font-size: 9px;
        color: var(--primary-600);
        background: var(--primary-50);
        border: 1px solid var(--primary-100);
        border-radius: 4px;
        padding: 2px 5px;
        text-transform: uppercase;
    }

    .assistant-answer {
        color: var(--slate-800);
        font-size: 13px;
        line-height: 1.65;
        padding-top: 12px;
        border-top: 1px solid var(--slate-100);
    }

    .activity-card {
        padding: 16px;
        position: sticky;
        top: 82px;
        background: #FFFFFF;
        border: 1px solid var(--slate-200);
        border-radius: 8px;
        box-shadow: 0 1px 3px rgba(15,23,42,.03);
    }

    .activity-head {
        display: flex;
        align-items: center;
        justify-content: space-between;
    }

    .activity-title {
        font-size: 13px;
        font-weight: 600;
        color: var(--slate-900);
    }

    .active-badge {
        padding: 4px 7px;
        border-radius: 4px;
        background: var(--slate-100);
        color: var(--slate-600);
        font-family: "JetBrains Mono", monospace;
        font-size: 9px;
        text-transform: uppercase;
        letter-spacing: .05em;
    }

    .activity-label {
        margin: 16px 0 8px;
        font-family: "JetBrains Mono", monospace;
        font-size: 9px;
        color: var(--slate-400);
        letter-spacing: .08em;
    }

    .tool-item {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 10px;
        padding: 9px 10px;
        margin-bottom: 6px;
        border: 1px solid var(--slate-200);
        border-radius: 6px;
        color: var(--slate-700);
        font-family: "JetBrains Mono", monospace;
        font-size: 10px;
        background: #FFFFFF;
    }

    .tool-status {
        color: var(--slate-400);
    }

    .telemetry {
        margin-top: 12px;
        padding: 12px 14px;
        border-radius: 6px;
        background: var(--slate-50);
        border: 1px solid var(--slate-100);
        color: var(--slate-600);
        font-size: 11px;
        line-height: 1.8;
    }

    .telemetry-row {
        display: flex;
        justify-content: space-between;
        gap: 12px;
    }

    .telemetry-value {
        font-family: "JetBrains Mono", monospace;
        color: var(--slate-700);
        text-align: right;
    }

    [data-testid="stButton"] > button {
        border-radius: 6px !important;
        border: 1px solid var(--slate-200) !important;
        background: #FFFFFF !important;
        color: var(--slate-700) !important;
        font-size: 12px !important;
        font-weight: 500 !important;
        box-shadow: none !important;
        min-height: 36px !important;
    }

    [data-testid="stButton"] > button:hover {
        background: var(--slate-50) !important;
        border-color: var(--slate-300) !important;
        color: var(--slate-900) !important;
    }

    [data-testid="stButton"] > button[kind="primary"] {
        background: var(--primary) !important;
        border-color: var(--primary) !important;
        color: #FFFFFF !important;
    }

    [data-testid="stButton"] > button[kind="primary"]:hover {
        background: var(--primary-600) !important;
        border-color: var(--primary-600) !important;
    }

    [data-testid="stChatInput"] {
        border-color: var(--slate-200) !important;
    }

    [data-testid="stChatInput"] textarea {
        font-size: 13px !important;
    }

    @media (max-width: 1100px) {
        .header-actions {
            display: none;
        }

        .block-container {
            padding-left: 20px;
            padding-right: 20px;
        }

        .top-header {
            margin-left: -20px;
            margin-right: -20px;
            padding-left: 20px;
            padding-right: 20px;
        }
    }
    </style>
    ''',
    unsafe_allow_html=True,
)

# CONSTANTS
# ============================================================

LOGO_URL = (
    "https://lh3.googleusercontent.com/aida/"
    "AEtjO1W1hfa8PdFe_XmoyULJs0H1kn0_2vu8wEW1eZo18tmo186J0Q9n"
    "ORBRbdKAxOYbfBkAFQei1NoGyagW8mC-cE6Hx7KtnyJKUUlkacE_FCmB8u"
    "IwuGDG0DZQOsw1gs9LkppvaANNsKSBqbIyD_dLrFzHhBYxEJmoyrJqERY"
    "VriEuSNbAjFFQXfBJ-Vh00b9gqU2w8_KJ42Uv-e-nWFcq6_Iqi2qUG_W_"
    "d zAc84QExN1xVLOleexVJqLlbX2pJ"
).replace(" ", "")

PROFILE_URL = (
    "https://lh3.googleusercontent.com/aida/"
    "AEtjO1UaUIYJiEGMB43XQiddLNKCcBQg9GSPRDzW57foChFugV02-k5g"
    "R-xkQ9h3ylKuRGk0S3xt10gclFkPitoGUiAZe-VC4x5xBR1g7BXCEahOzr"
    "XHM-UohAdqIe5BvAvfv_0Pgw3vfGmY886wFjBgoQhHfAXXtxv_c6yWhHz"
    "r6KwDCi7kUKXWgvgnhWNzDThYCTLQyggOn43R2c-C2BpUSQrwPvi2k3vQ"
    "AzQrZo_pSqP7aOUuIYgxM8wfX5Cg"
)


# ============================================================
# DATA HELPERS
# ============================================================

def safe_call(func, default=None, *args, **kwargs):
    try:
        return func(*args, **kwargs)
    except Exception:
        return default


@st.cache_data(ttl=300, show_spinner=False)
def load_overview_data():
    revenue = safe_call(analyze_revenue_structure, {})
    dependency = safe_call(analyze_late_fee_dependency, {})
    late_fee = safe_call(analyze_late_fee_contribution, {})
    rates = safe_call(analyze_average_rental_rate_by_category, {})
    stores = safe_call(get_store_data, [])
    return {
        "revenue": revenue or {},
        "dependency": dependency or {},
        "late_fee": late_fee or {},
        "rates": rates or {},
        "stores": stores or [],
    }


@st.cache_data(ttl=300, show_spinner=False)

@st.cache_data(ttl=300, show_spinner=False)
def load_categories():

    result = safe_call(
        analyze_average_rental_rate_by_category,
        {},
    )

    categories = (
        result.get("categories", [])
        if isinstance(result, dict)
        else []
    )

    names = [
        row.get("category")
        for row in categories
        if row.get("category")
    ]

    rates = {
        row.get("category"): float(
            row.get("average_rental_rate") or 0
        )
        for row in categories
        if row.get("category")
    }

    return names, rates


@st.cache_data(ttl=300, show_spinner=False)
def load_filter_metadata():

    names, rates = load_categories()

    stores = safe_call(get_store_data, [])
    stores = stores if isinstance(stores, list) else []

    store_ids = []

    for row in stores:
        try:
            sid = int(row.get("store_id"))
            store_ids.append(sid)
        except Exception:
            continue

    store_ids = sorted(set(store_ids))

    return {
        "categories": names,
        "rates": rates,
        "store_ids": store_ids,
        "stores": stores,
    }


@st.cache_data(ttl=300, show_spinner=False)
def load_category_detail_data():

    result = safe_call(get_category_data, [])

    return result if isinstance(result, list) else []


@st.cache_data(ttl=300, show_spinner=False)
def load_fee_constraints():

    result = safe_call(
        derive_fee_constraint,
        {},
    )

    return result if isinstance(result, dict) else {}




# ============================================================
# INTERACTIVE FILTER STATE
# ============================================================

if "overview_category" not in st.session_state:
    names, _rates = load_categories()
    st.session_state.overview_category = (
        "All Film Categories"
    )

if "overview_store" not in st.session_state:
    st.session_state.overview_store = "All Stores"




@st.cache_data(ttl=300, show_spinner=False)
def load_monthly_rental_trend():

    rows = safe_call(
        get_rental_data,
        [],
    )

    if not isinstance(rows, list) or not rows:
        return pd.DataFrame(
            columns=[
                "month",
                "rental_revenue",
            ]
        )

    df = pd.DataFrame(rows)

    if df.empty:
        return pd.DataFrame(
            columns=[
                "month",
                "rental_revenue",
            ]
        )

    if "rental_date" not in df.columns:
        return pd.DataFrame(
            columns=[
                "month",
                "rental_revenue",
            ]
        )

    if "rental_rate" not in df.columns:
        return pd.DataFrame(
            columns=[
                "month",
                "rental_revenue",
            ]
        )

    df["rental_date"] = pd.to_datetime(
        df["rental_date"],
        errors="coerce",
    )

    df["rental_rate"] = pd.to_numeric(
        df["rental_rate"],
        errors="coerce",
    ).fillna(0)

    df = df.dropna(
        subset=["rental_date"]
    )

    if df.empty:
        return pd.DataFrame(
            columns=[
                "month",
                "rental_revenue",
            ]
        )

    df["month"] = (
        df["rental_date"]
        .dt.to_period("M")
        .astype(str)
    )

    result = (
        df.groupby("month", as_index=False)
        ["rental_rate"]
        .sum()
        .rename(
            columns={
                "rental_rate": "rental_revenue"
            }
        )
        .sort_values("month")
    )

    return result


# ============================================================
# SHARED RENDERERS
# ============================================================

def money(value):
    try:
        return f"${float(value):,.2f}"
    except Exception:
        return "—"


def pct(value):
    try:
        return f"{float(value):.1f}%"
    except Exception:
        return "—"




def render_top_header():

    metadata = load_filter_metadata()

    categories = metadata.get(
        "categories",
        []
    ) or []

    store_ids = metadata.get(
        "store_ids",
        []
    ) or []

    category_options = [
        "All Film Categories"
    ] + categories

    store_options = [
        "All Stores"
    ] + [
        f"Store #{sid}"
        for sid in store_ids
    ]

    if (
        "overview_category"
        not in st.session_state
    ):
        st.session_state.overview_category = (
            "All Film Categories"
        )

    if (
        st.session_state.overview_category
        not in category_options
    ):
        st.session_state.overview_category = (
            "All Film Categories"
        )

    if (
        "overview_store"
        not in st.session_state
    ):
        st.session_state.overview_store = (
            "All Stores"
        )

    if (
        st.session_state.overview_store
        not in store_options
    ):
        st.session_state.overview_store = (
            "All Stores"
        )

    st.markdown(
        """
        <div class="top-header">
            <div class="system-badge">
                <span class="status-dot"></span>
                <span class="mono">
                    Sakila MySQL · Agent: Claude Sonnet 4.5
                </span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    c1, c2, c3, c4 = st.columns(
        [3.0, 2.4, 2.8, 0.55],
        gap="small",
    )

    with c1:

        st.markdown(
            '<div class="top-control-label">'
            'Film Category'
            '</div>',
            unsafe_allow_html=True,
        )

        st.selectbox(
            "Film Category",
            category_options,
            key="overview_category",
            label_visibility="collapsed",
        )

    with c2:

        st.markdown(
            '<div class="top-control-label">'
            'Store'
            '</div>',
            unsafe_allow_html=True,
        )

        st.selectbox(
            "Store",
            store_options,
            key="overview_store",
            label_visibility="collapsed",
        )

    with c3:

        st.markdown(
            '<div class="top-control-label">'
            'Data Scope'
            '</div>',
            unsafe_allow_html=True,
        )

        selected_category = (
            st.session_state.overview_category
        )

        selected_store = (
            st.session_state.overview_store
        )

        if selected_category != "All Film Categories":
            scope_text = selected_category
        else:
            scope_text = "Full Sakila dataset"

        if selected_store != "All Stores":
            scope_text += (
                f" · {selected_store}"
            )

        st.markdown(
            f'<div class="data-scope-chip">'
            f'{scope_text}'
            f'</div>',
            unsafe_allow_html=True,
        )

    with c4:

        st.markdown(
            '<div class="top-control-label">&nbsp;</div>',
            unsafe_allow_html=True,
        )

        if st.button(
            "↻",
            key="header_refresh",
            use_container_width=True,
            help="Refresh backend data",
        ):
            st.cache_data.clear()
            st.rerun()





def render_sidebar(page):

    st.sidebar.markdown(
        """
        <div class="brand-row">
            <div class="brand-logo-fallback">◆</div>
            <div>
                <div class="brand-name">Sakila AI</div>
                <div class="brand-badge">BI Intelligence</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.sidebar.markdown(
        '<div class="nav-section-title">Navigation</div>',
        unsafe_allow_html=True,
    )

    if st.sidebar.button(
        "▦  Overview",
        key="nav_overview",
        use_container_width=True,
        type=(
            "primary"
            if page == "overview"
            else "secondary"
        ),
    ):
        st.session_state.page = "overview"
        st.query_params["page"] = "overview"
        st.rerun()

    if st.sidebar.button(
        "↗  Predictions & Policy",
        key="nav_predictions",
        use_container_width=True,
        type=(
            "primary"
            if page == "predictions"
            else "secondary"
        ),
    ):
        st.session_state.page = "predictions"
        st.query_params["page"] = "predictions"
        st.rerun()

    st.sidebar.markdown(
        "<div style='height:4px'></div>",
        unsafe_allow_html=True,
    )

    if st.sidebar.button(
        "✦  AI Analyst",
        key="nav_analyst",
        use_container_width=True,
        type=(
            "primary"
            if page == "analyst"
            else "secondary"
        ),
    ):
        st.session_state.page = "analyst"
        st.query_params["page"] = "analyst"
        st.rerun()

    st.sidebar.markdown(
        """
        <div class="sidebar-bottom">
            <div class="activity-nav">
                <div class="activity-left">
                    <span class="material-symbols-outlined"
                          style="font-size:18px;">
                        tune
                    </span>
                    <span>Agent Activity</span>
                </div>
                <span class="activity-dot"></span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )



def render_page_header(title, subtitle, eyebrow=None, model_note=None):
    if eyebrow:
        left = f"""
        <div>
            <div>
                <span class="eyebrow">
                    <span class="material-symbols-outlined" style="font-size:13px;">model_training</span>
                    {html.escape(eyebrow)}
                </span>
                {f'<span class="model-note">{html.escape(model_note)}</span>' if model_note else ''}
            </div>
            <div class="page-title" style="margin-top:8px;">{html.escape(title)}</div>
            <div class="page-subtitle">{html.escape(subtitle)}</div>
        </div>
        """
    else:
        left = f"""
        <div>
            <div class="page-title">{html.escape(title)}</div>
            <div class="page-subtitle">{html.escape(subtitle)}</div>
        </div>
        """

    st.markdown(
        f"""
        <div style="padding:28px 0 18px 0;border-bottom:1px solid #E2E8F0;margin-bottom:20px;">
            {left}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_metric_card(label, value, badge=None, note="", primary_badge=False):
    badge_html = ""
    if badge:
        badge_class = "metric-badge primary" if primary_badge else "metric-badge"
        badge_html = f'<span class="{badge_class}">{html.escape(str(badge))}</span>'

    st.markdown(
        f"""
        <div class="metric-card">
            <div>
                <div class="metric-label">{html.escape(str(label))}</div>
                <div class="metric-value">{html.escape(str(value))}</div>
                <div style="margin-top:9px;">{badge_html}</div>
            </div>
            <div class="metric-note">{html.escape(str(note))}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_panel(title, subtitle="", body_html=""):
    st.markdown(
        f"""
        <div class="section-card">
            <div class="card-header">
                <div class="card-title">{html.escape(title)}</div>
                {f'<div class="card-subtitle">{html.escape(subtitle)}</div>' if subtitle else ''}
            </div>
            <div class="card-body">
                {body_html}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_horizontal_bars(rows, label_key, value_key, value_formatter=money, limit=8, light=False):
    if not rows:
        st.markdown(
            '<div class="empty-state">No data available from the current backend.</div>',
            unsafe_allow_html=True,
        )
        return

    rows = rows[:limit]
    max_value = max(float(row.get(value_key, 0) or 0) for row in rows) or 1.0
    chunks = []

    for row in rows:
        label = row.get(label_key, "—")
        value = float(row.get(value_key, 0) or 0)
        width = max(4, int((value / max_value) * 100))

        fill_class = "mini-bar-fill light" if light else "mini-bar-fill"
        chunks.append(
            f"""
            <div class="mini-bar-row">
                <div class="mini-bar-label">
                    <span>{html.escape(str(label))}</span>
                    <span class="mini-bar-value">{html.escape(value_formatter(value))}</span>
                </div>
                <div class="mini-bar-track">
                    <div class="{fill_class}" style="width:{width}%;"></div>
                </div>
            </div>
            """
        )

    st.markdown("".join(chunks), unsafe_allow_html=True)


def render_donut(rental_revenue, late_fee_revenue, total_revenue):
    total = max(float(total_revenue or 0), 0.0)
    base = max(float(rental_revenue or 0), 0.0)
    fee = max(float(late_fee_revenue or 0), 0.0)

    if total <= 0:
        st.markdown(
            '<div class="empty-state">No revenue data available.</div>',
            unsafe_allow_html=True,
        )
        return

    base_pct = base / total * 100
    gradient = (
        f"conic-gradient(#312E81 0 {base_pct:.2f}%, "
        f"#CBD5E1 {base_pct:.2f}% 100%)"
    )

    st.markdown(
        f"""
        <div class="donut-wrap">
            <div class="donut" style="background:{gradient};">
                <div class="donut-hole">
                    <div class="donut-total">{money(total)}</div>
                    <div class="donut-caption">Gross Rev</div>
                </div>
            </div>
            <div>
                <div class="legend-row">
                    <span class="legend-dot"></span>
                    <span>Base Rental</span>
                    <span style="margin-left:auto;font-family:'JetBrains Mono',monospace;">{money(base)}</span>
                </div>
                <div class="legend-row">
                    <span class="legend-dot neutral"></span>
                    <span>Late Fees</span>
                    <span style="margin-left:auto;font-family:'JetBrains Mono',monospace;">{money(fee)}</span>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_html_table(headers, rows, number_columns=None):
    number_columns = number_columns or set()

    head = "".join(f"<th>{html.escape(str(header))}</th>" for header in headers)
    body = []

    for row in rows:
        cells = []
        for idx, value in enumerate(row):
            cls = "number" if idx in number_columns else ""
            cells.append(f'<td class="{cls}">{html.escape(str(value))}</td>')
        body.append("<tr>" + "".join(cells) + "</tr>")

    table = f"""
    <table class="data-table">
        <thead><tr>{head}</tr></thead>
        <tbody>{''.join(body)}</tbody>
    </table>
    """

    st.markdown(table, unsafe_allow_html=True)


# ============================================================
# AGENT RESPONSE RENDERERS
# ============================================================

def render_agent_kpis(kpis):
    if not kpis:
        return

    st.markdown(
        '<div class="label" style="margin:14px 0 8px;">KEY METRICS</div>',
        unsafe_allow_html=True,
    )

    columns = st.columns(min(len(kpis), 4))
    for index, kpi in enumerate(kpis):
        with columns[index % len(columns)]:
            label = kpi.get("label", "Metric")
            value = kpi.get("value", "—")
            description = kpi.get("description", "")
            render_metric_card(label, value, note=description)


def render_agent_visualization(viz):
    if not isinstance(viz, dict):
        return

    title = viz.get("title", "Visualization")
    description = viz.get("description", "")
    chart_type = str(viz.get("type", "bar")).lower()
    data = viz.get("data", [])
    x_key = viz.get("x_key")
    y_key = viz.get("y_key")

    if not isinstance(data, list) or not data:
        return

    df = pd.DataFrame(data)
    if df.empty:
        return

    st.markdown(
        f"""
        <div class="section-card" style="margin-top:14px;">
            <div class="card-header">
                <div class="card-title">{html.escape(str(title))}</div>
                {f'<div class="card-subtitle">{html.escape(str(description))}</div>' if description else ''}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if x_key not in df.columns or y_key not in df.columns:
        st.dataframe(df, use_container_width=True, hide_index=True)
        return

    if chart_type == "bar":
        chart = (
            alt.Chart(df)
            .mark_bar(color="#312E81")
            .encode(
                x=alt.X(f"{x_key}:N", sort="-y", title=None),
                y=alt.Y(f"{y_key}:Q", title=None),
                tooltip=[x_key, y_key],
            )
            .properties(height=240)
        )
        st.altair_chart(chart, use_container_width=True)

    elif chart_type == "line":
        chart = (
            alt.Chart(df)
            .mark_line(color="#312E81", strokeWidth=2)
            .encode(
                x=alt.X(f"{x_key}:N", title=None),
                y=alt.Y(f"{y_key}:Q", title=None),
                tooltip=[x_key, y_key],
            )
            .properties(height=240)
        )
        st.altair_chart(chart, use_container_width=True)

    elif chart_type == "pie":
        chart = (
            alt.Chart(df)
            .mark_arc(innerRadius=55)
            .encode(
                theta=alt.Theta(f"{y_key}:Q"),
                color=alt.Color(
                    f"{x_key}:N",
                    scale=alt.Scale(range=["#312E81", "#64748B", "#94A3B8", "#CBD5E1"]),
                    legend=alt.Legend(title=None),
                ),
                tooltip=[x_key, y_key],
            )
            .properties(height=260)
        )
        st.altair_chart(chart, use_container_width=True)

    else:
        st.dataframe(df, use_container_width=True, hide_index=True)


def render_agent_table(table):
    if not isinstance(table, dict):
        return

    title = table.get("title", "Data")
    rows = table.get("rows", [])

    if not rows:
        return

    df = pd.DataFrame(rows)
    if df.empty:
        return

    st.markdown(
        f"""
        <div style="margin-top:14px;">
            <div class="label" style="margin-bottom:7px;">{html.escape(str(title))}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.dataframe(df, use_container_width=True, hide_index=True)


def render_agent_insights(insights):
    if not insights:
        return

    st.markdown(
        '<div class="label" style="margin:16px 0 8px;">KEY FINDINGS & ACTION ITEMS</div>',
        unsafe_allow_html=True,
    )

    cols = st.columns(min(len(insights), 3))
    for index, insight in enumerate(insights):
        with cols[index % len(cols)]:
            st.markdown(
                f"""
                <div class="insight-card">
                    <div class="insight-title">{index + 1}. Insight</div>
                    <div class="insight-text">{html.escape(str(insight))}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )




def render_agent_activity(trace):

    trace = trace or []

    with st.container(
        border=True,
    ):

        header_left, header_right = st.columns(
            [3, 1]
        )

        with header_left:
            st.markdown(
                "### Agent Activity"
            )

        with header_right:
            if trace:
                st.caption("ACTIVE")
            else:
                st.caption("READY")

        st.caption(
            "TOOL EXECUTION STEPS"
        )

        if not trace:

            st.info(
                "No tool execution in the current session."
            )

        else:

            for item in trace:

                if not isinstance(
                    item,
                    dict,
                ):
                    continue

                tool = str(
                    item.get(
                        "tool",
                        "unknown",
                    )
                )

                status = str(
                    item.get(
                        "status",
                        "complete",
                    )
                )

                c1, c2 = st.columns(
                    [3, 1]
                )

                with c1:
                    st.markdown(
                        f"✓  `{tool}`"
                    )

                with c2:
                    st.caption(
                        status
                    )

                st.divider()

        st.caption("Agent telemetry")

        t1, t2, t3 = st.columns(3)

        with t1:
            st.metric(
                "Model",
                "Claude Sonnet 4.5",
            )

        with t2:
            st.metric(
                "Data Source",
                "Sakila MySQL",
            )

        with t3:
            st.metric(
                "Tool Calls",
                len(trace),
            )




def render_agent_response(result):
    if not isinstance(result, dict):
        st.markdown(str(result))
        return

    answer = result.get("answer", "")
    if answer:
        st.markdown(
            '<div class="assistant-answer">',
            unsafe_allow_html=True,
        )
        st.markdown(answer)
        st.markdown("</div>", unsafe_allow_html=True)

    for kpi_group in [result.get("kpis", [])]:
        render_agent_kpis(kpi_group)

    for viz in result.get("visualizations", []) or []:
        render_agent_visualization(viz)

    for table in result.get("tables", []) or []:
        render_agent_table(table)

    render_agent_insights(result.get("insights", []) or [])


# ============================================================
# OVERVIEW PAGE
# ============================================================



def render_overview():

    metadata = load_filter_metadata()

    selected_category = st.session_state.get(
        "overview_category",
        "All Film Categories",
    )

    selected_store = st.session_state.get(
        "overview_store",
        "All Stores",
    )

    data = load_overview_data()

    revenue = data.get(
        "revenue",
        {}
    ) or {}

    dependency = data.get(
        "dependency",
        {}
    ) or {}

    late_fee = data.get(
        "late_fee",
        {}
    ) or {}

    rates = data.get(
        "rates",
        {}
    ) or {}

    stores = data.get(
        "stores",
        []
    ) or []

    category_rows = (
        late_fee.get(
            "categories",
            []
        )
        if isinstance(late_fee, dict)
        else []
    )

    category_detail = load_category_detail_data()

    # ========================================================
    # CATEGORY SCOPE
    # ========================================================

    selected_category_row = None

    if selected_category != "All Film Categories":

        for row in category_rows:

            if (
                row.get("category")
                == selected_category
            ):
                selected_category_row = row
                break

    selected_category_detail = None

    if selected_category != "All Film Categories":

        for row in category_detail:

            if (
                row.get("category")
                == selected_category
            ):
                selected_category_detail = row
                break

    # ========================================================
    # STORE SCOPE
    # ========================================================

    selected_store_row = None

    if selected_store != "All Stores":

        try:

            store_id = int(
                selected_store.replace(
                    "Store #",
                    "",
                )
            )

            for row in stores:

                if (
                    int(
                        row.get(
                            "store_id",
                            -1,
                        )
                    )
                    == store_id
                ):
                    selected_store_row = row
                    break

        except Exception:
            selected_store_row = None

    # ========================================================
    # METRICS
    # ========================================================

    if selected_store_row:

        store_revenue = float(
            selected_store_row.get(
                "total_revenue",
                0,
            )
            or 0
        )

        store_rentals = int(
            selected_store_row.get(
                "total_rentals",
                0,
            )
            or 0
        )

        total_revenue = store_revenue
        rental_revenue = store_revenue
        late_fee_revenue = 0
        late_fee_pct = 0
        total_rentals = store_rentals

        # Store tool does not expose late-fee detail.
        late_rentals = None
        late_rate = None

        scope_note = (
            f"{selected_store} · "
            "Store-level aggregate"
        )

    elif selected_category_row:

        total_revenue = float(
            selected_category_row.get(
                "total_revenue",
                0,
            )
            or 0
        )

        rental_revenue = float(
            selected_category_row.get(
                "rental_revenue",
                0,
            )
            or 0
        )

        late_fee_revenue = float(
            selected_category_row.get(
                "late_fee_revenue",
                0,
            )
            or 0
        )

        late_fee_pct = (
            late_fee_revenue
            / total_revenue
            * 100
            if total_revenue
            else 0
        )

        total_rentals = int(
            selected_category_detail.get(
                "total_rentals",
                0,
            )
            or 0
        ) if selected_category_detail else 0

        late_rentals = int(
            selected_category_detail.get(
                "late_rentals",
                0,
            )
            or 0
        ) if selected_category_detail else 0

        late_rate = (
            late_rentals
            / total_rentals
            * 100
            if total_rentals
            else 0
        )

        scope_note = (
            f"Category scope: "
            f"{selected_category}"
        )

    else:

        total_revenue = float(
            revenue.get(
                "total_revenue",
                0,
            )
            or 0
        )

        rental_revenue = float(
            revenue.get(
                "rental_revenue",
                0,
            )
            or 0
        )

        late_fee_revenue = float(
            revenue.get(
                "late_fee_revenue",
                0,
            )
            or 0
        )

        late_fee_pct = float(
            revenue.get(
                "late_fee_contribution_pct",
                0,
            )
            or 0
        )

        total_rentals = int(
            dependency.get(
                "total_rentals",
                0,
            )
            or 0
        )

        late_rentals = int(
            dependency.get(
                "late_rentals",
                0,
            )
            or 0
        )

        late_rate = float(
            dependency.get(
                "late_rate_pct",
                0,
            )
            or 0
        )

        scope_note = (
            "Full Sakila dataset"
        )

    # ========================================================
    # PAGE HEADER
    # ========================================================

    render_page_header(
        "Business Overview",
        "Observed revenue, rental behavior, category economics, "
        "and store performance from Sakila MySQL.",
        eyebrow="BI INTELLIGENCE",
        model_note=scope_note,
    )

    # ========================================================
    # AI ANALYST SHORTCUT
    # ========================================================

    ai_col1, ai_col2 = st.columns(
        [5.5, 1.6]
    )

    with ai_col2:

        if st.button(
            "✦ Open AI Analyst",
            key="overview_ai_analyst",
            use_container_width=True,
        ):

            st.session_state.page = (
                "analyst"
            )

            st.query_params["page"] = (
                "analyst"
            )

            st.rerun()

    st.markdown(
        "<div style='height:8px'></div>",
        unsafe_allow_html=True,
    )

    # ========================================================
    # KPI CARDS
    # ========================================================

    k1, k2, k3, k4, k5 = st.columns(5)

    with k1:

        label = (
            "STORE REVENUE"
            if selected_store_row
            else "TOTAL REVENUE"
        )

        render_metric_card(
            label,
            money(total_revenue),
            badge="Observed",
            note=scope_note,
            primary_badge=True,
        )

    with k2:

        label = (
            "STORE RENTALS"
            if selected_store_row
            else "RENTAL REVENUE"
        )

        value = (
            f"{total_rentals:,}"
            if selected_store_row
            else money(rental_revenue)
        )

        render_metric_card(
            label,
            value,
            badge="Observed",
            note=(
                "Rental volume returned by "
                "the store data tool."
                if selected_store_row
                else "Observed base rental revenue."
            ),
        )

    with k3:

        render_metric_card(
            "LATE-FEE REVENUE",
            (
                "—"
                if selected_store_row
                else money(late_fee_revenue)
            ),
            badge=(
                "Not exposed by store tool"
                if selected_store_row
                else pct(late_fee_pct)
            ),
            note=(
                "Current get_store_data() does "
                "not expose store-level late fees."
                if selected_store_row
                else "Observed overdue-fee revenue."
            ),
        )

    with k4:

        render_metric_card(
            "LATE-FEE CONTRIBUTION",
            (
                "—"
                if selected_store_row
                else pct(late_fee_pct)
            ),
            badge=(
                "No store-level field"
                if selected_store_row
                else "Of selected scope"
            ),
            note=(
                "Not calculated without store-level "
                "late-fee data."
                if selected_store_row
                else "Late-fee share of observed revenue."
            ),
        )

    with k5:

        render_metric_card(
            "LATE-RETURN RATE",
            (
                "—"
                if late_rate is None
                else pct(late_rate)
            ),
            badge=(
                "No store-level field"
                if late_rate is None
                else f"{late_rentals:,} late rentals"
            ),
            note=(
                "Current store tool does not expose "
                "store-level late-return rate."
                if late_rate is None
                else f"Across {total_rentals:,} completed rentals."
            ),
        )

    # ========================================================
    # REVENUE TREND
    # ========================================================

    trend_df = load_monthly_rental_trend()

    if selected_category != "All Film Categories":
        if "category" in trend_df.columns:
            trend_df = trend_df[
                trend_df["category"]
                == selected_category
            ]

    if (
        selected_category != "All Film Categories"
        and not trend_df.empty
    ):
        pass

    st.markdown(
        "<div style='height:14px'></div>",
        unsafe_allow_html=True,
    )

    trend_col, mix_col = st.columns(
        [1.55, 1.0],
        gap="medium",
    )

    with trend_col:

        st.markdown(
            """
            <div class="section-card">
                <div class="card-header">
                    <div class="card-title">
                        Revenue Trend
                    </div>
                    <div class="card-subtitle">
                        Monthly rental revenue derived from
                        get_rental_data().
                    </div>
                </div>
                <div class="card-body">
            """,
            unsafe_allow_html=True,
        )

        if (
            selected_store_row
            and not trend_df.empty
        ):

            st.markdown(
                '<div class="empty-state">'
                'The current rental data tool does not '
                'expose store_id, so the monthly trend '
                'cannot be scoped to a selected store '
                'without bypassing the backend tool layer.'
                '</div>',
                unsafe_allow_html=True,
            )

        elif trend_df.empty:

            st.markdown(
                '<div class="empty-state">'
                'No rental-date series was returned by '
                'the backend data tool.'
                '</div>',
                unsafe_allow_html=True,
            )

        else:

            chart = (
                alt.Chart(trend_df)
                .mark_line(
                    point=True,
                    color="#312E81",
                    strokeWidth=2,
                )
                .encode(
                    x=alt.X(
                        "month:N",
                        title=None,
                    ),
                    y=alt.Y(
                        "rental_revenue:Q",
                        title="Rental Revenue",
                    ),
                    tooltip=[
                        "month",
                        "rental_revenue",
                    ],
                )
                .properties(
                    height=280
                )
            )

            st.altair_chart(
                chart,
                use_container_width=True,
            )

            st.markdown(
                '<div class="card-subtitle">'
                'Note: this is rental revenue, '
                'not total payment revenue. '
                'The current revenue tool does not '
                'expose payment date.'
                '</div>',
                unsafe_allow_html=True,
            )

        st.markdown(
            "</div></div>",
            unsafe_allow_html=True,
        )

    # ========================================================
    # REVENUE MIX
    # ========================================================

    with mix_col:

        st.markdown(
            """
            <div class="section-card">
                <div class="card-header">
                    <div class="card-title">
                        Revenue Mix
                    </div>
                    <div class="card-subtitle">
                        Rental base vs late-fee contribution.
                    </div>
                </div>
                <div class="card-body">
            """,
            unsafe_allow_html=True,
        )

        if selected_store_row:

            st.markdown(
                '<div class="empty-state">'
                'Store-level late-fee revenue is not '
                'returned by get_store_data(), so a '
                'store revenue mix is not fabricated.'
                '</div>',
                unsafe_allow_html=True,
            )

        else:

            render_donut(
                rental_revenue,
                late_fee_revenue,
                total_revenue,
            )

        st.markdown(
            "</div></div>",
            unsafe_allow_html=True,
        )

    # ========================================================
    # CATEGORY PANELS
    # ========================================================

    st.markdown(
        "<div style='height:16px'></div>",
        unsafe_allow_html=True,
    )

    if selected_category == "All Film Categories":

        revenue_category_rows = sorted(
            category_rows,
            key=lambda x: float(
                x.get("total_revenue", 0)
                or 0
            ),
            reverse=True,
        )

        late_fee_rows = sorted(
            category_rows,
            key=lambda x: float(
                x.get("late_fee_revenue", 0)
                or 0
            ),
            reverse=True,
        )

        rate_rows = sorted(
            rates.get("categories", [])
            if isinstance(rates, dict)
            else [],
            key=lambda x: float(
                x.get(
                    "average_rental_rate",
                    0,
                )
                or 0
            ),
            reverse=True,
        )

    else:

        revenue_category_rows = (
            [selected_category_row]
            if selected_category_row
            else []
        )

        late_fee_rows = (
            [selected_category_row]
            if selected_category_row
            else []
        )

        rate_rows = [
            row
            for row in (
                rates.get(
                    "categories",
                    [],
                )
                if isinstance(
                    rates,
                    dict,
                )
                else []
            )
            if row.get("category")
            == selected_category
        ]

    left, right = st.columns(
        [1.15, 1.0],
        gap="medium",
    )

    with left:

        st.markdown(
            """
            <div class="section-card">
                <div class="card-header">
                    <div class="card-title">
                        Revenue by Category
                    </div>
                    <div class="card-subtitle">
                        Observed backend revenue.
                    </div>
                </div>
                <div class="card-body">
            """,
            unsafe_allow_html=True,
        )

        render_horizontal_bars(
            revenue_category_rows,
            "category",
            "total_revenue",
            limit=8,
        )

        st.markdown(
            "</div></div>",
            unsafe_allow_html=True,
        )

    with right:

        st.markdown(
            """
            <div class="section-card">
                <div class="card-header">
                    <div class="card-title">
                        Average Rental Rate by Category
                    </div>
                    <div class="card-subtitle">
                        Backend-calculated average rate.
                    </div>
                </div>
                <div class="card-body">
            """,
            unsafe_allow_html=True,
        )

        render_horizontal_bars(
            rate_rows,
            "category",
            "average_rental_rate",
            value_formatter=money,
            limit=8,
            light=True,
        )

        st.markdown(
            "</div></div>",
            unsafe_allow_html=True,
        )

    st.markdown(
        "<div style='height:16px'></div>",
        unsafe_allow_html=True,
    )

    # ========================================================
    # LATE FEE + STORE
    # ========================================================

    left, right = st.columns(
        [1.15, 1.0],
        gap="medium",
    )

    with left:

        st.markdown(
            """
            <div class="section-card">
                <div class="card-header">
                    <div class="card-title">
                        Late-Fee Revenue by Category
                    </div>
                    <div class="card-subtitle">
                        Observed overdue-fee revenue.
                    </div>
                </div>
                <div class="card-body">
            """,
            unsafe_allow_html=True,
        )

        render_horizontal_bars(
            late_fee_rows,
            "category",
            "late_fee_revenue",
            limit=8,
            light=True,
        )

        st.markdown(
            "</div></div>",
            unsafe_allow_html=True,
        )

    with right:

        st.markdown(
            """
            <div class="section-card">
                <div class="card-header">
                    <div class="card-title">
                        Performance by Store
                    </div>
                    <div class="card-subtitle">
                        Select a store above to change this panel.
                    </div>
                </div>
                <div class="card-body">
            """,
            unsafe_allow_html=True,
        )

        visible_stores = stores

        if selected_store_row:
            visible_stores = [
                selected_store_row
            ]

        rows = []

        for store in visible_stores:

            rows.append(
                [
                    f"Store #{store.get('store_id', '—')}",
                    f"{int(store.get('total_rentals', 0) or 0):,}",
                    money(
                        store.get(
                            "total_revenue",
                            0,
                        )
                    ),
                ]
            )

        if rows:

            render_html_table(
                [
                    "Store",
                    "Total Rentals",
                    "Total Revenue",
                ],
                rows,
                number_columns={1, 2},
            )

        else:

            st.markdown(
                '<div class="empty-state">'
                'No store data returned.'
                '</div>',
                unsafe_allow_html=True,
            )

        st.markdown(
            "</div></div>",
            unsafe_allow_html=True,
        )

    # ========================================================
    # FINDINGS
    # ========================================================

    st.markdown(
        "<div style='height:18px'></div>",
        unsafe_allow_html=True,
    )

    top_late_fee = (
        late_fee_rows[0]
        if late_fee_rows
        else {}
    )

    top_rate = (
        rate_rows[0]
        if rate_rows
        else {}
    )

    top_store = (
        max(
            visible_stores,
            key=lambda x: float(
                x.get(
                    "total_revenue",
                    0,
                )
                or 0
            ),
        )
        if visible_stores
        else {}
    )

    st.markdown(
        """
        <div style="display:flex;
                    align-items:center;
                    justify-content:space-between;
                    margin-bottom:10px;">
            <div class="card-title">
                Key Operational Findings & Insights
            </div>
            <div class="label">
                BACKEND-DERIVED
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    findings = [

        (
            "Current scope",
            scope_note,
        ),

        (
            "Top late-fee category",
            (
                f"{top_late_fee.get('category', '—')} "
                f"generates "
                f"{money(top_late_fee.get('late_fee_revenue', 0))} "
                "in observed late-fee revenue."
            ),
        ),

        (
            "Highest average rental rate",
            (
                f"{top_rate.get('category', '—')} "
                f"has an average rental rate of "
                f"{money(top_rate.get('average_rental_rate', 0))}."
            ),
        ),

        (
            "Visible store revenue",
            (
                f"Store #{top_store.get('store_id', '—')} "
                f"records "
                f"{money(top_store.get('total_revenue', 0))}."
            ),
        ),
    ]

    cols = st.columns(4)

    for col, (title, value) in zip(
        cols,
        findings,
    ):

        with col:

            st.markdown(
                f"""
                <div class="insight-card">
                    <div class="insight-title">
                        {html.escape(title)}
                    </div>
                    <div class="insight-text">
                        {html.escape(value)}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )




# ============================================================
# PREDICTIONS & POLICY PAGE
# ============================================================


def reset_prediction_defaults():

    names, rates = load_categories()

    if not names:
        names = [""]

    default_category = (
        "Sci-Fi"
        if "Sci-Fi" in names
        else names[0]
    )

    constraints = load_fee_constraints()

    current_fee = float(
        constraints.get(
            "current_fee_per_day",
            1.00,
        )
        or 1.00
    )

    st.session_state.pred_category = default_category

    st.session_state.pred_late_rate = 28.5

    st.session_state.pred_duration = 3

    st.session_state.pred_rental_rate = float(
        rates.get(default_category, 2.99)
        or 2.99
    )

    st.session_state.pred_fee = current_fee

    st.session_state.prediction_result = None
    st.session_state.policy_result = None
    st.session_state.scenario_result = None




def run_policy_engine():

    customer_rate = (
        float(st.session_state.pred_late_rate)
        / 100.0
    )

    category = st.session_state.pred_category

    duration = int(
        st.session_state.pred_duration
    )

    rental_rate = float(
        st.session_state.pred_rental_rate
    )

    fee = float(
        st.session_state.pred_fee
    )

    constraints = load_fee_constraints()

    current_fee = float(
        constraints.get(
            "current_fee_per_day",
            1.00,
        )
        or 1.00
    )

    min_duration = int(
        constraints.get(
            "min_rental_duration",
            3,
        )
        or 3
    )

    max_duration = int(
        constraints.get(
            "max_rental_duration",
            7,
        )
        or 7
    )

    st.session_state.prediction_result = {

        "probability": predict_late_probability(
            customer_late_rate=customer_rate,
            category=category,
            rental_duration=duration,
            rental_rate=rental_rate,
        ),

        "late_days": predict_expected_late_days(
            customer_late_rate=customer_rate,
            category=category,
            rental_duration=duration,
            rental_rate=rental_rate,
        ),

        "simulation": simulate_fee_policy(
            customer_late_rate=customer_rate,
            category=category,
            rental_duration=duration,
            rental_rate=rental_rate,
            fee_per_day=fee,
            current_fee_per_day=current_fee,
        ),
    }

    st.session_state.scenario_result = (
        compare_scenarios(
            customer_late_rate=customer_rate,
            category=category,
            current_rental_duration=duration,
            rental_rate=rental_rate,
            current_fee_per_day=current_fee,
        )
    )

    st.session_state.policy_result = (
        generate_policy_recommendation(
            customer_late_rate=customer_rate,
            category=category,
            current_rental_duration=duration,
            rental_rate=rental_rate,
            current_fee_per_day=current_fee,
            min_rental_duration=min_duration,
            max_rental_duration=max_duration,
        )
    )



def render_predictions():
    names, rates = load_categories()

    if not names:
        names = ["Action", "Animation", "Children", "Classics", "Comedy", "Documentary", "Drama", "Family", "Foreign", "Games", "Horror", "Music", "New", "Sci-Fi", "Sports", "Travel"]

    if st.session_state.pred_category not in names:
        st.session_state.pred_category = names[0]

    if st.session_state.pred_category in rates and st.session_state.pred_rental_rate <= 0:
        st.session_state.pred_rental_rate = rates[st.session_state.pred_category]

    render_page_header(
        "Predictions & Policy Optimization Engine",
        "Simulate delinquency, estimate overdue-fee revenue, and evaluate policy scenarios using the existing prediction, simulation, and optimization tools.",
        eyebrow="WHAT-IF WORKSPACE",
        model_note="Current Sakila late-return models · Calibrated inference",
    )

    spacer, preset_col, reset_col = st.columns([7, 1.35, 1.15])
    with preset_col:
        if st.button("Preset Scenarios", key="preset_btn", use_container_width=True):
            st.session_state.pred_late_rate = 28.5
            st.session_state.pred_duration = 3
            st.session_state.pred_fee = 1.00
            st.session_state.pred_rental_rate = float(
                rates.get(st.session_state.pred_category, 2.99)
            )
            st.session_state.prediction_result = None
            st.session_state.policy_result = None
            st.session_state.scenario_result = None

    with reset_col:
        if st.button("Reset Defaults", key="reset_btn", use_container_width=True):
            reset_prediction_defaults()

    left, right = st.columns([4, 8], gap="medium")

    with left:
        st.markdown(
            """
            <div class="workspace-card">
                <div class="workspace-header">
                    <div class="workspace-heading">
                        <div class="icon-box">
                            <span class="material-symbols-outlined">tune</span>
                        </div>
                        <div>
                            <div class="card-title">Scenario Inputs</div>
                            <div class="card-subtitle">Configure parameters for inference</div>
                        </div>
                    </div>
                    <span class="what-if-badge">What-If</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.selectbox(
            "Film Category",
            options=names,
            key="pred_category",
        )

        st.slider(
            "Customer Historical Late Rate",
            min_value=0.0,
            max_value=100.0,
            step=0.5,
            key="pred_late_rate",
        )

        st.markdown(
            f"""
            <div style="display:flex;justify-content:space-between;margin-top:-8px;margin-bottom:12px;color:#94A3B8;font-family:'JetBrains Mono',monospace;font-size:10px;">
                <span>0% (Pristine)</span>
                <span>25%</span>
                <span>50%</span>
                <span>100% (Chronic)</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown('<div class="control-label">Current Rental Duration</div>', unsafe_allow_html=True)

        dm1, dm2, dm3 = st.columns([1, 2.5, 1])
        with dm1:
            if st.button("−", key="duration_minus"):
                st.session_state.pred_duration = max(
                    1, int(st.session_state.pred_duration) - 1
                )
        with dm2:
            st.markdown(
                f"""
                <div style="height:36px;display:flex;align-items:center;justify-content:center;background:#F8FAFC;border:1px solid #E2E8F0;border-radius:6px;font-family:'JetBrains 
Mono',monospace;font-size:13px;font-weight:500;color:#0F172A;">
                    {st.session_state.pred_duration} Days
                </div>
                """,
                unsafe_allow_html=True,
            )
        with dm3:
            if st.button("+", key="duration_plus"):
                st.session_state.pred_duration = min(
                    14, int(st.session_state.pred_duration) + 1
                )

        r1, r2 = st.columns(2)
        with r1:
            st.number_input(
                "Rental Rate",
                min_value=0.01,
                step=0.10,
                key="pred_rental_rate",
            )
        with r2:
            st.number_input(
                "Late Fee per Day",
                min_value=0.01,
                step=0.05,
                key="pred_fee",
            )

        st.markdown(
            """
            <div class="section-card" style="margin-top:10px;">
                <div class="card-header" style="display:flex;align-items:center;justify-content:space-between;">
                    <div>
                        <div class="card-title">Business Constraints</div>
                    </div>
                </div>
                <div class="card-body">
            """,
            unsafe_allow_html=True,
        )

        current_range = None
        if st.session_state.scenario_result:
            current_range = st.session_state.scenario_result.get("fee_range", {})

        lower_fee = current_range.get("lower_bound") if current_range else None
        upper_fee = current_range.get("upper_bound") if current_range else None

        lower_text = money(lower_fee) if lower_fee is not None else "DB-derived"
        upper_text = money(upper_fee) if upper_fee is not None else "DB-derived"

        constraints_rows = [
            ["Min Rental Duration", "3 days"],
            ["Max Rental Duration", "7 days"],
            ["Observed Fee Range", f"{lower_text} - {upper_text}/day"],
        ]

        render_html_table(
            ["Constraint", "Value"],
            constraints_rows,
        )

        st.markdown("</div></div>", unsafe_allow_html=True)

        run = st.button(
            "Run Prediction & Optimize",
            key="run_prediction",
            type="primary",
            use_container_width=True,
        )

        if run:
            try:
                with st.spinner("Running prediction, simulation, and optimization..."):
                    run_policy_engine()
            except Exception as exc:
                st.error(str(exc))

    with right:
        prediction = st.session_state.prediction_result
        policy = st.session_state.policy_result
        scenarios = st.session_state.scenario_result

        if not prediction:
            st.markdown(
                """
                <div class="section-card" style="padding:28px;">
                    <div class="empty-state">
                        Configure the scenario inputs and run the existing prediction and optimization pipeline.
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            return

        probability = prediction["probability"]
        late_days = prediction["late_days"]
        simulation = prediction["simulation"]

        c1, c2, c3, c4 = st.columns(4)

        with c1:
            render_metric_card(
                "LATE-RETURN PROBABILITY",
                pct(probability.get("late_probability_pct")),
                badge=probability.get("risk_level", "—"),
                note="Prediction from the late-return classifier.",
                primary_badge=True,
            )

        with c2:
            render_metric_card(
                "EXPECTED LATE DAYS",
                f"{float(late_days.get('expected_late_days', 0)):.2f}",
                badge="Days",
                note="Predicted non-negative late duration.",
            )

        with c3:
            render_metric_card(
                "EXPECTED LATE-FEE REVENUE",
                money(simulation.get("expected_late_fee_revenue", 0)),
                badge=f"Fee {money(st.session_state.pred_fee)}/day",
                note="Current fee scenario estimate.",
            )

        with c4:
            render_metric_card(
                "EXPECTED TOTAL REVENUE",
                money(simulation.get("expected_total_revenue", 0)),
                badge=pct(simulation.get("revenue_change_pct", 0)),
                note="Expected rental revenue plus late-fee revenue.",
            )

        st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)

        if policy:
            recommendation = policy.get("recommendation")
            best = policy.get("best_policy") or {}
            reason = policy.get("reason", "")

            st.markdown(
                f"""
                <div class="result-panel">
                    <div class="result-badge">
                        <span class="material-symbols-outlined" style="font-size:13px;">auto_awesome</span>
                        AI OPTIMAL POLICY RECOMMENDATION
                    </div>

                    <div style="display:flex;justify-content:space-between;gap:16px;align-items:flex-start;margin-top:14px;">
                        <div>
                            <div class="policy-value">{html.escape(str(recommendation or "No feasible policy"))}</div>
                            <div class="policy-reason">{html.escape(str(reason))}</div>
                        </div>
                        <div class="metric-badge">
                            {html.escape(str(len(policy.get("feasible_scenarios", []))))} feasible scenarios
                        </div>
                    </div>

                    <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-top:16px;">
                        <div>
                            <div class="metric-label">POLICY TYPE</div>
                            <div style="margin-top:6px;font-family:'JetBrains Mono',monospace;font-size:13px;color:#0F172A;">
                                {html.escape(str(best.get("policy_type", "—")))}
                            </div>
                        </div>
                        <div>
                            <div class="metric-label">FEE / DAY</div>
                            <div style="margin-top:6px;font-family:'JetBrains Mono',monospace;font-size:13px;color:#0F172A;">
                                {money(best.get("fee_per_day", 0))}
                            </div>
                        </div>
                        <div>
                            <div class="metric-label">DURATION</div>
                            <div style="margin-top:6px;font-family:'JetBrains Mono',monospace;font-size:13px;color:#0F172A;">
                                {html.escape(str(best.get("rental_duration", "—")))} days
                            </div>
                        </div>
                        <div>
                            <div class="metric-label">UPLIFT</div>
                            <div style="margin-top:6px;font-family:'JetBrains Mono',monospace;font-size:13px;color:#312E81;">
                                {pct(best.get("revenue_change_pct", 0))}
                            </div>
                        </div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            a, b = st.columns([1, 2])
            with a:
                st.button(
                    "Apply Recommended Policy to POS",
                    disabled=True,
                    use_container_width=True,
                )
            with b:
                constraints = policy.get("constraints", {})
                st.markdown(
                    f"""
                    <div class="telemetry" style="margin-top:0;">
                        <div class="telemetry-row">
                            <span>Fee lower bound</span>
                            <span class="telemetry-value">{money(constraints.get('fee_lower_bound', 0))}/day</span>
                        </div>
                        <div class="telemetry-row">
                            <span>Fee upper bound</span>
                            <span class="telemetry-value">{money(constraints.get('fee_upper_bound', 0))}/day</span>
                        </div>
                        <div class="telemetry-row">
                            <span>Duration</span>
                            <span class="telemetry-value">{constraints.get('min_rental_duration', 3)}-{constraints.get('max_rental_duration', 7)} days</span>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

        st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

        st.markdown(
            """
            <div class="section-card">
                <div class="card-header">
                    <div class="card-title">Scenario Comparison &amp; Sensitivity Analysis</div>
                    <div class="card-subtitle">Expected revenue across fee and rental-duration scenarios generated by the current simulation pipeline.</div>
                </div>
                <div class="card-body">
            """,
            unsafe_allow_html=True,
        )

        all_scenarios = (scenarios or {}).get("all_scenarios", []) if scenarios else []

        if all_scenarios:
            scenario_df = pd.DataFrame(all_scenarios)
            scenario_df = scenario_df.head(8).copy()
            scenario_df["scenario_label"] = scenario_df.apply(
                lambda r: (
                    f"${float(r.get('fee_per_day', 0)):.2f} @ "
                    f"{int(r.get('rental_duration', 0))}d"
                ),
                axis=1,
            )

            chart = (
                alt.Chart(scenario_df)
                .mark_bar()
                .encode(
                    x=alt.X("scenario_label:N", sort=None, title=None),
                    y=alt.Y("expected_total_revenue:Q", title="Expected Revenue"),
                    color=alt.Color(
                        "policy:N",
                        scale=alt.Scale(range=["#312E81", "#64748B"]),
                        legend=None,
                    ),
                    tooltip=[
                        "scenario_label",
                        "expected_total_revenue",
                        "late_probability",
                        "expected_late_days",
                    ],
                )
                .properties(height=260)
            )

            st.altair_chart(chart, use_container_width=True)

            table_rows = []
            best_rank = all_scenarios[0].get("rank") if all_scenarios else None

            for row in all_scenarios[:8]:
                is_best = row.get("rank") == best_rank
                status = "Best" if is_best else "Scenario"
                table_rows.append(
                    [
                        f"${float(row.get('fee_per_day', 0)):.2f}/day",
                        f"{int(row.get('rental_duration', 0))} days",
                        pct(float(row.get("late_probability", 0)) * 100),
                        f"{float(row.get('expected_late_days', 0)):.2f}",
                        money(row.get("expected_total_revenue", 0)),
                        status,
                    ]
                )

            render_html_table(
                [
                    "Fee / Day",
                    "Rental Duration",
                    "Late Prob.",
                    "Expected Late Days",
                    "Expected Revenue",
                    "Status",
                ],
                table_rows,
                number_columns={4},
            )
        else:
            st.markdown(
                '<div class="empty-state">No scenario result returned by the current backend.</div>',
                unsafe_allow_html=True,
            )

        st.markdown("</div></div>", unsafe_allow_html=True)


# ============================================================
# AI ANALYST PAGE
# ============================================================

def prompt_button(label, question, icon):
    col = st.columns([1])[0]
    with col:
        clicked = st.button(
            label,
            key=f"prompt_{icon}_{label}",
            use_container_width=True,
        )
        if clicked:
            st.session_state.pending_question = question
            st.rerun()


def render_user_message(question, timestamp):
    st.markdown(
        f"""
        <div class="chat-user-row">
            <div class="chat-user-inner">
                <div style="min-width:0;">
                    <div class="chat-user-meta">
                        <span class="chat-user-name">Elena Vance</span>
                        <span class="chat-time">{html.escape(timestamp)}</span>
                    </div>
                    <div class="chat-user-bubble">{html.escape(question)}</div>
                </div>
                <img class="chat-avatar" src="{PROFILE_URL}" alt="Elena Vance"/>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )



def render_assistant_message(
    result,
    timestamp,
):

    if not isinstance(
        result,
        dict,
    ):
        result = {
            "answer": str(result)
        }

    with st.chat_message(
        "assistant"
    ):

        st.markdown(
            "**Sakila AI**"
        )

        answer = result.get(
            "answer",
            "",
        )

        if answer:

            st.markdown(
                str(answer)
            )

        else:

            st.warning(
                "The agent returned no answer."
            )

        render_agent_kpis(
            result.get(
                "kpis",
                [],
            )
        )

        for viz in (
            result.get(
                "visualizations",
                [],
            )
            or []
        ):

            render_agent_visualization(
                viz
            )

        for table in (
            result.get(
                "tables",
                [],
            )
            or []
        ):

            render_agent_table(
                table
            )

        render_agent_insights(
            result.get(
                "insights",
                [],
            )
            or []
        )

        trace = result.get(
            "tool_trace",
            [],
        ) or []

        st.caption(
            f"Generated {timestamp} · "
            f"{len(trace)} tool calls"
        )




def render_ai_analyst():

    # ========================================================
    # PROCESS NEW QUESTION FIRST
    # ========================================================

    pending = st.session_state.pop(
        "pending_question",
        None,
    )

    typed_question = st.chat_input(
        "Ask your business question..."
    )

    question = typed_question

    if not question and pending:
        question = pending

    if question:

        timestamp = datetime.now().strftime(
            "%H:%M"
        )

        # User message
        st.session_state.messages.append(
            {
                "role": "user",
                "content": question,
                "timestamp": timestamp,
            }
        )

        # Call the REAL backend agent
        try:

            with st.spinner(
                "Claude is analyzing Sakila data..."
            ):

                result = ask_claude(
                    question
                )

            if not isinstance(
                result,
                dict,
            ):
                result = {
                    "answer": str(result),
                    "kpis": [],
                    "visualizations": [],
                    "tables": [],
                    "insights": [],
                    "tool_trace": [],
                }

        except Exception as exc:

            result = {
                "answer": (
                    "The AI Agent could not "
                    "complete the request."
                ),
                "kpis": [],
                "visualizations": [],
                "tables": [],
                "insights": [
                    f"Agent error: {exc}"
                ],
                "tool_trace": [],
            }

            st.error(
                f"AI Agent error: {exc}"
            )

        # Assistant message
        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": result,
                "timestamp": datetime.now().strftime(
                    "%H:%M"
                ),
            }
        )


    # ========================================================
    # HEADER
    # ========================================================

    render_page_header(
        "AI Analyst",
        (
            "Ask questions in natural language. "
            "Claude chooses and executes the "
            "appropriate backend tools automatically."
        ),
        eyebrow="AUTONOMOUS BI ANALYST",
        model_note=(
            "ask_claude() · actual tool calling"
        ),
    )


    # ========================================================
    # WORKSPACE NAVIGATION
    # ========================================================

    st.markdown(
        "#### Workspace"
    )

    home_col, ai_col = st.columns(
        2,
        gap="medium",
    )

    with home_col:

        if st.button(
            "⌂  Home",
            key="ai_home_button",
            use_container_width=True,
        ):

            st.session_state.page = (
                "overview"
            )

            st.query_params["page"] = (
                "overview"
            )

            st.rerun()

    with ai_col:

        if st.button(
            "✦  AI Agent",
            key="ai_agent_button",
            use_container_width=True,
            type="primary",
        ):

            st.session_state.page = (
                "analyst"
            )

            st.query_params["page"] = (
                "analyst"
            )

            st.rerun()


    # ========================================================
    # SUGGESTED PROMPTS
    # ========================================================

    st.markdown(
        "#### Suggested Questions"
    )

    prompts = [

        (
            "Analyze revenue structure",
            "Analyze the current revenue structure.",
            "ai_prompt_revenue",
        ),

        (
            "Which categories drive late fees?",
            "Which categories generate the most late fee revenue?",
            "ai_prompt_latefee",
        ),

        (
            "Average rental rate by category",
            "What is the average rental rate by category?",
            "ai_prompt_rate",
        ),

        (
            "What policy maximizes revenue?",
            "What policy would maximize expected revenue?",
            "ai_prompt_policy",
        ),
    ]

    prompt_cols = st.columns(4)

    for i, (
        label,
        prompt,
        key,
    ) in enumerate(prompts):

        with prompt_cols[i]:

            if st.button(
                label,
                key=key,
                use_container_width=True,
            ):

                st.session_state.pending_question = (
                    prompt
                )

                st.rerun()


    # ========================================================
    # MAIN WORKSPACE
    # ========================================================

    chat_col, activity_col = st.columns(
        [1.8, 0.8],
        gap="large",
    )


    # ========================================================
    # LEFT: CHAT
    # ========================================================

    with chat_col:

        if not st.session_state.messages:

            with st.container(
                border=True
            ):

                st.markdown(
                    "### ✦ Sakila AI Analyst"
                )

                st.write(
                    "Ask about revenue, rentals, "
                    "late fees, categories, "
                    "pricing, simulation, "
                    "or policy optimization."
                )

                st.info(
                    "Use a suggested question above "
                    "or type your own question below."
                )

        else:

            for message in (
                st.session_state.messages
            ):

                role = message.get(
                    "role"
                )

                timestamp = message.get(
                    "timestamp",
                    "",
                )

                content = message.get(
                    "content",
                    "",
                )

                if role == "user":

                    with st.chat_message(
                        "user"
                    ):

                        st.markdown(
                            str(content)
                        )

                        st.caption(
                            timestamp
                        )

                else:

                    result = (
                        content
                        if isinstance(
                            content,
                            dict,
                        )
                        else {
                            "answer":
                            str(content)
                        }
                    )

                    render_assistant_message(
                        result,
                        timestamp,
                    )


    # ========================================================
    # RIGHT: ACTUAL AGENT ACTIVITY
    # ========================================================

    with activity_col:

        latest_trace = []

        for message in reversed(
            st.session_state.messages
        ):

            if (
                message.get("role")
                == "assistant"
            ):

                content = message.get(
                    "content"
                )

                if isinstance(
                    content,
                    dict,
                ):

                    latest_trace = (
                        content.get(
                            "tool_trace",
                            [],
                        )
                        or []
                    )

                break

        render_agent_activity(
            latest_trace
        )



# ============================================================
# ROUTING
# ============================================================

page = st.query_params.get("page", "overview")

if page not in {"overview", "predictions", "analyst"}:
    page = "overview"

render_sidebar(page)
render_top_header()

if page == "overview":
    render_overview()

elif page == "predictions":
    render_predictions()

else:
    render_ai_analyst()
