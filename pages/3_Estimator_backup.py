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

# Theme is globally handled by app.py
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
    "dr_scale":            1.0,
    "gcp_pricing_xlsx":    None,
    "onprem_sizing_xlsx":  None,
    "onprem_oracle_sizing_xlsx": None,
    "last_saved_id":       None,
    "pdf_report_path":     None,
    "gcp_pricing":         None,
    "comparison":          None,
    "selected_aws_region": "us-east-1",
    "selected_gcp_region": "us-central1",
    "last_gcp_sync_aws_region": "us-east-1",
    "chatbot_retrigger":   False,
    "instance_overrides":  {},
    # ClickHouse
    "include_clickhouse":  False,
    "ch_data_multiplier":  2.0,
    # AI Services
    "include_predictive":  False,
    "include_genai":       False,
    "include_agentic":     False,
    "predictive_envs":     ["prod"],
    "genai_envs":          ["prod"],
    "agentic_envs":        ["prod"],
    "bedrock_monthly":     3000.0,
    "ai_sizing_xlsx":      None,
    "last_ai_sizing":      None,
}
for k, v in DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ── Apply pending chatbot changes BEFORE widgets render ────────────────────
# The chatbot stores proposed changes in _pending_changes because Streamlit
# prohibits writing to widget keys after the widget has been instantiated.
# This block runs at the top of the page, before any widgets are created.
def _apply_pending_changes():
    """Resolve pending chatbot changes into widget session-state keys."""
    changes = st.session_state.pop("_pending_changes", None)
    if not changes:
        return

    client_mode = st.session_state.get("client_mode", "saas")
    is_saas = client_mode == "saas"
    env_suffix = "" if is_saas else "_op"

    _ENV_KEYS = {
        "include_preprod": f"chk_preprod{env_suffix}",
        "include_sit":     f"chk_sit{env_suffix}",
        "include_uat":     f"chk_uat{env_suffix}",
        "include_dr":      f"chk_dr{env_suffix}",
    }
    _dr_key = "dr_scale_pct_saas" if is_saas else "dr_scale_pct_op"
    _REGION_KEYS = {
        "aws_region": ("aws_region_sel", "selected_aws_region"),
        "gcp_region": ("gcp_region_sel", "selected_gcp_region"),
        "dr_region":  ("dr_region_sel_box", "selected_dr_region"),
    }
    _DIRECT_KEY_MAP = {
        "named_users":      "in_named_users",
        "concurrent_users": "in_concurrent_users",
        "mobile_users":     "in_mobile_users",
        "total_customers":  "in_total_customers",
        "leads":            "in_leads",
        "cases":            "in_cases",
        "workload_type":    "in_workload_type",
        "peak_load":        "in_peak_load",
        "mobile_heavy":     "in_mobile_heavy",
        "reporting_db":     "in_reporting_db",
        "high_compliance":  "in_high_compliance",
        "workload_notes":   "in_workload_notes",
        "db_type":          "in_db_type",
        "forecast_years":   "in_forecast_years",
        "perf_testing_cost":  "in_perf_testing",
        "migration_cost":     "in_migration_cost",
        "managed_svc_cost":   "in_managed_svc",
    }

    for prop_key, value in changes.items():
        if prop_key == "instance_overrides" and isinstance(value, dict):
            existing = st.session_state.get("instance_overrides", {})
            existing.update(value)
            st.session_state.instance_overrides = existing
            continue
        if prop_key in _ENV_KEYS:
            st.session_state[_ENV_KEYS[prop_key]] = bool(value)
            continue
        if prop_key == "dr_scale":
            st.session_state[_dr_key] = int(value)
            continue
        if prop_key in _REGION_KEYS:
            widget_key, tracking_key = _REGION_KEYS[prop_key]
            st.session_state[widget_key] = value
            st.session_state[tracking_key] = value
            continue
        # ClickHouse toggle
        if prop_key == "include_clickhouse":
            st.session_state["chk_clickhouse"]    = bool(value)
            st.session_state["include_clickhouse"] = bool(value)
            continue
        if prop_key == "ch_data_multiplier":
            st.session_state["ch_data_multiplier"] = float(value)
            continue
        ss_key = _DIRECT_KEY_MAP.get(prop_key)
        if ss_key:
            st.session_state[ss_key] = value

_apply_pending_changes()


AWS_TO_GCP_REGION_MAP = {
    # Americas
    "us-east-1": "us-central1",
    "us-east-2": "us-east5",
    "us-west-1": "us-west1",
    "us-west-2": "us-west1",
    "ca-central-1": "northamerica-northeast1",
    "ca-west-1": "northamerica-northeast2",
    "sa-east-1": "southamerica-east1",
    # Europe
    "eu-central-1": "europe-west3",
    "eu-central-2": "europe-west6",
    "eu-west-1": "europe-west1",
    "eu-west-2": "europe-west2",
    "eu-west-3": "europe-west9",
    "eu-north-1": "europe-north1",
    "eu-south-1": "europe-west8",
    "eu-south-2": "europe-southwest1",
    # Asia Pacific
    "ap-south-1": "asia-south1",
    "ap-south-2": "asia-south2",
    "ap-northeast-1": "asia-northeast1",
    "ap-northeast-2": "asia-northeast3",
    "ap-northeast-3": "asia-northeast2",
    "ap-southeast-1": "asia-southeast1",
    "ap-southeast-2": "australia-southeast1",
    "ap-southeast-3": "asia-southeast2",
    "ap-southeast-4": "australia-southeast2",
    "ap-southeast-5": "asia-southeast1",
    "ap-east-1": "asia-east2",
    # Middle East & Africa
    "me-south-1": "me-central2",
    "me-central-1": "me-central1",
    "af-south-1": "af-south1",
    "il-central-1": "me-west1",
}

# ── Top Navigation ────────────────────────────────────────────────────────
client = st.session_state.get("selected_client")

hdr_l, hdr_r = st.columns([4, 1])
with hdr_l:
    user_role = st.session_state.user.get("role", "viewer")
    role_colors = {"admin": ("#fef2f2", "#dc2626"), "estimator": ("#eff6ff", "#2563eb"), "viewer": ("#f0fdf4", "#16a34a")}
    bg, fg = role_colors.get(user_role, ("#f3f4f6", "#374151"))
    st.markdown(f"""
    <div class="bn-page-header">
      <div>
        <div class="bn-page-title" style="display:flex;align-items:center;gap:10px;">
          Cost Estimator
          <span style="font-size:12px;font-weight:600;padding:3px 10px;border-radius:20px;
                       background:{bg};color:{fg};vertical-align:middle;">{user_role}</span>
        </div>
        <div class="bn-page-subtitle" id="est-client-label">Configure inputs and generate pricing</div>
      </div>
    </div>
    """, unsafe_allow_html=True)
with hdr_r:
    st.markdown("<div style='padding-top:1.5rem'></div>", unsafe_allow_html=True)
    if st.button("← Clients", key="nav_back_clients_estimator", use_container_width=True):
        st.switch_page("pages/1_Clients.py")

# ── Page header detail (client + mode) ─────────────────────────────────────
client = st.session_state.get("selected_client")
default_customer = ""
if client:
    default_customer = client.get("name", "")
elif st.session_state.customer_name_snap:
    default_customer = st.session_state.customer_name_snap

page_header(
    customer_name=st.session_state.customer_name_snap or default_customer,
    client_mode=st.session_state.client_mode or "",
)

# ══════════════════════════════════════════════════════════════════════════
# SECTION 1 — Project Info
# ══════════════════════════════════════════════════════════════════════════
with st.container():
    section_title("📋", "Project Information")
    c1, c2, c3 = st.columns(3)

    customer_name = c1.text_input(
        "Customer / Bank Name",
        value=default_customer,
        placeholder="e.g. HDFC Bank, Emirates NBD…",
    )
    estimate_date = c2.date_input("Estimate Date", datetime.today())
    years         = c3.slider("Forecast Years", 3, 7, 5, key="in_forecast_years")

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
        "Output: Cloud Sizing XLSX + **On-Prem Sizing XLSX** (OpenShift for SQL Server/PostgreSQL; Kubeadm for Oracle) "
        "+ **Kubeadm Oracle XLSX** (always generated as an alternative architecture reference)",
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
    # DR Scale selector (SaaS) — shown inside SaaS branch
    if include_dr:
        _dr_col, _ = st.columns([2, 2])
        _dr_scale_pct = _dr_col.radio(
            "🛡️ DR Sizing Scale",
            options=[50, 100],
            index=1,
            format_func=lambda x: f"{x}% of Production",
            key="dr_scale_pct_saas",
            horizontal=True,
            help="**50%** — Pilot-light/warm-standby: compute nodes halved, **DB fully replicated (same as prod)**. **100%** — Full production mirror.",
        )
    else:
        _dr_scale_pct = 100
    dr_scale = _dr_scale_pct / 100.0

else:
    db1, _ = st.columns(2)
    db_type = db1.selectbox(
        "Database Type",
        ["PostgreSQL", "SQL Server", "Oracle"],
        help="PostgreSQL. SQL Server / Oracle = client provides licensing.",
        key="in_db_type",
    )
    st.markdown("<br>", unsafe_allow_html=True)
    env1, env2, env3, env4 = st.columns(4)
    include_preprod = env1.checkbox("📦 Pre-Prod",         value=False, key="chk_preprod_op")
    include_sit     = env2.checkbox("🧪 SIT",              value=False, key="chk_sit_op")
    include_uat     = env3.checkbox("✅ UAT",              value=False, key="chk_uat_op")
    include_dr      = env4.checkbox("🛡️ Include DR Requirements", value=False, key="chk_dr_op")

    env_multiplier  = sum([include_preprod, include_sit, include_uat])
    env_names       = [n for n, chk in [("Pre-Prod", include_preprod), ("SIT", include_sit), ("UAT", include_uat)] if chk]
    # DR Scale selector (On-Prem) — shown inside On-Prem branch
    if include_dr:
        _dr_col2, _ = st.columns([2, 2])
        _dr_scale_pct = _dr_col2.radio(
            "🛡️ DR Sizing Scale",
            options=[50, 100],
            index=1,
            format_func=lambda x: f"{x}% of Production",
            key="dr_scale_pct_op",
            horizontal=True,
            help="**50%** — Pilot-light/warm-standby: compute nodes halved, **DB fully replicated (same as prod)**. **100%** — Full production mirror.",
        )
    else:
        _dr_scale_pct = 100
    dr_scale = _dr_scale_pct / 100.0

# ── ClickHouse toggle (both SaaS and On-Prem) ─────────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
ch_col1, ch_col2 = st.columns([1, 3])
include_clickhouse = ch_col1.checkbox(
    "📊 Include ClickHouse (OLAP Analytics DB)",
    value=st.session_state.get("include_clickhouse", False),
    key="chk_clickhouse",
    help=(
        "Add a self-hosted ClickHouse cluster for real-time OLAP analytics and reporting. "
        "Includes: sharded + replicated DB cluster + ClickHouse Keeper coordination cluster. "
        "Sizing derived automatically from your data volume and customer activity."
    ),
)
# sync tracking key (separate from widget key 'chk_clickhouse') — safe to write
st.session_state["include_clickhouse"] = include_clickhouse
ch_data_multiplier = float(st.session_state.get("ch_data_multiplier", 2.0))
if include_clickhouse:
    with st.expander("⚙️ ClickHouse Sizing Options", expanded=False):
        _ch_col1, _ch_col2 = st.columns(2)
        ch_data_multiplier = _ch_col1.slider(
            "Analytics Data Multiplier (vs Transactional DB)",
            min_value=1.0, max_value=5.0,
            value=float(st.session_state.get("ch_data_multiplier", 2.0)),
            step=0.5,
            key="ch_data_multiplier",
            help="ClickHouse analytics data is typically 1.5–3× the transactional DB size (denormalised, aggregated). Default: 2×.",
        )
        # slider with key='ch_data_multiplier' auto-manages session_state — no write-back needed
        _ch_col2.info(
            f"📊 Estimated ClickHouse analytics data: "
            f"**~{int(2100 * ch_data_multiplier):,} GB** (based on default 2,100 GB transactional DB).",
            icon="ℹ️",
        )

#    msgs = {
#        "PostgreSQL":  ("✅ PostgreSQL — self-hosted, Patroni HA.", "success"),
#        "SQL Server":  ("⚠️ SQL Server — client provides Microsoft licensing.",  "warning"),
#        "Oracle":      ("⚠️ Oracle — client provides Oracle licensing (BYOL).",  "warning"),
#    }
#    msg, typ = msgs[db_type]
#    getattr(st, typ)(msg)

# ── AI Services toggle (both SaaS and On-Prem) ─────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
st.markdown(
    "<div style='font-size:0.9rem;font-weight:700;color:var(--text);margin-bottom:0.5rem;'>"
    "🤖 AI Services — Select which AI types to include:</div>",
    unsafe_allow_html=True,
)
_ai_c1, _ai_c2, _ai_c3 = st.columns(3)
include_predictive = _ai_c1.checkbox(
    "📈 Predictive AI",
    value=st.session_state.get("include_predictive", False),
    key="chk_predictive",
    help="ML-based scoring & forecasting: Next Best Action, Lead Scoring, Churn Score, Opportunity Scoring, etc.",
)
include_genai = _ai_c2.checkbox(
    "💬 GenAI",
    value=st.session_state.get("include_genai", False),
    key="chk_genai",
    help="Generative AI: Suggested Response, Call Summariser, Customer Summary, Voice Analyser, etc.",
)
include_agentic = _ai_c3.checkbox(
    "🤖 Agentic AI",
    value=st.session_state.get("include_agentic", False),
    key="chk_agentic",
    help="Multi-agent orchestration: Cross-Sell Agent, Outreach Agent, SR Categorisation, KYC Co-Pilot, etc.",
)
st.session_state["include_predictive"] = include_predictive
st.session_state["include_genai"]      = include_genai
st.session_state["include_agentic"]    = include_agentic

_ANY_AI = any([include_predictive, include_genai, include_agentic])
predictive_envs: list = list(st.session_state.get("predictive_envs", ["prod"]))
genai_envs:      list = list(st.session_state.get("genai_envs",      ["prod"]))
agentic_envs:    list = list(st.session_state.get("agentic_envs",    ["prod"]))
bedrock_monthly: float = float(st.session_state.get("bedrock_monthly", 3000.0))

if _ANY_AI:
    with st.expander("⚙️ AI Services — Environment & Cost Options", expanded=True):
        _ALL_AI_ENVS = ["prod", "uat", "training", "dr"]
        _ENV_LABELS  = {
            "prod": "🔵 Production", "uat": "🧪 UAT / Pre-Prod",
            "training": "🏋 Training", "dr": "🛡️ DR",
        }
        if include_predictive:
            st.markdown("**📈 Predictive AI — Environments**")
            _p_cols = st.columns(4)
            predictive_envs = [
                env for env, col in zip(_ALL_AI_ENVS, _p_cols)
                if col.checkbox(_ENV_LABELS[env], value=(env in predictive_envs),
                                key=f"ai_pred_{env}")
            ]
            if not predictive_envs:
                predictive_envs = ["prod"]
            st.session_state["predictive_envs"] = predictive_envs

        if include_genai:
            st.markdown("**💬 GenAI — Environments**")
            _g_cols = st.columns(4)
            genai_envs = [
                env for env, col in zip(_ALL_AI_ENVS, _g_cols)
                if col.checkbox(_ENV_LABELS[env], value=(env in genai_envs),
                                key=f"ai_genai_{env}")
            ]
            if not genai_envs:
                genai_envs = ["prod"]
            st.session_state["genai_envs"] = genai_envs

        if include_agentic:
            st.markdown("**🤖 Agentic AI — Environments**")
            _a_cols = st.columns(4)
            agentic_envs = [
                env for env, col in zip(_ALL_AI_ENVS, _a_cols)
                if col.checkbox(_ENV_LABELS[env], value=(env in agentic_envs),
                                key=f"ai_agent_{env}")
            ]
            if not agentic_envs:
                agentic_envs = ["prod"]
            st.session_state["agentic_envs"] = agentic_envs

        st.markdown("---")
        _br_col, _br_info = st.columns([2, 3])
        bedrock_monthly = float(_br_col.number_input(
            "☁️ AWS Bedrock Monthly Cost (USD)",
            min_value=0, value=int(st.session_state.get("bedrock_monthly", 3000)),
            step=100,
            key="ai_bedrock_monthly",
            help="Token-based AWS Bedrock LLM inference cost (GenAI + Agentic AI). "
                 "Default $3,000/mo — adjust for expected inference volume.",
        ))
        st.session_state["bedrock_monthly"] = bedrock_monthly
        _br_info.info(
            f"💡 **AWS Bedrock** managed LLM — no self-hosted GPU required.  \n"
            f"Monthly: **${bedrock_monthly:,.0f}**  |  Annual: **${bedrock_monthly*12:,.0f}**",
            icon="ℹ️",
        )

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
    previous_sync_aws = st.session_state.get("last_gcp_sync_aws_region", "us-east-1")
    previous_gcp_default = AWS_TO_GCP_REGION_MAP.get(previous_sync_aws, "us-central1")
    suggested_gcp_region = AWS_TO_GCP_REGION_MAP.get(aws_region_sel, "us-central1")
    current_gcp_region = st.session_state.get("selected_gcp_region", "us-central1")

    # Keep an explicit user-picked GCP region, but auto-sync when the current
    # selection still matches the previous AWS-driven default.
    if current_gcp_region == previous_gcp_default and suggested_gcp_region in gcp_region_options:
        st.session_state.selected_gcp_region = suggested_gcp_region
        st.session_state.gcp_region_sel = suggested_gcp_region

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
    st.session_state.last_gcp_sync_aws_region = aws_region_sel
    
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
    named_users_y1 = nu_val_col.number_input("Total Named Users (Y1)", min_value=0, value=15500, step=100, key="in_named_users")
    with nu_yoy_col:
        yoy_named_users = _yoy_select("YoY %", "yoy_named_users", default_pct=5)

    # ── Concurrent Users row (with YoY) ──
    cu_val_col, cu_yoy_col, cu_pad_col = st.columns([3, 1, 2])
    concurrent_y1 = cu_val_col.number_input("Concurrent Users (Y1)", min_value=0, value=4650, step=100, key="in_concurrent_users")
    with cu_yoy_col:
        yoy_concurrent = _yoy_select("YoY %", "yoy_concurrent", default_pct=5)

    # ── Mobile row ──
    mob_val_col, mob_yoy_col = st.columns([3, 1])
    mobile_y1 = mob_val_col.number_input("Concurrent Mobile Users (Y1)", min_value=0, value=4050, step=100, key="in_mobile_users")
    with mob_yoy_col:
        yoy_mobile = _yoy_select("YoY %", "yoy_mobile", default_pct=5)

    # ── Total Customers row ──
    cust_val_col, cust_yoy_col = st.columns([5, 1])
    total_customers_y1 = cust_val_col.number_input("Total Customers (Y1)", value=25_786_541, step=10_000, format="%d", key="in_total_customers")
    with cust_yoy_col:
        yoy_customers = _yoy_select("YoY %", "yoy_customers", default_pct=10)

    # ── Leads row ──
    leads_val_col, leads_yoy_col = st.columns([5, 1])
    leads_y1 = leads_val_col.number_input("Number of Leads (Y1)", value=10_700_000, step=10_000, format="%d", key="in_leads")
    with leads_yoy_col:
        yoy_leads = _yoy_select("YoY %", "yoy_leads", default_pct=10)

    # ── Cases row ──
    cases_val_col, cases_yoy_col = st.columns([5, 1])
    cases_y1 = cases_val_col.number_input("Number of Service Requests / Cases (Y1)", value=20_000, step=100, format="%d", key="in_cases")
    with cases_yoy_col:
        yoy_cases = _yoy_select("YoY %", "yoy_cases", default_pct=5)

# Build the YOY dict from widget values
YOY = dict(
    named_users=yoy_named_users,
    concurrent=yoy_concurrent,       # concurrent now has its own independent YoY rate
    mobile=yoy_mobile,               # mobile users has its own independent rate
    customers=yoy_customers,
    leads=yoy_leads,
    cases=yoy_cases,
    product_hold=0.05,               # product holdings — fixed at 5% (no explicit widget needed)
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
# SECTION 5 — One-Time Costs  (SaaS only — On-Prem is sizing only)
# ══════════════════════════════════════════════════════════════════════════
if client_mode != "onprem":
    with st.expander("💰 One-Time Costs  (Year 1 only — included in PUPM calculation)", expanded=True):
        st.caption("These are charged once in Year 1 and flow into: Total Cost → Discounted Cost → PUPM.")
        ot1, ot2, ot3 = st.columns(3)
        perf_testing_cost = ot1.number_input("Performance Testing ($)", min_value=0, value=5000, step=500, key="in_perf_testing")
        migration_cost    = ot2.number_input("Migration / Data Bootup ($)", min_value=0, value=5000, step=500, key="in_migration_cost")
        managed_svc_onetime = ot3.number_input("Managed Services Setup ($)", min_value=0, value=1000, step=100, key="in_managed_svc")
        one_time_total_display = perf_testing_cost + migration_cost + managed_svc_onetime
        st.markdown(
            f"<div style='margin: 1.5rem 0 0.5rem 0; padding:12px 18px; background:var(--surface2); border-radius:10px; border:1px solid var(--border); box-shadow:var(--shadow);'>"
            f"<span style='font-size:0.85rem; font-weight:600; color:var(--text2);'>Estimated One-Time Migration:</span> &nbsp; "
            f"<strong style='font-size:1.1rem; color:var(--accent);'>${one_time_total_display:,.0f}</strong>"
            f"</div>",
            unsafe_allow_html=True,
        )
else:
    # On-Prem: no pricing, zero out one-time cost variables
    perf_testing_cost   = 0
    migration_cost      = 0
    managed_svc_onetime = 0


# ══════════════════════════════════════════════════════════════════════════
# SECTION 6 — Workload Profile
# ══════════════════════════════════════════════════════════════════════════
with st.expander("⚙️ Workload Profile", expanded=False):
    wc1, wc2 = st.columns(2)
    workload_type = wc1.selectbox("Workload Type",
                       ["banking_crm", "retail_crm", "sme_crm", "insurance_crm"],
                       key="in_workload_type")
    peak_load     = wc2.selectbox("Peak Load", ["normal", "high", "very_high"],
                       key="in_peak_load")
    wc3, wc4, wc5 = st.columns(3)
    mobile_heavy    = wc3.checkbox("Mobile-heavy workload",   value=(mobile_y1 > 3000),
                       key="in_mobile_heavy")
    _reporting_db_disabled = (db_type == "PostgreSQL")
    reporting_db    = wc4.checkbox(
        "Reporting DB required",
        value=False if _reporting_db_disabled else True,
        disabled=_reporting_db_disabled,
        help="Not applicable for PostgreSQL — already runs in HA (Patroni), no separate Reporting DB needed." if _reporting_db_disabled else None,
        key="in_reporting_db",
    )
    if _reporting_db_disabled:
        wc4.caption("🔒 Disabled — PostgreSQL is HA")
    high_compliance = wc5.checkbox("High compliance / audit", value=True, key="in_high_compliance")
    workload_notes  = st.text_input("Additional notes",
                         placeholder="e.g. heavy batch jobs, real-time analytics",
                         key="in_workload_notes")

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
concurrent_arr   = [concurrent_y1]
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

# ── Chatbot retrigger banner ──────────────────────────────────────────────
_chatbot_retrigger = st.session_state.get("chatbot_retrigger", False)
if _chatbot_retrigger:
    st.session_state.chatbot_retrigger = False
    # Clear stale chat context so it gets rebuilt after regeneration
    st.session_state.pop("chat_context", None)
    st.info(
        "🤖 **Chatbot-initiated retrigger** — inputs updated from your chat conversation. "
        "Regenerating estimate with the new values…",
        icon="🔄",
    )

st.markdown('<span class="green-btn-target"></span>', unsafe_allow_html=True)
if st.button(btn_label, type="primary", use_container_width=True, key="btn_generate") or _chatbot_retrigger:
    inputs = {
        "named_users": named_users_y1, "concurrent_users": concurrent_y1,
        "total_customers": total_customers_y1, "leads": leads_y1,
        "cases": cases_y1, "mobile_users": mobile_y1,
        # YOY growth rates → written to column I of Customer Volumes sheet
        "yoy_named_users": yoy_named_users,
        "yoy_concurrent":  yoy_concurrent,    # concurrent now uses its own YoY rate
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
            distribution = distribute_nodes(
                metrics=metrics,
                workload_profile=workload_profile,
                use_llm=use_llm,
                db_type=db_type,
                include_clickhouse=include_clickhouse,
                ch_data_multiplier=ch_data_multiplier,
                include_predictive=include_predictive,
                include_genai=include_genai,
                include_agentic=include_agentic,
                predictive_envs=predictive_envs,
                genai_envs=genai_envs,
                agentic_envs=agentic_envs,
                bedrock_monthly=bedrock_monthly,
                dr_scale=dr_scale,
            )
            st.session_state.last_distribution = distribution
            st.session_state.last_ai_sizing = distribution.get("ai_nodes", {"enabled": False})

        pricing = None
        env_pricing = None

        if client_mode == "saas":
            with st.spinner("Step 4 — Fetching AWS prices…"):
                pricing = calculate_pricing(distribution, metrics, region=aws_region_sel,
                                            instance_overrides=st.session_state.get("instance_overrides", {}))
                st.session_state.last_pricing = pricing

            with st.spinner("Step 4b — Fetching GCP prices…"):
                gcp_pricing = calculate_gcp_pricing(distribution, metrics, region=gcp_region_sel)
                st.session_state.gcp_pricing = gcp_pricing
                comparison  = build_comparison(pricing, gcp_pricing)
                st.session_state.comparison = comparison

            if env_multiplier > 0 or include_dr:
                with st.spinner("Step 5 — Pricing environments…"):
                    # Pass deployment mode: "saas" for cloud or "onprem" for on-premise
                    deployment_mode = "saas" if client_mode == "saas" else "onprem"
                    env_pricing = price_additional_environments(
                        db_type=db_type, deployment=deployment_mode, metrics=metrics,
                        preprod_region=aws_region_sel, dr_region=dr_region_sel,
                        dr_scale=dr_scale,
                        distribution=distribution,
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
            # On-Prem: no pricing calculation at all — sizing only.
            # DR and Pre-Prod requirements go into the on-prem XLSX workbook,
            # not into the dashboard or cloud_sizing.xlsx.
            st.session_state.last_pricing = None
            st.session_state.env_pricing  = None

        with st.spinner("Generating Excel files…"):
            excel_paths = generate_excel_reports(
                pricing=pricing, distribution=distribution, metrics=metrics,
                customer=customer_name, output_dir="reports",
                env_pricing=st.session_state.env_pricing,
                db_type=db_type, client_mode=client_mode,
                gcp_pricing=st.session_state.get("gcp_pricing"),
                comparison=st.session_state.get("comparison"),
                include_dr=include_dr,
                env_names=env_names,
                dr_scale=dr_scale,
                ai_sizing=st.session_state.get("last_ai_sizing"),
            )
            st.session_state.cloud_sizing_xlsx        = excel_paths.get("cloud_sizing")
            st.session_state.aws_pricing_xlsx         = excel_paths.get("aws_pricing")
            st.session_state.gcp_pricing_xlsx         = excel_paths.get("gcp_pricing")
            st.session_state.onprem_sizing_xlsx       = excel_paths.get("onprem_sizing")
            st.session_state.onprem_oracle_sizing_xlsx = excel_paths.get("onprem_oracle_sizing")
            st.session_state.ai_sizing_xlsx           = excel_paths.get("ai_sizing")
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
                    ai_sizing=st.session_state.get("last_ai_sizing"),
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
    <div class="bn-alert-banner success">
      <span style="font-size:16px">✓</span>
      <span style="font-size:12px;font-weight:600;">Estimate generated and saved successfully!</span>
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

# ── AI Services Sizing Results ────────────────────────────────────────────
if (st.session_state.get("last_ai_sizing") or {}).get("enabled"):
    from ui_components import render_ai_sizing
    render_ai_sizing(st.session_state.last_ai_sizing)

if client_mode == "saas" and st.session_state.last_pricing:
    p = st.session_state.last_pricing
    five_yr = p.get("inflation_forecast", {}).get("five_year_total", 0)
    divider()
    cost_banner(p["total_monthly_usd"], p["total_annual_usd"], five_yr)
    render_db_selection(p)
    render_pricing_results(p, updated_file=st.session_state.last_updated_file)
    render_inflation_forecast(p)

if client_mode == "saas" and st.session_state.env_pricing:
    render_env_pricing(st.session_state.env_pricing, client_mode=client_mode)


#if client_mode == "onprem" and st.session_state.last_distribution:
#    st.info(
#        "**On-Premise mode:** No AWS pricing is calculated. "
#        "The Cloud Sizing XLSX contains infrastructure requirements only.",
#        icon="ℹ️",
#    )

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
if st.session_state.cloud_sizing_xlsx or st.session_state.aws_pricing_xlsx or st.session_state.get("onprem_sizing_xlsx"):
    divider()
    section_title("📥", "Download Reports")
    cname = re.sub(r'[^a-zA-Z0-9_\-]', '_', st.session_state.customer_name_snap)

    # Derive active db for on-prem labels
    _active_db = st.session_state.get("db_type_snap", db_type)
    _db_slug   = _active_db.lower().replace(" ", "_")

    # ── Column layout
    if client_mode == "saas":
        cols = st.columns(2)
        xl1, xl2 = cols[0], cols[1]
        xl3 = None
    else:
        # On-Prem always has 3 buttons: Cloud Sizing + OpenShift + Kubeadm
        cols = st.columns(3)
        xl1, xl2, xl3 = cols[0], cols[1], cols[2]

    # Button 1: Cloud Sizing (always)
    if st.session_state.cloud_sizing_xlsx:
        try:
            with open(st.session_state.cloud_sizing_xlsx, "rb") as f:
                xl1.download_button("📊 Cloud Sizing (XLSX)", f,
                    file_name=f"cloud_sizing_{cname}.xlsx",
                    key="dl_cloud_sizing", use_container_width=True)
        except Exception as e:
            st.error(f"Error downloading Cloud Sizing: {e}")

    # Button 2: SaaS → Pricing Forecast / On-Prem → OpenShift sizing
    if client_mode == "saas" and st.session_state.get("aws_pricing_xlsx"):
        try:
            with open(st.session_state.aws_pricing_xlsx, "rb") as f:
                xl2.download_button("💰 Pricing Forecast (XLSX)", f,
                    file_name=f"cloud_pricing_{cname}.xlsx",
                    key="dl_aws_pricing", use_container_width=True)
        except Exception as e:
            st.error(f"Error downloading Pricing Forecast: {e}")

    if client_mode == "onprem":
        # Button 2: OpenShift sizing — selected DB
        if st.session_state.get("onprem_sizing_xlsx"):
            try:
                with open(st.session_state.onprem_sizing_xlsx, "rb") as f:
                    xl2.download_button(
                        f"🏢 OpenShift — {_active_db} (XLSX)", f,
                        file_name=f"onprem_openshift_{_db_slug}_sizing_{cname}.xlsx",
                        key="dl_onprem_openshift", use_container_width=True,
                    )
            except Exception as e:
                st.error(f"Error downloading OpenShift Sizing: {e}")

        # Button 3: Kubeadm sizing — same selected DB
        if xl3 is not None and st.session_state.get("onprem_oracle_sizing_xlsx"):
            try:
                with open(st.session_state.onprem_oracle_sizing_xlsx, "rb") as f:
                    xl3.download_button(
                        f"🏢 Kubeadm — {_active_db} (XLSX)", f,
                        file_name=f"onprem_kubeadm_{_db_slug}_sizing_{cname}.xlsx",
                        key="dl_onprem_kubeadm", use_container_width=True,
                    )
            except Exception as e:
                st.error(f"Error downloading Kubeadm Sizing: {e}")

    # AI Services XLSX download
    if st.session_state.get("ai_sizing_xlsx"):
        try:
            with open(st.session_state.ai_sizing_xlsx, "rb") as f:
                st.download_button(
                    "🤖 AI Services Sizing (XLSX)", f,
                    file_name=f"ai_services_sizing_{cname}.xlsx",
                    key="dl_ai_sizing", use_container_width=True,
                )
        except Exception as e:
            st.error(f"Error downloading AI Sizing: {e}")

    if client_mode != "onprem" and st.session_state.get("pdf_report_path"):
        try:
            with open(st.session_state.pdf_report_path, "rb") as f:
                pdf_bytes = f.read()
            st.markdown("""
            <div class="bn-panel">
              <div class="bn-panel-header">
                <span class="bn-dot warn"></span>
                <span class="bn-panel-title">Full Pricing Report (PDF)</span>
                <span class="bn-badge warn">Executive Summary · PUPM · 5-Yr Forecast</span>
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

# ── Chatbot (SaaS and On-Premise) ────────────────────────────────────────────────────
if st.session_state.last_distribution:
    render_chatbot(
        pricing=st.session_state.last_pricing,
        distribution=st.session_state.last_distribution,
        metrics=st.session_state.last_metrics,
        client_mode=client_mode,
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
