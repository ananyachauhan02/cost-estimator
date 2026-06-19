"""
aws_machine_catalog.py — AWS EC2 Instance Catalog
==================================================
Single source of truth for ALL AWS context:
  • EC2 instance specs (vCPU, RAM GB)
  • On-demand hourly prices — us-east-1 base (March 2025)
  • Regional multipliers & availability
  • EBS, S3, ElastiCache, ALB, NAT pricing constants
  • best_ec2_instance(vcpu, ram_gb, family, region) — fallback selector

Regional prices = base_hourly × AWS_REGIONS[region]["multiplier"]
Pricing source: AWS EC2 On-Demand pricing page, March 2025.
"""
from __future__ import annotations

# ── AWS Regions — label + price multiplier vs us-east-1 base ─────────────
AWS_REGIONS: dict[str, dict] = {
    # Americas
    "us-east-1":      {"label": "US East (N. Virginia)",        "multiplier": 1.000},
    "us-east-2":      {"label": "US East (Ohio)",               "multiplier": 0.990},
    "us-west-1":      {"label": "US West (N. California)",      "multiplier": 1.090},
    "us-west-2":      {"label": "US West (Oregon)",             "multiplier": 1.000},
    "ca-central-1":   {"label": "Canada (Central)",             "multiplier": 1.030},
    "ca-west-1":      {"label": "Canada West (Calgary)",        "multiplier": 1.030},
    "sa-east-1":      {"label": "South America (São Paulo)",    "multiplier": 1.200},
    # Europe
    "eu-central-1":   {"label": "Europe (Frankfurt)",           "multiplier": 1.090},
    "eu-central-2":   {"label": "Europe (Zurich)",              "multiplier": 1.150},
    "eu-west-1":      {"label": "Europe (Ireland)",             "multiplier": 1.050},
    "eu-west-2":      {"label": "Europe (London)",              "multiplier": 1.090},
    "eu-west-3":      {"label": "Europe (Paris)",               "multiplier": 1.090},
    "eu-north-1":     {"label": "Europe (Stockholm)",           "multiplier": 1.060},
    "eu-south-1":     {"label": "Europe (Milan)",               "multiplier": 1.090},
    "eu-south-2":     {"label": "Europe (Spain)",               "multiplier": 1.090},
    # Asia Pacific
    "ap-south-1":     {"label": "Asia Pacific (Mumbai)",        "multiplier": 1.080},
    "ap-south-2":     {"label": "Asia Pacific (Hyderabad)",     "multiplier": 1.080},
    "ap-northeast-1": {"label": "Asia Pacific (Tokyo)",         "multiplier": 1.120},
    "ap-northeast-2": {"label": "Asia Pacific (Seoul)",         "multiplier": 1.120},
    "ap-northeast-3": {"label": "Asia Pacific (Osaka)",         "multiplier": 1.120},
    "ap-southeast-1": {"label": "Asia Pacific (Singapore)",     "multiplier": 1.100},
    "ap-southeast-2": {"label": "Asia Pacific (Sydney)",        "multiplier": 1.130},
    "ap-southeast-3": {"label": "Asia Pacific (Jakarta)",       "multiplier": 1.100},
    "ap-southeast-4": {"label": "Asia Pacific (Melbourne)",     "multiplier": 1.130},
    "ap-southeast-5": {"label": "Asia Pacific (Malaysia)",      "multiplier": 1.100},
    "ap-east-1":      {"label": "Asia Pacific (Hong Kong)",     "multiplier": 1.180},
    # Middle East & Africa
    "me-south-1":     {"label": "Middle East (Bahrain)",        "multiplier": 1.150},
    "me-central-1":   {"label": "Middle East (UAE)",            "multiplier": 1.150},
    "af-south-1":     {"label": "Africa (Cape Town)",           "multiplier": 1.200},
    "il-central-1":   {"label": "Israel (Tel Aviv)",            "multiplier": 1.160},
}

# ── EC2 instance specs + us-east-1 on-demand hourly price ────────────────
# fmt: (vcpu, ram_gb, hourly_usd_us_east_1)
_I: dict[str, tuple[int, float, float]] = {

    # ── r6a — AMD EPYC, Memory-Optimised (8 GB/vCPU) ────────────────────
    "r6a.large":    (2,   16,   0.11340),
    "r6a.xlarge":   (4,   32,   0.22680),
    "r6a.2xlarge":  (8,   64,   0.45360),
    "r6a.4xlarge":  (16,  128,  0.90720),
    "r6a.8xlarge":  (32,  256,  1.81440),
    "r6a.12xlarge": (48,  384,  2.72160),
    "r6a.16xlarge": (64,  512,  3.62880),
    "r6a.24xlarge": (96,  768,  5.44320),
    "r6a.48xlarge": (192, 1536, 10.88640),

    # ── r6i — Intel Ice Lake, Memory-Optimised (8 GB/vCPU) ──────────────
    "r6i.large":    (2,   16,   0.12600),
    "r6i.xlarge":   (4,   32,   0.25200),
    "r6i.2xlarge":  (8,   64,   0.50400),
    "r6i.4xlarge":  (16,  128,  1.00800),
    "r6i.8xlarge":  (32,  256,  2.01600),
    "r6i.12xlarge": (48,  384,  3.02400),
    "r6i.16xlarge": (64,  512,  4.03200),
    "r6i.24xlarge": (96,  768,  6.04800),

    # ── r5 — Intel Xeon, Memory-Optimised (8 GB/vCPU) ───────────────────
    "r5.large":     (2,   16,   0.12600),
    "r5.xlarge":    (4,   32,   0.25200),
    "r5.2xlarge":   (8,   64,   0.50400),
    "r5.4xlarge":   (16,  128,  1.00800),
    "r5.8xlarge":   (32,  256,  2.01600),
    "r5.12xlarge":  (48,  384,  3.02400),
    "r5.16xlarge":  (64,  512,  4.03200),
    "r5.24xlarge":  (96,  768,  6.04800),

    # ── m6i — Intel Ice Lake, General Purpose (4 GB/vCPU) ───────────────
    "m6i.large":    (2,   8,    0.09600),
    "m6i.xlarge":   (4,   16,   0.19200),
    "m6i.2xlarge":  (8,   32,   0.38400),
    "m6i.4xlarge":  (16,  64,   0.76800),
    "m6i.8xlarge":  (32,  128,  1.53600),
    "m6i.12xlarge": (48,  192,  2.30400),
    "m6i.16xlarge": (64,  256,  3.07200),
    "m6i.24xlarge": (96,  384,  4.60800),

    # ── m6a — AMD EPYC, General Purpose (4 GB/vCPU) ─────────────────────
    "m6a.large":    (2,   8,    0.08640),
    "m6a.xlarge":   (4,   16,   0.17280),
    "m6a.2xlarge":  (8,   32,   0.34560),
    "m6a.4xlarge":  (16,  64,   0.69120),
    "m6a.8xlarge":  (32,  128,  1.38240),
    "m6a.12xlarge": (48,  192,  2.07360),
    "m6a.16xlarge": (64,  256,  2.76480),
    "m6a.24xlarge": (96,  384,  4.14720),
    "m6a.48xlarge": (192, 768,  8.29440),

    # ── m5 — Intel Xeon, General Purpose (4 GB/vCPU) ────────────────────
    "m5.large":     (2,   8,    0.09600),
    "m5.xlarge":    (4,   16,   0.19200),
    "m5.2xlarge":   (8,   32,   0.38400),
    "m5.4xlarge":   (16,  64,   0.76800),
    "m5.8xlarge":   (32,  128,  1.53600),
    "m5.12xlarge":  (48,  192,  2.30400),
    "m5.16xlarge":  (64,  256,  3.07200),

    # ── c6a — AMD EPYC, Compute-Optimised (2 GB/vCPU) ───────────────────
    "c6a.large":    (2,   4,    0.07650),
    "c6a.xlarge":   (4,   8,    0.15300),
    "c6a.2xlarge":  (8,   16,   0.30600),
    "c6a.4xlarge":  (16,  32,   0.61200),
    "c6a.8xlarge":  (32,  64,   1.22400),
    "c6a.12xlarge": (48,  96,   1.83600),
    "c6a.16xlarge": (64,  128,  2.44800),
    "c6a.24xlarge": (96,  192,  3.67200),
    "c6a.48xlarge": (192, 384,  7.34400),

    # ── c6i — Intel Ice Lake, Compute-Optimised (2 GB/vCPU) ─────────────
    "c6i.large":    (2,   4,    0.08500),
    "c6i.xlarge":   (4,   8,    0.17000),
    "c6i.2xlarge":  (8,   16,   0.34000),
    "c6i.4xlarge":  (16,  32,   0.68000),
    "c6i.8xlarge":  (32,  64,   1.36000),
    "c6i.12xlarge": (48,  96,   2.04000),
    "c6i.16xlarge": (64,  128,  2.72000),

    # ── t3a — AMD EPYC, Burstable (variable GB/vCPU) ────────────────────
    "t3a.small":    (2,   2,    0.01880),
    "t3a.medium":   (2,   4,    0.03760),
    "t3a.large":    (2,   8,    0.07520),
    "t3a.xlarge":   (4,   16,   0.15040),
    "t3a.2xlarge":  (8,   32,   0.30080),

    # ── t3 — Intel, Burstable ────────────────────────────────────────────
    "t3.small":     (2,   2,    0.02080),
    "t3.medium":    (2,   4,    0.04160),
    "t3.large":     (2,   8,    0.08320),
    "t3.xlarge":    (4,   16,   0.16640),
}

EC2_CATALOG: dict[str, dict] = {
    k: {"vcpu": v[0], "ram_gb": v[1], "hourly_base": v[2]}
    for k, v in _I.items()
}

# ── Instance family membership ────────────────────────────────────────────
EC2_FAMILIES: dict[str, list[str]] = {
    "r6a":  [k for k in EC2_CATALOG if k.startswith("r6a")],
    "r6i":  [k for k in EC2_CATALOG if k.startswith("r6i")],
    "r5":   [k for k in EC2_CATALOG if k.startswith("r5")],
    "m6i":  [k for k in EC2_CATALOG if k.startswith("m6i")],
    "m6a":  [k for k in EC2_CATALOG if k.startswith("m6a")],
    "m5":   [k for k in EC2_CATALOG if k.startswith("m5")],
    "c6a":  [k for k in EC2_CATALOG if k.startswith("c6a")],
    "c6i":  [k for k in EC2_CATALOG if k.startswith("c6i")],
    "t3a":  [k for k in EC2_CATALOG if k.startswith("t3a")],
    "t3":   [k for k in EC2_CATALOG if k.startswith("t3")],
}

# ── Region → available EC2 families ──────────────────────────────────────
_REGION_FAMILIES: dict[str, list[str]] = {
    # Americas
    "us-east-1":      ["r6a","r6i","r5","m6i","m6a","m5","c6a","c6i","t3a","t3"],
    "us-east-2":      ["r6a","r6i","r5","m6i","m6a","m5","c6a","c6i","t3a","t3"],
    "us-west-1":      ["r6i","r5","m6i","m5","c6i","t3a","t3"],
    "us-west-2":      ["r6a","r6i","r5","m6i","m6a","m5","c6a","c6i","t3a","t3"],
    "ca-central-1":   ["r6i","r5","m6i","m5","c6i","t3a","t3"],
    "sa-east-1":      ["r5","m5","c6i","t3a","t3"],
    # Europe
    "eu-central-1":   ["r6a","r6i","r5","m6i","m6a","m5","c6a","c6i","t3a","t3"],
    "eu-west-1":      ["r6a","r6i","r5","m6i","m6a","m5","c6a","c6i","t3a","t3"],
    "eu-west-2":      ["r6i","r5","m6i","m5","c6a","c6i","t3a","t3"],
    "eu-west-3":      ["r6i","r5","m6i","m5","c6i","t3a","t3"],
    "eu-north-1":     ["r6i","r5","m6i","m5","c6i","t3a","t3"],
    "eu-south-1":     ["r5","m5","c6i","t3a"],
    # Asia Pacific
    "ap-south-1":     ["r6a","r6i","r5","m6i","m6a","m5","c6a","c6i","t3a","t3"],
    "ap-south-2":     ["r6i","r5","m6i","m5","c6i","t3a"],
    "ap-northeast-1": ["r6i","r5","m6i","m6a","m5","c6i","t3a","t3"],
    "ap-northeast-2": ["r6i","r5","m6i","m5","c6i","t3a","t3"],
    "ap-northeast-3": ["r5","m5","t3a"],
    "ap-southeast-1": ["r6a","r6i","r5","m6i","m6a","m5","c6a","c6i","t3a","t3"],
    "ap-southeast-2": ["r6i","r5","m6i","m5","c6i","t3a","t3"],
    "ap-southeast-3": ["r5","m5","t3a"],
    "ap-east-1":      ["r5","m5","c6i","t3a"],
    # Middle East & Africa
    "me-south-1":     ["r5","m5","c6i","t3a"],
    "me-central-1":   ["r5","m5","c6i","t3a"],
    "af-south-1":     ["r5","m5","t3a"],
    "il-central-1":   ["r5","m5","c6i","t3a"],
}

def region_families(region: str) -> list[str]:
    """Return EC2 families available in a region."""
    return _REGION_FAMILIES.get(region, ["r5", "m5", "t3a"])

# ── Storage & managed service pricing (us-east-1 base) ───────────────────
EBS_GP3_PER_GB_MONTH   = 0.080    # $/GB/month
EBS_IO2_PER_GB_MONTH   = 0.125    # $/GB/month (kept for reference)
S3_PER_GB_MONTH        = 0.023    # $/GB/month
ALB_BASE_MONTHLY       = 16.43    # $ Application Load Balancer base
NAT_BASE_MONTHLY       = 32.00    # $ ~2 NAT gateways base
NAT_PER_GB             = 0.045    # $/GB processed
CLOUDWATCH_PER_NODE    = 3.50     # $/node/month (CloudWatch + Container Insights)

# ElastiCache — r6g series (us-east-1 on-demand hourly)
ELASTICACHE_HOURLY: dict[str, float] = {
    "cache.r6g.large":   0.15400,
    "cache.r6g.xlarge":  0.30800,
    "cache.r6g.2xlarge": 0.61600,
    "cache.r6g.4xlarge": 1.23200,
    "cache.r6g.8xlarge": 2.46400,
}

# S3 server (self-hosted MinIO-equiv) — used for replication nodes
S3_SERVER_HOURLY: dict[str, float] = {
    "s3.t3.medium":  0.065,
    "s3.c5.large":   0.154,
    "s3.c5.2xlarge": 0.308,
}

# ── Best-fit selector ─────────────────────────────────────────────────────

def best_ec2_instance(
    vcpu: int,
    ram_gb: float,
    region: str = "us-east-1",
    prefer_families: list[str] | None = None,
    allow_cpu_compromise: bool = True,
) -> dict:
    """
    Find the smallest EC2 instance satisfying (vcpu, ram_gb) in a region.

    Selection order:
      1. Use prefer_families if given (e.g. ["r6a","r5"] for memory roles).
      2. Fall back to any available family in the region.
      3. With allow_cpu_compromise=True, accept instances with vcpu >= vcpu/2
         (mirrors aws_pricer 50% compromise logic).

    Returns:
        {type, vcpu, ram_gb, hourly_base, hourly_regional, family}
    """
    mult    = AWS_REGIONS.get(region, {}).get("multiplier", 1.0)
    avail   = region_families(region)
    ordered = [f for f in (prefer_families or []) if f in avail]
    # append remaining available families not already in ordered
    for f in avail:
        if f not in ordered:
            ordered.append(f)

    vcpu_min = vcpu // 2 if allow_cpu_compromise else vcpu

    for fam in ordered:
        candidates = [
            (name, specs)
            for name, specs in EC2_CATALOG.items()
            if name.startswith(fam)
            and specs["vcpu"] >= vcpu_min
            and specs["ram_gb"] >= ram_gb
        ]
        if candidates:
            name, specs = min(candidates, key=lambda x: x[1]["hourly_base"])
            return {
                "type":            name,
                "family":          fam,
                "vcpu":            specs["vcpu"],
                "ram_gb":          specs["ram_gb"],
                "hourly_base":     specs["hourly_base"],
                "hourly_regional": round(specs["hourly_base"] * mult, 6),
            }

    # Hard fallback: t3a.medium
    specs = EC2_CATALOG["t3a.medium"]
    return {
        "type":            "t3a.medium",
        "family":          "t3a",
        "vcpu":            specs["vcpu"],
        "ram_gb":          specs["ram_gb"],
        "hourly_base":     specs["hourly_base"],
        "hourly_regional": round(specs["hourly_base"] * mult, 6),
    }


def ec2_hourly(instance_type: str, region: str = "us-east-1") -> float:
    """
    Return on-demand hourly price for a known instance type in a region.
    Falls back to catalog base × multiplier, then EC2_CATALOG base price.
    """
    mult  = AWS_REGIONS.get(region, {}).get("multiplier", 1.0)
    specs = EC2_CATALOG.get(instance_type)
    if specs:
        return round(specs["hourly_base"] * mult, 6)
    return 0.0
