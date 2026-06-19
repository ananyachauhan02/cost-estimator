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
  EBS gp3/SAN   → Persistent Disk SSD (approx)
"""
from __future__ import annotations

import os
import math
import requests
from gcp_machine_catalog import best_gce_instance as _catalog_best


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
# (PD_EXTREME_PER_GB removed, using PD_SSD_PER_GB * 730)
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

# ── GCP GPU instance catalog (A2 = A100, G2 = L4, equivalent to AWS P-series) ──
# Source: https://cloud.google.com/compute/docs/gpus
GCP_GPU_CATALOG: dict[str, dict] = {
    # ── A2 family (NVIDIA A100 40GB) ── equivalent to AWS p4d ───────────────
    "a2-highgpu-1g":  {"vcpu":  12, "ram_gb":  85,   "gpu": 1, "gpu_model": "A100 40GB", "hourly_base": 3.673},
    "a2-highgpu-2g":  {"vcpu":  24, "ram_gb":  170,  "gpu": 2, "gpu_model": "A100 40GB", "hourly_base": 7.346},
    "a2-highgpu-4g":  {"vcpu":  48, "ram_gb":  340,  "gpu": 4, "gpu_model": "A100 40GB", "hourly_base": 14.693},
    "a2-highgpu-8g":  {"vcpu":  96, "ram_gb":  680,  "gpu": 8, "gpu_model": "A100 40GB", "hourly_base": 29.387},
    "a2-megagpu-16g": {"vcpu": 96, "ram_gb":  1360, "gpu": 16, "gpu_model": "A100 40GB", "hourly_base": 55.739},
    # ── A2 Ultra family (NVIDIA A100 80GB) ──────────────────────────────
    "a2-ultragpu-1g": {"vcpu":  12, "ram_gb":  170,  "gpu": 1, "gpu_model": "A100 80GB", "hourly_base": 5.184},
    "a2-ultragpu-2g": {"vcpu":  24, "ram_gb":  340,  "gpu": 2, "gpu_model": "A100 80GB", "hourly_base": 10.368},
    "a2-ultragpu-4g": {"vcpu":  48, "ram_gb":  680,  "gpu": 4, "gpu_model": "A100 80GB", "hourly_base": 20.736},
    "a2-ultragpu-8g": {"vcpu":  96, "ram_gb":  1360, "gpu": 8, "gpu_model": "A100 80GB", "hourly_base": 41.473},
    # ── G2 family (NVIDIA L4) ── cost-effective GPU for inference ─────────
    "g2-standard-4":  {"vcpu":  4,  "ram_gb":  16,   "gpu": 1, "gpu_model": "L4 24GB",   "hourly_base": 0.7063},
    "g2-standard-8":  {"vcpu":  8,  "ram_gb":  32,   "gpu": 1, "gpu_model": "L4 24GB",   "hourly_base": 1.1032},
    "g2-standard-12": {"vcpu":  12, "ram_gb":  48,   "gpu": 1, "gpu_model": "L4 24GB",   "hourly_base": 1.5001},
    "g2-standard-16": {"vcpu":  16, "ram_gb":  64,   "gpu": 1, "gpu_model": "L4 24GB",   "hourly_base": 1.8970},
    "g2-standard-24": {"vcpu":  24, "ram_gb":  96,   "gpu": 2, "gpu_model": "L4 24GB",   "hourly_base": 3.0064},
    "g2-standard-32": {"vcpu":  32, "ram_gb":  128,  "gpu": 1, "gpu_model": "L4 24GB",   "hourly_base": 3.6929},
    "g2-standard-48": {"vcpu":  48, "ram_gb":  192,  "gpu": 4, "gpu_model": "L4 24GB",   "hourly_base": 6.0128},
    "g2-standard-96": {"vcpu":  96, "ram_gb":  384,  "gpu": 8, "gpu_model": "L4 24GB",   "hourly_base": 12.0255},
}

def _gcp_gpu_instance(vcpu: int, ram_gb: float) -> dict:
    """Select cheapest A2/G2 GPU instance that meets the vCPU+RAM requirements."""
    # Prefer G2 (L4) for smaller workloads (inference), A2 (A100) for larger (training)
    ordered = [
        "g2-standard-4", "g2-standard-8", "g2-standard-12", "g2-standard-16",
        "g2-standard-24", "g2-standard-32", "g2-standard-48", "g2-standard-96",
        "a2-highgpu-1g", "a2-highgpu-2g", "a2-highgpu-4g", "a2-highgpu-8g",
        "a2-ultragpu-1g", "a2-ultragpu-2g", "a2-ultragpu-4g", "a2-ultragpu-8g",
        "a2-megagpu-16g",
    ]
    for name in ordered:
        spec = GCP_GPU_CATALOG[name]
        if spec["vcpu"] >= vcpu // 2 and spec["ram_gb"] >= ram_gb:
            return {"type": name, **spec}
    return {"type": "a2-highgpu-8g", **GCP_GPU_CATALOG["a2-highgpu-8g"]}

# ── GCP Cloud Billing Catalog API ────────────────────────────────────────────
_GCP_BILLING_BASE   = "https://cloudbilling.googleapis.com/v1"
_GCE_SERVICE_ID     = "6F81-5844-456A"   # Compute Engine
_MEMSTORE_SERVICE_ID= "58CD-E7C3-72CA"   # Memorystore (Redis)
_SKU_CACHE: dict[tuple[str, str], list] = {}   # (service_id, region) → [skus]

# ── GCP equivalent instance sizing ───────────────────────────────────────

def _gce_instance(vcpu: int, ram_gb: float, family_hint: str = "", region: str = "us-central1") -> dict:
    """
    Return the closest-fit GCP predefined machine type for (vcpu, ram_gb).
    Routes GPU/AI workloads to A2 (A100) or G2 (L4) instances.
    Falls back to n2-highmem/standard for regular workloads.
    """
    hint = (family_hint or "").lower()

    # GPU / P-series route — map to GCP A2/G2 equivalents
    if "gpu" in hint or "p-series" in hint or "p series" in hint:
        spec = _gcp_gpu_instance(vcpu, ram_gb)
        mult = 1.0   # regional multipliers handled upstream
        return {"type": spec["type"], "vcpu": spec["vcpu"], "ram_gb": spec["ram_gb"], "hourly": spec["hourly_base"]}

    try:
        prefer_amd = "amd" in hint
        result = _catalog_best(vcpu, ram_gb, region, prefer_amd=prefer_amd)
        return {
            "type":    result["type"],
            "vcpu":    result["vcpu"],
            "ram_gb":  result["ram_gb"],
            "hourly":  result["hourly_base"],   # _price_gce_role applies mult separately
        }
    except Exception:
        # Legacy fallback
        is_mem = "memory" in hint or (ram_gb / max(vcpu, 1)) >= 8
        valid  = [2, 4, 8, 16, 32, 48, 64, 80, 96]
        v      = next((x for x in valid if x >= vcpu), 96)
        if is_mem:
            r = v * 8
            return {"type": f"n2-highmem-{v}", "vcpu": v, "ram_gb": r,
                    "hourly": v * GCE_VCPU_HOUR + r * GCE_RAM_HOUR_HM}
        else:
            r = v * 4
            return {"type": f"n2-standard-{v}", "vcpu": v, "ram_gb": r,
                    "hourly": v * GCE_VCPU_HOUR + r * GCE_RAM_HOUR_STD}


# ── AWS instance actual specs (vCPU, RAM GB) ─────────────────────────────
# Used to resolve the *actual* instance size when vcpu_per_node stores
# the *required* vCPUs from the sizing step (may differ due to compromise).
_AWS_INSTANCE_SPECS: dict[str, tuple[int, int]] = {
    # r6a – memory optimised AMD (8 GB / vCPU)
    "r6a.large": (2, 16),    "r6a.xlarge": (4, 32),    "r6a.2xlarge": (8, 64),
    "r6a.4xlarge": (16, 128), "r6a.8xlarge": (32, 256), "r6a.12xlarge": (48, 384),
    "r6a.16xlarge": (64, 512), "r6a.24xlarge": (96, 768), "r6a.48xlarge": (192, 1536),
    # r6i – memory optimised Intel (8 GB / vCPU)
    "r6i.large": (2, 16),    "r6i.xlarge": (4, 32),    "r6i.2xlarge": (8, 64),
    "r6i.4xlarge": (16, 128), "r6i.8xlarge": (32, 256), "r6i.16xlarge": (64, 512),
    # r5 – memory optimised (8 GB / vCPU)
    "r5.large": (2, 16),    "r5.xlarge": (4, 32),    "r5.2xlarge": (8, 64),
    "r5.4xlarge": (16, 128), "r5.8xlarge": (32, 256),
    # m6i – general purpose Intel (4 GB / vCPU)
    "m6i.large": (2, 8),    "m6i.xlarge": (4, 16),    "m6i.2xlarge": (8, 32),
    "m6i.4xlarge": (16, 64), "m6i.8xlarge": (32, 128), "m6i.16xlarge": (64, 256),
    # m6a – general purpose AMD (4 GB / vCPU)
    "m6a.large": (2, 8),    "m6a.xlarge": (4, 16),    "m6a.2xlarge": (8, 32),
    "m6a.4xlarge": (16, 64), "m6a.8xlarge": (32, 128),
    # c6a – compute optimised AMD (2 GB / vCPU)
    "c6a.large": (2, 4),    "c6a.xlarge": (4, 8),    "c6a.2xlarge": (8, 16),
    "c6a.4xlarge": (16, 32), "c6a.8xlarge": (32, 64),
    # t3a / t3 – burstable
    "t3a.medium": (2, 4),   "t3a.large": (2, 8),    "t3a.xlarge": (4, 16),
    "t3.medium": (2, 4),    "t3.large": (2, 8),     "t3.xlarge": (4, 16),
}


def _aws_instance_specs(instance_type: str) -> tuple[int, int] | None:
    """Return (actual_vcpu, actual_ram_gb) for a known AWS instance type, or None."""
    return _AWS_INSTANCE_SPECS.get((instance_type or "").strip().lower())


def _memorystore_hourly(ram_gb: float) -> tuple[str, float]:
    if ram_gb <= 5:   return "redis-5gb",  MEMORYSTORE_HOURLY["5gb"]
    if ram_gb <= 16:  return "redis-16gb", MEMORYSTORE_HOURLY["16gb"]
    return "redis-32gb", MEMORYSTORE_HOURLY["32gb"]


# ── GCP Billing Catalog API helpers ──────────────────────────────────────────

def _init_gcp_api() -> str | None:
    """Return the GCP API key from env, or None if not configured."""
    return os.getenv("GCP_API_KEY") or None


def _sku_price(sku: dict) -> float:
    """Extract the first-tier hourly USD price from a raw SKU dict.
    GCP represents prices as { units: int, nanos: int } where
    price = units + nanos / 1_000_000_000.
    """
    try:
        pricing_info = sku.get("pricingInfo", [])
        if not pricing_info:
            return 0.0
        expr  = pricing_info[0].get("pricingExpression", {})
        rates = expr.get("tieredRates", [])
        # Use the first non-free tier (startUsageAmount == 0)
        for rate in rates:
            if rate.get("startUsageAmount", 0) == 0:
                up    = rate.get("unitPrice", {})
                units = int(up.get("units", 0))
                nanos = int(up.get("nanos", 0))
                return units + nanos / 1_000_000_000
    except Exception:
        pass
    return 0.0


def _fetch_gcp_skus(service_id: str, region: str, api_key: str) -> list:
    """Fetch all SKUs for *service_id* available in *region*, with pagination.
    Results are cached in _SKU_CACHE so repeated calls are free.
    """
    cache_key = (service_id, region)
    if cache_key in _SKU_CACHE:
        return _SKU_CACHE[cache_key]

    url     = f"{_GCP_BILLING_BASE}/services/{service_id}/skus"
    params  = {"key": api_key, "currencyCode": "USD"}
    skus: list = []
    try:
        while True:
            resp = requests.get(url, params=params, timeout=10)
            if resp.status_code != 200:
                print(f"[gcp_pricer] Billing API error {resp.status_code}: {resp.text[:200]}")
                break
            data      = resp.json()
            page_skus = data.get("skus", [])
            # Filter to SKUs that are available in the requested region
            for sku in page_skus:
                regions = sku.get("serviceRegions", [])
                if region in regions or "global" in regions:
                    skus.append(sku)
            next_token = data.get("nextPageToken")
            if not next_token:
                break
            params["pageToken"] = next_token
    except Exception as e:
        print(f"[gcp_pricer] SKU fetch failed for {service_id}/{region}: {e}")

    _SKU_CACHE[cache_key] = skus
    print(f"[gcp_pricer] Fetched {len(skus)} SKUs for service={service_id} region={region}")
    return skus


def _build_gce_price_map(skus: list) -> dict:
    """Build a lookup: (machine_family_lower, component) → price_per_unit_hour.
    component is 'cpu' or 'ram'.
    Examples:
      ('n2', 'cpu') → 0.031611   $/vCPU-hr
      ('n2', 'ram') → 0.004237   $/GB-hr  (standard)
      ('n2', 'ram_highmem') → 0.005678  $/GB-hr  (highmem)
    """
    price_map: dict = {}
    for sku in skus:
        desc = sku.get("description", "").lower()
        # Skip preemptible / spot / custom SKUs
        if any(x in desc for x in ["preemptible", "spot", "custom", "sole tenancy", "commitment", "sustained"]):
            continue

        price = _sku_price(sku)
        if price <= 0:
            continue

        # Determine machine family
        family = None
        for f in ["n2d", "n2", "n1", "c2d", "c2", "e2", "m1", "m2", "m3"]:
            if f in desc:
                family = f
                break
        if not family:
            continue

        # Component
        if "core" in desc or "vcpu" in desc or "cpu" in desc:
            price_map[(family, "cpu")] = price
        elif "ram" in desc or "memory" in desc:
            if "highmem" in desc or "high memory" in desc:
                price_map[(family, "ram_highmem")] = price
            else:
                price_map[(family, "ram")] = price

    return price_map


def _resolve_gce_hourly_api(
    vcpu: int, ram_gb: float, family_hint: str,
    region: str, api_key: str | None,
) -> tuple[str, float, bool]:
    """Return (gce_type, hourly_usd, from_api).
    Tries live Billing API first; falls back to hardcoded constants.
    """
    inst = _gce_instance(vcpu, ram_gb, family_hint)
    gce_type = inst["type"]   # e.g. 'n2-highmem-16'
    fallback = inst["hourly"]

    if not api_key:
        return gce_type, fallback, False

    try:
        skus      = _fetch_gcp_skus(_GCE_SERVICE_ID, region, api_key)
        price_map = _build_gce_price_map(skus)

        # Determine which family + RAM key to use
        is_highmem = "highmem" in gce_type
        # n2-highmem → family 'n2', n2-standard → family 'n2'
        fam = gce_type.split("-")[0]   # 'n2'

        cpu_rate = price_map.get((fam, "cpu"))
        ram_key  = "ram_highmem" if is_highmem else "ram"
        ram_rate = price_map.get((fam, ram_key)) or price_map.get((fam, "ram"))

        if cpu_rate and ram_rate:
            hourly = round(vcpu * cpu_rate + ram_gb * ram_rate, 6)
            return gce_type, hourly, True
    except Exception as e:
        print(f"[gcp_pricer] Live GCE price resolution failed: {e}")

    return gce_type, fallback, False


def _resolve_memorystore_hourly_api(
    ram_gb: float, region: str, api_key: str | None,
) -> tuple[str, float, bool]:
    """Return (instance_label, hourly_usd, from_api) for Memorystore Redis."""
    label, fallback = _memorystore_hourly(ram_gb)

    if not api_key:
        return label, fallback, False

    try:
        skus = _fetch_gcp_skus(_MEMSTORE_SERVICE_ID, region, api_key)
        # Look for Redis standard tier capacity SKU
        for sku in skus:
            desc = sku.get("description", "").lower()
            if "redis" in desc and "standard" in desc and "capacity" in desc:
                price = _sku_price(sku)
                if price > 0:
                    # price is per GB-hour; total = ram_gb * price
                    hourly = round(ram_gb * price, 6)
                    return label, hourly, True
    except Exception as e:
        print(f"[gcp_pricer] Live Memorystore price resolution failed: {e}")

    return label, fallback, False


# ── Role pricers ─────────────────────────────────────────────────────────

def _price_gce_role(role: dict, region: str, api_key: str | None = None) -> dict:
    # ── Resolve actual vCPU for the GCP equivalent ───────────────────────────
    # vcpu_per_node stores the *required* vCPUs from sizing (may differ from the
    # actual AWS instance vCPU due to 50% CPU compromise in aws_pricer).
    # We want the actual instance vCPU so GCP selects an equivalent machine.
    #
    # Priority order:
    #   1. Lookup from instance_type string (available when called with pricedRoles)
    #   2. Derive from ram_per_node using family-specific GB/vCPU ratio
    #   3. Fall back to vcpu_per_node (required vCPU)

    instance_type = role.get("instance_type", "")
    actual = _aws_instance_specs(instance_type)

    raw_vcpu = role.get("vcpu_per_node", 0)
    ram      = role.get("ram_per_node", 0)
    nodes    = role.get("nodes", 0)
    storage  = role.get("storage_per_node_gb", 0)
    family   = role.get("instance_family", "").lower()

    if actual:
        # Exact lookup — most accurate
        vcpu = actual[0]
        ram  = actual[1]
    elif "memory" in family and ram > 0:
        # r6a / r5 / r6i: 8 GB per vCPU → n2-highmem (also 8 GB/vCPU)
        # Derive actual vCPU by dividing required RAM by 8
        _valid = [2, 4, 8, 16, 32, 48, 64, 80, 96]
        vcpu = next((v for v in _valid if v >= max(round(ram / 8), 2)), 96)
    elif "general" in family and ram > 0:
        # m6i / m6a: 4 GB per vCPU → n2-standard (also 4 GB/vCPU)
        _valid = [2, 4, 8, 16, 32, 48, 64, 80, 96]
        vcpu = next((v for v in _valid if v >= max(round(ram / 4), 2)), 96)
    else:
        # Compute-optimised or unknown — use required vCPU directly
        vcpu = raw_vcpu


    if vcpu == 0 or nodes == 0:
        storage_mo = storage * nodes * PD_SSD_PER_GB * 730 if storage else 0
        return {**role,
                "gcp_instance_type": "N/A (storage only)",
                "gcp_hourly_usd": 0,
                "gcp_compute_monthly_usd": 0,
                "gcp_storage_monthly_usd": round(storage_mo, 2),
                "gcp_monthly_usd": round(storage_mo, 2),
                "from_api": False}

    mult  = GCP_REGIONS.get(region, {}).get("multiplier", 1.0)
    gce_type, base_hourly, from_api = _resolve_gce_hourly_api(vcpu, ram, family, region, api_key)
    hourly = round(base_hourly * (mult if not from_api else 1.0), 6)  # API prices are region-specific already

    compute_mo = hourly * nodes * HOURS_PER_MONTH
    storage_mo = storage * nodes * (PD_SSD_PER_GB * 730) * mult if storage else 0
    monthly    = round(compute_mo + storage_mo, 2)

    return {
        **role,
        "gcp_instance_type":         gce_type,
        "gcp_hourly_usd":            hourly,
        "gcp_compute_monthly_usd":   round(compute_mo, 2),
        "gcp_storage_monthly_usd":   round(storage_mo, 2),
        "gcp_monthly_usd":           monthly,
        "from_api":                  from_api,
        "gcp_note": f"{nodes}× {gce_type} @ ${hourly:.4f}/hr{'  ✓ live' if from_api else '  (est)'}",
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
        # Map to Persistent Disk SSD
        monthly = storage * nodes * (PD_SSD_PER_GB * 730) * mult
        return {**role,
                "gcp_instance_type": "Persistent Disk SSD",
                "gcp_hourly_usd": 0,
                "gcp_compute_monthly_usd": 0,
                "gcp_storage_monthly_usd": round(monthly, 2),
                "gcp_monthly_usd": round(monthly, 2),
                "gcp_note": f"{nodes}× {storage}GB PD SSD"}

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
    # Derive actual vCPU from RAM to match the actual AWS instance (not required vCPU).
    # memory family (r6a/r6i) = 8 GB/vCPU; general (m6i) = 4 GB/vCPU.
    if "memory" in family.lower() and ram > 0:
        _valid = [2, 4, 8, 16, 32, 48, 64, 80, 96]
        actual_vcpu = next((v for v in _valid if v >= max(round(ram / 8), 2)), 96)
    elif "general" in family.lower() and ram > 0:
        _valid = [2, 4, 8, 16, 32, 48, 64, 80, 96]
        actual_vcpu = next((v for v in _valid if v >= max(round(ram / 4), 2)), 96)
    else:
        actual_vcpu = vcpu
    inst  = _gce_instance(actual_vcpu, ram, family, region)
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
        nodes   = role.get("nodes", 2)
        ram_gb  = role.get("ram_per_node", 16)
        api_key = role.get("_api_key")   # injected by calculate_gcp_pricing
        rtype, base_hourly, from_api = _resolve_memorystore_hourly_api(ram_gb, region, api_key)
        hourly  = round(base_hourly * (mult if not from_api else 1.0), 6)
        monthly = round(hourly * nodes * HOURS_PER_MONTH, 2)
        return {**role, "gcp_instance_type": f"Memorystore Redis ({rtype})",
                "gcp_hourly_usd": hourly,
                "gcp_compute_monthly_usd": monthly,
                "gcp_storage_monthly_usd": 0,
                "gcp_monthly_usd": monthly,
                "from_api": from_api,
                "gcp_note": f"{nodes}× Memorystore Redis{'  ✓ live' if from_api else '  (est.)'}"}

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


def _price_gcp_clickhouse_roles(ch_sizing: dict, region: str, api_key: str | None = None) -> list:
    """
    Price all ClickHouse nodes on GCP.

    DB nodes  → n2-highmem (memory-optimised) + Persistent Disk SSD
                (SSD handles high-throughput part merges in ClickHouse)
    Keeper nodes → n2-standard + Persistent Disk SSD
    """
    if not ch_sizing or not ch_sizing.get("enabled"):
        return []

    mult   = GCP_REGIONS.get(region, {}).get("multiplier", 1.0)
    priced = []

    # ── ClickHouse DB Cluster nodes ──────────────────────────────────────
    db_cluster = ch_sizing.get("db_cluster", {})
    for node in db_cluster.get("nodes", []):
        vcpu    = node["vcpu_per_node"]
        ram     = node["ram_per_node"]
        storage = node["storage_per_node_gb"]

        gce_type, base_hourly, from_api = _resolve_gce_hourly_api(
            vcpu, ram, "memory", region, api_key
        )
        hourly     = round(base_hourly * (mult if not from_api else 1.0), 6)
        compute_mo = hourly * HOURS_PER_MONTH
        # Persistent Disk SSD — handles ClickHouse merges
        storage_mo = storage * (PD_SSD_PER_GB * 730) * mult
        monthly    = round(compute_mo + storage_mo, 2)

        priced.append({
            **node,
            "gcp_instance_type":         gce_type,
            "gcp_hourly_usd":            hourly,
            "gcp_compute_monthly_usd":   round(compute_mo, 2),
            "gcp_storage_monthly_usd":   round(storage_mo, 2),
            "gcp_monthly_usd":           monthly,
            "from_api":                  from_api,
            "gcp_note": (
                f"Shard {node['shard']} / Replica {node['replica']} — "
                f"{gce_type} + {storage:,}GB PD SSD"
            ),
        })

    # ── ClickHouse Keeper Cluster nodes ─────────────────────────────────
    keeper_cluster = ch_sizing.get("keeper_cluster", {})
    for node in keeper_cluster.get("nodes", []):
        vcpu    = node["vcpu_per_node"]
        ram     = node["ram_per_node"]
        storage = node["storage_per_node_gb"]

        gce_type, base_hourly, from_api = _resolve_gce_hourly_api(
            vcpu, ram, "general", region, api_key
        )
        hourly     = round(base_hourly * (mult if not from_api else 1.0), 6)
        compute_mo = hourly * HOURS_PER_MONTH
        storage_mo = storage * (PD_SSD_PER_GB * 730) * mult
        monthly    = round(compute_mo + storage_mo, 2)

        priced.append({
            **node,
            "gcp_instance_type":         gce_type,
            "gcp_hourly_usd":            hourly,
            "gcp_compute_monthly_usd":   round(compute_mo, 2),
            "gcp_storage_monthly_usd":   round(storage_mo, 2),
            "gcp_monthly_usd":           monthly,
            "from_api":                  from_api,
            "gcp_note": (
                f"Keeper Node {node['role_key'].split('_')[-1]} — "
                f"{gce_type} + {storage}GB PD SSD"
            ),
        })

    return priced


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
    api_key  = _init_gcp_api()
    mult     = GCP_REGIONS.get(region, {}).get("multiplier", 1.0)
    data_gb  = metrics.get("data_size_gb", 0)
    priced   = []

    # 1. Worker nodes (GCE)
    for role in distribution.get("worker_nodes", []):
        priced.append(_price_gce_role(role, region, api_key))

    # 2. DB nodes
    for role in distribution.get("db_nodes", []):
        priced.append(_price_gcp_db_role(role, region))

    # 3. Fixed infra — inject api_key into roles that need it (elasticache)
    for role in distribution.get("fixed_roles", []):
        role_copy = {**role, "_api_key": api_key}
        priced.append(_price_gcp_fixed_role(role_copy, region, data_gb))

    # 4. ClickHouse nodes (optional)
    ch_sizing = distribution.get("clickhouse_nodes")
    if ch_sizing and ch_sizing.get("enabled"):
        ch_priced = _price_gcp_clickhouse_roles(ch_sizing, region, api_key)
        priced.extend(ch_priced)
        print(f"[gcp_pricer] Priced {len(ch_priced)} ClickHouse nodes")

    # 5. Cloud Ops (equiv. CloudWatch) — include ClickHouse nodes
    tw = distribution["summary"]["total_worker_nodes"]
    td = distribution["summary"]["total_db_nodes"]
    tc = distribution["summary"].get("total_clickhouse_nodes", 0)
    priced.append(_gcp_cloudops_cost(tw + td + tc, mult))

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
            "from_api":      r.get("from_api", False),   # preserve live-API flag
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
        "warnings":             [] if api_key else ["GCP Billing API not configured (GCP_API_KEY missing) — using hardcoded March-2026 estimates."],
        "from_api":             any(r.get("from_api") for r in priced),
        "assumptions": {
            "region":            region,
            "region_label":      GCP_REGIONS.get(region, {}).get("label", region),
            "hours_per_month":   HOURS_PER_MONTH,
            "deployment":        "On-Demand (Committed Use Discounts not applied)",
            "os":                "Linux",
            "pd_type":           "SSD (compute & SAN/DB)",
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
