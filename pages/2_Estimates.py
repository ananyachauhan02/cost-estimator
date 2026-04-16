"""
pages/2_Estimates.py — Versioned estimate history matching businessnext_ui.html
"""
import os
import pathlib
import streamlit as st
from database import get_estimates_by_client, get_estimate_by_id, get_estimate_files, delete_estimate
from rbac import can
from theme import inject_theme

# ── Auth guard ────────────────────────────────────────────────────────────
client = st.session_state.get("selected_client")
if not client:
    st.switch_page("pages/1_Clients.py")

inject_theme()

# Compact button overrides for estimate history action buttons
st.markdown("""
<style>
.stButton > button {
  padding: 4px 10px !important;
  font-size: 11px !important;
  min-height: 28px !important;
  height: 28px !important;
  border-radius: 6px !important;
}
.stButton > button[data-testid="stBaseButton-primary"] {
  background: var(--accent) !important;
  color: #fff !important;
}
.stDownloadButton > button {
  padding: 4px 10px !important;
  font-size: 11px !important;
  min-height: 28px !important;
  height: 28px !important;
  border-radius: 6px !important;
}
</style>
""", unsafe_allow_html=True)

# ── Page header ──────────────────────────────────────────────────────────
hdr_l, hdr_r = st.columns([4, 2])
with hdr_l:
    st.markdown(f"""
    <div class="bn-page-header">
      <div>
        <div class="bn-page-title">{client['name']} — Estimates</div>
        <div class="bn-page-subtitle">{client.get('sector','Banking')} · All versioned cost estimates</div>
      </div>
    </div>
    """, unsafe_allow_html=True)
with hdr_r:
    st.markdown("<div style='padding-top:1.5rem'></div>", unsafe_allow_html=True)
    ba, bb = st.columns(2)
    if ba.button("← All Clients", key="back_to_clients", use_container_width=True):
        st.switch_page("pages/1_Clients.py")
    if can("create_estimate"):
        if bb.button("+ New Estimate", key="new_est_top", use_container_width=True, type="primary"):
            st.session_state.load_estimate = None
            for k in ["last_metrics","last_distribution","last_pricing","env_pricing",
                      "gcp_pricing","comparison","cloud_sizing_xlsx","aws_pricing_xlsx",
                      "gcp_pricing_xlsx","pdf_report_path","last_saved_id","client_mode",
                      "show_summary","summary_df","show_success","last_updated_file"]:
                st.session_state[k] = None if k not in ["show_summary","show_success"] else False
            st.switch_page("pages/3_Estimator.py")

# ── Estimates list ────────────────────────────────────────────────────────
try:
    estimates = get_estimates_by_client(client["id"])
except Exception as e:
    st.error(f"Error loading estimates: {e}")
    estimates = []

est_count = len(estimates)
st.markdown(f"""
<div class="bn-panel">
  <div class="bn-panel-header">
    <span class="bn-dot accent"></span>
    <span class="bn-panel-title">Estimate History</span>
    <span class="bn-badge accent">{est_count} estimate{'s' if est_count != 1 else ''}</span>
  </div>
</div>
""", unsafe_allow_html=True)

if not estimates:
    st.markdown("""
    <div class="bn-panel">
      <div class="bn-panel-body">
        <div class="bn-empty-state">
          <div class="bn-empty-icon">📭</div>
          <div class="bn-empty-title">No estimates yet</div>
          <div class="bn-empty-sub">Click <strong>+ New Estimate</strong> above to create the first one.</div>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)
else:
    # Render estimates inside a panel body
    st.markdown('<div class="bn-panel"><div>', unsafe_allow_html=True)

    for est in estimates:
        eid      = est["id"]
        version  = est.get("version") or "—"
        date_str = est["estimate_date"].strftime("%d %b %Y") if est.get("estimate_date") else "—"
        mode     = est.get("client_mode", "saas")
        db_type  = est.get("db_type", "PostgreSQL")
        monthly  = est.get("total_monthly_usd") or 0
        five_yr  = est.get("total_5year_usd") or 0
        mode_lbl = "SAAS" if mode == "saas" else "ONPREM"
        cost_str = f"${monthly:,.0f}/mo" if monthly else "Sizing only"
        annual   = monthly * 12 if monthly else 0
        f5_str   = f"${five_yr:,.0f} 5yr" if five_yr else ""

        row_l, row_r = st.columns([5, 3])
        with row_l:
            st.markdown(f"""
            <div class="bn-estimate-row">
              <div class="bn-est-ver">v{version}</div>
              <div class="bn-est-info">
                <div class="bn-est-name">{date_str} · {db_type}</div>
                <div class="bn-est-meta">
                  <span class="bn-tag {mode}">{mode_lbl}</span>
                  {cost_str}{' · ' + f5_str if f5_str else ''}
                </div>
              </div>
              <div class="bn-est-cost">{('$'+f'{annual/1000:.0f}K/yr') if annual else 'Sizing only'}</div>
            </div>
            """, unsafe_allow_html=True)

        with row_r:
            st.markdown("<div style='padding-top:0.6rem'></div>", unsafe_allow_html=True)
            a, b, c, d = st.columns([2, 1, 1, 1])

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

    st.markdown('</div></div>', unsafe_allow_html=True)