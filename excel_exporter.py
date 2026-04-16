"""
excel_exporter.py
─────────────────────────────────────────────────────────────
Generates two formatted Excel workbooks from pricing results:
  1. cloud_sizing.xlsx   — node distribution + architecture
  2. aws_pricing.xlsx    — 5-year cost forecast with inflation

Uses openpyxl with professional formatting per SKILL.md standards:
  Blue text  = hardcoded inputs
  Black text = formulas / calculations
  Green fill = section headers
─────────────────────────────────────────────────────────────
"""

from __future__ import annotations
import os
from datetime import datetime
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import (
    Alignment, Border, Font, GradientFill, PatternFill, Side
)
from openpyxl.utils import get_column_letter


# ── Style helpers ─────────────────────────────────────────────────────────

def _font(bold=False, size=11, color="000000", italic=False):
    return Font(name="Arial", bold=bold, size=size, color=color, italic=italic)

def _fill(hex_color):
    return PatternFill("solid", start_color=hex_color, fgColor=hex_color)

def _border():
    s = Side(style="thin", color="CCCCCC")
    return Border(left=s, right=s, top=s, bottom=s)

def _center():
    return Alignment(horizontal="center", vertical="center", wrap_text=True)

def _left():
    return Alignment(horizontal="left", vertical="center", wrap_text=True)

def _num_fmt(cell, fmt):
    cell.number_format = fmt

HEADER_FILL  = _fill("1F4E79")   # dark navy
SECTION_FILL = _fill("2E75B6")   # medium blue
ALT_FILL     = _fill("EBF3FB")   # light blue alternate row
TOTAL_FILL   = _fill("FFF2CC")   # yellow for totals
GREEN_FILL   = _fill("E2EFDA")   # light green for positives

def _header_row(ws, row, values, fill=None):
    for col, val in enumerate(values, 1):
        c = ws.cell(row=row, column=col, value=val)
        c.font      = _font(bold=True, color="FFFFFF", size=10)
        c.fill      = fill or _fill("1F4E79")
        c.alignment = _center()
        c.border    = _border()

def _data_row(ws, row, values, alt=False, bold=False, num_cols=None, total=False):
    fill = TOTAL_FILL if total else (_fill("EBF3FB") if alt else _fill("FFFFFF"))
    for col, val in enumerate(values, 1):
        c = ws.cell(row=row, column=col, value=val)
        c.font      = _font(bold=bold or total, size=10)
        c.fill      = fill
        c.alignment = _left() if col <= 2 else _center()
        c.border    = _border()
        if num_cols and col in num_cols and isinstance(val, (int, float)):
            c.number_format = '$#,##0.00'


def _set_col_widths(ws, widths: list):
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w


# ── Sheet 1: Cloud Sizing ─────────────────────────────────────────────────

def _build_cloud_sizing_sheet(wb: Workbook, distribution: dict, metrics: dict, customer: str):
    ws = wb.active
    ws.title = "Cloud Sizing"
    ws.sheet_view.showGridLines = False
    ws.freeze_panes = "A4"

    # ── Title block ───────────────────────────────────────────────────────
    ws.merge_cells("A1:J1")
    title = ws["A1"]
    title.value     = f"Cloud Sizing – Node Distribution  |  {customer}  |  {datetime.today().strftime('%d %b %Y')}"
    title.font      = _font(bold=True, size=13, color="FFFFFF")
    title.fill      = _fill("1F4E79")
    title.alignment = _center()
    ws.row_dimensions[1].height = 28

    ws.merge_cells("A2:J2")
    sub = ws["A2"]
    sub.value     = f"Total Worker Nodes: {distribution['summary']['total_worker_nodes']}   |   Total DB Nodes: {distribution['summary']['total_db_nodes']}   |   Confidence: {distribution['summary']['confidence'].title()}"
    sub.font      = _font(italic=True, size=10, color="FFFFFF")
    sub.fill      = _fill("2E75B6")
    sub.alignment = _center()
    ws.row_dimensions[2].height = 20

    # ── Headers ───────────────────────────────────────────────────────────
    headers = ["Category", "Service / Role", "Nodes", "Instance Family",
               "vCPU / Node", "RAM / Node (GB)", "Storage / Node (GB)",
               "Pricing Model", "Deployment", "Reasoning"]
    _header_row(ws, 3, headers)
    ws.row_dimensions[3].height = 32

    # ── Data: all roles combined ──────────────────────────────────────────
    all_roles = (
        distribution.get("worker_nodes", [])
        + distribution.get("db_nodes", [])
        + distribution.get("fixed_roles", [])
    )

    row = 4
    prev_cat = None
    for i, r in enumerate(all_roles):
        cat = r.get("category", "—")
        # Section separator when category changes
        if cat != prev_cat:
            ws.merge_cells(f"A{row}:J{row}")
            c = ws.cell(row=row, column=1, value=f"  {cat}")
            c.font      = _font(bold=True, size=10, color="FFFFFF")
            c.fill      = _fill("2E75B6")
            c.alignment = _left()
            c.border    = _border()
            ws.row_dimensions[row].height = 20
            row += 1
            prev_cat = cat

        vals = [
            cat,
            r.get("label", "—"),
            r.get("nodes", 0),
            r.get("instance_family", "—"),
            r.get("vcpu_per_node", "—") or "—",
            r.get("ram_per_node", "—")  or "—",
            r.get("storage_per_node_gb", 0) or "—",
            r.get("pricing_model") or "On Demand",
            "Self-Hosted" if any(db in r.get("role_key", "").lower() for db in ["pgsql", "oracle", "mssql"]) else "AWS Managed",
            r.get("reasoning", "—"),
        ]
        _data_row(ws, row, vals, alt=(i % 2 == 0))
        ws.row_dimensions[row].height = 18
        row += 1

    # ── Summary metrics block ─────────────────────────────────────────────
    row += 1
    ws.merge_cells(f"A{row}:J{row}")
    c = ws.cell(row=row, column=1, value="  Sizing Inputs (from Sizing Template)")
    c.font = _font(bold=True, size=10, color="FFFFFF")
    c.fill = _fill("1F4E79")
    c.alignment = _left()
    row += 1

    metric_pairs = [
        ("Total Worker Nodes",        metrics.get("total_workernodes", 0)),
        ("Total vCPUs (Worker)",       metrics.get("total_vcpus_workernode", 0)),
        ("Total RAM GB (Worker)",      metrics.get("total_memory_workernode_gb", 0)),
        (f"{metrics.get('db_type', 'PostgreSQL')} RAM GB", metrics.get("postgres_ram_gb", 0)),
        ("Data Size GB",               metrics.get("data_size_gb", 0)),
        ("S3 Size GB",                metrics.get("s3_size_gb", 0)),
    ]
    for i, (label, val) in enumerate(metric_pairs):
        _data_row(ws, row, [label, val, "", "", "", "", "", "", "", ""], alt=(i % 2 == 0))
        ws.cell(row=row, column=2).number_format = "#,##0"
        row += 1

    _set_col_widths(ws, [22, 40, 8, 22, 12, 16, 18, 16, 14, 45])


# ── Sheet 2: AWS Pricing ──────────────────────────────────────────────────

def _build_aws_pricing_sheet(wb: Workbook, pricing: dict, metrics: dict, customer: str):
    ws = wb.create_sheet("AWS Pricing")
    ws.sheet_view.showGridLines = False
    ws.freeze_panes = "A5"

    INFLATION = pricing.get("inflation_rate", 0.04)
    years     = 5

    # ── Title ─────────────────────────────────────────────────────────────
    total_cols = 3 + years + 1
    col_letter = get_column_letter(total_cols)
    ws.merge_cells(f"A1:{col_letter}1")
    t = ws["A1"]
    t.value     = f"AWS 5-Year Cost Forecast  |  {customer}  |  {datetime.today().strftime('%d %b %Y')}  |  Inflation: {INFLATION*100:.1f}%/yr"
    t.font      = _font(bold=True, size=13, color="FFFFFF")
    t.fill      = _fill("1F4E79")
    t.alignment = _center()
    ws.row_dimensions[1].height = 28

    ws.merge_cells(f"A2:{col_letter}2")
    s = ws["A2"]
    s.value     = f"Base Monthly: ${pricing['total_monthly_usd']:,.2f}  |  Annual Y1: ${pricing['total_annual_usd']:,.2f}  |  3-Year: ${pricing['total_3year_usd']:,.2f}"
    s.font      = _font(italic=True, size=10, color="FFFFFF")
    s.fill      = _fill("2E75B6")
    s.alignment = _center()
    ws.row_dimensions[2].height = 20

    # ── Column headers ────────────────────────────────────────────────────
    year_labels = [f"Year {y+1}" for y in range(years)]
    headers = ["Category", "Service / Role", "Instance Type", "Base Monthly (USD)"] + year_labels + ["5-Year Total"]
    _header_row(ws, 3, headers)
    ws.row_dimensions[3].height = 32

    # ── Inflation multipliers row ─────────────────────────────────────────
    mult_vals = ["", "", "Inflation Multiplier", "1.00"] + [f"={(1+INFLATION)**(y+1):.4f}" for y in range(years)] + [""]
    for col, val in enumerate(mult_vals, 1):
        c = ws.cell(row=4, column=col, value=val if not val.startswith("=") else None)
        if val.startswith("="):
            c.value = float(val[1:])
        c.font      = _font(italic=True, size=9, color="666666")
        c.fill      = _fill("F2F2F2")
        c.alignment = _center()
        c.border    = _border()
        if col >= 4:
            c.number_format = "0.0000"
    ws.row_dimensions[4].height = 16

    # ── Service rows ──────────────────────────────────────────────────────
    num_cols = set(range(4, 4 + years + 1 + 1))
    row = 5
    prev_cat = None

    priced_roles = sorted(
        pricing.get("priced_roles", []),
        key=lambda r: r.get("category", ""),
    )

    for i, r in enumerate(priced_roles):
        cat     = r.get("category", "Other")
        base    = r.get("monthly_usd", 0)
        if base == 0:
            continue

        # Category header
        if cat != prev_cat:
            ws.merge_cells(f"A{row}:{col_letter}{row}")
            c = ws.cell(row=row, column=1, value=f"  {cat}")
            c.font      = _font(bold=True, size=10, color="FFFFFF")
            c.fill      = _fill("2E75B6")
            c.alignment = _left()
            c.border    = _border()
            ws.row_dimensions[row].height = 18
            row += 1
            prev_cat = cat

        year_costs = [round(base * 12 * ((1 + INFLATION) ** y), 2) for y in range(years)]
        five_yr    = round(sum(year_costs), 2)

        vals = [cat, r.get("label", "—"), r.get("instance_type", "—"), base] + year_costs + [five_yr]
        _data_row(ws, row, vals, alt=(i % 2 == 0), num_cols=num_cols)
        ws.row_dimensions[row].height = 18
        row += 1

    # ── Category subtotals ────────────────────────────────────────────────
    row += 1
    ws.merge_cells(f"A{row}:{col_letter}{row}")
    c = ws.cell(row=row, column=1, value="  Category Subtotals")
    c.font = _font(bold=True, size=10, color="FFFFFF"); c.fill = _fill("1F4E79")
    c.alignment = _left(); c.border = _border()
    row += 1

    for i, (cat, base_monthly) in enumerate(sorted(pricing.get("category_totals", {}).items())):
        year_costs = [round(base_monthly * 12 * ((1 + INFLATION) ** y), 2) for y in range(years)]
        five_yr    = round(sum(year_costs), 2)
        vals = [cat, "All services", "—", base_monthly] + year_costs + [five_yr]
        _data_row(ws, row, vals, alt=(i % 2 == 0), num_cols=num_cols)
        row += 1

    # ── Grand total row ───────────────────────────────────────────────────
    base_monthly = pricing["total_monthly_usd"]
    year_costs   = [round(base_monthly * 12 * ((1 + INFLATION) ** y), 2) for y in range(years)]
    five_yr      = round(sum(year_costs), 2)
    vals = ["GRAND TOTAL", "", "", base_monthly] + year_costs + [five_yr]
    _data_row(ws, row, vals, total=True, num_cols=num_cols)
    ws.row_dimensions[row].height = 22

    # ── Assumptions block ─────────────────────────────────────────────────
    row += 2
    ws.merge_cells(f"A{row}:{col_letter}{row}")
    c = ws.cell(row=row, column=1, value="  Pricing Assumptions")
    c.font = _font(bold=True, size=10, color="FFFFFF"); c.fill = _fill("1F4E79")
    c.alignment = _left(); c.border = _border()
    row += 1

    a = pricing.get("assumptions", {})
    assumptions = [
        ("Region",             a.get("region", "us-east-1")),
        ("Inflation Rate/yr",  f"{INFLATION*100:.1f}%"),
        ("Hours/Month",        str(a.get("hours_per_month", 730))),
        ("Deployment",         a.get("deployment", "—")),
        ("OS",                 a.get("os", "Linux/RHEL")),
        ("EBS Type",           a.get("ebs_type", "gp3/io2")),
        ("Pricing Date",       a.get("pricing_date", "2026-03")),
        ("DB Hosting",         f"{metrics.get('db_type', 'PostgreSQL')} Hosting"),
    ]
    for i, (k, v) in enumerate(assumptions):
        for col, val in enumerate([k, v], 1):
            c = ws.cell(row=row, column=col, value=val)
            c.font      = _font(size=10, color="0000FF" if col == 2 else "000000")
            c.fill      = _fill("EBF3FB") if i % 2 == 0 else _fill("FFFFFF")
            c.alignment = _left()
            c.border    = _border()
        row += 1

    widths = [22, 40, 18, 18] + [16] * years + [16]
    _set_col_widths(ws, widths)


# ── Sheet 3: DB Selection ─────────────────────────────────────────────────

def _build_db_selection_sheet(wb: Workbook, db_selection: dict, customer: str):
    ws = wb.create_sheet("DB Selection")
    ws.sheet_view.showGridLines = False

    ws.merge_cells("A1:F1")
    t = ws["A1"]
    t.value     = f"Database Selection & Hosting Model  |  {customer}"
    t.font      = _font(bold=True, size=13, color="FFFFFF")
    t.fill      = _fill("1F4E79")
    t.alignment = _center()
    ws.row_dimensions[1].height = 28

    headers = ["Database", "Type", "Hosting Model", "AWS Service", "Estimated Monthly (USD)", "Rationale"]
    _header_row(ws, 2, headers)
    ws.row_dimensions[2].height = 28

    db_rows = [
        {
            "db":      "PostgreSQL",
            "type":    "Relational",
            "hosting": "Self-Hosted on EC2",
            "service": "EC2 r5.8xlarge × 2 + EBS io2",
            "monthly": db_selection.get("postgres_monthly", 0),
            "reason":  "PostgreSQL is open-source; self-hosted on EC2 avoids licensing premium. HA via Patroni + etcd.",
        },
        {
            "db":      "SQL Server",
            "type":    "Relational / Commercial",
            "hosting": "AWS Managed ",
            "service": "SQL Server Multi-AZ",
            "monthly": db_selection.get("sqlserver_monthly", 0),
            "reason":  "SQL Server requires Microsoft licensing; Managed handles patching, backups, and HA automatically.",
        },
        {
            "db":      "Oracle",
            "type":    "Relational / Commercial",
            "hosting": "AWS Managed ",
            "service": "Oracle Multi-AZ",
            "monthly": db_selection.get("oracle_monthly", 0),
            "reason":  "Oracle licensing is complex; Oracle reduces compliance risk and operational overhead.",
        },
        {
            "db":      "ElastiCache (Redis)",
            "type":    "In-Memory / Cache",
            "hosting": "AWS Managed",
            "service": "ElastiCache r6g.large × 2",
            "monthly": db_selection.get("elasticache_monthly", 0),
            "reason":  "Session store and API cache; always managed — no viable self-hosted alternative on AWS.",
        },
    ]

    for i, r in enumerate(db_rows):
        hosting_color = "E2EFDA" if "Self" in r["hosting"] else "FFF2CC"
        for col, val in enumerate([r["db"], r["type"], r["hosting"], r["service"], r["monthly"], r["reason"]], 1):
            c = ws.cell(row=3 + i, column=col, value=val)
            c.font      = _font(size=10)
            c.fill      = _fill(hosting_color)
            c.alignment = _left() if col != 5 else _center()
            c.border    = _border()
            if col == 5:
                c.number_format = '$#,##0.00'
        ws.row_dimensions[3 + i].height = 40

    # Legend
    row = 8
    ws.merge_cells(f"A{row}:F{row}")
    c = ws.cell(row=row, column=1, value="  Legend")
    c.font = _font(bold=True, size=10, color="FFFFFF"); c.fill = _fill("1F4E79")
    c.alignment = _left()
    row += 1

    for label, hex_c, desc in [
        ("Green",  "E2EFDA", "Self-Hosted on EC2 — lower cost, more control, requires DBA expertise"),
        ("Yellow", "FFF2CC", "AWS Managed — higher cost, zero ops overhead, commercial license compliance"),
    ]:
        c1 = ws.cell(row=row, column=1, value=label)
        c1.fill = _fill(hex_c); c1.font = _font(bold=True, size=10)
        c1.border = _border(); c1.alignment = _center()
        ws.merge_cells(f"B{row}:F{row}")
        c2 = ws.cell(row=row, column=2, value=desc)
        c2.fill = _fill(hex_c); c2.font = _font(size=10)
        c2.border = _border(); c2.alignment = _left()
        row += 1

    _set_col_widths(ws, [18, 26, 22, 30, 22, 55])




# ── Sheet: Pre-Prod / SIT / UAT ──────────────────────────────────────────

def _build_preprod_sheet(wb: Workbook, preprod: dict, db_type: str, customer: str):
    ws = wb.create_sheet("Pre-Prod SIT UAT")
    ws.sheet_view.showGridLines = False
    ws.freeze_panes = "A4"

    ws.merge_cells("A1:H1")
    t = ws["A1"]
    t.value     = f"Pre-Prod / SIT / UAT Environment  |  {customer}  |  DB: {db_type}"
    t.font      = _font(bold=True, size=13, color="FFFFFF")
    t.fill      = _fill("1F4E79"); t.alignment = _center()
    ws.row_dimensions[1].height = 28

    ws.merge_cells("A2:H2")
    s = ws["A2"]
    s.value     = f"Monthly: ${preprod['monthly_usd']:,.2f}   |   Annual: ${preprod['annual_usd']:,.2f}"
    s.font      = _font(italic=True, size=10, color="FFFFFF")
    s.fill      = _fill("2E75B6"); s.alignment = _center()
    ws.row_dimensions[2].height = 18

    headers = ["Category", "Service / Role", "Nodes", "Instance Type",
               "vCPU/Node", "RAM/Node (GB)", "Monthly (USD)", "Note"]
    _header_row(ws, 3, headers)
    ws.row_dimensions[3].height = 28

    row = 4
    prev_cat = None
    for i, r in enumerate(preprod.get("priced_roles", [])):
        if r.get("monthly_usd", 0) == 0:
            continue
        cat = r.get("category", "Other")
        if cat != prev_cat:
            ws.merge_cells(f"A{row}:H{row}")
            c = ws.cell(row=row, column=1, value=f"  {cat}")
            c.font = _font(bold=True, size=10, color="FFFFFF")
            c.fill = _fill("2E75B6"); c.alignment = _left(); c.border = _border()
            row += 1; prev_cat = cat

        vals = [cat, r.get("label","—"), r.get("nodes","—"),
                r.get("instance_type","—"), r.get("vcpu","—") or "—",
                r.get("ram","—") or "—", r.get("monthly_usd",0), r.get("note","—")]
        _data_row(ws, row, vals, alt=(i%2==0), num_cols={7})
        ws.cell(row=row, column=7).number_format = '$#,##0.00'
        row += 1

    # Total row
    _data_row(ws, row, ["TOTAL", "", "", "", "", "", preprod["monthly_usd"], ""], total=True, num_cols={7})
    ws.cell(row=row, column=7).number_format = '$#,##0.00'
    _set_col_widths(ws, [20, 45, 8, 22, 10, 14, 16, 40])


# ── Sheet: DR Environment ─────────────────────────────────────────────────

def _build_dr_sheet(wb: Workbook, dr: dict, db_type: str, customer: str):
    ws = wb.create_sheet("DR Environment")
    ws.sheet_view.showGridLines = False
    ws.freeze_panes = "A5"

    ws.merge_cells("A1:I1")
    t = ws["A1"]
    t.value     = f"Disaster Recovery Environment  |  {customer}  |  DB: {db_type}  |  Inflation: 4%/yr"
    t.font      = _font(bold=True, size=13, color="FFFFFF")
    t.fill      = _fill("1F4E79"); t.alignment = _center()
    ws.row_dimensions[1].height = 28

    five_yr = dr.get("five_year_forecast", {}).get("five_year_total", 0)
    ws.merge_cells("A2:I2")
    s = ws["A2"]
    s.value     = f"Monthly: ${dr['monthly_usd']:,.2f}   |   Annual: ${dr['annual_usd']:,.2f}   |   5-Year Total: ${five_yr:,.2f}"
    s.font      = _font(italic=True, size=10, color="FFFFFF")
    s.fill      = _fill("2E75B6"); s.alignment = _center()
    ws.row_dimensions[2].height = 18

    # 5-year forecast table
    ws.merge_cells("A3:I3")
    c = ws.cell(row=3, column=1, value="  5-Year DR Cost Forecast (4% inflation/year)")
    c.font = _font(bold=True, size=10, color="FFFFFF")
    c.fill = _fill("1F4E79"); c.alignment = _left(); c.border = _border()
    ws.row_dimensions[3].height = 18

    yr_headers = ["Year 1", "Year 2", "Year 3", "Year 4", "Year 5", "5-Year Total", "Inflation Factor Y1", "Inflation Factor Y5"]
    _header_row(ws, 4, [""] + yr_headers[:6] + ["Multiplier Y1","Multiplier Y5"])
    ws.row_dimensions[4].height = 28

    forecast = dr.get("five_year_forecast", {})
    yr_vals  = [forecast.get(f"year_{y}",{}).get("annual_usd",0) for y in range(1,6)]
    row_data = ["Annual DR Cost"] + yr_vals + [five_yr,
        f"{forecast.get('year_1',{}).get('multiplier',1):.4f}×",
        f"{forecast.get('year_5',{}).get('multiplier',1):.4f}×"]
    _data_row(ws, 5, row_data, num_cols=set(range(2,8)), total=True)
    for col in range(2, 8):
        ws.cell(row=5, column=col).number_format = '$#,##0.00'
    ws.row_dimensions[5].height = 22

    # Role breakdown
    row = 7
    ws.merge_cells(f"A{row}:I{row}")
    c = ws.cell(row=row, column=1, value="  Role-by-Role Breakdown")
    c.font = _font(bold=True, size=10, color="FFFFFF")
    c.fill = _fill("1F4E79"); c.alignment = _left(); c.border = _border()
    row += 1

    headers2 = ["Category","Service / Role","Nodes","Instance Type","vCPU/Node","RAM/Node","Monthly (USD)","Note",""]
    _header_row(ws, row, headers2)
    ws.row_dimensions[row].height = 28
    row += 1

    prev_cat = None
    for i, r in enumerate(dr.get("priced_roles", [])):
        if r.get("monthly_usd", 0) == 0:
            continue
        cat = r.get("category", "Other")
        if cat != prev_cat:
            ws.merge_cells(f"A{row}:I{row}")
            c = ws.cell(row=row, column=1, value=f"  {cat}")
            c.font = _font(bold=True, size=10, color="FFFFFF")
            c.fill = _fill("2E75B6"); c.alignment = _left(); c.border = _border()
            row += 1; prev_cat = cat

        vals = [cat, r.get("label","—"), r.get("nodes","—"),
                r.get("instance_type","—"), r.get("vcpu","—") or "—",
                r.get("ram","—") or "—", r.get("monthly_usd",0), r.get("note","—"), ""]
        _data_row(ws, row, vals, alt=(i%2==0), num_cols={7})
        ws.cell(row=row, column=7).number_format = '$#,##0.00'
        row += 1

    _data_row(ws, row, ["TOTAL","","","","","",dr["monthly_usd"],"",""], total=True, num_cols={7})
    ws.cell(row=row, column=7).number_format = '$#,##0.00'
    _set_col_widths(ws, [20, 45, 8, 22, 10, 14, 16, 40, 5])


# ── Sheet: PUPM Summary (Year-by-Year) ───────────────────────────────────

def _build_pupm_sheet(wb: Workbook, pricing: dict, env_pricing: dict | None,
                      metrics: dict, customer: str):
    """
    Builds the PUPM Summary sheet replicating the reference workbook format:

    Rows (per year column):
      BusinessNext section:
        - Production DC (monthly)
        - Production DR (monthly, if applicable)
        - Pre-Prod       (monthly, if applicable)
        - UAT            (blank — not separately priced)
        - SIT            (blank — not separately priced)
        - Performance Testing  [One-Time: $5,000]
        - Migration/Data Bootup [One-Time: $5,000]  ← Optional Component
      Security section:
        - Airtel SOC             $500/mo
        - SOC Machines           $416.67/mo  (Rs 30,000/unit/yr)
        - Req 4 – Antivirus & EDR  $36.11/mo  (Rs 2,600/unit/yr)
        - Req 6 – Data Discovery   $55.56/mo  (Rs 4,000/unit/yr)
        - Req 7 – DLP              $0
      ── Calculations ──
        Total Usage     = sum of all monthly costs
        Business Support = 3.91% of Total Usage
        Total Platform cost (Yearly) = (Total Usage + Business Support) × 12
        Buffer          = 5% of Total Platform cost
        Total cost (AWS) = Total Platform cost + Buffer
        Managed Services = 30% of Total cost AWS
        Total cost      = Total cost AWS + Managed Services
        Discount        = 11%
        Discounted cost = Total cost × (1 − 0.11)
        ── PUPM ──
        Users           = named users for that year
        PUPM            = Discounted cost / 12 / Users
    """
    ws = wb.create_sheet("PUPM Summary")
    ws.sheet_view.showGridLines = False
    ws.freeze_panes = "E4"

    INFLATION  = pricing.get("inflation_rate", 0.04)
    num_years  = 5

    # ── Derive yearly Production DC costs with inflation ──────────────────
    base_monthly  = pricing.get("total_monthly_usd", 0)

    # DR / Pre-Prod monthly
    dr_monthly     = 0.0
    preprod_monthly = 0.0
    if env_pricing:
        dr_data = env_pricing.get("dr")
        pp_data = env_pricing.get("preprod_sit_uat")
        if dr_data:
            dr_monthly = dr_data.get("monthly_usd", 0.0)
        if pp_data:
            preprod_monthly = pp_data.get("monthly_usd", 0.0)

    # Named users per year (grow at 5% YOY per app.py YOY settings)
    named_users_y1 = metrics.get("total_named_users",
                     metrics.get("named_users",
                     int(metrics.get("mobile_users", 0) / 0.30 * 1.0))) or 8500

    # ── One-time costs from user inputs (defaulting to $5000/$5000/$1000) ──
    ot_perf = float(metrics.get("one_time_perf_testing", 5000) or 5000)
    ot_migr = float(metrics.get("one_time_migration",    5000) or 5000)
    ot_ms   = float(metrics.get("one_time_managed_svc",  1000) or 1000)

    # Build per-year data
    years = []
    for y in range(1, num_years + 1):
        mult     = (1 + INFLATION) ** (y - 1)
        prod_dc  = round(base_monthly * mult, 2)
        prod_dr  = round(dr_monthly * mult, 2)  if dr_monthly  else 0.0
        preprod  = round(preprod_monthly * mult, 2) if preprod_monthly else 0.0
        users_y  = int(named_users_y1 * (1.05 ** (y - 1)))

        # Fixed security costs (INR-based, fixed in USD)
        airtel_soc  = 500.00
        soc_mach    = round(5000  / 12, 4)   # $5000/yr → $416.67/mo
        req4        = round(433.33 / 12, 4)  # Rs 2,600/unit/yr
        req6        = round(666.67 / 12, 4)  # Rs 4,000/unit/yr
        req7        = 0.0

        # One-time costs: only in Year 1, zero for subsequent years
        one_time_perf  = ot_perf if y == 1 else 0.0
        one_time_migr  = ot_migr if y == 1 else 0.0
        one_time_ms    = ot_ms   if y == 1 else 0.0
        one_time_total = one_time_perf + one_time_migr + one_time_ms

        total_usage = (prod_dc + prod_dr + preprod
                       + airtel_soc + soc_mach + req4 + req6 + req7)

        BUS_SUPPORT_PCT  = 0.039127
        BUFFER_PCT       = 0.05
        MANAGED_SVC_PCT  = 0.30
        DISCOUNT         = 0.11

        business_support   = round(total_usage * BUS_SUPPORT_PCT, 4)
        total_platform_yr  = round((total_usage + business_support) * 12, 4)
        buffer             = round(total_platform_yr * BUFFER_PCT, 4)
        total_aws          = round(total_platform_yr + buffer, 4)
        managed_svc        = round(total_aws * MANAGED_SVC_PCT, 4)
        total_cost         = round(total_aws + managed_svc + one_time_total, 4)
        discounted_cost    = round(total_cost * (1 - DISCOUNT), 4)
        pupm               = round(discounted_cost / 12 / users_y, 4) if users_y else 0

        years.append({
            "year":             y,
            "prod_dc":          prod_dc,
            "prod_dr":          prod_dr,
            "preprod":          preprod,
            "airtel_soc":       airtel_soc,
            "soc_mach":         soc_mach,
            "req4":             req4,
            "req6":             req6,
            "req7":             req7,
            "one_time_perf":    one_time_perf,
            "one_time_migr":    one_time_migr,
            "total_usage":      total_usage,
            "business_support": business_support,
            "total_platform_yr":total_platform_yr,
            "buffer":           buffer,
            "total_aws":        total_aws,
            "managed_svc":      managed_svc,
            "managed_svc_ot":   one_time_ms,
            "total_cost":       total_cost,
            "one_time_total":   one_time_total,
            "discounted_cost":  discounted_cost,
            "users":            users_y,
            "pupm":             pupm,
        })

    # ── Column layout ─────────────────────────────────────────────────────
    # A=Category, B=Line Item, C=Comments, D=One-Time ($), E..I = Y1..Y5 ($/month)
    _set_col_widths(ws, [16, 48, 30, 16, 16, 16, 16, 16, 16])

    # ── Title ─────────────────────────────────────────────────────────────
    last_col = get_column_letter(4 + num_years)
    ws.merge_cells(f"A1:{last_col}1")
    t = ws["A1"]
    t.value     = f"PUPM Summary – {num_years}-Year Cost Analysis  |  {customer}  |  {datetime.today().strftime('%d %b %Y')}  |  Inflation: {INFLATION*100:.1f}%/yr"
    t.font      = _font(bold=True, size=13, color="FFFFFF")
    t.fill      = _fill("1F4E79")
    t.alignment = _center()
    ws.row_dimensions[1].height = 28

    # ── Sub-title with PUPM range ─────────────────────────────────────────
    ws.merge_cells(f"A2:{last_col}2")
    pupm_range = f"PUPM Y1: ${years[0]['pupm']:,.2f}  →  PUPM Y{num_years}: ${years[-1]['pupm']:,.2f}   |   Discount: 11%  |  Managed Services: 30%"
    s = ws["A2"]
    s.value     = pupm_range
    s.font      = _font(italic=True, size=10, color="FFFFFF")
    s.fill      = _fill("2E75B6")
    s.alignment = _center()
    ws.row_dimensions[2].height = 18

    # ── Column headers ────────────────────────────────────────────────────
    hdrs = ["Category", "Line Item", "Comments", "One-Time Cost ($)"]
    hdrs += [f"Year {y}\n($/month)" for y in range(1, num_years + 1)]
    _header_row(ws, 3, hdrs)
    ws.row_dimensions[3].height = 36

    # ── Helper to write a section header row ─────────────────────────────
    def section_hdr(row_num, title, fill_hex="2E75B6"):
        ws.merge_cells(f"A{row_num}:{last_col}{row_num}")
        c = ws.cell(row=row_num, column=1, value=f"  {title}")
        c.font      = _font(bold=True, size=10, color="FFFFFF")
        c.fill      = _fill(fill_hex)
        c.alignment = _left()
        c.border    = _border()
        ws.row_dimensions[row_num].height = 20

    # ── Helper to write a data row ────────────────────────────────────────
    MONEY = '$#,##0.00'
    PCTFMT = '0.00%'

    def data_row(row_num, category, label, comment, one_time,
                 yr_vals, alt=False, bold=False, total=False,
                 is_pct=False, is_pupm=False):
        fill = TOTAL_FILL if total else (_fill("EBF3FB") if alt else _fill("FFFFFF"))
        if is_pupm:
            fill = _fill("D6E4F0")  # distinct light-blue highlight for PUPM

        cells_vals = [category, label, comment, one_time] + list(yr_vals)
        for col_i, val in enumerate(cells_vals, 1):
            c = ws.cell(row=row_num, column=col_i, value=val)
            c.font      = _font(bold=bold or total or is_pupm, size=10,
                                color="000000" if not (bold and col_i == 1) else "000000")
            c.fill      = fill
            c.border    = _border()
            c.alignment = _left() if col_i <= 3 else _center()
            if col_i == 4 and isinstance(val, (int, float)) and val:
                c.number_format = MONEY
            if col_i >= 5:
                if is_pct:
                    c.number_format = PCTFMT
                elif is_pupm:
                    c.number_format = '$#,##0.0000'
                elif isinstance(val, (int, float)):
                    c.number_format = MONEY

    def blank_row(row_num):
        for col_i in range(1, 5 + num_years):
            c = ws.cell(row=row_num, column=col_i, value="")
            c.fill   = _fill("FFFFFF")
            c.border = _border()
        ws.row_dimensions[row_num].height = 6

    # ── Build rows ────────────────────────────────────────────────────────
    r = 4

    # ── BUSINESSNEXT section ──────────────────────────────────────────────
    section_hdr(r, "BusinessNext"); r += 1

    data_row(r, "BusinessNext", "Production DC", "",
             "", [y["prod_dc"] for y in years], alt=False); r += 1

    if any(y["prod_dr"] for y in years):
        data_row(r, "", "Production DR", "",
                 "", [y["prod_dr"] for y in years], alt=True); r += 1

    if any(y["preprod"] for y in years):
        data_row(r, "", "Pre-Prod", "",
                 "", [y["preprod"] for y in years], alt=False); r += 1

    data_row(r, "", "UAT", "",  "", [""] * num_years, alt=True);  r += 1
    data_row(r, "", "SIT", "",  "", [""] * num_years, alt=False); r += 1

    data_row(r, "", "Performance Testing",
             "One-time — Year 1 only", years[0]["one_time_perf"],
             [""] * num_years, alt=True); r += 1

    data_row(r, "", "Migration / Data Bootup",
             "One-time — Year 1 only", years[0]["one_time_migr"],
             [""] * num_years, alt=False); r += 1

    blank_row(r); r += 1

    # ── SECURITY section ──────────────────────────────────────────────────
    section_hdr(r, "Security"); r += 1

    data_row(r, "Security", "Airtel SOC", "Infra for SOC machines",
             "", [y["airtel_soc"] for y in years], alt=False); r += 1
    data_row(r, "", "SOC Machines", "Rs. 30,000/unit/year",
             "", [y["soc_mach"] for y in years], alt=True); r += 1
    data_row(r, "", "Requirement 4 – Antivirus & EDR", "Rs. 2,600/unit/year",
             "", [y["req4"] for y in years], alt=False); r += 1
    data_row(r, "", "Requirement 6 – Data Discovery & Classification", "Rs. 4,000/unit/year",
             "", [y["req6"] for y in years], alt=True); r += 1
    data_row(r, "", "Requirement 7 – DLP", "",
             "", [y["req7"] for y in years], alt=False); r += 1

    blank_row(r); r += 1

    # ── CALCULATIONS section ──────────────────────────────────────────────
    section_hdr(r, "Calculations", fill_hex="1F4E79"); r += 1

    data_row(r, "", "Total Usage", "",
             "", [y["total_usage"] for y in years],
             bold=True, total=True); r += 1

    data_row(r, "", "Business Support (3.91% of Total Usage)", "",
             "", [y["business_support"] for y in years], alt=True); r += 1

    data_row(r, "", "Total Platform cost (Yearly cost)", "",
             sum(y["one_time_perf"] + y["one_time_migr"] for y in years[:1]),
             [y["total_platform_yr"] for y in years],
             bold=True); r += 1

    data_row(r, "", "Buffer (5%)", "",
             "", [y["buffer"] for y in years], alt=True); r += 1

    data_row(r, "", "Total cost (AWS)", "",
             sum(y["one_time_perf"] + y["one_time_migr"] for y in years[:1]),
             [y["total_aws"] for y in years],
             bold=True, total=True); r += 1

    data_row(r, "", "Managed Services (30% of AWS cost)", "",
             years[0]["managed_svc_ot"],
             [y["managed_svc"] for y in years], alt=True); r += 1

    data_row(r, "", "Total cost", "",
             sum(y["one_time_total"] for y in years[:1]),
             [y["total_cost"] for y in years],
             bold=True, total=True); r += 1

    data_row(r, "", "Discount", "",
             "", [0.11] * num_years, is_pct=True, alt=True); r += 1

    data_row(r, "", "Discounted cost", "",
             sum(y["one_time_total"] for y in years[:1]),
             [y["discounted_cost"] for y in years],
             bold=True, total=True); r += 1

    blank_row(r); r += 1

    # ── PUPM section ──────────────────────────────────────────────────────
    section_hdr(r, "PUPM Calculation", fill_hex="1F4E79"); r += 1

    data_row(r, "", "Named Users (YOY +5%)", "",
             "", [y["users"] for y in years], alt=False); r += 1

    # The star row
    data_row(r, "", "PUPM  (Price per User per Month)", "",
             "", [y["pupm"] for y in years],
             is_pupm=True, bold=True); r += 1

    ws.row_dimensions[r - 1].height = 26

    blank_row(r); r += 1

    # ── 5-Year PUPM trend table (visual summary) ──────────────────────────
    section_hdr(r, "5-Year PUPM Trend", fill_hex="2E75B6"); r += 1

    trend_hdrs = ["", "Metric"] + [f"Year {y}" for y in range(1, num_years + 1)] + ["5-Yr Avg"]
    for col_i, val in enumerate(trend_hdrs, 1):
        c = ws.cell(row=r, column=col_i, value=val)
        c.font = _font(bold=True, size=10, color="FFFFFF")
        c.fill = _fill("2E75B6"); c.border = _border(); c.alignment = _center()
    r += 1

    trend_rows = [
        ("Monthly Cost (Prod DC)",  [y["prod_dc"]  for y in years]),
        ("Total Monthly Usage",     [y["total_usage"] for y in years]),
        ("Discounted Cost (Annual)",[y["discounted_cost"] for y in years]),
        ("Named Users",             [y["users"] for y in years]),
        ("PUPM",                    [y["pupm"]  for y in years]),
    ]
    for t_i, (label, vals) in enumerate(trend_rows):
        avg = sum(vals) / len(vals)
        row_vals = ["", label] + vals + [avg]
        is_p = (label == "PUPM")
        fill = _fill("D6E4F0") if is_p else (_fill("EBF3FB") if t_i % 2 == 0 else _fill("FFFFFF"))
        for col_i, val in enumerate(row_vals, 1):
            c = ws.cell(row=r, column=col_i, value=val)
            c.font   = _font(bold=is_p, size=10)
            c.fill   = fill; c.border = _border()
            c.alignment = _left() if col_i == 2 else _center()
            if col_i >= 3 and isinstance(val, (int, float)):
                c.number_format = '$#,##0.0000' if is_p else MONEY
        r += 1

    # ── Footnotes ─────────────────────────────────────────────────────────
    r += 1
    notes = [
        "Notes:",
        "• PUPM = Price Per User Per Month = Discounted Annual Cost ÷ 12 ÷ Named Users",
        "• Business Support: 3.91% of Total Monthly Usage",
        "• Buffer: 5% of Total Platform Annual Cost",
        "• Managed Services: 30% of Total AWS Cost (Annual)",
        "• Discount: 11% applied to Total Cost",
        "• Production DC cost grows at inflation rate year-on-year",
        "• Named Users grow at 5% YOY",
        "• Performance Testing & Migration are one-time costs in Year 1 only",
    ]
    for note in notes:
        ws.merge_cells(f"A{r}:{last_col}{r}")
        c = ws.cell(row=r, column=1, value=note)
        c.font      = _font(italic=(note != "Notes:"), bold=(note == "Notes:"), size=9, color="595959")
        c.fill      = _fill("F2F2F2")
        c.alignment = _left()
        c.border    = _border()
        ws.row_dimensions[r].height = 16
        r += 1

# ── Public API ────────────────────────────────────────────────────────────

def generate_excel_reports(
    pricing:      dict,
    distribution: dict,
    metrics:      dict,
    customer:     str  = "Bank-Name",
    output_dir:   str  = "reports",
    env_pricing:  dict = None,
    db_type:      str  = "PostgreSQL",
    client_mode:  str  = "saas",
    gcp_pricing:  dict = None,
    comparison:   dict = None,
    years:        int  = 5,
    include_dr:   bool = False,
    env_names:    list = None,
) -> dict:
    """
    Generate cloud_sizing.xlsx and aws_pricing_forecast.xlsx (+GCP/Comparison sheets).
    For On-Prem clients also generates an OpenShift or Kubeadm style sizing workbook.
    Returns dict with file paths.
    """
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    db_selection = pricing.get("db_selection", {}) if pricing else {}

    # ── Workbook 1: Cloud Sizing ──────────────────────────────────────────
    wb1 = Workbook()
    _build_cloud_sizing_sheet(wb1, distribution, metrics, customer)
    # DB Selection sheet only makes sense for SaaS (where pricing is calculated)
    if client_mode == "saas" and db_selection:
        _build_db_selection_sheet(wb1, db_selection, customer)
    # Pre-Prod/DR sheets in Cloud Sizing XLSX only for SaaS — on-prem uses dedicated workbooks
    if client_mode == "saas" and env_pricing:
        preprod = env_pricing.get("preprod_sit_uat")
        dr      = env_pricing.get("dr")
        if preprod:
            _build_preprod_sheet(wb1, preprod, db_type, customer)
        if dr:
            _build_dr_sheet(wb1, dr, db_type, customer)
    sizing_path = os.path.join(output_dir, "cloud_sizing.xlsx")
    wb1.save(sizing_path)
    print(f"[excel_exporter] Saved {sizing_path}")

    # ── Workbook 2: AWS Pricing (SaaS only) ──────────────────────────────
    pricing_path = None
    if client_mode == "saas" and pricing is not None:
        wb2 = Workbook()
        wb2.remove(wb2.active)
        _build_aws_pricing_sheet(wb2, pricing, metrics, customer)
        if env_pricing:
            preprod = env_pricing.get("preprod_sit_uat")
            dr      = env_pricing.get("dr")
            if preprod:
                _build_preprod_sheet(wb2, preprod, db_type, customer)
            if dr:
                _build_dr_sheet(wb2, dr, db_type, customer)
        _build_pupm_sheet(wb2, pricing, env_pricing, metrics, customer)
        if gcp_pricing:
            _build_gcp_pricing_sheet(wb2, gcp_pricing, customer)
        if comparison:
            _build_comparison_sheet(wb2, comparison, customer)
        pricing_path = os.path.join(output_dir, "aws_pricing_forecast.xlsx")
        wb2.save(pricing_path)
        print(f"[excel_exporter] Saved {pricing_path}")

    # ── Workbook 3 & 4: On-Prem Sizing Sheets (On-Prem only) ──────────────
    # Both OpenShift and Kubeadm files are ALWAYS generated.
    # Both use the user-selected db_type — same DB, two cluster architectures.
    # DR and Pre-Prod environment sheets are included based on checkbox selections;
    # no pricing is shown — these are purely infrastructure sizing sheets.
    onprem_openshift_path = None
    onprem_kubeadm_path = None
    if client_mode == "onprem":
        primary_db_type = db_type if db_type else "SQL Server"
        db_slug = primary_db_type.lower().replace(" ", "_")

        # File 1: OpenShift cluster — user's selected DB
        onprem_openshift_path = generate_onprem_excel(
            metrics=metrics,
            distribution=distribution,
            customer=customer,
            output_dir=output_dir,
            db_type=primary_db_type,
            years=years,
            filename=f"onprem_openshift_{db_slug}_sizing.xlsx",
            cluster_name="OpenShift",
            include_dr=include_dr,
            env_names=env_names or [],
        )

        # File 2: Kubeadm cluster — same user-selected DB
        onprem_kubeadm_path = generate_onprem_excel(
            metrics=metrics,
            distribution=distribution,
            customer=customer,
            output_dir=output_dir,
            db_type=primary_db_type,
            years=years,
            filename=f"onprem_kubeadm_{db_slug}_sizing.xlsx",
            cluster_name="Kubeadm",
            include_dr=include_dr,
            env_names=env_names or [],
        )

    return {
        "cloud_sizing":         sizing_path,
        "aws_pricing":          pricing_path,   # None for on-prem
        "gcp_pricing":          pricing_path,
        "comparison":           pricing_path,
        "onprem_sizing":        onprem_openshift_path,
        "onprem_oracle_sizing": onprem_kubeadm_path,
    }


# ── GCP Pricing Sheet ─────────────────────────────────────────────────────
def _build_gcp_pricing_sheet(wb: Workbook, gcp_pricing: dict, customer: str):
    ws = wb.create_sheet("GCP Pricing")
    ws.sheet_view.showGridLines = False
    ws.column_dimensions["A"].width = 22
    ws.column_dimensions["B"].width = 32
    ws.column_dimensions["C"].width = 22
    ws.column_dimensions["D"].width = 16
    ws.column_dimensions["E"].width = 16
    ws.column_dimensions["F"].width = 16

    # Title
    ws.merge_cells("A1:F1")
    c = ws["A1"]
    c.value = f"GCP Compute Engine Pricing — {customer}"
    c.font  = _font(bold=True, size=14, color="FFFFFF")
    c.fill  = _fill("0F9D58")  # GCP green
    c.alignment = _center()
    ws.row_dimensions[1].height = 30

    # Region info
    ws.merge_cells("A2:F2")
    region_label = gcp_pricing.get("region_label", gcp_pricing.get("region",""))
    ws["A2"].value = (
        f"Region: {gcp_pricing.get('region','')}  ({region_label})  ·  "
        f"Generated: {datetime.today().strftime('%d %b %Y')}  ·  "
        f"All On-Demand prices  ·  GCP fallback rates"
    )
    ws["A2"].font      = _font(size=9, color="FFFFFF", italic=True)
    ws["A2"].fill      = _fill("137333")
    ws["A2"].alignment = _center()
    ws.row_dimensions[2].height = 18

    # Table header
    r = 4
    _header_row(ws, r, ["Category", "Role / Service", "Instance Type", "$/hr", "$/month", "$/year"],
                _fill("0F9D58"))
    ws.row_dimensions[r].height = 20
    r += 1

    total_monthly = 0.0
    for i, role in enumerate(gcp_pricing.get("priced_roles", [])):
        mo = role.get("monthly_usd", 0) or 0
        total_monthly += mo
        fill = ALT_FILL if i % 2 == 0 else _fill("FFFFFF")
        vals = [
            role.get("category", ""),
            role.get("label", ""),
            role.get("instance_type", ""),
            role.get("hourly_usd", 0),
            mo,
            round(mo * 12, 2),
        ]
        for col, val in enumerate(vals, 1):
            c = ws.cell(row=r, column=col, value=val)
            c.font      = _font(size=9)
            c.fill      = fill
            c.border    = _border()
            c.alignment = _center() if col >= 4 else _left()
            if col >= 4 and isinstance(val, (int, float)):
                c.number_format = '"$"#,##0.00'
        ws.row_dimensions[r].height = 15
        r += 1

    # Totals
    ws.cell(row=r, column=1, value="TOTAL").font = _font(bold=True, size=10)
    ws.cell(row=r, column=1).fill = TOTAL_FILL
    for col in range(1, 7):
        ws.cell(row=r, column=col).border = _border()
        ws.cell(row=r, column=col).fill   = TOTAL_FILL
    ws.cell(row=r, column=5, value=round(total_monthly, 2)).number_format = '"$"#,##0.00'
    ws.cell(row=r, column=5).font   = _font(bold=True)
    ws.cell(row=r, column=5).fill   = TOTAL_FILL
    ws.cell(row=r, column=6, value=round(total_monthly * 12, 2)).number_format = '"$"#,##0.00'
    ws.cell(row=r, column=6).font   = _font(bold=True)
    ws.cell(row=r, column=6).fill   = TOTAL_FILL
    ws.row_dimensions[r].height = 18
    r += 2

    # 5-Year Forecast
    ws.merge_cells(f"A{r}:F{r}")
    ws[f"A{r}"].value     = "5-Year GCP Cost Forecast (4% inflation per year)"
    ws[f"A{r}"].font      = _font(bold=True, size=11, color="FFFFFF")
    ws[f"A{r}"].fill      = _fill("0F9D58")
    ws[f"A{r}"].alignment = _center()
    ws.row_dimensions[r].height = 22
    r += 1

    _header_row(ws, r, ["Year", "Multiplier", "Monthly", "Annual", "Cumulative", "vs Base"],
                _fill("137333"))
    ws.row_dimensions[r].height = 18
    r += 1

    for yr in gcp_pricing.get("inflation_forecast", {}).get("yearly", []):
        fill = ALT_FILL if yr["year"] % 2 == 0 else _fill("FFFFFF")
        vals = [
            f"Year {yr['year']}",
            f"{yr['multiplier']:.4f}×",
            yr["monthly_usd"],
            yr["annual_usd"],
            yr["cumulative_usd"],
            f"+{(yr['multiplier']-1)*100:.1f}%",
        ]
        for col, val in enumerate(vals, 1):
            c = ws.cell(row=r, column=col, value=val)
            c.font      = _font(size=9)
            c.fill      = fill
            c.border    = _border()
            c.alignment = _center()
            if col in (3, 4, 5) and isinstance(val, (int, float)):
                c.number_format = '"$"#,##0.00'
        ws.row_dimensions[r].height = 15
        r += 1


# ── Comparison Sheet ──────────────────────────────────────────────────────
def _build_comparison_sheet(wb: Workbook, comparison: dict, customer: str):
    ws = wb.create_sheet("AWS vs GCP Comparison")
    ws.sheet_view.showGridLines = False
    for col, w in zip("ABCDEFG", [22, 18, 18, 18, 18, 18, 14]):
        ws.column_dimensions[col].width = w

    s = comparison.get("summary", {})

    # Title
    ws.merge_cells("A1:G1")
    ws["A1"].value     = f"AWS vs GCP Cost Comparison — {customer}"
    ws["A1"].font      = _font(bold=True, size=14, color="FFFFFF")
    ws["A1"].fill      = _fill("1F4E79")
    ws["A1"].alignment = _center()
    ws.row_dimensions[1].height = 30

    # Summary sub-header
    ws.merge_cells("A2:G2")
    aws_reg = s.get("aws_region", "us-east-1")
    gcp_reg = s.get("gcp_region", "us-central1")
    ws["A2"].value = (
        f"AWS Region: {aws_reg}   |   GCP Region: {gcp_reg}   |   "
        f"Generated: {datetime.today().strftime('%d %b %Y')}   |   On-Demand pricing"
    )
    ws["A2"].font      = _font(size=9, color="FFFFFF", italic=True)
    ws["A2"].fill      = _fill("2E75B6")
    ws["A2"].alignment = _center()
    ws.row_dimensions[2].height = 18

    # KPI summary row
    r = 4
    ws.merge_cells(f"A{r}:G{r}")
    ws[f"A{r}"].value     = "Cost Summary"
    ws[f"A{r}"].font      = _font(bold=True, size=11, color="FFFFFF")
    ws[f"A{r}"].fill      = SECTION_FILL
    ws[f"A{r}"].alignment = _center()
    ws.row_dimensions[r].height = 20
    r += 1

    summary_rows = [
        ("Monthly Cost (AWS)",   s.get("aws_monthly",  0), "$#,##0.00"),
        ("Monthly Cost (GCP)",   s.get("gcp_monthly",  0), "$#,##0.00"),
        ("Monthly Difference",   s.get("diff_monthly", 0), "$#,##0.00"),
        ("Cheaper Cloud (Monthly)", s.get("cheaper_monthly", "AWS"), "@"),
        ("Annual Cost (AWS)",    s.get("aws_annual",   0), "$#,##0.00"),
        ("Annual Cost (GCP)",    s.get("gcp_annual",   0), "$#,##0.00"),
        ("5-Year Total (AWS)",   s.get("aws_5year",    0), "$#,##0.00"),
        ("5-Year Total (GCP)",   s.get("gcp_5year",    0), "$#,##0.00"),
        ("5-Year Savings",       s.get("diff_5year",   0), "$#,##0.00"),
        ("5-Year Winner",        s.get("cheaper_5year","AWS"), "@"),
    ]
    for label, val, fmt in summary_rows:
        fill = GREEN_FILL if label in ("Cheaper Cloud (Monthly)","5-Year Winner") else _fill("FFFFFF")
        ws.cell(row=r, column=1, value=label).font      = _font(bold=True, size=10)
        ws.cell(row=r, column=1).alignment  = _left()
        ws.cell(row=r, column=1).border     = _border()
        ws.cell(row=r, column=2, value=val).font        = _font(size=10)
        ws.cell(row=r, column=2).alignment  = _center()
        ws.cell(row=r, column=2).border     = _border()
        ws.cell(row=r, column=2).fill       = fill
        if fmt != "@" and isinstance(val, (int, float)):
            ws.cell(row=r, column=2).number_format = fmt
        for col in range(1, 3):
            ws.cell(row=r, column=col).fill = fill
        ws.row_dimensions[r].height = 15
        r += 1
    r += 1

    # Category comparison table
    ws.merge_cells(f"A{r}:G{r}")
    ws[f"A{r}"].value     = "Category-Level Cost Comparison"
    ws[f"A{r}"].font      = _font(bold=True, size=11, color="FFFFFF")
    ws[f"A{r}"].fill      = SECTION_FILL
    ws[f"A{r}"].alignment = _center()
    ws.row_dimensions[r].height = 20
    r += 1

    _header_row(ws, r, ["Category", "AWS $/mo", "GCP $/mo", "Difference", "% Diff", "Cheaper", ""],
                _fill("1F4E79"))
    ws.row_dimensions[r].height = 18
    r += 1

    for i, row in enumerate(comparison.get("category_comparison", [])):
        fill = ALT_FILL if i % 2 == 0 else _fill("FFFFFF")
        diff = row["diff"]
        vals = [
            row["category"],
            row["aws_monthly"],
            row["gcp_monthly"],
            abs(diff),
            f"{abs(row.get('pct_diff',0)):.1f}%",
            row["cheaper"],
            "✔",
        ]
        for col, val in enumerate(vals, 1):
            c = ws.cell(row=r, column=col, value=val)
            c.font      = _font(size=9, bold=(col==7))
            c.fill      = GREEN_FILL if col == 6 else fill
            c.border    = _border()
            c.alignment = _center() if col > 1 else _left()
            if col in (2, 3, 4) and isinstance(val, (int, float)):
                c.number_format = '"$"#,##0.00'
        ws.row_dimensions[r].height = 15
        r += 1
    r += 1

    # Year-by-year comparison
    ws.merge_cells(f"A{r}:G{r}")
    ws[f"A{r}"].value     = "5-Year Year-by-Year Comparison"
    ws[f"A{r}"].font      = _font(bold=True, size=11, color="FFFFFF")
    ws[f"A{r}"].fill      = SECTION_FILL
    ws[f"A{r}"].alignment = _center()
    ws.row_dimensions[r].height = 20
    r += 1

    _header_row(ws, r, ["Year", "AWS Monthly", "GCP Monthly", "AWS Annual", "GCP Annual",
                         "AWS Cumul.", "GCP Cumul."], _fill("1F4E79"))
    ws.row_dimensions[r].height = 18
    r += 1

    for i, yr in enumerate(comparison.get("yearly_comparison", [])):
        fill = ALT_FILL if i % 2 == 0 else _fill("FFFFFF")
        cheaper_fill = GREEN_FILL if yr.get("cheaper") == "AWS" else _fill("E8F5E9")
        vals = [
            f"Year {yr['year']}",
            yr["aws_monthly"], yr["gcp_monthly"],
            yr["aws_annual"],  yr["gcp_annual"],
            yr["aws_cumulative"], yr["gcp_cumulative"],
        ]
        for col, val in enumerate(vals, 1):
            c = ws.cell(row=r, column=col, value=val)
            c.font      = _font(size=9)
            c.fill      = fill
            c.border    = _border()
            c.alignment = _center()
            if col > 1 and isinstance(val, (int, float)):
                c.number_format = '"$"#,##0.00'
        # Highlight cheaper cloud columns
        aws_col = 2 if yr.get("cheaper") == "AWS" else None
        gcp_col = 3 if yr.get("cheaper") == "GCP" else None
        if aws_col: ws.cell(row=r, column=aws_col).fill = GREEN_FILL
        if gcp_col: ws.cell(row=r, column=gcp_col).fill = GREEN_FILL
        ws.row_dimensions[r].height = 15


# ══════════════════════════════════════════════════════════════════════════════
# On-Premise OpenShift / Kubeadm Sizing Workbook
# ══════════════════════════════════════════════════════════════════════════════

MASTER_NODES = 3          # Always constant per user requirement
BOOTSTRAP_CPU, BOOTSTRAP_RAM, BOOTSTRAP_STORAGE = 2, 16, 256
MASTER_CPU,    MASTER_RAM,    MASTER_STORAGE    = 4, 16, 256
WORKER_CPU,    WORKER_RAM,    WORKER_STORAGE    = 8, 32, 256
INFRA_CPU,     INFRA_RAM,     INFRA_STORAGE     = 4, 32, 256
BASTION2_CPU,  BASTION2_RAM,  BASTION2_STORAGE  = 2, 8,  256
DB_WIN_STORAGE = 300      # per Windows node
IMAGE_REGISTRY_GB = 1024


def _onprem_metrics_by_year(metrics: dict, years: int) -> list:
    """
    Project per-year metrics for the On-Prem sizing sheets.
    Worker nodes grow ~5%/yr, data 10%/yr (matching template ratios 7→8 over 4 yrs).
    Returns list of dicts, one per year (index 0 = year 1).
    """
    base_workers  = int(metrics.get("total_workernodes", 7))
    base_data_gb  = int(metrics.get("data_size_gb",  14000))
    base_s3_gb    = int(metrics.get("s3_size_gb",     7100))
    base_vcpus    = int(metrics.get("total_vcpus_workernode", 56))

    # Infer DB node sizing from total_vcpus (template uses memory-intensive nodes)
    # Template Y1: 2 Windows nodes × 18 cores = 36 vCPU ≈ 64% of worker vCPUs
    base_db_vcpu   = max(18, int(base_vcpus * 0.64))
    base_db_ram    = base_db_vcpu * 16   # 16 GB per vCPU
    base_db_nodes  = 2                   # always 2 primary DB nodes in PROD

    result = []
    for y in range(1, years + 1):
        # Worker nodes: ceil of 5% growth
        worker_y = max(base_workers, int(base_workers * (1.05 ** (y - 1))))
        # Infra nodes: 3 for PROD (stable)
        infra_y  = 3
        # Data size: grows 10% per year
        data_y   = int(base_data_gb * (1.10 ** (y - 1)))
        s3_y     = int(base_s3_gb   * (1.10 ** (y - 1)))
        # DB vCPUs scale with data size
        scaler    = data_y / max(base_data_gb, 1)
        db_vcpu_y = max(base_db_vcpu, int(base_db_vcpu * scaler))
        db_ram_y  = db_vcpu_y * 16
        # NFS storage = data + S3 + per-node overhead + image registry
        nfs_y = data_y + s3_y + worker_y * 256 + infra_y * 256 + IMAGE_REGISTRY_GB
        # SAN mirrors data size
        san_y = data_y
        result.append({
            "year":         y,
            "worker_nodes": worker_y,
            "infra_nodes":  infra_y,
            "data_gb":      data_y,
            "s3_gb":        s3_y,
            "db_nodes":     base_db_nodes,
            "db_vcpu":      db_vcpu_y,
            "db_ram":       db_ram_y,
            "nfs_gb":       nfs_y,
            "san_gb":       san_y,
            "app_servers":  worker_y,
        })
    return result


def _build_onprem_data_sheet(wb: Workbook, metrics_by_year: list, customer: str):
    """Builds the 'Data' summary sheet matching the template's Data tab."""
    ws = wb.create_sheet("Data")
    ws.sheet_view.showGridLines = False

    NUM_YEARS   = len(metrics_by_year)
    yr_suffixes = ["1st", "2nd", "3rd"] + [f"{y}th" for y in range(4, NUM_YEARS + 1)]
    year_labels = yr_suffixes[:NUM_YEARS]

    HDR_FILL = _fill("1F4E79")
    SEC_FILL = _fill("2E75B6")
    ALT_FILL = _fill("EBF3FB")
    WHT_FILL = _fill("FFFFFF")

    last_col    = 2 + NUM_YEARS
    last_letter = get_column_letter(last_col)

    # Title
    ws.merge_cells(f"A1:{last_letter}1")
    t = ws["A1"]
    t.value     = f"On-Premise Infrastructure Metrics — {customer} — {datetime.today().strftime('%d %b %Y')}"
    t.font      = _font(bold=True, size=13, color="FFFFFF")
    t.fill      = HDR_FILL
    t.alignment = _center()
    ws.row_dimensions[1].height = 28

    # Header row: blank | "Year >" | 1st | 2nd | …
    ws.cell(row=2, column=1, value="Metric").font = _font(bold=True, color="FFFFFF", size=10)
    ws.cell(row=2, column=1).fill = HDR_FILL
    ws.cell(row=2, column=1).alignment = _left()
    ws.cell(row=2, column=1).border = _border()
    ws.cell(row=2, column=2, value="Year >").font = _font(bold=True, color="FFFFFF", size=10)
    ws.cell(row=2, column=2).fill = HDR_FILL
    ws.cell(row=2, column=2).alignment = _center()
    ws.cell(row=2, column=2).border = _border()
    for i, label in enumerate(year_labels):
        c = ws.cell(row=2, column=3+i, value=label)
        c.font      = _font(bold=True, color="FFFFFF", size=10)
        c.fill      = SEC_FILL
        c.alignment = _center()
        c.border    = _border()
    ws.row_dimensions[2].height = 22

    def _sec(row, title):
        ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=last_col)
        c = ws.cell(row=row, column=1, value=f"  {title}")
        c.font      = _font(bold=True, color="FFFFFF", size=10)
        c.fill      = SEC_FILL
        c.alignment = _left()
        c.border    = _border()
        ws.row_dimensions[row].height = 18

    def _dat(row, label, values, alt=False):
        fill = ALT_FILL if alt else WHT_FILL
        c = ws.cell(row=row, column=1, value=label)
        c.font = _font(size=10); c.fill = fill; c.alignment = _left(); c.border = _border()
        ws.cell(row=row, column=2).fill   = fill
        ws.cell(row=row, column=2).border = _border()
        for i, v in enumerate(values):
            cell = ws.cell(row=row, column=3+i, value=v)
            cell.font = _font(size=10); cell.fill = fill
            cell.alignment = _center(); cell.border = _border()
            if isinstance(v, (int, float)):
                cell.number_format = "#,##0"
        ws.row_dimensions[row].height = 16

    r = 3
    _sec(r, "CRMNEXT App Servers"); r += 1
    _dat(r, "Total App Servers (8 Phy. Cores/16vCPU, 32GB RAM Each)",
         [m["app_servers"] for m in metrics_by_year]); r += 1

    _sec(r, "CRMNEXT Database Server"); r += 1
    _dat(r, "Total Cores Required",
         [m["db_vcpu"] // 2 for m in metrics_by_year], alt=True); r += 1
    _dat(r, "Total vCPUs Required",
         [m["db_vcpu"] for m in metrics_by_year]); r += 1

    _sec(r, "Volumes"); r += 1
    _dat(r, "Data size (GB)",
         [m["data_gb"] for m in metrics_by_year], alt=True); r += 1
    _dat(r, "S3 size (GB)",
         [m["s3_gb"] for m in metrics_by_year]); r += 1

    _set_col_widths(ws, [52, 12] + [14] * NUM_YEARS)


def _build_onprem_env_sheet(
    wb: Workbook,
    sheet_name: str,
    env_label: str,
    env_data: dict,
    customer: str,
    is_prod: bool = False,
    include_reporting_db: bool = False,
    archival_san_gb: float = 0,
    db_type: str = "SQL Server",
    cluster_name: str = None,   # Override cluster label: "OpenShift" or "Kubeadm"
):
    """
    Builds one environment sheet (PROD-XYr, DR, PRE-PROD, UAT, SIT)
    matching the standard on-prem sizing layout exactly.
    """
    ws = wb.create_sheet(sheet_name)
    ws.sheet_view.showGridLines = False

    worker_nodes = int(env_data["worker_nodes"])
    infra_nodes  = int(env_data["infra_nodes"])
    db_nodes     = int(env_data["db_nodes"])
    db_vcpu      = int(env_data["db_vcpu"])
    db_ram       = int(env_data["db_ram"])
    data_gb      = int(env_data["data_gb"])
    s3_gb        = int(env_data["s3_gb"])
    nfs_gb       = int(env_data["nfs_gb"])
    san_gb       = int(env_data["san_gb"])

    # Use explicit override if provided; otherwise derive from db_type
    if cluster_name is None:
        cluster_name = "Kubeadm" if db_type == "Oracle" else "OpenShift"

    HDR_FILL  = _fill("1F4E79")
    SEC_FILL  = _fill("2E75B6")
    ALT_FILL  = _fill("EBF3FB")
    WHT_FILL  = _fill("FFFFFF")

    # ── Title row ────────────────────────────────────────────────────────────
    ws.merge_cells("B1:N1")
    t = ws["B1"]
    t.value     = f"{env_label} Environment On Premise"
    t.font      = _font(bold=True, size=12, color="FFFFFF")
    t.fill      = HDR_FILL
    t.alignment = _center()
    ws.row_dimensions[1].height = 26

    # ── Column header row ────────────────────────────────────────────────────
    col_headers = [
        "S.N.", "Services/Instances", "Nodes", "Instance Type", "Remarks",
        "Per Node\nCPU cores", "Per Node\nRAM", "Per Node\nStorage (GB)",
        "Total\nCPU cores", "Total\nRAM\n(GB)", "Total\nStorage\n(TB)",
        None, "Remarks", None,
    ]
    for i, h in enumerate(col_headers):
        c = ws.cell(row=2, column=2+i, value=h)
        c.font      = _font(bold=True, size=9, color="FFFFFF")
        c.fill      = HDR_FILL
        c.alignment = _center()
        c.border    = _border()
    ws.row_dimensions[2].height = 36

    def _sec(row, sn, title):
        ws.cell(row=row, column=2, value=sn).font      = _font(bold=True, size=10, color="FFFFFF")
        ws.cell(row=row, column=2).fill      = SEC_FILL
        ws.cell(row=row, column=2).border    = _border()
        ws.cell(row=row, column=2).alignment = _center()
        ws.merge_cells(start_row=row, start_column=3, end_row=row, end_column=15)
        c = ws.cell(row=row, column=3, value=title)
        c.font = _font(bold=True, size=10, color="FFFFFF")
        c.fill = SEC_FILL; c.alignment = _left(); c.border = _border()
        for col in [13, 14, 15]:
            ws.cell(row=row, column=col).fill   = SEC_FILL
            ws.cell(row=row, column=col).border = _border()
        ws.row_dimensions[row].height = 20

    def _dr(row, sn, service, nodes, inst_type, remarks,
            cpu_n, ram_n, stor_n, tot_cpu, tot_ram, tot_stor_tb,
            remarks2="", alt=False):
        fill = ALT_FILL if alt else WHT_FILL
        vals = [sn, service, nodes, inst_type, remarks,
                cpu_n, ram_n, stor_n, tot_cpu, tot_ram, tot_stor_tb, None, remarks2, None]
        for i, v in enumerate(vals):
            col = 2 + i
            c = ws.cell(row=row, column=col, value=v)
            c.font      = _font(size=9)
            c.fill      = fill
            c.alignment = _center() if col > 3 else _left()
            c.border    = _border()
            if col == 12 and isinstance(v, float):
                c.number_format = "0.00####"
        ws.row_dimensions[row].height = 16

    def _tb(n, gb):
        return round(n * gb / 1024, 8)

    r = 3

    # Section 1: Cluster
    _sec(r, 1, f"{cluster_name} Cluster"); r += 1
    _dr(r, None, "Bootstrap machine", 1, "Memory Intensive",
        f"{cluster_name} vendor to confirm on sizing.",
        BOOTSTRAP_CPU, BOOTSTRAP_RAM, BOOTSTRAP_STORAGE,
        BOOTSTRAP_CPU, BOOTSTRAP_RAM, _tb(1, BOOTSTRAP_STORAGE), alt=True); r += 1
    _dr(r, None, "Bastion Host", 1, "Memory Intensive", "",
        BOOTSTRAP_CPU, BOOTSTRAP_RAM, BOOTSTRAP_STORAGE,
        BOOTSTRAP_CPU, BOOTSTRAP_RAM, _tb(1, BOOTSTRAP_STORAGE)); r += 1
    _dr(r, None, "Master Nodes", MASTER_NODES, "Compute Intensive", "",
        MASTER_CPU, MASTER_RAM, MASTER_STORAGE,
        MASTER_NODES*MASTER_CPU, MASTER_NODES*MASTER_RAM,
        _tb(MASTER_NODES, MASTER_STORAGE), alt=True); r += 1
    _dr(r, None, "Linux Worker Nodes (BUSINESSNEXT)", worker_nodes, "Compute Intensive", "",
        WORKER_CPU, WORKER_RAM, WORKER_STORAGE,
        worker_nodes*WORKER_CPU, worker_nodes*WORKER_RAM,
        _tb(worker_nodes, WORKER_STORAGE)); r += 1

    # Section 2: Operational Services
    _sec(r, 2, "Operational Services"); r += 1
    _dr(r, None, "Infra Nodes (Grafana & Prometheus, EFK, Redis)",
        infra_nodes, "Compute Intensive", "",
        INFRA_CPU, INFRA_RAM, INFRA_STORAGE,
        infra_nodes*INFRA_CPU, infra_nodes*INFRA_RAM,
        _tb(infra_nodes, INFRA_STORAGE), alt=True); r += 1
    _dr(r, None, "NFS Storage", 1, "", "",
        None, None, nfs_gb, None, None, round(nfs_gb/1024, 8)); r += 1

    sn = 3

    vcpu_per = db_vcpu // max(db_nodes, 1)
    ram_per  = db_ram  // max(db_nodes, 1)

    if db_type == "Oracle":
        # Section 3: Oracle Database
        _sec(r, sn, "Oracle Database"); r += 1
        _dr(r, None, "OEL/RHEL", db_nodes, "Memory Intensive", "",
            vcpu_per, ram_per, DB_WIN_STORAGE,
            db_vcpu, db_ram, _tb(db_nodes, DB_WIN_STORAGE), alt=True); r += 1
        _dr(r, None, "Oracle License", db_nodes, "Memory Intensive", "",
            None, None, None, None, None, None); r += 1
        _dr(r, None, "Storage: SAN", db_nodes, "20K IOPS", "",
            None, None, san_gb, None, None,
            _tb(db_nodes, san_gb), alt=True); r += 1
        if is_prod:
            _dr(r, None, "RAC - Active/Active", 1, "20K IOPS",
                "As per current archival database size",
                None, None, archival_san_gb, None, None,
                _tb(1, archival_san_gb)); r += 1
            _dr(r, None, "Dataguard", 1, "", "",
                None, None, None, None, None, None, alt=True); r += 1
        sn += 1

        # Section 4: Oracle Database - Reporting (PROD only)
        if is_prod and include_reporting_db:
            _sec(r, sn, "Oracle Database - Reporting"); r += 1
            _dr(r, None, "OEL/RHEL", 1, "Memory Intensive", "",
                vcpu_per, ram_per, DB_WIN_STORAGE,
                vcpu_per, ram_per, _tb(1, DB_WIN_STORAGE), alt=True); r += 1
            _dr(r, None, "Oracle License", 1, "Memory Intensive", "",
                None, None, None, None, None, None); r += 1
            _dr(r, None, "Storage: SAN", 1, "20K IOPS", "",
                None, None, san_gb, None, None,
                _tb(1, san_gb), alt=True); r += 1
            sn += 1
    else:
        # Section 3: MSSQL Enterprise Database
        _sec(r, sn, "MSSQL Enterprise Database"); r += 1
        _dr(r, None, "Windows Nodes", db_nodes, "Memory Intensive", "",
            vcpu_per, ram_per, DB_WIN_STORAGE,
            db_vcpu, db_ram, _tb(db_nodes, DB_WIN_STORAGE), alt=True); r += 1
        _dr(r, None, "SQL License", db_nodes, "Memory Intensive", "",
            None, None, None, None, None, None); r += 1
        _dr(r, None, "Storage: SAN", db_nodes, "20K IOPS", "",
            None, None, san_gb, None, None,
            _tb(db_nodes, san_gb), alt=True); r += 1
        if is_prod:
            _dr(r, None, "Storage: SAN (Archival)", db_nodes, "20K IOPS",
                "As per current archival database size",
                None, None, archival_san_gb, None, None,
                _tb(db_nodes, archival_san_gb)); r += 1
        sn += 1

        # Section 4: MSSQL Reporting DB (PROD only)
        if is_prod and include_reporting_db:
            _sec(r, sn, "MSSQL Enterprise Database - Reporting"); r += 1
            _dr(r, None, "Windows Nodes", 1, "Memory Intensive", "",
                vcpu_per, ram_per, DB_WIN_STORAGE,
                vcpu_per, ram_per, _tb(1, DB_WIN_STORAGE), alt=True); r += 1
            _dr(r, None, "SQL License", 1, "Memory Intensive", "",
                None, None, None, None, None, None); r += 1
            _dr(r, None, "Storage: SAN", 1, "20K IOPS", "",
                None, None, san_gb, None, None,
                _tb(1, san_gb), alt=True); r += 1
            sn += 1

    # S3 section
    _sec(r, sn, "S3"); r += 1
    _dr(r, None, "S3 Storage", 1,
        "To be consumed from main NFS storage",
        "Will be based on the number of documents provided, "
        "Considering per document size per Service Request of 512KB Each.",
        None, None, s3_gb, None, None, round(s3_gb/1024, 8), alt=True); r += 1
    sn += 1

    # Infrastructure & Monitoring
    _sec(r, sn, "Infrastructure & Monitoring"); r += 1
    _dr(r, None, "SSL", 1, "Provided by Bank", "",
        None, None, None, None, None, None); r += 1
    _dr(r, None, "Image Registry", 1, "For Containers docker images", "",
        None, None, IMAGE_REGISTRY_GB, None, None,
        round(IMAGE_REGISTRY_GB/1024, 8), alt=True); r += 1
    _dr(r, None, "Web Application Firewall (WAF)", 1, "",
        "As per banks security policy.",
        None, None, None, None, None, None); r += 1
    _dr(r, None, "Bastion Host", 1, "", "As per banks policy.",
        BASTION2_CPU, BASTION2_RAM, BASTION2_STORAGE,
        BASTION2_CPU, BASTION2_RAM, _tb(1, BASTION2_STORAGE), alt=True); r += 1
    _dr(r, None, "Email Service", 1, "Two million mails/month", "",
        None, None, None, None, None, None); r += 1
    if is_prod:
        _dr(r, None, "Back Up - DB", 1,
            "As per banks retention policy. Backup solution can be used.", "",
            None, None, None, None, None, None); r += 1

    # Column widths (col A=stub, B onward)
    ws.column_dimensions["A"].width = 2
    for col_i, w in enumerate([8, 42, 8, 20, 35, 14, 12, 16, 12, 14, 16, 4, 35, 4]):
        ws.column_dimensions[get_column_letter(2+col_i)].width = w


def generate_onprem_excel(
    metrics:      dict,
    distribution: dict,
    customer:     str  = "Bank-Name",
    output_dir:   str  = "reports",
    db_type:      str  = "SQL Server",
    years:        int  = 5,
    filename:     str  = "onprem_openshift_sizing.xlsx",
    cluster_name: str  = None,    # "OpenShift" or "Kubeadm" — overrides auto-detect
    include_dr:   bool = False,   # Add DR sheet only when user checked the DR checkbox
    env_names:    list = None,    # e.g. ["Pre-Prod", "SIT", "UAT"] — only add checked envs
) -> str:
    """
    Generates the OpenShift or Kubeadm On-Premise sizing workbook.
    Sheets always included: Data, PROD-1Yr…NYr
    Sheets added conditionally based on user checkbox selections:
      - DR         → only if include_dr=True
      - PRE-PROD   → only if "Pre-Prod" in env_names
      - UAT        → only if "UAT" in env_names
      - SIT        → only if "SIT" in env_names
    No pricing data is written — this is a pure infrastructure sizing file.
    Returns the saved file path.
    """
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    env_names = env_names or []

    metrics_by_year = _onprem_metrics_by_year(metrics, years)

    wb = Workbook()
    wb.remove(wb.active)   # remove default blank sheet

    # Data sheet — always present
    _build_onprem_data_sheet(wb, metrics_by_year, customer)

    # PROD sheets — one per year, always present
    for m in metrics_by_year:
        y = m["year"]
        _build_onprem_env_sheet(
            wb,
            sheet_name=f"PROD-{y}Yr",
            env_label=f"PROD (Year {y})",
            env_data=m,
            customer=customer,
            is_prod=True,
            include_reporting_db=True,
            archival_san_gb=5000,
            db_type=db_type,
            cluster_name=cluster_name,
        )

    # DR sheet — only when the DR checkbox was checked
    if include_dr:
        _build_onprem_env_sheet(
            wb,
            sheet_name="DR",
            env_label="DR",
            env_data=dict(metrics_by_year[-1]),
            customer=customer,
            is_prod=True,
            include_reporting_db=True,
            archival_san_gb=5000,
            db_type=db_type,
            cluster_name=cluster_name,
        )

    # Pre-Prod / SIT / UAT sheets — only when the respective checkbox was checked
    y1 = metrics_by_year[0]
    preprod_m = dict(y1)
    preprod_m["worker_nodes"] = 1
    preprod_m["infra_nodes"]  = 2
    preprod_m["db_nodes"]     = 1
    preprod_m["db_vcpu"]      = y1["db_vcpu"] // max(y1["db_nodes"], 1)
    preprod_m["db_ram"]       = y1["db_ram"]  // max(y1["db_nodes"], 1)
    preprod_m["nfs_gb"]       = y1["data_gb"] + y1["s3_gb"] + 1*256 + 2*256 + IMAGE_REGISTRY_GB
    preprod_m["san_gb"]       = y1["data_gb"]

    if "Pre-Prod" in env_names:
        _build_onprem_env_sheet(
            wb, "PRE-PROD", "PRE-PROD", preprod_m, customer,
            is_prod=False, include_reporting_db=False,
            db_type=db_type, cluster_name=cluster_name,
        )

    uat_m = dict(y1)
    uat_m["worker_nodes"] = 1
    uat_m["infra_nodes"]  = 2
    uat_m["db_nodes"]     = 1
    uat_m["db_vcpu"]      = y1["db_vcpu"] // max(y1["db_nodes"], 1)
    uat_m["db_ram"]       = y1["db_ram"]  // max(y1["db_nodes"], 1)
    uat_m["data_gb"]      = 500
    uat_m["s3_gb"]        = 500
    uat_m["nfs_gb"]       = 500 + 500 + 1*256 + 2*256 + IMAGE_REGISTRY_GB
    uat_m["san_gb"]       = 500

    if "UAT" in env_names:
        _build_onprem_env_sheet(
            wb, "UAT", "UAT", uat_m, customer,
            is_prod=False, include_reporting_db=False,
            db_type=db_type, cluster_name=cluster_name,
        )

    if "SIT" in env_names:
        sit_m = dict(uat_m)
        _build_onprem_env_sheet(
            wb, "SIT", "SIT", sit_m, customer,
            is_prod=False, include_reporting_db=False,
            db_type=db_type, cluster_name=cluster_name,
        )

    out_path = os.path.join(output_dir, filename)
    wb.save(out_path)
    print(f"[excel_exporter] Saved On-Prem sizing ({cluster_name or db_type}): {out_path}")
    return out_path