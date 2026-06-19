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
import os
import boto3

# ── Single source of truth: import catalog for pricing, specs & regions ───
from aws_machine_catalog import (
    AWS_REGIONS,
    EC2_CATALOG,
    EBS_GP3_PER_GB_MONTH   as EBS_GP3_PER_GB,
    S3_PER_GB_MONTH        as S3_PER_GB,
    ALB_BASE_MONTHLY,
    NAT_BASE_MONTHLY,
    NAT_PER_GB,
    CLOUDWATCH_PER_NODE,
    ELASTICACHE_HOURLY,
    S3_SERVER_HOURLY       as S3_HOURLY,
    best_ec2_instance      as _catalog_best,
    ec2_hourly             as _catalog_hourly,
    region_families        as _catalog_region_families,
)

HOURS_PER_MONTH = 730
REGION          = "us-east-1"   # default; overridden by calculate_pricing(region=...)

# EC2 fallback dict — derived from catalog for backward compat
EC2_FALLBACK: dict[str, float] = {
    k: v["hourly_base"] for k, v in EC2_CATALOG.items()
}
# Add legacy cache/S3 keys expected by old code
EC2_FALLBACK.update({
    k: v for k, v in {**ELASTICACHE_HOURLY, **S3_HOURLY}.items()
})

_INSTANCE_OFFERING_CACHE: dict[tuple[str, str], bool | None] = {}


# ── Instance type selection ───────────────────────────────────────────────

INSTANCE_SIZE_TABLES = {
    "c6i": [
        (2, 4, "large"), (4, 8, "xlarge"), (8, 16, "2xlarge"),
        (16, 32, "4xlarge"), (32, 64, "8xlarge"), (48, 96, "12xlarge"),
        (64, 128, "16xlarge"),
    ],
    "c6a": [
        (2, 4, "large"), (4, 8, "xlarge"), (8, 16, "2xlarge"),
        (16, 32, "4xlarge"), (32, 64, "8xlarge"), (48, 96, "12xlarge"),
        (64, 128, "16xlarge"),
    ],
    "m5": [
        (2, 8, "large"), (4, 16, "xlarge"), (8, 32, "2xlarge"),
        (16, 64, "4xlarge"), (32, 128, "8xlarge"), (48, 192, "12xlarge"),
        (64, 256, "16xlarge"),
    ],
    "r5": [
        (2, 16, "large"), (4, 32, "xlarge"), (8, 64, "2xlarge"),
        (16, 128, "4xlarge"), (32, 256, "8xlarge"), (48, 384, "12xlarge"),
        (64, 512, "16xlarge"),
    ],
    "r6a": [
        (2, 16, "large"), (4, 32, "xlarge"), (8, 64, "2xlarge"),
        (16, 128, "4xlarge"), (32, 256, "8xlarge"), (48, 384, "12xlarge"),
        (64, 512, "16xlarge"),
    ],
}

# ── P-series GPU instance catalog (on-demand, us-east-1 base) ─────────────────
# AWS GPU instances for AI/ML workloads
# Source: AWS EC2 pricing (https://aws.amazon.com/ec2/pricing/)
P_SERIES_CATALOG: dict[str, dict] = {
    # ── p3 family (NVIDIA Tesla V100) ──────────────────────────────────────
    "p3.2xlarge":    {"vcpu":  8, "ram_gb":  61,  "gpu": 1, "gpu_model": "V100 16GB",  "hourly_base": 3.0600},
    "p3.8xlarge":    {"vcpu": 32, "ram_gb":  244, "gpu": 4, "gpu_model": "V100 16GB",  "hourly_base": 12.240},
    "p3.16xlarge":   {"vcpu": 64, "ram_gb":  488, "gpu": 8, "gpu_model": "V100 16GB",  "hourly_base": 24.480},
    "p3dn.24xlarge": {"vcpu": 96, "ram_gb":  768, "gpu": 8, "gpu_model": "V100 32GB",  "hourly_base": 31.218},
    # ── p4d family (NVIDIA A100) ──────────────────────────────────────────
    "p4d.24xlarge":  {"vcpu": 96, "ram_gb": 1152, "gpu": 8, "gpu_model": "A100 40GB",  "hourly_base": 32.7726},
    # ── p4de family (NVIDIA A100 80GB) ───────────────────────────────────
    "p4de.24xlarge": {"vcpu": 96, "ram_gb": 1152, "gpu": 8, "gpu_model": "A100 80GB",  "hourly_base": 40.9677},
    # ── p5 family (NVIDIA H100) ───────────────────────────────────────────
    "p5.48xlarge":   {"vcpu": 192, "ram_gb": 2048, "gpu": 8, "gpu_model": "H100 80GB", "hourly_base": 98.320},
}

# Select the best P-series instance for the given vCPU / RAM requirements
def _gpu_instance(vcpu: int, ram_gb: float) -> str:
    """Pick the most cost-effective P-series instance that satisfies the requested vCPU+RAM."""
    # Order by ascending cost (prefer cheaper GPU instances)
    ordered = [
        "p3.2xlarge", "p3.8xlarge", "p3.16xlarge", "p3dn.24xlarge",
        "p4d.24xlarge", "p4de.24xlarge", "p5.48xlarge",
    ]
    for name in ordered:
        spec = P_SERIES_CATALOG[name]
        # Allow up to 2× CPU overcommit (GPU nodes are often memory/GPU-bound)
        if spec["vcpu"] >= vcpu // 2 and spec["ram_gb"] >= ram_gb:
            return name
    return "p4d.24xlarge"  # default: A100 node


def _preferred_families(vcpu: int, ram_gb: float, family_hint: str = "") -> list[str]:
    """Return ordered family preferences for the requested shape."""
    hint = (family_hint or "").lower()

    # GPU / AI compute — P-series route handled separately via _gpu_instance()
    if "gpu" in hint or "p-series" in hint or "p series" in hint:
        return ["p-series"]   # sentinel: caller should use _gpu_instance()

    ram_to_vcpu = ram_gb / max(vcpu, 1)
    is_memory = "memory" in hint or ram_to_vcpu > 8
    is_compute = "compute" in hint or ram_to_vcpu <= 2

    # User explicitly wants AMD over Intel when available, and strictly memory-optimized defaults
    if "amd" in hint or "byol" in hint:
        return ["r6a", "r5"] if is_memory else ["c6a", "c6i", "m6a", "m5"]
    if "intel" in hint:
        return ["r5", "r6a"] if is_memory else ["c6i", "c6a", "m5", "m6a"]
        
    # Default behavior: select memory optimized sessions first, prefer AMD
    if is_memory or not is_compute: 
        return ["r6a", "r5"]
    if is_compute:
        return ["c6a", "c6i", "m6a", "m5"]
        
    return ["r6a", "r5"] # Fallback memory optimized AMD


def _instance_candidates(vcpu: int, ram_gb: float, family_hint: str = "") -> list[str]:
    """Return ordered instance-type candidates across Intel/AMD families."""
    candidates = []
    for family in _preferred_families(vcpu, ram_gb, family_hint):
        for c, r, size in INSTANCE_SIZE_TABLES[family]:
            # Compromise on CPU up to 50% to minimize RAM deviation (cost)
            # Memory must always be >= requested
            if (vcpu <= c * 2) and (ram_gb <= r):
                candidates.append(f"{family}.{size}")
                break
        else:
            candidates.append(f"{family}.16xlarge")
    return candidates

def _ec2_instance(vcpu: int, ram_gb: float, family_hint: str = "") -> str:
    """Pick best-fit preferred EC2 instance type from vCPU + RAM."""
    return _instance_candidates(vcpu, ram_gb, family_hint)[0]


def _s3_instance(s3_gb: float) -> str:
    if s3_gb <= 100:  return "s3.t3.medium"
    if s3_gb <= 500:  return "s3.c5.large"
    return "s3.c5.2xlarge"


def _cache_instance(ram_gb: float) -> str:
    if ram_gb <= 16:  return "cache.r6g.large"
    if ram_gb <= 32:  return "cache.r6g.xlarge"
    return "cache.r6g.2xlarge"


def _ec2_sql_server_byol(vcpu: int, ram_gb: float) -> str:
    """Pick AMD EPYC instance for SQL Server BYOL (more cost-effective than Intel).
    SQL Server licensing is expensive, so choosing AMD EPYC reduces overall TCO.
    """
    return _ec2_instance(vcpu, ram_gb, family_hint="amd")


# ── AWS Pricing API helpers ───────────────────────────────────────────────

def _aws_credentials() -> dict:
    """Return explicit credential kwargs for boto3 if env vars are set.
    Falls back to boto3's default chain (IAM role, ~/.aws/credentials, etc.)
    when the vars are absent.
    """
    key    = os.getenv("AWS_ACCESS_KEY_ID")
    secret = os.getenv("AWS_SECRET_ACCESS_KEY")
    token  = os.getenv("AWS_SESSION_TOKEN")   # optional, for temporary credentials
    if key and secret:
        creds = {"aws_access_key_id": key, "aws_secret_access_key": secret}
        if token:
            creds["aws_session_token"] = token
        return creds
    return {}   # let boto3 use its default chain (IAM role, ~/.aws, env, etc.)


def _init_pricing(region: str = "us-east-1"):
    try:
        return boto3.client("pricing", region_name="us-east-1", **_aws_credentials())  # Pricing API always in us-east-1
    except Exception as e:
        print(f"[aws_pricer] Could not init pricing client: {e}")
        return None


def _init_ec2(region: str = "us-east-1"):
    try:
        return boto3.client("ec2", region_name=region, **_aws_credentials())
    except Exception as e:
        print(f"[aws_pricer] Could not init EC2 client for {region}: {e}")
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


def _fetch_ec2_hourly_api(client, instance_type: str, region: str = "us-east-1") -> tuple[float | None, bool]:
    """Return API price only; None means not returned for that region/type."""
    if not client:
        return None, False
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
        print(f"[aws_pricer] EC2 region availability check failed for {instance_type}: {e}")
    return None, False


def _instance_type_offered(ec2_client, instance_type: str, region: str = "us-east-1") -> bool | None:
    """Return True/False when EC2 confirms regional offering; None if unknown."""
    cache_key = (region, instance_type)
    if cache_key in _INSTANCE_OFFERING_CACHE:
        return _INSTANCE_OFFERING_CACHE[cache_key]

    if not ec2_client:
        _INSTANCE_OFFERING_CACHE[cache_key] = None
        return None

    try:
        resp = ec2_client.describe_instance_type_offerings(
            LocationType="region",
            Filters=[
                {"Name": "instance-type", "Values": [instance_type]},
                {"Name": "location", "Values": [region]},
            ],
            MaxResults=5,
        )
        offered = bool(resp.get("InstanceTypeOfferings"))
        _INSTANCE_OFFERING_CACHE[cache_key] = offered
        return offered
    except Exception as e:
        print(f"[aws_pricer] EC2 offering check failed for {instance_type} in {region}: {e}")
        _INSTANCE_OFFERING_CACHE[cache_key] = None
        return None


def _resolve_ec2_instance(vcpu: int, ram_gb: float, family_hint: str, pricing_client, ec2_client=None, region: str = "us-east-1") -> tuple[str, float, bool]:
    """Pick preferred instance, skipping types not offered in the selected region."""
    mult = AWS_REGIONS.get(region, {}).get("multiplier", 1.0)
    hint = (family_hint or "").lower()

    # ── GPU / P-series route ──────────────────────────────────────────────────
    if "gpu" in hint or "p-series" in hint or "p series" in hint:
        instance_type = _gpu_instance(vcpu, ram_gb)
        spec = P_SERIES_CATALOG.get(instance_type, {})
        hourly_base = spec.get("hourly_base", 3.06)
        # Try live API price first
        if pricing_client:
            api_hourly, from_api = _fetch_ec2_hourly_api(pricing_client, instance_type, region)
            if api_hourly:
                return instance_type, round(api_hourly, 6), True
        return instance_type, round(hourly_base * mult, 6), False

    candidates = _instance_candidates(vcpu, ram_gb, family_hint)
    checked_candidates: list[str] = []

    for instance_type in candidates:
        offered = _instance_type_offered(ec2_client, instance_type, region)
        if offered is False:
            continue
        checked_candidates.append(instance_type)
        if pricing_client:
            hourly, from_api = _fetch_ec2_hourly_api(pricing_client, instance_type, region)
            if hourly is not None:
                return instance_type, hourly, from_api

    fallback_candidates = checked_candidates or candidates
    for instance_type in fallback_candidates:
        if instance_type in EC2_FALLBACK:
            return instance_type, round(EC2_FALLBACK[instance_type] * mult, 6), False

    preferred = fallback_candidates[0]
    return preferred, round(EC2_FALLBACK.get(preferred, 0.384) * mult, 6), False


def _resolve_override(instance_type: str, pricing_client, ec2_client=None, region: str = "us-east-1") -> tuple[str, float, bool]:
    """Look up the price for a user-specified override instance type."""
    mult = AWS_REGIONS.get(region, {}).get("multiplier", 1.0)
    if pricing_client:
        hourly, from_api = _fetch_ec2_hourly_api(pricing_client, instance_type, region)
        if hourly is not None:
            return instance_type, hourly, from_api
    if instance_type in EC2_FALLBACK:
        return instance_type, round(EC2_FALLBACK[instance_type] * mult, 6), False
    # Unknown instance — use a reasonable fallback price
    return instance_type, round(0.384 * mult, 6), False


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

def _price_worker_role(role: dict, pricing_client, ec2_client, region: str = "us-east-1", instance_overrides: dict | None = None) -> dict:
    """Price a scalable K8s worker role."""
    vcpu    = role.get("vcpu_per_node", 0)
    ram     = role.get("ram_per_node", 0)
    nodes   = role.get("nodes", 0)
    storage = role.get("storage_per_node_gb", 0)
    family  = role.get("instance_family", "")
    role_key = role.get("role_key", "")

    if vcpu == 0 or nodes == 0:
        return {**role, "instance_type": "N/A", "hourly_usd": 0,
                "compute_monthly_usd": 0, "storage_monthly_usd": 0,
                "monthly_usd": 0, "from_api": False}

    # Check for instance type override
    override = (instance_overrides or {}).get(role_key)
    if override:
        instance_type, hourly, from_api = _resolve_override(override, pricing_client, ec2_client, region)
    else:
        instance_type, hourly, from_api = _resolve_ec2_instance(vcpu, ram, family, pricing_client, ec2_client, region)

    compute_monthly = hourly * nodes * HOURS_PER_MONTH
    reg_mult = AWS_REGIONS.get(region, {}).get("multiplier", 1.0)
    storage_monthly = storage * nodes * EBS_GP3_PER_GB * reg_mult

    monthly = compute_monthly + storage_monthly
    note_suffix = " (override)" if override else ""
    return {
        **role,
        "instance_type":        instance_type,
        "hourly_usd":           round(hourly, 4),
        "compute_monthly_usd":  round(compute_monthly, 2),
        "storage_monthly_usd":  round(storage_monthly, 2),
        "monthly_usd":          round(monthly, 2),
        "from_api":             from_api,
        "note": f"{nodes}× {instance_type} @ ${hourly:.4f}/hr + {storage}GB EBS{note_suffix}",
    }


def _price_db_role(role: dict, pricing_client, ec2_client, region: str = "us-east-1", instance_overrides: dict | None = None) -> dict:
    """Price a DB or storage role."""
    vcpu    = role.get("vcpu_per_node", 0)
    ram     = role.get("ram_per_node", 0)
    nodes   = role.get("nodes", 0)
    storage = role.get("storage_per_node_gb", 0)
    family  = role.get("instance_family", "")
    role_key = role.get("role_key", "")

    # Pure storage roles (SAN)
    reg_mult = AWS_REGIONS.get(region, {}).get("multiplier", 1.0)
    if "10K IOPS" in family or vcpu == 0:
        storage_monthly = storage * nodes * EBS_GP3_PER_GB * reg_mult
        return {
            **role,
            "instance_type":       "EBS gp3",
            "hourly_usd":          0,
            "compute_monthly_usd": 0,
            "storage_monthly_usd": round(storage_monthly, 2),
            "monthly_usd":         round(storage_monthly, 2),
            "from_api":            False,
            "note": f"{nodes}× {storage}GB gp3 SAN",
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

    # Check for instance type override
    override = (instance_overrides or {}).get(role_key)
    if override:
        instance_type, hourly, from_api = _resolve_override(override, pricing_client, ec2_client, region)
    else:
        instance_type, hourly, from_api = _resolve_ec2_instance(vcpu, ram, family, pricing_client, ec2_client, region)
    compute_monthly = hourly * nodes * HOURS_PER_MONTH
    reg_mult = AWS_REGIONS.get(region, {}).get("multiplier", 1.0)
    storage_monthly = storage * nodes * EBS_GP3_PER_GB * reg_mult

    note_suffix = " (override)" if override else ""
    return {
        **role,
        "instance_type":        instance_type,
        "hourly_usd":           round(hourly, 4),
        "compute_monthly_usd":  round(compute_monthly, 2),
        "storage_monthly_usd":  round(storage_monthly, 2),
        "monthly_usd":          round(compute_monthly + storage_monthly, 2),
        "from_api":             from_api,
        "note": f"{nodes}× {instance_type} @ ${hourly:.4f}/hr{note_suffix}",
    }


def _price_fixed_role(role: dict, pricing_client, ec2_client, data_gb: float = 0, region: str = "us-east-1", instance_overrides: dict | None = None) -> dict:
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
        override = (instance_overrides or {}).get("elasticache")
        if override:
            inst = override
        else:
            inst    = _cache_instance(ram)
        hourly, from_api = _fetch_elasticache_hourly(pricing_client, inst)
        monthly = hourly * nodes * HOURS_PER_MONTH
        note_suffix = " (override)" if override else ""
        return {**role, "instance_type": inst, "hourly_usd": round(hourly, 4),
                "compute_monthly_usd": round(monthly, 2),
                "storage_monthly_usd": 0, "monthly_usd": round(monthly, 2),
                "from_api": from_api, "note": f"{nodes}× {inst}{note_suffix}"}

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

    # Bastion host — always t3a.medium (AMD EPYC, 2vCPU/4GB, cost-optimised)
    if key == "bastion" and vcpu > 0:
        instance_type = "t3a.medium"
        hourly        = EC2_FALLBACK["t3a.medium"] * AWS_REGIONS.get(region, {}).get("multiplier", 1.0)
        from_api      = False
        compute_monthly = hourly * nodes * HOURS_PER_MONTH
        reg_mult = AWS_REGIONS.get(region, {}).get("multiplier", 1.0)
        storage_monthly = storage * EBS_GP3_PER_GB * reg_mult
        monthly         = compute_monthly + storage_monthly
        return {**role, "instance_type": instance_type, "hourly_usd": round(hourly, 4),
                "compute_monthly_usd": round(compute_monthly, 2),
                "storage_monthly_usd": round(storage_monthly, 2),
                "monthly_usd": round(monthly, 2), "from_api": from_api,
                "note": f"{nodes}× {instance_type} (fixed: bastion policy)"}

    # Everything else (WAF, Route53, CloudTrail etc.) — zero compute cost
    return {**role, "instance_type": "Managed Service", "hourly_usd": 0,
            "compute_monthly_usd": 0, "storage_monthly_usd": 0,
            "monthly_usd": 0, "from_api": False,
            "note": "No direct instance cost"}


# ── CloudWatch add-on ─────────────────────────────────────────────────────

def _price_clickhouse_roles(
    ch_sizing: dict,
    pricing_client,
    ec2_client,
    region: str = "us-east-1",
) -> list:
    """
    Price all ClickHouse nodes (DB Cluster + Keeper Cluster).

    DB nodes  → Memory Intensive EC2 (r5/r6a) + EBS gp3 storage
                (high-throughput columnar storage; gp3 handles merge I/O)
    Keeper nodes → General Purpose EC2 (m5/c6i) + EBS gp3
    """
    if not ch_sizing or not ch_sizing.get("enabled"):
        return []

    reg_mult = AWS_REGIONS.get(region, {}).get("multiplier", 1.0)
    priced   = []

    # ── ClickHouse DB Cluster nodes ───────────────────────────────────────
    db_cluster = ch_sizing.get("db_cluster", {})
    for node in db_cluster.get("nodes", []):
        vcpu    = node["vcpu_per_node"]
        ram     = node["ram_per_node"]
        storage = node["storage_per_node_gb"]

        itype, hourly, from_api = _resolve_ec2_instance(
            vcpu, ram, "memory", pricing_client, ec2_client, region
        )
        compute_monthly = hourly * HOURS_PER_MONTH
        # gp3 for ClickHouse data nodes — handles high-throughput part merges
        storage_monthly = storage * EBS_GP3_PER_GB * reg_mult
        monthly         = round(compute_monthly + storage_monthly, 2)

        priced.append({
            **node,
            "instance_type":        itype,
            "hourly_usd":           round(hourly, 4),
            "compute_monthly_usd":  round(compute_monthly, 2),
            "storage_monthly_usd":  round(storage_monthly, 2),
            "monthly_usd":          monthly,
            "from_api":             from_api,
            "note": (
                f"Shard {node['shard']} / Replica {node['replica']} — "
                f"{itype} @ ${hourly:.4f}/hr + {storage:,}GB EBS gp3 "
                f"(${storage * EBS_GP3_PER_GB * reg_mult:,.2f}/mo)"
            ),
        })

    # ── ClickHouse Keeper Cluster nodes ───────────────────────────────────
    keeper_cluster = ch_sizing.get("keeper_cluster", {})
    for node in keeper_cluster.get("nodes", []):
        vcpu    = node["vcpu_per_node"]
        ram     = node["ram_per_node"]
        storage = node["storage_per_node_gb"]

        itype, hourly, from_api = _resolve_ec2_instance(
            vcpu, ram, "general", pricing_client, ec2_client, region
        )
        compute_monthly = hourly * HOURS_PER_MONTH
        storage_monthly = storage * EBS_GP3_PER_GB * reg_mult
        monthly         = round(compute_monthly + storage_monthly, 2)

        priced.append({
            **node,
            "instance_type":        itype,
            "hourly_usd":           round(hourly, 4),
            "compute_monthly_usd":  round(compute_monthly, 2),
            "storage_monthly_usd":  round(storage_monthly, 2),
            "monthly_usd":          monthly,
            "from_api":             from_api,
            "note": (
                f"Keeper Node {node['role_key'].split('_')[-1]} — "
                f"{itype} @ ${hourly:.4f}/hr + {storage}GB EBS gp3"
            ),
        })

    return priced


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


def _price_ai_roles(ai_sizing: dict, region: str) -> list:
    """
    Convert ai_nodes structure from distribute_nodes() into priced_role dicts
    using P-series GPU instances. One role entry per (ai_type, environment) combo.
    """
    roles = []
    environments = ai_sizing.get("environments", {})
    bedrock_monthly = ai_sizing.get("bedrock_monthly", 0)

    # Type → human label + category
    TYPE_META = {
        "predictive": ("Predictive AI Cluster", "AI Services"),
        "genai":      ("Generative AI Cluster", "AI Services"),
        "agentic":    ("Agentic AI Cluster",    "AI Services"),
    }

    # Environment label mapping
    ENV_LABELS = {"prod": "Production", "uat": "UAT", "sit": "SIT", "dr": "DR"}

    for ai_type, envs in environments.items():
        label_prefix, category = TYPE_META.get(ai_type, (f"{ai_type.title()} AI", "AI Services"))
        for env_key, env_cfg in envs.items():
            services = env_cfg.get("services", [])
            env_label = ENV_LABELS.get(env_key, env_key.upper())
            for svc in services:
                nodes   = svc.get("nodes", 1)
                vcpu    = svc.get("vcpu_per_node", 8)
                ram_gb  = svc.get("ram_per_node_gb", 32)
                storage = svc.get("storage_per_node_gb", 200)
                role_name = svc.get("name", label_prefix)

                # Select P-series GPU instance
                inst_type = _gpu_instance(vcpu, ram_gb)
                spec      = P_SERIES_CATALOG.get(inst_type, {})
                hourly    = spec.get("hourly_base", 3.06)
                monthly   = round(nodes * hourly * 730, 2)

                roles.append({
                    "label":          f"{role_name} ({env_label})",
                    "category":       category,
                    "role_key":       f"ai_{ai_type}_{env_key}",
                    "nodes":          nodes,
                    "vcpu_per_node":  vcpu,
                    "ram_per_node":   f"{ram_gb}GB",
                    "storage_per_node_gb": storage,
                    "instance_type":  inst_type,
                    "hourly_usd":     round(hourly * nodes, 4),
                    "compute_monthly_usd": monthly,
                    "storage_monthly_usd": 0,
                    "monthly_usd":    monthly,
                    "from_api":       False,
                    "note":           f"{nodes}× {inst_type} | {spec.get('gpu',1)}× {spec.get('gpu_model','V100')} GPU | {vcpu}vCPU {ram_gb}GB RAM",
                    "reasoning":      f"GPU compute for {ai_type} AI workloads in {env_label}",
                })

    # Add Bedrock/LLM API cost if any
    if bedrock_monthly > 0:
        roles.append({
            "label":          "Managed LLM API (Bedrock/External)",
            "category":       "AI Services",
            "role_key":       "ai_bedrock",
            "nodes":          0,
            "vcpu_per_node":  None,
            "ram_per_node":   None,
            "storage_per_node_gb": 0,
            "instance_type":  "Managed API",
            "hourly_usd":     0,
            "compute_monthly_usd": round(bedrock_monthly, 2),
            "storage_monthly_usd": 0,
            "monthly_usd":    round(bedrock_monthly, 2),
            "from_api":       False,
            "note":           f"AWS Bedrock / external LLM API — estimated ${bedrock_monthly:,.0f}/mo",
            "reasoning":      "GenAI inference API cost",
        })

    return roles


# ── Public API ────────────────────────────────────────────────────────────

def calculate_pricing(distribution: dict, metrics: dict, region: str = "us-east-1", instance_overrides: dict | None = None) -> dict:
    """
    Main entry point.

    Args:
        distribution: output of node_distributor.distribute_nodes()
        metrics:      output of excel_handler.extract_metrics()
        instance_overrides: optional dict mapping role_key -> instance_type string

    Returns rich pricing dict with:
        priced_roles, category_totals,
        total_monthly_usd, total_annual_usd, total_3year_usd,
        assumptions, warnings
    """
    pricing_client = _init_pricing(region)
    ec2_client     = _init_ec2(region)
    data_gb        = metrics.get("data_size_gb", 0)
    warnings       = []
    priced_roles   = []
    overrides      = instance_overrides or {}

    # 1. Worker nodes
    for role in distribution.get("worker_nodes", []):
        priced_roles.append(_price_worker_role(role, pricing_client, ec2_client, region, overrides))

    # 2. DB + storage nodes
    for role in distribution.get("db_nodes", []):
        priced_roles.append(_price_db_role(role, pricing_client, ec2_client, region, overrides))

    # 3. Fixed infra roles
    for role in distribution.get("fixed_roles", []):
        priced_roles.append(_price_fixed_role(role, pricing_client, ec2_client, data_gb, region, overrides))

    # 4. ClickHouse nodes (optional)
    ch_sizing = distribution.get("clickhouse_nodes")
    if ch_sizing and ch_sizing.get("enabled"):
        ch_priced = _price_clickhouse_roles(ch_sizing, pricing_client, ec2_client, region)
        priced_roles.extend(ch_priced)
        print(f"[aws_pricer] Priced {len(ch_priced)} ClickHouse nodes")

    # 5. AI Service nodes (optional) — GPU / P-series instances
    ai_sizing = distribution.get("ai_nodes", {})
    if ai_sizing and ai_sizing.get("enabled"):
        ai_priced = _price_ai_roles(ai_sizing, region)
        priced_roles.extend(ai_priced)
        print(f"[aws_pricer] Priced {len(ai_priced)} AI GPU node roles")

    # 6. CloudWatch (include ClickHouse nodes in monitored count)
    total_worker = distribution["summary"]["total_worker_nodes"]
    total_db     = distribution["summary"]["total_db_nodes"]
    total_ch     = distribution["summary"].get("total_clickhouse_nodes", 0)
    priced_roles.append(_cloudwatch_cost(total_worker + total_db + total_ch))

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
    # Derive per-node RAM: total RAM / 2 primary nodes, snapped to nearest tier
    # Apply 1.5× headroom (buffer pools, OS page cache, replica overhead)
    _pg_raw_per_node = (postgres_ram / 2) if postgres_ram > 0 else 128
    _MEM_TIERS = [(8, 32), (16, 64), (32, 128), (48, 192), (64, 256)]
    pg_vcpu_node, pg_ram_node = _MEM_TIERS[-1]
    for _v, _r in _MEM_TIERS:
        if (_pg_raw_per_node * 1.5) <= _r:
            pg_vcpu_node, pg_ram_node = _v, _r
            break
    pg_instance, pg_hourly, _ = _resolve_ec2_instance(pg_vcpu_node, pg_ram_node, "memory", pricing_client, ec2_client, region)
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
            "reason":    "No licensing cost. HA via Patroni+etcd on EC2.",
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
            "os":                "Linux",
            "ebs_type":          "gp3 (compute & SAN/DB)",
            "pricing_date":      "2026-03",
            "inflation_rate":    f"{INFLATION_RATE*100:.0f}% per year",
            "db_hosting_note":   "PostgreSQL=Self-Hosted EC2, SQL Server/Oracle=AWS Managed",
        },
        "warnings": warnings,
    }
