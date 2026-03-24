"""
app.py — BusinessNext Cost Estimator · Login Page
"""
import streamlit as st
from database import init_db, verify_user

init_db()

st.set_page_config(
    page_title="BusinessNext | Cost Estimator",
    layout="wide",
    page_icon="☁️",
    initial_sidebar_state="auto",
)

# ── Global styles ─────────────────────────────────────────────────────────
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@500;600;700;800&family=Inter:wght@400;500;600&display=swap');

  html, body, [data-testid="stAppViewContainer"] {
    font-family: 'Inter', sans-serif;
    background-color: var(--bg) !important;
  }

  /* ── Login page: lock to viewport, no scrollbar ── */
  .login-outer {
    position: fixed;
    inset: 0;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    background-color: var(--bg);
    pointer-events: none; /* let Streamlit inputs receive events */
  }
  .login-logo {
    font-family: 'Plus Jakarta Sans', sans-serif;
    font-size: 2.2rem;
    font-weight: 800;
    letter-spacing: -0.03em;
    background: linear-gradient(135deg, #60a5fa 0%, #4f8ef7 40%, #00d4aa 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    text-align: center;
    margin-bottom: 0.3rem;
    filter: drop-shadow(0 0 16px rgba(79,142,247,0.25));
  }
  .login-sub {
    color: var(--text2);
    font-size: 0.88rem;
    text-align: center;
    margin-bottom: 2.5rem;
  }

  /* Input fields */
  .stTextInput > label {
    color: var(--text2) !important;
    font-size: 0.82rem !important;
    font-weight: 500 !important;
  }
  .stTextInput input {
    background: var(--surface2) !important;
    border: 1px solid var(--border) !important;
    border-radius: 10px !important;
    color: var(--text) !important;
    padding: 0.65rem 1rem !important;
  }
  .stTextInput input:focus {
    border-color: #4f8ef7 !important;
    box-shadow: 0 0 0 3px rgba(79,142,247,0.15) !important;
  }

  /* Sign-In button */
  div.stButton > button {
    width: 100% !important;
    background: linear-gradient(135deg, #4f8ef7, #3b7de8) !important;
    color: white !important;
    font-weight: 600 !important;
    font-size: 0.95rem !important;
    border: none !important;
    border-radius: 10px !important;
    padding: 0.7rem 1.5rem !important;
    margin-top: 0.5rem !important;
    transition: all 0.2s ease !important;
    cursor: pointer !important;
  }
  div.stButton > button:hover {
    background: linear-gradient(135deg, #3b7de8, #2d6dd4) !important;
    transform: translateY(-1px) !important;
    box-shadow: 0 8px 24px rgba(79,142,247,0.3) !important;
  }
</style>
""", unsafe_allow_html=True)


def login_ui():
    # Narrow centred column for all content
    _, col, _ = st.columns([1.8, 2, 1.8])
    with col:
        # Push everything down to roughly centre on screen
        st.markdown("<div style='height: 15vh'></div>", unsafe_allow_html=True)

        # Branding header
        st.markdown("""
        <div style="text-align:center; margin-bottom: 1.75rem;">
          <div style="font-family:'Plus Jakarta Sans',sans-serif; font-size:2.2rem; font-weight:800;
                      letter-spacing:-0.03em;
                      background:linear-gradient(135deg,#60a5fa,#4f8ef7 40%,#00d4aa);
                      -webkit-background-clip:text; -webkit-text-fill-color:transparent;
                      filter:drop-shadow(0 0 16px rgba(79,142,247,0.25));">
            ☁️ BusinessNext
          </div>
          <div style="color:var(--text2); font-size:0.88rem; margin-top:0.2rem; font-family:'Inter',sans-serif;">
            Cloud Cost Estimator Platform
          </div>
        </div>
        """, unsafe_allow_html=True)

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

pg.run()