"""
onprem_sizer.py — On-Premise Infrastructure Sizing Engine
==========================================================
Cloud-aware, database-aware sizing for On-Premise clients.

Scope: SIZING ONLY. No pricing/cost figures are produced anywhere in this
module — on-prem clients receive infrastructure sizing (node counts, vCPU,
RAM, storage) and nothing else, per product requirement.

Supported clouds:        AWS, GCP, Kubeadm, OpenShift
Supported databases:     PostgreSQL, SQL Server, Oracle

DB hosting model per cloud:
  AWS        → Self-hosted on EC2. SQL Server = BYOL + AWS-owned Enterprise
               license, AMD EPYC preferred (cost-effective for BYOL), falls
               back to best available family if AMD is not offered in the
               selected region. Oracle = self-hosted, AMD-first. PostgreSQL =
               self-hosted, Patroni HA (same architecture as SaaS).
  GCP        → Managed-equivalent (Cloud SQL for PostgreSQL/SQL Server,
               Oracle via Bare Metal Solution / self-managed Compute Engine
               equivalent sizing). AMD EPYC (N2D) preferred when available.
               Sizing shown as a managed-tier label + underlying vCPU/RAM so
               the result reads like a real Cloud SQL instance class.
  Kubeadm    → Self-hosted on generic on-prem VM/bare-metal equivalent nodes.
               Cloud-agnostic vCPU/RAM/storage sizing (no specific instance
               catalog — customer brings their own hardware).
  OpenShift  → Same as Kubeadm; OpenShift-flavoured cluster role labels.

This module does NOT replace node_distributor.py's worker-node distribution
(web/app tier sizing stays cloud-agnostic and is reused as-is). It only
supplies the DB/storage sizing layer, cloud-aware, for on-prem estimates.
"""
from __future__ import annotations

import math
from typing import Optional

# ── Reuse existing AMD-aware machine catalogs (read-only imports) ──────────
from aws_machine_catalog import best_ec2_instance, region_families as aws_region_families
from gcp_machine_catalog import best_gce_instance, region_families as gcp_region_families

DB_HEADROOM = 1.5          # DB engines need buffer pool + OS cache headroom
PRIMARY_NODES = 2          # Primary + standby/replica, all DBs, all clouds

# AMD-first family preference (mirrors aws_pricer._ec2_sql_server_byol intent,
# extended to all three DB types — AMD EPYC is the most cost-effective choice
# for self-hosted, license-heavy workloads).
_AWS_MEMORY_FAMILIES_AMD_FIRST = ["r6a", "r6i", "r5"]
_AWS_GENERAL_FAMILIES_AMD_FIRST = ["m6a", "m6i", "m5"]


# ── Per-DB RAM extraction (mirrors node_distributor._db_nodes) ─────────────

def _total_db_ram(metrics: dict, db_type: str) -> float:
    if db_type == "Oracle":
        return float(metrics.get("oracle_ram_gb", 0) or 0)
    if db_type == "SQL Server":
        return float(metrics.get("sql_server_ram_gb", 0) or 0)
    return float(metrics.get("postgres_ram_gb", 0) or 0)


def _snap_to_memory_tier(ram_per_node: float) -> tuple[int, int]:
    """Snap to the nearest standard memory-optimised tier (vcpu, ram_gb)."""
    tiers = [(8, 32), (16, 64), (32, 128), (48, 192), (64, 256), (96, 384)]
    for vcpu, ram in tiers:
        if ram_per_node <= ram:
            return vcpu, ram
    return tiers[-1]


def _db_compute_shape(metrics: dict, db_type: str) -> dict:
    """
    Compute the raw vCPU/RAM requirement per primary DB node, before any
    cloud-specific instance selection. Shared math across all 4 clouds so
    the same workload produces a comparable shape everywhere.
    """
    total_ram = _total_db_ram(metrics, db_type)
    raw_ram_per_node = (total_ram / PRIMARY_NODES) if total_ram > 0 else 128
    effective_ram_per_node = raw_ram_per_node * DB_HEADROOM
    vcpu, ram = _snap_to_memory_tier(effective_ram_per_node)
    return {
        "total_db_ram_gb":   round(total_ram, 1),
        "raw_ram_per_node":  round(raw_ram_per_node, 1),
        "vcpu_per_node":     vcpu,
        "ram_per_node":      ram,
        "primary_nodes":     PRIMARY_NODES,
    }


# ── DB role labels (per db_type) ────────────────────────────────────────────

def _db_labels(db_type: str) -> dict:
    if db_type == "Oracle":
        return {
            "category":     "Oracle Database",
            "primary":      "Database Server (Primary) — Oracle",
            "cluster_info": "Active/Active RAC-equivalent",
            "os":           "Linux/RHEL",
        }
    if db_type == "SQL Server":
        return {
            "category":     "SQL Server Database",
            "primary":      "Database Server (Primary) — SQL Server",
            "cluster_info": "Always On Availability Group / AD / Witness",
            "os":           "Windows Server",
        }
    return {
        "category":     "PostgreSQL Database",
        "primary":      "Database Server (Primary) — PostgreSQL",
        "cluster_info": "etcd + HAProxy + Patroni, pgBackRest",
        "os":           "Linux/RHEL",
    }


# ── AWS: self-hosted EC2, AMD-first, BYOL for SQL Server/Oracle ────────────

def size_db_aws(metrics: dict, db_type: str, region: str = "ap-south-1") -> dict:
    """
    AWS on-prem DB sizing: always self-hosted on EC2.
      - SQL Server: BYOL + AWS-owned Enterprise license. AMD EPYC (r6a)
        preferred for cost-effective BYOL; falls back automatically to the
        best available family if AMD is not offered in the region.
      - Oracle: self-hosted, AMD-first, same fallback behaviour.
      - PostgreSQL: self-hosted, Patroni HA — identical architecture to the
        SaaS deployment model, just costed/labelled for on-prem.
    """
    shape  = _db_compute_shape(metrics, db_type)
    labels = _db_labels(db_type)
    vcpu, ram = shape["vcpu_per_node"], shape["ram_per_node"]

    instance = best_ec2_instance(
        vcpu=vcpu, ram_gb=ram, region=region,
        prefer_families=_AWS_MEMORY_FAMILIES_AMD_FIRST,
    )
    amd_available = "r6a" in aws_region_families(region) or "m6a" in aws_region_families(region)
    used_amd = instance["family"].endswith("a")  # r6a / m6a

    licensing = None
    if db_type == "SQL Server":
        licensing = "BYOL — AWS-owned Microsoft Enterprise license (customer license, AWS-hosted infra)"
    elif db_type == "Oracle":
        licensing = "BYOL — customer-provided Oracle license"
    else:
        licensing = "Open-source — no licensing cost"

    return {
        "cloud":              "AWS",
        "db_type":             db_type,
        "hosting_model":       "Self-Hosted (EC2)",
        "licensing":           licensing,
        "category":            labels["category"],
        "primary_label":       labels["primary"],
        "cluster_info":        labels["cluster_info"],
        "os":                  labels["os"],
        "region":              region,
        "primary_nodes":       shape["primary_nodes"],
        "vcpu_per_node":       instance["vcpu"],
        "ram_per_node_gb":     instance["ram_gb"],
        "instance_type":       instance["type"],
        "instance_family":     instance["family"],
        "amd_preferred":       True,
        "amd_available_in_region": amd_available,
        "amd_selected":        used_amd,
        "selection_note": (
            f"AMD EPYC ({instance['type']}) selected — available in {region}."
            if used_amd else
            f"AMD EPYC not available in {region}; best equivalent alternative selected: {instance['type']} ({instance['family']} family)."
        ),
        "total_db_ram_gb_requested": shape["total_db_ram_gb"],
    }


# ── GCP: managed-equivalent (Cloud SQL), AMD-first (N2D) ───────────────────

def _cloud_sql_tier_label(vcpu: int, ram_gb: float, db_type: str) -> str:
    """Build a Cloud-SQL-style custom tier label, e.g. db-custom-32-131072 (MB)."""
    ram_mb = int(ram_gb * 1024)
    if db_type == "Oracle":
        # GCP has no native managed Oracle; Bare Metal Solution / equivalent sizing shown.
        return f"oracle-bms-equiv-{vcpu}vcpu-{int(ram_gb)}gb"
    return f"db-custom-{vcpu}-{ram_mb}"


def size_db_gcp(metrics: dict, db_type: str, region: str = "asia-south1") -> dict:
    """
    GCP on-prem DB sizing: managed-equivalent service.
      - PostgreSQL / SQL Server → Cloud SQL custom machine tier.
      - Oracle → no native GCP managed Oracle; sized as the Bare Metal
        Solution / self-managed Compute Engine equivalent (closest GCP
        analogue), clearly labelled as such.
    AMD EPYC (N2D) preferred when available in the region; falls back
    automatically to N2/E2 otherwise.
    """
    shape  = _db_compute_shape(metrics, db_type)
    labels = _db_labels(db_type)
    vcpu, ram = shape["vcpu_per_node"], shape["ram_per_node"]

    instance = best_gce_instance(vcpu=vcpu, ram_gb=ram, region=region, prefer_amd=True)
    avail = gcp_region_families(region)
    amd_available = "n2d" in avail
    used_amd = instance["type"].startswith("n2d")

    is_managed = db_type in ("PostgreSQL", "SQL Server")
    hosting_model = "Managed (Cloud SQL)" if is_managed else "Managed-Equivalent (Bare Metal Solution)"
    licensing = (
        "Included in Cloud SQL managed service" if db_type == "SQL Server" else
        "Customer-provided (Bare Metal Solution licensing)" if db_type == "Oracle" else
        "Open-source — no licensing cost"
    )

    return {
        "cloud":               "GCP",
        "db_type":             db_type,
        "hosting_model":       hosting_model,
        "licensing":           licensing,
        "category":            labels["category"],
        "primary_label":       labels["primary"],
        "cluster_info":        "Cloud SQL HA (regional)" if is_managed else labels["cluster_info"],
        "os":                  "Managed by GCP" if is_managed else labels["os"],
        "region":              region,
        "primary_nodes":       shape["primary_nodes"],
        "vcpu_per_node":       instance["vcpu"],
        "ram_per_node_gb":     instance["ram_gb"],
        "instance_type":       instance["type"],
        "managed_tier_label":  _cloud_sql_tier_label(instance["vcpu"], instance["ram_gb"], db_type),
        "amd_preferred":       True,
        "amd_available_in_region": amd_available,
        "amd_selected":        used_amd,
        "selection_note": (
            f"AMD EPYC ({instance['type']}) selected — available in {region}."
            if used_amd else
            f"AMD EPYC (N2D) not available in {region}; best equivalent alternative selected: {instance['type']}."
        ),
        "total_db_ram_gb_requested": shape["total_db_ram_gb"],
    }


# ── Kubeadm / OpenShift: generic self-hosted VM equivalent sizing ──────────

def size_db_generic(metrics: dict, db_type: str, cluster_name: str = "Kubeadm") -> dict:
    """
    Cloud-agnostic on-prem DB sizing for Kubeadm / OpenShift clusters.
    Customer brings their own hardware — no specific instance catalog is
    applicable, so this returns raw vCPU/RAM/storage requirements snapped
    to standard tiers, with cluster-appropriate role labels.
    """
    shape  = _db_compute_shape(metrics, db_type)
    labels = _db_labels(db_type)

    licensing = (
        "BYOL — customer-provided Microsoft Enterprise license" if db_type == "SQL Server" else
        "BYOL — customer-provided Oracle license" if db_type == "Oracle" else
        "Open-source — no licensing cost"
    )

    return {
        "cloud":               cluster_name,   # "Kubeadm" or "OpenShift"
        "db_type":             db_type,
        "hosting_model":       f"Self-Hosted (on-prem VM/bare-metal — {cluster_name})",
        "licensing":           licensing,
        "category":            labels["category"],
        "primary_label":       labels["primary"],
        "cluster_info":        labels["cluster_info"],
        "os":                  labels["os"],
        "region":              "On-Premise Data Center",
        "primary_nodes":       shape["primary_nodes"],
        "vcpu_per_node":       shape["vcpu_per_node"],
        "ram_per_node_gb":     shape["ram_per_node"],
        "instance_type":       f"Generic VM — {shape['vcpu_per_node']} vCPU / {shape['ram_per_node']} GB RAM",
        "amd_preferred":       None,   # not applicable — customer hardware
        "amd_available_in_region": None,
        "amd_selected":        None,
        "selection_note":      "Customer-provided hardware — sized to standard vCPU/RAM tier; no cloud instance catalog applies.",
        "total_db_ram_gb_requested": shape["total_db_ram_gb"],
    }


# ── SAN / S3-equivalent storage sizing (cloud-agnostic, reused everywhere) ──

def size_storage(metrics: dict, db_type: str) -> dict:
    data_gb = int(metrics.get("data_size_gb", 2100))
    s3_gb   = int(metrics.get("s3_size_gb", 5900))
    return {
        "primary_san_gb":   data_gb,
        "reporting_san_gb": data_gb,
        "object_storage_gb": s3_gb,
        "label_primary":   f"Storage: SAN (Primary {db_type} DB)",
        "label_reporting": f"Storage: SAN (Reporting {db_type} DB)",
        "label_object":    "Object Storage (S3-equivalent)",
    }


# ── Public entry point ──────────────────────────────────────────────────────

CLOUD_DB_SIZERS = {
    "aws":       size_db_aws,
    "gcp":       size_db_gcp,
    "kubeadm":   lambda metrics, db_type, region=None: size_db_generic(metrics, db_type, "Kubeadm"),
    "openshift": lambda metrics, db_type, region=None: size_db_generic(metrics, db_type, "OpenShift"),
}


def size_onprem_database(
    metrics:  dict,
    db_type:  str,
    cloud:    str,
    region:   Optional[str] = None,
) -> dict:
    """
    Single entry point: route to the correct cloud-aware DB sizing function.

    Args:
        metrics:  Output of excel_handler.extract_metrics() — must contain
                  postgres_ram_gb / sql_server_ram_gb / oracle_ram_gb,
                  data_size_gb, s3_size_gb.
        db_type:  "PostgreSQL" | "SQL Server" | "Oracle"
        cloud:    "aws" | "gcp" | "kubeadm" | "openshift"
        region:   Cloud region (AWS/GCP only; ignored for kubeadm/openshift).

    Returns:
        dict combining DB compute sizing + storage sizing. No cost figures.
    """
    cloud_key = (cloud or "aws").lower()
    sizer = CLOUD_DB_SIZERS.get(cloud_key)
    if sizer is None:
        raise ValueError(f"Unknown on-prem cloud option: {cloud!r}. Expected one of {list(CLOUD_DB_SIZERS)}.")

    if cloud_key == "aws":
        db_result = sizer(metrics, db_type, region or "ap-south-1")
    elif cloud_key == "gcp":
        db_result = sizer(metrics, db_type, region or "asia-south1")
    else:
        db_result = sizer(metrics, db_type)

    storage = size_storage(metrics, db_type)

    return {
        "cloud":   cloud_key,
        "db_type": db_type,
        "db":      db_result,
        "storage": storage,
    }
