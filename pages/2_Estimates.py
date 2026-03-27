"""
pages/2_Estimates.py — Versioned estimate history for a selected client
"""
import os
import re
import pathlib
import streamlit as st
from database import get_estimates_by_client, get_estimate_by_id, get_estimate_files, delete_estimate
from rbac import can, role_badge
from theme import inject_theme

inject_theme()

# ── Auth guard ────────────────────────────────────────────────────────────
# Auth is now handled by st.navigation in app.py

client = st.session_state.get("selected_client")
if not client:
    st.switch_page("pages/1_Clients.py")

# Config handled by app.py

st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@500;600;700;800&family=Inter:wght@400;500;600&display=swap');

  .page-header {
    padding: 1.25rem 0 1.75rem;
    border-bottom: 2px solid #fadde1;
    margin-bottom: 2rem;
    position: relative;
  }
  .page-header::after {
    content: '';
    position: absolute;
    bottom: -2px; left: 0;
    width: 60px; height: 2px;
    background: linear-gradient(90deg, #ff69b4, #fadde1);
  }
  .breadcrumb { font-size: 0.78rem; color: #555555; margin-bottom: 0.5rem; }
  .breadcrumb a { color: #ff69b4; text-decoration: none; }
  .page-title { font-family: 'Plus Jakarta Sans', sans-serif; font-size: 1.75rem; font-weight: 800; color: #111111; letter-spacing: -0.025em; }
  .page-subtitle { color: #555555; font-size: 0.85rem; margin-top: 0.25rem; }

  .estimate-card {
    background: #ffffff;
    border: 1.5px solid #fadde1;
    border-left: 4px solid #ff69b4;
    border-radius: 14px;
    padding: 1.25rem 1.5rem;
    margin-bottom: 1rem;
    transition: border-color 0.2s, box-shadow 0.2s, transform 0.2s;
    display: flex; align-items: center; gap: 1rem;
    box-shadow: 0 4px 16px rgba(0,0,0,0.07), 0 1px 4px rgba(0,0,0,0.04);
  }
  .estimate-card:hover {
    border-color: #ff69b4;
    border-left-color: #c2185b;
    box-shadow: 0 6px 24px rgba(255,105,180,0.15);
    transform: translateX(3px);
  }

  .version-badge {
    background: linear-gradient(135deg, #ff69b4, #c2185b);
    border-radius: 8px; padding: 0.4rem 0.85rem;
    font-family: 'Plus Jakarta Sans', sans-serif; font-size: 0.95rem;
    font-weight: 700; color: white; white-space: nowrap;
    flex-shrink: 0;
  }
  .est-info { flex: 1; min-width: 0; }
  .est-date { font-size: 0.78rem; color: #555555; margin-bottom: 0.2rem; }
  .est-mode { font-size: 0.82rem; font-weight: 600; color: #111111; }
  .est-cost { font-size: 0.82rem; color: #aacc00; font-weight: 600; }
  .mode-badge {
    display: inline-block; font-size: 0.68rem; font-weight: 600;
    padding: 0.15rem 0.5rem; border-radius: 5px; margin-left: 0.5rem;
  }
  .mode-saas { background: rgba(170,204,0,0.15); color: #6b8800; }
  .mode-onprem { background: rgba(255,105,180,0.1); color: #c2185b; }

  .empty-state {
    text-align: center; padding: 4rem 2rem;
    color: #555555;
  }
  .empty-icon { font-size: 3rem; margin-bottom: 1rem; }
  .empty-title { font-family: 'Plus Jakarta Sans', sans-serif; font-size: 1.2rem; color: #888888; }

  div.stButton > button {
    border-radius: 8px !important; font-size: 0.8rem !important;
    padding: 0.4rem 0.75rem !important; font-weight: 600 !important;
  }

  /* Load button — faded green idle, vivid on hover */
  div.stButton > button[kind="primary"] {
    background: #ddeea0 !important;
    border: 1px solid #bbcc66 !important;
    color: #556600 !important;
    font-weight: 700 !important;
    box-shadow: 0 1px 4px rgba(170,204,0,0.15) !important;
  }
  div.stButton > button[kind="primary"]:hover {
    background: #aacc00 !important;
    border-color: #88aa00 !important;
    color: #ffffff !important;
    box-shadow: 0 4px 14px rgba(170,204,0,0.4) !important;
  }

  /* ── Sidebar — black theme ── */
  /* ── Page content tweaks ── */
</style>
""", unsafe_allow_html=True)

inject_theme()

# ── Top Navigation ────────────────────────────────────────────────────────
top_logo, top_nav = st.columns([10, 2])
with top_logo:
    st.image("assets/logo.png", width=180)
with top_nav:
    if st.button("← Clients", key="nav_back_clients", use_container_width=True):
        st.switch_page("pages/1_Clients.py")

# ── Header ─────────────────────────────────────────────────────────────────
st.markdown(f"""
<div class="page-header" style="margin-top:-1.5rem;">
  <div class="breadcrumb">
    Clients › <strong style="color:var(--text)">{client['name']}</strong>
  </div>
  <div class="page-title">{client['name']} <span style="vertical-align: text-bottom;">{role_badge()}</span></div>
  <div class="page-subtitle">{client.get('sector','Banking')} · All versioned cost estimates</div>
</div>
""", unsafe_allow_html=True)

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