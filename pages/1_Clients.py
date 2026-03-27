"""
pages/1_Clients.py — Client Dashboard with hover-overlay cards
"""
import streamlit as st
from database import get_all_clients, create_client, delete_client
from rbac import can, role_badge
from theme import inject_theme

inject_theme()

# Config handled by app.py


def handle_delete_client(client_id, client_name):
    try:
        delete_client(client_id)
        st.session_state["delete_success"] = f"Client '{client_name}' deleted successfully!"
        if st.session_state.get("selected_client", {}).get("id") == client_id:
            st.session_state.selected_client = None
    except Exception as e:
        st.session_state["delete_error"] = f"Error deleting client: {e}"


# ── CSS ───────────────────────────────────────────────────────────────────
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Syne:wght@600;800&family=Inter:wght@400;500;600&family=Plus+Jakarta+Sans:wght@500;600;700;800&display=swap');

  /* ── Top nav ── */
  .top-nav {
    display:flex; align-items:center; justify-content:space-between;
    padding:1rem 0 1.5rem; border-bottom:2px solid #fadde1; margin-bottom:2rem;
  }
  .top-nav .brand {
    font-family:'Plus Jakarta Sans',sans-serif;
    font-size:2rem; font-weight:800;
    letter-spacing:-0.03em; line-height:1;
    color: #111111;
  }
  .top-nav .welcome { color:#555555; font-size:0.85rem; }

  /* ── Section title ── */
  .sec-title {
    font-family:'Plus Jakarta Sans',sans-serif;
    font-size:1.75rem; font-weight:800;
    color:var(--text); margin-bottom:0.25rem;
    letter-spacing:-0.02em;
    line-height:1.2;
  }
  .sec-sub   { color:#555555; font-size:0.84rem; margin-bottom:1.5rem; padding-bottom:1rem; border-bottom:1px solid #fadde1; }

  /* ══════════════════════════════════════════════
     CLIENT CARD — base
  ══════════════════════════════════════════════ */
  .client-card {
    background: #ffffff;
    border: 1.5px solid #fadde1;
    border-radius: 16px;
    padding: 1.4rem 1.5rem;
    transition: border-color 0.25s ease, box-shadow 0.25s ease, transform 0.25s ease;
    position: relative;
    cursor: pointer;
    min-height: 160px;
    box-shadow: 0 4px 18px rgba(0,0,0,0.1), 0 1px 4px rgba(0,0,0,0.06);
    overflow: hidden;
  }
  .client-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 3px;
    background: linear-gradient(90deg, #ff69b4, #fadde1);
    border-radius: 16px 16px 0 0;
    z-index: 5;
  }

  /* Card content elements */
  .card-icon   { width:42px; height:42px; border-radius:10px;
    background:linear-gradient(135deg,rgba(255,105,180,.15),rgba(255,182,193,.1));
    border:1px solid rgba(255,105,180,.2);
    display:flex; align-items:center; justify-content:center;
    font-size:1.2rem; margin-bottom:0.65rem; opacity:1; transition:opacity 0.2s ease; }
  .card-name   { font-family:'Plus Jakarta Sans',sans-serif; font-size:1.1rem; font-weight:700;
    color:#111111; margin-bottom:0.15rem; white-space:nowrap; overflow:hidden;
    text-overflow:ellipsis; letter-spacing:-0.01em; opacity:1; transition:opacity 0.2s ease; }
  .card-sector { font-size:.72rem; color:#333333; font-weight:600;
    text-transform:uppercase; letter-spacing:.06em; margin-bottom:.65rem;
    opacity:1; transition:opacity 0.2s ease; }
  .card-meta   { display:flex; gap:.85rem; font-size:.78rem; color:#444444; font-weight:500; opacity:1; transition:opacity 0.2s ease; }
  .card-meta span { color:#ff69b4; font-weight:700; }

  /* ══════════════════════════════════════════════
     HOVER OVERLAY — buttons appear INSIDE the card
     using position:absolute on the stVerticalBlock

     stVerticalBlock = positioning context (pos:relative)
     children 2-4    = position:absolute, overlaid on card
  ══════════════════════════════════════════════ */

  /* Make the column's vertical block the positioning anchor */
  div[data-testid="stColumn"] > div[data-testid="stVerticalBlock"]:has(.client-card) {
    position: relative !important;
  }

  /* Card content: always visible by default */
  .card-icon, .card-name, .card-sector, .card-meta {
    opacity: 1 !important;
  }

  /* Card hover: highlight border, darken bg, fade content — only on true hover devices */
  @media (hover: hover) {
    div[data-testid="stColumn"] > div[data-testid="stVerticalBlock"]:has(.client-card):hover
        .client-card {
      border-color: #ff69b4 !important;
      background: #fffafd !important;
      box-shadow: 0 8px 30px rgba(255,105,180,0.15) !important;
    }
    div[data-testid="stColumn"] > div[data-testid="stVerticalBlock"]:has(.client-card):hover
        .card-icon,
    div[data-testid="stColumn"] > div[data-testid="stVerticalBlock"]:has(.client-card):hover
        .card-name,
    div[data-testid="stColumn"] > div[data-testid="stVerticalBlock"]:has(.client-card):hover
        .card-sector,
    div[data-testid="stColumn"] > div[data-testid="stVerticalBlock"]:has(.client-card):hover
        .card-meta {
      opacity: 0 !important;
      transition: opacity 0.18s ease !important;
    }
  }

  /* Button containers: absolutely positioned, hidden by default */
  div[data-testid="stColumn"] > div[data-testid="stVerticalBlock"]:has(.client-card)
      > div:nth-child(2),
  div[data-testid="stColumn"] > div[data-testid="stVerticalBlock"]:has(.client-card)
      > div:nth-child(3),
  div[data-testid="stColumn"] > div[data-testid="stVerticalBlock"]:has(.client-card)
      > div:nth-child(4) {
    position: absolute !important;
    left: 0 !important;
    right: 0 !important;
    margin: 0 !important;
    padding: 0 0.5rem !important;
    opacity: 0 !important;
    pointer-events: none !important;
    transition: opacity 0.2s ease !important;
    z-index: 10 !important;
  }
  /* Vertical positions — centered in 160px card:
     3 buttons × 40px + 2 gaps × 6px = 132px
     offset = (160-132)/2 = 14px
     btn1: top 14px, btn2: top 14+40+6=60px, btn3: top 60+40+6=106px */
  div[data-testid="stColumn"] > div[data-testid="stVerticalBlock"]:has(.client-card)
      > div:nth-child(2) { top: 14px !important; }
  div[data-testid="stColumn"] > div[data-testid="stVerticalBlock"]:has(.client-card)
      > div:nth-child(3) { top: 60px !important; }
  div[data-testid="stColumn"] > div[data-testid="stVerticalBlock"]:has(.client-card)
      > div:nth-child(4) { top: 106px !important; }

  /* Stagger fade-in */
  div[data-testid="stColumn"] > div[data-testid="stVerticalBlock"]:has(.client-card)
      > div:nth-child(2) { transition-delay: 0s !important; }
  div[data-testid="stColumn"] > div[data-testid="stVerticalBlock"]:has(.client-card)
      > div:nth-child(3) { transition-delay: 0.06s !important; }
  div[data-testid="stColumn"] > div[data-testid="stVerticalBlock"]:has(.client-card)
      > div:nth-child(4) { transition-delay: 0.12s !important; }

  /* Reveal on hover */
  @media (hover: hover) {
    div[data-testid="stColumn"] > div[data-testid="stVerticalBlock"]:has(.client-card):hover
        > div:nth-child(2),
    div[data-testid="stColumn"] > div[data-testid="stVerticalBlock"]:has(.client-card):hover
        > div:nth-child(3),
    div[data-testid="stColumn"] > div[data-testid="stVerticalBlock"]:has(.client-card):hover
        > div:nth-child(4) {
      opacity: 1 !important;
      pointer-events: auto !important;
    }
  }

  /* — Button base style — */
  div[data-testid="stVerticalBlock"]:has(.client-card) .stButton > button {
    width: 100% !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    font-size: 0.8rem !important;
    padding: 0.42rem 1rem !important;
    line-height: 1.4 !important;
    cursor: pointer !important;
    min-height: unset !important;
    transition: all 0.18s ease !important;
  }

  /* — New Estimate: dark neutral — */
  div[data-testid="stColumn"] > div[data-testid="stVerticalBlock"]:has(.client-card)
      > div:nth-child(2) .stButton > button {
    background: #ddeea0 !important;
    border: 1px solid #bbcc66 !important;
    color: #556600 !important;
    font-weight: 700 !important;
    box-shadow: 0 1px 4px rgba(170,204,0,0.15) !important;
  }
  div[data-testid="stColumn"] > div[data-testid="stVerticalBlock"]:has(.client-card)
      > div:nth-child(2) .stButton > button:hover {
    background: #aacc00 !important;
    border-color: #88aa00 !important;
    color: #ffffff !important;
    box-shadow: 0 4px 14px rgba(170,204,0,0.4) !important;
  }

  /* — View History: clearly visible grey — */
  div[data-testid="stColumn"] > div[data-testid="stVerticalBlock"]:has(.client-card)
      > div:nth-child(3) .stButton > button {
    background: #e8e8e8 !important;
    border: 1px solid #aaaaaa !important;
    color: #111111 !important;
    font-weight: 600 !important;
  }
  div[data-testid="stColumn"] > div[data-testid="stVerticalBlock"]:has(.client-card)
      > div:nth-child(3) .stButton > button:hover {
    background: #cccccc !important;
    border-color: #888888 !important;
    color: #000000 !important;
  }

  /* — Delete Client: clear danger style — */
  div[data-testid="stColumn"] > div[data-testid="stVerticalBlock"]:has(.client-card)
      > div:nth-child(4) .stButton > button {
    background: #fff0f0 !important;
    border: 1px solid #f87171 !important;
    color: #dc2626 !important;
    font-weight: 600 !important;
  }
  div[data-testid="stColumn"] > div[data-testid="stVerticalBlock"]:has(.client-card)
      > div:nth-child(4) .stButton > button:hover {
    background: #dc2626 !important;
    border-color: #dc2626 !important;
    color: #ffffff !important;
    box-shadow: 0 3px 14px rgba(220,38,38,0.35) !important;
  }

  /* ── Text inputs ── */
  .stTextInput > label { color:#444444 !important; font-size:.82rem !important; }
  .stTextInput input   { background:#ffffff !important; border:1px solid #fadde1 !important; border-radius:10px !important; color:#111111 !important; }
  .stTextInput input:focus { border-color:#ff69b4 !important; }

  /* ── Logout btn ── */
  #logout-btn > button { background:transparent !important; border:1px solid #dedede !important; color:#555555 !important; border-radius:8px !important; font-size:.8rem !important; padding:.35rem .8rem !important; }
  #logout-btn > button:hover { border-color:#ff4d6d !important; color:#ff4d6d !important; }

</style>
""", unsafe_allow_html=True)



# ── Top Navigation ────────────────────────────────────────────────────────
logo_col, logout_col = st.columns([10, 2])
with logo_col:
    st.image("assets/logo.png", width=180)
with logout_col:
    if st.button("Logout", key="logout_btn_clients"):
        st.session_state.logged_in = False
        st.rerun()

user_email = st.session_state.get("user", {}).get("email", "")
st.markdown(f'<div style="color:#666; font-size:0.85rem; margin-top:-1.5rem; margin-bottom:1.5rem;">Welcome, {user_email} · {role_badge()}</div>', unsafe_allow_html=True)

# ── Section title + Add Client ─────────────────────────────────────────────
col_title, col_add = st.columns([5, 1])
with col_title:
    st.markdown("""
    <div class="sec-title">🏢 Clients</div>
    <div class="sec-sub">Hover over a card to see actions.</div>
    """, unsafe_allow_html=True)
with col_add:
    st.markdown("<div style='padding-top:1.5rem'></div>", unsafe_allow_html=True)
    if can("create_client"):
        if st.button("➕ Add Client", key="show_add_form_top", use_container_width=True, type="primary"):
            st.session_state["show_add_client_form"] = True
            st.rerun()

# ── Messages ───────────────────────────────────────────────────────────────
if "delete_success" in st.session_state:
    st.success(st.session_state.pop("delete_success"))
if "delete_error" in st.session_state:
    st.error(st.session_state.pop("delete_error"))

# ── Load clients ───────────────────────────────────────────────────────────
try:
    clients = get_all_clients()
except Exception as e:
    st.error(f"Database error: {e}")
    clients = []

SECTOR_ICONS = {
    "Banking": "🏦", "Insurance": "🛡️", "Finance": "💳",
    "Retail": "🛒", "Healthcare": "🏥", "Telecom": "📡",
    "Default": "🏢",
}

# ── Client grid ────────────────────────────────────────────────────────────
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

            # Card HTML (purely visual — no buttons inside)
            st.markdown(f"""
            <div class="client-card">
              <div class="card-icon">{icon}</div>
              <div class="card-name">{cname}</div>
              <div class="card-sector">{sector}</div>
              <div class="card-meta">
                <div>{count} estimate{"s" if count != 1 else ""}</div>
                <div>Last: <span>{last_str}</span></div>
              </div>
            </div>
            """, unsafe_allow_html=True)

            # ── Real Streamlit buttons — positioned over card via CSS ──
            # These are rendered AFTER the card (DOM siblings), pulled UP
            # into the card's visual area via negative margin-top CSS.
            # They use opacity:0 (not visibility:hidden) so they're clickable.
            
            btn_new = False
            if can("create_estimate"):
                btn_new = st.button("➕  New Estimate", key=f"new_{cid}", use_container_width=True, type="primary")
            else:
                st.markdown("<div style='display:none'></div>", unsafe_allow_html=True)
                
            btn_hist = st.button("📋  View History", key=f"hist_{cid}", use_container_width=True)
            
            btn_delete = False
            if can("delete_client"):
                btn_delete = st.button(
                    "🗑️  Delete Client",
                    key=f"del_{cid}",
                    use_container_width=True,
                    on_click=handle_delete_client,
                    args=(cid, cname),
                )
            else:
                st.markdown("<div style='display:none'></div>", unsafe_allow_html=True)

            if btn_new:
                st.session_state.selected_client = item
                st.session_state.load_estimate = None
                for k in ["last_metrics","last_distribution","last_pricing",
                          "env_pricing","gcp_pricing","comparison",
                          "cloud_sizing_xlsx","aws_pricing_xlsx","gcp_pricing_xlsx",
                          "pdf_report_path","last_saved_id","client_mode",
                          "show_summary","summary_df","show_success"]:
                    st.session_state[k] = None if k not in ["show_summary","show_success"] else False
                st.switch_page("pages/3_Estimator.py")

            if btn_hist:
                st.session_state.selected_client = item
                st.switch_page("pages/2_Estimates.py")

# ── Add New Client form ────────────────────────────────────────────────────
if st.session_state.get("show_add_client_form"):
    st.divider()
    st.markdown("### ＋ Add New Client")

    new_name = st.text_input("Client Name", placeholder="e.g. Axis Bank", key="new_client_name")

    submit_col, cancel_col = st.columns([1, 1])
    if submit_col.button("✅ Create & Start Estimate", key="btn_add_client", type="primary", use_container_width=True):
        if new_name.strip():
            try:
                new_cid = create_client(new_name.strip(), "Default")
                st.session_state["show_add_client_form"] = False
                st.session_state.selected_client = {"id": new_cid, "name": new_name.strip(), "sector": "Default"}
                st.session_state.load_estimate = None
                for k in ["last_metrics","last_distribution","last_pricing",
                          "env_pricing","gcp_pricing","comparison",
                          "cloud_sizing_xlsx","aws_pricing_xlsx","gcp_pricing_xlsx",
                          "pdf_report_path","last_saved_id","client_mode",
                          "show_summary","summary_df","show_success"]:
                    st.session_state[k] = None if k not in ["show_summary","show_success"] else False
                st.switch_page("pages/3_Estimator.py")
            except Exception as e:
                st.error(f"Failed to add client: {e}")
        else:
            st.warning("Please enter a client name.")

    if cancel_col.button("✕ Cancel", key="btn_cancel_add", use_container_width=True):
        st.session_state["show_add_client_form"] = False
        st.rerun()