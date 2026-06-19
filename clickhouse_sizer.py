"""
clickhouse_sizer.py
─────────────────────────────────────────────────────────────
Responsible for computing ClickHouse cluster sizing:

  1. ClickHouse DB Cluster  — sharded + replicated OLAP nodes
                              (self-hosted, same for SaaS and On-Prem)
  2. ClickHouse Keeper Cluster — 3-node coordination cluster
                              (replaces ZooKeeper; always 3 nodes for HA quorum)

Architecture reference (2 shards × 2 replicas = 4 DB nodes):
  Shard 1: Node 1 + Node 2  → 32 vCPU / 128 GB / 20 TB SSD each
  Shard 2: Node 1 + Node 2  → 32 vCPU / 128 GB / 20 TB SSD each
  Keeper:  Node 1/2/3       →  4 vCPU /  16 GB / 200 GB SSD each

Shard count is driven by a combination of data volume AND customer
volumes (named users, customers, leads, cases) so sizing stays
conservative and does not overshoot for smaller deployments.
─────────────────────────────────────────────────────────────
"""

from __future__ import annotations
import math


# ── Constants matching reference architecture ─────────────────────────────

# Replication factor — fixed at 2 for HA (per-shard: primary + standby)
REPLICATION_FACTOR = 2

# ClickHouse Keeper: always 3 nodes (Raft quorum)
KEEPER_NODES     = 3
KEEPER_VCPU      = 4
KEEPER_RAM_GB    = 16
KEEPER_STORAGE_GB = 200    # 200 GB SSD per keeper node (matches reference image)

# Storage overhead multiplier for ClickHouse data nodes
# Accounts for index files, part merges, compaction, TTL temp files
STORAGE_OVERHEAD = 1.30    # 30% overhead on top of raw data per shard-replica

# Default data multiplier: ClickHouse analytics store vs transactional DB
# Denormalized/aggregated analytics data is typically 1.5–2× the source DB
DEFAULT_CH_DATA_MULTIPLIER = 2.0


# ── Shard sizing tiers ─────────────────────────────────────────────────────
# Each tier: (ch_data_gb_threshold, vcpu_per_node, ram_per_node)
# Following 1:4 vCPU:RAM ratio — industry standard for OLAP workloads
_SHARD_TIERS = [
    (5_000,   8,  32),    # ≤ 5 TB  → small deployment
    (20_000, 32, 128),    # ≤ 20 TB → medium (matches reference image)
    (50_000, 32, 128),    # ≤ 50 TB → large
    (float("inf"), 48, 192),  # > 50 TB → xlarge
]


# ── Customer-volume adjustment ─────────────────────────────────────────────
# Adds an extra data growth factor based on customer activity volumes.
# Keeps sizing conservative — capped at a modest multiplier.

def _volume_factor(metrics: dict) -> float:
    """
    Return a modest data volume multiplier (1.0–1.5) based on customer
    activity signals. Avoids inflating sizing unnecessarily.

    Signals used:
      - total_customers: large customer base → more event rows
      - leads + cases:   high transaction activity → more INSERT throughput
      - mobile_users:    mobile events often logged to analytics
    """
    named_users     = metrics.get("total_named_users",  metrics.get("named_users", 0)) or 0
    total_customers = metrics.get("total_customers", 0) or 0
    leads           = metrics.get("leads", 0) or 0
    cases           = metrics.get("cases", 0) or 0
    mobile_users    = metrics.get("mobile_users", 0) or 0

    # Activity score: normalise to [0, 1] range
    # Thresholds chosen conservatively based on typical banking-CRM deployments
    customer_score = min(total_customers / 50_000_000, 1.0)
    activity_score = min((leads + cases) / 20_000_000, 1.0)
    user_score     = min((named_users + mobile_users) / 100_000, 1.0)

    composite = (customer_score * 0.40 + activity_score * 0.40 + user_score * 0.20)

    # Map composite [0, 1] → multiplier [1.0, 1.5]
    # Conservative cap: never exceeds 1.5× to avoid overprovisioning
    return round(1.0 + composite * 0.5, 2)


def _num_shards(ch_data_gb: float) -> int:
    """
    Determine the number of ClickHouse shards based on analytics data volume.

    Thresholds:
      ≤  5 000 GB  (~ 5 TB) →  1 shard
      ≤ 20 000 GB  (~20 TB) →  2 shards  (reference image scenario)
      ≤ 50 000 GB  (~50 TB) →  3 shards
      >  50 000 GB          →  4 shards
    """
    if ch_data_gb <= 5_000:
        return 1
    elif ch_data_gb <= 20_000:
        return 2
    elif ch_data_gb <= 50_000:
        return 3
    else:
        return 4


def _node_specs(ch_data_gb: float) -> tuple[int, int]:
    """Return (vcpu_per_node, ram_per_node) for the appropriate tier."""
    for threshold, vcpu, ram in _SHARD_TIERS:
        if ch_data_gb <= threshold:
            return vcpu, ram
    return 48, 192    # fallback for extremely large deployments


def _storage_per_node_gb(ch_data_gb: float, num_shards: int) -> int:
    """
    Compute SSD storage per replica node.

    Formula:
        raw_per_shard  = ch_data_gb / num_shards
        with_overhead  = ceil(raw_per_shard × STORAGE_OVERHEAD)
        rounded to nearest 500 GB boundary (clean presentation)
    """
    raw_per_shard   = ch_data_gb / max(num_shards, 1)
    with_overhead   = math.ceil(raw_per_shard * STORAGE_OVERHEAD)
    # Round up to the nearest 500 GB for clean node specs
    rounded         = math.ceil(with_overhead / 500) * 500
    return max(rounded, 500)    # minimum 500 GB


# ── Public API ─────────────────────────────────────────────────────────────

def compute_clickhouse_sizing(
    metrics:             dict,
    ch_data_multiplier:  float = DEFAULT_CH_DATA_MULTIPLIER,
) -> dict:
    """
    Compute ClickHouse DB Cluster + Keeper Cluster sizing from production metrics.

    Args:
        metrics:            Output of excel_handler.extract_metrics() (plus enriched fields)
        ch_data_multiplier: Ratio of CH analytics data to transactional data_size_gb.
                            Default 2.0× (analytics data is typically 2× transactional DB)

    Returns:
        dict with keys:
            enabled          — always True when called
            ch_data_gb       — computed ClickHouse data volume in GB
            db_cluster       — shard/replica layout and per-node specs
            keeper_cluster   — 3-node Keeper specs
            summary          — aggregate totals
    """
    # ── Derive ClickHouse data volume ─────────────────────────────────────
    data_size_gb    = metrics.get("data_size_gb", 2100.0) or 2100.0
    vol_factor      = _volume_factor(metrics)
    ch_data_gb      = round(data_size_gb * ch_data_multiplier * vol_factor, 0)

    # ── DB Cluster sizing ─────────────────────────────────────────────────
    num_shards          = _num_shards(ch_data_gb)
    replicas_per_shard  = REPLICATION_FACTOR   # fixed at 2
    total_db_nodes      = num_shards * replicas_per_shard
    vcpu_per_node, ram_per_node = _node_specs(ch_data_gb)
    storage_per_node_gb = _storage_per_node_gb(ch_data_gb, num_shards)

    # Build individual node list (shard_N, replica_M)
    db_nodes = []
    for shard_idx in range(1, num_shards + 1):
        for replica_idx in range(1, replicas_per_shard + 1):
            db_nodes.append({
                "role_key":            f"ch_db_s{shard_idx}r{replica_idx}",
                "label":               f"ClickHouse DB — Shard {shard_idx}, Node {replica_idx}",
                "category":            "ClickHouse DB Cluster",
                "shard":               shard_idx,
                "replica":             replica_idx,
                "nodes":               1,
                "vcpu_per_node":       vcpu_per_node,
                "ram_per_node":        ram_per_node,
                "storage_per_node_gb": storage_per_node_gb,
                "instance_family":     "Memory Intensive",
                "pricing_model":       "Self-Hosted",
                "reasoning": (
                    f"Shard {shard_idx} / Replica {replica_idx} — "
                    f"derived from {ch_data_gb:,.0f} GB analytics data "
                    f"({num_shards} shards × {replicas_per_shard} replicas)"
                ),
            })

    db_cluster = {
        "num_shards":           num_shards,
        "replicas_per_shard":   replicas_per_shard,
        "total_nodes":          total_db_nodes,
        "vcpu_per_node":        vcpu_per_node,
        "ram_per_node":         ram_per_node,
        "storage_per_node_gb":  storage_per_node_gb,
        "total_vcpu":           total_db_nodes * vcpu_per_node,
        "total_ram_gb":         total_db_nodes * ram_per_node,
        "total_storage_gb":     total_db_nodes * storage_per_node_gb,
        "nodes":                db_nodes,
    }

    # ── Keeper Cluster sizing ─────────────────────────────────────────────
    keeper_nodes = []
    for n in range(1, KEEPER_NODES + 1):
        keeper_nodes.append({
            "role_key":            f"ch_keeper_{n}",
            "label":               f"ClickHouse Keeper — Node {n}",
            "category":            "ClickHouse Keeper Cluster",
            "nodes":               1,
            "vcpu_per_node":       KEEPER_VCPU,
            "ram_per_node":        KEEPER_RAM_GB,
            "storage_per_node_gb": KEEPER_STORAGE_GB,
            "instance_family":     "General Purpose",
            "pricing_model":       "Self-Hosted",
            "reasoning":           "ClickHouse Keeper Raft quorum node (always 3 for HA)",
        })

    keeper_cluster = {
        "total_nodes":          KEEPER_NODES,
        "vcpu_per_node":        KEEPER_VCPU,
        "ram_per_node":         KEEPER_RAM_GB,
        "storage_per_node_gb":  KEEPER_STORAGE_GB,
        "total_vcpu":           KEEPER_NODES * KEEPER_VCPU,
        "total_ram_gb":         KEEPER_NODES * KEEPER_RAM_GB,
        "total_storage_gb":     KEEPER_NODES * KEEPER_STORAGE_GB,
        "nodes":                keeper_nodes,
    }

    # ── Aggregate summary ─────────────────────────────────────────────────
    total_nodes   = total_db_nodes + KEEPER_NODES
    total_vcpu    = db_cluster["total_vcpu"]    + keeper_cluster["total_vcpu"]
    total_ram_gb  = db_cluster["total_ram_gb"]  + keeper_cluster["total_ram_gb"]
    total_stor_gb = db_cluster["total_storage_gb"] + keeper_cluster["total_storage_gb"]

    return {
        "enabled":          True,
        "ch_data_gb":       ch_data_gb,
        "ch_data_multiplier": ch_data_multiplier,
        "volume_factor":    vol_factor,
        "db_cluster":       db_cluster,
        "keeper_cluster":   keeper_cluster,
        "summary": {
            "total_nodes":      total_nodes,
            "total_db_nodes":   total_db_nodes,
            "total_vcpu":       total_vcpu,
            "total_ram_gb":     total_ram_gb,
            "total_storage_gb": total_stor_gb,
            "num_shards":       num_shards,
            "replicas_per_shard": replicas_per_shard,
        },
    }


def all_ch_nodes(ch_sizing: dict) -> list:
    """Return a flat list of all ClickHouse nodes (DB + Keeper) for pricing loops."""
    if not ch_sizing or not ch_sizing.get("enabled"):
        return []
    return (
        ch_sizing["db_cluster"]["nodes"]
        + ch_sizing["keeper_cluster"]["nodes"]
    )
