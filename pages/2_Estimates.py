"""
pages/2_Estimates.py — Versioned estimate history for a selected client
"""
import os
import re
import pathlib
import streamlit as st
from database import get_estimates_by_client, get_estimate_by_id, get_estimate_files, delete_estimate
from rbac import can, role_badge

# ── Auth guard ────────────────────────────────────────────────────────────
# Auth is now handled by st.navigation in app.py

client = st.session_state.get("selected_client")
if not client:
    st.switch_page("pages/1_Clients.py")

# Config handled by app.py

st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@500;600;700;800&family=Inter:wght@400;500;600&display=swap');
  html, body, [data-testid="stAppViewContainer"] { font-family: 'Inter', sans-serif; background-color: var(--bg) !important; color: var(--text) !important; }

  .page-header {
    padding: 1.25rem 0 1.75rem;
    border-bottom: 2px solid var(--border);
    margin-bottom: 2rem;
    position: relative;
  }
  .page-header::after {
    content: '';
    position: absolute;
    bottom: -2px; left: 0;
    width: 60px; height: 2px;
    background: linear-gradient(90deg, var(--accent), var(--accent2));
  }
  .breadcrumb { font-size: 0.78rem; color: var(--text2); margin-bottom: 0.5rem; }
  .breadcrumb a { color: var(--accent); text-decoration: none; }
  .page-title { font-family: 'Plus Jakarta Sans', sans-serif; font-size: 1.75rem; font-weight: 800; color: var(--text); letter-spacing: -0.025em; }
  .page-subtitle { color: var(--text2); font-size: 0.85rem; margin-top: 0.25rem; }

  .estimate-card {
    background: var(--surface);
    border: 1.5px solid rgba(79,142,247,0.2);
    border-left: 4px solid var(--accent);
    border-radius: 14px;
    padding: 1.25rem 1.5rem;
    margin-bottom: 1rem;
    transition: border-color 0.2s, box-shadow 0.2s, transform 0.2s;
    display: flex; align-items: center; gap: 1rem;
    box-shadow: 0 4px 20px rgba(0,0,0,0.3), 0 1px 4px rgba(0,0,0,0.2);
  }
  .estimate-card:hover {
    border-color: rgba(79,142,247,0.5);
    border-left-color: var(--accent2);
    box-shadow: 0 6px 24px rgba(79,142,247,0.2);
    transform: translateX(3px);
  }

  .version-badge {
    background: linear-gradient(135deg, #4f8ef7, #3b7de8);
    border-radius: 8px; padding: 0.4rem 0.85rem;
    font-family: 'Syne', sans-serif; font-size: 0.95rem;
    font-weight: 700; color: white; white-space: nowrap;
    flex-shrink: 0;
  }
  .est-info { flex: 1; min-width: 0; }
  .est-date { font-size: 0.78rem; color: var(--text3); margin-bottom: 0.2rem; }
  .est-mode { font-size: 0.82rem; font-weight: 600; color: var(--text); }
  .est-cost { font-size: 0.82rem; color: var(--accent3); }
  .mode-badge {
    display: inline-block; font-size: 0.68rem; font-weight: 600;
    padding: 0.15rem 0.5rem; border-radius: 5px; margin-left: 0.5rem;
  }
  .mode-saas { background: rgba(0,212,170,0.15); color: #00d4aa; }
  .mode-onprem { background: rgba(79,142,247,0.15); color: #4f8ef7; }

  .empty-state {
    text-align: center; padding: 4rem 2rem;
    color: #5a637a;
  }
  .empty-icon { font-size: 3rem; margin-bottom: 1rem; }
  .empty-title { font-family: 'Syne', sans-serif; font-size: 1.2rem; color: #8b9ab8; }

  div.stButton > button {
    border-radius: 8px !important; font-size: 0.8rem !important;
    padding: 0.4rem 0.75rem !important; font-weight: 600 !important;
  }

  /* ── Force dark on ALL Streamlit native containers ── */
  .stApp, section[data-testid="stMain"], section[data-testid="stMain"] > *,
  div[data-testid="stMainBlockContainer"], div[data-testid="stMainBlockContainer"] > *,
  div[data-testid="block-container"], div[data-testid="block-container"] > *,
  div[data-testid="stVerticalBlock"], div[data-testid="stHorizontalBlock"],
  .main, .main > * { background-color: #0a0e1a !important; color: #e8edf8 !important; }
  input, textarea, select, div[data-baseweb="input"] > div,
  div[data-baseweb="base-input"] > input, div[data-baseweb="select"] > div,
  div[data-testid="stDateInput"] input, div[data-testid="stTextInput"] input,
  div[data-testid="stNumberInput"] input, div[role="listbox"], div[role="option"] {
    background-color: #151d35 !important; color: #e8edf8 !important; border-color: #2a3555 !important;
  }
  div[data-testid="stExpander"], div[data-testid="stExpander"] > div {
    background-color: #151d35 !important; border-color: #2a3555 !important;
  }
  div[data-testid="stAlert"] { background-color: #151d35 !important; border-color: #2a3555 !important; }

  /* ── Auto-hide sidebar ──────────────────────────────────────────── */
  [data-testid="stSidebar"] {
    width: 60px !important;
    min-width: 60px !important;
    overflow: hidden !important;
    transition: width 0.3s ease, min-width 0.3s ease !important;
  }
  [data-testid="stSidebar"]:hover {
    width: 280px !important;
    min-width: 280px !important;
  }
  [data-testid="stSidebar"]:not(:hover) [data-testid="stSidebarNavLink"] p,
  [data-testid="stSidebar"]:not(:hover) [data-testid="stSidebarNavSectionHeader"],
  [data-testid="stSidebar"]:not(:hover) .stMarkdown {
    opacity: 0 !important;
    transition: opacity 0.15s ease !important;
  }
  [data-testid="stSidebar"]:hover [data-testid="stSidebarNavLink"] p,
  [data-testid="stSidebar"]:hover [data-testid="stSidebarNavSectionHeader"],
  [data-testid="stSidebar"]:hover .stMarkdown {
    opacity: 1 !important;
    transition: opacity 0.25s ease 0.1s !important;
  }
  /* Hide collapse button */
  [data-testid="stSidebarCollapseButton"],
  button[data-testid="collapsedControl"] {
    display: none !important;
  }
  /* Remove empty sidebar box */
  [data-testid="stSidebarUserContent"] {
    display: none !important;
    height: 0 !important;
    min-height: 0 !important;
    padding: 0 !important;
    margin: 0 !important;
    overflow: hidden !important;
  }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<style>
/* ═══════════════════════════════════════════════
   NUCLEAR DARK MODE — hardcoded, no config needed
═══════════════════════════════════════════════ */

/* Every possible Streamlit container */
html, body,
.stApp,
[data-testid="stAppViewContainer"],
[data-testid="stMain"],
[data-testid="stMainBlockContainer"],
[data-testid="block-container"],
[data-testid="stVerticalBlock"],
[data-testid="stHorizontalBlock"],
[data-testid="stSidebar"],
[data-testid="stSidebarContent"],
[data-testid="stSidebarUserContent"],
[data-testid="stHeader"],
[data-testid="stToolbar"],
[data-testid="stDecoration"],
[data-testid="stStatusWidget"],
section.main,
.main,
.block-container,
div[class*="appview"],
div[class*="main"],
div[class*="block"] {
  background-color: #0a0e1a !important;
  color: #e8edf8 !important;
}

/* Sidebar specifically */
[data-testid="stSidebar"],
[data-testid="stSidebar"] > div,
[data-testid="stSidebarContent"] {
  background-color: #0f1629 !important;
  border-right: 2px solid rgba(79,142,247,0.2) !important;
}

/* Sidebar nav items */
[data-testid="stSidebarNav"],
[data-testid="stSidebarNavItems"],
[data-testid="stSidebarNavLink"],
[data-testid="stSidebarNavLink"] * {
  background-color: #0f1629 !important;
  color: #e8edf8 !important;
}

/* All inputs */
input, textarea, select {
  background-color: #1c2640 !important;
  color: #e8edf8 !important;
  border: 1px solid #2a3555 !important;
}

/* Streamlit input wrappers */
[data-testid="stTextInput"] > div > div,
[data-testid="stTextInput"] input,
[data-testid="stNumberInput"] > div > div,
[data-testid="stNumberInput"] input,
[data-testid="stDateInput"] > div > div,
[data-testid="stDateInput"] input,
[data-testid="stTimeInput"] input,
[data-testid="stTextArea"] textarea {
  background-color: #1c2640 !important;
  color: #e8edf8 !important;
  border-color: #2a3555 !important;
}

/* Selectbox / dropdown */
[data-testid="stSelectbox"] > div > div,
[data-baseweb="select"] > div,
[data-baseweb="input"] > div,
[data-baseweb="base-input"],
[data-baseweb="base-input"] > div,
[data-baseweb="popover"],
[data-baseweb="menu"],
[role="listbox"],
[role="option"],
ul[role="listbox"],
li[role="option"] {
  background-color: #151d35 !important;
  color: #e8edf8 !important;
  border-color: #2a3555 !important;
}

/* Slider */
[data-testid="stSlider"] > div > div > div,
[data-testid="stSlider"] div[role="slider"] {
  background-color: #2a3555 !important;
}

/* Expanders */
[data-testid="stExpander"],
[data-testid="stExpander"] > div,
[data-testid="stExpander"] summary {
  background-color: #151d35 !important;
  border-color: #2a3555 !important;
  color: #e8edf8 !important;
}

/* Tabs */
[data-baseweb="tab-list"],
[data-baseweb="tab"],
[data-baseweb="tab-panel"],
[role="tabpanel"],
[role="tab"] {
  background-color: #151d35 !important;
  color: #e8edf8 !important;
  border-color: #2a3555 !important;
}
[aria-selected="true"] {
  background-color: #4f8ef7 !important;
  color: #ffffff !important;
}

/* Alerts / info boxes */
[data-testid="stAlert"],
[data-testid="stAlert"] > div,
[data-testid="stNotification"] {
  background-color: #151d35 !important;
  border-color: #2a3555 !important;
  color: #e8edf8 !important;
}

/* Metrics */
[data-testid="stMetric"],
[data-testid="stMetricValue"],
[data-testid="stMetricLabel"],
[data-testid="stMetricDelta"] {
  background-color: #151d35 !important;
  color: #e8edf8 !important;
}

/* Dataframes */
[data-testid="stDataFrame"],
[data-testid="stDataFrame"] > div,
[data-testid="stTable"],
.stDataFrame iframe {
  background-color: #151d35 !important;
  color: #e8edf8 !important;
}

/* Checkboxes, radios */
[data-testid="stCheckbox"],
[data-testid="stRadio"],
[data-testid="stRadio"] > div,
[data-testid="stCheckbox"] > label {
  color: #e8edf8 !important;
}

/* All labels */
label, .stMarkdown p, .stMarkdown span,
p, span, li {
  color: #e8edf8 !important;
}

/* Dividers */
hr { border-color: #2a3555 !important; }

/* Scrollbar */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: #0a0e1a; }
::-webkit-scrollbar-thumb { background: #2a3555; border-radius: 10px; }
::-webkit-scrollbar-thumb:hover { background: #4f8ef7; }
</style>
""", unsafe_allow_html=True)

# ── Header ─────────────────────────────────────────────────────────────────
hdr_l, hdr_r = st.columns([5, 1])
with hdr_l:
    st.markdown(f"""
    <div class="page-header">
      <div class="breadcrumb">
        Clients › <strong style="color:var(--text)">{client['name']}</strong>
      </div>
      <div class="page-title">{client['name']} <span style="vertical-align: text-bottom;">{role_badge()}</span></div>
      <div class="page-subtitle">{client.get('sector','Banking')} · All versioned cost estimates</div>
    </div>
    """, unsafe_allow_html=True)
with hdr_r:
    st.markdown("<div style='padding-top:1.2rem'></div>", unsafe_allow_html=True)
    if st.button("← Clients", key="back_to_clients", use_container_width=True):
        st.switch_page("pages/1_Clients.py")

# ── New estimate button ────────────────────────────────────────────────────
new_l, _ = st.columns([2, 5])
with new_l:
    if can("create_estimate"):
        if st.button("➕  New Estimate", key="new_est_top", type="primary", use_container_width=True):
            st.session_state.load_estimate = None
            for k in ["last_metrics","last_distribution","last_pricing","env_pricing",
                      "gcp_pricing","comparison","cloud_sizing_xlsx","aws_pricing_xlsx",
                      "gcp_pricing_xlsx","pdf_report_path","last_saved_id","client_mode",
                      "show_summary","summary_df","show_success","last_updated_file"]:
                st.session_state[k] = None if k not in ["show_summary","show_success"] else False
            st.switch_page("pages/3_Estimator.py")

st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)

# ── Estimates list ─────────────────────────────────────────────────────────
try:
    estimates = get_estimates_by_client(client["id"])
except Exception as e:
    st.error(f"Error loading estimates: {e}")
    estimates = []

if not estimates:
    st.markdown("""
    <div class="empty-state">
      <div class="empty-icon">📭</div>
      <div class="empty-title">No estimates yet</div>
      <div style="margin-top:0.5rem;font-size:0.85rem;">
        Click <strong>New Estimate</strong> above to create the first one.
      </div>
    </div>
    """, unsafe_allow_html=True)
else:
    for est in estimates:
        eid      = est["id"]
        version  = est.get("version") or "—"
        date_str = est["estimate_date"].strftime("%d %b %Y") if est.get("estimate_date") else "—"
        mode     = est.get("client_mode", "saas")
        db_type  = est.get("db_type", "PostgreSQL")
        monthly  = est.get("total_monthly_usd") or 0
        five_yr  = est.get("total_5year_usd") or 0
        mode_lbl = "SaaS" if mode == "saas" else "On-Prem"
        mode_cls = "mode-saas" if mode == "saas" else "mode-onprem"
        cost_str = f"${monthly:,.0f}/mo" if monthly else "Sizing only"
        f5_str   = f" · ${five_yr:,.0f} over 5yr" if five_yr else ""

        row_l, row_r = st.columns([6, 4])
        with row_l:
            st.markdown(f"""
            <div class="estimate-card">
              <div class="version-badge">v{version}</div>
              <div class="est-info">
                <div class="est-date">📅 {date_str} &nbsp;·&nbsp; {db_type}</div>
                <div class="est-mode">
                  {mode_lbl}
                  <span class="mode-badge {mode_cls}">{mode_lbl}</span>
                </div>
                <div class="est-cost">💰 {cost_str}{f5_str}</div>
              </div>
            </div>
            """, unsafe_allow_html=True)
        with row_r:
            st.markdown("<div style='padding-top:0.6rem'></div>", unsafe_allow_html=True)
            a, b, c, d = st.columns(4)

            if a.button("Load", key=f"load_{eid}", use_container_width=True, type="primary"):
                data = get_estimate_by_id(eid)
                if data:
                    st.session_state.client_mode        = data["client_mode"]
                    st.session_state.last_metrics       = data["all_metrics"]
                    st.session_state.last_pricing       = data["pricing_json"]
                    st.session_state.last_distribution  = data["distribution_json"]
                    st.session_state.env_pricing        = data["env_pricing_json"]
                    st.session_state.customer_name_snap = data["customer_name"]
                    st.session_state.db_type_snap       = data.get("db_type", "PostgreSQL")
                    st.session_state.last_saved_id      = eid
                    st.session_state.load_estimate      = data
                    # Restore Excel files
                    files = get_estimate_files(eid)
                    pathlib.Path("reports").mkdir(exist_ok=True)
                    if files.get("cloud_sizing"):
                        p = f"reports/restored_cloud_sizing_{eid}.xlsx"
                        open(p, "wb").write(files["cloud_sizing"])
                        st.session_state.cloud_sizing_xlsx = p
                    if files.get("aws_pricing"):
                        p = f"reports/restored_aws_pricing_{eid}.xlsx"
                        open(p, "wb").write(files["aws_pricing"])
                        st.session_state.aws_pricing_xlsx = p
                    st.switch_page("pages/3_Estimator.py")

            if can("delete_estimate"):
                if b.button("🗑", key=f"del_{eid}", use_container_width=True):
                    delete_estimate(eid)
                    st.rerun()

            # Download XLSX
            files = get_estimate_files(eid)
            if files.get("cloud_sizing"):
                c.download_button(
                    "📊", files["cloud_sizing"],
                    file_name=f"cloud_sizing_v{version}.xlsx",
                    key=f"dl_sizing_{eid}", use_container_width=True,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            if files.get("aws_pricing"):
                d.download_button(
                    "💰", files["aws_pricing"],
                    file_name=f"pricing_v{version}.xlsx",
                    key=f"dl_pricing_{eid}", use_container_width=True,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )