"""
app.py — BusinessNext Cost Estimator · Login Page
"""
import base64
import pathlib
import streamlit as st
from database import init_db, verify_user
from theme import inject_theme

init_db()

st.set_page_config(
    page_title="BusinessNext | Cost Estimator",
    layout="wide",
    page_icon="assets/favicon.png",
    initial_sidebar_state="expanded",
)

inject_theme()





def login_ui():
    # Load favicon as base64 for inline use
    _favicon_b64 = base64.b64encode(
        pathlib.Path("assets/favicon.png").read_bytes()
    ).decode()
    _logo_src = f"data:image/png;base64,{_favicon_b64}"

    # CSS to make the middle column look like a unified login card
    st.markdown("""
    <style>
    /* Hide sidebar on login */
    [data-testid="stSidebar"] { display: none !important; }
    [data-testid="stMain"] { margin-left: 0 !important; }

    /* Full page centering */
    [data-testid="stMainBlockContainer"],
    [data-testid="block-container"] {
        padding: 0 !important;
        max-width: 100% !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        min-height: 100vh !important;
    }
    /* Hide horizontal block wrapper padding */
    [data-testid="stHorizontalBlock"] {
        width: 100% !important;
        display: flex !important;
        justify-content: center !important;
        align-items: flex-start !important;
        gap: 0 !important;
        padding: 0 !important;
    }
    /* Hide the side spacer columns */
    [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:first-child,
    [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:last-child {
        display: none !important;
    }
    /* Style the middle column as the card */
    [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(2) {
        background: #ffffff !important;
        border: 1px solid rgba(15,23,42,.08) !important;
        border-radius: 16px !important;
        box-shadow: 0 20px 60px rgba(0,0,0,.10), 0 4px 16px rgba(0,0,0,.06) !important;
        padding: 36px 32px !important;
        width: 400px !important;
        max-width: 440px !important;
        min-width: 340px !important;
        flex: none !important;
        animation: fadeUp .5s ease both !important;
        margin-top: -6vh !important;
    }
    /* Override block child background */
    [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(2) *,
    [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(2) > div,
    [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(2) [data-testid="stVerticalBlock"] {
        background-color: transparent !important;
        background: transparent !important;
    }
    /* Button full width and margin */
    [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(2) .stButton { 
        width: 100% !important; 
        margin-top: 16px !important; 
    }
    [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(2) .stButton > button {
        width: 100% !important;
        padding: 9px 16px !important;
        font-size: 13px !important;
    }
    /* Hide 'Press Enter to apply' text overlay */
    [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(2) div[data-testid="InputInstructions"] {
        display: none !important;
    }
    /* Input styling */
    [data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(2) input {
        background: var(--bg3) !important;
        border: 1px solid var(--border2) !important;
        padding: 8px 12px !important;
    }
    </style>
    """, unsafe_allow_html=True)

    _, col, _ = st.columns([1, 1.4, 1])
    with col:
        # Logo + title block
        st.markdown(f"""
        <div style="margin-bottom:24px;">
          <div style="display:flex;align-items:center;gap:10px;margin-bottom:20px;">
            <img src="{_logo_src}" width="36" height="36"
                 style="border-radius:8px;object-fit:contain;flex-shrink:0;" />
            <div>
              <div class="bn-login-logo-text">BusinessNext</div>
              <div class="bn-login-logo-sub">Cloud Infra &amp; Sizing Estimator</div>
            </div>
          </div>
          <div class="bn-login-title">Welcome back</div>
          <div class="bn-login-sub">Sign in to continue to your workspace</div>
        </div>
        """, unsafe_allow_html=True)

        email    = st.text_input("Email address", placeholder="admin@businessnext.com", key="login_email")
        password = st.text_input("Password", placeholder="••••••••", type="password", key="login_pass")

        if st.button("Sign in →", key="btn_login", use_container_width=True, type="primary"):
            if not email.strip() or not password.strip():
                st.error("Please enter both email and password.", icon="⚠️")
            else:
                user = verify_user(email.strip(), password.strip())
                if user:
                    st.session_state.logged_in   = True
                    st.session_state.user        = user
                    st.session_state.client_mode = None
                    st.rerun()
                else:
                    st.error("Invalid email or password.", icon="🔒")



# ── Navigation ────────────────────────────────────────────────────────────
login_pg      = st.Page(login_ui,               title="Login",     icon="🔒")
clients_pg    = st.Page("pages/1_Clients.py",   title="Clients",   icon="🏢")
estimates_pg  = st.Page("pages/2_Estimates.py", title="Estimates", icon="📋")
estimator_pg  = st.Page("pages/3_Estimator.py", title="Estimator", icon="🧮")
admin_pg      = st.Page("pages/4_Admin.py",     title="Admin",     icon="⚙️")

if not st.session_state.get("logged_in"):
    pg = st.navigation([login_pg], position="hidden")
else:
    pages = [clients_pg, estimates_pg, estimator_pg]
    if st.session_state.user.get("role") == "admin":
        pages.append(admin_pg)
    pg = st.navigation(pages, position="sidebar")


# ── Sidebar logo ──────────────────────────────────────────────────────────
if st.session_state.get("logged_in"):
    st.logo("assets/logo_black.png")
    # Show signed-in user info in sidebar bottom
    user_email = st.session_state.user.get("email", "")
    user_role  = st.session_state.user.get("role", "viewer")
    role_color = {"admin": "var(--danger-lt)", "estimator": "var(--accent-lt)", "viewer": "var(--success-lt)"}
    role_text_color = {"admin": "var(--danger)", "estimator": "var(--accent)", "viewer": "var(--success)"}
    st.sidebar.markdown(f"""
    <div style="padding:12px;border-top:1px solid var(--border);margin-top:auto;">
      <div style="font-size:10px;color:var(--text3);margin-bottom:4px;font-weight:700;
                  text-transform:uppercase;letter-spacing:.4px;">Signed in as</div>
      <div style="font-size:11px;font-weight:600;color:var(--text);margin-bottom:4px;">{user_email}</div>
      <span style="font-size:10px;font-weight:700;padding:2px 8px;border-radius:20px;
                   background:{role_color.get(user_role,'var(--accent-lt)')};
                   color:{role_text_color.get(user_role,'var(--accent)')};
                   font-family:var(--fm);">{user_role}</span>
    </div>
    """, unsafe_allow_html=True)

    # ── Logout Button ────────────────────────────────────────────────────────
    if st.sidebar.button("Logout", key="logout_sidebar_btn", use_container_width=True):
        st.session_state.logged_in = False
        st.session_state.user = None
        st.rerun()



pg.run()