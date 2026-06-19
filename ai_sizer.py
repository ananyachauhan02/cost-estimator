"""
ai_sizer.py
─────────────────────────────────────────────────────────────
Computes AI Services infrastructure sizing for three AI types:
  1. Predictive AI  — ML model training + real-time inference
  2. GenAI          — Generative AI / LLM services
  3. Agentic AI     — Multi-agent orchestration (largest footprint)

Constants derived from: MayBank Hardware Sizing - AI.xlsx
  - Agentic AI Prod sheet  (9 worker nodes, 1 TB SSD)
  - Agentic AI UAT sheet   (5 worker nodes, 800 GB SSD)
  - Predictive Prod sheet  (2 worker nodes, 250 GB SSD)
  - Predictive Training    (4 worker nodes, 500 GB SSD)
  - GenAI Prod sheet       (2 worker nodes, 200 GB SSD)
  - GenAI Training sheet   (2 worker nodes, 200 GB SSD)

Environment types supported: prod, uat, training, dr
─────────────────────────────────────────────────────────────
"""

from __future__ import annotations
import math

# ─────────────────────────────────────────────────────────────────────────────
# Hardcoded constants from Maybank template
# Source sheet noted for each value
# ─────────────────────────────────────────────────────────────────────────────

# ── Agentic AI service pod definitions ─────────────────────────────────────
# Source: Agentic AI Prod sheet (rows 5–12)
AGENTIC_SERVICES_PROD = [
    {"name": "Minio",                       "category": "Common",  "cpu_per_pod": 2, "ram_per_pod": 4,  "pods": 4, "storage_gb": 200},
    {"name": "Config-service",              "category": "Common",  "cpu_per_pod": 2, "ram_per_pod": 4,  "pods": 4, "storage_gb": 0},
    {"name": "MCP Server",                  "category": "Common",  "cpu_per_pod": 2, "ram_per_pod": 4,  "pods": 4, "storage_gb": 0},
    {"name": "businessnext-crmmeta",        "category": "Agent",   "cpu_per_pod": 2, "ram_per_pod": 4,  "pods": 4, "storage_gb": 0},
    {"name": "businessnext-runtime",        "category": "Agent",   "cpu_per_pod": 2, "ram_per_pod": 4,  "pods": 4, "storage_gb": 0},
    {"name": "businessnext-sessionmanager", "category": "Agent",   "cpu_per_pod": 2, "ram_per_pod": 4,  "pods": 4, "storage_gb": 0},
    {"name": "Agent Hub",                   "category": "Agent",   "cpu_per_pod": 8, "ram_per_pod": 12, "pods": 8, "storage_gb": 0},
    {"name": "datanext-guardrails-service", "category": "Agent",   "cpu_per_pod": 4, "ram_per_pod": 8,  "pods": 6, "storage_gb": 0},
]

# Source: Agentic AI UAT sheet (rows 5–12) — same services, fewer pods
AGENTIC_SERVICES_UAT = [
    {"name": "Minio",                       "category": "Common",  "cpu_per_pod": 2, "ram_per_pod": 4,  "pods": 4, "storage_gb": 200},
    {"name": "Config-service",              "category": "Common",  "cpu_per_pod": 2, "ram_per_pod": 4,  "pods": 2, "storage_gb": 0},
    {"name": "MCP Server",                  "category": "Common",  "cpu_per_pod": 2, "ram_per_pod": 4,  "pods": 2, "storage_gb": 0},
    {"name": "businessnext-crmmeta",        "category": "Agent",   "cpu_per_pod": 2, "ram_per_pod": 4,  "pods": 2, "storage_gb": 0},
    {"name": "businessnext-runtime",        "category": "Agent",   "cpu_per_pod": 2, "ram_per_pod": 4,  "pods": 2, "storage_gb": 0},
    {"name": "businessnext-sessionmanager", "category": "Agent",   "cpu_per_pod": 2, "ram_per_pod": 4,  "pods": 2, "storage_gb": 0},
    {"name": "Agent Hub",                   "category": "Agent",   "cpu_per_pod": 8, "ram_per_pod": 12, "pods": 3, "storage_gb": 0},
    {"name": "datanext-guardrails-service", "category": "Agent",   "cpu_per_pod": 4, "ram_per_pod": 8,  "pods": 3, "storage_gb": 0},
]

# ── Predictive AI service pod definitions ───────────────────────────────────
# Source: Predictive Prod sheet (rows 5–6) + Predictive Training (rows 5–17)
PREDICTIVE_SERVICES_PROD = [
    {"name": "Minio",        "category": "Common",    "cpu_per_pod": 2, "ram_per_pod": 4,  "pods": 2, "storage_gb": 400},
    {"name": "AI Evaluator", "category": "Predictive","cpu_per_pod": 2, "ram_per_pod": 4,  "pods": 3, "storage_gb": 0},
]

PREDICTIVE_SERVICES_TRAINING = [
    {"name": "Config-service",                      "category": "Data Platform",          "cpu_per_pod": 1, "ram_per_pod": 2,  "pods": 1, "storage_gb": 0},
    {"name": "Dataflowengine",                      "category": "Data Platform",          "cpu_per_pod": 2, "ram_per_pod": 4,  "pods": 1, "storage_gb": 0},
    {"name": "Datastore",                           "category": "Data Platform",          "cpu_per_pod": 1, "ram_per_pod": 2,  "pods": 1, "storage_gb": 0},
    {"name": "Runtime",                             "category": "Data Platform",          "cpu_per_pod": 1, "ram_per_pod": 2,  "pods": 1, "storage_gb": 0},
    {"name": "Scheduler",                           "category": "Data Platform",          "cpu_per_pod": 1, "ram_per_pod": 2,  "pods": 1, "storage_gb": 0},
    {"name": "Apache Spark (Job Manager)",          "category": "Data Platform",          "cpu_per_pod": 1, "ram_per_pod": 2,  "pods": 1, "storage_gb": 0},
    {"name": "Apache Spark (Worker Node)",          "category": "Data Platform",          "cpu_per_pod": 8, "ram_per_pod": 16, "pods": 3, "storage_gb": 0},
    {"name": "Minio",                               "category": "Predictive+DataPlatform","cpu_per_pod": 4, "ram_per_pod": 8,  "pods": 1, "storage_gb": 400},
    {"name": "Hive Meta Store",                     "category": "Data Platform",          "cpu_per_pod": 2, "ram_per_pod": 4,  "pods": 1, "storage_gb": 0},
    {"name": "Trino Master",                        "category": "Data Platform",          "cpu_per_pod": 1, "ram_per_pod": 2,  "pods": 1, "storage_gb": 0},
    {"name": "Trino Worker",                        "category": "Data Platform",          "cpu_per_pod": 4, "ram_per_pod": 8,  "pods": 2, "storage_gb": 0},
    {"name": "AI Trainer",                          "category": "Predictive",             "cpu_per_pod": 8, "ram_per_pod": 16, "pods": 2, "storage_gb": 0},
    {"name": "AI Evaluator",                        "category": "Predictive",             "cpu_per_pod": 2, "ram_per_pod": 4,  "pods": 1, "storage_gb": 0},
]

# ── GenAI service pod definitions ───────────────────────────────────────────
# Source: GenAI Prod sheet (rows 5–7) + GenAI Training (rows 5–7)
GENAI_SERVICES_PROD = [
    {"name": "Minio",          "category": "Common",   "cpu_per_pod": 2, "ram_per_pod": 4, "pods": 2, "storage_gb": 500},
    {"name": "Config-service", "category": "Common",   "cpu_per_pod": 1, "ram_per_pod": 2, "pods": 3, "storage_gb": 0},
    {"name": "Datanext GenAI", "category": "Worknext", "cpu_per_pod": 4, "ram_per_pod": 8, "pods": 4, "storage_gb": 0},
]

GENAI_SERVICES_TRAINING = [
    {"name": "Config-service", "category": "Common",   "cpu_per_pod": 1, "ram_per_pod": 2, "pods": 1, "storage_gb": 0},
    {"name": "Minio",          "category": "Common",   "cpu_per_pod": 2, "ram_per_pod": 4, "pods": 1, "storage_gb": 300},
    {"name": "Datanext GenAI", "category": "WorkNext", "cpu_per_pod": 4, "ram_per_pod": 8, "pods": 2, "storage_gb": 0},
]

# ── Kubernetes cluster node configurations ──────────────────────────────────
# Source: "Kubernetes Cluster Configuration" tables in each sheet
AI_CLUSTER_CONFIGS = {
    # (ai_type, env_type): (worker_nodes, cores_per_node, ram_per_node_gb, storage_per_node_gb)
    # GPU-accelerated worker nodes — P-series (AWS) / A2 highgpu (GCP)
    ("agentic",   "prod"):     {"nodes": 9, "cores_per_node": 16, "ram_per_node": 64,  "storage_gb": 1024, "instance_family": "GPU Compute (P-Series)"},
    ("agentic",   "uat"):      {"nodes": 5, "cores_per_node": 16, "ram_per_node": 64,  "storage_gb": 800,  "instance_family": "GPU Compute (P-Series)"},
    ("agentic",   "training"): {"nodes": 5, "cores_per_node": 16, "ram_per_node": 64,  "storage_gb": 800,  "instance_family": "GPU Compute (P-Series)"},
    ("agentic",   "dr_full"):  {"nodes": 9, "cores_per_node": 16, "ram_per_node": 64,  "storage_gb": 1024, "instance_family": "GPU Compute (P-Series)"},
    ("agentic",   "dr_half"):  {"nodes": 5, "cores_per_node": 16, "ram_per_node": 64,  "storage_gb": 800,  "instance_family": "GPU Compute (P-Series)"},
    ("predictive","prod"):     {"nodes": 2, "cores_per_node":  8, "ram_per_node": 32,  "storage_gb": 250,  "instance_family": "GPU Compute (P-Series)"},
    ("predictive","uat"):      {"nodes": 2, "cores_per_node":  8, "ram_per_node": 32,  "storage_gb": 250,  "instance_family": "GPU Compute (P-Series)"},
    ("predictive","training"): {"nodes": 4, "cores_per_node": 16, "ram_per_node": 64,  "storage_gb": 500,  "instance_family": "GPU Compute (P-Series)"},
    ("predictive","dr_full"):  {"nodes": 2, "cores_per_node":  8, "ram_per_node": 32,  "storage_gb": 250,  "instance_family": "GPU Compute (P-Series)"},
    ("predictive","dr_half"):  {"nodes": 2, "cores_per_node":  8, "ram_per_node": 32,  "storage_gb": 250,  "instance_family": "GPU Compute (P-Series)"},
    ("genai",     "prod"):     {"nodes": 2, "cores_per_node": 16, "ram_per_node": 64,  "storage_gb": 200,  "instance_family": "GPU Compute (P-Series)"},
    ("genai",     "uat"):      {"nodes": 2, "cores_per_node":  8, "ram_per_node": 32,  "storage_gb": 200,  "instance_family": "GPU Compute (P-Series)"},
    ("genai",     "training"): {"nodes": 2, "cores_per_node":  8, "ram_per_node": 32,  "storage_gb": 200,  "instance_family": "GPU Compute (P-Series)"},
    ("genai",     "dr_full"):  {"nodes": 2, "cores_per_node": 16, "ram_per_node": 64,  "storage_gb": 200,  "instance_family": "GPU Compute (P-Series)"},
    ("genai",     "dr_half"):  {"nodes": 2, "cores_per_node":  8, "ram_per_node": 32,  "storage_gb": 200,  "instance_family": "GPU Compute (P-Series)"},
}

# ── Database requirements ────────────────────────────────────────────────────
# Source: "Databases" sections in Agentic AI sheets
# Vector DB (Milvus) — same in UAT and Prod
MILVUS_PODS          = 3
MILVUS_CPU_PER_POD   = 8
MILVUS_RAM_PER_POD   = 16   # GB
MILVUS_STORAGE_GB    = 200
MILVUS_TOTAL_RAM     = MILVUS_PODS * MILVUS_RAM_PER_POD   # 48 GB
MILVUS_TOTAL_CPU     = MILVUS_PODS * MILVUS_CPU_PER_POD   # 24

# CRM Database storage (SQL) — varies by environment
CRM_DB_STORAGE_PROD     = 800   # GB — Agentic AI Prod sheet
CRM_DB_STORAGE_UAT      = 500   # GB — Agentic AI UAT sheet
CRM_DB_STORAGE_TRAINING = 100   # GB — GenAI/Predictive Training sheets (minimal)

# ── Bedrock default ─────────────────────────────────────────────────────────
BEDROCK_MONTHLY_DEFAULT = 3000  # USD/month — user-adjustable

# ── Environment label map ────────────────────────────────────────────────────
ENV_LABELS = {
    "prod":     "Production",
    "uat":      "UAT / Pre-Prod",
    "training": "Training",
    "dr_full":  "DR (100% Compute)",
    "dr_half":  "DR (50% Compute)",
}


# ─────────────────────────────────────────────────────────────────────────────
# Helper: compute pod-level totals for a services list
# ─────────────────────────────────────────────────────────────────────────────

def _service_totals(services: list) -> dict:
    total_cpu = sum(s["cpu_per_pod"] * s["pods"] for s in services)
    total_ram = sum(s["ram_per_pod"] * s["pods"] for s in services)
    total_stor = sum(s.get("storage_gb", 0) for s in services)
    return {
        "total_cpu":     total_cpu,
        "total_ram_gb":  total_ram,
        "total_stor_gb": total_stor,
    }


def _cluster_summary(cfg: dict) -> dict:
    nodes = cfg["nodes"]
    return {
        "worker_nodes":    nodes,
        "cores_per_node":  cfg["cores_per_node"],
        "ram_per_node_gb": cfg["ram_per_node"],
        "storage_gb":      cfg["storage_gb"],
        "instance_family": cfg.get("instance_family", "GPU Compute (P-Series)"),
        "total_cores":     nodes * cfg["cores_per_node"],
        "total_ram_gb":    nodes * cfg["ram_per_node"],
        "total_storage_gb": nodes * cfg["storage_gb"],
    }


# ─────────────────────────────────────────────────────────────────────────────
# Per-AI-type sizing builders
# ─────────────────────────────────────────────────────────────────────────────

def _build_agentic_sizing(env_type: str, include_milvus: bool = True) -> dict:
    """Return Agentic AI sizing dict for one environment."""
    if env_type == "uat":
        services = AGENTIC_SERVICES_UAT
        crm_stor = CRM_DB_STORAGE_UAT
    elif env_type == "training":
        services = AGENTIC_SERVICES_UAT   # Training ~ UAT footprint
        crm_stor = CRM_DB_STORAGE_UAT
    else:
        services = AGENTIC_SERVICES_PROD
        crm_stor = CRM_DB_STORAGE_PROD

    cfg     = AI_CLUSTER_CONFIGS.get(("agentic", env_type), AI_CLUSTER_CONFIGS[("agentic", "prod")])
    cluster = _cluster_summary(cfg)
    svc_tot = _service_totals(services)

    databases = []
    if include_milvus:
        databases.append({
            "name":       "Vector DB (Milvus)",
            "type":       "Vector Database",
            "pods":       MILVUS_PODS,
            "cpu_per_pod": MILVUS_CPU_PER_POD,
            "ram_per_pod": MILVUS_RAM_PER_POD,
            "total_cpu":   MILVUS_TOTAL_CPU,
            "total_ram_gb": MILVUS_TOTAL_RAM,
            "storage_gb":  MILVUS_STORAGE_GB,
            "persistent":  True,
        })
    databases.append({
        "name":       "CRM Database (SQL DB)",
        "type":       "Relational Database",
        "pods":       0,
        "cpu_per_pod": 0,
        "ram_per_pod": 0,
        "total_cpu":   0,
        "total_ram_gb": 0,
        "storage_gb":  crm_stor,
        "persistent":  True,
    })

    return {
        "ai_type":    "agentic",
        "env_type":   env_type,
        "env_label":  ENV_LABELS.get(env_type, env_type),
        "services":   services,
        "cluster":    cluster,
        "databases":  databases,
        "gpu_note":   "AWS p3/p4d (NVIDIA V100/A100) — GPU-accelerated AI inference & training",
        "totals": {
            "total_pods":      sum(s["pods"] for s in services),
            "total_cpu":       svc_tot["total_cpu"],
            "total_ram_gb":    svc_tot["total_ram_gb"],
            "total_stor_gb":   svc_tot["total_stor_gb"],
            "cluster_nodes":   cluster["worker_nodes"],
            "cluster_cpu":     cluster["total_cores"],
            "cluster_ram_gb":  cluster["total_ram_gb"],
            "cluster_stor_gb": cluster["total_storage_gb"],
        },
    }


def _build_predictive_sizing(env_type: str) -> dict:
    """Return Predictive AI sizing dict for one environment."""
    if env_type == "training":
        services = PREDICTIVE_SERVICES_TRAINING
    else:
        services = PREDICTIVE_SERVICES_PROD

    cfg     = AI_CLUSTER_CONFIGS.get(("predictive", env_type), AI_CLUSTER_CONFIGS[("predictive", "prod")])
    cluster = _cluster_summary(cfg)
    svc_tot = _service_totals(services)

    return {
        "ai_type":    "predictive",
        "env_type":   env_type,
        "env_label":  ENV_LABELS.get(env_type, env_type),
        "services":   services,
        "cluster":    cluster,
        "databases":  [],   # Predictive uses Minio (object storage) — no separate DB
        "gpu_note":   "AWS Bedrock (Managed) — no self-hosted GPU",
        "totals": {
            "total_pods":      sum(s["pods"] for s in services),
            "total_cpu":       svc_tot["total_cpu"],
            "total_ram_gb":    svc_tot["total_ram_gb"],
            "total_stor_gb":   svc_tot["total_stor_gb"],
            "cluster_nodes":   cluster["worker_nodes"],
            "cluster_cpu":     cluster["total_cores"],
            "cluster_ram_gb":  cluster["total_ram_gb"],
            "cluster_stor_gb": cluster["total_storage_gb"],
        },
    }


def _build_genai_sizing(env_type: str) -> dict:
    """Return GenAI sizing dict for one environment."""
    if env_type == "training":
        services = GENAI_SERVICES_TRAINING
        crm_stor = CRM_DB_STORAGE_TRAINING
    else:
        services = GENAI_SERVICES_PROD
        crm_stor = CRM_DB_STORAGE_UAT  # 300 GB for prod (from template)

    cfg     = AI_CLUSTER_CONFIGS.get(("genai", env_type), AI_CLUSTER_CONFIGS[("genai", "prod")])
    cluster = _cluster_summary(cfg)
    svc_tot = _service_totals(services)

    databases = [{
        "name":       "CRM Database (SQL DB)",
        "type":       "Relational Database",
        "pods":       0,
        "cpu_per_pod": 0,
        "ram_per_pod": 0,
        "total_cpu":   0,
        "total_ram_gb": 0,
        "storage_gb":  crm_stor,
        "persistent":  True,
    }]

    return {
        "ai_type":    "genai",
        "env_type":   env_type,
        "env_label":  ENV_LABELS.get(env_type, env_type),
        "services":   services,
        "cluster":    cluster,
        "databases":  databases,
        "gpu_note":   "AWS Bedrock (Managed) — no self-hosted GPU",
        "totals": {
            "total_pods":      sum(s["pods"] for s in services),
            "total_cpu":       svc_tot["total_cpu"],
            "total_ram_gb":    svc_tot["total_ram_gb"],
            "total_stor_gb":   svc_tot["total_stor_gb"],
            "cluster_nodes":   cluster["worker_nodes"],
            "cluster_cpu":     cluster["total_cores"],
            "cluster_ram_gb":  cluster["total_ram_gb"],
            "cluster_stor_gb": cluster["total_storage_gb"],
        },
    }


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def compute_ai_sizing(
    include_predictive: bool  = False,
    include_genai:      bool  = False,
    include_agentic:    bool  = False,
    # Per-type environment flags
    predictive_envs:    list  = None,   # e.g. ["prod", "training", "uat", "dr"]
    genai_envs:         list  = None,
    agentic_envs:       list  = None,
    # Bedrock
    bedrock_monthly:    float = BEDROCK_MONTHLY_DEFAULT,
    # DR scale (0.5 = half, 1.0 = full)
    dr_scale:           float = 1.0,
) -> dict:
    """
    Compute AI Services infrastructure sizing.

    Returns:
    {
      "enabled": True,
      "include_predictive": bool,
      "include_genai": bool,
      "include_agentic": bool,
      "bedrock_monthly": float,
      "environments": {
        "predictive": {
          "prod": {...},      # _build_predictive_sizing() result
          "training": {...},
          ...
        },
        "genai": {...},
        "agentic": {...},
      },
      "combined_summary": {
        "total_worker_nodes": int,
        "total_vcpu": int,
        "total_ram_gb": int,
        "total_storage_gb": int,
        "bedrock_monthly": float,
      }
    }
    """
    if not any([include_predictive, include_genai, include_agentic]):
        return {"enabled": False}

    predictive_envs = predictive_envs or ["prod"]
    genai_envs      = genai_envs      or ["prod"]
    agentic_envs    = agentic_envs    or ["prod"]

    # Resolve DR env key
    def _dr_key(scale: float) -> str:
        return "dr_full" if scale >= 1.0 else "dr_half"

    environments = {}

    if include_predictive:
        environments["predictive"] = {}
        for env in predictive_envs:
            env_key = _dr_key(dr_scale) if env == "dr" else env
            environments["predictive"][env] = _build_predictive_sizing(env_key)

    if include_genai:
        environments["genai"] = {}
        for env in genai_envs:
            env_key = _dr_key(dr_scale) if env == "dr" else env
            environments["genai"][env] = _build_genai_sizing(env_key)

    if include_agentic:
        environments["agentic"] = {}
        for env in agentic_envs:
            env_key = _dr_key(dr_scale) if env == "dr" else env
            environments["agentic"][env] = _build_agentic_sizing(env_key)

    # Combined summary across all enabled types × prod environment only
    total_nodes   = 0
    total_vcpu    = 0
    total_ram_gb  = 0
    total_stor_gb = 0

    for ai_type, envs_data in environments.items():
        prod_data = envs_data.get("prod")
        if prod_data:
            t = prod_data["totals"]
            total_nodes   += t["cluster_nodes"]
            total_vcpu    += t["cluster_cpu"]
            total_ram_gb  += t["cluster_ram_gb"]
            total_stor_gb += t["cluster_stor_gb"]

    return {
        "enabled":            True,
        "include_predictive": include_predictive,
        "include_genai":      include_genai,
        "include_agentic":    include_agentic,
        "bedrock_monthly":    bedrock_monthly,
        "environments":       environments,
        "combined_summary": {
            "total_worker_nodes": total_nodes,
            "total_vcpu":         total_vcpu,
            "total_ram_gb":       total_ram_gb,
            "total_storage_gb":   total_stor_gb,
            "bedrock_monthly":    bedrock_monthly,
        },
    }
