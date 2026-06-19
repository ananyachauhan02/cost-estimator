"""
gcp_machine_catalog.py — GCP VM Instance Catalog
=================================================
Predefined GCP machine types with:
  • vCPU, RAM (GB), on-demand hourly price (us-central1)
  • Regional availability flags
  • Smart selection function: best_gce_instance(vcpu, ram_gb, region)

Pricing source: GCP Compute Engine pricing (March 2025)
Regional prices = base × regional multiplier (same as gcp_pricer.GCP_REGIONS)
"""
from __future__ import annotations

# ── Predefined machine specs + us-central1 on-demand hourly price ─────────
# fmt: (vcpu, ram_gb, hourly_usd_us_central1)
_M: dict[str, tuple[int, float, float]] = {

    # ── N2 Standard (4 GB/vCPU) ──────────────────────────────────────────
    "n2-standard-2":   (2,   8,   0.09720),
    "n2-standard-4":   (4,   16,  0.19440),
    "n2-standard-8":   (8,   32,  0.38881),
    "n2-standard-16":  (16,  64,  0.77761),
    "n2-standard-32":  (32,  128, 1.55522),
    "n2-standard-48":  (48,  192, 2.33283),
    "n2-standard-64":  (64,  256, 3.11044),
    "n2-standard-80":  (80,  320, 3.88805),
    "n2-standard-96":  (96,  384, 4.66566),
    "n2-standard-128": (128, 512, 6.22088),

    # ── N2 High-Memory (8 GB/vCPU) ───────────────────────────────────────
    "n2-highmem-2":   (2,   16,  0.13116),
    "n2-highmem-4":   (4,   32,  0.26233),
    "n2-highmem-8":   (8,   64,  0.52466),
    "n2-highmem-16":  (16,  128, 1.04931),
    "n2-highmem-32":  (32,  256, 2.09863),
    "n2-highmem-48":  (48,  384, 3.14794),
    "n2-highmem-64":  (64,  512, 4.19725),
    "n2-highmem-80":  (80,  640, 5.24657),
    "n2-highmem-96":  (96,  768, 6.29588),
    "n2-highmem-128": (128, 864, 7.34520),

    # ── N2 High-CPU (2 GB/vCPU) ──────────────────────────────────────────
    "n2-highcpu-2":   (2,   2,  0.06248),
    "n2-highcpu-4":   (4,   4,  0.12496),
    "n2-highcpu-8":   (8,   8,  0.24992),
    "n2-highcpu-16":  (16,  16, 0.49984),
    "n2-highcpu-32":  (32,  32, 0.99968),
    "n2-highcpu-48":  (48,  48, 1.49952),
    "n2-highcpu-64":  (64,  64, 1.99936),
    "n2-highcpu-80":  (80,  80, 2.49920),
    "n2-highcpu-96":  (96,  96, 2.99904),

    # ── N2D Standard — AMD EPYC (4 GB/vCPU) ─────────────────────────────
    "n2d-standard-2":  (2,  8,   0.08839),
    "n2d-standard-4":  (4,  16,  0.17678),
    "n2d-standard-8":  (8,  32,  0.35356),
    "n2d-standard-16": (16, 64,  0.70712),
    "n2d-standard-32": (32, 128, 1.41424),
    "n2d-standard-48": (48, 192, 2.12136),
    "n2d-standard-64": (64, 256, 2.82848),
    "n2d-standard-96": (96, 384, 4.24272),

    # ── N2D High-Memory — AMD EPYC (8 GB/vCPU) ──────────────────────────
    "n2d-highmem-2":  (2,  16,  0.11688),
    "n2d-highmem-4":  (4,  32,  0.23376),
    "n2d-highmem-8":  (8,  64,  0.46751),
    "n2d-highmem-16": (16, 128, 0.93503),
    "n2d-highmem-32": (32, 256, 1.87006),
    "n2d-highmem-48": (48, 384, 2.80509),
    "n2d-highmem-64": (64, 512, 3.74012),
    "n2d-highmem-96": (96, 768, 5.61018),

    # ── E2 Standard — cost-optimised (4 GB/vCPU) ─────────────────────────
    "e2-standard-2":  (2,  8,   0.06701),
    "e2-standard-4":  (4,  16,  0.13402),
    "e2-standard-8":  (8,  32,  0.26803),
    "e2-standard-16": (16, 64,  0.53606),
    "e2-standard-32": (32, 128, 1.07212),

    # ── E2 High-Memory (8 GB/vCPU) ───────────────────────────────────────
    "e2-highmem-2":  (2,  16,  0.09034),
    "e2-highmem-4":  (4,  32,  0.18068),
    "e2-highmem-8":  (8,  64,  0.36136),
    "e2-highmem-16": (16, 128, 0.72273),

    # ── C2 Compute-Optimised (Intel Cascade Lake) ────────────────────────
    "c2-standard-4":  (4,  16,  0.20991),
    "c2-standard-8":  (8,  32,  0.41983),
    "c2-standard-16": (16, 64,  0.83966),
    "c2-standard-30": (30, 120, 1.57436),
    "c2-standard-60": (60, 240, 3.14872),

    # ── C3 Compute-Optimised (Intel Sapphire Rapids) ─────────────────────
    "c3-standard-4":  (4,  16,  0.21200),
    "c3-standard-8":  (8,  32,  0.42400),
    "c3-standard-22": (22, 88,  1.16600),
    "c3-standard-44": (44, 176, 2.33200),
    "c3-standard-88": (88, 352, 4.66400),

    # ── M1 Memory-Mega (28 GB/vCPU) ──────────────────────────────────────
    "m1-megamem-96":   (96,  1433.6, 10.67400),
    "m1-ultramem-40":  (40,  961,    6.30300),
    "m1-ultramem-80":  (80,  1922,   12.60600),
    "m1-ultramem-160": (160, 3844,   25.21200),

    # ── M2 (ultra-high memory) ────────────────────────────────────────────
    "m2-ultramem-208": (208, 5888,   41.77200),
    "m2-megamem-416":  (416, 5888,   83.54400),

    # ── M3 (Intel Sapphire Rapids memory-optimised) ──────────────────────
    "m3-ultramem-32":  (32,  976,    5.07360),
    "m3-ultramem-64":  (64,  1952,   10.14720),
    "m3-ultramem-128": (128, 3904,   20.29440),
    "m3-megamem-64":   (64,  976,    4.77120),
    "m3-megamem-128":  (128, 1952,   9.54240),
}

GCP_MACHINE_TYPES: dict[str, dict] = {
    k: {"vcpu": v[0], "ram_gb": v[1], "hourly_base": v[2]}
    for k, v in _M.items()
}

# ── Region availability ───────────────────────────────────────────────────
# True = available, implicit False = not listed (check GCP console for latest)
_REGION_FAMILIES: dict[str, list[str]] = {
    # Americas
    "us-central1":           ["n2", "n2d", "e2", "c2", "c3", "m1", "m2", "m3"],
    "us-east1":              ["n2", "n2d", "e2", "c2", "c3", "m1"],
    "us-east4":              ["n2", "n2d", "e2", "c2", "c3", "m1", "m2"],
    "us-west1":              ["n2", "n2d", "e2", "c2"],
    "us-west2":              ["n2", "n2d", "e2", "c2"],
    "northamerica-northeast1": ["n2", "n2d", "e2", "c2"],
    "southamerica-east1":    ["n2", "n2d", "e2"],
    # Europe
    "europe-west1":          ["n2", "n2d", "e2", "c2", "c3", "m1"],
    "europe-west2":          ["n2", "n2d", "e2", "c2", "m1"],
    "europe-west3":          ["n2", "n2d", "e2", "c2", "m1"],
    "europe-west4":          ["n2", "n2d", "e2", "c2", "c3", "m1", "m2"],
    "europe-west6":          ["n2", "n2d", "e2"],
    "europe-north1":         ["n2", "n2d", "e2"],
    # Asia Pacific
    "asia-south1":           ["n2", "n2d", "e2", "c2"],          # Mumbai
    "asia-south2":           ["n2", "n2d", "e2"],                 # Delhi
    "asia-southeast1":       ["n2", "n2d", "e2", "c2", "c3"],    # Singapore
    "asia-southeast2":       ["n2", "n2d", "e2"],                 # Jakarta
    "asia-east1":            ["n2", "n2d", "e2", "c2"],          # Taiwan
    "asia-east2":            ["n2", "n2d", "e2"],                 # Hong Kong
    "asia-northeast1":       ["n2", "n2d", "e2", "c2"],          # Tokyo
    "asia-northeast2":       ["n2", "n2d", "e2"],                 # Osaka
    "asia-northeast3":       ["n2", "n2d", "e2", "c2"],          # Seoul
    "australia-southeast1":  ["n2", "n2d", "e2", "c2"],
    # Middle East
    "me-west1":              ["n2", "n2d", "e2"],
    "me-central1":           ["n2", "e2"],
}

def region_families(region: str) -> list[str]:
    """Return available machine families for a GCP region."""
    return _REGION_FAMILIES.get(region, ["n2", "e2"])


def best_gce_instance(
    vcpu: int,
    ram_gb: float,
    region: str = "us-central1",
    prefer_amd: bool = False,
) -> dict:
    """
    Find the smallest GCP predefined machine that satisfies (vcpu, ram_gb).

    Selection strategy:
      1. Determine RAM:vCPU ratio → maps to family (highmem / standard / highcpu)
      2. Find the cheapest predefined type where type.vcpu >= vcpu AND type.ram >= ram_gb
      3. Prefer n2d (AMD) when prefer_amd=True and available in region
      4. Fall back to n2-standard if nothing fits exactly

    Returns dict: {type, vcpu, ram_gb, hourly_base, hourly_regional}
    """
    from gcp_pricer import GCP_REGIONS  # avoid circular at module level
    mult = GCP_REGIONS.get(region, {}).get("multiplier", 1.0)
    avail = region_families(region)

    ratio = ram_gb / max(vcpu, 1)

    # Ordered preference list of prefixes to try
    if ratio >= 7:
        prefixes = ["n2-highmem", "n2d-highmem", "e2-highmem"] if not prefer_amd \
                   else ["n2d-highmem", "n2-highmem", "e2-highmem"]
    elif ratio >= 3:
        prefixes = ["n2-standard", "n2d-standard", "e2-standard"] if not prefer_amd \
                   else ["n2d-standard", "n2-standard", "e2-standard"]
    else:
        prefixes = ["n2-highcpu", "n2-standard", "n2d-standard"]

    for prefix in prefixes:
        fam = prefix.split("-")[0]  # "n2", "n2d", "e2", etc.
        if fam not in avail:
            continue
        candidates = [
            (name, specs) for name, specs in GCP_MACHINE_TYPES.items()
            if name.startswith(prefix)
            and specs["vcpu"] >= vcpu
            and specs["ram_gb"] >= ram_gb
        ]
        if candidates:
            name, specs = min(candidates, key=lambda x: x[1]["hourly_base"])
            return {
                "type":            name,
                "vcpu":            specs["vcpu"],
                "ram_gb":          specs["ram_gb"],
                "hourly_base":     specs["hourly_base"],
                "hourly_regional": round(specs["hourly_base"] * mult, 6),
            }

    # Hard fallback: n2-standard-2 (smallest)
    specs = GCP_MACHINE_TYPES["n2-standard-2"]
    return {
        "type":            "n2-standard-2",
        "vcpu":            specs["vcpu"],
        "ram_gb":          specs["ram_gb"],
        "hourly_base":     specs["hourly_base"],
        "hourly_regional": round(specs["hourly_base"] * mult, 6),
    }
