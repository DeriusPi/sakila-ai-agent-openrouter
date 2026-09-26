import html
import re
from datetime import datetime

import altair as alt
import pandas as pd
import streamlit as st

from llm import ask_claude, get_model_label

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
from tools.data.business_metrics import get_business_kpis
from tools.data.get_store_data import get_store_data
from tools.data.get_revenue_by_time import get_revenue_by_time

from tools.data.get_category_data import get_category_data
from tools.optimization.derive_fee_constraint import derive_fee_constraint
from tools.ml.predict_expected_late_days import predict_expected_late_days
from tools.ml.predict_late_probability import predict_late_probability
from tools.optimization.generate_policy_recommendation import (
    generate_policy_recommendation,
)
from tools.simulation.compare_scenarios import compare_scenarios
from tools.simulation.simulate_fee_policy import simulate_fee_policy
from textwrap import dedent


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

    /* Hide only the toolbar actions (Deploy / menu). The toolbar itself must
       stay visible: in Streamlit >= 1.4x it contains the ">>" button that
       re-opens a collapsed sidebar. */
    [data-testid="stToolbarActions"],
    [data-testid="stAppDeployButton"],
    [data-testid="stMainMenu"] {
        display: none;
    }

    [data-testid="stExpandSidebarButton"],
    [data-testid="stSidebarCollapsedControl"],
    [data-testid="collapsedControl"] {
        display: flex !important;
        visibility: visible !important;
        z-index: 1000000;
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

# Data-load errors are stored on the (persistent) db module so they
# survive Streamlit reruns and cached calls.
import time as _time

import db as _db

if not hasattr(_db, "RECENT_ERRORS"):
    _db.RECENT_ERRORS = []
    _db.LAST_CACHE_CLEAR = 0.0


def safe_call(func, default=None, *args, **kwargs):
    """
    Call a backend tool. Errors are no longer swallowed silently:
    they are logged and shown as a warning on the page instead of
    displaying $0 / "—" as if it were real data.
    """

    name = getattr(func, '__name__', 'tool')

    try:
        result = func(*args, **kwargs)
    except Exception as exc:  # noqa: BLE001
        message = f"{name}: {exc}"
        print(f"[App] Data load failed - {message}")
        _db.RECENT_ERRORS.append((_time.time(), message))
        del _db.RECENT_ERRORS[:-20]
        return default

    # FIX: once the tool works again (e.g. MySQL is back), forget its old
    # errors instead of showing a stale warning for 5 more minutes.
    _db.RECENT_ERRORS[:] = [
        (ts, msg) for ts, msg in _db.RECENT_ERRORS
        if not msg.startswith(f"{name}: ")
    ]
    return result


def render_data_errors():
    now = _time.time()
    recent = [
        (ts, msg) for ts, msg in _db.RECENT_ERRORS if now - ts < 300
    ]

    if not recent:
        return

    # Do not keep a failed (empty) result cached for 5 minutes:
    # clear the data cache so the next interaction retries MySQL.
    newest = max(ts for ts, _ in recent)
    if newest > _db.LAST_CACHE_CLEAR:
        st.cache_data.clear()
        _db.LAST_CACHE_CLEAR = now

    messages = list(dict.fromkeys(msg for _, msg in recent))

    st.warning(
        "Some data could not be loaded from MySQL, so parts of this page "
        "may be empty. Check DB_HOST / DB_USER / DB_PASSWORD / DB_NAME.\n\n"
        + "\n".join(f"- {err}" for err in messages[:5])
    )


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
def load_scope_kpis(category=None, store_id=None, start_date=None, end_date=None):
    """
    KPIs for any Overview scope (all / one category / one store /
    category + store, optionally for one time period) from ONE
    consistent SQL tool.
    """

    result = safe_call(
        get_business_kpis,
        {},
        category=category,
        store_id=store_id,
        start_date=start_date,
        end_date=end_date,
    )

    return result if isinstance(result, dict) else {}


@st.cache_data(ttl=300, show_spinner=False)
def load_category_rows(store_id=None, start_date=None, end_date=None):
    """Category revenue / late-fee rows for the selected store / period."""

    result = safe_call(
        get_category_data,
        [],
        store_id=store_id,
        start_date=start_date,
        end_date=end_date,
    )

    return result if isinstance(result, list) else []


@st.cache_data(ttl=300, show_spinner=False)
def load_store_rows(category=None, start_date=None, end_date=None):
    """Store rows for the selected category / period."""

    result = safe_call(
        get_store_data,
        [],
        category=category,
        start_date=start_date,
        end_date=end_date,
    )

    return result if isinstance(result, list) else []


ALL_TIME_LABEL = "All Time"

_MONTH_ABBR = [
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
]


@st.cache_data(ttl=300, show_spinner=False)
def load_period_options():
    """
    Time-slicer options built from the months that actually have
    payments in the database:
        All Time / Year 2005 / Year 2006 / May 2005 / ... / Feb 2006
    Each label maps to (start_date, end_date) accepted by the tools.
    """

    result = safe_call(get_revenue_by_time, {}, group_by="month")

    months = sorted(
        str(row.get("group"))
        for row in (
            result.get("grouped_revenue", [])
            if isinstance(result, dict)
            else []
        )
        if re.fullmatch(r"\d{4}-\d{2}", str(row.get("group", "")))
    )

    options = {ALL_TIME_LABEL: (None, None)}

    for year in sorted({m[:4] for m in months}):
        options[f"Year {year}"] = (year, year)

    for month in months:
        year, mm = month.split("-")
        options[f"{_MONTH_ABBR[int(mm) - 1]} {year}"] = (month, month)

    return options


def get_selected_period():
    """(label, start_date, end_date) of the Time Period slicer."""

    options = load_period_options()
    label = st.session_state.get("overview_period", ALL_TIME_LABEL)

    if label not in options:
        label = ALL_TIME_LABEL

    start_date, end_date = options.get(label, (None, None))

    return label, start_date, end_date


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

if "overview_period" not in st.session_state:
    st.session_state.overview_period = "All Time"




@st.cache_data(ttl=300, show_spinner=False)
def load_monthly_rental_trend(
    category=None,
    store_id=None,
    start_date=None,
    end_date=None,
    group_by="month",
):

    result = safe_call(
        get_revenue_by_time,
        {},
        start_date=start_date or "2005-05-01",
        end_date=end_date or "2006-02-28",
        group_by=group_by,
        category=category,
        store_id=store_id,
    )

    if not isinstance(result, dict):
        return pd.DataFrame(
            columns=[
                "month",
                "revenue",
                "transaction_count",
            ]
        )

    rows = result.get(
        "grouped_revenue",
        [],
    ) or []

    if not rows:
        return pd.DataFrame(
            columns=[
                "month",
                "revenue",
                "transaction_count",
            ]
        )

    trend = pd.DataFrame(rows)

    if "group" not in trend.columns:
        return pd.DataFrame(
            columns=[
                "month",
                "revenue",
                "transaction_count",
            ]
        )

    trend = trend.rename(
        columns={
            "group": "month",
            "revenue": "revenue",
        }
    )

    if "transaction_count" not in trend.columns:
        trend["transaction_count"] = 0

    trend["revenue"] = pd.to_numeric(
        trend["revenue"],
        errors="coerce",
    ).fillna(0)

    trend["transaction_count"] = pd.to_numeric(
        trend["transaction_count"],
        errors="coerce",
    ).fillna(0).astype(int)

    return trend[
        [
            "month",
            "revenue",
            "transaction_count",
        ]
    ].sort_values("month")


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
        f"""
        <div class="top-header">
            <div class="system-badge">
                <span class="status-dot"></span>
                <span class="mono">
                    Sakila MySQL · Agent: {html.escape(get_model_label())}
                </span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    period_options = list(load_period_options().keys())

    if st.session_state.get("overview_period") not in period_options:
        st.session_state.overview_period = ALL_TIME_LABEL

    c1, c2, c_time, c3, c4 = st.columns(
        [2.6, 2.0, 2.0, 2.4, 0.55],
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

    with c_time:

        st.markdown(
            '<div class="top-control-label">'
            'Time Period'
            '</div>',
            unsafe_allow_html=True,
        )

        st.selectbox(
            "Time Period",
            period_options,
            key="overview_period",
            label_visibility="collapsed",
            help=(
                "Revenue is filtered by payment date, rentals and late "
                "returns by rental date. Sakila only has data for "
                "May-Aug 2005 and Feb 2006."
            ),
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

        selected_period = st.session_state.get(
            "overview_period", ALL_TIME_LABEL
        )

        if selected_period != ALL_TIME_LABEL:
            scope_text = (
                selected_period
                if scope_text == "Full Sakila dataset"
                else f"{scope_text} · {selected_period}"
            )

        st.markdown(
            f'<div class="data-scope-chip">'
            f'{html.escape(scope_text)}'
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
            width="stretch",
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
        width="stretch",
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
        width="stretch",
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
        width="stretch",
        type=(
            "primary"
            if page == "analyst"
            else "secondary"
        ),
    ):
        st.session_state.page = "analyst"
        st.query_params["page"] = "analyst"
        st.rerun()

    activity_placeholder = st.sidebar.empty()

    with activity_placeholder.container():
        st.markdown("### Agent Activity")
        st.caption("READY")

    return activity_placeholder

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
    subtitle_html = (
        f'<div class="card-subtitle">{html.escape(subtitle)}</div>'
        if subtitle
        else ""
    )
    st.markdown(
        '<div class="section-card"><div class="card-header">'
        f'<div class="card-title">{html.escape(title)}</div>'
        f"{subtitle_html}</div>"
        f'<div class="card-body">{body_html}</div></div>',
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

def _to_float_or_none(value):
    """'$1,707.97' / '51.2%' / 1707.97 -> float, otherwise None."""

    if isinstance(value, bool):
        return None

    if isinstance(value, (int, float)):
        return float(value)

    if isinstance(value, str):
        text = (
            value.replace("$", "")
            .replace(",", "")
            .replace("%", "")
            .strip()
        )
        try:
            return float(text)
        except ValueError:
            return None

    return None


_MONTH_NAMES = {
    name: i + 1
    for i, names in enumerate([
        ("jan", "january"), ("feb", "february"), ("mar", "march"),
        ("apr", "april"), ("may",), ("jun", "june"), ("jul", "july"),
        ("aug", "august"), ("sep", "sept", "september"), ("oct", "october"),
        ("nov", "november"), ("dec", "december"),
    ])
    for name in names
}


def _time_sort_key(value):
    """
    Returns a sortable (year, month, day) tuple when the label looks like a
    period ("2005-07", "2005-07-15", "07/2005", "Tháng 7/2005", "Jul 2005",
    "2005-Q3", "2005-W28", "2005"), otherwise None.
    """

    text = str(value).strip().lower()
    if not text:
        return None

    m = re.fullmatch(r"(\d{4})-(\d{1,2})-(\d{1,2})(?:[ t].*)?", text)
    if m:
        return (int(m[1]), int(m[2]), int(m[3]))

    m = re.fullmatch(r"(\d{4})[-/.](\d{1,2})", text)
    if m:
        return (int(m[1]), int(m[2]), 0)

    m = re.fullmatch(r"(\d{4})-?w(\d{1,2})", text)
    if m:
        return (int(m[1]), 0, int(m[2]))

    m = re.fullmatch(r"(\d{4})[- ]?q([1-4])|q([1-4])[- /]?(\d{4})", text)
    if m:
        year = int(m[1] or m[4])
        quarter = int(m[2] or m[3])
        return (year, quarter * 3 - 2, 0)

    m = re.fullmatch(r"(\d{1,2})[-/.](\d{1,2})[-/.](\d{4})", text)
    if m:
        return (int(m[3]), int(m[2]), int(m[1]))

    m = re.fullmatch(r"(?:tháng|thang|t|month|m)?\s*(\d{1,2})\s*[-/.,]?\s*(?:năm|nam)?\s*(\d{4})", text)
    if m and 1 <= int(m[1]) <= 12:
        return (int(m[2]), int(m[1]), 0)

    m = re.fullmatch(r"([a-z]+)\.?[\s,-]*(\d{4})", text)
    if m and m[1] in _MONTH_NAMES:
        return (int(m[2]), _MONTH_NAMES[m[1]], 0)

    m = re.fullmatch(r"(\d{4})[\s,-]*([a-z]+)\.?", text)
    if m and m[2] in _MONTH_NAMES:
        return (int(m[1]), _MONTH_NAMES[m[2]], 0)

    if re.fullmatch(r"(19|20)\d{2}", text):
        return (int(text), 0, 0)

    m = re.fullmatch(r"(?:tháng|thang|month)\s*(\d{1,2})", text)
    if m and 1 <= int(m[1]) <= 12:
        return (0, int(m[1]), 0)

    if text in _MONTH_NAMES:
        return (0, _MONTH_NAMES[text], 0)

    return None


def _chronological_order(values):
    """Ordered list of x labels if every label is a period, else None."""

    unique = list(dict.fromkeys(str(v) for v in values))
    keys = {v: _time_sort_key(v) for v in unique}

    if not unique or any(k is None for k in keys.values()):
        return None

    return sorted(unique, key=lambda v: keys[v])


def render_agent_kpis(kpis):
    # FIX: the model sometimes returns KPI strings instead of objects,
    # which crashed the page with AttributeError.
    kpis = [
        kpi if isinstance(kpi, dict) else {"label": "Metric", "value": kpi}
        for kpi in (kpis or [])
        if kpi not in (None, "")
    ]

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
    """
    FIX:
      - numbers sent as strings ("1,707.97", "$4,823.44") were plotted as
        empty charts -> coerced to numbers;
      - field names with ':' or '.' broke Altair shorthand -> use
        field=/type= encodings;
      - missing x_key/y_key are inferred from the data;
      - bar chart width adapts to the number of bars instead of a fixed
        1100px (horizontal overflow on small screens).
    """

    if not isinstance(viz, dict):
        return

    title = viz.get("title", "Visualization")
    description = viz.get("description", "")
    chart_type = str(viz.get("type", "bar")).lower()
    data = viz.get("data", [])
    x_key = viz.get("x_key")
    y_key = viz.get("y_key")
    x_label = viz.get("x_label")
    y_label = viz.get("y_label")

    if not isinstance(data, list) or not data:
        return

    rows = [row for row in data if isinstance(row, dict)]

    if not rows:
        return

    df = pd.DataFrame(rows)
    if df.empty:
        return

    if x_key not in df.columns:
        x_key = next(
            (c for c in df.columns if df[c].map(_to_float_or_none).isna().any()),
            df.columns[0],
        )

    if y_key not in df.columns:
        y_key = next(
            (
                c for c in df.columns
                if c != x_key and df[c].map(_to_float_or_none).notna().all()
            ),
            None,
        )

    # FIX: build the header on one line - an empty indented line (when
    # there is no description) made Markdown render a stray "</div>"
    # code block above the chart.
    subtitle_html = (
        f'<div class="card-subtitle">{html.escape(str(description))}</div>'
        if description
        else ""
    )

    st.markdown(
        '<div class="section-card" style="margin-top:14px;">'
        '<div class="card-header">'
        f'<div class="card-title">{html.escape(str(title))}</div>'
        f"{subtitle_html}"
        "</div></div>",
        unsafe_allow_html=True,
    )

    if y_key is None or x_key not in df.columns:
        st.dataframe(df, width="stretch", hide_index=True)
        return

    df[y_key] = df[y_key].map(_to_float_or_none)
    df = df[df[y_key].notna()]
    df[x_key] = df[x_key].astype(str)

    if df.empty:
        st.info("The chart data returned by the agent is not numeric.")
        return

    x_title = x_label or None
    y_title = y_label or None

    # FIX: time periods (months, dates, quarters...) must be shown in
    # chronological order, not ranked by value. Categories keep the
    # largest-first ranking.
    time_order = _chronological_order(df[x_key])
    if time_order is not None:
        position = {v: i for i, v in enumerate(time_order)}
        df = df.assign(_order=df[x_key].map(position)).sort_values(
            "_order", kind="stable"
        ).drop(columns="_order")
        bar_sort = time_order
        line_sort = time_order
    else:
        bar_sort = "-y"
        line_sort = None

    tooltip = [
        alt.Tooltip(field=x_key, type="nominal"),
        alt.Tooltip(field=y_key, type="quantitative", format=",.2f"),
    ]

    if chart_type == "bar":
        bar_count = len(df)
        chart = (
            alt.Chart(df)
            .mark_bar(color="#312E81")
            .encode(
                x=alt.X(
                    field=x_key,
                    type="nominal",
                    sort=bar_sort,
                    title=x_title,
                    axis=alt.Axis(
                        labelAngle=0 if bar_count <= 8 else -40,
                        labelOverlap=False,
                        labelLimit=140,
                    ),
                ),
                y=alt.Y(field=y_key, type="quantitative", title=y_title),
                tooltip=tooltip,
            )
            .properties(height=300)
        )
        st.altair_chart(chart)

    elif chart_type == "line":
        chart = (
            alt.Chart(df)
            .mark_line(color="#312E81", strokeWidth=2, point=True)
            .encode(
                x=alt.X(
                    field=x_key,
                    type="nominal",
                    sort=line_sort,
                    title=x_title,
                    axis=alt.Axis(labelAngle=0, labelOverlap=False),
                ),
                y=alt.Y(field=y_key, type="quantitative", title=y_title),
                tooltip=tooltip,
            )
            .properties(height=260)
        )
        st.altair_chart(chart)

    elif chart_type == "pie":
        chart = (
            alt.Chart(df)
            .mark_arc(innerRadius=55)
            .encode(
                theta=alt.Theta(field=y_key, type="quantitative"),
                color=alt.Color(
                    field=x_key,
                    type="nominal",
                    scale=alt.Scale(range=["#312E81", "#64748B", "#94A3B8", "#CBD5E1"]),
                    legend=alt.Legend(title=None),
                ),
                tooltip=tooltip,
            )
            .properties(height=260)
        )
        st.altair_chart(chart)

    else:
        st.dataframe(df, width="stretch", hide_index=True)


def render_agent_table(table):
    if not isinstance(table, dict):
        return

    title = table.get("title", "Data")
    rows = table.get("rows", [])
    columns = table.get("columns") or None

    if not rows:
        return

    # FIX: rows given as lists (with a separate "columns" list) used to
    # render with 0,1,2 headers or fail.
    if all(isinstance(row, (list, tuple)) for row in rows):
        width = len(rows[0])
        if not columns or len(columns) != width:
            columns = [f"Col {i + 1}" for i in range(width)]
        df = pd.DataFrame(rows, columns=columns)
    else:
        df = pd.DataFrame([row for row in rows if isinstance(row, dict)])
        if columns and set(columns).issubset(df.columns):
            df = df[columns]

    if df.empty:
        return

    # FIX: a table whose first column is a time period (months, dates...)
    # is shown in chronological order.
    first_col = df.columns[0]
    time_order = _chronological_order(df[first_col].astype(str))
    if time_order is not None:
        position = {v: i for i, v in enumerate(time_order)}
        df = df.assign(_order=df[first_col].astype(str).map(position)).sort_values(
            "_order", kind="stable"
        ).drop(columns="_order")

    st.markdown(
        f"""
        <div style="margin-top:14px;">
            <div class="label" style="margin-bottom:7px;">{html.escape(str(title))}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.dataframe(df, width="stretch", hide_index=True)


def render_agent_insights(insights):
    items = []

    for insight in insights or []:
        if isinstance(insight, dict):
            text = " — ".join(
                str(insight.get(k))
                for k in ("title", "text", "insight", "description")
                if insight.get(k)
            )
        else:
            text = str(insight or "").strip()

        if text:
            items.append(text)

    if not items:
        return

    st.markdown(
        '<div class="label" style="margin:16px 0 8px;">KEY FINDINGS & ACTION ITEMS</div>',
        unsafe_allow_html=True,
    )

    cols = st.columns(min(len(items), 3))
    for index, insight in enumerate(items):
        with cols[index % len(cols)]:
            st.markdown(
                f"""
                <div class="insight-card">
                    <div class="insight-title">{index + 1}. Insight</div>
                    <div class="insight-text">{html.escape(insight)}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def _compact_activity_text(
    value,
    limit=520,
):
    text = str(value or "")
    text = text.replace("\n", " ").strip()

    if len(text) > limit:
        return text[:limit] + "..."

    return text


def _activity_event_view(event):
    if not isinstance(event, dict):
        return (
            "PROCESS",
            _compact_activity_text(event),
        )

    name = str(
        event.get("event", "")
    ).lower()

    labels = {
        "question_received": "QUESTION RECEIVED",
        "mode": "MODE DETECTED",
        "agent_decision": "AGENT DECISION",
        "tool_selected": "TOOL SELECTED",
        "tool_call": "EXECUTING BI TOOL",
        "tool_output": "BI OUTPUT RECEIVED",
        "tool_completed": "TOOL COMPLETED",
        "next_step": "NEXT AGENT STEP",
        "synthesis_started": "SYNTHESIZING ANSWER",
        "answer_ready": "ANSWER READY",
        "completed": "COMPLETED",
        "error": "ERROR",
    }

    label = labels.get(
        name,
        name.upper() or "PROCESS",
    )

    if name == "question_received":
        return (
            label,
            _compact_activity_text(
                event.get("question", "")
            ),
        )

    if name == "mode":
        return (
            label,
            f"Mode: {event.get('mode', '')}",
        )

    if name == "agent_decision":
        tools = event.get(
            "tools",
            [],
        ) or []

        return (
            label,
            f"Round {event.get('round', '?')} · "
            f"Selected: "
            f"{', '.join(str(x) for x in tools) or 'no tool'}",
        )

    if name == "tool_selected":
        return (
            label,
            f"{event.get('tool', 'unknown')} · "
            f"Input: "
            f"{_compact_activity_text(event.get('input', {}), 360)}",
        )

    if name == "tool_call":
        return (
            label,
            f"Running {event.get('tool', 'unknown')}",
        )

    if name == "tool_output":
        return (
            label,
            _compact_activity_text(
                event.get("output", ""),
                700,
            ),
        )

    if name == "tool_completed":
        status = str(
            event.get(
                "status",
                "unknown",
            )
        ).upper()

        error = event.get(
            "error",
            "",
        )

        if error:
            return (
                label,
                f"{status} · "
                f"{_compact_activity_text(error, 260)}",
            )

        return (
            label,
            status,
        )

    if name == "next_step":
        return (
            label,
            f"Round {event.get('round', '?')} · "
            f"{event.get('tool_count', 0)} "
            f"tool result(s) returned to Agent",
        )

    if name == "synthesis_started":
        return (
            label,
            f"{event.get('tool_count', 0)} tool call(s) · "
            f"{event.get('rounds', 0)} round(s)",
        )

    if name == "answer_ready":
        sections = []

        if event.get("has_kpis"):
            sections.append("KPI")

        if event.get("has_visualizations"):
            sections.append("Visualization")

        if event.get("has_tables"):
            sections.append("Table")

        if event.get("has_insights"):
            sections.append("Insights")

        return (
            label,
            "Prepared: "
            + (
                ", ".join(sections)
                if sections
                else "Answer"
            ),
        )

    if name == "completed":
        return (
            label,
            f"{event.get('tool_count', 0)} tool call(s)",
        )

    if name == "error":
        return (
            label,
            _compact_activity_text(
                event.get("error", "")
            ),
        )

    return (
        label,
        _compact_activity_text(
            event.get("detail", "")
        ),
    )


def _activity_text(
    value,
    limit=420,
):
    text = str(value or "")
    text = text.replace("\n", " ").strip()

    if len(text) > limit:
        return text[:limit] + "..."

    return text


def _activity_symbol(status):
    status = str(
        status or "READY"
    ).upper()

    if status == "RUNNING":
        return "◌", "#4F46E5"

    if status == "SUCCESS":
        return "✓", "#334155"

    if status == "ERROR":
        return "!", "#B91C1C"

    return "•", "#64748B"


def render_live_agent_activity(
    placeholder,
    state,
):
    status = str(
        state.get(
            "status",
            "READY",
        )
    ).upper()

    steps = state.get(
        "steps",
        [],
    ) or []

    if status == "RUNNING":
        status_badge = "RUNNING"
        badge_color = "#4338CA"

    elif status == "ERROR":
        status_badge = "ERROR"
        badge_color = "#B91C1C"

    elif status == "COMPLETED":
        status_badge = "COMPLETED"
        badge_color = "#334155"

    else:
        status_badge = "READY"
        badge_color = "#64748B"

    rows = []

    if not steps:
        rows.append(
            dedent(
                """
                <div style="
                    padding:6px 12px;
                    font:500 9px 'JetBrains Mono',monospace;
                    color:#64748B;
                ">
                    ● Processing user request
                </div>
                """
            )
        )

    for step in steps[-30:]:
        label = html.escape(
            str(
                step.get(
                    "label",
                    step.get(
                        "tool",
                        "unknown",
                    ),
                )
            )
        )

        step_status = str(
            step.get(
                "status",
                "READY",
            )
        ).upper()

        symbol, symbol_color = _activity_symbol(
            step_status
        )

        detail = _activity_text(
            step.get(
                "detail",
                "",
            ),
            420,
        )

        detail_html = ""

        if detail:
            detail_html = (
                f"""
                <div style="
                    margin-top:3px;
                    padding-left:20px;
                    color:#94A3B8;
                    font-size:8px;
                    line-height:1.35;
                    overflow:hidden;
                    text-overflow:ellipsis;
                    white-space:nowrap;
                ">
                    {html.escape(detail)}
                </div>
                """
            )

        rows.append(
            dedent(
                f"""
                <div style="
                    display:flex;
                    justify-content:space-between;
                    align-items:flex-start;
                    gap:8px;
                    padding:7px 12px;
                    border-bottom:1px solid #F8FAFC;
                    font:500 9px 'JetBrains Mono',monospace;
                ">
                    <div style="
                        min-width:0;
                        flex:1;
                    ">
                        <div style="
                            color:#334155;
                            display:flex;
                            align-items:center;
                            min-width:0;
                        ">
                            <span style="
                                color:{symbol_color};
                                font-size:12px;
                                margin-right:5px;
                                flex-shrink:0;
                            ">
                                {symbol}
                            </span>
                            <span style="
                                overflow:hidden;
                                text-overflow:ellipsis;
                                white-space:nowrap;
                            ">
                                {label}
                            </span>
                        </div>
                        {detail_html}
                    </div>

                    <span style="
                        color:{symbol_color};
                        font-size:8px;
                        white-space:nowrap;
                        flex-shrink:0;
                    ">
                        {step_status}
                    </span>
                </div>
                """
            )
        )

    html_block = dedent(
        f"""
        <div style="
            width:100%;
            box-sizing:border-box;
            background:#FFFFFF;
            margin-top:8px;
        ">

            <div style="
                display:flex;
                justify-content:space-between;
                align-items:center;
                padding:8px 12px;
                border-bottom:1px solid #E2E8F0;
            ">

                <div style="
                    display:flex;
                    align-items:center;
                    gap:7px;
                    color:#0F172A;
                    font:600 10px 'JetBrains Mono',monospace;
                ">

                    <span class="material-symbols-outlined"
                          style="font-size:18px;">
                        tune
                    </span>

                    <span>Agent Activity</span>

                </div>

                <span style="
                    font:600 8px 'JetBrains Mono',monospace;
                    color:{badge_color};
                ">
                    {status_badge}
                </span>

            </div>

            {''.join(rows)}


        </div>
        """
    )

    html_block = "\n".join(
        line.lstrip()
        for line in html_block.splitlines()
    )

    placeholder.markdown(
        html_block,
        unsafe_allow_html=True,
    )



def render_agent_activity(
    trace,
    events=None,
):
    trace = trace or []
    events = events or []

    completed = any(
        isinstance(event, dict)
        and event.get("event") == "completed"
        for event in events
    )

    status = (
        "COMPLETED"
        if completed or trace
        else "READY"
    )

    with st.container(
        border=True,
    ):
        left, right = st.columns(
            [3, 1]
        )

        with left:
            st.markdown(
                "### Agent Activity"
            )

        with right:
            st.caption(status)

        st.caption(
            "FULL AGENT PROCESS"
        )

        if events:
            for event in events[-30:]:
                label, detail = _activity_event_view(
                    event
                )

                st.markdown(
                    f"**{label}**"
                )

                if detail:
                    if label == "BI OUTPUT RECEIVED":
                        st.code(
                            detail,
                            language="text",
                        )
                    else:
                        st.caption(
                            detail
                        )

        elif trace:
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

                status_text = str(
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
                        f"✓ `{tool}`"
                    )

                with c2:
                    st.caption(
                        status_text
                    )

        else:
            st.info(
                "No Agent activity in the current session."
            )

        tool_count = sum(
            1
            for event in events
            if isinstance(event, dict)
            and event.get("event")
            == "tool_selected"
        )

        if not tool_count:
            tool_count = len(trace)

        st.caption(
            "Agent telemetry"
        )

        c1, c2, c3 = st.columns(3)

        with c1:
            st.metric(
                "Model",
                get_model_label(),
            )

        with c2:
            st.metric(
                "Data Source",
                "Sakila MySQL",
            )

        with c3:
            st.metric(
                "Tool Calls",
                tool_count,
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

    # ========================================================
    # SCOPE (category and/or store and/or time period)
    # ========================================================
    #
    # FIX: all KPIs now come from get_business_kpis() for the selected
    # scope. Previously:
    #   - with a store selected, "Rental revenue" showed the store's
    #     TOTAL revenue and late fees / late rate showed "—";
    #   - with a category selected, the late rate used a DATEDIFF rule
    #     that did not match the overall 51.20% definition;
    #   - with both selected, the category filter was ignored;
    #   - the revenue trend ignored both filters.

    selected_category_name = (
        None
        if selected_category == "All Film Categories"
        else selected_category
    )

    selected_store_id = None

    if selected_store != "All Stores":
        try:
            selected_store_id = int(
                str(selected_store).replace("Store #", "").strip()
            )
        except Exception:
            selected_store_id = None

    period_label, period_start, period_end = get_selected_period()

    scope_kpis = load_scope_kpis(
        selected_category_name,
        selected_store_id,
        period_start,
        period_end,
    )

    # Category rows for the category panels (store- and period-scoped,
    # so the panels match the KPI cards).
    category_rows = load_category_rows(
        selected_store_id,
        period_start,
        period_end,
    )

    # Store rows for the store panel (category- and period-scoped).
    stores = load_store_rows(
        selected_category_name,
        period_start,
        period_end,
    )

    selected_category_row = None

    if selected_category_name:
        for row in category_rows:
            if row.get("category") == selected_category_name:
                selected_category_row = row
                break

    selected_store_row = None

    if selected_store_id is not None:
        for row in stores:
            try:
                if int(row.get("store_id", -1)) == selected_store_id:
                    selected_store_row = row
                    break
            except Exception:
                continue

    total_revenue = float(scope_kpis.get("total_revenue", 0) or 0)
    rental_revenue = float(scope_kpis.get("rental_revenue", 0) or 0)
    late_fee_revenue = float(scope_kpis.get("late_fee_revenue", 0) or 0)
    late_fee_pct = float(
        scope_kpis.get("late_fee_contribution_pct", 0) or 0
    )
    total_rentals = int(scope_kpis.get("completed_rentals", 0) or 0)
    late_rentals = int(scope_kpis.get("late_rentals", 0) or 0)
    late_rate = float(scope_kpis.get("late_rate_pct", 0) or 0)
    payment_count = int(scope_kpis.get("payment_count", 0) or 0)

    scope_parts = []

    if selected_store_id is not None:
        scope_parts.append(f"Store #{selected_store_id}")

    if selected_category_name:
        scope_parts.append(f"Category: {selected_category_name}")

    if period_start or period_end:
        scope_parts.append(period_label)

    scope_note = (
        " · ".join(scope_parts)
        if scope_parts
        else "Full Sakila dataset"
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

    render_data_errors()

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
            width="stretch",
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
        render_metric_card(
            "TOTAL REVENUE",
            money(total_revenue),
            badge="Observed",
            note=f"{scope_note} · {payment_count:,} payments",
            primary_badge=True,
        )

    with k2:
        render_metric_card(
            "RENTAL REVENUE",
            money(rental_revenue),
            badge="Observed",
            note="Payments up to the film rental rate.",
        )

    with k3:
        render_metric_card(
            "LATE-FEE REVENUE",
            money(late_fee_revenue),
            badge=pct(late_fee_pct),
            note="Payment amount above the film rental rate.",
        )

    with k4:
        render_metric_card(
            "LATE-FEE CONTRIBUTION",
            pct(late_fee_pct),
            badge="Of selected scope",
            note="Late-fee share of observed revenue.",
        )

    with k5:
        render_metric_card(
            "LATE-RETURN RATE",
            pct(late_rate),
            badge=f"{late_rentals:,} late rentals",
            note=(
                f"Across {total_rentals:,} completed rentals."
                if total_rentals
                else "No returned rentals in this period yet."
            ),
        )

    # ========================================================
    # REVENUE TREND
    # ========================================================

    # One month selected -> daily trend; otherwise monthly.
    single_month = bool(
        period_start
        and period_start == period_end
        and re.fullmatch(r"\d{4}-\d{2}", str(period_start))
    )
    trend_grain = "day" if single_month else "month"

    trend_df = load_monthly_rental_trend(
        selected_category_name,
        selected_store_id,
        period_start,
        period_end,
        trend_grain,
    )

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
                        Total revenue from payment.amount grouped by
                        payment.payment_date (monthly, or daily when one
                        month is selected).
                    </div>
                </div>
                <div class="card-body">
            """,
            unsafe_allow_html=True,
        )

        if trend_df.empty:

            st.markdown(
                '<div class="empty-state">'
                'No revenue series was returned by '
                'the backend data tool.'
                '</div>',
                unsafe_allow_html=True,
            )

        else:

            # Daily view uses bars: Sakila has gaps between payment days,
            # and a line would suggest values on days without data.
            base = alt.Chart(trend_df)
            marked = (
                base.mark_bar(color="#312E81")
                if trend_grain == "day"
                else base.mark_line(
                    point=True,
                    color="#312E81",
                    strokeWidth=2,
                )
            )

            chart = (
                marked
                .encode(
                    x=alt.X(
                        "month:N",
                        title=None,
                        sort=None,
                        axis=alt.Axis(
                            labelAngle=0 if trend_grain == "month" else -45,
                            labelOverlap=True,
                        ),
                    ),
                    y=alt.Y(
                        "revenue:Q",
                        title="Total Revenue",
                    ),
                    tooltip=[
                        alt.Tooltip(
                            "month:N",
                            title="Day" if trend_grain == "day" else "Month",
                        ),
                        alt.Tooltip(
                            "revenue:Q",
                            title="Revenue",
                            format="$,.2f",
                        ),
                        alt.Tooltip(
                            "transaction_count:Q",
                            title="Payments",
                            format=",",
                        ),
                    ],
                )
                .properties(
                    height=280
                )
            )

            st.altair_chart(chart)

            st.markdown(
                '<div class="card-subtitle">'
                f'Scope: {html.escape(scope_note)}. Sakila has no '
                'payments between 2005-09 and 2006-01.'
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
                        Film catalogue average (not affected by the
                        store / time filters).
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

            location = ", ".join(
                str(x)
                for x in (store.get("city"), store.get("country"))
                if x
            )

            rows.append(
                [
                    f"Store #{store.get('store_id', '—')}"
                    + (f" · {location}" if location else ""),
                    f"{int(store.get('total_rentals', 0) or 0):,}",
                    money(store.get("total_revenue", 0)),
                    money(store.get("late_fee_revenue", 0)),
                    pct(store.get("late_rate_pct", 0)),
                ]
            )

        if rows:

            render_html_table(
                [
                    "Store",
                    "Rentals",
                    "Total Revenue",
                    "Late Fees",
                    "Late Rate",
                ],
                rows,
                number_columns={1, 2, 3, 4},
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
        if st.button("Preset Scenarios", key="preset_btn", width="stretch"):
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
        if st.button("Reset Defaults", key="reset_btn", width="stretch"):
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

        if not 3 <= int(st.session_state.pred_duration) <= 7:
            st.caption(
                "⚠ The ML models were trained on 3-7 day rentals; "
                "other durations are extrapolations."
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

        # FIX: show the DB-derived range even before the engine has run
        # (it used to display "DB-derived - DB-derived/day").
        if not current_range:
            current_range = load_fee_constraints()

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
            width="stretch",
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
                            <div class="policy-value">{recommendation or "No feasible policy"}</div>
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
                    width="stretch",
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
            scenario_df = scenario_df.head(12).copy()
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
                        "policy_type:N",
                        scale=alt.Scale(
                            domain=["current", "fee", "rental_duration"],
                            range=["#94A3B8", "#312E81", "#64748B"],
                        ),
                        legend=alt.Legend(title=None, orient="bottom"),
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

            st.altair_chart(chart)

            table_rows = []
            best_rank = all_scenarios[0].get("rank") if all_scenarios else None

            for row in all_scenarios[:12]:
                is_best = row.get("rank") == best_rank
                if is_best:
                    status = "Best"
                elif row.get("policy_type") == "current":
                    status = "Current"
                else:
                    status = "Scenario"
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
            width="stretch",
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

        data_check = result.get("data_check") or {}
        unverified = data_check.get("unverified_kpis") or []

        if unverified:
            st.caption(
                "⚠ Data check: these KPI values were not found directly "
                "in the tool results (they may be derived or incorrect): "
                + ", ".join(str(x) for x in unverified)
            )

        if trace and not any(
            str(t.get("status")) == "success" for t in trace
        ):
            st.caption("⚠ No tool call succeeded for this answer.")

        st.caption(
            f"Generated {timestamp} · "
            f"{len(trace)} tool calls"
            + (
                f" · {result.get('model')}"
                if result.get("model")
                else ""
            )
        )




def record_activity_event(event):
    """
    Store an agent activity event in the session.

    FIX: this function was called in the error handler of
    render_ai_analyst() but was never defined, so every agent error
    (e.g. an OpenRouter rate limit) crashed the page with NameError
    instead of showing the error message.
    """

    if not isinstance(event, dict):
        return

    events = list(st.session_state.get("agent_activity_events", []) or [])
    events.append(event)
    st.session_state["agent_activity_events"] = events[-200:]


def render_ai_analyst(activity_placeholder=None):


    persisted_events = list(
        st.session_state.get(
            "agent_activity_events",
            [],
        ) or []
    )

    saved_state = st.session_state.get(
        "agent_activity_state",
        None,
    )

    if isinstance(
        saved_state,
        dict,
    ):
        activity_state = {
            "status": saved_state.get(
                "status",
                "READY",
            ),
            "steps": list(
                saved_state.get(
                    "steps",
                    [],
                ) or []
            ),
            "mode": saved_state.get(
                "mode",
                None,
            ),
        }
    else:
        activity_state = {
            "status": "READY",
            "steps": [],
            "mode": None,
        }

    def save_activity_state():
        st.session_state[
            "agent_activity_state"
        ] = {
            "status": activity_state.get(
                "status",
                "READY",
            ),
            "steps": list(
                activity_state.get(
                    "steps",
                    [],
                ) or []
            ),
            "mode": activity_state.get(
                "mode",
                None,
            ),
        }

    def find_running_tool(tool_name):
        for step in reversed(
            activity_state["steps"]
        ):
            if (
                step.get("kind") == "tool"
                and step.get("tool") == tool_name
                and str(
                    step.get("status")
                ).upper() == "RUNNING"
            ):
                return step

        return None

    def find_step(kind):
        for step in reversed(
            activity_state["steps"]
        ):
            if step.get("kind") == kind:
                return step

        return None

    def add_step(
        label,
        status="SUCCESS",
        detail="",
        kind="process",
        tool=None,
    ):
        activity_state["steps"].append(
            {
                "label": label,
                "status": status,
                "detail": detail,
                "kind": kind,
                "tool": tool,
            }
        )

    def handle_activity_event(event):
        if not isinstance(
            event,
            dict,
        ):
            return

        event_name = str(
            event.get(
                "event",
                "",
            )
        ).lower()

        if event_name == "question_received":
            add_step(
                "Understanding question",
                "RUNNING",
                _activity_text(
                    event.get(
                        "question",
                        "",
                    )
                ),
                "question",
            )

        elif event_name == "mode":
            understanding = find_step("question")
            if understanding is not None:
                understanding["status"] = "SUCCESS"
            activity_state["mode"] = event.get(
                "mode",
                "",
            )

            add_step(
                "Detecting analysis mode",
                "SUCCESS",
                f"Mode: {event.get('mode', '')}",
                "mode",
            )

        elif event_name == "agent_decision":
            previous_next = find_step("next_step")
            if previous_next is not None:
                previous_next["status"] = "SUCCESS"
            tools = event.get(
                "tools",
                [],
            ) or []
            add_step(
                "Selecting BI tool",
                "RUNNING",
                "Selected: "
                + (
                    ", ".join(
                        str(x)
                        for x in tools
                    )
                    or "No tool"
                ),
                "decision",
            )

        elif event_name == "tool_selected":
            decision = find_step("decision")
            if decision is not None:
                decision["status"] = "SUCCESS"
            tool_name = str(
                event.get(
                    "tool",
                    "unknown",
                )
            )

            input_text = _activity_text(
                event.get(
                    "input",
                    {},
                ),
                360,
            )

            add_step(
                tool_name,
                "RUNNING",
                "Input: " + input_text,
                "tool",
                tool_name,
            )

        elif event_name == "tool_call":
            tool_name = str(
                event.get(
                    "tool",
                    "unknown",
                )
            )

            step = find_running_tool(
                tool_name
            )

            if step is None:
                add_step(
                    tool_name,
                    "RUNNING",
                    "",
                    "tool",
                    tool_name,
                )
            else:
                step["status"] = "RUNNING"

        elif event_name == "tool_completed":
            tool_name = str(
                event.get(
                    "tool",
                    "unknown",
                )
            )

            status = str(
                event.get(
                    "status",
                    "success",
                )
            ).upper()

            step = find_running_tool(
                tool_name
            )

            if step is None:
                add_step(
                    tool_name,
                    status.upper(),
                    "",
                    "tool",
                    tool_name,
                )
            else:
                step["status"] = status

                if event.get("error"):
                    step["detail"] = _activity_text(
                        event.get(
                            "error",
                            "",
                        ),
                        360,
                    )

        elif event_name == "tool_output":
            tool_name = str(
                event.get(
                    "tool",
                    "unknown",
                )
            )

            output = _activity_text(
                event.get(
                    "output",
                    "",
                ),
                700,
            )

            add_step(
                "BI output received",
                "SUCCESS",
                f"{tool_name}: {output}",
                "output",
                tool_name,
            )

        elif event_name == "next_step":
            add_step(
                "Selecting next step",
                "RUNNING",
                (
                    f"Round {event.get('round', '?')} · "
                    f"{event.get('tool_count', 0)} "
                    f"tool result(s)"
                ),
                "next_step",
            )

        elif event_name == "synthesis_started":
            previous_next = find_step("next_step")
            if previous_next is not None:
                previous_next["status"] = "SUCCESS"
            add_step(
                "Synthesizing answer",
                "RUNNING",
                (
                    f"{event.get('tool_count', 0)} "
                    f"tool call(s) · "
                    f"{event.get('rounds', 0)} round(s)"
                ),
                "synthesis",
            )

        elif event_name == "answer_ready":
            synthesis = find_step(
                "synthesis"
            )

            if synthesis is not None:
                synthesis["status"] = "SUCCESS"

            sections = []

            if event.get("has_kpis"):
                sections.append("KPI")

            if event.get("has_visualizations"):
                sections.append("Visualization")

            if event.get("has_tables"):
                sections.append("Table")

            if event.get("has_insights"):
                sections.append("Insights")

            add_step(
                "Answer ready",
                "SUCCESS",
                (
                    "Prepared: "
                    + ", ".join(sections)
                    if sections
                    else "Answer prepared"
                ),
                "answer",
            )

        elif event_name == "llm_retry":
            add_step(
                "Retrying model call",
                "RUNNING",
                _activity_text(
                    f"{event.get('model', '')} · attempt "
                    f"{event.get('attempt', '?')} · "
                    f"{event.get('error', '')}",
                    360,
                ),
                "retry",
            )

        elif event_name == "completed":
            activity_state["status"] = "COMPLETED"
            for step in activity_state["steps"]:
                if str(step.get("status")).upper() == "RUNNING":
                    step["status"] = "SUCCESS"

        elif event_name == "error":
            add_step(
                "Agent error",
                "ERROR",
                _activity_text(
                    event.get(
                        "error",
                        "",
                    ),
                    360,
                ),
                "error",
            )

            activity_state["status"] = "ERROR"

        if event_name not in {
            "completed",
            "error",
        }:
            activity_state["status"] = "RUNNING"

        save_activity_state()

        if activity_placeholder is not None:
            render_live_agent_activity(
                activity_placeholder,
                activity_state,
            )

    def activity_callback(event):
        record_activity_event(event)
        handle_activity_event(
            event
        )

    if activity_placeholder is not None:
        render_live_agent_activity(
            activity_placeholder,
            activity_state,
        )

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
        activity_state = {
            "status": "RUNNING",
            "steps": [],
            "mode": None,
        }

        st.session_state[
            "agent_activity_state"
        ] = activity_state

        if activity_placeholder is not None:
            render_live_agent_activity(
                activity_placeholder,
                activity_state,
            )

        activity_state["status"] = "RUNNING"
        activity_state["steps"] = []
        activity_state["mode"] = None
        activity_state["events"] = []

        st.session_state[
            "agent_activity_events"
        ] = []

        if activity_placeholder is not None:
            render_live_agent_activity(
                activity_placeholder,
                activity_state,
            )


        timestamp = datetime.now().strftime(
            "%H:%M"
        )

        # Previous turns, so follow-up questions keep their context.
        chat_history = list(st.session_state.messages)

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
                "AI Agent is analyzing Sakila data..."
            ):

                activity_state["status"] = "RUNNING"

                render_live_agent_activity(
                    activity_placeholder,
                    activity_state,
                )

                result = ask_claude(
                    question,
                    activity_callback=activity_callback,
                    history=chat_history,
                )

                activity_state["status"] = (
                    "ERROR"
                    if isinstance(result, dict) and result.get("error")
                    else "COMPLETED"
                )

                save_activity_state()

                render_live_agent_activity(
                    activity_placeholder,
                    activity_state,
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

            activity_state["status"] = "ERROR"
            handle_activity_event(
                {
                    "event": "error",
                    "error": str(exc),
                }
            )

            record_activity_event(
                {
                    "event": "error",
                    "error": str(exc),
                }
            )


            render_live_agent_activity(
                activity_placeholder,
                activity_state,
            )

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
            "The AI agent chooses and executes the "
            "appropriate backend tools automatically."
        ),
        eyebrow="AUTONOMOUS BI ANALYST",
        model_note=(
            f"{get_model_label()} · actual tool calling"
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
            width="stretch",
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
            width="stretch",
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
                width="stretch",
            ):

                st.session_state.pending_question = (
                    prompt
                )

                st.rerun()


    # ========================================================
    # MAIN WORKSPACE
    # ========================================================

    chat_col = st.container()
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

# ============================================================
# ROUTING
# ============================================================

page = st.query_params.get("page", "overview")

if page not in {"overview", "predictions", "analyst"}:
    page = "overview"

activity_placeholder = render_sidebar(page)
render_top_header()

if page == "overview":
    render_overview()

elif page == "predictions":
    render_predictions()

else:
    render_ai_analyst(activity_placeholder)
