"""
pages/1_Clients.py — Client Dashboard matching businessnext_ui.html
"""
import streamlit as st
from database import get_all_clients, create_client, delete_client
from rbac import can
from theme import inject_theme

# Config handled by app.py
inject_theme()

# Compact button overrides for client card action buttons
st.markdown("""
<style>
/* Client card action buttons — compact size */
div[data-testid="stVerticalBlock"] > div[data-testid="stHorizontalBlock"]:has(> div[data-testid="stColumn"] button) button[kind="primary"],
div[data-testid="stVerticalBlock"] > div[data-testid="stHorizontalBlock"]:has(> div[data-testid="stColumn"] button) button[kind="secondary"] {
  padding: 4px 6px !important;
  font-size: 11px !important;
  border-radius: 6px !important;
  min-height: 26px !important;
  height: 26px !important;
  line-height: 1 !important;
  font-weight: 600 !important;
}
/* Narrow all buttons inside the cards grid */
.stButton > button {
  padding: 5px 10px !important;
  font-size: 11.5px !important;
  min-height: 30px !important;
  height: 30px !important;
  border-radius: 7px !important;
}
/* Keep primary accent buttons normal */
.stButton > button[data-testid="stBaseButton-primary"] {
  background: var(--accent) !important;
  color: #fff !important;
}
</style>
""", unsafe_allow_html=True)


def handle_delete_client(client_id, client_name):
    try:
        delete_client(client_id)
        st.session_state["delete_success"] = f"Client '{client_name}' deleted successfully!"
        if st.session_state.get("selected_client", {}).get("id") == client_id:
            st.session_state.selected_client = None
    except Exception as e:
        st.session_state["delete_error"] = f"Error deleting client: {e}"


# ── Page header ─────────────────────────────────────────────────────────────
title_col, actions_col = st.columns([3, 1])
with title_col:
    user_role = st.session_state.user.get("role", "viewer")
    role_colors = {"admin": ("#fef2f2", "#dc2626"), "estimator": ("#eff6ff", "#2563eb"), "viewer": ("#f0fdf4", "#16a34a")}
    bg, fg = role_colors.get(user_role, ("#f3f4f6", "#374151"))
    st.markdown(f"""
    <div class="bn-page-header">
      <div>
        <div class="bn-page-title" style="display:flex;align-items:center;gap:10px;">
          Clients
          <span style="font-size:12px;font-weight:600;padding:3px 10px;border-radius:20px;
                       background:{bg};color:{fg};vertical-align:middle;">{user_role}</span>
        </div>
        <div class="bn-page-subtitle">Manage client accounts and their cost estimates</div>
      </div>
    </div>
    """, unsafe_allow_html=True)
with actions_col:
    st.markdown("<div style='padding-top:1.5rem'></div>", unsafe_allow_html=True)
    c1, c2 = st.columns([1, 1])
    with c1:
        if st.button("Logout", key="logout_clients_top", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.user = None
            st.rerun()
    with c2:
        if can("create_client"):
            if st.button("+ New", key="show_add_form_top", use_container_width=True, type="primary"):
                st.session_state["show_add_client_form"] = True
                st.rerun()

# ── Messages ─────────────────────────────────────────────────────────────────
if "delete_success" in st.session_state:
    msg = st.session_state.pop("delete_success")
    st.markdown(f"""
    <div class="bn-alert-banner success">
      <span style="font-size:16px">✓</span>
      <span style="font-size:12px;font-weight:500">{msg}</span>
    </div>
    """, unsafe_allow_html=True)
if "delete_error" in st.session_state:
    msg = st.session_state.pop("delete_error")
    st.markdown(f"""
    <div class="bn-alert-banner warn">
      <span style="font-size:16px">⚠</span>
      <span style="font-size:12px;font-weight:500">{msg}</span>
    </div>
    """, unsafe_allow_html=True)

# ── Load clients ──────────────────────────────────────────────────────────────
try:
    clients = get_all_clients()
except Exception as e:
    st.error(f"Database error: {e}")
    clients = []

# ── Metric cards ──────────────────────────────────────────────────────────────
total = len(clients)
with_est = sum(1 for c in clients if c.get("estimate_count", 0) > 0)

st.markdown(f"""
<div class="bn-metrics">
  <div class="bn-metric-card accent">
    <div class="bn-metric-label">Total Clients</div>
    <div class="bn-metric-value">{total}</div>
    <div class="bn-metric-delta flat">All registered clients</div>
  </div>
  <div class="bn-metric-card success">
    <div class="bn-metric-label">With Estimates</div>
    <div class="bn-metric-value">{with_est}</div>
    <div class="bn-metric-delta flat">{round(with_est/max(total,1)*100)}% of clients</div>
  </div>
  <div class="bn-metric-card warn">
    <div class="bn-metric-label">Without Estimates</div>
    <div class="bn-metric-value">{total - with_est}</div>
    <div class="bn-metric-delta flat">Pending first estimate</div>
  </div>
</div>
""", unsafe_allow_html=True)

# ── Add new client inline form ────────────────────────────────────────────────
if st.session_state.get("show_add_client_form"):
    st.markdown("""
    <div class="bn-panel" style="border-color:var(--accent);animation:slideDown .3s ease both">
      <div class="bn-panel-header">
        <span class="bn-dot accent"></span>
        <span class="bn-panel-title">Add New Client</span>
      </div>
    </div>
    """, unsafe_allow_html=True)

    with st.container():
        c1, c2, c3 = st.columns([3, 1, 1])
        new_name = c1.text_input("Client Name", placeholder="e.g. HDFC Bank", key="new_client_name",
                                  label_visibility="visible")
        with c2:
            st.markdown("<div style='padding-top:1.6rem'></div>", unsafe_allow_html=True)
            if st.button("Create Client →", key="btn_add_client", type="primary", use_container_width=True):
                if new_name.strip():
                    try:
                        new_cid = create_client(new_name.strip(), "Banking")
                        st.session_state["show_add_client_form"] = False
                        st.session_state.selected_client = {
                            "id": new_cid, "name": new_name.strip(), "sector": "Banking"
                        }
                        st.session_state.load_estimate = None
                        for k in ["last_metrics","last_distribution","last_pricing",
                                  "env_pricing","gcp_pricing","comparison",
                                  "cloud_sizing_xlsx","cloud_pricing_xlsx","gcp_pricing_xlsx",
                                  "pdf_report_path","last_saved_id","client_mode",
                                  "show_summary","summary_df","show_success"]:
                            st.session_state[k] = None if k not in ["show_summary","show_success"] else False
                        st.switch_page("pages/3_Estimator.py")
                    except Exception as e:
                        st.error(f"Failed to add client: {e}")
                else:
                    st.warning("Please enter a client name.")
        with c3:
            st.markdown("<div style='padding-top:1.6rem'></div>", unsafe_allow_html=True)
            if st.button("✕ Cancel", key="btn_cancel_add", use_container_width=True):
                st.session_state["show_add_client_form"] = False
                st.rerun()

st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)

# ── Client grid ───────────────────────────────────────────────────────────────
SECTOR_ICONS = {
    "Banking": "🏦", "Insurance": "🛡️", "Finance": "💳",
    "Retail": "🛒", "Healthcare": "🏥", "Telecom": "📡", "Default": "🏢",
}
CARD_COLORS = ["accent", "success", "warn", "accent", "purple", "info"]

if not clients:
    st.markdown("""
    <div class="bn-panel">
      <div class="bn-panel-body">
        <div class="bn-empty-state">
          <div class="bn-empty-icon">◫</div>
          <div class="bn-empty-title">No clients yet</div>
          <div class="bn-empty-sub">Click "+ New Client" above to add your first client.</div>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)
else:
    COLS = 3
    for row_start in range(0, len(clients), COLS):
        row_items = clients[row_start: row_start + COLS]
        cols = st.columns(COLS, gap="medium")

        for col_idx, item in enumerate(row_items):
            with cols[col_idx]:
                cid      = item["id"]
                cname    = item["name"]
                sector   = item.get("sector", "Default")
                icon     = SECTOR_ICONS.get(sector, SECTOR_ICONS["Default"])
                count    = item.get("estimate_count", 0)
                last     = item.get("last_estimate")
                last_str = last.strftime("%d %b %Y") if last else "—"
                color    = CARD_COLORS[(row_start + col_idx) % len(CARD_COLORS)]
                badge_cls = "success" if count > 0 else "info"

                # Card HTML
                st.markdown(f"""
                <div class="bn-client-card {color}">
                  <div class="bn-client-card-top">
                    <div class="bn-client-icon">{icon}</div>
                    <span class="bn-badge {badge_cls}">{count} est.</span>
                  </div>
                  <div class="bn-client-name">{cname}</div>
                  <div class="bn-client-sector">{sector}</div>
                  <div class="bn-client-meta">
                    <div class="bn-client-meta-item">
                      Last: <span class="bn-client-meta-val">{last_str}</span>
                    </div>
                  </div>
                </div>
                """, unsafe_allow_html=True)

                # Spacing between card and buttons
                st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

                # Action buttons
                b1, b2, b3 = st.columns(3)

                btn_new = False
                if can("create_estimate"):
                    btn_new = b1.button("+ Estimate", key=f"new_{cid}", use_container_width=True, type="primary")
                else:
                    b1.markdown("<div></div>", unsafe_allow_html=True)

                btn_hist = b2.button("History", key=f"hist_{cid}", use_container_width=True)

                btn_delete = False
                if can("delete_client"):
                    btn_delete = b3.button("Delete", key=f"del_{cid}", use_container_width=True,
                                           on_click=handle_delete_client, args=(cid, cname))

                if btn_new:
                    st.session_state.selected_client = item
                    st.session_state.load_estimate = None
                    for k in ["last_metrics","last_distribution","last_pricing",
                              "env_pricing","gcp_pricing","comparison",
                              "cloud_sizing_xlsx","cloud_pricing_xlsx","gcp_pricing_xlsx",
                              "pdf_report_path","last_saved_id","client_mode",
                              "show_summary","summary_df","show_success"]:
                        st.session_state[k] = None if k not in ["show_summary","show_success"] else False
                    st.switch_page("pages/3_Estimator.py")

                if btn_hist:
                    st.session_state.selected_client = item
                    st.switch_page("pages/2_Estimates.py")