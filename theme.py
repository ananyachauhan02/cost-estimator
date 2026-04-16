"""
theme.py — BusinessNext Cost Estimator Design System
Matches businessnext_ui.html exactly
"""
import html as _html
import streamlit as st

# ── Complete CSS Design System ──────────────────────────────────────────────
THEME_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700&family=IBM+Plex+Mono:wght@400;500&family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200&display=block');

/* ── Reset ──────────────────────────────────────────────────────────── */
*,*::before,*::after{box-sizing:border-box}

/* ── Semantic palette (invariant) ───────────────────────────────────── */
:root{
  --accent:#4f6ef7;--accent-lt:rgba(79,110,247,.10);--accent-md:rgba(79,110,247,.20);
  --success:#16a34a;--success-lt:rgba(22,163,74,.10);
  --warn:#d97706;--warn-lt:rgba(217,119,6,.10);
  --danger:#dc2626;--danger-lt:rgba(220,38,38,.10);
  --info:#0891b2;--info-lt:rgba(8,145,178,.10);
  --purple:#7c3aed;--purple-lt:rgba(124,58,237,.10);
  --trans:all .25s cubic-bezier(.4,0,.2,1);
  --ff:'Plus Jakarta Sans',sans-serif;
  --fm:'IBM Plex Mono',monospace;
  /* Light surfaces */
  --bg:#f8fafc;--bg2:#ffffff;--bg3:#f1f5f9;
  --border:rgba(15,23,42,.08);--border2:rgba(15,23,42,.14);
  --text:#0f172a;--text2:#475569;--text3:#94a3b8;--text4:#cbd5e1;
  --shadow:0 1px 3px rgba(0,0,0,.06),0 1px 2px rgba(0,0,0,.04);
  --shadow2:0 4px 16px rgba(0,0,0,.08),0 1px 3px rgba(0,0,0,.04);
  --shadow3:0 20px 60px rgba(0,0,0,.10),0 4px 16px rgba(0,0,0,.06);
}

/* ── Force light mode on Streamlit ───────────────────────────────────── */
html, body,
.stApp,
[data-testid="stAppViewContainer"],
[data-testid="stMain"],
[data-testid="stMainBlockContainer"],
[data-testid="block-container"],
[data-testid="stVerticalBlock"],
[data-testid="stHorizontalBlock"],
.main, .block-container {
  background-color: var(--bg) !important;
  color: var(--text) !important;
  font-family: var(--ff) !important;
  -webkit-font-smoothing: antialiased !important;
}

header[data-testid="stHeader"] { display:none !important; }

/* ── Keyframes ──────────────────────────────────────────────────────── */
@keyframes fadeUp{from{opacity:0;transform:translateY(16px)}to{opacity:1;transform:translateY(0)}}
@keyframes fadeIn{from{opacity:0}to{opacity:1}}
@keyframes slideDown{from{opacity:0;transform:translateY(-8px)}to{opacity:1;transform:translateY(0)}}
@keyframes numPop{from{opacity:0;transform:scale(.92) translateY(4px)}to{opacity:1;transform:scale(1) translateY(0)}}
@keyframes countUp{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:translateY(0)}}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.35}}
@keyframes barGrow{from{width:0}to{width:var(--w)}}
@keyframes accentLine{from{transform:scaleX(0)}to{transform:scaleX(1)}}
@keyframes pageIn{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:translateY(0)}}
@keyframes shimmer{0%{background-position:-200% 0}100%{background-position:200% 0}}

/* ── Page transition ─────────────────────────────────────────────────── */
[data-testid="stMainBlockContainer"],
div[data-testid="block-container"] {
  animation: pageIn 0.25s ease-out both !important;
}
[data-testid="stSidebar"],
[data-testid="stSidebarContent"] {
  animation: none !important;
  transition: none !important;
}

/* ── Sidebar ─────────────────────────────────────────────────────────── */
[data-testid="stSidebar"],
[data-testid="stSidebar"][aria-expanded="true"],
[data-testid="stSidebar"][aria-expanded="false"] {
  width: 220px !important;
  min-width: 220px !important;
  max-width: 220px !important;
  background: var(--bg2) !important;
  border-right: 1px solid var(--border) !important;
  box-shadow: 1px 0 8px rgba(0,0,0,.04) !important;
  transform: none !important;
  transition: none !important;
}

[data-testid="stSidebarContent"] {
  width: 220px !important;
  min-width: 220px !important;
  background: var(--bg2) !important;
  transition: none !important;
  display: flex !important;
  flex-direction: column !important;
}

/* Hide collapse arrows */
[data-testid="stSidebarCollapseButton"],
button[data-testid="collapsedControl"] {
  display: none !important;
}

/* ── Sidebar Logo ────────────────────────────────────────────────────── */
[data-testid="stSidebarHeader"],
button[aria-label="Navigate to home page"] {
  width: 220px !important;
  max-width: 220px !important;
  height: auto !important;
  padding: 24px 0 12px 0 !important; /* Premium spacing at top */
  margin: 0 !important;
  display: flex !important;
  justify-content: center !important;
  align-items: center !important;
  background: transparent !important;
  border: none !important;
  border-bottom: 1px solid var(--border) !important;
}


[data-testid="stSidebarHeader"] img,
[data-testid="stLogo"] img,
button[aria-label="Navigate to home page"] img {
  width: 195px !important; /* Optimized for perfect sidebar fit */
  max-width: 195px !important;
  height: auto !important;
  max-height: 90px !important;
  object-fit: contain !important;
  margin: 0 auto !important;
  padding: 0 !important;
  display: block !important;
}


/* ── Sidebar Nav ─────────────────────────────────────────────────────── */
[data-testid="stSidebarNav"] {
  padding-top: 0.5rem !important;
  margin-top: 0 !important;
}

[data-testid="stSidebarNavLink"] {
  border-radius: 8px !important;
  margin: 2px 10px !important;
  padding: 7px 10px !important;
  display: flex !important;
  align-items: center !important;
  gap: 9px !important;
  transition: background 0.2s ease !important;
  border: none !important;
  font-size: 12px !important;
  font-weight: 500 !important;
  color: var(--text2) !important;
  white-space: nowrap !important;
}

[data-testid="stSidebarNavLink"]:hover {
  background: var(--bg3) !important;
  color: var(--text) !important;
}

[data-testid="stSidebarNavLink"][aria-current="page"] {
  background: var(--accent-lt) !important;
  color: var(--accent) !important;
  border-left: 3px solid var(--accent) !important;
}

[data-testid="stSidebarNavLink"] p,
[data-testid="stSidebarNavLink"] span {
  background: transparent !important;
  font-size: 12px !important;
  font-weight: 500 !important;
  opacity: 1 !important;
  visibility: visible !important;
}

[data-testid="stSidebarNavLink"][aria-current="page"] p,
[data-testid="stSidebarNavLink"][aria-current="page"] span {
  color: var(--accent) !important;
  background: transparent !important;
}

[data-testid="stSidebarNavLink"] svg {
  width: 16px !important;
  height: 16px !important;
  flex-shrink: 0 !important;
  opacity: 1 !important;
}

/* ── Expander summary styling (Definitive Surgical Fix for Icon Text) ─ */
[data-testid="stExpander"] summary {
  background: var(--bg2) !important;
  border-radius: 10px !important;
  padding: 10px 14px !important;
  list-style: none !important;
  cursor: pointer !important;
  display: flex !important;
  align-items: center !important;
  gap: 8px !important;
  /* Kills any bare text nodes nodes in the summary */
  font-size: 0 !important;
  color: transparent !important;
  line-height: 0 !important;
}

/* Kill all text in all children (icons, symbols, etc.) */
[data-testid="stExpander"] summary * {
  font-size: 0 !important;
  color: transparent !important;
  line-height: 0 !important;
}

/* Selectively restore ONLY the actual text components (p and label) */
[data-testid="stExpander"] summary p,
[data-testid="stExpander"] summary label {
  display: inline-block !important;
  font-size: 13px !important;
  font-weight: 600 !important;
  color: var(--text) !important;
  opacity: 1 !important;
  visibility: visible !important;
  font-family: var(--ff) !important;
  line-height: 1.4 !important;
}





/* Hide the clickable toggle button entirely (it contains "LABEL expand_more") */
[data-testid="stSidebarNavSectionHeader"] > button,
[data-testid="stSidebarNavSectionHeader"] button {
  opacity: 0 !important;
  pointer-events: none !important;
  position: absolute !important;
  height: 0 !important;
  overflow: hidden !important;
}

/* The header wrapper itself — give it height and a top border/label look */
[data-testid="stSidebarNavSectionHeader"] {
  padding: 16px 12px 4px 12px !important;
  height: 28px !important;
  overflow: visible !important;
  position: relative !important;
  display: flex !important;
  align-items: center !important;
}

/* Inject the section label text from the button's aria-label via CSS
   — fallback: render first span text visible */
[data-testid="stSidebarNavSectionHeader"] > span,
[data-testid="stSidebarNavSectionHeader"] span:first-child {
  font-size: 9px !important;
  font-weight: 700 !important;
  text-transform: uppercase !important;
  letter-spacing: 0.08em !important;
  color: var(--text3) !important;
  display: block !important;
  line-height: 1 !important;
  opacity: 1 !important;
  visibility: visible !important;
  white-space: nowrap !important;
  overflow: hidden !important;
  text-overflow: ellipsis !important;
  max-width: calc(100% - 8px) !important;
}

/* Hide all SVGs (expand/collapse icons) inside nav header */
[data-testid="stSidebarNavSectionHeader"] svg,
[data-testid="stSidebarNavSectionHeader"] svg * {
  display: none !important;
  width: 0 !important;
  height: 0 !important;
}

[data-testid="stSidebarUserContent"] {
  display: none !important;
}

/* ─── Global compact button sizes ─────────────────────────────────── */
/* All secondary/default buttons in the app — compact */
button[data-testid="stBaseButton-secondary"],
button[kind="secondary"],
.stButton > button[kind="secondary"] {
  padding: 4px 10px !important;
  font-size: 11px !important;
  min-height: 28px !important;
  height: 28px !important;
  border-radius: 6px !important;
  line-height: 1 !important;
  background-color: var(--bg3) !important;
  color: var(--text2) !important;
  border: 1px solid var(--border2) !important;
}
button[data-testid="stBaseButton-secondary"]:hover {
  border-color: var(--accent) !important;
  color: var(--text) !important;
  background-color: var(--bg2) !important;
}

/* Suppression rule for 'expand_more' and other ligatures that leak as text */
button span:empty { display:none !important; }
button span { font-family: var(--ff) !important; }
button [data-testid="stIconMaterial"],
[data-testid="stIconMaterial"] {
  font-family: 'Material Symbols Outlined' !important;
  font-variation-settings: 'FILL' 0, 'wght' 400, 'GRAD' 0, 'opsz' 48 !important;
}

/* Surgical suppression for the specific expand_more text node */
button div span span {
    font-size: 0 !important;
    color: transparent !important;
}
button div span span::before {
    /* If we wanted to restore icons we would do it here, but for now just killing the text */
}
/* Primary buttons — compact but keep accent color */
button[data-testid="stBaseButton-primary"],
button[kind="primary"],
.stButton > button[kind="primary"] {
  padding: 4px 10px !important;
  font-size: 11px !important;
  min-height: 28px !important;
  height: 28px !important;
  border-radius: 6px !important;
  line-height: 1 !important;
  background: var(--accent) !important;
  color: #fff !important;
}
/* Download buttons too */
.stDownloadButton > button {
  padding: 4px 10px !important;
  font-size: 11px !important;
  min-height: 28px !important;
  height: 28px !important;
  border-radius: 6px !important;
}
/* Exception: specific nav/header action buttons stay at normal size */
[data-testid="stMainBlockContainer"] > div > div:first-child .stButton > button {
  height: auto !important;
  min-height: 34px !important;
  padding: 6px 14px !important;
  font-size: 12px !important;
}


/* ── Main content padding ────────────────────────────────────────────── */
[data-testid="stMainBlockContainer"],
[data-testid="block-container"],
.main .block-container {
  padding-top: 1.5rem !important;
  padding-left: 1.75rem !important;
  padding-right: 1.75rem !important;
  padding-bottom: 2rem !important;
  max-width: 1400px !important;
}

/* ── Typography ──────────────────────────────────────────────────────── */
p, span, label, li, div {
  font-family: var(--ff) !important;
  color: var(--text) !important;
}

/* ── Inputs ──────────────────────────────────────────────────────────── */
input, textarea, select,
[data-baseweb="input"] > div,
[data-baseweb="base-input"] > input,
[data-baseweb="select"] > div,
[data-testid="stDateInput"] input {
  background: var(--bg3) !important;
  color: var(--text) !important;
  border: 1px solid var(--border2) !important;
  border-radius: 8px !important;
  font-family: var(--ff) !important;
  font-size: 12px !important;
}

[data-testid="stTextInput"] input,
[data-testid="stTextInput"] textarea,
[data-testid="stTextInput"] [role="textbox"],
[data-testid="stNumberInput"] input {
  background: transparent !important;
  background-color: transparent !important;
  color: var(--text) !important;
  border: 1px solid var(--border2) !important;
  border-radius: 10px !important;
  font-family: var(--ff) !important;
  font-size: 12px !important;
  padding: 0.75rem !important;
  box-shadow: none !important;
}

div[data-testid="stTextInput"] > div,
div[data-testid="stTextInput"] > div > div,
div[data-testid="stTextInput"] > div > div > input,
[data-testid="stTextInput"] input,
[data-testid="stTextInput"] textarea,
[data-testid="stTextInput"] [role="textbox"],
[data-testid="stTextInput"] *,
[data-testid="stTextInput"] div,
[data-testid="stTextInput"] span,
[data-testid="stTextInput"] p {
  background: transparent !important;
  background-color: transparent !important;
  box-shadow: none !important;
  border: none !important;
}

[data-testid="stTextInput"] input:focus,
[data-testid="stNumberInput"] input:focus {
  border-color: var(--accent) !important;
  box-shadow: none !important;
  outline: none !important;
}

/* Chat bubbles should be minimal and avoid a separate white text background */
[data-testid="stChatMessage"],
.stChatMessage,
[data-testid="stChatMessage"] > div,
.stChatMessage > div,
[data-testid="stChatMessage"] div,
.stChatMessage div,
[data-testid="stChatMessage"] span,
.stChatMessage span,
[data-testid="stChatMessage"] p,
.stChatMessage p,
[data-testid="stChatMessage"] [data-testid="stMarkdownContainer"],
.stChatMessage [data-testid="stMarkdownContainer"] {
  background: transparent !important;
  background-color: transparent !important;
  box-shadow: none !important;
  border: none !important;
}

/* Number input wrappers */
div[data-testid="stNumberInput"] > div,
div[data-testid="stNumberInput"] > div > div {
  background: var(--bg3) !important;
  border-color: var(--border2) !important;
}

div[data-testid="stNumberInput"] button {
  background: var(--bg3) !important;
  color: var(--text2) !important;
  border-color: var(--border2) !important;
}

/* Selectbox */
[data-testid="stSelectbox"] > div > div,
[data-baseweb="select"] > div {
  background: var(--bg3) !important;
  color: var(--text) !important;
  border: 1px solid var(--border2) !important;
  border-radius: 8px !important;
  font-size: 12px !important;
}

[data-baseweb="popover"],
[data-baseweb="menu"],
[role="listbox"],
[role="option"],
ul[role="listbox"],
li[role="option"] {
  background: var(--bg2) !important;
  color: var(--text) !important;
  border-color: var(--border2) !important;
}

/* Hide caret on selectbox */
[data-testid="stSelectbox"] input,
[data-baseweb="select"] input {
  caret-color: transparent !important;
  border: none !important;
  background: transparent !important;
  box-shadow: none !important;
}

/* Labels */
label,
div[data-testid="stNumberInput"] label,
div[data-testid="stTextInput"] label,
div[data-testid="stSelectbox"] label,
div[data-testid="stSlider"] label,
div[data-testid="stDateInput"] label {
  font-family: var(--ff) !important;
  color: var(--text2) !important;
  font-size: 11px !important;
  font-weight: 600 !important;
  text-transform: none !important;
  letter-spacing: 0.04em !important;
}

div[data-testid="stDateInput"] input {
  border: none !important;
  background: transparent !important;
  box-shadow: none !important;
}

/* ── Sliders ─────────────────────────────────────────────────────────── */
[data-testid="stSlider"] > div > div > div {
  background: var(--border2) !important;
}
[data-testid="stSlider"] div[role="slider"] {
  background: var(--accent) !important;
}

/* ── Checkboxes ──────────────────────────────────────────────────────── */
[data-testid="stCheckbox"] {
  color: var(--text2) !important;
}
[data-testid="stCheckbox"] input[type="checkbox"] {
  accent-color: var(--accent) !important;
}







/* ── Tabs ────────────────────────────────────────────────────────────── */
.stTabs [data-baseweb="tab-list"] {
  background: var(--bg3) !important;
  border: 1px solid var(--border) !important;
  border-radius: 10px !important;
  padding: 3px !important;
  gap: 2px !important;
}
.stTabs [data-baseweb="tab"] {
  background: transparent !important;
  border-radius: 7px !important;
  color: var(--text2) !important;
  font-weight: 600 !important;
  font-size: 12px !important;
  padding: 6px 16px !important;
}
.stTabs [aria-selected="true"] {
  background: var(--accent) !important;
  color: #fff !important;
  box-shadow: 0 2px 8px rgba(79,110,247,.35) !important;
}
div[data-baseweb="tab-panel"],
div[role="tabpanel"] {
  background: var(--bg) !important;
}

/* ── Alerts / Info boxes ─────────────────────────────────────────────── */
[data-testid="stAlert"] {
  background: var(--bg2) !important;
  border: 1px solid var(--border) !important;
  border-radius: 10px !important;
  color: var(--text) !important;
}

/* ── Metrics ─────────────────────────────────────────────────────────── */
[data-testid="stMetric"] {
  background: var(--bg2) !important;
  border: 1px solid var(--border) !important;
  border-radius: 12px !important;
  padding: 14px 16px !important;
  box-shadow: var(--shadow) !important;
}
[data-testid="stMetricValue"] { color: var(--text) !important; }
[data-testid="stMetricLabel"] { color: var(--text3) !important; }

/* ── Dataframes ──────────────────────────────────────────────────────── */
[data-testid="stDataFrame"],
[data-testid="stDataFrame"] > div,
[data-testid="stTable"] {
  background: var(--bg2) !important;
  border: 1px solid var(--border) !important;
  border-radius: 12px !important;
  color: var(--text) !important;
}

[data-testid="stDataFrame"] table,
[data-testid="stDataFrame"] thead,
[data-testid="stDataFrame"] tbody,
[data-testid="stDataFrame"] th,
[data-testid="stDataFrame"] td,
[data-testid="stTable"] table,
[data-testid="stTable"] thead,
[data-testid="stTable"] tbody,
[data-testid="stTable"] th,
[data-testid="stTable"] td {
  color: var(--text) !important;
  border-color: var(--border2) !important;
  background-color: transparent !important;
}

[data-testid="stDataFrame"] table,
[data-testid="stTable"] table {
  border-collapse: collapse !important;
  width: 100% !important;
  border: 1px solid var(--border2) !important;
  background: var(--bg2) !important;
}

[data-testid="stDataFrame"] th,
[data-testid="stTable"] th {
  background: var(--bg3) !important;
  color: var(--text2) !important;
  font-weight: 700 !important;
  border: 1px solid var(--border2) !important;
}

[data-testid="stDataFrame"] td,
[data-testid="stTable"] td {
  background: var(--bg2) !important;
  color: var(--text) !important;
  border: 1px solid var(--border2) !important;
  padding: 8px 12px !important;
}

[data-testid="stDataFrame"] td:first-child,
[data-testid="stTable"] td:first-child {
  border-left: 1px solid var(--border2) !important;
}

[data-testid="stDataFrame"] td:last-child,
[data-testid="stTable"] td:last-child {
  border-right: 1px solid var(--border2) !important;
}

[data-testid="stDataFrame"] div[role="grid"],
[data-testid="stDataFrame"] div[role="gridcell"],
[data-testid="stDataFrame"] div[role="row"] {
  background-color: var(--bg2) !important;
}

[data-testid="stDataFrame"] div[role="columnheader"] {
  background-color: var(--bg3) !important;
  color: var(--text2) !important;
  font-weight: 700 !important;
}

[data-testid="stDataFrame"] button {
  color: var(--text2) !important;
  background: transparent !important;
}
  color: inherit !important;
  box-shadow: none !important;
}

/* ── Buttons ─────────────────────────────────────────────────────────── */
[data-testid="stButton"],
[data-testid="stDownloadButton"] {
  display: flex !important;
  align-items: center !important;
  margin-top: 0 !important;
}

.stButton > button,
.stButton > button[kind="primary"],
.stDownloadButton > button {
  font-family: var(--ff) !important;
  font-weight: 600 !important;
  font-size: 12px !important;
  border-radius: 8px !important;
  transition: var(--trans) !important;
  cursor: pointer !important;
}

.stButton > button[kind="primary"] {
  background: var(--accent) !important;
  border: none !important;
  color: #fff !important;
  box-shadow: 0 2px 8px rgba(79,110,247,.3) !important;
  padding: 6px 18px !important;
}
.stButton > button[kind="primary"]:hover {
  background: #3d5ce5 !important;
  transform: translateY(-1px) !important;
  box-shadow: 0 4px 16px rgba(79,110,247,.35) !important;
}

.stButton > button[kind="secondary"],
.stButton > button:not([kind]) {
  background: transparent !important;
  border: 1px solid var(--border2) !important;
  color: var(--text2) !important;
  padding: 5px 14px !important;
}
.stButton > button[kind="secondary"]:hover,
.stButton > button:not([kind]):hover {
  background: var(--bg3) !important;
  color: var(--text) !important;
}

.stDownloadButton > button {
  background: transparent !important;
  border: 1px solid var(--border2) !important;
  color: var(--text2) !important;
}
.stDownloadButton > button:hover {
  background: var(--bg3) !important;
  color: var(--text) !important;
}

/* ── Scrollbar ───────────────────────────────────────────────────────── */
::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: var(--bg); }
::-webkit-scrollbar-thumb { background: var(--border2); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: var(--text4); }

/* ── Divider ──────────────────────────────────────────────────────────── */
hr { border-color: var(--border) !important; }

/* ── Popover ──────────────────────────────────────────────────────────── */
[data-testid="stPopover"],
[data-baseweb="popover"] > div,
[data-baseweb="popover"] [data-baseweb="block"] {
  background: var(--bg2) !important;
  border: 1px solid var(--border2) !important;
  border-radius: 10px !important;
  box-shadow: var(--shadow2) !important;
}

/* ══════════════════════════════════════════════
   CUSTOM HTML COMPONENTS (matching businessnext_ui.html)
══════════════════════════════════════════════ */

/* ── Page header ──────────────────────────────────────────────────── */
.bn-page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 24px;
}
.bn-page-title {
  font-size: 20px;
  font-weight: 700;
  color: var(--text);
  letter-spacing: -.4px;
  font-family: var(--ff);
}
.bn-page-subtitle {
  font-size: 12px;
  color: var(--text2);
  margin-top: 3px;
  font-family: var(--ff);
}

/* ── Panel ────────────────────────────────────────────────────────── */
.bn-panel {
  background: var(--bg2);
  border: 1px solid var(--border);
  border-radius: 12px;
  overflow: hidden;
  box-shadow: var(--shadow);
  transition: box-shadow .25s;
  margin-bottom: 16px;
}
.bn-panel:hover { box-shadow: var(--shadow2); }
.bn-panel-header {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 14px 16px;
  border-bottom: 1px solid var(--border);
}
.bn-panel-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--text);
  flex: 1;
  font-family: var(--ff);
}
.bn-panel-body { padding: 16px; }

/* ── Metric cards ─────────────────────────────────────────────────── */
.bn-metrics {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  margin-bottom: 20px;
}
.bn-metric-card {
  background: var(--bg2);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 14px 16px;
  box-shadow: var(--shadow);
  cursor: pointer;
  transition: all .25s;
  position: relative;
  overflow: hidden;
  animation: numPop .5s ease both;
}
.bn-metric-card:hover { transform: translateY(-3px); box-shadow: var(--shadow2); }
.bn-metric-card::after {
  content: '';
  position: absolute; bottom: 0; left: 0; right: 0; height: 2px;
  transform: scaleX(0); transform-origin: left; transition: transform .3s ease;
}
.bn-metric-card:hover::after { transform: scaleX(1); }
.bn-metric-card.accent::after { background: var(--accent); }
.bn-metric-card.success::after { background: var(--success); }
.bn-metric-card.warn::after { background: var(--warn); }
.bn-metric-card.danger::after { background: var(--danger); }
.bn-metric-card.purple::after { background: var(--purple); }
.bn-metric-card.info::after { background: var(--info); }
.bn-metric-label {
  font-size: 10px; font-weight: 700; text-transform: uppercase;
  letter-spacing: .6px; color: var(--text3); margin-bottom: 6px;
  font-family: var(--ff);
}
.bn-metric-value {
  font-size: 22px; font-weight: 700; font-family: var(--fm);
  color: var(--text); line-height: 1;
}
.bn-metric-delta { font-size: 10px; font-family: var(--fm); margin-top: 4px; }
.bn-metric-delta.up { color: var(--success); }
.bn-metric-delta.down { color: var(--danger); }
.bn-metric-delta.flat { color: var(--text3); }

/* ── Badge ────────────────────────────────────────────────────────── */
.bn-badge {
  display: inline-flex; align-items: center; gap: 4px;
  font-size: 10px; font-weight: 700; padding: 2px 8px;
  border-radius: 20px; font-family: var(--fm);
}
.bn-badge.success { background: var(--success-lt); color: var(--success); }
.bn-badge.warn { background: var(--warn-lt); color: var(--warn); }
.bn-badge.danger { background: var(--danger-lt); color: var(--danger); }
.bn-badge.info { background: var(--info-lt); color: var(--info); }
.bn-badge.accent { background: var(--accent-lt); color: var(--accent); }
.bn-badge.purple { background: var(--purple-lt); color: var(--purple); }

/* ── Status dot ───────────────────────────────────────────────────── */
.bn-dot {
  width: 6px; height: 6px; border-radius: 50%;
  display: inline-block; animation: pulse 2s ease-in-out infinite; flex-shrink: 0;
}
.bn-dot.success { background: var(--success); }
.bn-dot.warn { background: var(--warn); animation-duration: 1.5s; }
.bn-dot.danger { background: var(--danger); animation-duration: 1s; }
.bn-dot.info { background: var(--info); animation-duration: 2.5s; }
.bn-dot.accent { background: var(--accent); }

/* ── Section label ────────────────────────────────────────────────── */
.bn-section-label {
  font-size: 10px; font-weight: 700; text-transform: uppercase;
  letter-spacing: .6px; color: var(--text3); display: flex;
  align-items: center; gap: 8px; margin-bottom: 12px;
  padding-bottom: 8px; border-bottom: 1px solid var(--border);
  font-family: var(--ff);
}
.bn-section-label::before {
  content: ''; width: 3px; height: 14px;
  background: var(--accent); border-radius: 2px; flex-shrink: 0;
}

/* ── Client cards ─────────────────────────────────────────────────── */
.bn-client-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 14px;
  margin-bottom: 20px;
}
.bn-client-card {
  background: var(--bg2);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 16px;
  box-shadow: var(--shadow);
  cursor: pointer;
  transition: all .25s;
  animation: fadeUp .4s ease both;
  position: relative;
  overflow: hidden;
}
.bn-client-card:hover {
  transform: translateY(-3px);
  box-shadow: var(--shadow2);
  border-color: var(--border2);
}
.bn-client-card::before {
  content: ''; position: absolute; top: 0; left: 0; right: 0; height: 3px;
  background: var(--accent); border-radius: 12px 12px 0 0;
}
.bn-client-card.success::before { background: var(--success); }
.bn-client-card.warn::before { background: var(--warn); }
.bn-client-card-top {
  display: flex; align-items: center;
  justify-content: space-between; margin-bottom: 10px;
}
.bn-client-icon {
  width: 36px; height: 36px; border-radius: 10px;
  background: var(--accent-lt); display: flex;
  align-items: center; justify-content: center; font-size: 16px;
}
.bn-client-name {
  font-size: 13px; font-weight: 600; color: var(--text); margin-bottom: 2px;
  font-family: var(--ff);
}
.bn-client-sector {
  font-size: 10px; color: var(--text3); text-transform: uppercase;
  letter-spacing: .4px; font-weight: 600; font-family: var(--ff);
}
.bn-client-meta {
  display: flex; gap: 12px; margin-top: 10px; padding-top: 10px;
  border-top: 1px solid var(--border);
}
.bn-client-meta-item { font-size: 10px; color: var(--text3); font-family: var(--ff); }
.bn-client-meta-val { font-family: var(--fm); font-weight: 600; color: var(--text2); }

/* ── Client card action buttons (+ Estimate / History / Delete) ─────── */
[data-testid="stHorizontalBlock"]:has(button[data-testid="stBaseButton-secondary"])
  [data-testid="stColumn"] .stButton > button,
.bn-client-card + div .stButton > button,
.bn-client-card ~ [data-testid="stHorizontalBlock"] .stButton > button {
  padding: 4px 8px !important;
  font-size: 11px !important;
  border-radius: 6px !important;
  min-height: 28px !important;
  height: 28px !important;
  line-height: 1 !important;
  font-family: var(--ff) !important;
}

/* ── Estimate rows ────────────────────────────────────────────────── */
.bn-estimate-row {
  display: flex; align-items: center; gap: 12px; padding: 12px 16px;
  border-bottom: 1px solid var(--border); cursor: pointer;
  transition: background .15s;
}
.bn-estimate-row:hover { background: var(--bg3); }
.bn-estimate-row:last-child { border-bottom: none; }
.bn-est-ver {
  background: var(--accent); color: #fff; font-size: 10px; font-weight: 700;
  font-family: var(--fm); padding: 3px 8px; border-radius: 6px; flex-shrink: 0;
}
.bn-est-info { flex: 1; min-width: 0; }
.bn-est-name { font-size: 12px; font-weight: 600; color: var(--text); font-family: var(--ff); }
.bn-est-meta {
  font-size: 10px; color: var(--text3); font-family: var(--fm); margin-top: 2px;
}
.bn-est-cost {
  font-size: 13px; font-weight: 700; font-family: var(--fm);
  color: var(--accent); flex-shrink: 0;
}
.bn-est-actions { display: flex; gap: 6px; flex-shrink: 0; }

/* ── Tag ──────────────────────────────────────────────────────────── */
.bn-tag {
  display: inline-block; font-size: 9px; font-weight: 700; font-family: var(--fm);
  text-transform: uppercase; letter-spacing: .4px;
  padding: 2px 6px; border-radius: 4px; margin-right: 4px;
}
.bn-tag.saas { background: var(--accent-lt); color: var(--accent); }
.bn-tag.onprem { background: var(--success-lt); color: var(--success); }

/* ── Mode buttons ─────────────────────────────────────────────────── */
.bn-mode-btns { display: flex; gap: 8px; margin-bottom: 16px; }
.bn-mode-btn {
  flex: 1; padding: 14px; border-radius: 10px;
  border: 1px solid var(--border2); background: var(--bg3);
  cursor: pointer; transition: all .25s; text-align: center;
}
.bn-mode-btn:hover { border-color: var(--accent); background: var(--bg2); }
.bn-mode-btn.active {
  border-color: var(--accent); background: var(--accent-lt);
  box-shadow: 0 0 0 1px var(--accent);
}
.bn-mode-btn-icon { font-size: 18px; margin-bottom: 6px; }
.bn-mode-btn-label {
  font-size: 12px; font-weight: 600; color: var(--text); display: block;
  font-family: var(--ff);
}
.bn-mode-btn-sub {
  font-size: 10px; color: var(--text3); display: block; margin-top: 2px;
  font-family: var(--ff);
}

/* ── Cost summary bands ───────────────────────────────────────────── */
.bn-cost-summary {
  display: grid; grid-template-columns: repeat(3, 1fr);
  gap: 1px; background: var(--border);
  border-radius: 12px; overflow: hidden; margin-bottom: 16px;
}
.bn-cost-band { background: var(--bg2); padding: 20px; text-align: center; }
.bn-cost-band-label {
  font-size: 10px; font-weight: 700; text-transform: uppercase;
  letter-spacing: .6px; color: var(--text3); margin-bottom: 6px;
  font-family: var(--ff);
}
.bn-cost-band-value {
  font-size: 26px; font-weight: 700; font-family: var(--fm);
  color: var(--text); letter-spacing: -1px;
}
.bn-cost-band-sub {
  font-size: 10px; color: var(--text3); font-family: var(--fm); margin-top: 3px;
}

/* ── Bar track (progress bars) ────────────────────────────────────── */
.bn-bar-row {
  display: flex; align-items: center; gap: 12px; padding: 6px 0;
}
.bn-bar-row-label {
  font-size: 11px; color: var(--text2); width: 150px; flex-shrink: 0;
  font-weight: 500; font-family: var(--ff);
}
.bn-bar-track {
  flex: 1; height: 6px; background: var(--bg3); border-radius: 3px; overflow: hidden;
}
.bn-bar-fill {
  height: 100%; border-radius: 3px;
  animation: barGrow .9s .3s ease both; animation-fill-mode: forwards;
}
.bn-bar-row-val {
  font-size: 11px; font-family: var(--fm); color: var(--text);
  width: 80px; text-align: right; flex-shrink: 0; font-weight: 600;
}

/* ── Feed items ───────────────────────────────────────────────────── */
.bn-feed-item {
  display: flex; gap: 11px; padding: 11px 16px;
  border-bottom: 1px solid var(--border);
  cursor: pointer; transition: background .15s, transform .15s; align-items: flex-start;
}
.bn-feed-item:hover { background: var(--bg3); transform: translateX(3px); }
.bn-feed-item:last-child { border-bottom: none; }
.bn-feed-icon {
  width: 28px; height: 28px; border-radius: 8px; flex-shrink: 0;
  display: flex; align-items: center; justify-content: center; font-size: 12px;
}

/* ── PUPM panel ───────────────────────────────────────────────────── */
.bn-pupm-value {
  font-size: 36px; font-weight: 700; font-family: var(--fm); color: var(--purple);
}

/* ── Alert banner ─────────────────────────────────────────────────── */
.bn-alert-banner {
  display: flex; align-items: center; gap: 12px; padding: 12px 16px;
  border-radius: 10px; border: 1px solid; margin-bottom: 16px;
}
.bn-alert-banner.warn {
  background: linear-gradient(135deg,rgba(217,119,6,.06),rgba(217,119,6,.03));
  border-color: rgba(217,119,6,.25); color: var(--warn);
}
.bn-alert-banner.info {
  background: var(--info-lt); border-color: rgba(8,145,178,.25); color: var(--info);
}
.bn-alert-banner.success {
  background: var(--success-lt); border-color: rgba(22,163,74,.25); color: var(--success);
}

/* ── Login card ───────────────────────────────────────────────────── */
.bn-login-shell {
  min-height: 90vh; display: flex; align-items: center; justify-content: center;
}
.bn-login-card {
  background: var(--bg2); border: 1px solid var(--border); border-radius: 16px;
  padding: 36px 32px; width: 100%; max-width: 400px; box-shadow: var(--shadow3);
  animation: fadeUp .5s ease both;
}
.bn-login-logo {
  display: flex; align-items: center; gap: 10px; margin-bottom: 28px;
}
.bn-login-logo-icon {
  width: 36px; height: 36px; background: var(--accent); border-radius: 10px;
  display: flex; align-items: center; justify-content: center;
  color: #fff; font-size: 16px; font-weight: 700; flex-shrink: 0;
}
.bn-login-logo-text { font-size: 16px; font-weight: 700; color: var(--text); letter-spacing: -.4px; }
.bn-login-logo-sub {
  font-size: 9px; color: var(--text3); letter-spacing: .5px; text-transform: uppercase;
}
.bn-login-title {
  font-size: 18px; font-weight: 700; color: var(--text); margin-bottom: 4px; letter-spacing: -.3px;
  font-family: var(--ff);
}
.bn-login-sub { font-size: 12px; color: var(--text2); margin-bottom: 24px; font-family: var(--ff); }
.bn-login-hint {
  margin-top: 20px; padding-top: 16px; border-top: 1px solid var(--border);
  display: flex; justify-content: space-between; align-items: center;
}
.bn-login-hint-text { font-size: 10px; color: var(--text3); font-family: var(--fm); }

/* ── Data table ───────────────────────────────────────────────────── */
.bn-data-table { width: 100%; border-collapse: collapse; background: var(--bg2) !important; color: var(--text) !important; }
.bn-data-table th {
  font-size: 10px; font-weight: 700; letter-spacing: .6px; color: var(--text3);
  text-transform: uppercase; padding: 8px 16px; border-bottom: 1px solid var(--border);
  text-align: left; font-family: var(--ff); background: var(--bg3) !important;
}
.bn-data-table tr { cursor: pointer; transition: background .15s; }
.bn-data-table tr:hover td { background: var(--bg3); }
.bn-data-table td {
  padding: 10px 16px; border-bottom: 1px solid var(--border);
  font-size: 12px; color: var(--text); font-family: var(--ff); background: var(--bg2) !important;
}
.bn-data-table tr:last-child td { border-bottom: none; }
.bn-data-table .mono { font-family: var(--fm); color: var(--text2); }

/* ── Empty state ──────────────────────────────────────────────────── */
.bn-empty-state { text-align: center; padding: 40px 20px; color: var(--text3); }
.bn-empty-icon { font-size: 32px; margin-bottom: 12px; opacity: .4; }
.bn-empty-title { font-size: 13px; font-weight: 600; color: var(--text2); margin-bottom: 4px; }
.bn-empty-sub { font-size: 11px; color: var(--text3); }

/* ── Success banner ───────────────────────────────────────────────── */
.bn-success-banner {
  background: var(--success-lt); border: 1px solid rgba(22,163,74,.25);
  border-radius: 10px; padding: 12px 18px; margin-bottom: 1.5rem;
  display: flex; align-items: center; gap: 12px;
}

/* ── Env chips ────────────────────────────────────────────────────── */
.bn-env-row { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 10px; }
.bn-env-chip {
  display: flex; align-items: center; gap: 6px; padding: 6px 12px;
  border-radius: 8px; border: 1px solid var(--border2); background: var(--bg3);
  cursor: pointer; transition: all .25s; font-size: 11px; font-weight: 600;
  color: var(--text2); font-family: var(--ff);
}
.bn-env-chip:hover { border-color: var(--accent); color: var(--text); }
.bn-env-chip.active {
  border-color: var(--accent); background: var(--accent-lt); color: var(--accent);
}

/* ── Divider ──────────────────────────────────────────────────────── */
.bn-divider { height: 1px; background: var(--border); margin: 20px 0; }

/* ── Shimmer ──────────────────────────────────────────────────────── */
.bn-shimmer {
  background: linear-gradient(90deg, var(--bg3) 25%, var(--bg2) 50%, var(--bg3) 75%);
  background-size: 200% 100%; animation: shimmer 1.5s infinite; border-radius: 6px;
}

/* ── Legacy compat: protect color classes ─────────────────────────── */
.bn-panel, .bn-metric-card, .bn-client-card, .bn-estimate-row,
.bn-cost-band, .bn-feed-item, .bn-alert-banner {
  color: var(--text) !important;
}
</style>
"""


def inject_theme():
    st.markdown(THEME_CSS, unsafe_allow_html=True)


def page_header(customer_name: str = "", client_mode: str = ""):
    """Render a clean breadcrumb-style client + mode indicator."""
    mode_badge = ""
    if client_mode == "saas":
        mode_badge = '<span class="bn-badge accent">☁️ SaaS — PostgreSQL</span>'
    elif client_mode == "onprem":
        mode_badge = '<span class="bn-badge success">🏢 On-Premise</span>'

    if customer_name:
        st.markdown(f"""
        <div style="margin-bottom:1.25rem; display:flex; align-items:center; gap:10px;">
            <span style="color:var(--text2); font-size:0.88rem; font-family:var(--ff);">Client:</span>
            <span style="color:var(--text); font-weight:700; font-size:1rem; font-family:var(--ff);">{_html.escape(customer_name)}</span>
            &nbsp;·&nbsp; {mode_badge}
        </div>
        """, unsafe_allow_html=True)
    elif mode_badge:
        st.markdown(f"<div style='margin-bottom:1rem;'>{mode_badge}</div>",
                    unsafe_allow_html=True)


def section_title(icon: str, title: str, subtitle: str = ""):
    """Render a section label with accent line, icon and optional subtitle."""
    sub = (f"<div style='font-size:11px;color:var(--text2);margin-top:3px;"
           f"font-family:var(--ff);'>{subtitle}</div>") if subtitle else ""
    st.markdown(f"""
    <div style='margin-bottom:1rem;'>
      <div class='bn-section-label'>{icon} {title}</div>
      {sub}
    </div>
    """, unsafe_allow_html=True)


def kpi_row(items: list):
    """items = list of (label, value, sub, variant)
    variant = '' | 'accent' | 'success' | 'warn' | 'danger' | 'purple' | 'info'
    """
    cards_html = ""
    for label, value, sub, variant in items:
        cards_html += f"""
        <div class="bn-metric-card {variant}">
          <div class="bn-metric-label">{label}</div>
          <div class="bn-metric-value">{value}</div>
          <div class="bn-metric-delta flat">{sub}</div>
        </div>"""
    st.markdown(f'<div class="bn-metrics">{cards_html}</div>', unsafe_allow_html=True)


def cost_banner(monthly: float, annual: float, five_yr: float):
    st.markdown(f"""
    <div class="bn-cost-summary">
      <div class="bn-cost-band">
        <div class="bn-cost-band-label">Monthly</div>
        <div class="bn-cost-band-value">${monthly:,.0f}</div>
        <div class="bn-cost-band-sub">Production</div>
      </div>
      <div class="bn-cost-band">
        <div class="bn-cost-band-label">Annual Y1</div>
        <div class="bn-cost-band-value">${annual:,.0f}</div>
        <div class="bn-cost-band-sub">with environments</div>
      </div>
      <div class="bn-cost-band">
        <div class="bn-cost-band-label">5-Year Total</div>
        <div class="bn-cost-band-value">${five_yr:,.0f}</div>
        <div class="bn-cost-band-sub">4% inflation/yr</div>
      </div>
    </div>
    """, unsafe_allow_html=True)


def divider():
    st.markdown('<div class="bn-divider"></div>', unsafe_allow_html=True)