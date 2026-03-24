"""
env_pricer.py
─────────────────────────────────────────────────────────────
Prices three additional environments based on actual node specs
read from Cloud-sizing-AWS-pgsql-SAAS.xlsx:

  1. Pre-Prod / SIT / UAT  (Pre-Prod_sit_uat sheet)
  2. DR                    (DR-5Yr sheet, 5-year forecast)

Only relevant for SaaS / PostgreSQL customers.
For SQL Server / Oracle (managed RDS) customers, DR and Pre-Prod
use smaller RDS Multi-AZ instances and are priced differently.
─────────────────────────────────────────────────────────────
"""

from __future__ import annotations
import json
import boto3
from aws_pricer import AWS_REGIONS

HOURS_PER_MONTH = 730
INFLATION_RATE  = 0.04

# ── Fallback prices matching aws_pricer.py ────────────────────────────────
EC2_FALLBACK = {
    "m5.large": 0.096, "m5.xlarge": 0.192, "m5.2xlarge": 0.384,
    "m5.4xlarge": 0.768, "m5.8xlarge": 1.536,
    "r5.large": 0.126, "r5.xlarge": 0.252, "r5.2xlarge": 0.504,
    "r5.4xlarge": 1.008, "r5.8xlarge": 2.016, "r5.16xlarge": 4.032,
    "cache.r6g.large": 0.166,
}
EBS_GP3   = 0.08
EBS_IO2   = 0.125
S3_PER_GB = 0.023
ALB_MONTHLY = 16.43
NAT_MONTHLY = 16.00   # per gateway
EKS_MONTHLY = 73.00
ELASTICACHE_HOURLY = 0.166

# ── Pre-Prod / SIT / UAT node spec (from Pre-Prod_sit_uat sheet) ──────────
# Exactly as read from the workbook
PREPROD_ROLES = [
    # Kubernetes
    {"label": "Cloud Managed K8s",                              "category": "Kubernetes",    "nodes": 1,  "vcpu": 0,  "ram": 0,   "storage_gb": 0,    "family": "k8s"},
    {"label": "Worker Nodes (Web, Mobile, WebAPI)",             "category": "Kubernetes",    "nodes": 2,  "vcpu": 16, "ram": 32,  "storage_gb": 300,  "family": "compute"},
    {"label": "Worker Nodes (Graphana & Prometheus) – optional","category": "Kubernetes",    "nodes": 1,  "vcpu": 8,  "ram": 16,  "storage_gb": 512,  "family": "compute"},
    {"label": "Worker Nodes (EFK) – optional",                  "category": "Kubernetes",    "nodes": 1,  "vcpu": 16, "ram": 32,  "storage_gb": 512,  "family": "compute"},
    # DB (Pre-prod uses lighter spec: 8vCPU/64GB = 1 node)
    {"label": "DB Server (Pre-Prod)",                           "category": "PGSQL DB",      "nodes": 1,  "vcpu": 8,  "ram": 64,  "storage_gb": 300,  "family": "memory"},
    {"label": "Storage: SAN Pre-Prod",                          "category": "PGSQL DB",      "nodes": 1,  "vcpu": 0,  "ram": 0,   "storage_gb": 1000, "family": "san"},
    {"label": "Storage: SAN SIT",                               "category": "PGSQL DB",      "nodes": 1,  "vcpu": 0,  "ram": 0,   "storage_gb": 500,  "family": "san"},
    {"label": "Storage: SAN UAT",                               "category": "PGSQL DB",      "nodes": 1,  "vcpu": 0,  "ram": 0,   "storage_gb": 500,  "family": "san"},
    # S3
    {"label": "S3 Storage + Replication",                      "category": "S3",           "nodes": 1,  "vcpu": 0,  "ram": 0,   "storage_gb": 1500, "family": "s3"},
    # Caching
    {"label": "Caching Service (ElastiCache)",                  "category": "Caching",       "nodes": 1,  "vcpu": 4,  "ram": 16,  "storage_gb": 0,    "family": "cache"},
    # Infra
    {"label": "Load Balancer (Internal + External)",            "category": "Infrastructure","nodes": 1,  "vcpu": 0,  "ram": 0,   "storage_gb": 0,    "family": "alb"},
    {"label": "NAT Gateway",                                    "category": "Infrastructure","nodes": 2,  "vcpu": 0,  "ram": 0,   "storage_gb": 0,    "family": "nat"},
    {"label": "Bastion Host",                                   "category": "Infrastructure","nodes": 1,  "vcpu": 2,  "ram": 4,   "storage_gb": 300,  "family": "compute"},
    {"label": "Image Registry (ECR)",                           "category": "Infrastructure","nodes": 1,  "vcpu": 0,  "ram": 0,   "storage_gb": 500,  "family": "ecr"},
    {"label": "Back Up – DB & Infra Logs",                      "category": "Backup",        "nodes": 1,  "vcpu": 0,  "ram": 0,   "storage_gb": 1500, "family": "s3"},
]

# ── DR node spec (from DR-5Yr sheet) — mirrors PROD but in separate region ─
DR_ROLES = [
    {"label": "Cloud Managed K8s (DR)",                         "category": "Kubernetes",    "nodes": 1,  "vcpu": 0,  "ram": 0,   "storage_gb": 0,    "family": "k8s"},
    {"label": "Worker Nodes (Web, Mobile, WebAPI) – DR",        "category": "Kubernetes",    "nodes": 4,  "vcpu": 16, "ram": 32,  "storage_gb": 256,  "family": "compute"},
    {"label": "Worker Nodes (Graphana) – DR",                   "category": "Kubernetes",    "nodes": 2,  "vcpu": 8,  "ram": 16,  "storage_gb": 512,  "family": "compute"},
    {"label": "Worker Nodes (EFK) – DR",                        "category": "Kubernetes",    "nodes": 2,  "vcpu": 8,  "ram": 16,  "storage_gb": 1024, "family": "compute"},
    {"label": "DB Server Primary – DR",                         "category": "PGSQL DB",      "nodes": 2,  "vcpu": 32, "ram": 128, "storage_gb": 300,  "family": "memory"},
    {"label": "DB Cluster (etcd+haproxy) – DR",                 "category": "PGSQL DB",      "nodes": 4,  "vcpu": 2,  "ram": 8,   "storage_gb": 100,  "family": "memory"},
    {"label": "Storage: SAN Primary – DR",                      "category": "PGSQL DB",      "nodes": 2,  "vcpu": 0,  "ram": 0,   "storage_gb": 3000, "family": "san"},
    {"label": "Reporting DB – DR",                              "category": "PGSQL DB",      "nodes": 1,  "vcpu": 32, "ram": 128, "storage_gb": 300,  "family": "memory"},
    {"label": "Storage: SAN Reporting – DR",                    "category": "PGSQL DB",      "nodes": 1,  "vcpu": 0,  "ram": 0,   "storage_gb": 3000, "family": "san"},
    {"label": "S3 Storage + Replication – DR",                 "category": "S3",           "nodes": 1,  "vcpu": 0,  "ram": 0,   "storage_gb": 8000, "family": "s3"},
    {"label": "Elasticache Service – DR",                       "category": "Caching",       "nodes": 2,  "vcpu": 4,  "ram": 16,  "storage_gb": 0,    "family": "cache"},
    {"label": "Load Balancer – DR",                             "category": "Infrastructure","nodes": 2,  "vcpu": 0,  "ram": 0,   "storage_gb": 0,    "family": "alb"},
    {"label": "NAT Gateway – DR",                               "category": "Infrastructure","nodes": 2,  "vcpu": 0,  "ram": 0,   "storage_gb": 0,    "family": "nat"},
    {"label": "Bastion Host – DR",                              "category": "Infrastructure","nodes": 1,  "vcpu": 2,  "ram": 4,   "storage_gb": 300,  "family": "compute"},
    {"label": "Image Registry (ECR) – DR",                      "category": "Infrastructure","nodes": 1,  "vcpu": 0,  "ram": 0,   "storage_gb": 512,  "family": "ecr"},
    {"label": "Back Up – DR",                                   "category": "Backup",        "nodes": 1,  "vcpu": 0,  "ram": 0,   "storage_gb": 5120, "family": "s3"},
]


# ── Pricing helpers ───────────────────────────────────────────────────────

def _init_pricing():
    try:
        return boto3.client("pricing", region_name="us-east-1")
    except Exception:
        return None


def _ec2_instance(vcpu: int, ram: float) -> str:
    family = "r5" if (ram / max(vcpu, 1)) > 8 else "m5"
    for c, r, sz in [(2,8,"large"),(4,16,"xlarge"),(8,32,"2xlarge"),
                     (16,64,"4xlarge"),(32,128,"8xlarge"),(64,256,"16xlarge")]:
        if vcpu <= c and ram <= r:
            return f"{family}.{sz}"
    return f"{family}.16xlarge"


def _ec2_hourly(client, itype: str, region: str) -> tuple:
    mult = AWS_REGIONS.get(region, {}).get("multiplier", 1.0)
    if not client:
        return EC2_FALLBACK.get(itype, 0.384) * mult, False
    try:
        resp = client.get_products(
            ServiceCode="AmazonEC2",
            Filters=[
                {"Type":"TERM_MATCH","Field":"instanceType",   "Value":itype},
                {"Type":"TERM_MATCH","Field":"regionCode",     "Value":region},
                {"Type":"TERM_MATCH","Field":"tenancy",        "Value":"Shared"},
                {"Type":"TERM_MATCH","Field":"operatingSystem","Value":"Linux"},
                {"Type":"TERM_MATCH","Field":"preInstalledSw", "Value":"NA"},
                {"Type":"TERM_MATCH","Field":"capacitystatus", "Value":"Used"},
            ],
        )
        if resp["PriceList"]:
            item  = json.loads(resp["PriceList"][0])
            term  = next(iter(item["terms"]["OnDemand"].values()))
            dim   = next(iter(term["priceDimensions"].values()))
            price = float(dim["pricePerUnit"]["USD"])
            if price > 0:
                return price, True
    except Exception:
        pass
    return EC2_FALLBACK.get(itype, 0.384) * mult, False


def _price_role(role: dict, client, region: str) -> dict:
    """Price a single role dict. Returns role + monthly_usd + instance_type."""
    fam   = role["family"]
    nodes = role["nodes"]
    vcpu  = role["vcpu"]
    ram   = role["ram"]
    stor  = role["storage_gb"]

    if fam == "k8s":
        return {**role, "instance_type": "EKS", "monthly_usd": EKS_MONTHLY, "note": "EKS control plane"}

    if fam == "alb":
        m = ALB_MONTHLY * nodes
        return {**role, "instance_type": "ALB", "monthly_usd": round(m,2), "note": f"{nodes}× ALB"}

    if fam == "nat":
        m = NAT_MONTHLY * nodes
        return {**role, "instance_type": "NAT", "monthly_usd": round(m,2), "note": f"{nodes}× NAT"}

    if fam == "cache":
        m = ELASTICACHE_HOURLY * nodes * HOURS_PER_MONTH
        return {**role, "instance_type": "cache.r6g.large", "monthly_usd": round(m,2), "note": f"{nodes}× ElastiCache"}

    if fam == "s3":
        m = stor * S3_PER_GB
        return {**role, "instance_type": "S3", "monthly_usd": round(m,2), "note": f"{stor}GB S3"}

    if fam == "ecr":
        m = stor * 0.10
        return {**role, "instance_type": "ECR", "monthly_usd": round(m,2), "note": f"{stor}GB ECR"}

    if fam == "san":
        m = stor * nodes * EBS_IO2
        return {**role, "instance_type": "EBS io2", "monthly_usd": round(m,2), "note": f"{nodes}× {stor}GB io2"}

    if fam == "s3":
        s3_m = 0.154 * HOURS_PER_MONTH
        s3_m  = stor * S3_PER_GB
        m     = s3_m + s3_m
        return {**role, "instance_type": "s3.c5.large", "monthly_usd": round(m,2),
                "note": f"S3 replication + {stor}GB S3"}

    # compute / memory
    if vcpu == 0:
        return {**role, "instance_type": "N/A", "monthly_usd": 0, "note": "No compute"}

    if fam in ("compute", "memory"):
        itype = _ec2_instance(vcpu, ram)
        hr, from_api = _ec2_hourly(client, itype, region)
        compute = hr * nodes * HOURS_PER_MONTH
        storage = stor * nodes * EBS_GP3 if stor > 0 else 0
        m       = compute + storage
        return {
            **role,
            "instance_type": itype,
            "hourly_usd":    round(hr, 4),
            "monthly_usd":   round(m, 2),
            "from_api":      from_api,
            "note":          f"{nodes}× {itype} @ ${hr:.4f}/hr + {stor}GB EBS",
        }

    return role


def _price_env(roles: list, client, region: str) -> dict:
    """Price a list of roles. Returns priced list + totals + category breakdown."""
    priced = []
    category_totals = {}
    total = 0.0

    for r in roles:
        pr = _price_role(r, client, region)
        priced.append(pr)
        total += pr["monthly_usd"]
        category_totals[pr["category"]] = round(category_totals.get(pr["category"], 0) + pr["monthly_usd"], 2)

    return {
        "priced_roles":    priced,
        "category_totals": category_totals,
        "monthly_usd":     round(total, 2),
        "annual_usd":      round(total * 12, 2),
    }


def _rds_preprod_pricing(db_type: str) -> dict:
    """Pre-Prod pricing for SQL Server / Oracle uses RDS instead of EC2."""
    if db_type == "SQL Server":
        monthly = 850.0   # db.r5.2xlarge RDS SQL Server Multi-AZ estimate
        note    = "RDS SQL Server db.r5.2xlarge Single-AZ (Pre-Prod)"
    else:  # Oracle
        monthly = 1100.0
        note    = "RDS Oracle db.r5.2xlarge Single-AZ (Pre-Prod)"

    return {"monthly_usd": monthly, "note": note,
            "instance_type": "db.r5.2xlarge", "category": "PGSQL DB"}


def _rds_dr_pricing(db_type: str) -> dict:
    """DR pricing for SQL Server / Oracle — RDS Multi-AZ in DR region."""
    if db_type == "SQL Server":
        monthly = 3200.0
        note    = "RDS SQL Server db.r5.4xlarge Multi-AZ DR"
    else:
        monthly = 4500.0
        note    = "RDS Oracle db.r5.4xlarge Multi-AZ DR"
    return {"monthly_usd": monthly, "note": note,
            "instance_type": "db.r5.4xlarge", "category": "Managed DB"}


# ── Public API ────────────────────────────────────────────────────────────

def price_additional_environments(db_type: str, deployment: str, metrics: dict, preprod_region: str = "us-east-1", dr_region: str = "us-east-1") -> dict:
    """
    Main entry point for pricing Pre-Prod/SIT/UAT and DR.
    Returns:
    {
        "preprod_sit_uat": { "priced_roles": [...], "monthly_usd": ..., "annual_usd": ... },
        "dr":              { "priced_roles": [...], "monthly_usd": ..., "annual_usd": ..., "five_year_forecast": ... },
        "combined_monthly": float,
        "db_type": str,
        "db_note": str,
    }
    """
    client = _init_pricing()

    is_postgres = db_type == "PostgreSQL"

    # ── Pre-Prod / SIT / UAT ─────────────────────────────────────────────
    if is_postgres:
        preprod = _price_env(PREPROD_ROLES, client, preprod_region)
    else:
        # Replace PostgreSQL DB roles with RDS equivalent
        rds_extra  = _rds_preprod_pricing(db_type)
        non_db_roles = [r for r in PREPROD_ROLES if r["category"] != "PGSQL DB"]
        preprod    = _price_env(non_db_roles, client, preprod_region)
        preprod["monthly_usd"] += rds_extra["monthly_usd"]
        preprod["annual_usd"]   = round(preprod["monthly_usd"] * 12, 2)
        preprod["priced_roles"].append(rds_extra)
        preprod["category_totals"]["Managed DB"] = rds_extra["monthly_usd"]

    # ── DR ────────────────────────────────────────────────────────────────
    if is_postgres:
        dr_result = _price_env(DR_ROLES, client, dr_region)
    else:
        rds_extra  = _rds_dr_pricing(db_type)
        non_db_roles = [r for r in DR_ROLES if r["category"] != "PGSQL DB"]
        dr_result  = _price_env(non_db_roles, client, dr_region)
        dr_result["monthly_usd"] += rds_extra["monthly_usd"]
        dr_result["annual_usd"]   = round(dr_result["monthly_usd"] * 12, 2)
        dr_result["priced_roles"].append(rds_extra)
        dr_result["category_totals"]["Managed DB"] = rds_extra["monthly_usd"]

    # DR 5-year inflation forecast
    dr_forecast = {}
    cumulative  = 0.0
    for yr in range(1, 6):
        annual = round(dr_result["monthly_usd"] * 12 * ((1 + INFLATION_RATE) ** yr), 2)
        dr_forecast[f"year_{yr}"] = {"annual_usd": annual, "multiplier": round((1+INFLATION_RATE)**yr, 4)}
        cumulative += annual
    dr_forecast["five_year_total"] = round(cumulative, 2)
    dr_result["five_year_forecast"] = dr_forecast

    db_notes = {
        "PostgreSQL":  "Self-Hosted on EC2 — Patroni HA, no licensing cost",
        "SQL Server":  "AWS RDS Managed — commercial license, automated HA/backups",
        "Oracle":      "AWS RDS Managed — Oracle BYOL or License Included, automated HA",
    }

    return {
        "preprod_sit_uat":   preprod,
        "dr":                dr_result,
        "combined_monthly":  round(preprod["monthly_usd"] + dr_result["monthly_usd"], 2),
        "db_type":           db_type,
        "db_note":           db_notes.get(db_type, ""),
        "is_saas":           is_postgres,
    }