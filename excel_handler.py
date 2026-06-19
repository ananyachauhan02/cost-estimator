"""
excel_handler.py
─────────────────────────────────────────────────────────────
Responsible for:
  - Copying the Sizing Template
  - Writing UI input values into correct cells
  - Triggering LibreOffice recalculation
  - Extracting computed metrics back out

All cell references are based on the actual Sizing_Template.xlsx
sheet/cell audit performed on 2026-03-10.
─────────────────────────────────────────────────────────────
"""

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import openpyxl


# ── Cell map: UI field → Excel cell reference ─────────────────────────────
# These are the only "blue" (user-editable) cells in the template.
INPUT_CELL_MAP = {
    # ── Year 1 base values (column D) ─────────────────────────────────────
    "named_users":        "Customer Volumes!D3",
    "concurrent_users":   "Customer Volumes!D4",
    "total_customers":    "Customer Volumes!D5",
    "leads":              "Customer Volumes!D7",
    "cases":              "Customer Volumes!D9",
    "mobile_users":       "Customer Volumes!D13",
    # ── YOY growth rates (column I) ───────────────────────────────────────
    # Values are written as decimals, e.g. 0.05 for 5%
    "yoy_named_users":    "Customer Volumes!I3",
    "yoy_concurrent":     "Customer Volumes!I4",   # always same as named users (auto-derived)
    "yoy_customers":      "Customer Volumes!I5",
    "yoy_leads":          "Customer Volumes!I7",
    "yoy_cases":          "Customer Volumes!I9",
    "yoy_mobile":         "Customer Volumes!I13",
}

# ── Cells to read back after recalculation ────────────────────────────────
# Derived from the Server size sheet formula audit.
OUTPUT_CELL_MAP = {
    # Worker nodes
    "total_vcpus_workernode":     "Server size!C6",
    "total_memory_workernode_gb": "Server size!C7",
    "total_workernodes":          "Server size!C18",

    # DB RAM (Postgres path — template uses Postgres)
    "sql_server_ram_gb":          "Server size!C23",
    "oracle_ram_gb":              "Server size!C24",
    "postgres_ram_gb":            "Server size!C25",

    # Storage
    "data_size_gb":               "Server size!C35",
    "s3_size_gb":                "Server size!C36",
}


def write_and_recalculate(
    inputs: dict,
    template_path: str = "templates/Sizing_Template.xlsx",
    output_path:   str = "reports/updated_estimate.xlsx",
) -> str:
    """
    1. Copy template → output path
    2. Write input values into mapped cells
    3. Recalculate with LibreOffice headless
    4. Return path to the recalculated file

    inputs dict keys must match INPUT_CELL_MAP keys above.
    """
    src = Path(template_path).resolve()
    dst = Path(output_path).resolve()
    dst.parent.mkdir(parents=True, exist_ok=True)

    if not src.exists():
        raise FileNotFoundError(f"Template not found: {src}")

    shutil.copy(src, dst)
    print(f"[excel_handler] Template copied → {dst}")

    # ── Write inputs ──────────────────────────────────────────────────────
    wb = openpyxl.load_workbook(dst, data_only=False)
    updated = 0
    for field, value in inputs.items():
        cell_ref = INPUT_CELL_MAP.get(field)
        if not cell_ref:
            print(f"[excel_handler] WARNING: no cell map for field '{field}', skipping")
            continue
        sheet_name, coord = cell_ref.split("!")
        try:
            wb[sheet_name][coord] = value
            print(f"[excel_handler]   wrote {cell_ref} = {value}")
            updated += 1
        except KeyError:
            print(f"[excel_handler] WARNING: sheet '{sheet_name}' not found")

    wb.save(dst)
    print(f"[excel_handler] Saved {updated} cells.")

    # ── LibreOffice recalculation ─────────────────────────────────────────
    with tempfile.TemporaryDirectory() as tmp:
        try:
            print("[excel_handler] Starting LibreOffice recalculation...")
            result = subprocess.run(
                [
                    "libreoffice", "--headless", "--norestore",
                    "--convert-to", "xlsx",
                    str(dst), "--outdir", tmp,
                ],
                check=True, capture_output=True, text=True, timeout=120,
            )
            converted = Path(tmp) / dst.name
            if converted.exists():
                shutil.copy(converted, dst)
                print("[excel_handler] Recalculation complete.")
            else:
                print(f"[excel_handler] WARNING: LibreOffice output missing at {converted}")
        except FileNotFoundError:
            print("[excel_handler] LibreOffice not found — formula cache may be stale.")
        except subprocess.CalledProcessError as e:
            print(f"[excel_handler] LibreOffice error: {e.stderr}")
        except subprocess.TimeoutExpired:
            print("[excel_handler] LibreOffice timed out after 120s.")

    if not dst.exists():
        raise FileNotFoundError(f"Output file was not created: {dst}")

    return str(dst)


def extract_metrics(file_path: str) -> dict:
    """
    Read computed values from the recalculated workbook.
    Returns dict keyed by OUTPUT_CELL_MAP keys, values as floats.
    """
    path = Path(file_path)
    print(f"[excel_handler] Extracting metrics from {path.name} "
          f"(modified {os.path.getmtime(path):.0f})")

    wb = openpyxl.load_workbook(str(path), data_only=True)
    metrics = {}

    for key, cell_ref in OUTPUT_CELL_MAP.items():
        sheet_name, coord = cell_ref.split("!")
        try:
            value = wb[sheet_name][coord].value
            metrics[key] = float(value) if value is not None else 0.0
        except Exception as e:
            print(f"[excel_handler] WARNING: could not read {cell_ref}: {e}")
            metrics[key] = 0.0
        print(f"[excel_handler]   {key} = {metrics[key]}  ({cell_ref})")

    return metrics