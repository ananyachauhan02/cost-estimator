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

# ── Global styles ─────────────────────────────────────────────────────────
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@500;600;700;800&family=Inter:wght@400;500;600&display=swap');

  /* ── Premium Login Page Styles ── */
  html, body, [data-testid="stAppViewContainer"] {
    font-family: 'Inter', sans-serif;
    background-color: var(--bg) !important;
  }

  /* When on login page, inject radial gradients */
  [data-testid="stAppViewContainer"]:has(.login-title) {
      background: radial-gradient(circle at 15% 50%, rgba(79, 142, 247, 0.12), transparent 45%), 
                  radial-gradient(circle at 85% 30%, rgba(0, 212, 170, 0.08), transparent 45%),
                  var(--bg) !important;
  }
  
  /* Glassmorphic Login Card */
  div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"]:nth-child(2):has(.login-title) {
      background: rgba(21, 29, 53, 0.7) !important;
      backdrop-filter: blur(20px) !important;
      -webkit-backdrop-filter: blur(20px) !important;
      border: 1px solid rgba(79, 142, 247, 0.2) !important;
      border-right: 1px solid rgba(79, 142, 247, 0.1) !important;
      border-bottom: 1px solid rgba(79, 142, 247, 0.1) !important;
      border-radius: 28px !important;
      padding: 3.5rem 3rem !important;
      box-shadow: 0 16px 40px rgba(0, 0, 0, 0.5), inset 0 1px 0 0 rgba(255, 255, 255, 0.05) !important;
      margin-top: 10vh !important;
      transition: transform 0.3s ease, box-shadow 0.3s ease;
  }
  
  /* Make the logo look intentional if it has a white bg */
  div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"]:nth-child(2):has(.login-title) [data-testid="stImage"] img {
      border-radius: 12px;
      box-shadow: 0 4px 12px rgba(0,0,0,0.3);
  }

  .login-title {
      font-family: 'Plus Jakarta Sans', sans-serif;
      font-size: 2.1rem;
      font-weight: 800;
      text-align: center;
      background: linear-gradient(135deg, #ffffff 0%, #a2adcc 100%);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      margin-top: 1.5rem;
      margin-bottom: 0.25rem;
      letter-spacing: -0.02em;
  }
  
  .login-subtitle {
      color: var(--text2);
      text-align: center;
      font-size: 0.95rem;
      margin-bottom: 2.5rem;
  }

  /* Inputs */
  .stTextInput > label {
    color: var(--text2) !important;
    font-size: 0.85rem !important;
    font-weight: 500 !important;
    margin-bottom: 4px !important;
  }
  .stTextInput input {
      background: rgba(0, 0, 0, 0.25) !important;
      border: 1px solid rgba(255, 255, 255, 0.08) !important;
      color: white !important;
      border-radius: 12px !important;
      padding: 0.75rem 1rem !important;
      transition: all 0.3s ease;
  }
  .stTextInput input:focus {
      border-color: var(--accent) !important;
      box-shadow: 0 0 0 3px rgba(79, 142, 247, 0.2) !important;
      background: rgba(0, 0, 0, 0.4) !important;
  }

  /* Sign-In button */
  div.stButton > button {
      width: 100% !important;
      background: linear-gradient(135deg, #4f8ef7 0%, #2563eb 100%) !important;
      color: white !important;
      border-radius: 12px !important;
      padding: 0.75rem 2rem !important;
      font-family: 'Plus Jakarta Sans', sans-serif !important;
      font-weight: 700 !important;
      letter-spacing: 0.02em;
      font-size: 1rem !important;
      border: none !important;
      box-shadow: 0 4px 14px rgba(37, 99, 235, 0.3) !important;
      transition: all 0.3s ease !important;
      margin-top: 1.5rem !important;
      cursor: pointer !important;
  }
  div.stButton > button:hover {
      transform: translateY(-2px) !important;
      box-shadow: 0 8px 24px rgba(37, 99, 235, 0.45) !important;
      background: linear-gradient(135deg, #3b7de8 0%, #1d4ed8 100%) !important;
  }
</style>
""", unsafe_allow_html=True)


def login_ui():
    _, col, _ = st.columns([1.2, 1.25, 1.2])  # tighter middle column for a sleek card
    with col:
        # We center the logo nicely using sub-columns
        c1, c2, c3 = st.columns([1, 1.8, 1])
        with c2:
            st.image("assets/logo.png", use_container_width=True)
            
        st.markdown('<div class="login-title">BusinessNext Portal</div>', unsafe_allow_html=True)
        st.markdown('<div class="login-subtitle">Sign in to your cost estimator</div>', unsafe_allow_html=True)

        email    = st.text_input("Email address", placeholder="admin@businessnext.com", key="login_email")
        password = st.text_input("Password",      placeholder="••••••••",              type="password", key="login_pass")

        if st.button("Sign In →", key="btn_login"):
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
    nav_dict = {
        "Dashboard": [clients_pg],
        "Details":   [estimates_pg, estimator_pg],
    }
    
    if st.session_state.user.get("role") == "admin":
        nav_dict["Administration"] = [admin_pg]
    pg = st.navigation(nav_dict, position="sidebar")


# ── Sidebar logo — Native Streamlit Component ──────
if st.session_state.get("logged_in"):
    st.logo("assets/logo.png")
    st.markdown(
        """
        <style>
        [data-testid="stSidebarUserContent"] {
            display: none !important;
        }
        [data-testid="stSidebarNav"] {
            margin-top: 0 !important;
            padding-top: 0.5rem !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


pg.run()