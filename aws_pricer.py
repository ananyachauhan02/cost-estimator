"""
aws_pricer.py
─────────────────────────────────────────────────────────────
Responsible for:
  - Mapping node distribution roles → AWS instance types
  - Fetching On-Demand prices from AWS Pricing API
  - Falling back to hardcoded estimates if API unavailable
  - Computing monthly / annual / 3-year cost breakdowns
  - Returning structured pricing dict consumed by ui_pricing.py
─────────────────────────────────────────────────────────────
"""

from __future__ import annotations

import json
import boto3


HOURS_PER_MONTH = 730
REGION          = "us-east-1"   # default; overridden by calculate_pricing(region=...)

# Supported AWS regions + cost multipliers relative to us-east-1
AWS_REGIONS = {
    # Americas
    "us-east-1":      {"label": "US East (N. Virginia)",       "multiplier": 1.000},
    "us-east-2":      {"label": "US East (Ohio)",              "multiplier": 0.990},
    "us-west-1":      {"label": "US West (N. California)",     "multiplier": 1.090},
    "us-west-2":      {"label": "US West (Oregon)",            "multiplier": 1.000},
    "ca-central-1":   {"label": "Canada (Central)",            "multiplier": 1.030},
    "ca-west-1":      {"label": "Canada West (Calgary)",       "multiplier": 1.030},
    "sa-east-1":      {"label": "South America (São Paulo)",   "multiplier": 1.200},
    
    # Europe
    "eu-central-1":   {"label": "Europe (Frankfurt)",          "multiplier": 1.090},
    "eu-central-2":   {"label": "Europe (Zurich)",             "multiplier": 1.150},
    "eu-west-1":      {"label": "Europe (Ireland)",            "multiplier": 1.050},
    "eu-west-2":      {"label": "Europe (London)",             "multiplier": 1.090},
    "eu-west-3":      {"label": "Europe (Paris)",              "multiplier": 1.090},
    "eu-north-1":     {"label": "Europe (Stockholm)",          "multiplier": 1.060},
    "eu-south-1":     {"label": "Europe (Milan)",              "multiplier": 1.090},
    "eu-south-2":     {"label": "Europe (Spain)",              "multiplier": 1.090},

    # Asia Pacific
    "ap-south-1":     {"label": "Asia Pacific (Mumbai)",       "multiplier": 1.080},
    "ap-south-2":     {"label": "Asia Pacific (Hyderabad)",    "multiplier": 1.080},
    "ap-northeast-1": {"label": "Asia Pacific (Tokyo)",        "multiplier": 1.120},
    "ap-northeast-2": {"label": "Asia Pacific (Seoul)",        "multiplier": 1.120},
    "ap-northeast-3": {"label": "Asia Pacific (Osaka)",        "multiplier": 1.120},
    "ap-southeast-1": {"label": "Asia Pacific (Singapore)",    "multiplier": 1.100},
    "ap-southeast-2": {"label": "Asia Pacific (Sydney)",       "multiplier": 1.130},
    "ap-southeast-3": {"label": "Asia Pacific (Jakarta)",      "multiplier": 1.100},
    "ap-southeast-4": {"label": "Asia Pacific (Melbourne)",    "multiplier": 1.130},
    "ap-east-1":      {"label": "Asia Pacific (Hong Kong)",    "multiplier": 1.180},
    
    # Middle East & Africa
    "me-south-1":     {"label": "Middle East (Bahrain)",       "multiplier": 1.150},
    "me-central-1":   {"label": "Middle East (UAE)",           "multiplier": 1.150},
    "af-south-1":     {"label": "Africa (Cape Town)",          "multiplier": 1.200},
    "il-central-1":   {"label": "Israel (Tel Aviv)",           "multiplier": 1.160},
}

# ── Fallback hourly prices (USD) — March 2026 estimates ───────────────────
EC2_FALLBACK = {
    "t3.medium":    0.0416,
    "m5.large":     0.096,
    "m5.xlarge":    0.192,
    "m5.2xlarge":   0.384,
    "m5.4xlarge":   0.768,
    "m5.8xlarge":   1.536,
    "m5.12xlarge":  2.304,
    "r5.large":     0.126,
    "r5.xlarge":    0.252,
    "r5.2xlarge":   0.504,
    "r5.4xlarge":   1.008,
    "r5.8xlarge":   2.016,
    "r5.12xlarge":  3.024,
    "r5.16xlarge":  4.032,
    "cache.r6g.large":   0.166,
    "cache.r6g.xlarge":  0.332,
    "cache.r6g.2xlarge": 0.665,
}

S3_PER_GB          = 0.023
EBS_GP3_PER_GB     = 0.08
EBS_IO2_PER_GB     = 0.125   # 10K IOPS SAN equivalent
S3_HOURLY = {
    "s3.t3.medium":  0.065,
    "s3.c5.large":   0.154,
    "s3.c5.2xlarge": 0.308,
}
ALB_BASE_MONTHLY   = 16.43
NAT_PER_GB         = 0.045
NAT_BASE_MONTHLY   = 32.00   # ~2 NAT gateways base
CLOUDWATCH_PER_NODE = 3.50


# ── Instance type selection ───────────────────────────────────────────────

def _ec2_instance(vcpu: int, ram_gb: float, family_hint: str = "") -> str:
    """Pick best-fit EC2 instance type from vCPU + RAM."""
    hint = family_hint.lower()
    if "memory" in hint or (ram_gb / max(vcpu, 1)) > 8:
        family = "r5"
    else:
        family = "m5"

    sizes = [
        (2,  8,   "large"),
        (4,  16,  "xlarge"),
        (8,  32,  "2xlarge"),
        (16, 64,  "4xlarge"),
        (32, 128, "8xlarge"),
        (48, 192, "12xlarge"),
        (64, 256, "16xlarge"),
    ]
    for c, r, size in sizes:
        if vcpu <= c and ram_gb <= r:
            return f"{family}.{size}"
    return f"{family}.16xlarge"


def _s3_instance(s3_gb: float) -> str:
    if s3_gb <= 100:  return "s3.t3.medium"
    if s3_gb <= 500:  return "s3.c5.large"
    return "s3.c5.2xlarge"


def _cache_instance(ram_gb: float) -> str:
    if ram_gb <= 16:  return "cache.r6g.large"
    if ram_gb <= 32:  return "cache.r6g.xlarge"
    return "cache.r6g.2xlarge"


# ── AWS Pricing API helpers ───────────────────────────────────────────────

def _init_pricing(region: str = "us-east-1"):
    try:
        return boto3.client("pricing", region_name="us-east-1")  # Pricing API always in us-east-1
    except Exception as e:
        print(f"[aws_pricer] Could not init pricing client: {e}")
        return None


def _fetch_ec2_hourly(client, instance_type: str, region: str = "us-east-1") -> tuple:
    """Returns (hourly_usd, from_api)."""
    if not client:
        base = EC2_FALLBACK.get(instance_type, 0.384)
        mult = AWS_REGIONS.get(region, {}).get("multiplier", 1.0)
        return round(base * mult, 6), False
    try:
        resp = client.get_products(
            ServiceCode="AmazonEC2",
            Filters=[
                {"Type": "TERM_MATCH", "Field": "instanceType",    "Value": instance_type},
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
    except Exception as e:
        print(f"[aws_pricer] EC2 price fetch failed for {instance_type}: {e}")
    return EC2_FALLBACK.get(instance_type, 0.384), False


def _fetch_elasticache_hourly(client, instance_type: str, region: str = "us-east-1") -> tuple:
    if not client:
        base = EC2_FALLBACK.get(instance_type, 0.166)
        mult = AWS_REGIONS.get(region, {}).get("multiplier", 1.0)
        return round(base * mult, 6), False
    try:
        resp = client.get_products(
            ServiceCode="AmazonElastiCache",
            Filters=[
                {"Type": "TERM_MATCH", "Field": "instanceType", "Value": instance_type},
                {"Type": "TERM_MATCH", "Field": "regionCode",   "Value": region},
                {"Type": "TERM_MATCH", "Field": "cacheEngine",  "Value": "Redis"},
            ],
        )
        if resp["PriceList"]:
            item  = json.loads(resp["PriceList"][0])
            term  = next(iter(item["terms"]["OnDemand"].values()))
            dim   = next(iter(term["priceDimensions"].values()))
            price = float(dim["pricePerUnit"]["USD"])
            if price > 0:
                return price, True
    except Exception as e:
        print(f"[aws_pricer] ElastiCache price failed for {instance_type}: {e}")
    return EC2_FALLBACK.get(instance_type, 0.166), False


# ── Role → cost mapper ────────────────────────────────────────────────────

def _price_worker_role(role: dict, pricing_client, region: str = "us-east-1") -> dict:
    """Price a scalable K8s worker role."""
    vcpu    = role.get("vcpu_per_node", 0)
    ram     = role.get("ram_per_node", 0)
    nodes   = role.get("nodes", 0)
    storage = role.get("storage_per_node_gb", 0)
    family  = role.get("instance_family", "")

    if vcpu == 0 or nodes == 0:
        return {**role, "instance_type": "N/A", "hourly_usd": 0,
                "compute_monthly_usd": 0, "storage_monthly_usd": 0,
                "monthly_usd": 0, "from_api": False}

    instance_type = _ec2_instance(vcpu, ram, family)
    hourly, from_api = _fetch_ec2_hourly(pricing_client, instance_type, region)

    compute_monthly = hourly * nodes * HOURS_PER_MONTH
    # storage_per_node_gb is already in GB
    reg_mult = AWS_REGIONS.get(region, {}).get("multiplier", 1.0)
    storage_monthly = storage * nodes * EBS_GP3_PER_GB * reg_mult

    monthly = compute_monthly + storage_monthly
    return {
        **role,
        "instance_type":        instance_type,
        "hourly_usd":           round(hourly, 4),
        "compute_monthly_usd":  round(compute_monthly, 2),
        "storage_monthly_usd":  round(storage_monthly, 2),
        "monthly_usd":          round(monthly, 2),
        "from_api":             from_api,
        "note": f"{nodes}× {instance_type} @ ${hourly:.4f}/hr + {storage}GB EBS",
    }


def _price_db_role(role: dict, pricing_client, region: str = "us-east-1") -> dict:
    """Price a DB or storage role."""
    vcpu    = role.get("vcpu_per_node", 0)
    ram     = role.get("ram_per_node", 0)
    nodes   = role.get("nodes", 0)
    storage = role.get("storage_per_node_gb", 0)
    family  = role.get("instance_family", "")

    # Pure storage roles (SAN)
    reg_mult = AWS_REGIONS.get(region, {}).get("multiplier", 1.0)
    if "10K IOPS" in family or vcpu == 0:
        storage_monthly = storage * nodes * EBS_IO2_PER_GB * reg_mult
        return {
            **role,
            "instance_type":       "EBS io2",
            "hourly_usd":          0,
            "compute_monthly_usd": 0,
            "storage_monthly_usd": round(storage_monthly, 2),
            "monthly_usd":         round(storage_monthly, 2),
            "from_api":            False,
            "note": f"{nodes}× {storage}GB io2 SAN",
        }

    # S3
    if "Cloud Storage Service" in family or role.get("role_key") == "s3":
        s3_inst    = _s3_instance(storage)
        s3_hourly  = S3_HOURLY.get(s3_inst, 0.154)
        s3_monthly = s3_hourly * HOURS_PER_MONTH
        s3_monthly  = storage * S3_PER_GB
        monthly     = s3_monthly + s3_monthly
        return {
            **role,
            "instance_type":       s3_inst,
            "hourly_usd":          s3_hourly,
            "compute_monthly_usd": round(s3_monthly, 2),
            "storage_monthly_usd": round(s3_monthly, 2),
            "monthly_usd":         round(monthly, 2),
            "from_api":            False,
            "note": f"{s3_inst} + {storage}GB S3",
        }

    # Memory-intensive compute (DB nodes)
    if nodes == 0:
        return {**role, "instance_type": "N/A", "hourly_usd": 0,
                "compute_monthly_usd": 0, "storage_monthly_usd": 0,
                "monthly_usd": 0, "from_api": False}

    instance_type   = _ec2_instance(vcpu, ram, family)
    hourly, from_api = _fetch_ec2_hourly(pricing_client, instance_type)
    compute_monthly = hourly * nodes * HOURS_PER_MONTH
    storage_monthly = storage * nodes * EBS_GP3_PER_GB

    return {
        **role,
        "instance_type":        instance_type,
        "hourly_usd":           round(hourly, 4),
        "compute_monthly_usd":  round(compute_monthly, 2),
        "storage_monthly_usd":  round(storage_monthly, 2),
        "monthly_usd":          round(compute_monthly + storage_monthly, 2),
        "from_api":             from_api,
        "note": f"{nodes}× {instance_type} @ ${hourly:.4f}/hr",
    }


def _price_fixed_role(role: dict, pricing_client, data_gb: float = 0, region: str = "us-east-1") -> dict:
    """Price a fixed infra role."""
    key     = role.get("role_key", "")
    nodes   = role.get("nodes", 0)
    vcpu    = role.get("vcpu_per_node", 0)
    ram     = role.get("ram_per_node", 0)
    storage = role.get("storage_per_node_gb", 0)

    # ALB
    if key == "alb":
        monthly = ALB_BASE_MONTHLY * nodes
        return {**role, "instance_type": "ALB", "hourly_usd": 0,
                "compute_monthly_usd": round(monthly, 2),
                "storage_monthly_usd": 0, "monthly_usd": round(monthly, 2),
                "from_api": False, "note": f"{nodes}× ALB (base charge)"}

    # NAT Gateway
    if key == "nat":
        egress  = data_gb * 0.10 * NAT_PER_GB
        monthly = NAT_BASE_MONTHLY + egress
        return {**role, "instance_type": "NAT", "hourly_usd": 0,
                "compute_monthly_usd": round(NAT_BASE_MONTHLY, 2),
                "storage_monthly_usd": round(egress, 2),
                "monthly_usd": round(monthly, 2),
                "from_api": False, "note": f"Base + 10% egress of {data_gb:.0f}GB"}

    # ElastiCache
    if key == "elasticache":
        inst    = _cache_instance(ram)
        hourly, from_api = _fetch_elasticache_hourly(pricing_client, inst)
        monthly = hourly * nodes * HOURS_PER_MONTH
        return {**role, "instance_type": inst, "hourly_usd": round(hourly, 4),
                "compute_monthly_usd": round(monthly, 2),
                "storage_monthly_usd": 0, "monthly_usd": round(monthly, 2),
                "from_api": from_api, "note": f"{nodes}× {inst}"}

    # Backup storage (S3)
    if key == "backup":
        monthly = storage * S3_PER_GB
        return {**role, "instance_type": "S3", "hourly_usd": 0,
                "compute_monthly_usd": 0,
                "storage_monthly_usd": round(monthly, 2),
                "monthly_usd": round(monthly, 2),
                "from_api": False, "note": f"{storage}GB S3 standard"}

    # ECR
    if key == "ecr":
        reg_mult2 = AWS_REGIONS.get(region, {}).get("multiplier", 1.0)
        monthly = storage * 0.10 * reg_mult2   # ECR $0.10/GB/month
        return {**role, "instance_type": "ECR", "hourly_usd": 0,
                "compute_monthly_usd": 0, "storage_monthly_usd": round(monthly, 2),
                "monthly_usd": round(monthly, 2),
                "from_api": False, "note": f"{storage}GB ECR"}

    # K8s managed (EKS control plane)
    if key == "k8s_managed":
        monthly = 73.00   # EKS cluster ~$0.10/hr = $73/month
        return {**role, "instance_type": "EKS", "hourly_usd": 0.10,
                "compute_monthly_usd": monthly, "storage_monthly_usd": 0,
                "monthly_usd": monthly, "from_api": False,
                "note": "EKS managed control plane"}

    # Bastion host
    if key == "bastion" and vcpu > 0:
        instance_type    = _ec2_instance(vcpu, ram, "general")
        hourly, from_api = _fetch_ec2_hourly(pricing_client, instance_type, region)
        compute_monthly = hourly * nodes * HOURS_PER_MONTH
        storage_monthly = storage * EBS_GP3_PER_GB
        monthly         = compute_monthly + storage_monthly
        return {**role, "instance_type": instance_type, "hourly_usd": round(hourly, 4),
                "compute_monthly_usd": round(compute_monthly, 2),
                "storage_monthly_usd": round(storage_monthly, 2),
                "monthly_usd": round(monthly, 2), "from_api": from_api,
                "note": f"{nodes}× {instance_type}"}

    # Everything else (WAF, Route53, CloudTrail etc.) — zero compute cost
    return {**role, "instance_type": "Managed Service", "hourly_usd": 0,
            "compute_monthly_usd": 0, "storage_monthly_usd": 0,
            "monthly_usd": 0, "from_api": False,
            "note": "No direct instance cost"}


# ── CloudWatch add-on ─────────────────────────────────────────────────────

def _cloudwatch_cost(total_nodes: int) -> dict:
    monthly = 10.0 + total_nodes * CLOUDWATCH_PER_NODE
    return {
        "role_key": "cloudwatch", "label": "CloudWatch Monitoring",
        "category": "Operations", "nodes": 0,
        "instance_type": "CloudWatch", "hourly_usd": 0,
        "compute_monthly_usd": round(monthly, 2),
        "storage_monthly_usd": 0, "monthly_usd": round(monthly, 2),
        "from_api": False,
        "note": f"Base $10 + {total_nodes} nodes × ${CLOUDWATCH_PER_NODE}/node",
        "reasoning": "Logs + metrics",
    }


# ── Public API ────────────────────────────────────────────────────────────

def calculate_pricing(distribution: dict, metrics: dict, region: str = "us-east-1") -> dict:
    """
    Main entry point.

    Args:
        distribution: output of node_distributor.distribute_nodes()
        metrics:      output of excel_handler.extract_metrics()

    Returns rich pricing dict with:
        priced_roles, category_totals,
        total_monthly_usd, total_annual_usd, total_3year_usd,
        assumptions, warnings
    """
    pricing_client = _init_pricing(region)
    data_gb        = metrics.get("data_size_gb", 0)
    warnings       = []
    priced_roles   = []

    # 1. Worker nodes
    for role in distribution.get("worker_nodes", []):
        priced_roles.append(_price_worker_role(role, pricing_client, region))

    # 2. DB + storage nodes
    for role in distribution.get("db_nodes", []):
        priced_roles.append(_price_db_role(role, pricing_client, region))

    # 3. Fixed infra roles
    for role in distribution.get("fixed_roles", []):
        priced_roles.append(_price_fixed_role(role, pricing_client, data_gb, region))

    # 4. CloudWatch
    total_worker = distribution["summary"]["total_worker_nodes"]
    total_db     = distribution["summary"]["total_db_nodes"]
    priced_roles.append(_cloudwatch_cost(total_worker + total_db))

    # 5. Aggregate
    total_monthly = sum(r.get("monthly_usd", 0) for r in priced_roles)

    # Category rollup
    category_totals: dict = {}
    for r in priced_roles:
        cat = r.get("category", "Other")
        category_totals[cat] = round(
            category_totals.get(cat, 0) + r.get("monthly_usd", 0), 2
        )

    # Warnings
    if not pricing_client:
        warnings.append("AWS Pricing API unavailable — all prices are estimates.")
    api_count = sum(1 for r in priced_roles if r.get("from_api"))
    if api_count == 0:
        warnings.append("No prices fetched from AWS API — using fallback rates.")

    # ── Inflation forecast (5 years, 4% default) ───────────────────────
    INFLATION_RATE = 0.04
    inflation_yearly = []
    cumulative = 0.0
    for yr in range(1, 6):
        mult   = (1 + INFLATION_RATE) ** (yr - 1)   # Year 1 = base cost
        mo     = round(total_monthly * mult, 2)
        annual = round(mo * 12, 2)
        cumulative += annual
        inflation_yearly.append({
            "year":            yr,
            "multiplier":      round(mult, 4),
            "monthly_usd":     mo,
            "annual_usd":      annual,
            "cumulative_usd":  round(cumulative, 2),
        })
    inflation_forecast = {
        "yearly":                          inflation_yearly,
        "five_year_total":                 round(cumulative, 2),
        "five_year_savings_vs_nodiscount": round(cumulative - (total_monthly * 12 * 5), 2),
    }
    # Legacy keys so any old code using year_N format still works
    for _y in inflation_yearly:
        inflation_forecast[f"year_{_y['year']}"] = {
            "annual_usd": _y["annual_usd"], "multiplier": _y["multiplier"],
        }

    # ── DB selection logic ────────────────────────────────────────────────
    postgres_ram  = metrics.get("postgres_ram_gb", 224)
    sql_ram       = metrics.get("sql_server_ram_gb", 0)
    oracle_ram    = metrics.get("oracle_ram_gb", 0)

    # PostgreSQL = self-hosted on EC2 (no licensing cost)
    pg_instance   = _ec2_instance(32, min(postgres_ram, 128), "memory")
    pg_hourly, _  = _fetch_ec2_hourly(pricing_client, pg_instance)
    pg_monthly    = round(pg_hourly * 2 * HOURS_PER_MONTH, 2)   # 2 primary nodes
    
    # helper for sizing RDS based on requested RAM
    def _rds_instance(ram: float) -> str:
        sizes = [(16, "large"), (32, "xlarge"), (64, "2xlarge"), (128, "4xlarge"), (256, "8xlarge"), (512, "16xlarge")]
        for limit, sz in sizes:
            if ram <= limit: return f"db.r5.{sz}"
        return "db.r5.24xlarge"

    # SQL Server = AWS managed (commercial license included)
    # Estimate: ~$26/mo per GB for Multi-AZ Standard Edition (db.r5 family)
    sql_instance  = _rds_instance(sql_ram) if sql_ram > 0 else "N/A"
    sql_monthly   = round(sql_ram * 26.0, 2) if sql_ram > 0 else 0

    # Oracle = AWS managed (commercial license included)
    # Estimate: ~$22/mo per GB for Multi-AZ SE2 Edition (db.r5 family)
    oracle_instance = _rds_instance(oracle_ram) if oracle_ram > 0 else "N/A"
    oracle_monthly  = round(oracle_ram * 22.0, 2) if oracle_ram > 0 else 0

    # Elasticache
    cache_role = next((r for r in priced_roles if r.get("role_key") == "elasticache"), {})

    db_selection = {
        "postgres": {
            "hosting":   "Self-Hosted on EC2",
            "reason":    "Open-source — no licensing cost. HA via Patroni+etcd on EC2.",
            "instance":  pg_instance,
            "monthly":   pg_monthly,
            "note":      f"2× {pg_instance} @ ${pg_hourly:.4f}/hr",
        },
        "sql_server": {
            "hosting":   "AWS Managed ",
            "reason":    "Commercial license — reduces compliance risk and ops overhead.",
            "instance":  f"{sql_instance} (estimated)",
            "monthly":   sql_monthly,
            "note":      "SQL Server Multi-AZ (License Included)" if sql_ram > 0 else "Not required",
        },
        "oracle": {
            "hosting":   "AWS Managed",
            "reason":    "Oracle licensing complexity — Oracle is the safest choice on AWS.",
            "instance":  f"{oracle_instance} (estimated)",
            "monthly":   oracle_monthly,
            "note":      " Oracle SE2 Multi-AZ (License Included)" if oracle_ram > 0 else "Not required",
        },
        "elasticache": {
            "hosting":   "AWS Managed",
            "reason":    "Session store + API cache — always managed on AWS.",
            "instance":  cache_role.get("instance_type", "cache.r6g.large"),
            "monthly":   cache_role.get("monthly_usd", 0),
            "note":      cache_role.get("note", ""),
        },
        "postgres_monthly":    pg_monthly,
        "sqlserver_monthly":   sql_monthly,
        "oracle_monthly":      oracle_monthly,
        "elasticache_monthly": cache_role.get("monthly_usd", 0),
        "summary": (
            "PostgreSQL → Self-Hosted EC2 (open-source). "
            + ("SQL Server → AWS Managed. " if sql_ram > 0 else "")
            + ("Oracle → AWS Managed. " if oracle_ram > 0 else "")
        ),
    }

    return {
        "priced_roles":         priced_roles,
        "category_totals":      category_totals,
        "region":               region,
        "region_label":         AWS_REGIONS.get(region, {}).get("label", region),
        "total_monthly_usd":    round(total_monthly, 2),
        "total_annual_usd":     round(total_monthly * 12, 2),
        "total_3year_usd":      round(total_monthly * 36, 2),
        "inflation_rate":       INFLATION_RATE,
        "inflation_forecast":   inflation_forecast,
        "db_selection":         db_selection,
        "distribution_summary": distribution["summary"],
        "assumptions": {
            "region":            region,
            "region_label":      AWS_REGIONS.get(region, {}).get("label", region),
            "hours_per_month":   HOURS_PER_MONTH,
            "deployment":        "Multi-AZ (HA) for Prod/DR; Single-AZ for Pre-Prod",
            "os":                "Linux/RHEL",
            "ebs_type":          "gp3 (compute), io2 (SAN/DB)",
            "pricing_date":      "2026-03",
            "inflation_rate":    f"{INFLATION_RATE*100:.0f}% per year",
            "db_hosting_note":   "PostgreSQL=Self-Hosted EC2, SQL Server/Oracle=AWS Managed",
        },
        "warnings": warnings,
    }