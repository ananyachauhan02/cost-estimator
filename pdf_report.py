"""
pdf_report.py — BusinessNext AWS Cost Estimator
────────────────────────────────────────────────
Beautiful multi-page PDF pricing report using ReportLab.

Sections:
  Cover · Executive Summary · Node Distribution · AWS Cost Breakdown
  5-Year Forecast · Environment Pricing · PUPM Analysis · Assumptions
"""
from __future__ import annotations
import os
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    BaseDocTemplate, Frame, NextPageTemplate, PageBreak, PageTemplate,
    Paragraph, Spacer, Table, TableStyle, KeepTogether,
)
from reportlab.platypus.flowables import HRFlowable
from reportlab.pdfgen import canvas as rl_canvas

# ── Palette ───────────────────────────────────────────────────────────────
INK        = colors.HexColor("#0A0E1A")
NAVY       = colors.HexColor("#0F1629")
NAVY2      = colors.HexColor("#1C2E5C")
AZURE      = colors.HexColor("#2563EB")
AZURE_L    = colors.HexColor("#3B82F6")
AZURE_BG   = colors.HexColor("#EFF6FF")
AZURE_BG2  = colors.HexColor("#DBEAFE")
VIOLET     = colors.HexColor("#7C3AED")
VIOLET_BG  = colors.HexColor("#F5F3FF")
TEAL       = colors.HexColor("#0D9488")
TEAL_BG    = colors.HexColor("#F0FDFA")
TEAL_BG2   = colors.HexColor("#CCFBF1")
GOLD       = colors.HexColor("#D97706")
GOLD_BG    = colors.HexColor("#FFFBEB")
GOLD_BG2   = colors.HexColor("#FDE68A")
RED        = colors.HexColor("#DC2626")
RED_BG     = colors.HexColor("#FEF2F2")
GREEN      = colors.HexColor("#16A34A")
WHITE      = colors.white
GRAY1      = colors.HexColor("#F8FAFC")
GRAY2      = colors.HexColor("#F1F5F9")
GRAY3      = colors.HexColor("#E2E8F0")
GRAY4      = colors.HexColor("#94A3B8")
GRAY5      = colors.HexColor("#64748B")
GRAY6      = colors.HexColor("#475569")
DARK       = colors.HexColor("#1E293B")

W, H   = A4
MARGIN = 1.6 * cm
CW     = W - 2 * MARGIN      # content width

# ── Style factory ─────────────────────────────────────────────────────────
_BASE = getSampleStyleSheet()["Normal"]

def sty(name, **kw):
    d = dict(fontName="Helvetica", fontSize=9, textColor=DARK,
             leading=13, parent=_BASE)
    d.update(kw)
    return ParagraphStyle(name, **d)

S_TITLE    = sty("title",   fontName="Helvetica-Bold", fontSize=28, textColor=WHITE,   alignment=TA_CENTER, leading=34)
S_SUBTITLE = sty("sub",     fontName="Helvetica",      fontSize=13, textColor=colors.HexColor("#93C5FD"), alignment=TA_CENTER)
S_META     = sty("meta",    fontName="Helvetica",      fontSize=9,  textColor=GRAY4,   alignment=TA_CENTER)
S_SEC      = sty("sec",     fontName="Helvetica-Bold", fontSize=14, textColor=WHITE,   leading=18)
S_H2       = sty("h2",      fontName="Helvetica-Bold", fontSize=11, textColor=AZURE,   spaceBefore=10, spaceAfter=4)
S_H3       = sty("h3",      fontName="Helvetica-Bold", fontSize=9.5,textColor=DARK,    spaceBefore=6,  spaceAfter=2)
S_BODY     = sty("body",    fontSize=9,  textColor=GRAY6,  leading=13)
S_BOLD     = sty("bold",    fontName="Helvetica-Bold", fontSize=9,  textColor=DARK)
S_SMALL    = sty("small",   fontSize=7.5,textColor=GRAY4,  leading=11)
S_TH       = sty("th",      fontName="Helvetica-Bold", fontSize=8,  textColor=WHITE,   alignment=TA_CENTER, leading=11)
S_TD       = sty("td",      fontSize=8,  textColor=DARK,  leading=11)
S_TDC      = sty("tdc",     fontSize=8,  textColor=DARK,  alignment=TA_CENTER, leading=11)
S_TDR      = sty("tdr",     fontName="Helvetica-Bold", fontSize=8, textColor=DARK, alignment=TA_RIGHT, leading=11)
S_MONEY    = sty("money",   fontName="Helvetica-Bold", fontSize=8,  textColor=DARK,  alignment=TA_RIGHT, leading=11)
S_NOTE     = sty("note",    fontSize=8,  textColor=GRAY6,  leading=12)
S_KPI_V    = sty("kpiv",    fontName="Helvetica-Bold", fontSize=20, alignment=TA_CENTER, leading=24)
S_KPI_L    = sty("kpil",    fontSize=7.5,textColor=GRAY5,  alignment=TA_CENTER, leading=10)
S_KPI_S    = sty("kpis",    fontSize=7,  textColor=GRAY4,  alignment=TA_CENTER, leading=9)
S_FOOTER   = sty("ftr",     fontSize=7,  textColor=GRAY4,  alignment=TA_CENTER)

def P(t, s=None):  return Paragraph(str(t), s or S_BODY)
def SP(h=4):       return Spacer(1, h)
def HR(c=GRAY3, w=0.5): return HRFlowable(width="100%", thickness=w, color=c, spaceAfter=3, spaceBefore=3)

def fmt(v, d=0):
    if v is None: return "—"
    try:
        f = float(v)
        return f"${f:,.{d}f}" if d else f"${f:,.0f}"
    except: return "—"

def fmt2(v): return fmt(v, 2)

# ══════════════════════════════════════════════════════════════════════════
# NUMBERED CANVAS  (fixed page-number tracking)
# ══════════════════════════════════════════════════════════════════════════
class NumberedCanvas(rl_canvas.Canvas):
    """Tracks page count then stamps header + footer on every non-cover page."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._page_num   = 0
        self._all_pages  = []          # list of (page_num, saved_dict)

    def showPage(self):
        self._page_num += 1
        # snapshot only the keys we need — avoid comparing huge dicts
        self._all_pages.append((self._page_num, dict(self.__dict__)))
        self._startPage()

    def save(self):
        total = len(self._all_pages)
        for pnum, state in self._all_pages:
            self.__dict__.update(state)
            if pnum > 1:           # skip cover
                self._stamp(pnum, total)
            super().showPage()
        super().save()

    def _stamp(self, pnum, total):
        self.saveState()
        # ── Header ──────────────────────────────────────────────
        self.setFillColor(NAVY)
        self.rect(0, H - 1.1*cm, W, 1.1*cm, fill=1, stroke=0)
        # tri-colour accent stripe
        for col, x_frac, w_frac in [(AZURE, 0, 0.4), (VIOLET, 0.4, 0.3), (TEAL, 0.7, 0.3)]:
            self.setFillColor(col)
            self.rect(W*x_frac, H - 1.1*cm, W*w_frac, 0.14*cm, fill=1, stroke=0)
        self.setFont("Helvetica-Bold", 7.5)
        self.setFillColor(WHITE)
        self.drawString(MARGIN, H - 0.73*cm, "BusinessNext  Cost Estimator  ·  Pricing Report")
        self.setFont("Helvetica", 7.5)
        self.setFillColor(GRAY4)
        self.drawRightString(W - MARGIN, H - 0.73*cm,
                             f"Confidential  ·  {datetime.today().strftime('%d %b %Y')}")
        # ── Footer ──────────────────────────────────────────────
        self.setFillColor(GRAY2)
        self.rect(0, 0, W, 0.85*cm, fill=1, stroke=0)
        self.setStrokeColor(GRAY3)
        self.setLineWidth(0.4)
        self.line(MARGIN, 0.85*cm, W - MARGIN, 0.85*cm)
        self.setFont("Helvetica", 7)
        self.setFillColor(GRAY4)
        self.drawString(MARGIN, 0.27*cm, "Internal Use Only  ·  BusinessNext Platform")
        self.setFont("Helvetica-Bold", 7)
        self.setFillColor(AZURE)
        self.drawRightString(W - MARGIN, 0.27*cm, f"Page {pnum} of {total}")
        self.restoreState()


# ══════════════════════════════════════════════════════════════════════════
# REUSABLE COMPONENTS
# ══════════════════════════════════════════════════════════════════════════

def section_header(title, subtitle="", color=AZURE):
    hdr_style = TableStyle([
        ("BACKGROUND",   (0,0),(-1,-1), NAVY),
        ("TOPPADDING",   (0,0),(-1,-1), 9),
        ("BOTTOMPADDING",(0,0),(-1,-1), 9),
        ("LEFTPADDING",  (0,0),(-1,-1), 12),
        ("RIGHTPADDING", (0,0),(-1,-1), 12),
        ("LINEABOVE",    (0,0),(-1,0),  2.5, color),
    ])
    elems = [
        SP(8),
        Table([[P(f"  {title}", S_SEC)]], colWidths=[CW], style=hdr_style),
    ]
    if subtitle:
        elems.append(P(f"  {subtitle}",
                       sty("shsub", fontSize=7.5, textColor=GRAY4, spaceBefore=2, spaceAfter=5)))
    return elems


def kpi_strip(items):
    """items = [(label, value, sublabel, colour), ...]"""
    n   = len(items)
    cw  = CW / n
    vals = [P(v, sty(f"kv{i}", fontName="Helvetica-Bold", fontSize=17,
                     textColor=c, alignment=TA_CENTER, leading=21))
            for i, (_, v, __, c) in enumerate(items)]
    lbls = [P(l, S_KPI_L) for l, *_ in items]
    subs = [P(s, S_KPI_S) for _, __, s, ___ in items]

    ts = TableStyle([
        ("BACKGROUND",    (0,0),(-1,-1), WHITE),
        ("BOX",           (0,0),(-1,-1), 0.4, GRAY3),
        ("INNERGRID",     (0,0),(-1,-1), 0.4, GRAY3),
        ("TOPPADDING",    (0,0),(-1,0),  10),
        ("BOTTOMPADDING", (0,2),(-1,2),  8),
        ("TOPPADDING",    (0,1),(-1,2),  2),
    ])
    for idx, (_, __, ___, c) in enumerate(items):
        ts.add("LINEABOVE", (idx,0), (idx,0), 3, c)
    return Table([vals, lbls, subs], colWidths=[cw]*n, style=ts)


def info_card(pairs, fill=AZURE_BG, accent=AZURE):
    rows = [[P(k, S_BOLD), P(str(v), S_BODY)] for k, v in pairs]
    ts = TableStyle([
        ("ROWBACKGROUNDS", (0,0),(-1,-1), [fill, WHITE]),
        ("TOPPADDING",     (0,0),(-1,-1), 4),
        ("BOTTOMPADDING",  (0,0),(-1,-1), 4),
        ("LEFTPADDING",    (0,0),(-1,-1), 8),
        ("RIGHTPADDING",   (0,0),(-1,-1), 8),
        ("LINEABOVE",      (0,0),(-1,0),  2, accent),
        ("GRID",           (0,0),(-1,-1), 0.3, GRAY3),
    ])
    return Table(rows, colWidths=[CW*0.36, CW*0.64], style=ts)


def data_table(headers, rows, col_widths, accent=AZURE,
               alt=None, money_cols=None, center_cols=None):
    money_cols  = money_cols  or []
    center_cols = center_cols or []
    alt_bg      = alt or AZURE_BG

    def cell(val, ci, hdr=False):
        if hdr:  return P(val, S_TH)
        if ci in money_cols:  return P(val, S_TDR)
        if ci in center_cols: return P(val, S_TDC)
        return P(val, S_TD)

    tdata = [[cell(h, i, True) for i, h in enumerate(headers)]]
    for r in rows:
        tdata.append([cell(str(v), i) for i, v in enumerate(r)])

    ts = TableStyle([
        ("BACKGROUND",    (0,0),(-1,0),  NAVY),
        ("ROWBACKGROUNDS",(0,1),(-1,-1), [WHITE, alt_bg]),
        ("TOPPADDING",    (0,0),(-1,-1), 4),
        ("BOTTOMPADDING", (0,0),(-1,-1), 4),
        ("LEFTPADDING",   (0,0),(-1,-1), 5),
        ("RIGHTPADDING",  (0,0),(-1,-1), 5),
        ("GRID",          (0,0),(-1,-1), 0.3, GRAY3),
        ("LINEABOVE",     (0,0),(-1,0),  2,   accent),
    ])
    return Table(tdata, colWidths=col_widths, style=ts, repeatRows=1)


def mini_bar_chart(yearly, label_key, value_key, bar_color, canvas_w, canvas_h=90):
    """Draw a simple horizontal bar chart inline using a Table of coloured cells."""
    if not yearly: return SP(4)
    vals  = [float(y.get(value_key, 0) or 0) for y in yearly]
    labs  = [str(y.get(label_key, "")) for y in yearly]
    maxv  = max(vals) if vals else 1
    bar_w = canvas_w * 0.55   # bar column width
    rows  = []
    for lbl, val in zip(labs, vals):
        ratio  = val / maxv if maxv else 0
        filled = int(ratio * 40)   # 40 "cells" wide
        empty  = 40 - filled
        bar_cell = Table(
            [[" " * filled + " " * empty]],
            colWidths=[bar_w],
            style=TableStyle([
                ("BACKGROUND",   (0,0),(-1,-1), WHITE),
                ("LINEBELOW",    (0,0),(-1,-1), 0, WHITE),
            ])
        )
        # Use a progress-bar look: coloured rect inside a grey track
        bar_inner = Table(
            [[""]],
            colWidths=[bar_w * ratio if ratio > 0.01 else 0.5],
            style=TableStyle([
                ("BACKGROUND", (0,0),(-1,-1), bar_color),
                ("TOPPADDING", (0,0),(-1,-1), 6),
                ("BOTTOMPADDING",(0,0),(-1,-1), 6),
            ])
        )
        rows.append([
            P(lbl, sty("bl", fontSize=8, textColor=DARK, alignment=TA_RIGHT)),
            bar_inner,
            P(fmt(val), sty("bv", fontName="Helvetica-Bold", fontSize=8,
                            textColor=bar_color, alignment=TA_LEFT)),
        ])
    ts = TableStyle([
        ("TOPPADDING",    (0,0),(-1,-1), 2),
        ("BOTTOMPADDING", (0,0),(-1,-1), 2),
        ("LEFTPADDING",   (0,0),(-1,-1), 4),
        ("RIGHTPADDING",  (0,0),(-1,-1), 4),
        ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
        ("LINEBELOW",     (0,0),(-1,-1), 0.2, GRAY3),
    ])
    return Table(rows, colWidths=[2.4*cm, bar_w, 2.6*cm], style=ts)


def cost_band(label, monthly, annual, five_yr, accent=AZURE):
    """A coloured summary band showing 3 key figures."""
    ts = TableStyle([
        ("BACKGROUND",    (0,0),(-1,-1), accent),
        ("TOPPADDING",    (0,0),(-1,-1), 10),
        ("BOTTOMPADDING", (0,0),(-1,-1), 10),
        ("LEFTPADDING",   (0,0),(-1,-1), 12),
        ("RIGHTPADDING",  (0,0),(-1,-1), 12),
        ("INNERGRID",     (0,0),(-1,-1), 0.3, colors.HexColor("#FFFFFF40")),
    ])
    items = [
        [P("Monthly", sty("cl", fontSize=7, textColor=colors.HexColor("#FFFFFF99"), alignment=TA_CENTER)),
         P("Annual",  sty("cl", fontSize=7, textColor=colors.HexColor("#FFFFFF99"), alignment=TA_CENTER)),
         P("5-Year",  sty("cl", fontSize=7, textColor=colors.HexColor("#FFFFFF99"), alignment=TA_CENTER))],
        [P(fmt(monthly), sty("cv", fontName="Helvetica-Bold", fontSize=15, textColor=WHITE, alignment=TA_CENTER, leading=18)),
         P(fmt(annual),  sty("cv", fontName="Helvetica-Bold", fontSize=15, textColor=WHITE, alignment=TA_CENTER, leading=18)),
         P(fmt(five_yr), sty("cv", fontName="Helvetica-Bold", fontSize=15, textColor=WHITE, alignment=TA_CENTER, leading=18))],
    ]
    return Table(items, colWidths=[CW/3]*3, style=ts)


# ══════════════════════════════════════════════════════════════════════════
# MAIN ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════
def generate_pdf_report(
    pricing:      dict | None,
    distribution: dict | None,
    metrics:      dict,
    env_pricing:  dict | None,
    customer:     str = "Bank",
    client_mode:  str = "saas",
    output_path:  str = "reports/pricing_report.pdf",
    gcp_pricing:  dict | None = None,
    comparison:   dict | None = None,
) -> str:
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    today      = datetime.today().strftime("%d %B %Y")
    mode_label = ("SaaS — BusinessNext Hosted" if client_mode == "saas"
                  else "On-Premise — Client Hosted")
    dist       = distribution or {}
    pricing    = pricing or {}
    env_pricing= env_pricing or {}

    # ── Document ──────────────────────────────────────────────────────────
    doc = BaseDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=1.25*cm, bottomMargin=1.0*cm,
        title=f"Pricing Report — {customer}",
        author="BusinessNext Platform",
    )

    cover_frame   = Frame(0, 0, W, H, leftPadding=0, rightPadding=0,
                          topPadding=0, bottomPadding=0)
    content_frame = Frame(MARGIN, 0.95*cm, CW, H - 2.2*cm,
                          leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)

    def _cover_bg(c, doc):
        # Full dark BG
        c.setFillColor(INK)
        c.rect(0, 0, W, H, fill=1, stroke=0)
        # Hero panel
        c.setFillColor(NAVY2)
        c.rect(0, H * 0.48, W, H * 0.52 - 0.5*cm, fill=1, stroke=0)
        # Top tri-stripe
        for col, x, ww in [(AZURE, 0, W/3), (VIOLET, W/3, W/3), (TEAL, 2*W/3, W/3)]:
            c.setFillColor(col)
            c.rect(x, H - 0.5*cm, ww, 0.5*cm, fill=1, stroke=0)
        # Accent divider below hero
        c.setFillColor(AZURE)
        c.rect(0, H * 0.48, W, 0.22*cm, fill=1, stroke=0)
        # Decorative circles
        c.setFillColor(colors.HexColor("#1E3A8A"))
        c.circle(W * 0.87, H * 0.28, 3.2*cm, fill=1, stroke=0)
        c.setFillColor(colors.HexColor("#0F766E"))
        c.circle(W * 0.10, H * 0.18, 1.8*cm, fill=1, stroke=0)
        c.setFillColor(colors.HexColor("#4C1D95"))
        c.circle(W * 0.92, H * 0.68, 1.2*cm, fill=1, stroke=0)
        # Bottom bar
        c.setFillColor(colors.HexColor("#060810"))
        c.rect(0, 0, W, 1.8*cm, fill=1, stroke=0)
        c.setFont("Helvetica", 6.5)
        c.setFillColor(GRAY4)
        c.drawCentredString(W/2, 0.65*cm,
            "BUSINESSNEXT PLATFORM  ·  AWS COST ESTIMATOR  ·  INTERNAL USE ONLY")

    cover_tpl   = PageTemplate(id="cover",   frames=[cover_frame],   onPage=_cover_bg)
    content_tpl = PageTemplate(id="content", frames=[content_frame])
    doc.addPageTemplates([cover_tpl, content_tpl])

    story = []

    # ══════════════════════════════════════════════════════════════════════
    # COVER
    # ══════════════════════════════════════════════════════════════════════
    story.append(NextPageTemplate("cover"))
    story.append(SP(H * 0.10))

    story.append(P("☁  BusinessNext",
                   sty("cl", fontName="Helvetica", fontSize=11,
                       textColor=colors.HexColor("#93C5FD"), alignment=TA_CENTER)))
    story.append(SP(10))
    story.append(P("Cost Estimator", S_TITLE))
    story.append(SP(4))
    story.append(P("Pricing &amp; Infrastructure Report", S_SUBTITLE))
    story.append(SP(28))

    # Customer name card
    cname_style = TableStyle([
        ("BACKGROUND",    (0,0),(-1,-1), colors.HexColor("#1E3A5F")),
        ("BOX",           (0,0),(-1,-1), 1,   AZURE),
        ("LINEABOVE",     (0,0),(-1,0),  3,   AZURE),
        ("TOPPADDING",    (0,0),(-1,-1), 14),
        ("BOTTOMPADDING", (0,0),(-1,-1), 14),
        ("LEFTPADDING",   (0,0),(-1,-1), 20),
        ("RIGHTPADDING",  (0,0),(-1,-1), 20),
    ])
    story.append(Table(
        [[P(f"<b>{customer}</b>",
           sty("cn", fontName="Helvetica-Bold", fontSize=22,
               textColor=WHITE, alignment=TA_CENTER))]],
        colWidths=[W * 0.68], style=cname_style, hAlign="CENTER"
    ))
    story.append(SP(22))

    # Meta row
    meta_ts = TableStyle([
        ("TOPPADDING",    (0,0),(-1,-1), 4),
        ("BOTTOMPADDING", (0,0),(-1,-1), 4),
    ])
    story.append(Table([[
        P(f"<b>Mode:</b>  {mode_label}",    sty("m1", fontSize=8.5, textColor=GRAY4, alignment=TA_CENTER)),
        P(f"<b>Date:</b>  {today}",         sty("m2", fontSize=8.5, textColor=GRAY4, alignment=TA_CENTER)),
        P("<b>Inflation:</b>  4% / yr",     sty("m3", fontSize=8.5, textColor=GRAY4, alignment=TA_CENTER)),
    P(f"<b>AWS Region:</b>  {(pricing or {}).get('region', 'us-east-1')}",
      sty("m4", fontSize=8.5, textColor=GRAY4, alignment=TA_CENTER)),
    ]], colWidths=[W/4]*4, style=meta_ts))

    story.append(NextPageTemplate("content"))
    story.append(PageBreak())

    # ══════════════════════════════════════════════════════════════════════
    # SECTION 1 — EXECUTIVE SUMMARY
    # ══════════════════════════════════════════════════════════════════════
    story += section_header("Executive Summary",
                            "High-level cost overview and infrastructure snapshot")
    story.append(SP(6))

    if client_mode == "saas" and pricing:
        monthly = pricing.get("total_monthly_usd", 0)
        annual  = pricing.get("total_annual_usd",  0)
        five_yr = pricing.get("inflation_forecast", {}).get("five_year_total", 0)
        infr    = pricing.get("inflation_rate", 0.04)
        named_u = int(metrics.get("total_named_users", 0) or 0)

        story.append(kpi_strip([
            ("Monthly Cost",  fmt(monthly), "Production + environments", AZURE),
            ("Annual Cost",   fmt(annual),  "Year 1 total",              VIOLET),
            ("5-Year Total",  fmt(five_yr), f"At {infr*100:.0f}% inflation/yr", TEAL),
            ("Named Users",   f"{named_u:,}" if named_u else "—",
                              "Year 1 licensed",                          GOLD),
        ]))
        story.append(SP(8))

        # Big cost band
        story.append(cost_band("", monthly, annual, five_yr, AZURE))

    else:
        wn = metrics.get("total_workernodes", 0) or 0
        vc = metrics.get("total_vcpus_workernode", 0) or 0
        rm = metrics.get("total_memory_workernode_gb", 0) or 0
        db = (metrics.get("postgres_ram_gb", 0) or
              metrics.get("sql_server_ram_gb", 0) or
              metrics.get("oracle_ram_gb", 0) or 0)
        story.append(kpi_strip([
            ("Worker Nodes", str(int(wn)), "Total compute nodes",  AZURE),
            ("vCPUs",        str(int(vc)), "Total virtual CPUs",   VIOLET),
            ("RAM (GB)",     str(int(rm)), "Total memory",         TEAL),
            ("DB RAM (GB)",  str(int(db)), "Database memory",      GOLD),
        ]))

    story.append(SP(10))
    story.append(P("Project Details", S_H2))
    story.append(info_card([
        ("Customer / Bank",       customer),
        ("Client Mode",           mode_label),
        ("Database Type",         metrics.get("db_type", "PostgreSQL")),
        ("Total Named Users",     f"{int(metrics.get('total_named_users',0) or 0):,}"),
        ("Concurrent Users",      f"{int((metrics.get('total_named_users',0) or 0)*0.3):,}  (30% of named)"),
        ("Mobile Users",          f"{int(metrics.get('mobile_users',0) or 0):,}"),
        ("Worker Nodes",          str(int(metrics.get('total_workernodes',0) or 0))),
        ("Total vCPUs (worker)",  str(int(metrics.get('total_vcpus_workernode',0) or 0))),
        ("Total RAM GB (worker)", f"{int(metrics.get('total_memory_workernode_gb',0) or 0)} GB"),
        ("Data Size",             f"{int(metrics.get('data_size_gb',0) or 0)} GB"),
        ("Estimate Date",         today),
    ]))

    story.append(PageBreak())

    # ══════════════════════════════════════════════════════════════════════
    # SECTION 2 — NODE DISTRIBUTION
    # ══════════════════════════════════════════════════════════════════════
    story += section_header("Node Distribution", "AI-assisted infrastructure architecture", TEAL)
    story.append(SP(6))

    all_roles = (dist.get("worker_nodes", []) +
                 dist.get("db_nodes",     []) +
                 dist.get("fixed_roles",  []))

    summ = dist.get("summary", {})
    story.append(info_card([
        ("Total Worker Nodes",   summ.get("total_worker_nodes", "—")),
        ("Total DB Nodes",       summ.get("total_db_nodes",     "—")),
        ("Fixed / Managed Roles",len(dist.get("fixed_roles",   []))),
        ("Confidence",           str(summ.get("confidence","—")).title()),
    ], fill=TEAL_BG, accent=TEAL))
    story.append(SP(8))

    if all_roles:
        rows = []
        for r in all_roles:
            rows.append([
                r.get("category", "—"),
                r.get("label", "—"),
                str(r.get("nodes", "—")),
                r.get("instance_family", "—"),
                str(r.get("vcpu_per_node", "—") or "—"),
                str(r.get("ram_per_node",  "—") or "—"),
                r.get("pricing_model", "On Demand"),
            ])
        story.append(data_table(
            ["Category", "Role / Service", "Nodes", "Instance Fam.", "vCPU/node", "RAM GB/node", "Model"],
            rows,
            col_widths=[2.4*cm, 5.0*cm, 1.3*cm, 2.8*cm, 1.6*cm, 1.8*cm, 1.9*cm],
            accent=TEAL, alt=TEAL_BG, center_cols=[2, 4, 5, 6]
        ))

    story.append(PageBreak())

    # ══════════════════════════════════════════════════════════════════════
    # SECTION 3 — AWS COST BREAKDOWN
    # ══════════════════════════════════════════════════════════════════════
    if client_mode == "saas" and pricing:
        story += section_header("AWS Cost Breakdown",
                                "Service-by-service monthly and annual costs")
        story.append(SP(6))

        priced_roles = pricing.get("priced_roles", [])
        fixed_costs  = pricing.get("fixed_costs",  {}) or {}

        if priced_roles:
            story.append(P("Compute &amp; Database Roles", S_H2))
            rows = []
            for r in priced_roles:
                if not r.get("monthly_usd"): continue
                rows.append([
                    r.get("category", "—"),
                    r.get("label", "—"),
                    str(r.get("nodes", "—")),
                    r.get("instance_type", "—"),
                    fmt2(r.get("hourly_usd", 0)),
                    fmt(r.get("monthly_usd", 0)),
                    fmt(r.get("annual_usd",  0)),
                ])
            if rows:
                story.append(data_table(
                    ["Category", "Role", "Nodes", "Instance", "$/hr", "$/month", "$/year"],
                    rows,
                    col_widths=[2.2*cm, 4.4*cm, 1.2*cm, 3.0*cm, 1.6*cm, 2.3*cm, 2.1*cm],
                    accent=AZURE, alt=AZURE_BG, money_cols=[4,5,6], center_cols=[2]
                ))
            story.append(SP(8))

        if fixed_costs:
            story.append(P("Fixed &amp; Managed Services", S_H2))
            fixed_rows = []
            for k, v in fixed_costs.items():
                if isinstance(v, dict):
                    fixed_rows.append([
                        k.replace("_"," ").title(),
                        v.get("description","—"),
                        fmt(v.get("monthly_usd",0)),
                        fmt(v.get("annual_usd",0)),
                    ])
            if fixed_rows:
                story.append(data_table(
                    ["Service", "Description", "$/month", "$/year"],
                    fixed_rows,
                    col_widths=[3.2*cm, 8.5*cm, 2.2*cm, 2.9*cm],
                    accent=VIOLET, alt=VIOLET_BG, money_cols=[2,3]
                ))
            story.append(SP(8))

        # Cost summary
        story.append(P("Cost Summary", S_H2))
        story.append(info_card([
            ("Total Monthly (Production)",   fmt(pricing.get("total_monthly_usd",0))),
            ("Total Annual (Year 1)",         fmt(pricing.get("total_annual_usd",0))),
            ("5-Year Total (with inflation)", fmt(pricing.get("inflation_forecast",{}).get("five_year_total",0))),
            ("Inflation Rate Applied",        f"{pricing.get('inflation_rate',0.04)*100:.0f}%"),
        ], fill=GOLD_BG, accent=GOLD))

        story.append(PageBreak())

        # ══════════════════════════════════════════════════════════════════
        # SECTION 4 — 5-YEAR FORECAST
        # ══════════════════════════════════════════════════════════════════
        story += section_header("5-Year Inflation Forecast",
                                "Cost projection at 4% annual inflation")
        story.append(SP(6))

        forecast = pricing.get("inflation_forecast", {})
        yearly   = forecast.get("yearly", [])

        if yearly:
            # Table
            rows = []
            cumul = 0
            for yr in yearly:
                cumul += float(yr.get("annual_usd", 0) or 0)
                rows.append([
                    f"Year {yr.get('year','?')}",
                    f"{float(yr.get('multiplier',1)):.4f}×",
                    fmt(yr.get("monthly_usd",0)),
                    fmt(yr.get("annual_usd",0)),
                    fmt(cumul),
                ])
            story.append(data_table(
                ["Year", "Multiplier", "Monthly Cost", "Annual Cost", "Cumulative Total"],
                rows,
                col_widths=[2.2*cm, 2.8*cm, 3.8*cm, 3.8*cm, 4.2*cm],
                accent=GOLD, alt=GOLD_BG, money_cols=[2,3,4], center_cols=[0,1]
            ))
            story.append(SP(8))

            # Visual bar chart (annual costs)
            story.append(P("Annual Cost Trend", S_H2))
            story.append(mini_bar_chart(
                yearly, "year", "annual_usd", GOLD, CW
            ))
            story.append(SP(8))

            total = forecast.get("five_year_total", 0)
            story.append(info_card([
                ("Total 5-Year Investment",  fmt(total)),
                ("Average Annual Cost",      fmt(float(total)/5 if total else 0)),
                ("Average Monthly Cost",     fmt(float(total)/60 if total else 0)),
                ("Year-over-Year Growth",    "4.0% (inflation) applied from Year 2"),
            ], fill=GOLD_BG, accent=GOLD))

        story.append(PageBreak())

    # ══════════════════════════════════════════════════════════════════════
    # SECTION 5 — ENVIRONMENT PRICING
    # ══════════════════════════════════════════════════════════════════════
    if env_pricing:
        story += section_header("Environment Pricing",
                                "Pre-Prod / SIT / UAT and DR environment costs")
        story.append(SP(6))

        preprod = env_pricing.get("preprod_sit_uat")
        dr      = env_pricing.get("dr")

        if preprod:
            env_mult  = preprod.get("env_multiplier", 1)
            env_names = preprod.get("env_names", [])
            base_mo   = round(preprod.get("monthly_usd", 0) / env_mult, 2) if env_mult else preprod.get("monthly_usd", 0)
            base_yr   = round(preprod.get("annual_usd",  0) / env_mult, 2) if env_mult else preprod.get("annual_usd",  0)

            lbl = f"Environments: {', '.join(env_names)}" if env_names else "Pre-Prod / SIT / UAT"
            story.append(P(lbl, S_H2))

            if env_mult > 1:
                story.append(info_card([
                    ("Environments Selected",   f"{env_mult}  —  {', '.join(env_names)}"),
                    ("Base Cost per Env / mo",  fmt(base_mo)),
                    ("Base Cost per Env / yr",  fmt(base_yr)),
                    ("Calculation",             f"{env_mult} envs  ×  {fmt(base_mo)}/mo  =  {fmt(preprod.get('monthly_usd', 0))}/mo total"),
                ], fill=AZURE_BG2, accent=AZURE_L))
                story.append(SP(6))

            story.append(cost_band("", preprod.get("monthly_usd", 0),
                                   preprod.get("annual_usd", 0), 0, AZURE_L))
            story.append(SP(6))
            pp_roles = preprod.get("priced_roles", [])
            if pp_roles:
                rows = [[
                    r.get("category","—"), r.get("label","—"),
                    str(r.get("nodes","—")), r.get("instance_type","—"),
                    fmt(r.get("monthly_usd",0)),
                ] for r in pp_roles if r.get("monthly_usd",0)]
                if rows:
                    story.append(data_table(
                        ["Category","Role","Nodes","Instance","$/month"],
                        rows,
                        col_widths=[2.6*cm, 5.8*cm, 1.4*cm, 4.4*cm, 2.6*cm],
                        accent=AZURE, alt=AZURE_BG, money_cols=[4], center_cols=[2]
                    ))

        if dr:
            story.append(SP(12))
            story.append(P("Disaster Recovery (DR) Environment", S_H2))
            five_yr_dr = dr.get("five_year_forecast", {}).get("five_year_total", 0)
            story.append(cost_band("", dr.get("monthly_usd",0),
                                   dr.get("annual_usd",0), five_yr_dr, RED))
            story.append(SP(6))
            dr_roles = dr.get("priced_roles", [])
            if dr_roles:
                rows = [[
                    r.get("category","—"), r.get("label","—"),
                    str(r.get("nodes","—")), r.get("instance_type","—"),
                    fmt(r.get("monthly_usd",0)),
                ] for r in dr_roles if r.get("monthly_usd",0)]
                if rows:
                    story.append(data_table(
                        ["Category","Role","Nodes","Instance","$/month"],
                        rows,
                        col_widths=[2.6*cm, 5.8*cm, 1.4*cm, 4.4*cm, 2.6*cm],
                        accent=RED, alt=RED_BG, money_cols=[4], center_cols=[2]
                    ))
            dr_yearly = dr.get("five_year_forecast",{}).get("yearly",[])
            if dr_yearly:
                story.append(SP(8))
                story.append(P("DR 5-Year Forecast", S_H3))
                rows = [[
                    f"Year {y.get('year','?')}",
                    f"{float(y.get('multiplier',1)):.4f}×",
                    fmt(y.get("monthly_usd",0)),
                    fmt(y.get("annual_usd",0)),
                ] for y in dr_yearly]
                story.append(data_table(
                    ["Year","Multiplier","$/month","$/year"],
                    rows,
                    col_widths=[2.4*cm, 3.4*cm, 5.4*cm, 5.6*cm],
                    accent=RED, alt=RED_BG, money_cols=[2,3], center_cols=[0,1]
                ))

        story.append(PageBreak())

    # ══════════════════════════════════════════════════════════════════════
    # SECTION 6 — PUPM ANALYSIS  (SaaS only)
    # ══════════════════════════════════════════════════════════════════════
    if client_mode == "saas" and pricing:
        story += section_header("PUPM Analysis",
                                "Price Per User Per Month — 5-year projection", GOLD)
        story.append(SP(6))

        INF_R    = pricing.get("inflation_rate", 0.04)
        base_mo  = pricing.get("total_monthly_usd", 0)
        named_u  = int(metrics.get("total_named_users", 0) or 8500)
        ot_perf  = float(metrics.get("one_time_perf_testing", 5000) or 5000)
        ot_migr  = float(metrics.get("one_time_migration",    5000) or 5000)
        ot_ms    = float(metrics.get("one_time_managed_svc",  1000) or 1000)

        dr_mo     = 0.0
        preprod_mo = 0.0
        if env_pricing:
            if env_pricing.get("dr"):
                dr_mo = float(env_pricing["dr"].get("monthly_usd", 0) or 0)
            if env_pricing.get("preprod_sit_uat"):
                preprod_mo = float(env_pricing["preprod_sit_uat"].get("monthly_usd", 0) or 0)

        # Security constants (fixed INR estimates)
        AIRTEL   = 500.0
        SOC_MACH = round(5000 / 12, 4)
        REQ4     = round(433.33 / 12, 4)
        REQ6     = round(666.67 / 12, 4)
        BUS_PCT  = 0.039127
        BUF_PCT  = 0.05
        MGMT_PCT = 0.30
        DISC     = 0.11

        pupm_rows = []
        pupm_chart_data = []
        for y in range(1, 6):
            mult     = (1 + INF_R) ** (y - 1)
            prod_dc  = round(base_mo * mult, 2)
            prod_dr  = round(dr_mo * mult, 2) if dr_mo else 0.0
            preprod  = round(preprod_mo * mult, 2) if preprod_mo else 0.0
            users_y  = int(named_u * (1.05 ** (y - 1)))
            ot_ms_y  = ot_ms if y == 1 else 0.0

            total_usage = prod_dc + prod_dr + preprod + AIRTEL + SOC_MACH + REQ4 + REQ6
            bus_sup     = round(total_usage * BUS_PCT, 2)
            platform_yr = round((total_usage + bus_sup) * 12, 2)
            buffer      = round(platform_yr * BUF_PCT, 2)
            total_aws   = round(platform_yr + buffer, 2)
            managed_svc = round(total_aws * MGMT_PCT + ot_ms_y, 2)
            total_cost  = round(total_aws + managed_svc + (ot_perf + ot_migr if y == 1 else 0), 2)
            discounted  = round(total_cost * (1 - DISC), 2)
            pupm        = round(discounted / 12 / users_y, 4) if users_y else 0

            pupm_rows.append([
                f"Year {y}",
                f"{users_y:,}",
                fmt(total_usage),
                fmt(platform_yr),
                fmt(total_aws),
                fmt(discounted),
                f"${pupm:.4f}",
            ])
            pupm_chart_data.append({"year": y, "pupm_annual": discounted})

        story.append(data_table(
            ["Year", "Named Users", "Monthly Usage", "Platform Annual",
             "AWS Total", "Discounted Cost", "PUPM"],
            pupm_rows,
            col_widths=[1.6*cm, 2.2*cm, 3.0*cm, 3.2*cm, 2.8*cm, 3.2*cm, 2.4*cm],
            accent=GOLD, alt=GOLD_BG, money_cols=[2,3,4,5,6], center_cols=[0,1]
        ))
        story.append(SP(10))

        # Discounted cost visual chart
        story.append(P("Discounted Annual Cost Trend", S_H2))
        story.append(mini_bar_chart(pupm_chart_data, "year", "pupm_annual", GOLD, CW))
        story.append(SP(10))

        story.append(P("Formula Applied", S_H2))
        story.append(info_card([
            ("Business Support",    "3.91% of Total Monthly Usage"),
            ("Buffer",              "5% of Total Platform Annual Cost"),
            ("Managed Services",    "30% of Total AWS Annual Cost"),
            ("Discount",            "11% off Total Cost"),
            ("PUPM",                "Discounted Annual Cost ÷ 12 ÷ Named Users"),
            ("User Growth",         "+5% per year (Year-over-Year)"),
            ("One-Time Costs (Y1)", f"Performance: {fmt(ot_perf)}  ·  Migration: {fmt(ot_migr)}  ·  Managed Setup: {fmt(ot_ms)}"),
        ], fill=GOLD_BG, accent=GOLD))

    # ══════════════════════════════════════════════════════════════════════
    # SECTION 7 — GCP PRICING  (when available)
    # ══════════════════════════════════════════════════════════════════════
    if client_mode == "saas" and gcp_pricing:
        story.append(PageBreak())
        story += section_header("GCP Compute Engine Pricing",
                                f"Google Cloud equivalent — {gcp_pricing.get('region_label', gcp_pricing.get('region',''))}",
                                color=colors.HexColor("#0F9D58"))
        story.append(SP(6))

        gcp_mo  = gcp_pricing.get("total_monthly_usd", 0)
        gcp_yr  = gcp_pricing.get("total_annual_usd",  0)
        gcp_5yr = gcp_pricing.get("inflation_forecast", {}).get("five_year_total", 0)

        story.append(cost_band("", gcp_mo, gcp_yr, gcp_5yr,
                               colors.HexColor("#0F9D58")))
        story.append(SP(8))

        gcp_roles = gcp_pricing.get("priced_roles", [])
        if gcp_roles:
            rows = []
            for r in gcp_roles:
                if not r.get("monthly_usd"): continue
                rows.append([
                    r.get("category", "—"),
                    r.get("label",    "—"),
                    str(r.get("nodes", "—")),
                    r.get("instance_type", "—"),
                    fmt2(r.get("hourly_usd",  0)),
                    fmt(r.get("monthly_usd", 0)),
                    fmt(r.get("annual_usd",  0)),
                ])
            if rows:
                story.append(data_table(
                    ["Category", "Role", "Nodes", "GCP Machine", "$/hr", "$/month", "$/year"],
                    rows,
                    col_widths=[2.2*cm, 4.4*cm, 1.2*cm, 3.0*cm, 1.6*cm, 2.3*cm, 2.1*cm],
                    accent=colors.HexColor("#0F9D58"),
                    alt=colors.HexColor("#E8F5E9"),
                    money_cols=[4, 5, 6], center_cols=[2]
                ))
        story.append(SP(8))

        # GCP 5-year forecast
        gcp_yearly = gcp_pricing.get("inflation_forecast", {}).get("yearly", [])
        if gcp_yearly:
            story.append(P("GCP 5-Year Forecast", S_H2))
            rows = []
            for yr in gcp_yearly:
                rows.append([
                    f"Year {yr.get('year','?')}",
                    f"{float(yr.get('multiplier',1)):.4f}×",
                    fmt(yr.get("monthly_usd", 0)),
                    fmt(yr.get("annual_usd",  0)),
                    fmt(yr.get("cumulative_usd", 0)),
                ])
            story.append(data_table(
                ["Year", "Multiplier", "Monthly Cost", "Annual Cost", "Cumulative"],
                rows,
                col_widths=[2.2*cm, 2.8*cm, 3.8*cm, 3.8*cm, 4.2*cm],
                accent=colors.HexColor("#0F9D58"), alt=colors.HexColor("#E8F5E9"),
                money_cols=[2, 3, 4], center_cols=[0, 1]
            ))

    # ══════════════════════════════════════════════════════════════════════
    # SECTION 8 — AWS vs GCP COMPARISON
    # ══════════════════════════════════════════════════════════════════════
    if client_mode == "saas" and comparison:
        story.append(PageBreak())
        story += section_header("AWS vs GCP Cost Comparison",
                                "Side-by-side cost analysis — same workload, two clouds",
                                color=VIOLET)
        story.append(SP(6))

        comp_s   = comparison.get("summary", {})
        aws_mo   = comp_s.get("aws_monthly", 0)
        gcp_mo   = comp_s.get("gcp_monthly", 0)
        aws_yr   = comp_s.get("aws_annual",  0)
        gcp_yr   = comp_s.get("gcp_annual",  0)
        aws_5yr  = comp_s.get("aws_5year",   0)
        gcp_5yr  = comp_s.get("gcp_5year",   0)
        cheaper  = comp_s.get("cheaper_monthly", "AWS")
        chp_5yr  = comp_s.get("cheaper_5year",   "AWS")
        diff_mo  = comp_s.get("diff_monthly", 0)
        diff_5yr = comp_s.get("diff_5year",   0)

        # Summary KPI strip
        story.append(kpi_strip([
            ("AWS Monthly",  fmt(aws_mo),  comp_s.get("aws_region", "us-east-1"),   AZURE),
            ("GCP Monthly",  fmt(gcp_mo),  comp_s.get("gcp_region", "us-central1"), colors.HexColor("#0F9D58")),
            ("Monthly Diff", fmt(diff_mo), f"{cheaper} is cheaper",                  GOLD),
            ("5-Yr Winner",  chp_5yr,      f"Saves {fmt(diff_5yr)}",                 VIOLET),
        ]))
        story.append(SP(8))

        story.append(info_card([
            ("AWS Annual",          fmt(aws_yr)),
            ("GCP Annual",          fmt(gcp_yr)),
            ("AWS 5-Year Total",    fmt(aws_5yr)),
            ("GCP 5-Year Total",    fmt(gcp_5yr)),
            ("Cheaper (Monthly)",   cheaper),
            ("Cheaper (5-Year)",    chp_5yr),
            ("5-Year Saving",       fmt(diff_5yr)),
        ], fill=VIOLET_BG, accent=VIOLET))
        story.append(SP(10))

        # Category comparison table
        cat_rows = comparison.get("category_comparison", [])
        if cat_rows:
            story.append(P("Category-Level Breakdown", S_H2))
            rows = []
            for r in cat_rows:
                rows.append([
                    r["category"],
                    fmt(r["aws_monthly"]),
                    fmt(r["gcp_monthly"]),
                    fmt(abs(r["diff"])),
                    f"{abs(r.get('pct_diff',0)):.1f}%",
                    r["cheaper"],
                ])
            story.append(data_table(
                ["Category", "AWS $/mo", "GCP $/mo", "Difference", "% Diff", "✔ Cheaper"],
                rows,
                col_widths=[4.6*cm, 2.6*cm, 2.6*cm, 2.6*cm, 1.8*cm, 2.6*cm],
                accent=VIOLET, alt=VIOLET_BG, money_cols=[1, 2, 3]
            ))
            story.append(SP(8))

        # Year-by-year comparison
        yr_rows = comparison.get("yearly_comparison", [])
        if yr_rows:
            story.append(P("5-Year Year-by-Year Comparison", S_H2))
            rows = []
            for yr in yr_rows:
                rows.append([
                    f"Year {yr['year']}",
                    fmt(yr["aws_monthly"]),
                    fmt(yr["gcp_monthly"]),
                    fmt(yr["aws_annual"]),
                    fmt(yr["gcp_annual"]),
                    fmt(yr["aws_cumulative"]),
                    fmt(yr["gcp_cumulative"]),
                    yr["cheaper"],
                ])
            story.append(data_table(
                ["Year", "AWS/mo", "GCP/mo", "AWS/yr", "GCP/yr", "AWS Cumul.", "GCP Cumul.", "Winner"],
                rows,
                col_widths=[1.5*cm, 2.2*cm, 2.2*cm, 2.5*cm, 2.5*cm, 2.8*cm, 2.8*cm, 1.7*cm],
                accent=VIOLET, alt=VIOLET_BG, money_cols=[1, 2, 3, 4, 5, 6],
                center_cols=[0, 7]
            ))

    # ══════════════════════════════════════════════════════════════════════
    # FINAL — Notes & Assumptions
    # ══════════════════════════════════════════════════════════════════════
    story.append(PageBreak())
    story += section_header("Notes & Assumptions",
                            "Detailed pricing basis, scope, and validity", GRAY4)
    story.append(SP(8))

    # ── 15-Day Validity Banner ────────────────────────────────────────────
    story.append(KeepTogether([
        Table([[
            P("⚠  Pricing Validity — 15 Days Only",
              sty("vt", fontName="Helvetica-Bold", fontSize=11, textColor=WHITE,
                  alignment=TA_CENTER, leading=14)),
        ]], colWidths=[CW], style=TableStyle([
            ("BACKGROUND",  (0,0),(-1,-1), RED),
            ("TOPPADDING",  (0,0),(-1,-1), 12),
            ("BOTTOMPADDING",(0,0),(-1,-1), 12),
            ("LEFTPADDING", (0,0),(-1,-1), 16),
            ("RIGHTPADDING",(0,0),(-1,-1), 16),
            ("LINEABOVE",   (0,0),(-1,0),  3, colors.HexColor("#7F1D1D")),
            ("BOX",         (0,0),(-1,-1), 0.6, colors.HexColor("#7F1D1D")),
        ])),
        SP(3),
        Table([[
            P(
                f"This estimate is valid for <b>15 calendar days</b> from the date of issue "
                f"(<b>{today}</b>). AWS On-Demand prices, instance availability, and currency "
                f"exchange rates are subject to change without notice. A revised estimate must "
                f"be requested if requirements change or the validity period lapses.",
                sty("vb", fontSize=9, textColor=colors.HexColor("#7F1D1D"),
                    alignment=TA_CENTER, leading=13, spaceBefore=6, spaceAfter=6)),
        ]], colWidths=[CW], style=TableStyle([
            ("BACKGROUND",   (0,0),(-1,-1), RED_BG),
            ("BOX",          (0,0),(-1,-1), 0.6, RED),
            ("TOPPADDING",   (0,0),(-1,-1), 8),
            ("BOTTOMPADDING",(0,0),(-1,-1), 8),
            ("LEFTPADDING",  (0,0),(-1,-1), 14),
            ("RIGHTPADDING", (0,0),(-1,-1), 14),
        ])),
        SP(14),
    ]))

    # ── Pricing & Infrastructure Assumptions ─────────────────────────────
    story.append(P("Pricing & Infrastructure Assumptions", S_H2))
    story.append(SP(4))

    notes = [
        ("AWS Pricing Basis",
         "All prices are AWS On-Demand, Linux/UNIX, shared tenancy. No Reserved Instances or "
         "Savings Plans applied. Switching to 1-Year Reserved pricing typically reduces compute "
         "costs by 30-40%."),
        ("Region",
         f"Estimate uses region: {(pricing or {}).get('region', 'us-east-1')}. "
         "Costs vary by region — a regional multiplier is applied to the base us-east-1 rate."),
        ("Inflation Rate",
         "4% per annum applied to all compute and managed-service costs from Year 2 onwards, "
         "reflecting typical AWS price adjustments and currency exposure."),
        ("High Availability (AZ)",
         "Production and DR environments are architected as Multi-AZ (High Availability). "
         "Pre-Prod/SIT/UAT are Single-AZ to optimize costs while maintaining functional parity."),
        ("Security & Compliance Costs",
         "Fixed INR-converted estimates included: Airtel SOC $500/mo, SOC Machines Rs.30,000/yr, "
         "Req 4 Antivirus Rs.2,600/yr, Req 6 Data Discovery Rs.4,000/yr. These are not subject "
         "to AWS price changes."),
        ("Pre-Prod / SIT / UAT",
         "Environments sized at ~40% of Production infrastructure. PostgreSQL uses self-hosted "
         "EC2 (Patroni HA). SQL Server / Oracle use AWS Managed. Costs are additive and "
         "not included in the Production PUPM."),
        ("Disaster Recovery (DR)",
         "DR sized using a Pilot Light / Warm Standby model at ~50% of Production compute. "
         "Active-Active DR would approximately double the DR cost shown."),
        ("Managed Services",
         "Managed Services fees (30% of AWS annual total) cover platform monitoring, patching, "
         "incident management, and lifecycle support by the BusinessNext operations team."),
    ]

    for k, v in notes:
        story.append(KeepTogether([
            Table([[P(k, S_BOLD), P(v, S_NOTE)]],
                  colWidths=[3.8*cm, CW - 3.8*cm],
                  style=TableStyle([
                      ("TOPPADDING",    (0,0),(-1,-1), 5),
                      ("BOTTOMPADDING", (0,0),(-1,-1), 5),
                      ("LEFTPADDING",   (0,0),(-1,-1), 6),
                      ("RIGHTPADDING",  (0,0),(-1,-1), 6),
                      ("GRID",          (0,0),(-1,-1), 0.3, GRAY3),
                      ("ROWBACKGROUNDS",(0,0),(-1,-1), [GRAY1, WHITE]),
                  ])),
            SP(2),
        ]))

    # ── Scope of This Estimate ────────────────────────────────────────────
    story.append(SP(12))
    story.append(P("Scope of This Estimate", S_H2))
    story.append(SP(4))
    scope_items = [
        ("in",  "Production cloud infrastructure (compute, database, storage, networking)"),
        ("in",  "Pre-Production / SIT / UAT environments (if selected)"),
        ("in",  "Disaster Recovery environment (if selected)"),
        ("in",  "BusinessNext platform licensing and managed services"),
        ("in",  "One-time migration, performance testing, and managed-service setup (Year 1)"),
        ("out", "Application development or customisation effort"),
        ("out", "End-user device provisioning or on-site hardware"),
        ("out", "Third-party SaaS subscriptions (e.g. Salesforce, Twilio, Okta)"),
        ("out", "Data centre co-location or physical network charges"),
        ("out", "Regulatory compliance certification fees"),
    ]
    scope_rows = []
    for kind, text in scope_items:
        icon  = "Included" if kind == "in" else "Excluded"
        color = GREEN     if kind == "in" else RED
        scope_rows.append([
            P(f"<b>{icon}</b>",
              sty(f"si_{kind}", fontName="Helvetica-Bold", fontSize=8,
                  textColor=color, alignment=TA_CENTER)),
            P(text, sty("st", fontSize=8.5, textColor=DARK, leading=12)),
        ])
    story.append(Table(
        scope_rows,
        colWidths=[2.0*cm, CW - 2.0*cm],
        style=TableStyle([
            ("TOPPADDING",    (0,0),(-1,-1), 5),
            ("BOTTOMPADDING", (0,0),(-1,-1), 5),
            ("LEFTPADDING",   (0,0),(-1,-1), 6),
            ("RIGHTPADDING",  (0,0),(-1,-1), 6),
            ("GRID",          (0,0),(-1,-1), 0.3, GRAY3),
            ("ROWBACKGROUNDS",(0,0),(-1,-1), [WHITE, GRAY1]),
            ("VALIGN",        (0,0),(-1,-1), "MIDDLE"),
        ])
    ))

    # ── Legal Disclaimer ──────────────────────────────────────────────────
    story.append(SP(16))
    story.append(Table([[
        P(
            "<b>Legal Disclaimer</b><br/><br/>"
            "This document is prepared by BusinessNext for the exclusive use of the named client "
            "organisation. All cost figures are estimates based on current AWS/GCP published "
            "pricing and the inputs provided at the time of generation. Actual costs may vary "
            "depending on usage patterns, reserved-instance commitments, enterprise discount "
            "programmes, and any changes to cloud provider pricing.<br/><br/>"
            "This estimate does <b>not</b> constitute a binding commercial offer or contract. "
            "A formal Statement of Work (SOW) and Order Form must be executed prior to "
            "commencement of any services. BusinessNext reserves the right to revise this "
            "estimate upon receipt of updated requirements or upon expiry of the 15-day "
            "validity period.<br/><br/>"
            "<b>Confidentiality:</b> This document is CONFIDENTIAL. It must not be reproduced, "
            "distributed, or disclosed to any third party without prior written consent from "
            "BusinessNext.",
            sty("disc", fontSize=8, textColor=GRAY6, leading=12)),
    ]], colWidths=[CW], style=TableStyle([
        ("BACKGROUND",    (0,0),(-1,-1), GRAY2),
        ("BOX",           (0,0),(-1,-1), 0.4, GRAY3),
        ("LINEABOVE",     (0,0),(-1,0),  2, GOLD),
        ("TOPPADDING",    (0,0),(-1,-1), 10),
        ("BOTTOMPADDING", (0,0),(-1,-1), 10),
        ("LEFTPADDING",   (0,0),(-1,-1), 12),
        ("RIGHTPADDING",  (0,0),(-1,-1), 12),
    ])))

    story.append(SP(20))
    story.append(HR(GRAY3))
    story.append(P(
        f"Generated by BusinessNext Cost Estimator  ·  {today}  ·  Internal Use Only  ·  "
        f"Pricing valid for 15 days from {today}",
        S_FOOTER
    ))


    # ── Build ─────────────────────────────────────────────────────────────
    doc.build(story, canvasmaker=NumberedCanvas)
    return output_path