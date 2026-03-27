"""
theme.py — Inject dark premium UI with animations into Streamlit
"""
import html
import streamlit as st

FORCE_DARK = """
<style>
/* ═══════════════════════════════════════════════
   NUCLEAR DARK MODE — hardcoded, no config needed
═══════════════════════════════════════════════ */

/* Every possible Streamlit container */
html, body,
.stApp,
[data-testid="stAppViewContainer"],
[data-testid="stMain"] {
  background-color: #ffffff !important;
  color: #000000 !important;
  margin: 0 !important;
  padding: 0 !important;
}

/* Main block container (inner content) — use padding here instead */
[data-testid="stMainBlockContainer"],
[data-testid="block-container"],
.main .block-container {
  padding-top: 0 !important;
  padding-bottom: 1rem !important;
  padding-left: 2rem !important;
  padding-right: 2rem !important;
}

header[data-testid="stHeader"] {
    display: none !important;
}

/* Push primary logo to top edge only */
[data-testid="stMainBlockContainer"] [data-testid="stImage"]:first-child img {
    margin-left: 0 !important;
    margin-top: -0.8rem !important;
}

/* ALL sidebar nav elements — Visibility & Sizing (Default State) */
[data-testid="stSidebarNav"] {
  padding-top: 0.5rem !important;
}

[data-testid="stSidebarNavLink"] p,
[data-testid="stSidebarNavSectionHeader"],
[data-testid="stSidebarNavLink"] span {
  background-color: transparent !important;
  color: #eeeeee !important;
  font-size: 1.1rem !important;
  opacity: 1 !important;
  visibility: visible !important;
}

[data-testid="stSidebarNavLink"] svg {
  width: 24px !important;
  height: 24px !important;
  margin-right: 0.8rem !important;
  fill: #eeeeee !important;
  color: #eeeeee !important;
  opacity: 1 !important;
  visibility: visible !important;
}

/* Nav link base */
[data-testid="stSidebarNavLink"] {
  background-color: transparent !important;
  border-radius: 6px !important;
  margin: 1px 4px !important;
  border-left: 3px solid transparent !important;
}

/* Hover state */
[data-testid="stSidebarNavLink"]:hover,
[data-testid="stSidebarNavLink"]:hover *,
[data-testid="stSidebarNavLink"]:hover p,
[data-testid="stSidebarNavLink"]:hover span {
  background-color: #222222 !important;
  color: #ffffff !important;
}

/* Active/selected */
[data-testid="stSidebarNavLink"][aria-current],
[data-testid="stSidebarNavLink"][aria-current="page"],
[data-testid="stSidebarNavLink"][aria-selected="true"] {
  background-color: #2a2a2a !important;
  border-left: 3px solid #ff69b4 !important;
}
[data-testid="stSidebarNavLink"][aria-current] *,
[data-testid="stSidebarNavLink"][aria-current="page"] *,
[data-testid="stSidebarNavLink"][aria-current="page"] p,
[data-testid="stSidebarNavLink"][aria-current="page"] span,
[data-testid="stSidebarNavLink"][aria-selected="true"] *,
[data-testid="stSidebarNavLink"][aria-selected="true"] p,
[data-testid="stSidebarNavLink"][aria-selected="true"] span {
  background-color: transparent !important;
  color: #ffffff !important;
}

/* Section headers */
[data-testid="stSidebarNavSectionHeader"],
[data-testid="stSidebarNavSectionHeader"] * {
  background-color: transparent !important;
  color: #666666 !important;
  font-size: 0.68rem !important;
  font-weight: 700 !important;
  letter-spacing: 0.1em !important;
  text-transform: uppercase !important;
}

/* All inputs */
input, textarea, select {
  background-color: #ffffff !important;
  color: #000000 !important;
  border: 1px solid #2a3555 !important;
}

/* Streamlit input wrappers */
[data-testid="stTextInput"] > div > div,
[data-testid="stTextInput"] input,
[data-testid="stNumberInput"] > div > div,
[data-testid="stNumberInput"] input,
[data-testid="stDateInput"] > div > div,
[data-testid="stDateInput"] input,
[data-testid="stTimeInput"] input,
[data-testid="stTextArea"] textarea {
  background-color: #ffffff !important;
  color: #000000 !important;
  border-color: #2a3555 !important;
}

/* Selectbox / dropdown */
[data-testid="stSelectbox"] > div > div,
[data-baseweb="select"] > div,
[data-baseweb="input"] > div,
[data-baseweb="base-input"],
[data-baseweb="base-input"] > div {
  background-color: #ffffff !important;
  color: #000000 !important;
  border-color: #2a3555 !important;
}

/* Hide the trailing cursor/box in dropdown search inputs */
[data-testid="stSelectbox"] input,
[data-baseweb="select"] input {
  caret-color: transparent !important;
  border: none !important;
  box-shadow: none !important;
  outline: none !important;
  background: transparent !important;
}

[data-baseweb="popover"],
[data-baseweb="menu"],
[role="listbox"],
[role="option"],
ul[role="listbox"],
li[role="option"] {
  background-color: #ffffff !important;
  color: #000000 !important;
  border-color: #dee2e6 !important;
}

/* Expanders */
[data-testid="stExpander"],
[data-testid="stExpander"] > div {
  background-color: #ffffff !important;
  border-color: #2a3555 !important;
  color: #000000 !important;
  margin: 1rem 0 !important;
}

[data-testid="stExpander"] summary {
  background-color: #fadde1 !important;
  border-color: #2a3555 !important;
  color: #000000 !important;
}

/* Tabs */
[data-baseweb="tab-list"],
[data-baseweb="tab"],
[data-baseweb="tab-panel"],
[role="tabpanel"],
[role="tab"] {
  background-color: #ffffff !important;
  color: #000000 !important;
  border-color: #2a3555 !important;
}
[aria-selected="true"] {
  background-color: #4f8ef7 !important;
  color: #ffffff !important;
}

/* Alerts / info boxes */
[data-testid="stAlert"],
[data-testid="stAlert"] > div,
[data-testid="stNotification"] {
  background-color: #ffffff !important;
  border-color: #2a3555 !important;
  color: #000000 !important;
}

/* Metrics */
[data-testid="stMetric"],
[data-testid="stMetricValue"],
[data-testid="stMetricLabel"],
[data-testid="stMetricDelta"] {
  background-color: #ffffff !important;
  color: #000000 !important;
}

/* Dataframes */
[data-testid="stDataFrame"],
[data-testid="stDataFrame"] > div,
[data-testid="stTable"],
.stDataFrame iframe {
  background-color: #ffffff !important;
  color: #000000 !important;
}

/* Checkboxes, radios */
[data-testid="stCheckbox"],
[data-testid="stRadio"],
[data-testid="stRadio"] > div,
[data-testid="stCheckbox"] > label {
  color: #000000 !important;
}

/* All labels */
label, .stMarkdown p, .stMarkdown span,
p, span, li {
  color: #000000 !important;
}

/* Dividers */
hr { border-color: #2a3555 !important; }

/* Scrollbar */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: #0a0e1a; }
::-webkit-scrollbar-thumb { background: #2a3555; border-radius: 10px; }
::-webkit-scrollbar-thumb:hover { background: #4f8ef7; }
</style>
"""

THEME_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@500;600;700;800&family=Inter:wght@300;400;500;600;700;800&display=swap');

/* ── Root variables ─────────────────────── */
:root {
  --bg:         #ffffff;
  --bg2:        #000000;
  --surface:    #f8f9fa;
  --surface2:   #f1f3f5;
  --border:     #2a3555;
  --accent:     #4f8ef7;
  --accent2:    #7c5cfc;
  --accent3:    #00d4aa;
  --gold:       #f0a500;
  --danger:     #ff4d6d;
  --success:    #00d4aa;
  --warning:    #f0a500;
  --error:      #ff4d6d;
  --info:       #4f8ef7;
  --text:       #000000;
  --text2:      #333333;
  --text3:      #555555;
  --radius:     12px;
  --radius-lg:  20px;
  --shadow:     0 8px 32px rgba(0,0,0,0.4);
  --glow:       0 0 40px rgba(79,142,247,0.15);
  --header-grad: linear-gradient(135deg, #0f1629 0%, #1a2540 40%, #0f2044 100%);
}

/* ── Base reset ──────────────────────────────────────────────── */
html, body,
[data-testid="stAppViewContainer"],
[data-testid="stMain"],
[data-testid="stMainBlockContainer"],
.stApp, .main, .block-container,
section[data-testid="stSidebar"] + div,
div[class*="appview-container"],
div[class*="main"] {
  font-family: 'Inter', sans-serif !important;
  background-color: #ffffff !important;
  color: #000000 !important;
}

.stApp {
  background-color: #ffffff !important;
  color: #000000 !important;
}

/* ── Animated gradient header bar ───────────────────────────── */
.bn-header {
  background: #fffafd !important;
  border: 1.5px solid #fadde1 !important;
  border-radius: var(--radius-lg);
  padding: 2.25rem 2.75rem;
  margin: 1.5rem 0 2.5rem 0 !important;
  position: relative;
  overflow: hidden;
  animation: fadeSlideDown 0.6s ease-out;
  box-shadow: 0 12px 48px rgba(255,105,180,0.1), 0 2px 12px rgba(0,0,0,0.03) !important;
}

.bn-header::before {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 4px;
  background: linear-gradient(90deg, #ff69b4, #fadde1);
}

.bn-header h1 {
  font-family: 'Plus Jakarta Sans', sans-serif !important;
  font-size: 2rem !important;
  font-weight: 800 !important;
  color: #000000 !important;
  margin: 0 0 0.35rem 0 !important;
  letter-spacing: -0.035em;
  line-height: 1.1;
}

.bn-header p {
  color: #444444 !important;
  margin: 0 !important;
  font-size: 0.95rem;
  font-weight: 400;
  opacity: 0.85;
}

.bn-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: rgba(255,105,180,0.1) !important;
  border: 1px solid rgba(255,105,180,0.2) !important;
  color: #ff69b4 !important;
  font-size: 0.8rem;
  font-weight: 700;
  padding: 6px 14px;
  border-radius: 20px;
  margin-top: 1rem;
  letter-spacing: 0.03em;
  box-shadow: 0 2px 8px rgba(255,105,180,0.08);
}

/* ── Section cards ───────────────────────────────────────────── */
.bn-card {
  background: var(--surface);
  border: 1.5px solid rgba(79,142,247,0.2);
  border-top: 3px solid var(--accent);
  border-radius: var(--radius-lg);
  padding: 1.5rem;
  margin-bottom: 1.25rem;
  animation: fadeSlideUp 0.5s ease-out both;
  transition: border-color 0.2s, box-shadow 0.2s;
  box-shadow: 0 4px 20px rgba(0,0,0,0.35), 0 1px 4px rgba(0,0,0,0.25);
}

.bn-card:hover {
  border-color: var(--accent);
  box-shadow: 0 6px 24px rgba(79,142,247,0.12);
}

.bn-card-title {
  font-family: 'Plus Jakarta Sans', sans-serif;
  font-size: 0.8rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: var(--accent);
  margin-bottom: 1rem;
  display: flex;
  align-items: center;
  gap: 8px;
}

/* ── Mode selection buttons ──────────────────────────────────── */
.mode-btn-saas, .mode-btn-onprem {
  background: var(--surface2) !important;
  border: 2px solid var(--border) !important;
  border-radius: var(--radius-lg) !important;
  padding: 1.5rem !important;
  cursor: pointer;
  transition: all 0.3s ease;
  text-align: center;
  position: relative;
  overflow: hidden;
}

.mode-btn-saas.active {
  border-color: var(--accent) !important;
  background: var(--glow) !important;
  box-shadow: 0 0 30px rgba(79,142,247,0.15);
}

.mode-btn-onprem.active {
  border-color: var(--accent3) !important;
  background: var(--glow) !important;
  box-shadow: 0 0 30px rgba(0,212,170,0.15);
}

/* ── KPI metric cards ─────────────────────────────────────────── */
.kpi-card {
  background: var(--surface);
  border: 1.5px solid var(--border);
  border-radius: var(--radius);
  padding: 1.25rem 1.5rem;
  position: relative;
  overflow: hidden;
  animation: fadeSlideUp 0.6s ease-out both;
  transition: transform 0.2s, box-shadow 0.2s;
  box-shadow: 0 4px 16px rgba(0,0,0,0.06), 0 1px 2px rgba(0,0,0,0.04) !important;
}

.kpi-card:hover {
  transform: translateY(-3px);
  box-shadow: var(--glow);
}

.kpi-card::before {
  content: '';
  position: absolute;
  top: 0; left: 0;
  width: 4px; height: 100%;
  background: var(--accent);
  border-radius: 4px 0 0 4px;
}

.kpi-card.gold::before  { background: var(--gold); }
.kpi-card.green::before { background: var(--accent3); }
.kpi-card.purple::before{ background: var(--accent2); }

.kpi-label {
  font-size: 0.72rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--text2);
  margin-bottom: 0.4rem;
}

.kpi-value {
  font-family: 'Plus Jakarta Sans', sans-serif;
  font-size: 1.65rem;
  font-weight: 800;
  color: var(--text);
  line-height: 1;
}

.kpi-sub {
  font-size: 0.75rem;
  color: var(--text3);
  margin-top: 0.3rem;
}

/* ── Cost banner ──────────────────────────────────────────────── */
.cost-banner {
  background: linear-gradient(135deg, rgba(79,142,247,0.12), rgba(124,92,252,0.12));
  border: 1px solid rgba(79,142,247,0.25);
  border-radius: var(--radius-lg);
  padding: 2rem 2.5rem;
  text-align: center;
  animation: pulse-glow 2s ease-in-out 1;
}

.cost-banner .label {
  font-size: 0.8rem;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: var(--text2);
  font-weight: 600;
}

.cost-banner .amount {
  font-family: 'Plus Jakarta Sans', sans-serif;
  font-size: 3rem;
  font-weight: 800;
  background: linear-gradient(135deg, var(--accent), var(--accent2));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  line-height: 1.1;
  letter-spacing: -0.03em;
}

.cost-banner .sub {
  color: var(--text2);
  font-size: 0.85rem;
  margin-top: 0.5rem;
}

/* ── Section divider ──────────────────────────────────────────── */
.bn-divider {
  height: 1px;
  background: linear-gradient(90deg, transparent, var(--border), transparent);
  margin: 2rem 0;
}

/* ── History cards ────────────────────────────────────────────── */
.history-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 1rem 1.25rem;
  margin-bottom: 0.75rem;
  cursor: pointer;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
}

.history-card:hover {
  border-color: var(--accent);
  background: var(--surface2);
  transform: translateX(4px);
}

.history-name {
  font-family: 'Plus Jakarta Sans', sans-serif;
  font-weight: 700;
  font-size: 0.95rem;
  color: var(--text);
}

.history-meta {
  font-size: 0.75rem;
  color: var(--text2);
  margin-top: 2px;
}

.history-cost {
  font-family: 'Plus Jakarta Sans', sans-serif;
  font-weight: 800;
  font-size: 1.1rem;
  color: var(--accent);
  text-align: right;
  white-space: nowrap;
}

.history-mode-badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 10px;
  font-size: 0.65rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.mode-saas  { background: var(--info); opacity: 0.15; color: var(--info); }
.mode-onprem{ background: var(--success); opacity: 0.15; color: var(--success); }

/* ── Table styling ────────────────────────────────────────────── */
.dataframe {
  background: var(--surface) !important;
  border: 1px solid var(--border) !important;
  border-radius: var(--radius) !important;
}

/* ── Streamlit button overrides ──────────────────────────────────────── */
.stButton > button,
.stButton > button[kind="primary"],
.stButton > button[kind="secondary"] {
  font-family: 'Plus Jakarta Sans', sans-serif !important;
  font-weight: 600 !important;
  border-radius: 10px !important;
  transition: all 0.2s ease !important;
  background: #4f8ef7 !important;
  border: none !important;
  color: #ffffff !important;
  box-shadow: 0 4px 16px rgba(79,142,247,0.3) !important;
}

.stButton > button:hover,
.stButton > button[kind="primary"]:hover,
.stButton > button[kind="secondary"]:hover {
  transform: translateY(-2px) !important;
  box-shadow: 0 8px 24px rgba(79,142,247,0.4) !important;
  background: #73a5f8 !important;
}

/* Green Generate buttons */
div[data-testid="stMarkdownContainer"]:has(.green-btn-target) {
  display: none !important;
  margin: 0 !important;
  padding: 0 !important;
}

div.element-container:has(.green-btn-target) + div.element-container .stButton > button {
  background: #aacc00 !important;
  box-shadow: 0 4px 16px rgba(170,204,0,0.3) !important;
}

div.element-container:has(.green-btn-target) + div.element-container .stButton > button:hover {
  background: #bbee00 !important;
  box-shadow: 0 8px 24px rgba(170,204,0,0.4) !important;
}

.stTextInput > div > div > input,
.stNumberInput > div > div > input,
.stSelectbox > div > div {
  background: #ffffff !important;
  border: 1px solid var(--border) !important;
  border-radius: 8px !important;
  color: var(--text) !important;
}

div[data-testid="stDateInput"] input {
  border: none !important;
  background-color: transparent !important;
  box-shadow: none !important;
}

.stTextInput > div > div > input:focus,
.stNumberInput > div > div > input:focus {
  border-color: #ff69b4 !important;
  box-shadow: 0 0 0 2px rgba(255,105,180,0.2) !important;
}

label, .stCheckbox label, .stSelectbox label {
  color: var(--text2) !important;
  font-size: 0.82rem !important;
  font-weight: 500 !important;
}

.stExpander {
  background: var(--surface) !important;
  border: 1px solid var(--border) !important;
  border-radius: var(--radius) !important;
}

.stExpander summary {
  color: var(--text) !important;
  font-weight: 600 !important;
}

.stTabs [data-baseweb="tab-list"] {
  background: var(--surface) !important;
  border-radius: var(--radius) !important;
  border: 1px solid var(--border) !important;
  padding: 4px !important;
  gap: 4px !important;
}

.stTabs [data-baseweb="tab"] {
  background: transparent !important;
  border-radius: 8px !important;
  color: var(--text2) !important;
  font-weight: 500 !important;
}

.stTabs [aria-selected="true"] {
  background: var(--accent) !important;
  color: white !important;
}

.stAlert {
  border-radius: var(--radius) !important;
  border: 1px solid var(--border) !important;
}

.stSuccess { background: rgba(0,212,170,0.08) !important; border-color: var(--success) !important; color: var(--success) !important; }
.stInfo    { background: rgba(79,142,247,0.08) !important; border-color: var(--info) !important;    color: var(--info) !important; }
.stWarning { background: rgba(240,165,0,0.08) !important;  border-color: var(--warning) !important; color: var(--warning) !important; }
.stError   { background: rgba(255,77,109,0.08) !important; border-color: var(--error) !important;   color: var(--error) !important; }

/* ══════════════════════════════════════════════════════════════════
   SIDEBAR — fixed 200px dark panel
══════════════════════════════════════════════════════════════════ */
  [data-testid="stSidebar"],
  [data-testid="stSidebar"][aria-expanded="true"],
  [data-testid="stSidebar"][aria-expanded="false"] {
    width: 200px !important;
    min-width: 200px !important;
    max-width: 200px !important;
    transform: none !important;
    transition: none !important;
    background: #111111 !important;
    border-right: 1px solid rgba(255,255,255,0.1) !important;
    box-shadow: 2px 0 16px rgba(0,0,0,0.3) !important;
  }

  [data-testid="stSidebarContent"] {
    width: 200px !important;
    min-width: 200px !important;
    background: #111111 !important;
    transition: none !important;
    /* ── KEY: flex column lets us reorder logo above nav ── */
    display: flex !important;
    flex-direction: column !important;
  }

  /* ── Logo block: pulled to top via order: -1 ── */
  [data-testid="stSidebarUserContent"] {
    order: -1 !important;
    background: #111111 !important;
    padding: 1.25rem 1rem 1rem 1rem !important;
    border-bottom: 1px solid rgba(255,255,255,0.1) !important;
    margin-bottom: 0.25rem !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    flex-shrink: 0 !important;
  }

  /* Strip all Streamlit wrapper padding from inside the logo block */
  [data-testid="stSidebarUserContent"] > div,
  [data-testid="stSidebarUserContent"] section,
  [data-testid="stSidebarUserContent"] .block-container,
  [data-testid="stSidebarUserContent"] [data-testid="stVerticalBlock"] {
    background: transparent !important;
    padding: 0 !important;
    margin: 0 !important;
    width: 100% !important;
  }

  /* Center and size the image */
  [data-testid="stSidebarUserContent"] [data-testid="stImage"] {
    display: flex !important;
    justify-content: center !important;
    width: 100% !important;
  }
  [data-testid="stSidebarUserContent"] [data-testid="stImage"] img {
    max-width: 148px !important;
    width: 85% !important;
    margin: 0 auto !important;
    display: block !important;
    background: transparent !important;
  }

  /* ── Nav sits below logo ── */
  [data-testid="stSidebarNav"] {
    order: 0 !important;
    padding-top: 0.5rem !important;
    margin-top: 0 !important;
  }

  /* Hide collapse toggle arrows */
  [data-testid="stSidebarCollapseButton"],
  button[data-testid="collapsedControl"] {
    display: none !important;
  }

  /* Nav link base */
  [data-testid="stSidebarNavLink"] {
    border-radius: 10px !important;
    margin: 4px 8px !important;
    padding: 10px 14px !important;
    display: flex !important;
    align-items: center !important;
    gap: 12px !important;
    white-space: nowrap !important;
    overflow: hidden !important;
    transition: background 0.2s ease !important;
  }
  [data-testid="stSidebarNavLink"]:hover {
    background: rgba(255,255,255,0.08) !important;
  }
  [data-testid="stSidebarNavLink"][aria-current="page"] {
    background: rgba(255,255,255,0.12) !important;
    border-left: 3px solid #ff0055 !important;
  }

  /* Icons */
  [data-testid="stSidebarNavLink"] svg,
  [data-testid="stSidebarNavLink"] img,
  [data-testid="stSidebarNavLink"] span:first-child {
    min-width: 22px !important;
    width: 22px !important;
    height: 22px !important;
    flex-shrink: 0 !important;
    opacity: 1 !important;
    fill: #ffffff !important;
    color: #ffffff !important;
  }

  /* Labels */
  [data-testid="stSidebarNavLink"] p {
    opacity: 1 !important;
    font-size: 0.9rem !important;
    font-weight: 500 !important;
    color: #ffffff !important;
  }

  /* Section headers */
  [data-testid="stSidebarNavSectionHeader"] {
    font-size: 0.65rem !important;
    font-weight: 700 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.1em !important;
    color: rgba(255,255,255,0.5) !important;
    padding: 18px 16px 8px !important;
    opacity: 1 !important;
  }

  [data-testid="stSidebar"] .stMarkdown h1,
  [data-testid="stSidebar"] .stMarkdown h2,
  [data-testid="stSidebar"] .stMarkdown h3 {
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    color: #ffffff !important;
  }

/* ── Animations ───────────────────────────────────────────────── */
@keyframes fadeSlideDown {
  from { opacity: 0; transform: translateY(-20px); }
  to   { opacity: 1; transform: translateY(0); }
}

@keyframes fadeSlideUp {
  from { opacity: 0; transform: translateY(20px); }
  to   { opacity: 1; transform: translateY(0); }
}

@keyframes shimmer {
  0%   { background-position: -300% 0; }
  100% { background-position: 300% 0; }
}

@keyframes pulse-glow {
  0%   { box-shadow: 0 0 0 rgba(79,142,247,0); }
  50%  { box-shadow: 0 0 40px rgba(79,142,247,0.25); }
  100% { box-shadow: 0 0 0 rgba(79,142,247,0); }
}

@keyframes spin-slow {
  from { transform: rotate(0deg); }
  to   { transform: rotate(360deg); }
}

/* stagger delays for cards */
.bn-card:nth-child(1) { animation-delay: 0.05s; }
.bn-card:nth-child(2) { animation-delay: 0.10s; }
.bn-card:nth-child(3) { animation-delay: 0.15s; }
.bn-card:nth-child(4) { animation-delay: 0.20s; }

/* ── Scrollbar ─────────────────────────────────────────────────── */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: var(--bg); }
::-webkit-scrollbar-thumb { background: var(--border); border-radius: 10px; }
::-webkit-scrollbar-thumb:hover { background: var(--text3); }

/* ── Number inputs ────────────────────────────────────────────── */
div[data-testid="stNumberInput"] > div,
div[data-testid="stNumberInput"] input,
div[data-testid="stNumberInput"] button,
div[data-testid="stNumberInput"] > div > div {
  background-color: #f1f3f5 !important;
  color: #000000 !important;
  border-color: #2a3555 !important;
}
div[data-testid="stNumberInput"] button {
  background-color: #dee2e6 !important;
  color: #000000 !important;
  border-color: #2a3555 !important;
}
div[data-testid="stNumberInput"] button:hover {
  background-color: #ced4da !important;
  color: #000000 !important;
}

/* Labels above inputs */
div[data-testid="stNumberInput"] label,
div[data-testid="stTextInput"] label,
div[data-testid="stSelectbox"] label,
div[data-testid="stSlider"] label {
  color: #000000 !important;
  font-size: 0.82rem !important;
  font-weight: 500 !important;
}

/* Expander header */
div[data-testid="stExpander"] summary,
div[data-testid="stExpander"] > div[role="button"] {
  background-color: #fadde1 !important;
  color: #000000 !important;
}

/* ── Force white background on all Streamlit containers ───────── */
.stApp,
.stApp > *,
section[data-testid="stMain"],
section[data-testid="stMain"] > *,
div[data-testid="stMainBlockContainer"],
div[data-testid="stMainBlockContainer"] > *,
div[data-testid="block-container"],
div[data-testid="block-container"] > *,
div[data-testid="stVerticalBlock"],
div[data-testid="stHorizontalBlock"],
.main, .main > * {
  background-color: #ffffff !important;
  color: #000000 !important;
}

/* ── Inputs, selects ────────────────────────────────────────────── */
input, textarea, select,
div[data-baseweb="input"] > div,
div[data-baseweb="base-input"] > input,
div[data-baseweb="select"] > div,
div[data-testid="stDateInput"] input,
div[data-testid="stTextInput"] input,
div[data-testid="stNumberInput"] input {
  background-color: #ffffff !important;
  color: #000000 !important;
  border-color: #2a3555 !important;
}

div[data-baseweb="popover"],
div[role="listbox"],
div[role="option"] {
  background-color: #ffffff !important;
  color: #000000 !important;
  border-color: #dee2e6 !important;
}

/* ── Expanders ──────────────────────────────────────────────────── */
div[data-testid="stExpander"],
div[data-testid="stExpander"] > div {
  background-color: #ffffff !important;
  border-color: #2a3555 !important;
}

/* ── Dataframes ─────────────────────────────────────────────────── */
div[data-testid="stDataFrame"],
div[data-testid="stDataFrame"] > div,
iframe {
  background-color: #ffffff !important;
  color: #000000 !important;
}

/* ── Metric cards ───────────────────────────────────────────────── */
div[data-testid="stMetric"],
div[data-testid="stMetricValue"],
div[data-testid="stMetricLabel"] {
  background-color: #ffffff !important;
  color: #000000 !important;
}

/* ── Tabs ───────────────────────────────────────────────────────── */
div[data-baseweb="tab-panel"],
div[role="tabpanel"] {
  background-color: #ffffff !important;
}

/* ── Alert boxes ────────────────────────────────────────────────── */
div[data-testid="stAlert"] {
  background-color: #ffffff !important;
  border-color: #2a3555 !important;
}

/* ── Text ───────────────────────────────────────────────────────── */
p, span, label, div, h1, h2, h3, h4, h5, h6, li {
  color: #000000;
}

/* ── Protect custom colored elements ────────────────────────────── */
.bn-header, .bn-card, .kpi-card, .cost-banner,
.history-card, .client-card, .estimate-card {
  color: #000000 !important;
}
</style>
"""


def inject_theme():
    st.markdown(FORCE_DARK, unsafe_allow_html=True)
    st.markdown(THEME_CSS, unsafe_allow_html=True)


def page_header(customer_name: str = "", client_mode: str = ""):
    mode_badge = ""
    if client_mode == "saas":
        mode_badge = '<span class="bn-badge">☁️ SaaS — PostgreSQL</span>'
    elif client_mode == "onprem":
        mode_badge = '<span class="bn-badge" style="background:var(--success); opacity:0.15; border-color:var(--success); color:var(--success);">🏢 On-Premise</span>'

    if customer_name:
        st.markdown(f"""
        <div style="margin-top:-1.5rem; margin-bottom:1.5rem;">
            <span style="color:var(--text2); font-size:0.9rem;">Client:</span>
            <span style="color:var(--text); font-weight:700; font-size:1.1rem; margin-left:4px;">{html.escape(customer_name)}</span>
            &nbsp;·&nbsp; {mode_badge}
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"<div style='margin-top:-1.5rem; margin-bottom:1.5rem;'>{mode_badge}</div>", unsafe_allow_html=True)


def section_title(icon: str, title: str, subtitle: str = ""):
    sub = f"<div style='font-size:0.8rem;color:var(--text2);margin-top:4px;font-weight:300;'>{subtitle}</div>" if subtitle else ""
    st.markdown(f"""
    <div style='margin-bottom:1.5rem;'>
      <div style='font-family:Inter,sans-serif;font-size:1.15rem;font-weight:700;
                  color:var(--text);display:flex;align-items:center;gap:8px;'>
        <span style='font-size:1.25rem;'>{icon}</span> {title}
      </div>
      {sub}
    </div>
    """, unsafe_allow_html=True)


def kpi_row(items: list):
    """items = list of (label, value, sub, variant) where variant = '' | 'gold' | 'green' | 'purple'"""
    cols = st.columns(len(items))
    for col, (label, value, sub, variant) in zip(cols, items):
        with col:
            st.markdown(f"""
            <div class="kpi-card {variant}">
              <div class="kpi-label">{label}</div>
              <div class="kpi-value">{value}</div>
              <div class="kpi-sub">{sub}</div>
            </div>
            """, unsafe_allow_html=True)


def cost_banner(monthly: float, annual: float, five_yr: float):
    st.markdown(f"""
    <div class="cost-banner">
      <div class="label">Total Monthly Cost</div>
      <div class="amount">${monthly:,.0f}</div>
      <div class="sub">
        Annual: <strong style='color:var(--text);'>${annual:,.0f}</strong>
        &nbsp;&nbsp;·&nbsp;&nbsp;
        5-Year (incl. inflation): <strong style='color:var(--gold);'>${five_yr:,.0f}</strong>
      </div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("")


def divider():
    st.markdown('<div class="bn-divider" style="background:var(--border); opacity:0.5;"></div>', unsafe_allow_html=True)