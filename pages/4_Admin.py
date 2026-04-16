"""
pages/4_Admin.py — User management panel matching businessnext_ui.html
"""
import streamlit as st
import pandas as pd
from database import get_all_users, create_user, update_user, delete_user, reset_user_password
from rbac import require
from theme import inject_theme, section_title

# ── Auth & Role Guard ─────────────────────────────────────────────────────
require("manage_users", "Only Administrators can access the Admin Panel.")

inject_theme()

# ── Admin-specific CSS ────────────────────────────────────────────────────
st.markdown("""
<style>

/* ── Popover trigger button — single line, no wrapping ───────────────────── */
[data-testid="stPopover"] {
  width: 100% !important;
}
[data-testid="stPopover"] > button {
  width: 100% !important;
  white-space: nowrap !important;
  overflow: hidden !important;
  text-overflow: ellipsis !important;
  background: var(--bg3) !important;
  border: 1px solid var(--border2) !important;
  color: var(--text2) !important;
  border-radius: 7px !important;
  font-size: 11px !important;
  font-weight: 600 !important;
  padding: 0 10px !important;
  height: 28px !important;
  min-height: 28px !important;
  max-height: 28px !important;
  line-height: 28px !important;
  display: flex !important;
  align-items: center !important;
  justify-content: center !important;
  gap: 4px !important;
  font-family: var(--ff) !important;
  letter-spacing: 0.01em !important;
  transition: all 0.18s ease !important;
  box-sizing: border-box !important;
}
[data-testid="stPopover"] > button:hover {
  background: var(--accent-lt) !important;
  border-color: var(--accent) !important;
  color: var(--accent) !important;
}
/* Kill any child spans that might cause wrapping */
[data-testid="stPopover"] > button > span,
[data-testid="stPopover"] > button > div {
  white-space: nowrap !important;
  overflow: hidden !important;
  text-overflow: ellipsis !important;
  line-height: 1 !important;
}

/* ── Popover body ─────────────────────────────────────────────────────────── */
[data-testid="stPopoverBody"] {
  background: var(--bg2) !important;
  border: 1px solid var(--border2) !important;
  border-radius: 12px !important;
  box-shadow: 0 12px 40px rgba(0,0,0,0.14), 0 2px 8px rgba(0,0,0,0.08) !important;
  padding: 14px !important;
  min-width: 260px !important;
  max-width: 300px !important;
}

/* ── All text inside popover ─────────────────────────────────────────────── */
[data-testid="stPopoverBody"] p,
[data-testid="stPopoverBody"] label,
[data-testid="stPopoverBody"] span,
[data-testid="stPopoverBody"] div {
  font-family: var(--ff) !important;
  color: var(--text) !important;
}

/* ── Selectbox inside popover ────────────────────────────────────────────── */
[data-testid="stPopoverBody"] [data-testid="stSelectbox"] {
  margin-bottom: 8px !important;
}
[data-testid="stPopoverBody"] [data-testid="stSelectbox"] > div > div {
  background: var(--bg3) !important;
  border: 1px solid var(--border2) !important;
  border-radius: 8px !important;
  min-height: 36px !important;
  font-size: 12px !important;
  font-family: var(--ff) !important;
  color: var(--text) !important;
  padding: 0 10px !important;
}
[data-testid="stPopoverBody"] [data-testid="stSelectbox"] > div > div:hover {
  border-color: var(--accent) !important;
}
/* Hide the SVG chart icon that Streamlit sometimes inserts */
[data-testid="stPopoverBody"] [data-testid="stSelectbox"] svg:not([data-testid="stIconMaterial"]) {
  display: none !important;
}
[data-testid="stPopoverBody"] [data-testid="stSelectbox"] [data-testid="stIconMaterial"] {
  display: none !important;
}

/* ── Dropdown list ────────────────────────────────────────────────────────── */
[data-baseweb="popover"] [role="listbox"],
[role="listbox"] {
  background: var(--bg2) !important;
  border: 1px solid var(--border2) !important;
  border-radius: 10px !important;
  box-shadow: 0 8px 24px rgba(0,0,0,0.12) !important;
  padding: 4px !important;
  overflow: hidden !important;
}
[role="option"] {
  background: transparent !important;
  color: var(--text2) !important;
  font-size: 12px !important;
  font-family: var(--ff) !important;
  border-radius: 6px !important;
  padding: 7px 10px !important;
  margin: 1px 0 !important;
  transition: background 0.15s !important;
  cursor: pointer !important;
}
[role="option"]:hover {
  background: var(--accent-lt) !important;
  color: var(--accent) !important;
}
[aria-selected="true"][role="option"] {
  background: var(--accent-lt) !important;
  color: var(--accent) !important;
  font-weight: 600 !important;
}

/* ── Password input inside popover ───────────────────────────────────────── */
[data-testid="stPopoverBody"] [data-testid="stTextInput"] {
  margin-bottom: 8px !important;
}
[data-testid="stPopoverBody"] [data-testid="stTextInput"] input {
  background: var(--bg3) !important;
  border: 1px solid var(--border2) !important;
  border-radius: 8px !important;
  font-size: 12px !important;
  color: var(--text) !important;
  font-family: var(--fm) !important;
  padding: 8px 10px !important;
  height: 36px !important;
  width: 100% !important;
}
[data-testid="stPopoverBody"] [data-testid="stTextInput"] input:focus {
  border-color: var(--accent) !important;
  box-shadow: 0 0 0 3px rgba(79,110,247,.12) !important;
  outline: none !important;
}

/* ── Buttons inside popover ──────────────────────────────────────────────── */
[data-testid="stPopoverBody"] .stButton {
  margin-bottom: 4px !important;
}
[data-testid="stPopoverBody"] .stButton > button {
  width: 100% !important;
  border-radius: 7px !important;
  font-size: 11px !important;
  font-weight: 600 !important;
  height: 32px !important;
  min-height: 32px !important;
  padding: 0 12px !important;
  font-family: var(--ff) !important;
  transition: all 0.18s !important;
  cursor: pointer !important;
}
[data-testid="stPopoverBody"] .stButton > button[kind="primary"] {
  background: var(--accent) !important;
  color: #fff !important;
  border: none !important;
  box-shadow: 0 2px 6px rgba(79,110,247,0.28) !important;
}
[data-testid="stPopoverBody"] .stButton > button[kind="primary"]:hover {
  background: #3d5ce5 !important;
  box-shadow: 0 4px 14px rgba(79,110,247,0.38) !important;
  transform: translateY(-1px) !important;
}
[data-testid="stPopoverBody"] .stButton > button[kind="secondary"],
[data-testid="stPopoverBody"] .stButton > button:not([kind="primary"]) {
  background: var(--bg3) !important;
  color: var(--text2) !important;
  border: 1px solid var(--border2) !important;
}
[data-testid="stPopoverBody"] .stButton > button[kind="secondary"]:hover,
[data-testid="stPopoverBody"] .stButton > button:not([kind="primary"]):hover {
  background: var(--bg2) !important;
  border-color: var(--border2) !important;
  color: var(--text) !important;
}

/* ── Divider ─────────────────────────────────────────────────────────────── */
[data-testid="stPopoverBody"] hr {
  border: none !important;
  border-top: 1px solid var(--border) !important;
  margin: 10px 0 !important;
}

/* ── Alert messages ──────────────────────────────────────────────────────── */
[data-testid="stPopoverBody"] [data-testid="stAlert"] {
  border-radius: 8px !important;
  font-size: 11px !important;
  padding: 7px 10px !important;
  margin-top: 4px !important;
}
</style>
""", unsafe_allow_html=True)

# ── Page header ───────────────────────────────────────────────────────────
hdr_l, hdr_r = st.columns([5, 1])
with hdr_l:
    st.markdown("""
    <div class="bn-page-header">
      <div>
        <div class="bn-page-title">Admin Panel</div>
        <div class="bn-page-subtitle">Manage users and role-based access control</div>
      </div>
    </div>
    """, unsafe_allow_html=True)
with hdr_r:
    st.markdown("<div style='padding-top:1.5rem'></div>", unsafe_allow_html=True)
    c1, c2 = st.columns([1, 1])
    with c1:
        if st.button("Logout", key="logout_admin_top", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.user = None
            st.rerun()
    with c2:
        if st.button("← Clients", key="admin_back_to_clients", use_container_width=True):
            st.switch_page("pages/1_Clients.py")

# ── Data fetch ────────────────────────────────────────────────────────────
users = get_all_users()

# ── Layout ────────────────────────────────────────────────────────────────
col_list, col_form = st.columns([2, 1], gap="large")

with col_list:
    st.markdown(f"""
    <div class="bn-panel">
      <div class="bn-panel-header">
        <span class="bn-dot accent"></span>
        <span class="bn-panel-title">Users</span>
        <span class="bn-badge accent">{len(users)} users</span>
      </div>
    </div>
    """, unsafe_allow_html=True)

    if not users:
        st.markdown("""
        <div class="bn-panel"><div class="bn-panel-body">
          <div class="bn-empty-state">
            <div class="bn-empty-icon">👥</div>
            <div class="bn-empty-title">No users found</div>
          </div>
        </div></div>
        """, unsafe_allow_html=True)
    else:
        # ── Column headers ─────────────────────────────────────────────
        h_cols = st.columns([1.6, 2.4, 0.9, 1.4, 0.9])
        for col, label in zip(h_cols, ["Name", "Email", "Role", "Joined", "Actions"]):
            col.markdown(
                f"<div style='font-size:10px;font-weight:700;text-transform:uppercase;"
                f"letter-spacing:.6px;color:var(--text3);padding:8px 0;'>{label}</div>",
                unsafe_allow_html=True
            )
        st.markdown("<hr style='margin:0 0 4px 0;border-color:var(--border);'>", unsafe_allow_html=True)

        # ── User rows ──────────────────────────────────────────────────
        for u in users:
            role_cls = ("danger" if u['role'] == "admin"
                        else "accent" if u['role'] == "estimator"
                        else "success")
            joined_str = pd.to_datetime(u['created_at']).strftime('%d %b %Y')

            row = st.columns([1.6, 2.4, 0.9, 1.4, 0.9])

            row[0].markdown(
                f"<div style='padding:.45rem 0;font-size:12px;font-weight:600;"
                f"color:var(--text);'>{u['name'] or '—'}</div>",
                unsafe_allow_html=True
            )
            row[1].markdown(
                f"<div style='padding:.45rem 0;font-size:11px;font-family:var(--fm);"
                f"color:var(--text2);word-break:break-all;'>{u['email']}</div>",
                unsafe_allow_html=True
            )
            row[2].markdown(
                f"<div style='padding:.45rem 0;'>"
                f"<span class='bn-badge {role_cls}'>{u['role']}</span></div>",
                unsafe_allow_html=True
            )
            row[3].markdown(
                f"<div style='padding:.45rem 0;font-size:11px;color:var(--text3);"
                f"font-family:var(--fm);'>{joined_str}</div>",
                unsafe_allow_html=True
            )

            with row[4]:
                with st.popover("Manage", use_container_width=True):

                    # User email header
                    st.markdown(f"""
                    <div style="margin-bottom:12px;padding-bottom:10px;
                                border-bottom:1px solid var(--border);">
                      <div style="font-size:9px;font-weight:700;text-transform:uppercase;
                                  letter-spacing:.5px;color:var(--text3);
                                  margin-bottom:3px;">User</div>
                      <div style="font-size:11px;font-weight:600;color:var(--text);
                                  font-family:var(--fm);word-break:break-all;
                                  line-height:1.4;">{u['email']}</div>
                    </div>
                    """, unsafe_allow_html=True)

                    # ── Role ──────────────────────────────────────────
                    st.markdown("""<div style="font-size:9px;font-weight:700;
                        text-transform:uppercase;letter-spacing:.5px;color:var(--text3);
                        margin-bottom:5px;">Assign Role</div>""",
                        unsafe_allow_html=True)

                    new_role = st.selectbox(
                        "role",
                        options=["viewer", "estimator", "admin"],
                        index=["viewer", "estimator", "admin"].index(u["role"]),
                        key=f"role_{u['id']}",
                        label_visibility="collapsed",
                    )

                    if st.button("Update Role", key=f"btn_role_{u['id']}",
                                 use_container_width=True, type="primary"):
                        if update_user(u['id'], new_role, u["name"]):
                            st.success("Role updated!")
                            st.rerun()

                    st.divider()

                    # ── Password ──────────────────────────────────────
                    st.markdown("""<div style="font-size:9px;font-weight:700;
                        text-transform:uppercase;letter-spacing:.5px;color:var(--text3);
                        margin-bottom:5px;">Reset Password</div>""",
                        unsafe_allow_html=True)

                    new_pass = st.text_input(
                        "pw",
                        type="password",
                        placeholder="New password…",
                        key=f"pass_{u['id']}",
                        label_visibility="collapsed",
                    )

                    if st.button("Reset Password", key=f"btn_pass_{u['id']}",
                                 use_container_width=True):
                        if not new_pass.strip():
                            st.error("Enter a new password.")
                        elif reset_user_password(u['id'], new_pass.strip()):
                            st.success("Password reset!")
                        else:
                            st.error("Failed.")

                    st.divider()

                    # ── Delete ────────────────────────────────────────
                    st.markdown("""
                    <style>
                    /* Target the delete button specifically via its position */
                    [data-testid="stPopoverBody"] .stButton:last-child > button {
                      background: rgba(220,38,38,0.08) !important;
                      color: var(--danger) !important;
                      border: 1px solid rgba(220,38,38,0.2) !important;
                    }
                    [data-testid="stPopoverBody"] .stButton:last-child > button:hover {
                      background: var(--danger) !important;
                      color: #fff !important;
                      border-color: var(--danger) !important;
                    }
                    </style>
                    """, unsafe_allow_html=True)

                    if st.button("🗑 Delete User", key=f"btn_del_{u['id']}",
                                 use_container_width=True):
                        if u["email"] == st.session_state.user["email"]:
                            st.error("Cannot delete yourself.")
                        elif delete_user(u['id']):
                            st.success("Deleted.")
                            st.rerun()
                        else:
                            st.error("Failed.")

with col_form:
    st.markdown("""
    <div class="bn-panel">
      <div class="bn-panel-header">
        <span class="bn-dot success"></span>
        <span class="bn-panel-title">Create New User</span>
      </div>
    </div>
    """, unsafe_allow_html=True)

    with st.form("create_user_form"):
        new_name  = st.text_input("Full Name", placeholder="Jane Smith")
        new_email = st.text_input("Email Address", placeholder="jane@bank.com")
        new_pass  = st.text_input("Password", type="password", placeholder="••••••••")
        new_role  = st.selectbox(
            "Role",
            ["viewer", "estimator", "admin"],
            format_func=lambda r: {
                "viewer":    "Viewer — Read only",
                "estimator": "Estimator — Create estimates",
                "admin":     "Admin — Full access",
            }[r]
        )
        if st.form_submit_button("Create User →", type="primary", use_container_width=True):
            if not new_email or not new_pass:
                st.error("Email and password are required.")
            else:
                try:
                    create_user(new_email.strip(), new_pass.strip(), new_name.strip(), new_role)
                    st.success(f"User {new_email} created!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")

    st.markdown("""
    <div class="bn-panel">
      <div class="bn-panel-body" style="padding:14px 16px;">
        <div class="bn-section-label">Role Permissions</div>
        <div style="font-size:11px;color:var(--text2);line-height:2.2;">
          <span class="bn-badge danger">Admin</span>&nbsp;
          Full access · Create, edit, delete<br>
          <span class="bn-badge accent">Estimator</span>&nbsp;
          Create clients and estimates<br>
          <span class="bn-badge success">Viewer</span>&nbsp;
          Read-only access to all estimates
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)