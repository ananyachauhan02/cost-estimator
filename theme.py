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
[data-testid="stMain"],
[data-testid="stMainBlockContainer"],
[data-testid="block-container"],
[data-testid="stVerticalBlock"],
[data-testid="stHorizontalBlock"],
[data-testid="stSidebar"],
[data-testid="stSidebarContent"],
[data-testid="stSidebarUserContent"],
[data-testid="stHeader"],
[data-testid="stToolbar"],
[data-testid="stDecoration"],
[data-testid="stStatusWidget"],
section.main,
.main,
.block-container,
div[class*="appview"],
div[class*="main"],
div[class*="block"] {
  background-color: #0a0e1a !important;
  color: #e8edf8 !important;
}

/* Sidebar specifically */
[data-testid="stSidebar"],
[data-testid="stSidebar"] > div,
[data-testid="stSidebarContent"] {
  background-color: #0f1629 !important;
  border-right: 2px solid rgba(79,142,247,0.2) !important;
}

/* Sidebar nav items */
[data-testid="stSidebarNav"],
[data-testid="stSidebarNavItems"],
[data-testid="stSidebarNavLink"],
[data-testid="stSidebarNavLink"] * {
  background-color: #0f1629 !important;
  color: #e8edf8 !important;
}

/* All inputs */
input, textarea, select {
  background-color: #1c2640 !important;
  color: #e8edf8 !important;
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
  background-color: #1c2640 !important;
  color: #e8edf8 !important;
  border-color: #2a3555 !important;
}

/* Selectbox / dropdown */
[data-testid="stSelectbox"] > div > div,
[data-baseweb="select"] > div,
[data-baseweb="input"] > div,
[data-baseweb="base-input"],
[data-baseweb="base-input"] > div,
[data-baseweb="popover"],
[data-baseweb="menu"],
[role="listbox"],
[role="option"],
ul[role="listbox"],
li[role="option"] {
  background-color: #151d35 !important;
  color: #e8edf8 !important;
  border-color: #2a3555 !important;
}

/* Slider */
[data-testid="stSlider"] > div > div > div,
[data-testid="stSlider"] div[role="slider"] {
  background-color: #2a3555 !important;
}

/* Expanders */
[data-testid="stExpander"],
[data-testid="stExpander"] > div,
[data-testid="stExpander"] summary {
  background-color: #151d35 !important;
  border-color: #2a3555 !important;
  color: #e8edf8 !important;
}

/* Tabs */
[data-baseweb="tab-list"],
[data-baseweb="tab"],
[data-baseweb="tab-panel"],
[role="tabpanel"],
[role="tab"] {
  background-color: #151d35 !important;
  color: #e8edf8 !important;
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
  background-color: #151d35 !important;
  border-color: #2a3555 !important;
  color: #e8edf8 !important;
}

/* Metrics */
[data-testid="stMetric"],
[data-testid="stMetricValue"],
[data-testid="stMetricLabel"],
[data-testid="stMetricDelta"] {
  background-color: #151d35 !important;
  color: #e8edf8 !important;
}

/* Dataframes */
[data-testid="stDataFrame"],
[data-testid="stDataFrame"] > div,
[data-testid="stTable"],
.stDataFrame iframe {
  background-color: #151d35 !important;
  color: #e8edf8 !important;
}

/* Checkboxes, radios */
[data-testid="stCheckbox"],
[data-testid="stRadio"],
[data-testid="stRadio"] > div,
[data-testid="stCheckbox"] > label {
  color: #e8edf8 !important;
}

/* All labels */
label, .stMarkdown p, .stMarkdown span,
p, span, li {
  color: #e8edf8 !important;
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

/* ── Root variables (Dark Mode Default) ─────────────────────── */
:root {
  --bg:         #0a0e1a;
  --bg2:        #0f1629;
  --surface:    #151d35;
  --surface2:   #1c2640;
  --border:     #2a3555;
  --accent:     #4f8ef7;
  --accent2:    #7c5cfc;
  --accent3:    #00d4aa;
  --gold:       #f0a500;
  --danger:     #ff4d6d;
  
  /* Semantic */
  --success:    #00d4aa;
  --warning:    #f0a500;
  --error:      #ff4d6d;
  --info:       #4f8ef7;

  --text:       #e8edf8;
  --text2:      #8b95b0;
  --text3:      #5a637a;
  --radius:     12px;
  --radius-lg:  20px;
  --shadow:     0 8px 32px rgba(0,0,0,0.4);
  --glow:       0 0 40px rgba(79,142,247,0.15);
  --header-grad: linear-gradient(135deg, #0f1629 0%, #1a2540 40%, #0f2044 100%);
}

/* Light mode removed — dark only */

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
  background-color: #0a0e1a !important;
  color: #e8edf8 !important;
}

.stApp {
  background-color: #0a0e1a !important;
  color: #e8edf8 !important;
}

/* Force all Streamlit section/frame backgrounds */
.stApp > header,
.stApp > div,
.stApp section,
.stApp > section {
  background-color: #0a0e1a !important;
}

.main .block-container {
  padding: 2rem 2.5rem !important;
  max-width: 1400px !important;
  background-color: #0a0e1a !important;
}

/* ── Animated gradient header bar ───────────────────────────── */
.bn-header {
  background: var(--header-grad);
  border: 1.5px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 2rem 2.5rem;
  margin-bottom: 2rem;
  position: relative;
  overflow: hidden;
  animation: fadeSlideDown 0.6s ease-out;
  box-shadow: 0 4px 28px rgba(0,0,0,0.45), 0 1px 6px rgba(0,0,0,0.3);
}

.bn-header::before {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 3px;
  background: linear-gradient(90deg, var(--accent), var(--accent2), var(--accent3), var(--accent));
  background-size: 300% 100%;
  animation: shimmer 3s linear infinite;
}

.bn-header::after {
  content: '';
  position: absolute;
  top: -60%; right: -10%;
  width: 400px; height: 400px;
  background: radial-gradient(circle, rgba(79,142,247,0.08) 0%, transparent 70%);
  pointer-events: none;
}

.bn-header h1 {
  font-family: 'Plus Jakarta Sans', sans-serif !important;
  font-size: 1.85rem !important;
  font-weight: 800 !important;
  color: var(--text) !important;
  margin: 0 0 0.25rem 0 !important;
  letter-spacing: -0.025em;
}

.bn-header p {
  color: var(--text2) !important;
  margin: 0 !important;
  font-size: 0.9rem;
  font-weight: 300;
}

.bn-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: rgba(79,142,247,0.15);
  border: 1px solid rgba(79,142,247,0.3);
  color: var(--accent);
  font-size: 0.75rem;
  font-weight: 600;
  padding: 4px 12px;
  border-radius: 20px;
  margin-top: 0.75rem;
  letter-spacing: 0.05em;
  text-transform: uppercase;
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
  box-shadow: 0 4px 20px rgba(0,0,0,0.35), 0 1px 4px rgba(0,0,0,0.25);
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

/* ── Streamlit overrides ──────────────────────────────────────── */
.stButton > button {
  font-family: 'Plus Jakarta Sans', sans-serif !important;
  font-weight: 600 !important;
  border-radius: 10px !important;
  transition: all 0.2s ease !important;
}

.stButton > button[kind="primary"] {
  background: linear-gradient(135deg, var(--accent), var(--accent2)) !important;
  border: none !important;
  color: white !important;
  box-shadow: 0 4px 16px rgba(79,142,247,0.3) !important;
}

.stButton > button[kind="primary"]:hover {
  transform: translateY(-2px) !important;
  box-shadow: 0 8px 24px rgba(79,142,247,0.4) !important;
}

.stButton > button[kind="secondary"] {
  background: var(--surface2) !important;
  border: 1px solid var(--border) !important;
  color: var(--text2) !important;
}

.stTextInput > div > div > input,
.stNumberInput > div > div > input,
.stSelectbox > div > div,
.stDateInput > div > div > input {
  background: var(--surface2) !important;
  border: 1px solid var(--border) !important;
  border-radius: 8px !important;
  color: var(--text) !important;
}

.stTextInput > div > div > input:focus,
.stNumberInput > div > div > input:focus {
  border-color: var(--accent) !important;
  box-shadow: 0 0 0 2px rgba(79,142,247,0.2) !important;
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
.stInfo    { background: rgba(79,142,247,0.08) !important; border-color: var(--info) !important; color: var(--info) !important; }
.stWarning { background: rgba(240,165,0,0.08) !important;  border-color: var(--warning) !important; color: var(--warning) !important; }
.stError   { background: rgba(255,77,109,0.08) !important; border-color: var(--error) !important; color: var(--error) !important; }

/* ── Auto-hide sidebar ──────────────────────────────────────────── */
  [data-testid="stSidebar"] {
    width: 56px !important;
    min-width: 56px !important;
    overflow: hidden !important;
    transition: width 0.3s cubic-bezier(0.4,0,0.2,1), min-width 0.3s cubic-bezier(0.4,0,0.2,1) !important;
    background: #0f1629 !important;
    border-right: 1px solid rgba(79,142,247,0.15) !important;
    box-shadow: 2px 0 16px rgba(0,0,0,0.3) !important;
  }
  [data-testid="stSidebar"]:hover {
    width: 260px !important;
    min-width: 260px !important;
    border-right: 1px solid rgba(79,142,247,0.3) !important;
    box-shadow: 4px 0 24px rgba(0,0,0,0.5) !important;
  }

  /* Clean up the nav items */
  [data-testid="stSidebarNavLink"] {
    border-radius: 10px !important;
    margin: 2px 6px !important;
    padding: 8px 10px !important;
    transition: background 0.2s ease !important;
    display: flex !important;
    align-items: center !important;
    gap: 10px !important;
    white-space: nowrap !important;
    overflow: hidden !important;
  }
  [data-testid="stSidebarNavLink"]:hover {
    background: rgba(79,142,247,0.12) !important;
  }
  [data-testid="stSidebarNavLink"][aria-current="page"] {
    background: rgba(79,142,247,0.18) !important;
    border-left: 3px solid #4f8ef7 !important;
  }

  /* Icons always visible and centered when collapsed */
  [data-testid="stSidebarNavLink"] svg,
  [data-testid="stSidebarNavLink"] img,
  [data-testid="stSidebarNavLink"] span:first-child {
    min-width: 20px !important;
    flex-shrink: 0 !important;
    opacity: 1 !important;
  }

  /* Hide text labels when collapsed */
  [data-testid="stSidebar"]:not(:hover) [data-testid="stSidebarNavLink"] p,
  [data-testid="stSidebar"]:not(:hover) [data-testid="stSidebarNavLink"] span:not(:first-child),
  [data-testid="stSidebar"]:not(:hover) [data-testid="stSidebarNavSectionHeader"],
  [data-testid="stSidebar"]:not(:hover) .stMarkdown {
    opacity: 0 !important;
    width: 0 !important;
    overflow: hidden !important;
    transition: opacity 0.15s ease, width 0.15s ease !important;
  }

  [data-testid="stSidebar"]:hover [data-testid="stSidebarNavLink"] p,
  [data-testid="stSidebar"]:hover [data-testid="stSidebarNavLink"] span:not(:first-child),
  [data-testid="stSidebar"]:hover [data-testid="stSidebarNavSectionHeader"],
  [data-testid="stSidebar"]:hover .stMarkdown {
    opacity: 1 !important;
    width: auto !important;
    transition: opacity 0.25s ease 0.1s, width 0.25s ease !important;
  }

  /* Section headers styling */
  [data-testid="stSidebarNavSectionHeader"] {
    font-size: 0.65rem !important;
    font-weight: 700 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.1em !important;
    color: rgba(79,142,247,0.6) !important;
    padding: 12px 16px 4px !important;
    white-space: nowrap !important;
  }

  /* A subtle vertical accent line when collapsed */
  [data-testid="stSidebar"]:not(:hover)::after {
    content: '';
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translateX(-50%) translateY(-50%);
    width: 2px;
    height: 40px;
    background: linear-gradient(180deg, transparent, rgba(79,142,247,0.4), transparent);
    border-radius: 2px;
    pointer-events: none;
  }

  /* Hide collapse button */
  [data-testid="stSidebarCollapseButton"],
  button[data-testid="collapsedControl"] { display: none !important; }
  [data-testid="stSidebarUserContent"] {
    display: none !important;
    height: 0 !important;
    min-height: 0 !important;
    padding: 0 !important;
    margin: 0 !important;
  }

  [data-testid="stSidebar"] .stMarkdown h1,
  [data-testid="stSidebar"] .stMarkdown h2,
  [data-testid="stSidebar"] .stMarkdown h3 {
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    color: var(--text) !important;
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

/* ── Number inputs specifically ────────────────────────────────── */
div[data-testid="stNumberInput"] > div,
div[data-testid="stNumberInput"] input,
div[data-testid="stNumberInput"] button,
div[data-testid="stNumberInput"] > div > div {
  background-color: #1c2640 !important;
  color: #e8edf8 !important;
  border-color: #2a3555 !important;
}
div[data-testid="stNumberInput"] button {
  background-color: #2a3555 !important;
  color: #e8edf8 !important;
  border-color: #3a4565 !important;
}
div[data-testid="stNumberInput"] button:hover {
  background-color: #4f8ef7 !important;
  color: #ffffff !important;
}
/* Labels above inputs */
div[data-testid="stNumberInput"] label,
div[data-testid="stTextInput"] label,
div[data-testid="stSelectbox"] label,
div[data-testid="stSlider"] label {
  color: #8b95b0 !important;
  font-size: 0.82rem !important;
  font-weight: 500 !important;
}
/* Expander header */
div[data-testid="stExpander"] summary,
div[data-testid="stExpander"] > div[role="button"] {
  background-color: #151d35 !important;
  color: #e8edf8 !important;
}

/* ── Force dark on ALL Streamlit native containers ─────────────── */
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
  background-color: #0a0e1a !important;
  color: #e8edf8 !important;
}

/* ── Inputs, selects, sliders ───────────────────────────────────── */
input, textarea, select,
div[data-baseweb="input"] > div,
div[data-baseweb="base-input"] > input,
div[data-baseweb="select"] > div,
div[data-testid="stDateInput"] input,
div[data-testid="stTextInput"] input,
div[data-testid="stNumberInput"] input,
div[data-baseweb="popover"],
div[role="listbox"],
div[role="option"] {
  background-color: #151d35 !important;
  color: #e8edf8 !important;
  border-color: #2a3555 !important;
}

/* ── Slider track ───────────────────────────────────────────────── */
div[data-testid="stSlider"] > div > div > div {
  background-color: #2a3555 !important;
}

/* ── Expanders ──────────────────────────────────────────────────── */
div[data-testid="stExpander"],
div[data-testid="stExpander"] > div {
  background-color: #151d35 !important;
  border-color: #2a3555 !important;
}

/* ── Dataframes / tables ────────────────────────────────────────── */
div[data-testid="stDataFrame"],
div[data-testid="stDataFrame"] > div,
iframe {
  background-color: #151d35 !important;
  color: #e8edf8 !important;
}

/* ── Metric cards ───────────────────────────────────────────────── */
div[data-testid="stMetric"],
div[data-testid="stMetricValue"],
div[data-testid="stMetricLabel"] {
  background-color: #151d35 !important;
  color: #e8edf8 !important;
}

/* ── Tabs ───────────────────────────────────────────────────────── */
div[data-baseweb="tab-panel"],
div[role="tabpanel"] {
  background-color: #0a0e1a !important;
}

/* ── Alert / info boxes ─────────────────────────────────────────── */
div[data-testid="stAlert"] {
  background-color: #151d35 !important;
  border-color: #2a3555 !important;
}

/* ── Labels and markdown text ───────────────────────────────────── */
p, span, label, div, h1, h2, h3, h4, h5, h6, li {
  color: #e8edf8;
}

/* ── Protect custom colored elements ────────────────────────────── */
.bn-header, .bn-card, .kpi-card, .cost-banner,
.history-card, .client-card, .estimate-card {
  color: #e8edf8 !important;
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

    name_line = f" &nbsp;·&nbsp; <span style='color:var(--accent);'>{html.escape(customer_name)}</span>" if customer_name else ""

    st.markdown(f"""
    <div class="bn-header">
      <h1>BusinessNext Cost Estimator{name_line}</h1>
      <p>Infrastructure sizing &amp; cloud cost forecasting platform</p>
      {mode_badge}
    </div>
    """, unsafe_allow_html=True)


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