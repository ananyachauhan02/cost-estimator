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
inject_theme()
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@500;600;700;800&family=Inter:wght@400;500;600&display=swap');
  
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
    padding: 0.4rem 0;
  }
  /* Remove border from the header column block to avoid double lines at top */
  [data-testid="stHorizontalBlock"]:has(div[style*="font-weight:bold"]),
  [data-testid="stHorizontalBlock"]:has(b),
  [data-testid="stHorizontalBlock"]:has(strong) {
     border-bottom: 2px solid var(--border) !important;
  }

  /* ── Form panel ── */
  [data-testid="stVerticalBlock"] > [data-testid="stVerticalBlock"] {
    background: var(--surface);
    border: 1.5px solid var(--border);
    border-top: 3px solid var(--accent);
    border-radius: 14px;
    padding: 1.5rem !important;
    box-shadow: 0 4px 16px rgba(0,0,0,0.4);
  }

  /* ── Page content tweaks ── */
</style>
""", unsafe_allow_html=True)

# Theme globally injected in app.py

# ── Top Navigation ────────────────────────────────────────────────────────
_, back_col, logout_col = st.columns([8, 2, 2])
with back_col:
    if st.button("← Clients", key="admin_back_to_clients", use_container_width=True):
        st.switch_page("pages/1_Clients.py")
with logout_col:
    if st.button("Logout", key="admin_logout", use_container_width=True):
        st.session_state.logged_in = False
        st.rerun()

st.markdown("""
<div class="page-header" style="margin-top:-1.5rem;">
    <div class="page-title">⚙️ Admin Panel</div>
    <div class="page-subtitle">Manage users and role-based access control</div>
</div>
""", unsafe_allow_html=True)

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
            # Fixed redundant horizontal lines


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