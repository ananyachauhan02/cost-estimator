"""
env_pricer.py
─────────────────────────────────────────────────────────────
Prices three additional environments based on actual production
metrics extracted from the sizing template:

  1. Pre-Prod / SIT / UAT  — scaled at ~40% of Production
  2. DR                    — scaled at ~60% of Production
                             with 5-year inflation forecast

All node counts and storage sizes are derived dynamically from
the metrics dict (total_workernodes, postgres_ram_gb, data_size_gb,
s3_size_gb) so DR/Pre-Prod costs always make logical sense
relative to Production.
─────────────────────────────────────────────────────────────
"""

from __future__ import annotations
import json
import math
import boto3
from aws_pricer import (
    AWS_REGIONS,
    _init_ec2,
    _instance_candidates,
    _resolve_ec2_instance,
)

HOURS_PER_MONTH  = 730
INFLATION_RATE   = 0.04

# Scaling factors relative to Production
DR_SCALE       = 0.60   # DR = 60% of prod compute (Pilot Light / Warm Standby)
PREPROD_SCALE  = 0.40   # Pre-Prod = 40% of prod compute

# ── Fallback prices (USD/hr) matching aws_pricer.py ──────────────────────
EC2_FALLBACK = {
    "t3.medium":   0.0416,
    "m5.large":    0.096,  "m5.xlarge":   0.192,  "m5.2xlarge":  0.384,
    "m5.4xlarge":  0.768,  "m5.8xlarge":  1.536,  "m5.12xlarge": 2.304,
    "r5.large":    0.126,  "r5.xlarge":   0.252,  "r5.2xlarge":  0.504,
    "r5.4xlarge":  1.008,  "r5.8xlarge":  2.016,  "r5.12xlarge": 3.024,
    "r5.16xlarge": 4.032,
    "c6i.large":    0.085,  "c6i.xlarge":   0.170,  "c6i.2xlarge":  0.340,
    "c6i.4xlarge":  0.680,  "c6i.8xlarge":  1.360,  "c6i.12xlarge": 2.040,
    "c6i.16xlarge": 2.720,
    # AMD EPYC for BYOL
    "c6a.large":    0.085,  "c6a.xlarge":   0.170,  "c6a.2xlarge":  0.340,
    "c6a.4xlarge":  0.680,  "c6a.8xlarge":  1.360,  "c6a.12xlarge": 2.040,
    "c6a.16xlarge": 2.720,
    "r6a.large":    0.110,  "r6a.xlarge":   0.220,  "r6a.2xlarge":  0.440,
    "r6a.4xlarge":  0.880,  "r6a.8xlarge":  1.760,  "r6a.12xlarge": 2.640,
    "r6a.16xlarge": 3.520,
}
EBS_GP3_PER_GB      = 0.08
EBS_IO2_PER_GB      = 0.125
S3_PER_GB           = 0.023
ECR_PER_GB          = 0.10
ALB_MONTHLY         = 16.43
NAT_MONTHLY         = 16.00   # per gateway
EKS_MONTHLY         = 73.00
ELASTICACHE_HOURLY  = 0.166   # cache.r6g.large
CLOUDWATCH_BASE     = 10.0
CLOUDWATCH_PER_NODE = 3.50


# ── Instance sizing helper ────────────────────────────────────────────────

def _ec2_instance(vcpu: int, ram_gb: float, family_hint: str = "") -> str:
    """Pick preferred EC2 instance type from the shared Intel/AMD family logic."""
    return _instance_candidates(vcpu, ram_gb, family_hint)[0]


def _init_pricing():
    try:
        return boto3.client("pricing", region_name="us-east-1")
    except Exception:
        return None


def _ec2_hourly(client, itype: str, region: str) -> tuple:
    """Return (hourly_usd, from_api). Falls back to hardcoded estimates."""
    mult = AWS_REGIONS.get(region, {}).get("multiplier", 1.0)
    if not client:
        return round(EC2_FALLBACK.get(itype, 0.384) * mult, 6), False
    try:
        resp = client.get_products(
            ServiceCode="AmazonEC2",
            Filters=[
                {"Type": "TERM_MATCH", "Field": "instanceType",    "Value": itype},
                {"Type": "TERM_MATCH", "Field": "regionCode",      "Value": region},
                {"Type": "TERM_MATCH", "Field": "tenancy",         "Value": "Shared"},
                {"Type": "TERM_MATCH", "Field": "operatingSystem", "Value": "Linux"},
                {"Type": "TERM_MATCH", "Field": "preInstalledSw",  "Value": "NA"},
                {"Type": "TERM_MATCH", "Field": "capacitystatus",  "Value": "Used"},
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
    return round(EC2_FALLBACK.get(itype, 0.384) * mult, 6), False


# ── Dynamic environment builder ───────────────────────────────────────────

def _build_env_roles(
    metrics:    dict,
    scale:      float,
    env_label:  str,
    region:     str,
    pricing_client,
    ec2_client,
    db_type:    str = "PostgreSQL",
    single_az:  bool = True,
    deployment: str = "saas",  # "saas" or "onprem"
) -> list:
    """
    Build a list of priced roles for one environment (Pre-Prod or DR),
    scaling everything from actual Production metrics.

    scale=0.40 → Pre-Prod/SIT/UAT
    scale=0.60 → DR
    
    deployment="onprem" → Uses EC2 instances for ALL components (SQL Server BYOL on AMD)
    deployment="saas"   → Uses RDS for databases (PostgreSQL only)
    """
    mult = AWS_REGIONS.get(region, {}).get("multiplier", 1.0)

    # ── Derive production node counts ──────────────────────────────────────
    prod_worker_nodes = int(metrics.get("total_workernodes", 9))
    prod_vcpu_per_node = int(
        metrics.get("total_vcpus_workernode", prod_worker_nodes * 16)
        / max(prod_worker_nodes, 1)
    )
    prod_ram_per_node = int(
        metrics.get("total_memory_workernode_gb", prod_worker_nodes * 32)
        / max(prod_worker_nodes, 1)
    )
    data_gb   = int(metrics.get("data_size_gb",  2100))
    s3_gb     = int(metrics.get("s3_size_gb",    5900))

    # Derive DB sizing from production DB RAM
    if db_type == "Oracle":
        prod_db_ram   = int(metrics.get("oracle_ram_gb",     128))
        prod_db_vcpu  = max(4, prod_db_ram // 4)
    elif db_type == "SQL Server":
        prod_db_ram   = int(metrics.get("sql_server_ram_gb", 128))
        prod_db_vcpu  = max(4, prod_db_ram // 4)
    else:
        prod_db_ram   = int(metrics.get("postgres_ram_gb",   128))
        prod_db_vcpu  = max(4, prod_db_ram // 4)

    # ── Scale everything ───────────────────────────────────────────────────
    env_worker_nodes  = max(1, math.ceil(prod_worker_nodes * scale))
    env_vcpu_per_node = max(4, prod_vcpu_per_node)
    env_ram_per_node  = max(16, prod_ram_per_node)

    # DB: floor at sensible minimum
    env_db_ram  = max(32, math.ceil(prod_db_ram * scale / 8) * 8)   # round to 8GB
    env_db_vcpu = max(4,  math.ceil(prod_db_vcpu * scale / 2) * 2)  # round to 2 vCPU
    env_db_nodes = 2 if not single_az else 1

    # Storage scales with data
    env_data_gb = max(300, math.ceil(data_gb * scale))
    env_s3_gb   = max(500, math.ceil(s3_gb   * scale))

    # Worker node storage per node (256GB baseline, scale down for pre-prod)
    worker_storage = 256 if scale >= 0.55 else 300

    # ── EC2 instance types ─────────────────────────────────────────────────
    worker_itype, worker_hr, worker_from_api = _resolve_ec2_instance(
        env_vcpu_per_node, env_ram_per_node, "", pricing_client, ec2_client, region
    )
    
    # For on-prem SQL Server BYOL, use AMD EPYC instances (more cost-effective)
    if deployment == "onprem" and db_type == "SQL Server":
        db_itype, db_hr, db_from_api = _resolve_ec2_instance(
            env_db_vcpu, env_db_ram, "amd", pricing_client, ec2_client, region
        )
    else:
        db_itype, db_hr, db_from_api = _resolve_ec2_instance(
            env_db_vcpu, env_db_ram, "", pricing_client, ec2_client, region
        )
    
    bastion_itype= "t3.medium"
    bastion_hr,_ = _ec2_hourly(pricing_client, bastion_itype, region)

    priced = []
    
    # For on-prem deployments, use simpler infrastructure (no managed EKS)
    if deployment == "onprem":
        # Skip EKS, use simple K8s cluster marker
        priced.append({
            "category": "Kubernetes",
            "label":    f"Self-Managed K8s / OpenShift ({env_label})",
            "nodes": 1, "vcpu": 0, "ram": 0,
            "instance_type": "K8s-Self-Managed",
            "monthly_usd": 0.00,
            "note": "Self-hosted Kubernetes (no managed service cost)",
        })
    else:
        # ── EKS / K8s ──────────────────────────────────────────────────────
        priced.append({
            "category": "Kubernetes",
            "label":    f"Cloud Managed K8s ({env_label})",
            "nodes": 1, "vcpu": 0, "ram": 0,
            "instance_type": "EKS",
            "monthly_usd": EKS_MONTHLY,
            "note": "EKS managed control plane",
        })

    # ── Worker nodes ───────────────────────────────────────────────────────
    worker_compute = worker_hr * env_worker_nodes * HOURS_PER_MONTH
    worker_storage_cost = worker_storage * env_worker_nodes * EBS_GP3_PER_GB * mult
    priced.append({
        "category": "Kubernetes",
        "label":    f"Worker Nodes (Web, Mobile, WebAPI) – {env_label}",
        "nodes": env_worker_nodes,
        "vcpu": env_vcpu_per_node, "ram": env_ram_per_node,
        "instance_type": worker_itype,
        "hourly_usd": round(worker_hr, 4),
        "monthly_usd": round(worker_compute + worker_storage_cost, 2),
        "note": f"{env_worker_nodes}× {worker_itype} @ ${worker_hr:.4f}/hr + {worker_storage}GB EBS",
        "from_api": worker_from_api,
    })

    # ── Infra / monitoring workers (Grafana + EFK) ─────────────────────────
    # Scale: 1 node for pre-prod, 2 for DR
    infra_nodes = 2 if scale >= 0.55 else 1
    infra_vcpu, infra_ram = 8, 16
    infra_storage = 512
    infra_itype, infra_hr, infra_from_api = _resolve_ec2_instance(
        infra_vcpu, infra_ram, "", pricing_client, ec2_client, region
    )
    infra_compute = infra_hr * infra_nodes * HOURS_PER_MONTH
    infra_stor_cost = infra_storage * infra_nodes * EBS_GP3_PER_GB * mult
    priced.append({
        "category": "Kubernetes",
        "label":    f"Worker Nodes (Monitoring/EFK) – {env_label}",
        "nodes": infra_nodes,
        "vcpu": infra_vcpu, "ram": infra_ram,
        "instance_type": infra_itype,
        "hourly_usd": round(infra_hr, 4),
        "monthly_usd": round(infra_compute + infra_stor_cost, 2),
        "note": f"{infra_nodes}× {infra_itype} @ ${infra_hr:.4f}/hr + {infra_storage}GB EBS",
        "from_api": infra_from_api,
    })

    # ── Database primary nodes ─────────────────────────────────────────────
    db_compute = db_hr * env_db_nodes * HOURS_PER_MONTH
    db_stor_cost = 300 * env_db_nodes * EBS_GP3_PER_GB * mult
    db_cat = (
        "PGSQL DB" if db_type == "PostgreSQL"
        else f"{db_type} DB"
    )
    priced.append({
        "category": db_cat,
        "label":    f"DB Server (Primary) – {env_label}",
        "nodes": env_db_nodes,
        "vcpu": env_db_vcpu, "ram": env_db_ram,
        "instance_type": db_itype,
        "hourly_usd": round(db_hr, 4),
        "monthly_usd": round(db_compute + db_stor_cost, 2),
        "note": f"{env_db_nodes}× {db_itype} @ ${db_hr:.4f}/hr + 300GB EBS",
        "from_api": db_from_api,
    })

    # ── SAN storage ────────────────────────────────────────────────────────
    san_cost = env_data_gb * env_db_nodes * EBS_IO2_PER_GB * mult
    priced.append({
        "category": db_cat,
        "label":    f"Storage: SAN – {env_label}",
        "nodes": env_db_nodes, "vcpu": 0, "ram": 0,
        "instance_type": "EBS io2",
        "monthly_usd": round(san_cost, 2),
        "note": f"{env_db_nodes}× {env_data_gb}GB io2 SAN (scaled {scale*100:.0f}% of prod)",
    })

    # ── S3 ─────────────────────────────────────────────────────────────────
    s3_cost = env_s3_gb * S3_PER_GB
    priced.append({
        "category": "S3",
        "label":    f"S3 Storage + Replication – {env_label}",
        "nodes": 1, "vcpu": 0, "ram": 0,
        "instance_type": "S3",
        "monthly_usd": round(s3_cost, 2),
        "note": f"{env_s3_gb}GB S3 (scaled {scale*100:.0f}% of prod {s3_gb}GB)",
    })

    # ── ElastiCache ────────────────────────────────────────────────────────
    cache_nodes = 2 if scale >= 0.55 else 1
    cache_cost  = ELASTICACHE_HOURLY * cache_nodes * HOURS_PER_MONTH * mult
    priced.append({
        "category": "Caching",
        "label":    f"ElastiCache – {env_label}",
        "nodes": cache_nodes, "vcpu": 4, "ram": 16,
        "instance_type": "cache.r6g.large",
        "hourly_usd": round(ELASTICACHE_HOURLY * mult, 4),
        "monthly_usd": round(cache_cost, 2),
        "note": f"{cache_nodes}× cache.r6g.large",
    })

    # ── Load balancer ──────────────────────────────────────────────────────
    alb_nodes = 2 if scale >= 0.55 else 1
    alb_cost  = ALB_MONTHLY * alb_nodes
    priced.append({
        "category": "Infrastructure",
        "label":    f"Load Balancer – {env_label}",
        "nodes": alb_nodes, "vcpu": 0, "ram": 0,
        "instance_type": "ALB",
        "monthly_usd": round(alb_cost, 2),
        "note": f"{alb_nodes}× ALB",
    })

    # ── NAT Gateway ────────────────────────────────────────────────────────
    nat_cost = NAT_MONTHLY * 2   # always 2 for HA
    priced.append({
        "category": "Infrastructure",
        "label":    f"NAT Gateway – {env_label}",
        "nodes": 2, "vcpu": 0, "ram": 0,
        "instance_type": "NAT",
        "monthly_usd": round(nat_cost, 2),
        "note": "2× NAT gateway (one per AZ)",
    })

    # ── Bastion ────────────────────────────────────────────────────────────
    bastion_compute = bastion_hr * 1 * HOURS_PER_MONTH
    bastion_stor    = 300 * EBS_GP3_PER_GB * mult
    priced.append({
        "category": "Infrastructure",
        "label":    f"Bastion Host – {env_label}",
        "nodes": 1, "vcpu": 2, "ram": 4,
        "instance_type": bastion_itype,
        "hourly_usd": round(bastion_hr, 4),
        "monthly_usd": round(bastion_compute + bastion_stor, 2),
        "note": f"1× {bastion_itype}",
    })

    # ── ECR ───────────────────────────────────────────────────────────────
    ecr_cost = 512 * ECR_PER_GB * mult
    priced.append({
        "category": "Infrastructure",
        "label":    f"Image Registry (ECR) – {env_label}",
        "nodes": 1, "vcpu": 0, "ram": 0,
        "instance_type": "ECR",
        "monthly_usd": round(ecr_cost, 2),
        "note": "512GB ECR",
    })

    # ── Backup ────────────────────────────────────────────────────────────
    backup_gb   = max(1000, math.ceil((data_gb + s3_gb) * scale))
    backup_cost = backup_gb * S3_PER_GB
    priced.append({
        "category": "Backup",
        "label":    f"Back Up – DB & Infra Logs – {env_label}",
        "nodes": 1, "vcpu": 0, "ram": 0,
        "instance_type": "S3",
        "monthly_usd": round(backup_cost, 2),
        "note": f"{backup_gb}GB S3 backup (scaled {scale*100:.0f}% of prod)",
    })

    # ── CloudWatch ────────────────────────────────────────────────────────
    total_nodes = env_worker_nodes + infra_nodes + env_db_nodes + cache_nodes
    cw_cost     = CLOUDWATCH_BASE + total_nodes * CLOUDWATCH_PER_NODE
    priced.append({
        "category": "Operations",
        "label":    f"CloudWatch Monitoring – {env_label}",
        "nodes": 0, "vcpu": 0, "ram": 0,
        "instance_type": "CloudWatch",
        "monthly_usd": round(cw_cost, 2),
        "note": f"Base ${CLOUDWATCH_BASE} + {total_nodes} nodes × ${CLOUDWATCH_PER_NODE}",
    })

    return priced


def _summarise(priced: list) -> tuple:
    """Return (category_totals dict, monthly_total float)."""
    cat_totals = {}
    total = 0.0
    for r in priced:
        mo = r.get("monthly_usd", 0) or 0
        total += mo
        cat = r.get("category", "Other")
        cat_totals[cat] = round(cat_totals.get(cat, 0) + mo, 2)
    return cat_totals, round(total, 2)


# ── DB label helper ───────────────────────────────────────────────────────

def _db_category_label(db_type: str) -> str:
    return {
        "PostgreSQL": "PostgreSQL DB",
        "SQL Server": "SQL Server DB",
        "Oracle":     "Oracle DB",
    }.get(db_type, f"{db_type} DB")


# ── Public API ────────────────────────────────────────────────────────────

def price_additional_environments(
    db_type:        str,
    deployment:     str,
    metrics:        dict,
    preprod_region: str = "us-east-1",
    dr_region:      str = "us-east-1",
) -> dict:
    """
    Price Pre-Prod/SIT/UAT and DR environments scaled dynamically
    from the actual production metrics.

    Returns:
    {
        "preprod_sit_uat": {
            "priced_roles": [...],
            "category_totals": {...},
            "monthly_usd": float,
            "annual_usd": float,
        },
        "dr": {
            "priced_roles": [...],
            "category_totals": {...},
            "monthly_usd": float,
            "annual_usd": float,
            "five_year_forecast": {...},
        },
        "combined_monthly": float,
        "db_type": str,
        "db_note": str,
        "is_saas": bool,
    }
    """
    pricing_client = _init_pricing()
    preprod_ec2_client = _init_ec2(preprod_region)
    dr_ec2_client = _init_ec2(dr_region)
    is_saas   = db_type == "PostgreSQL"

    # ── Pre-Prod / SIT / UAT ──────────────────────────────────────────────
    preprod_roles = _build_env_roles(
        metrics=metrics,
        scale=PREPROD_SCALE,
        env_label="Pre-Prod",
        region=preprod_region,
        pricing_client=pricing_client,
        ec2_client=preprod_ec2_client,
        db_type=db_type,
        single_az=True,
    )
    preprod_cats, preprod_total = _summarise(preprod_roles)

    preprod_result = {
        "priced_roles":    preprod_roles,
        "category_totals": preprod_cats,
        "monthly_usd":     preprod_total,
        "annual_usd":      round(preprod_total * 12, 2),
    }

    # ── DR ────────────────────────────────────────────────────────────────
    dr_roles = _build_env_roles(
        metrics=metrics,
        scale=DR_SCALE,
        env_label="DR",
        region=dr_region,
        pricing_client=pricing_client,
        ec2_client=dr_ec2_client,
        db_type=db_type,
        single_az=False,   # DR uses Multi-AZ (2 DB nodes)
    )
    dr_cats, dr_total = _summarise(dr_roles)

    # DR 5-year inflation forecast
    dr_forecast = {}
    cumulative  = 0.0
    for yr in range(1, 6):
        annual = round(dr_total * 12 * ((1 + INFLATION_RATE) ** yr), 2)
        dr_forecast[f"year_{yr}"] = {
            "annual_usd":  annual,
            "multiplier":  round((1 + INFLATION_RATE) ** yr, 4),
        }
        cumulative += annual
    dr_forecast["five_year_total"] = round(cumulative, 2)

    dr_result = {
        "priced_roles":      dr_roles,
        "category_totals":   dr_cats,
        "monthly_usd":       dr_total,
        "annual_usd":        round(dr_total * 12, 2),
        "five_year_forecast": dr_forecast,
    }

    db_notes = {
        "PostgreSQL": (
            "Self-Hosted on EC2 — Patroni HA, no licensing cost" if deployment == "saas"
            else "Self-Hosted on EC2 — Patroni HA, no licensing cost (On-Premise)"
        ),
        "SQL Server": (
            "AWS RDS Managed — commercial license, automated HA/backups" if deployment == "saas"
            else "EC2 Self-Hosted (AMD EPYC) — SQL Server BYOL + AWS Owned Enterprise License"
        ),
        "Oracle": (
            "AWS RDS Managed — Oracle BYOL or License Included, automated HA" if deployment == "saas"
            else "EC2 Self-Hosted (AMD EPYC) — Oracle BYOL (On-Premise)"
        ),
    }

    return {
        "preprod_sit_uat":  preprod_result,
        "dr":               dr_result,
        "combined_monthly": round(preprod_total + dr_total, 2),
        "db_type":          db_type,
        "deployment":       deployment,
        "db_note":          db_notes.get(db_type, ""),
        "is_saas":          is_saas,
    }
