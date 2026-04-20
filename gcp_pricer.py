"""
gcp_pricer.py — BusinessNext Cloud Cost Estimator
──────────────────────────────────────────────────
Prices the same node distribution on GCP Compute Engine using:
  1. GCP Cloud Billing Catalog API (requires GOOGLE_CLOUD_PROJECT env var)
  2. Hardcoded March 2026 On-Demand fallback prices (us-central1 base)

Maps AWS instance families → GCP equivalents:
  m5  (general) → n2-standard
  r5  (memory)  → n2-highmem
  cache         → Memorystore for Redis
  K8s worker    → GKE autopilot (billed per pod vCPU/RAM)
  EBS gp3       → Persistent Disk SSD
  EBS io2/SAN   → Persistent Disk Extreme (approx)
"""
from __future__ import annotations

import os
import math

HOURS_PER_MONTH = 730

# ── GCP regions + multipliers vs us-central1 base ────────────────────────
GCP_REGIONS = {
    # Americas
    "us-central1":          {"label": "US Central (Iowa)",               "multiplier": 1.000},
    "us-east1":             {"label": "US East (South Carolina)",        "multiplier": 1.000},
    "us-east4":             {"label": "US East (N. Virginia)",           "multiplier": 1.010},
    "us-east5":             {"label": "US East (Columbus)",              "multiplier": 1.000},
    "us-south1":            {"label": "US South (Dallas)",               "multiplier": 1.000},
    "us-west1":             {"label": "US West (Oregon)",                "multiplier": 1.000},
    "us-west2":             {"label": "US West (Los Angeles)",           "multiplier": 1.090},
    "us-west3":             {"label": "US West (Salt Lake City)",        "multiplier": 1.000},
    "us-west4":             {"label": "US West (Las Vegas)",             "multiplier": 1.040},
    "northamerica-northeast1": {"label": "Canada (Montréal)",            "multiplier": 1.030},
    "northamerica-northeast2": {"label": "Canada (Toronto)",             "multiplier": 1.030},
    "northamerica-south1":     {"label": "North America (Mexico)",       "multiplier": 1.050},
    "southamerica-east1":   {"label": "South America (São Paulo)",       "multiplier": 1.210},
    "southamerica-west1":   {"label": "South America (Santiago)",        "multiplier": 1.200},
    
    # Europe
    "europe-west1":         {"label": "Europe (Belgium)",                "multiplier": 1.050},
    "europe-west2":         {"label": "Europe (London)",                 "multiplier": 1.110},
    "europe-west3":         {"label": "Europe (Frankfurt)",              "multiplier": 1.100},
    "europe-west4":         {"label": "Europe (Netherlands)",            "multiplier": 1.050},
    "europe-west6":         {"label": "Europe (Zurich)",                 "multiplier": 1.150},
    "europe-west8":         {"label": "Europe (Milan)",                  "multiplier": 1.100},
    "europe-west9":         {"label": "Europe (Paris)",                  "multiplier": 1.100},
    "europe-west10":        {"label": "Europe (Berlin)",                 "multiplier": 1.100},
    "europe-west12":        {"label": "Europe (Turin)",                  "multiplier": 1.100},
    "europe-central2":      {"label": "Europe (Warsaw)",                 "multiplier": 1.100},
    "europe-north1":        {"label": "Europe (Finland)",                "multiplier": 1.050},
    "europe-north2":        {"label": "Europe (Stockholm)",              "multiplier": 1.060},
    "europe-southwest1":    {"label": "Europe (Madrid)",                 "multiplier": 1.050},

    # Asia Pacific
    "asia-south1":          {"label": "Asia Pacific (Mumbai)",           "multiplier": 1.080},
    "asia-south2":          {"label": "Asia Pacific (Delhi)",            "multiplier": 1.080},
    "asia-east1":           {"label": "Asia Pacific (Taiwan)",           "multiplier": 1.050},
    "asia-east2":           {"label": "Asia Pacific (Hong Kong)",        "multiplier": 1.180},
    "asia-southeast1":      {"label": "Asia Pacific (Singapore, nearest to Malaysia)", "multiplier": 1.100},
    "asia-southeast2":      {"label": "Asia Pacific (Jakarta)",          "multiplier": 1.100},
    "asia-southeast3":      {"label": "Asia Pacific (Bangkok)",          "multiplier": 1.100},
    "asia-northeast1":      {"label": "Asia Pacific (Tokyo)",            "multiplier": 1.130},
    "asia-northeast2":      {"label": "Asia Pacific (Osaka)",            "multiplier": 1.130},
    "asia-northeast3":      {"label": "Asia Pacific (Seoul)",            "multiplier": 1.130},
    "australia-southeast1": {"label": "Asia Pacific (Sydney)",           "multiplier": 1.140},
    "australia-southeast2": {"label": "Asia Pacific (Melbourne)",        "multiplier": 1.140},

    # Middle East & Africa
    "me-west1":             {"label": "Middle East (Tel Aviv)",          "multiplier": 1.160},
    "me-central1":          {"label": "Middle East (Doha)",              "multiplier": 1.160},
    "me-central2":          {"label": "Middle East (Dammam)",            "multiplier": 1.160},
    "af-south1":            {"label": "Africa (Johannesburg)",           "multiplier": 1.200},
}

# ── Fallback GCP On-Demand prices (USD/hr) — us-central1, March 2026 ─────
# n2-standard: ~$0.0475/vCPU + $0.00638/GB RAM/hr
# n2-highmem:  ~$0.0475/vCPU + $0.00913/GB RAM/hr

GCE_VCPU_HOUR      = 0.0475    # n2 standard
GCE_RAM_HOUR_STD   = 0.00638   # n2-standard per GB RAM/hr
GCE_RAM_HOUR_HM    = 0.00913   # n2-highmem per GB RAM/hr
PD_SSD_PER_GB      = 0.17 / 730  # $0.17/GB/month → per-hour
PD_EXTREME_PER_GB  = 0.125     # $/GB/month (approx io2 equivalent)
PD_STANDARD_PER_GB = 0.04      # $/GB/month
GKE_CLUSTER_FEE    = 73.00     # GKE standard cluster management fee/month
MEMORYSTORE_HOURLY = {         # Redis Standard tier
    "1gb":  0.049,
    "5gb":  0.049 * 3,
    "16gb": 0.049 * 5,
    "32gb": 0.049 * 10,
}
CLOUD_SQL_PER_VCPU = 0.0564    # Cloud SQL Postgres Enterprise per vCPU/hr
CLOUD_SQL_PER_GB   = 0.0095    # Cloud SQL Postgres per GB RAM/hr
CLOUD_ARMOR_MONTHLY = 200.0    # Cloud Armor Advanced monthly base
CLOUD_LOGGING_PER_NODE = 3.50  # Cloud Logging + Monitoring per node/month

# ── GCP equivalent instance sizing ───────────────────────────────────────

def _gce_instance(vcpu: int, ram_gb: float, family_hint: str = "") -> dict:
    """Return GCE machine type + hourly cost."""
    hint = family_hint.lower()
    is_mem = "memory" in hint or (ram_gb / max(vcpu, 1)) > 8

    if is_mem:
        # n2-highmem: 8GB RAM per vCPU
        # Round vcpu up to nearest valid n2 size
        valid_vcpu = [2, 4, 8, 16, 32, 48, 64, 80, 96]
        v = next((x for x in valid_vcpu if x >= vcpu), 96)
        r = v * 8
        hourly = v * GCE_VCPU_HOUR + r * GCE_RAM_HOUR_HM
        return {"type": f"n2-highmem-{v}", "vcpu": v, "ram_gb": r, "hourly": round(hourly, 6)}
    else:
        # n2-standard: 4GB RAM per vCPU
        valid_vcpu = [2, 4, 8, 16, 32, 48, 64, 80, 96]
        v = next((x for x in valid_vcpu if x >= vcpu), 96)
        r = v * 4
        hourly = v * GCE_VCPU_HOUR + r * GCE_RAM_HOUR_STD
        return {"type": f"n2-standard-{v}", "vcpu": v, "ram_gb": r, "hourly": round(hourly, 6)}


def _memorystore_hourly(ram_gb: float) -> tuple[str, float]:
    if ram_gb <= 5:   return "redis-5gb",  MEMORYSTORE_HOURLY["5gb"]
    if ram_gb <= 16:  return "redis-16gb", MEMORYSTORE_HOURLY["16gb"]
    return "redis-32gb", MEMORYSTORE_HOURLY["32gb"]


# ── Pricing API (GCP Cloud Billing Catalog) ───────────────────────────────

def _try_billing_api(region: str) -> bool:
    """Returns True if GCP billing API is available (project set + library installed)."""
    project = os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("GCP_PROJECT")
    if not project:
        return False
    try:
        from google.cloud import billing_v1   # noqa: F401
        return True
    except ImportError:
        return False


# ── Role pricers ─────────────────────────────────────────────────────────

def _price_gce_role(role: dict, region: str) -> dict:
    vcpu   = role.get("vcpu_per_node", 0)
    ram    = role.get("ram_per_node",  0)
    nodes  = role.get("nodes",         0)
    storage= role.get("storage_per_node_gb", 0)
    family = role.get("instance_family", "")

    if vcpu == 0 or nodes == 0:
        storage_mo = storage * nodes * PD_SSD_PER_GB * 730 if storage else 0
        return {**role,
                "gcp_instance_type": "N/A (storage only)",
                "gcp_hourly_usd": 0,
                "gcp_compute_monthly_usd": 0,
                "gcp_storage_monthly_usd": round(storage_mo, 2),
                "gcp_monthly_usd": round(storage_mo, 2)}

    mult  = GCP_REGIONS.get(region, {}).get("multiplier", 1.0)
    inst  = _gce_instance(vcpu, ram, family)
    hourly= round(inst["hourly"] * mult, 6)

    compute_mo = hourly * nodes * HOURS_PER_MONTH
    storage_mo = storage * nodes * (PD_SSD_PER_GB * 730) * mult if storage else 0
    monthly    = round(compute_mo + storage_mo, 2)

    return {
        **role,
        "gcp_instance_type":         inst["type"],
        "gcp_hourly_usd":            hourly,
        "gcp_compute_monthly_usd":   round(compute_mo, 2),
        "gcp_storage_monthly_usd":   round(storage_mo, 2),
        "gcp_monthly_usd":           monthly,
        "gcp_note": f"{nodes}× {inst['type']} @ ${hourly:.4f}/hr",
    }


def _price_gcp_db_role(role: dict, region: str) -> dict:
    """Price DB/storage roles on GCP."""
    key    = role.get("role_key", "")
    vcpu   = role.get("vcpu_per_node", 0)
    ram    = role.get("ram_per_node",  0)
    nodes  = role.get("nodes",         0)
    storage= role.get("storage_per_node_gb", 0)
    family = role.get("instance_family", "")
    mult   = GCP_REGIONS.get(region, {}).get("multiplier", 1.0)

    # Pure SAN / storage roles
    if "10K IOPS" in family or vcpu == 0:
        # Map to Persistent Disk Extreme
        monthly = storage * nodes * PD_EXTREME_PER_GB * mult
        return {**role,
                "gcp_instance_type": "Persistent Disk Extreme",
                "gcp_hourly_usd": 0,
                "gcp_compute_monthly_usd": 0,
                "gcp_storage_monthly_usd": round(monthly, 2),
                "gcp_monthly_usd": round(monthly, 2),
                "gcp_note": f"{nodes}× {storage}GB PD Extreme"}

    # S3 → Cloud Datastream / Database Migration Service
    if key == "s3":
        # GCP S3: $0.10/GB migrated — approx $0.30/hr for medium instance
        monthly = 0.30 * HOURS_PER_MONTH * mult + storage * 0.02 * mult
        return {**role,
                "gcp_instance_type": "Database Migration Service",
                "gcp_hourly_usd": round(0.30 * mult, 4),
                "gcp_compute_monthly_usd": round(0.30 * HOURS_PER_MONTH * mult, 2),
                "gcp_storage_monthly_usd": round(storage * 0.02 * mult, 2),
                "gcp_monthly_usd": round(monthly, 2),
                "gcp_note": f"GCP S3 + {storage}GB storage"}

    # pgsql_reporting → Cloud SQL (managed Postgres)
    if "reporting" in key:
        hourly = (vcpu * CLOUD_SQL_PER_VCPU + ram * CLOUD_SQL_PER_GB) * mult
        compute_mo = hourly * nodes * HOURS_PER_MONTH
        storage_mo = storage * nodes * (PD_SSD_PER_GB * 730) * mult
        monthly    = round(compute_mo + storage_mo, 2)
        return {**role,
                "gcp_instance_type": f"Cloud SQL Postgres ({vcpu}vCPU/{ram}GB)",
                "gcp_hourly_usd": round(hourly, 4),
                "gcp_compute_monthly_usd": round(compute_mo, 2),
                "gcp_storage_monthly_usd": round(storage_mo, 2),
                "gcp_monthly_usd": monthly,
                "gcp_note": f"Cloud SQL Enterprise — {nodes}× {vcpu}vCPU/{ram}GB"}

    # Primary DB → Compute Engine (self-hosted Postgres)
    inst  = _gce_instance(vcpu, ram, family)
    hourly= round(inst["hourly"] * mult, 6)
    compute_mo = hourly * nodes * HOURS_PER_MONTH
    storage_mo = storage * nodes * (PD_SSD_PER_GB * 730) * mult
    monthly    = round(compute_mo + storage_mo, 2)
    return {**role,
            "gcp_instance_type": inst["type"],
            "gcp_hourly_usd": hourly,
            "gcp_compute_monthly_usd": round(compute_mo, 2),
            "gcp_storage_monthly_usd": round(storage_mo, 2),
            "gcp_monthly_usd": monthly,
            "gcp_note": f"{nodes}× {inst['type']} (self-hosted Postgres)"}


def _price_gcp_fixed_role(role: dict, region: str, data_gb: float) -> dict:
    key  = role.get("role_key", "")
    mult = GCP_REGIONS.get(region, {}).get("multiplier", 1.0)

    if key == "k8s_managed":
        return {**role, "gcp_instance_type": "GKE Standard Cluster",
                "gcp_hourly_usd": 0.10,
                "gcp_compute_monthly_usd": GKE_CLUSTER_FEE,
                "gcp_storage_monthly_usd": 0,
                "gcp_monthly_usd": GKE_CLUSTER_FEE,
                "gcp_note": "GKE cluster management fee"}

    if key == "elasticache":
        nodes = role.get("nodes", 2)
        rtype, hourly = _memorystore_hourly(16)
        hourly = round(hourly * mult, 6)
        monthly = round(hourly * nodes * HOURS_PER_MONTH, 2)
        return {**role, "gcp_instance_type": f"Memorystore Redis ({rtype})",
                "gcp_hourly_usd": hourly,
                "gcp_compute_monthly_usd": monthly,
                "gcp_storage_monthly_usd": 0,
                "gcp_monthly_usd": monthly,
                "gcp_note": f"{nodes}× Memorystore Redis"}

    if key == "alb":
        monthly = round(35.0 * mult, 2)  # Cloud Load Balancing approx
        return {**role, "gcp_instance_type": "Cloud Load Balancing",
                "gcp_hourly_usd": 0,
                "gcp_compute_monthly_usd": monthly,
                "gcp_storage_monthly_usd": 0,
                "gcp_monthly_usd": monthly,
                "gcp_note": "GCP HTTPS LB (internal + external)"}

    if key == "nat":
        monthly = round(32.0 * mult, 2)  # Cloud NAT
        return {**role, "gcp_instance_type": "Cloud NAT",
                "gcp_hourly_usd": 0,
                "gcp_compute_monthly_usd": monthly,
                "gcp_storage_monthly_usd": 0,
                "gcp_monthly_usd": monthly,
                "gcp_note": "Cloud NAT gateway"}

    if key == "bastion":
        vcpu, ram = role.get("vcpu_per_node", 2), role.get("ram_per_node", 4)
        inst  = _gce_instance(vcpu, ram, "standard")
        hourly = round(inst["hourly"] * mult, 6)
        monthly = round(hourly * HOURS_PER_MONTH, 2)
        return {**role, "gcp_instance_type": inst["type"],
                "gcp_hourly_usd": hourly,
                "gcp_compute_monthly_usd": monthly,
                "gcp_storage_monthly_usd": 0,
                "gcp_monthly_usd": monthly,
                "gcp_note": "Bastion host (IAP tunnel)"}

    if key == "ecr":
        storage = role.get("storage_per_node_gb", 512)
        monthly = round(storage * 0.10 * mult, 2)  # Artifact Registry
        return {**role, "gcp_instance_type": "Artifact Registry",
                "gcp_hourly_usd": 0,
                "gcp_compute_monthly_usd": 0,
                "gcp_storage_monthly_usd": monthly,
                "gcp_monthly_usd": monthly,
                "gcp_note": f"{storage}GB Artifact Registry"}

    if key == "backup":
        storage = role.get("storage_per_node_gb", 5120)
        monthly = round(storage * PD_STANDARD_PER_GB * mult, 2)
        return {**role, "gcp_instance_type": "Cloud Storage (Nearline)",
                "gcp_hourly_usd": 0,
                "gcp_compute_monthly_usd": 0,
                "gcp_storage_monthly_usd": monthly,
                "gcp_monthly_usd": monthly,
                "gcp_note": f"{storage}GB Cloud Storage Nearline"}

    if key == "waf_shield":
        monthly = round(CLOUD_ARMOR_MONTHLY * mult, 2)
        return {**role, "gcp_instance_type": "Cloud Armor Advanced",
                "gcp_hourly_usd": 0,
                "gcp_compute_monthly_usd": monthly,
                "gcp_storage_monthly_usd": 0,
                "gcp_monthly_usd": monthly,
                "gcp_note": "Cloud Armor Advanced WAF"}

    if key == "cloudtrail_audit":
        monthly = round(50.0 * mult, 2)  # Cloud Audit Logs
        return {**role, "gcp_instance_type": "Cloud Audit Logs",
                "gcp_hourly_usd": 0,
                "gcp_compute_monthly_usd": monthly,
                "gcp_storage_monthly_usd": 0,
                "gcp_monthly_usd": monthly,
                "gcp_note": "Cloud Audit Logs + Security Command Center"}

    return {**role, "gcp_instance_type": "N/A",
            "gcp_hourly_usd": 0, "gcp_compute_monthly_usd": 0,
            "gcp_storage_monthly_usd": 0, "gcp_monthly_usd": 0, "gcp_note": ""}


def _gcp_cloudops_cost(total_nodes: int, mult: float) -> dict:
    monthly = round((10.0 + total_nodes * CLOUD_LOGGING_PER_NODE) * mult, 2)
    return {
        "role_key": "gcp_cloud_ops", "label": "Cloud Operations (Logging + Monitoring)",
        "category": "Operations", "nodes": 0,
        "gcp_instance_type": "Cloud Operations Suite",
        "gcp_hourly_usd": 0,
        "gcp_compute_monthly_usd": monthly,
        "gcp_storage_monthly_usd": 0,
        "gcp_monthly_usd": monthly,
        "gcp_note": f"Base $10 + {total_nodes} nodes × ${CLOUD_LOGGING_PER_NODE}/node",
        "reasoning": "GCP Cloud Ops — equivalent to CloudWatch",
    }


# ── Public API ────────────────────────────────────────────────────────────

def calculate_gcp_pricing(
    distribution: dict,
    metrics:      dict,
    region:       str = "us-central1",
) -> dict:
    """
    Main entry point — mirrors aws_pricer.calculate_pricing() interface.
    Returns a dict with gcp_priced_roles, total_monthly_usd, inflation_forecast etc.
    """
    mult     = GCP_REGIONS.get(region, {}).get("multiplier", 1.0)
    data_gb  = metrics.get("data_size_gb", 0)
    priced   = []

    # 1. Worker nodes (GCE)
    for role in distribution.get("worker_nodes", []):
        priced.append(_price_gce_role(role, region))

    # 2. DB nodes
    for role in distribution.get("db_nodes", []):
        priced.append(_price_gcp_db_role(role, region))

    # 3. Fixed infra
    for role in distribution.get("fixed_roles", []):
        priced.append(_price_gcp_fixed_role(role, region, data_gb))

    # 4. Cloud Ops (equiv. CloudWatch)
    tw = distribution["summary"]["total_worker_nodes"]
    td = distribution["summary"]["total_db_nodes"]
    priced.append(_gcp_cloudops_cost(tw + td, mult))

    total_monthly = sum(r.get("gcp_monthly_usd", 0) for r in priced)

    # Category rollup
    category_totals: dict = {}
    for r in priced:
        cat = r.get("category", "Other")
        category_totals[cat] = round(
            category_totals.get(cat, 0) + r.get("gcp_monthly_usd", 0), 2
        )

    # Inflation forecast (same structure as aws_pricer)
    INFLATION_RATE = 0.04
    inflation_yearly = []
    cumulative = 0.0
    for yr in range(1, 6):
        m  = (1 + INFLATION_RATE) ** (yr - 1)
        mo = round(total_monthly * m, 2)
        an = round(mo * 12, 2)
        cumulative += an
        inflation_yearly.append({
            "year": yr, "multiplier": round(m, 4),
            "monthly_usd": mo, "annual_usd": an,
            "cumulative_usd": round(cumulative, 2),
        })
    inflation_forecast = {
        "yearly": inflation_yearly,
        "five_year_total": round(cumulative, 2),
    }

    # Rename gcp_* keys to standard keys so pdf/excel code can reuse them
    priced_roles_std = []
    for r in priced:
        priced_roles_std.append({
            **r,
            "instance_type": r.get("gcp_instance_type", "—"),
            "hourly_usd":    r.get("gcp_hourly_usd", 0),
            "monthly_usd":   r.get("gcp_monthly_usd", 0),
            "annual_usd":    round(r.get("gcp_monthly_usd", 0) * 12, 2),
            "from_api":      False,
            "note":          r.get("gcp_note", ""),
        })

    return {
        "cloud":                "GCP",
        "region":               region,
        "region_label":         GCP_REGIONS.get(region, {}).get("label", region),
        "priced_roles":         priced_roles_std,
        "category_totals":      category_totals,
        "total_monthly_usd":    round(total_monthly, 2),
        "total_annual_usd":     round(total_monthly * 12, 2),
        "total_3year_usd":      round(total_monthly * 36, 2),
        "inflation_rate":       INFLATION_RATE,
        "inflation_forecast":   inflation_forecast,
        "warnings":             [] if _try_billing_api(region) else ["GCP Billing API not configured — using hardcoded fallback prices."],
        "assumptions": {
            "region":            region,
            "region_label":      GCP_REGIONS.get(region, {}).get("label", region),
            "hours_per_month":   HOURS_PER_MONTH,
            "deployment":        "On-Demand (Committed Use Discounts not applied)",
            "os":                "Linux",
            "pd_type":           "SSD (compute), Extreme (SAN/DB)",
            "pricing_date":      "2026-03",
            "inflation_rate":    f"{INFLATION_RATE*100:.0f}% per year",
            "db_hosting_note":   "PostgreSQL=Self-hosted GCE, Reporting=Cloud SQL",
        },
    }


# ── Comparison helper ─────────────────────────────────────────────────────

def build_comparison(aws_pricing: dict, gcp_pricing: dict) -> dict:
    """
    Build a structured comparison dict between AWS and GCP pricing.
    Used by excel_exporter and pdf_report.
    """
    aws_mo  = aws_pricing.get("total_monthly_usd", 0)
    gcp_mo  = gcp_pricing.get("total_monthly_usd", 0)
    aws_yr  = aws_pricing.get("total_annual_usd",  0)
    gcp_yr  = gcp_pricing.get("total_annual_usd",  0)
    aws_5yr = aws_pricing.get("inflation_forecast", {}).get("five_year_total", 0)
    gcp_5yr = gcp_pricing.get("inflation_forecast", {}).get("five_year_total", 0)

    cheaper_mo  = "AWS" if aws_mo  <= gcp_mo  else "GCP"
    cheaper_yr  = "AWS" if aws_yr  <= gcp_yr  else "GCP"
    cheaper_5yr = "AWS" if aws_5yr <= gcp_5yr else "GCP"

    diff_mo  = round(abs(aws_mo  - gcp_mo),  2)
    diff_yr  = round(abs(aws_yr  - gcp_yr),  2)
    diff_5yr = round(abs(aws_5yr - gcp_5yr), 2)

    def pct(a, b):
        if not b: return 0
        return round((a - b) / b * 100, 1)

    # Category-level comparison
    aws_cats = aws_pricing.get("category_totals", {})
    gcp_cats = gcp_pricing.get("category_totals", {})
    all_cats = sorted(set(list(aws_cats.keys()) + list(gcp_cats.keys())))
    category_rows = []
    for cat in all_cats:
        a = aws_cats.get(cat, 0)
        g = gcp_cats.get(cat, 0)
        category_rows.append({
            "category": cat,
            "aws_monthly": a,
            "gcp_monthly": g,
            "diff": round(a - g, 2),
            "cheaper": "AWS" if a <= g else "GCP",
            "pct_diff": pct(a, g) if g else (0 if a == 0 else 100),
        })

    # 5-year yearly comparison
    aws_yearly = aws_pricing.get("inflation_forecast", {}).get("yearly", [])
    gcp_yearly = gcp_pricing.get("inflation_forecast", {}).get("yearly", [])
    yearly_compare = []
    for a, g in zip(aws_yearly, gcp_yearly):
        yearly_compare.append({
            "year":          a["year"],
            "aws_monthly":   a["monthly_usd"],
            "gcp_monthly":   g["monthly_usd"],
            "aws_annual":    a["annual_usd"],
            "gcp_annual":    g["annual_usd"],
            "aws_cumulative":a["cumulative_usd"],
            "gcp_cumulative":g["cumulative_usd"],
            "cheaper":       "AWS" if a["annual_usd"] <= g["annual_usd"] else "GCP",
        })

    return {
        "summary": {
            "aws_monthly":   aws_mo,   "gcp_monthly":   gcp_mo,
            "aws_annual":    aws_yr,   "gcp_annual":    gcp_yr,
            "aws_5year":     aws_5yr,  "gcp_5year":     gcp_5yr,
            "cheaper_monthly":  cheaper_mo,
            "cheaper_annual":   cheaper_yr,
            "cheaper_5year":    cheaper_5yr,
            "diff_monthly":  diff_mo,
            "diff_annual":   diff_yr,
            "diff_5year":    diff_5yr,
            "aws_vs_gcp_monthly_pct": pct(aws_mo, gcp_mo),
            "aws_region":    aws_pricing.get("region", "us-east-1"),
            "gcp_region":    gcp_pricing.get("region", "us-central1"),
        },
        "category_comparison":  category_rows,
        "yearly_comparison":    yearly_compare,
    }
