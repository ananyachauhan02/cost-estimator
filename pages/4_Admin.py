"""
pages/4_Admin.py — User management panel for RBAC
"""
import streamlit as st
import pandas as pd
from database import get_all_users, create_user, update_user, delete_user, reset_user_password
from rbac import require
from theme import inject_theme, section_title

# ── Auth & Role Guard ─────────────────────────────────────────────────────
require("manage_users", "Only Administrators can access the Admin Panel.")

# ── Theme Setup ───────────────────────────────────────────────────────────
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
  .page-title { font-family: 'Plus Jakarta Sans', sans-serif; font-size: 1.75rem; font-weight: 800; color: var(--text); letter-spacing: -0.025em; }
  .page-subtitle { color: var(--text2); font-size: 0.85rem; margin-top: 0.25rem; }

  /* ── Admin table rows ── */
  [data-testid="stHorizontalBlock"] {
    border-bottom: 1px solid var(--border);
    padding: 0.25rem 0;
  }

  /* ── Form panel ── */
  [data-testid="stVerticalBlock"] > [data-testid="stVerticalBlock"] {
    background: var(--surface);
    border: 1.5px solid var(--border);
    border-top: 3px solid var(--accent2);
    border-radius: 14px;
    padding: 1.5rem !important;
    box-shadow: 0 2px 12px rgba(0,0,0,0.07);
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

inject_theme()

st.markdown("""
<div class="page-header">
    <div class="page-title">⚙️ Admin Panel</div>
    <div class="page-subtitle">Manage users and role-based access control</div>
</div>
""", unsafe_allow_html=True)

# ── Header Nav ────────────────────────────────────────────────────────────
nav_col1, nav_col2, nav_col3 = st.columns([1,1,6])
with nav_col1:
    if st.button("← Back to Clients", use_container_width=True):
        st.switch_page("pages/1_Clients.py")
with nav_col2:
    if st.button("⏏ Logout", use_container_width=True):
        st.session_state.clear()
        st.rerun()

st.markdown("<br>", unsafe_allow_html=True)

# ── Data Fetch ────────────────────────────────────────────────────────────
users = get_all_users()

# ── Layout ────────────────────────────────────────────────────────────────
col_list, col_form = st.columns([2, 1], gap="large")

with col_list:
    section_title("👥", "User Management")
    if not users:
        st.info("No users found.")
    else:
        # ── Table Header ──
        h_id, h_name, h_email, h_role, h_joined, h_action = st.columns([0.5, 1.5, 2, 1, 1.5, 1])
        h_id.markdown("**ID**")
        h_name.markdown("**Name**")
        h_email.markdown("**Email**")
        h_role.markdown("**Role**")
        h_joined.markdown("**Joined**")
        h_action.markdown("**Actions**")
        st.markdown("<hr style='margin: 0.5rem 0; border-color: var(--border);'>", unsafe_allow_html=True)

        # ── Table Rows ──
        for u in users:
            c_id, c_name, c_email, c_role, c_joined, c_action = st.columns([0.5, 1.5, 2, 1, 1.5, 1])
            c_id.markdown(f"<div style='padding-top:0.5rem;'>{u['id']}</div>", unsafe_allow_html=True)
            c_name.markdown(f"<div style='padding-top:0.5rem;'>{u['name'] or '<i>N/A</i>'}</div>", unsafe_allow_html=True)
            c_email.markdown(f"<div style='padding-top:0.5rem;'>{u['email']}</div>", unsafe_allow_html=True)
            
            # Role color coding
            role_colors = {"admin": "var(--error)", "estimator": "var(--accent)", "viewer": "var(--success)"}
            r_col = role_colors.get(u['role'], "var(--text)")
            c_role.markdown(f"<div style='padding-top:0.5rem; color:{r_col}; font-weight:600;'>{u['role'].capitalize()}</div>", unsafe_allow_html=True)
            
            joined_str = pd.to_datetime(u['created_at']).strftime('%d %b %Y')
            c_joined.markdown(f"<div style='padding-top:0.5rem;'>{joined_str}</div>", unsafe_allow_html=True)
            
            # Action Toggle
            with c_action:
                with st.popover("⚙️ Manage", use_container_width=True):
                    st.markdown(f"**Manage: {u['email']}**")
                    
                    # 1. Update Role
                    new_role = st.selectbox("Assign Role", ["viewer", "estimator", "admin"], 
                                         index=["viewer", "estimator", "admin"].index(u["role"]),
                                         key=f"role_{u['id']}")
                    if st.button("Update Role", key=f"btn_role_{u['id']}", use_container_width=True, type="primary"):
                        if update_user(u['id'], new_role, u["name"]):
                            st.success("Role updated!")
                            st.rerun()
                            
                    st.divider()
                    
                    # 2. Reset Password
                    new_pass = st.text_input("New Password", type="password", key=f"pass_{u['id']}")
                    if st.button("Reset Password", key=f"btn_pass_{u['id']}", use_container_width=True):
                        if not new_pass.strip():
                            st.error("Please enter a new password.")
                        elif reset_user_password(u['id'], new_pass.strip()):
                            st.success("Password reset!")
                        else:
                            st.error("Failed to reset password.")
                            
                    st.divider()
                    
                    # 3. Delete
                    if st.button("🗑️ Delete User", key=f"btn_del_{u['id']}", use_container_width=True):
                        if u["email"] == st.session_state.user["email"]:
                            st.error("Cannot delete yourself.")
                        elif delete_user(u['id']):
                            st.success("User deleted.")
                            st.rerun()
                        else:
                            st.error("Failed to delete.")
            st.markdown("<hr style='margin: 0.25rem 0; border-color: var(--border); opacity: 0.3;'>", unsafe_allow_html=True)

with col_form:
    st.markdown("<h4 style='color: var(--text); font-family: \"Plus Jakarta Sans\", sans-serif;'>➕ Create New User</h4>", unsafe_allow_html=True)
    
    with st.form("create_user_form"):
        new_name  = st.text_input("Full Name")
        new_email = st.text_input("Email Address")
        new_pass  = st.text_input("Password", type="password")
        new_role  = st.selectbox("Assign Role", ["viewer", "estimator", "admin"])
        
        submit = st.form_submit_button("Create User", type="primary", use_container_width=True)
        
        if submit:
            if not new_email or not new_pass:
                st.error("Email and password are required.")
            else:
                try:
                    create_user(new_email.strip(), new_pass.strip(), new_name.strip(), new_role)
                    st.success(f"User {new_email} created successfully!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error creating user: {e}")
    
    # Show role definition legend
    st.markdown("""
    <div style="font-size: 0.8rem; color: var(--text2); background: var(--surface); padding: 1.25rem; border-radius: 10px; border: 1px solid var(--border); margin-top: 1rem;">
    <strong style="color:var(--text)">Role Legend:</strong><br>
    <div style="margin-top:8px;">
      <span style="color:var(--error)">Admin</span>: Full access. Create, edit, delete anything.<br>
      <span style="color:var(--accent)">Estimator</span>: Can create clients and estimates, but cannot delete.<br>
      <span style="color:var(--success)">Viewer</span>: Read-only access to estimates and dashboard.
    </div>
    </div>
    """, unsafe_allow_html=True)