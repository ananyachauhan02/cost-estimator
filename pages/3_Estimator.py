"""
pages/3_Estimator.py — Full Cost Estimator (moved from original app.py)
"""
import os
import traceback
from datetime import datetime
import html
import re

import streamlit as st

from database import (
    init_db, save_estimate, get_all_estimates,
    get_estimate_by_id, get_estimate_files, delete_estimate,
)
from excel_handler import write_and_recalculate, extract_metrics
from node_distributor import distribute_nodes
from aws_pricer import calculate_pricing, AWS_REGIONS
from gcp_pricer import calculate_gcp_pricing, build_comparison, GCP_REGIONS
from env_pricer import price_additional_environments
from excel_exporter import generate_excel_reports
from pdf_report import generate_pdf_report
from chatbot import render_chatbot
from rbac import require, role_badge
from theme import inject_theme, page_header, section_title, kpi_row, cost_banner, divider
from ui_components import (
    build_summary_dataframe, render_summary_table,
    render_metrics_cards, render_node_distribution,
    render_pricing_results, render_inflation_forecast,
    render_db_selection, render_env_pricing,
)

# ── Auth guard / config handled by app.py ────────────────────────────────

# ── Hide sidebar ───────────────────────────────────────────────────────────
st.markdown("""
<style>
/* ── Force dark number inputs ── */
div[data-testid="stNumberInput"] > div,
div[data-testid="stNumberInput"] input,
div[data-testid="stNumberInput"] > div > div {
  background-color: #1c2640 !important;
  color: #e8edf8 !important;
  border-color: #2a3555 !important;
}
div[data-testid="stNumberInput"] button {
  background-color: #2a3555 !important;
  color: #e8edf8 !important;
}
div[data-testid="stNumberInput"] button:hover {
  background-color: #4f8ef7 !important;
  color: #fff !important;
}
div[data-testid="stNumberInput"] label,
div[data-testid="stTextInput"] label,
div[data-testid="stSelectbox"] label,
div[data-testid="stSlider"] label,
div[data-testid="stDateInput"] label {
  color: #8b95b0 !important;
  font-size: 0.82rem !important;
}
div[data-testid="stTextInput"] input,
div[data-testid="stDateInput"] input {
  background-color: #1c2640 !important;
  color: #e8edf8 !important;
  border-color: #2a3555 !important;
}
div[data-testid="stSelectbox"] > div > div {
  background-color: #1c2640 !important;
  color: #e8edf8 !important;
  border-color: #2a3555 !important;
}
div[data-testid="stExpander"],
div[data-testid="stExpander"] > div,
div[data-testid="stExpander"] summary {
  background-color: #151d35 !important;
  color: #e8edf8 !important;
  border-color: #2a3555 !important;
}
</style>
""", unsafe_allow_html=True)

inject_theme()

# ── Role Guard ─────────────────────────────────────────────────────────────
require("create_estimate", "Only Estimators and Admins can use the Cost Estimator tool. Viewers have read-only access to saved estimates.")

# ── Session state defaults ─────────────────────────────────────────────────
DEFAULTS = {
    "last_updated_file":   None,
    "last_metrics":        None,
    "last_distribution":   None,
    "last_pricing":        None,
    "env_pricing":         None,
    "show_summary":        False,
    "summary_df":          None,
    "show_success":        False,
    "cloud_sizing_xlsx":   None,
    "aws_pricing_xlsx":    None,
    "customer_name_snap":  "",
    "client_mode":         None,
    "db_type_snap":        "PostgreSQL",
    "last_saved_id":       None,
    "pdf_report_path":     None,
    "gcp_pricing":         None,
    "comparison":          None,
    "gcp_pricing_xlsx":    None,
    "selected_aws_region": "us-east-1",
    "selected_gcp_region": "us-central1",
}
for k, v in DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ── Back navigation ────────────────────────────────────────────────────────
client = st.session_state.get("selected_client")
nav_back, nav_title = st.columns([1, 7])
with nav_back:
    if st.button("← Estimates" if client else "← Clients", key="back_nav",
                 use_container_width=True):
        if client:
            st.switch_page("pages/2_Estimates.py")
        else:
            st.switch_page("pages/1_Clients.py")

# ── Page header ────────────────────────────────────────────────────────────
page_header(
    customer_name=st.session_state.customer_name_snap,
    client_mode=st.session_state.client_mode or "",
)

# ══════════════════════════════════════════════════════════════════════════
# SECTION 1 — Project Info
# ══════════════════════════════════════════════════════════════════════════
with st.container():
    section_title("📋", "Project Information")
    c1, c2, c3 = st.columns(3)

    # Pre-fill customer name from selected client
    default_customer = ""
    if client:
        default_customer = client.get("name", "")
    elif st.session_state.customer_name_snap:
        default_customer = st.session_state.customer_name_snap

    customer_name = c1.text_input(
        "Customer / Bank Name",
        value=default_customer,
        placeholder="e.g. HDFC Bank, Emirates NBD…",
    )
    estimate_date = c2.date_input("Estimate Date", datetime.today())
    years         = c3.slider("Forecast Years", 3, 7, 5)

    if customer_name != st.session_state.customer_name_snap:
        st.session_state.customer_name_snap = customer_name


# ══════════════════════════════════════════════════════════════════════════
# SECTION 2 — Client Type
# ══════════════════════════════════════════════════════════════════════════
divider()
section_title("🚀", "Client Type", "Drives DB options, environments included, and output files generated.")

mode_col1, mode_col2 = st.columns(2)

with mode_col1:
    saas_active = st.session_state.client_mode == "saas"
    if st.button(
        "☁️  SaaS Client  (BusinessNext Hosted)",
        use_container_width=True,
        type="primary" if saas_active else "secondary",
        key="btn_saas_mode",
    ):
        st.session_state.client_mode = "saas"
        for k, v in DEFAULTS.items():
            if k not in ("client_mode", "customer_name_snap"):
                st.session_state[k] = v
        st.rerun()

with mode_col2:
    onprem_active = st.session_state.client_mode == "onprem"
    if st.button(
        "🏢  On-Premise Client  (Client Hosted)",
        use_container_width=True,
        type="primary" if onprem_active else "secondary",
        key="btn_onprem_mode",
    ):
        st.session_state.client_mode = "onprem"
        for k, v in DEFAULTS.items():
            if k not in ("client_mode", "customer_name_snap"):
                st.session_state[k] = v
        st.rerun()

if st.session_state.client_mode == "saas":
    st.success(
        "**☁️ SaaS Mode** — DB: PostgreSQL only (EC2 self-hosted, Patroni HA) · "
        "Environments: Pre-Prod/SIT/UAT + DR optional · "
        "Outputs: Cloud Sizing XLSX + AWS Pricing XLSX",
        icon="✅",
    )
elif st.session_state.client_mode == "onprem":
    st.info(
        "**🏢 On-Premise Mode** — DB: PostgreSQL / SQL Server / Oracle · "
        "Environments: DR optional · "
        "Output: Cloud Sizing XLSX only (no pricing)",
        icon="ℹ️",
    )
else:
    st.warning("👆 Select a client type to continue.", icon="⚠️")
    st.stop()

client_mode = st.session_state.client_mode

if not customer_name.strip():
    st.warning("⚠️ Please enter a Customer / Bank Name above before generating.", icon="⚠️")
    st.stop()


# ══════════════════════════════════════════════════════════════════════════
# SECTION 3 — DB & Environment
# ══════════════════════════════════════════════════════════════════════════
divider()
section_title("🗄️", "Database & Environment Options")

if client_mode == "saas":
    db_type = "PostgreSQL"
    st.markdown(
        "<div style='color:var(--accent3);font-size:0.85rem;font-weight:600;margin-bottom:0.75rem;'>"
        "✅ Database locked to <strong>PostgreSQL</strong> for SaaS — self-hosted on EC2, "
        "Patroni HA, no licensing cost.</div>",
        unsafe_allow_html=True,
    )
    env1, env2, env3, env4 = st.columns(4)
    include_preprod = env1.checkbox("📦 Pre-Prod",         value=True,  key="chk_preprod")
    include_sit     = env2.checkbox("🧪 SIT",              value=True,  key="chk_sit")
    include_uat     = env3.checkbox("✅ UAT",              value=True,  key="chk_uat")
    include_dr      = env4.checkbox("🛡️ DR Environment",  value=True,  key="chk_dr")
    # count of pre-prod-family envs selected (used to multiply the base cost)
    env_multiplier  = sum([include_preprod, include_sit, include_uat])
    env_names       = [n for n, chk in [("Pre-Prod", include_preprod), ("SIT", include_sit), ("UAT", include_uat)] if chk]

else:
    db1, _ = st.columns(2)
    db_type = db1.selectbox(
        "Database Type",
        ["PostgreSQL", "SQL Server", "Oracle"],
        help="PostgreSQL. SQL Server / Oracle = client provides licensing.",
    )
    st.markdown("<br>", unsafe_allow_html=True)
    env1, env2, env3, env4 = st.columns(4)
    include_preprod = env1.checkbox("📦 Pre-Prod",         value=False, key="chk_preprod_op")
    include_sit     = env2.checkbox("🧪 SIT",              value=False, key="chk_sit_op")
    include_uat     = env3.checkbox("✅ UAT",              value=False, key="chk_uat_op")
    include_dr      = env4.checkbox("🛡️ Include DR Requirements", value=False, key="chk_dr_op")
    
    env_multiplier  = sum([include_preprod, include_sit, include_uat])
    env_names       = [n for n, chk in [("Pre-Prod", include_preprod), ("SIT", include_sit), ("UAT", include_uat)] if chk]

    msgs = {
        "PostgreSQL":  ("✅ PostgreSQL — self-hosted, Patroni HA.", "success"),
        "SQL Server":  ("⚠️ SQL Server — client provides Microsoft licensing.",  "warning"),
        "Oracle":      ("⚠️ Oracle — client provides Oracle licensing (BYOL).",  "warning"),
    }
    msg, typ = msgs[db_type]
    getattr(st, typ)(msg)


# ══════════════════════════════════════════════════════════════════════════
# SECTION 3b — Cloud Region Selection
# ══════════════════════════════════════════════════════════════════════════
if client_mode == "saas":
    divider()
    section_title("🌍", "Cloud Region Selection",
                  "Prices vary by region. Select the target deployment region for each cloud.")
    reg1, reg2 = st.columns(2)

    aws_region_options = list(AWS_REGIONS.keys())
    aws_region_idx     = aws_region_options.index(
        st.session_state.selected_aws_region
        if st.session_state.selected_aws_region in aws_region_options else "us-east-1"
    )
    aws_region_sel = reg1.selectbox(
        "☁️ AWS Region",
        options=aws_region_options,
        format_func=lambda k: f"{k}  —  {AWS_REGIONS[k]['label']}",
        index=aws_region_idx,
        key="aws_region_sel",
        help="AWS On-Demand prices fetched / estimated for this region.",
    )
    aws_mult = AWS_REGIONS[aws_region_sel]["multiplier"]
    reg1.caption(f"Cost multiplier vs us-east-1: **{aws_mult:.3f}×**")
    st.session_state.selected_aws_region = aws_region_sel

    gcp_region_options = list(GCP_REGIONS.keys())
    gcp_region_idx     = gcp_region_options.index(
        st.session_state.selected_gcp_region
        if st.session_state.selected_gcp_region in gcp_region_options else "us-central1"
    )
    gcp_region_sel = reg2.selectbox(
        "🟦 GCP Region",
        options=gcp_region_options,
        format_func=lambda k: f"{k}  —  {GCP_REGIONS[k]['label']}",
        index=gcp_region_idx,
        key="gcp_region_sel",
        help="GCP Compute Engine prices estimated for this region.",
    )
    gcp_mult = GCP_REGIONS[gcp_region_sel]["multiplier"]
    reg2.caption(f"Cost multiplier vs us-central1: **{gcp_mult:.3f}×**")
    st.session_state.selected_gcp_region = gcp_region_sel
    
    # Optional DR Region selection
    if include_dr:
        dr_reg1, _ = st.columns(2)
        dr_region_options = aws_region_options
        dr_region_idx = dr_region_options.index(
            st.session_state.get("selected_dr_region", aws_region_sel)
            if st.session_state.get("selected_dr_region", aws_region_sel) in dr_region_options else aws_region_sel
        )
        dr_region_sel = dr_reg1.selectbox(
            "🛡️ DR AWS Region",
            options=dr_region_options,
            format_func=lambda k: f"{k}  —  {AWS_REGIONS[k]['label']}",
            index=dr_region_idx,
            key="dr_region_sel_box",
            help="AWS prices for the Disaster Recovery environment fetched / estimated for this specific region.",
        )
        dr_mult = AWS_REGIONS[dr_region_sel]["multiplier"]
        dr_reg1.caption(f"DR multiplier vs us-east-1: **{dr_mult:.3f}×**")
        st.session_state.selected_dr_region = dr_region_sel
    else:
        dr_region_sel = aws_region_sel
else:
    aws_region_sel = "us-east-1"
    gcp_region_sel = "us-central1"
    dr_region_sel  = "us-east-1"


# ══════════════════════════════════════════════════════════════════════════
# SECTION 4 — Year 1 Base Values
# ══════════════════════════════════════════════════════════════════════════
# ── YOY dropdown helper ───────────────────────────────────────────────────
_YOY_OPTIONS = [0, 3, 5, 8, 10, 12, 15, 20]  # percent values

def _yoy_select(label: str, key: str, default_pct: int = 5) -> float:
    """Render a compact YoY % selectbox and return the fraction (e.g. 0.05)."""
    idx = _YOY_OPTIONS.index(default_pct) if default_pct in _YOY_OPTIONS else 2
    pct = st.selectbox(
        label,
        options=_YOY_OPTIONS,
        index=idx,
        format_func=lambda x: f"{x}%",
        key=key,
        label_visibility="visible",
    )
    return pct / 100.0

divider()
with st.expander("📈 Year 1 Base Values", expanded=True):
    # ── Named Users row ──
    nu_val_col, nu_yoy_col, nu_pad_col = st.columns([3, 1, 2])
    named_users_y1 = nu_val_col.number_input("Total Named Users (Y1)", min_value=0, value=15500, step=100)
    with nu_yoy_col:
        yoy_named_users = _yoy_select("YoY %", "yoy_named_users", default_pct=5)

    # ── Concurrent (auto) + Mobile row ──
    concurrent_y1_auto = int(named_users_y1 * 0.30)
    cu_auto_col, cu_pad_col, mob_val_col, mob_yoy_col = st.columns([2, 1, 2, 1])
    cu_auto_col.number_input(
        f"Concurrent Users ≈ {concurrent_y1_auto:,}", value=concurrent_y1_auto,
        disabled=True, help="Auto: 30% of named users"
    )
    mobile_y1 = mob_val_col.number_input("Concurrent Mobile Users (Y1)", min_value=0, value=4050, step=100)
    with mob_yoy_col:
        yoy_mobile = _yoy_select("YoY %", "yoy_mobile", default_pct=5)

    # ── Total Customers row ──
    cust_val_col, cust_yoy_col = st.columns([5, 1])
    total_customers_y1 = cust_val_col.number_input("Total Customers (Y1)", value=25_786_541, step=10_000, format="%d")
    with cust_yoy_col:
        yoy_customers = _yoy_select("YoY %", "yoy_customers", default_pct=10)

    # ── Leads row ──
    leads_val_col, leads_yoy_col = st.columns([5, 1])
    leads_y1 = leads_val_col.number_input("Number of Leads (Y1)", value=10_700_000, step=10_000, format="%d")
    with leads_yoy_col:
        yoy_leads = _yoy_select("YoY %", "yoy_leads", default_pct=10)

    # ── Cases row ──
    cases_val_col, cases_yoy_col = st.columns([5, 1])
    cases_y1 = cases_val_col.number_input("Number of Service Requests / Cases (Y1)", value=20_000, step=100, format="%d")
    with cases_yoy_col:
        yoy_cases = _yoy_select("YoY %", "yoy_cases", default_pct=5)

# Build the YOY dict from widget values
YOY = dict(
    named_users=yoy_named_users,
    concurrent=yoy_named_users,   # concurrent inherits named-users rate
    mobile=yoy_mobile,            # mobile users has its own independent rate
    customers=yoy_customers,
    leads=yoy_leads,
    cases=yoy_cases,
    product_hold=0.05,            # product holdings — fixed at 5% (no explicit widget needed)
)

with st.expander("🔧 Detailed Sizing Assumptions", expanded=False):
    c1, c2, c3, c4 = st.columns(4)
    docs_per_customer = c1.number_input("Docs per customer", value=2, step=1)
    docs_per_lead     = c1.number_input("Docs per Lead",     value=2, step=1)
    docs_per_case     = c1.number_input("Docs per Case",     value=1, step=1)
    acts_per_customer = c2.number_input("Activities per customer", value=2, step=1)
    acts_per_lead     = c2.number_input("Activities per Lead",     value=2, step=1)
    acts_per_case     = c2.number_input("Activities per Case",     value=4, step=1)
    pdf_per_user_h    = c3.number_input("PDF reports per user/hr", value=1, step=1)
    doc_size_mb       = c3.number_input("Document size (MB)",      value=0.25, step=0.1)
    emails_auto      = int((leads_y1 + cases_y1) * 0.05)
    escalations_auto = int((total_customers_y1 + leads_y1 + cases_y1) * 0.10)
    c4.number_input(f"Emails ≈ {emails_auto:,}",           value=emails_auto,      disabled=True)
    c4.number_input(f"Escalations ≈ {escalations_auto:,}", value=escalations_auto, disabled=True)


# ══════════════════════════════════════════════════════════════════════════
# SECTION 5 — One-Time Costs
# ══════════════════════════════════════════════════════════════════════════
with st.expander("💰 One-Time Costs  (Year 1 only — included in PUPM calculation)", expanded=True):
    st.caption("These are charged once in Year 1 and flow into: Total Cost → Discounted Cost → PUPM.")
    ot1, ot2, ot3 = st.columns(3)
    perf_testing_cost = ot1.number_input("Performance Testing ($)", min_value=0, value=5000, step=500)
    migration_cost    = ot2.number_input("Migration / Data Bootup ($)", min_value=0, value=5000, step=500)
    managed_svc_onetime = ot3.number_input("Managed Services Setup ($)", min_value=0, value=1000, step=100)
    one_time_total_display = perf_testing_cost + migration_cost + managed_svc_onetime
    st.markdown(
        f"<div style='margin-top:0.5rem;padding:10px 16px;background:var(--surface2);border-radius:8px;border:1px solid var(--border);'>"
        f"<span style='font-size:0.82rem;color:var(--text2);'>Estimated One-Time Migration:</span> &nbsp; "
        f"<strong style='color:var(--accent);'>${one_time_total_display:,.0f}</strong>"
        f"</div>",
        unsafe_allow_html=True,
    )


# ══════════════════════════════════════════════════════════════════════════
# SECTION 6 — Workload Profile
# ══════════════════════════════════════════════════════════════════════════
with st.expander("⚙️ Workload Profile", expanded=False):
    wc1, wc2 = st.columns(2)
    workload_type = wc1.selectbox("Workload Type",
                       ["banking_crm", "retail_crm", "sme_crm", "insurance_crm"])
    peak_load     = wc2.selectbox("Peak Load", ["normal", "high", "very_high"])
    wc3, wc4, wc5 = st.columns(3)
    mobile_heavy    = wc3.checkbox("Mobile-heavy workload",   value=(mobile_y1 > 3000))
    _reporting_db_disabled = (db_type == "PostgreSQL")
    reporting_db    = wc4.checkbox(
        "Reporting DB required",
        value=False if _reporting_db_disabled else True,
        disabled=_reporting_db_disabled,
        help="Not applicable for PostgreSQL — already runs in HA (Patroni), no separate Reporting DB needed." if _reporting_db_disabled else None,
    )
    if _reporting_db_disabled:
        wc4.caption("🔒 Disabled — PostgreSQL is HA")
    high_compliance = wc5.checkbox("High compliance / audit", value=True)
    workload_notes  = st.text_input("Additional notes",
                         placeholder="e.g. heavy batch jobs, real-time analytics")

    api_key_set = bool(os.getenv("GROQ_API_KEY"))
    if api_key_set:
        use_llm = st.toggle("🤖 Use AI for node distribution", value=True)
    else:
        st.info("🔑 `GROQ_API_KEY` not set — rule-based node distribution will be used.", icon="ℹ️")
        use_llm = False

workload_profile = {
    "workload_type": workload_type, "peak_load": peak_load,
    "mobile_heavy": mobile_heavy, "mobile_users": mobile_y1,
    "reporting_db": reporting_db, "high_compliance": high_compliance,
    "db_type": db_type, "client_mode": client_mode, "notes": workload_notes,
}


# ══════════════════════════════════════════════════════════════════════════
# Yearly growth arrays
# ══════════════════════════════════════════════════════════════════════════
years_list       = [f"Y{y+1}" for y in range(years)]
named_users_arr  = [named_users_y1]
concurrent_arr   = [concurrent_y1_auto]
mobile_arr       = [mobile_y1]
customers_arr    = [total_customers_y1]
leads_arr        = [leads_y1]
cases_arr        = [cases_y1]
product_hold_arr = [1]

for _ in range(1, years):
    named_users_arr.append( int(named_users_arr[-1]  * (1 + YOY["named_users"])))
    concurrent_arr.append(  int(concurrent_arr[-1]   * (1 + YOY["concurrent"])))
    mobile_arr.append(      int(mobile_arr[-1]        * (1 + YOY["mobile"])))
    customers_arr.append(   int(customers_arr[-1]     * (1 + YOY["customers"])))
    leads_arr.append(       int(leads_arr[-1]          * (1 + YOY["leads"])))
    cases_arr.append(       int(cases_arr[-1]          * (1 + YOY["cases"])))
    product_hold_arr.append(int(product_hold_arr[-1]  * (1 + YOY["product_hold"])))

SUMMARY_KWARGS = dict(
    years_list=years_list,
    named_users=named_users_arr,   concurrent=concurrent_arr,   customers=customers_arr,
    leads_list=leads_arr,          cases_list=cases_arr,        mobile=mobile_arr,
    product_holdings=product_hold_arr,
    activities_per_customer=acts_per_customer, activities_per_lead=acts_per_lead,
    activities_per_case=acts_per_case,
    documents_per_customer=docs_per_customer, documents_per_lead=docs_per_lead,
    documents_per_case=docs_per_case,
    YOY_NAMED_USERS=YOY["named_users"], YOY_CONCURRENT=YOY["concurrent"],
    YOY_MOBILE=YOY["mobile"],
    YOY_CUSTOMERS=YOY["customers"], YOY_LEADS=YOY["leads"],
    YOY_CASES=YOY["cases"], YOY_PRODUCT_HOLD=YOY["product_hold"],
)


# ── Yearly Summary button ──────────────────────────────────────────────────
divider()
if st.button("📊 Generate Yearly Summary", type="primary", key="btn_summary", use_container_width=True):
    st.session_state.summary_df   = build_summary_dataframe(**SUMMARY_KWARGS)
    st.session_state.show_summary = True
    st.rerun()

if st.session_state.show_summary and st.session_state.summary_df is not None:
    render_summary_table(st.session_state.summary_df, years_list)
    if st.button("Hide Summary", type="secondary", key="hide_summary"):
        st.session_state.show_summary = False
        st.session_state.summary_df   = None
        st.rerun()

divider()


# ══════════════════════════════════════════════════════════════════════════
# MAIN GENERATE BUTTON
# ══════════════════════════════════════════════════════════════════════════
btn_label = (
    f"🚀  Generate Cloud Sizing + Full Pricing  —  {customer_name}"
    if client_mode == "saas"
    else f"🚀  Generate Cloud Sizing Requirements  —  {customer_name}"
)

if st.button(btn_label, type="primary", use_container_width=True, key="btn_generate"):
    inputs = {
        "named_users": named_users_y1, "concurrent_users": concurrent_y1_auto,
        "total_customers": total_customers_y1, "leads": leads_y1,
        "cases": cases_y1, "mobile_users": mobile_y1,
        # YOY growth rates → written to column I of Customer Volumes sheet
        "yoy_named_users": yoy_named_users,
        "yoy_concurrent":  yoy_named_users,   # concurrent is auto-derived → same rate as named users
        "yoy_customers":   yoy_customers,
        "yoy_leads":       yoy_leads,
        "yoy_cases":       yoy_cases,
        "yoy_mobile":      yoy_mobile,
    }
    try:
        with st.spinner(f"Step 1 — Recalculating sizing template for **{customer_name}**…"):
            updated_file = write_and_recalculate(
                inputs=inputs,
                template_path="templates/Sizing_Template.xlsx",
                output_path="reports/updated_estimate.xlsx",
            )
            st.session_state.last_updated_file = updated_file

        with st.spinner("Step 2 — Extracting sizing metrics…"):
            metrics = extract_metrics(updated_file)
            metrics.update({
                "mobile_users": mobile_y1, "db_type": db_type,
                "client_mode": client_mode, "customer_name": customer_name,
                "total_named_users": named_users_y1,
                "one_time_perf_testing": perf_testing_cost,
                "one_time_migration": migration_cost,
                "one_time_managed_svc": managed_svc_onetime,
            })
            st.session_state.last_metrics = metrics

        with st.spinner("Step 3 — Distributing nodes…"):
            distribution = distribute_nodes(metrics=metrics, workload_profile=workload_profile, use_llm=use_llm)
            st.session_state.last_distribution = distribution

        pricing = None
        env_pricing = None

        if client_mode == "saas":
            with st.spinner("Step 4 — Fetching AWS prices…"):
                pricing = calculate_pricing(distribution, metrics, region=aws_region_sel)
                st.session_state.last_pricing = pricing

            with st.spinner("Step 4b — Fetching GCP prices…"):
                gcp_pricing = calculate_gcp_pricing(distribution, metrics, region=gcp_region_sel)
                st.session_state.gcp_pricing = gcp_pricing
                comparison  = build_comparison(pricing, gcp_pricing)
                st.session_state.comparison = comparison

            if env_multiplier > 0 or include_dr:
                with st.spinner("Step 5 — Pricing environments…"):
                    env_pricing = price_additional_environments(
                        db_type="PostgreSQL", deployment="saas", metrics=metrics,
                        preprod_region=aws_region_sel, dr_region=dr_region_sel
                    )
                    if env_multiplier == 0:
                        env_pricing["preprod_sit_uat"] = None
                    else:
                        # same base cost × number of selected environments
                        base = env_pricing.get("preprod_sit_uat") or {}
                        if base:
                            for key in ("monthly_usd", "annual_usd"):
                                if key in base:
                                    base[key] = round(base[key] * env_multiplier, 2)
                            # store metadata for display
                            base["env_multiplier"] = env_multiplier
                            base["env_names"]      = env_names
                            env_pricing["preprod_sit_uat"] = base
                        # also multiply combined_monthly
                        env_pricing["combined_monthly"] = round(
                            env_pricing.get("combined_monthly", 0)
                            - (env_pricing.get("combined_monthly", 0) / max(env_multiplier, 1))
                            + (base.get("monthly_usd", 0) if base else 0), 2
                        )
                    if not include_dr:
                        env_pricing["dr"] = None
                    # recalculate combined_monthly cleanly
                    pp_mo = (env_pricing.get("preprod_sit_uat") or {}).get("monthly_usd", 0)
                    dr_mo = (env_pricing.get("dr")              or {}).get("monthly_usd", 0)
                    env_pricing["combined_monthly"] = round(pp_mo + dr_mo, 2)
                    st.session_state.env_pricing = env_pricing
                    if env_multiplier > 0 and pricing and "assumptions" in pricing:
                        pricing["assumptions"]["deployment"] = f"Multi-AZ (HA) for Prod/DR; Single-AZ for {' + '.join(env_names)}"
            else:
                st.session_state.env_pricing = None
                if pricing and "assumptions" in pricing:
                    pricing["assumptions"]["deployment"] = "Multi-AZ (HA) for Prod/DR"
                
        else:
            st.session_state.last_pricing = None
            if env_multiplier > 0 or include_dr:
                with st.spinner("Step 4 — Building additional environment requirements…"):
                    env_pricing = price_additional_environments(
                        db_type=db_type, deployment="onprem", metrics=metrics,
                        preprod_region=aws_region_sel, dr_region=dr_region_sel
                    )
                    
                    if env_multiplier == 0:
                        env_pricing["preprod_sit_uat"] = None
                    else:
                        base = env_pricing.get("preprod_sit_uat") or {}
                        if base:
                            base["env_multiplier"] = env_multiplier
                            base["env_names"]      = env_names
                            env_pricing["preprod_sit_uat"] = base
                            
                    if not include_dr:
                        env_pricing["dr"] = None
                        
                    st.session_state.env_pricing = env_pricing
            else:
                st.session_state.env_pricing = None

        with st.spinner("Generating Excel files…"):
            excel_paths = generate_excel_reports(
                pricing=pricing, distribution=distribution, metrics=metrics,
                customer=customer_name, output_dir="reports",
                env_pricing=st.session_state.env_pricing,
                db_type=db_type, client_mode=client_mode,
                gcp_pricing=st.session_state.get("gcp_pricing"),
                comparison=st.session_state.get("comparison"),
            )
            st.session_state.cloud_sizing_xlsx  = excel_paths.get("cloud_sizing")
            st.session_state.aws_pricing_xlsx   = excel_paths.get("aws_pricing")
            st.session_state.gcp_pricing_xlsx   = excel_paths.get("gcp_pricing")
            st.session_state.customer_name_snap = customer_name
            st.session_state.db_type_snap       = db_type

        with st.spinner("Generating PDF report…"):
            try:
                cname_safe = re.sub(r'[^a-zA-Z0-9_\-]', '_', customer_name)
                pdf_path = generate_pdf_report(
                    pricing=pricing, distribution=distribution, metrics=metrics,
                    env_pricing=st.session_state.env_pricing, customer=customer_name,
                    client_mode=client_mode,
                    output_path=f"reports/pricing_report_{cname_safe}.pdf",
                    gcp_pricing=st.session_state.get("gcp_pricing"),
                    comparison=st.session_state.get("comparison"),
                )
                st.session_state.pdf_report_path = pdf_path
            except Exception as pdf_err:
                st.session_state.pdf_report_path = None
                st.warning(f"PDF generation skipped: {pdf_err}")

        with st.spinner("Saving to database…"):
            client_id = client["id"] if client else None
            saved_id = save_estimate(
                customer_name=customer_name, estimate_date=estimate_date,
                years=years, metrics=metrics,
                client_mode=client_mode, db_type=db_type,
                pricing=pricing, distribution=distribution,
                env_pricing=st.session_state.env_pricing,
                cloud_sizing_path=st.session_state.cloud_sizing_xlsx,
                aws_pricing_path=st.session_state.aws_pricing_xlsx,
                client_id=client_id,
            )
            st.session_state.last_saved_id = saved_id

        st.session_state.summary_df   = build_summary_dataframe(**SUMMARY_KWARGS)
        st.session_state.show_summary = True
        st.session_state.show_success = True
        st.rerun()

    except Exception as e:
        st.error(f"Error: {e}")
        st.code(traceback.format_exc())

if st.session_state.get("show_success"):
    st.markdown("""
    <div style="background:var(--surface2);border:1px solid var(--success);
                padding:12px 18px;border-radius:10px;margin-bottom:1.5rem;display:flex;align-items:center;gap:12px;">
      <span style="font-size:1.3rem;">✅</span>
      <span style="color:var(--success);font-weight:600;">Estimate generated and saved successfully!</span>
    </div>
    """, unsafe_allow_html=True)
    st.session_state.show_success = False


# ══════════════════════════════════════════════════════════════════════════
# RESULTS
# ══════════════════════════════════════════════════════════════════════════
if st.session_state.last_metrics:
    render_metrics_cards(st.session_state.last_metrics)

if st.session_state.last_distribution:
    render_node_distribution(st.session_state.last_distribution)

if client_mode == "saas" and st.session_state.last_pricing:
    p = st.session_state.last_pricing
    five_yr = p.get("inflation_forecast", {}).get("five_year_total", 0)
    divider()
    cost_banner(p["total_monthly_usd"], p["total_annual_usd"], five_yr)
    render_db_selection(p)
    render_pricing_results(p, updated_file=st.session_state.last_updated_file)
    render_inflation_forecast(p)

if st.session_state.env_pricing:
    render_env_pricing(st.session_state.env_pricing, client_mode=client_mode)

if client_mode == "onprem" and st.session_state.last_distribution:
    st.info(
        "**On-Premise mode:** No AWS pricing is calculated. "
        "The Cloud Sizing XLSX contains infrastructure requirements only.",
        icon="ℹ️",
    )

# ── AWS vs GCP Comparison ─────────────────────────────────────────────────
if client_mode == "saas" and st.session_state.get("comparison"):
    comp    = st.session_state.comparison
    s       = comp.get("summary", {})
    aws_mo  = s.get("aws_monthly", 0)
    gcp_mo  = s.get("gcp_monthly", 0)
    cheaper = s.get("cheaper_monthly", "AWS")
    diff_mo = s.get("diff_monthly", 0)
    diff_5yr= s.get("diff_5year", 0)
    aws_5yr = s.get("aws_5year", 0)
    gcp_5yr = s.get("gcp_5year", 0)
    cheaper_5yr = s.get("cheaper_5year", "AWS")
    aws_reg = s.get("aws_region", "us-east-1")
    gcp_reg = s.get("gcp_region", "us-central1")

    divider()
    section_title("⚖️", "AWS vs GCP Cost Comparison",
                  f"AWS ({aws_reg})  vs  GCP ({gcp_reg}) — same workload, two clouds")
    cc1, cc2, cc3 = st.columns(3)
    cc1.metric("☁️ AWS Monthly",  f"${aws_mo:,.0f}",
               delta=f"{'cheaper' if cheaper=='AWS' else 'pricier'} by ${diff_mo:,.0f}",
               delta_color="normal" if cheaper == "AWS" else "inverse")
    cc2.metric("🟦 GCP Monthly",  f"${gcp_mo:,.0f}",
               delta=f"{'cheaper' if cheaper=='GCP' else 'pricier'} by ${diff_mo:,.0f}",
               delta_color="normal" if cheaper == "GCP" else "inverse")
    cc3.metric(f"🏆 5-Year Winner: {cheaper_5yr}", f"Save ${diff_5yr:,.0f}",
               delta=f"AWS ${aws_5yr:,.0f}  /  GCP ${gcp_5yr:,.0f}")

    cat_rows = comp.get("category_comparison", [])
    if cat_rows:
        import pandas as pd
        df_comp = pd.DataFrame([{
            "Category":    r["category"],
            "AWS $/mo":    f"${r['aws_monthly']:,.2f}",
            "GCP $/mo":    f"${r['gcp_monthly']:,.2f}",
            "Difference":  f"${abs(r['diff']):,.2f}",
            "✔ Cheaper":   r["cheaper"],
        } for r in cat_rows])
        st.dataframe(df_comp, use_container_width=True, hide_index=True)

# ── Download buttons ───────────────────────────────────────────────────────
if st.session_state.cloud_sizing_xlsx or st.session_state.aws_pricing_xlsx:
    divider()
    section_title("📥", "Download Reports")
    cname = re.sub(r'[^a-zA-Z0-9_\-]', '_', st.session_state.customer_name_snap)
    xl1, xl2 = st.columns(2)
    if st.session_state.cloud_sizing_xlsx:
        try:
            with open(st.session_state.cloud_sizing_xlsx, "rb") as f:
                xl1.download_button("📊 Cloud Sizing (XLSX)", f,
                    file_name=f"cloud_sizing_{cname}.xlsx",
                    key="dl_cloud_sizing", use_container_width=True)
        except Exception as e:
            st.error(f"Error downloading Cloud Sizing: {e}")
    if client_mode == "saas" and st.session_state.aws_pricing_xlsx:
        try:
            with open(st.session_state.aws_pricing_xlsx, "rb") as f:
                xl2.download_button("💰 Pricing Forecast (XLSX)", f,
                    file_name=f"cloud_pricing_{cname}.xlsx",
                    key="dl_aws_pricing", use_container_width=True)
        except Exception as e:
            st.error(f"Error downloading Pricing Forecast: {e}")

    if st.session_state.get("pdf_report_path"):
        try:
            with open(st.session_state.pdf_report_path, "rb") as f:
                pdf_bytes = f.read()
            st.markdown("""
            <div style="margin-top:1rem;padding:14px 18px;
                        background:var(--surface2); border:1px solid var(--warning);
                        border-radius:10px;display:flex;align-items:center;gap:14px;">
              <span style="font-size:1.4rem;">📄</span>
              <div>
                <div style="color:var(--warning);font-weight:700;font-size:0.95rem;">Full Pricing Report (PDF)</div>
                <div style="color:#78716c;font-size:0.78rem;margin-top:2px;">
                  Executive Summary · Node Distribution · Cost Breakdown · 5-Year Forecast · PUPM Analysis
                </div>
              </div>
            </div>
            """, unsafe_allow_html=True)
            st.download_button(
                label="📄  Download Full Pricing Report (PDF)",
                data=pdf_bytes,
                file_name=f"pricing_report_{cname}.pdf",
                mime="application/pdf",
                key="dl_pdf_report",
                use_container_width=True,
                type="primary",
            )
        except Exception as e:
            st.error(f"Error downloading PDF Report: {e}")

# ── Chatbot (SaaS only) ────────────────────────────────────────────────────
if client_mode == "saas" and st.session_state.last_pricing:
    render_chatbot(
        pricing=st.session_state.last_pricing,
        distribution=st.session_state.last_distribution,
        metrics=st.session_state.last_metrics,
    )

# ── Clear results ──────────────────────────────────────────────────────────
if st.session_state.last_distribution or st.session_state.last_pricing:
    divider()
    if st.button("🗑️ Clear Results", type="secondary", key="clear_all"):
        mode  = st.session_state.client_mode
        cname_snap = st.session_state.customer_name_snap
        for k, v in DEFAULTS.items():
            st.session_state[k] = v
        st.session_state.client_mode        = mode
        st.session_state.customer_name_snap = cname_snap
        st.rerun()