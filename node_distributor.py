"""
node_distributor.py
─────────────────────────────────────────────────────────────
Responsible for:
  - Taking sizing metrics (total nodes, vCPUs, RAM etc.)
  - Running rule-based baseline distribution
  - Optionally calling Claude API to adjust for workload type
  - Returning structured node distribution used by aws_pricer.py

Reference architecture derived from Cloud-sizing-AWS-pgsql-SAAS.xlsx
audit on 2026-03-10.
─────────────────────────────────────────────────────────────
"""

from __future__ import annotations

import hashlib
import json
import os


# ── In-process cache: same inputs → same output, no LLM call ─────────────
# Key = SHA256 of (metrics + workload_profile relevant fields)
# Value = (worker_nodes list, confidence str, notes str)
_DISTRIBUTION_CACHE: dict = {}


def _cache_key(metrics: dict, workload_profile: dict) -> str:
    """Build a stable hash from the inputs that actually affect node counts."""
    relevant = {
        "total_workernodes":      metrics.get("total_workernodes"),
        "total_vcpus_workernode": metrics.get("total_vcpus_workernode"),
        "total_memory_workernode_gb": metrics.get("total_memory_workernode_gb"),
        "mobile_users":           metrics.get("mobile_users"),
        "data_size_gb":           metrics.get("data_size_gb"),
        "workload_type":          workload_profile.get("workload_type"),
        "peak_load":              workload_profile.get("peak_load"),
        "mobile_heavy":           workload_profile.get("mobile_heavy"),
        "reporting_db":           workload_profile.get("reporting_db"),
        "high_compliance":        workload_profile.get("high_compliance"),
    }
    blob = json.dumps(relevant, sort_keys=True)
    return hashlib.sha256(blob.encode()).hexdigest()


# ── Scalable worker role definitions ──────────────────────────────────────
ROLE_DEFINITIONS = {
    "web_mobile_webapi": {
        "label":               "Worker Nodes Linux/RHEL (Web, Mobile, WebAPI)",
        "category":            "Kubernetes Cluster",
        "vcpu_per_node":       16,
        "ram_per_node":        32,
        "storage_per_node_gb": 256,
        "instance_family":     "Compute Intensive",
        "pricing_model":       "Reserved 3 Yr",
        "base_ratio":          0.45,
        "min_nodes":           2,
    },
    "graphana_prometheus": {
        "label":               "Worker Nodes Linux/RHEL for Graphana & Prometheus",
        "category":            "Kubernetes Cluster",
        "vcpu_per_node":       8,
        "ram_per_node":        16,
        "storage_per_node_gb": 512,
        "instance_family":     "Compute Intensive",
        "pricing_model":       "Reserved 3 Yr",
        "base_ratio":          0.22,
        "min_nodes":           1,
        "optional":            True,
    },
    "efk_logging": {
        "label":               "Worker Nodes Linux/RHEL for EFK - optional",
        "category":            "Kubernetes Cluster",
        "vcpu_per_node":       8,
        "ram_per_node":        16,
        "storage_per_node_gb": 1024,
        "instance_family":     "Compute Intensive",
        "pricing_model":       "Reserved 3 Yr",
        "base_ratio":          0.22,
        "min_nodes":           1,
        "optional":            True,
    },
}

# ── Fixed infrastructure roles (always present, not scaled) ───────────────
FIXED_ROLES = [
    {
        "role_key": "k8s_managed", "label": "Cloud Managed K8s",
        "category": "Kubernetes Cluster", "nodes": 1,
        "vcpu_per_node": 0, "ram_per_node": 0, "storage_per_node_gb": 0,
        "instance_family": "K8s Service", "pricing_model": None,
        "reasoning": "Managed control plane — always 1",
    },
    {
        "role_key": "elasticache", "label": "Elasticache Service",
        "category": "Caching & Session", "nodes": 2,
        "vcpu_per_node": 4, "ram_per_node": 16, "storage_per_node_gb": 0,
        "instance_family": "Memory Optimized", "pricing_model": "Reserved 3 Yr",
        "reasoning": "Standard 2-node cache cluster",
    },
    {
        "role_key": "alb", "label": "Load Balancer (Internal + External)",
        "category": "Infrastructure & Monitoring", "nodes": 2,
        "vcpu_per_node": 0, "ram_per_node": 0, "storage_per_node_gb": 0,
        "instance_family": "ALB", "pricing_model": "On Demand",
        "reasoning": "1 internal + 1 external ALB",
    },
    {
        "role_key": "bastion", "label": "Bastion Host",
        "category": "Infrastructure & Monitoring", "nodes": 1,
        "vcpu_per_node": 2, "ram_per_node": 4, "storage_per_node_gb": 300,
        "instance_family": "General Purpose", "pricing_model": "Reserved 3 Yr",
        "reasoning": "Single bastion for SSH access",
    },
    {
        "role_key": "nat", "label": "NAT Gateway",
        "category": "Infrastructure & Monitoring", "nodes": 2,
        "vcpu_per_node": 0, "ram_per_node": 0, "storage_per_node_gb": 0,
        "instance_family": "NAT", "pricing_model": "On Demand",
        "reasoning": "One per AZ for HA",
    },
    {
        "role_key": "ecr", "label": "Image Registry (ECR)",
        "category": "Infrastructure & Monitoring", "nodes": 1,
        "vcpu_per_node": 0, "ram_per_node": 0, "storage_per_node_gb": 512,
        "instance_family": "Managed Service", "pricing_model": "On Demand",
        "reasoning": "Container image storage",
    },
    {
        "role_key": "backup", "label": "Back Up - DB & Infra Logs",
        "category": "Infrastructure & Monitoring", "nodes": 1,
        "vcpu_per_node": 0, "ram_per_node": 0, "storage_per_node_gb": 5120,
        "instance_family": "Cloud Storage Service", "pricing_model": "On Demand",
        "reasoning": "As per bank backup policy",
    },
]


def _rule_based_distribution(metrics: dict, workload_profile: dict | None = None) -> list:
    wp           = workload_profile or {}
    total_nodes  = int(metrics.get("total_workernodes", 9))
    mobile_users = metrics.get("mobile_users", 0)
    mobile_heavy = wp.get("mobile_heavy", False)
    boost        = 1 if (mobile_heavy or mobile_users > 3000) else 0

    roles     = []
    allocated = 0

    for role_key, role in ROLE_DEFINITIONS.items():
        if role_key == "web_mobile_webapi":
            count = max(role["min_nodes"], round(total_nodes * role["base_ratio"]) + boost)
        else:
            count = max(role["min_nodes"], round(total_nodes * role["base_ratio"]))
        allocated += count
        roles.append({
            "role_key":            role_key,
            "label":               role["label"],
            "category":            role["category"],
            "nodes":               count,
            "vcpu_per_node":       role["vcpu_per_node"],
            "ram_per_node":        role["ram_per_node"],
            "storage_per_node_gb": role["storage_per_node_gb"],
            "instance_family":     role["instance_family"],
            "pricing_model":       role["pricing_model"],
            "reasoning":           f"Rule-based: {role['base_ratio']*100:.0f}% of {total_nodes} nodes",
        })

    # Fix rounding drift on web tier
    drift = total_nodes - allocated
    if roles and drift != 0:
        roles[0]["nodes"] = max(1, roles[0]["nodes"] + drift)
        roles[0]["reasoning"] += f" (±{abs(drift)} rounding fix)"

    return roles


def _llm_adjust(baseline: list, metrics: dict, workload_profile: dict) -> tuple:
    """Returns (adjusted_list, confidence, notes).
    Uses Groq API — OpenAI-compatible, very generous free tier (~14,400 req/day).
    pip install groq
    Falls back to baseline on any error.
    """
    import time
    try:
        from groq import Groq
    except ImportError:
        print("[node_distributor] groq not installed. Run: pip install groq")
        return baseline, "rule-based (groq not installed)", "package missing"

    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    total_nodes = int(metrics.get("total_workernodes", 9))

    # Groq free-tier models ordered by capability + quota
    # llama-3.3-70b-versatile : 1000 req/day, best reasoning
    # llama-3.1-8b-instant     : 14400 req/day, fast + sufficient for JSON tasks
    # gemma2-9b-it             : 14400 req/day, good JSON compliance
    MODELS_TO_TRY = [
        "llama-3.3-70b-versatile",
        "llama-3.1-8b-instant",
        "gemma2-9b-it",
    ]

    prompt = f"""You are a senior AWS cloud architect for banking CRM deployments.

SIZING METRICS:
{json.dumps(metrics, indent=2)}

WORKLOAD PROFILE:
{json.dumps(workload_profile, indent=2)}

RULE-BASED BASELINE:
{json.dumps(baseline, indent=2)}

RULES:
1. Total nodes across all scalable roles MUST equal exactly {total_nodes}
2. Web/Mobile/WebAPI always gets the largest share (minimum 2 nodes)
3. If mobile_users > 5000: add 1 to web tier, reduce graphana by 1 (if graphana >= 2)
4. If high_compliance is true: keep both Graphana AND EFK regardless
5. If reporting_db is false: reduce or remove EFK if nodes are tight
6. Per-node specs must match instance_family (Compute Intensive = 16vCPU/32GB RAM)
7. Return ONLY raw JSON — no markdown, no explanation, no code fences

OUTPUT FORMAT:
{{
  "distribution": [
    {{
      "role_key": "web_mobile_webapi",
      "label": "Worker Nodes Linux/RHEL (Web, Mobile, WebAPI)",
      "category": "Kubernetes Cluster",
      "nodes": 5,
      "vcpu_per_node": 16,
      "ram_per_node": 32,
      "storage_per_node_gb": 256,
      "instance_family": "Compute Intensive",
      "pricing_model": "Reserved 3 Yr",
      "reasoning": "Increased by 1 due to high mobile users"
    }}
  ],
  "total_nodes_allocated": {total_nodes},
  "confidence": "high",
  "notes": "summary of changes made"
}}"""

    def _parse_raw(raw: str) -> dict:
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        return json.loads(raw.strip())

    class RateLimited(Exception):
        pass

    def _call_model(model_name: str, max_retries: int = 3) -> dict:
        for attempt in range(max_retries):
            try:
                response = client.chat.completions.create(
                    model=model_name,
                    messages=[
                        {
                            "role": "system",
                            "content": "You are an AWS cloud architect. Always respond with valid raw JSON only. No markdown, no explanation."
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    temperature=0,   # fully deterministic — same inputs always give same result
                    max_tokens=1500,
                )
                raw = response.choices[0].message.content
                return _parse_raw(raw)
            except json.JSONDecodeError as e:
                print(f"[node_distributor] {model_name} bad JSON on attempt {attempt+1}: {e}")
                if attempt == max_retries - 1:
                    raise
            except Exception as e:
                err = str(e)
                is_rate_limit = "429" in err or "rate_limit" in err.lower() or "rate limit" in err.lower()
                is_quota_done = "quota" in err.lower() and "exceeded" in err.lower()

                if is_quota_done:
                    raise Exception(f"quota_exceeded: {err}")
                elif is_rate_limit and attempt < max_retries - 1:
                    wait = (2 ** attempt) * 3   # 3s, 6s, 12s
                    print(f"[node_distributor] Rate limited on {model_name}, waiting {wait}s (attempt {attempt+1})...")
                    time.sleep(wait)
                else:
                    raise

    last_error = ""
    for model_name in MODELS_TO_TRY:
        try:
            print(f"[node_distributor] Trying Groq model: {model_name}")
            parsed = _call_model(model_name)
            print(f"[node_distributor] Success with {model_name}")
            return (
                parsed.get("distribution", baseline),
                parsed.get("confidence", "unknown"),
                parsed.get("notes", ""),
            )
        except Exception as e:
            last_error = str(e)
            print(f"[node_distributor] {model_name} failed: {e}. Trying next...")
            continue

    print("[node_distributor] All Groq models failed. Using rule-based baseline.")
    return baseline, "rule-based (all groq models failed)", last_error


def _db_nodes(metrics: dict, workload_profile: dict | None = None) -> list:
    """
    Build DB/storage node list. Respects workload_profile flags:
      reporting_db    (bool) -> Reporting DB server + SAN   [default True]
      high_compliance (bool) -> WAF + CloudTrail audit       [default False]
    """
    wp              = workload_profile or {}
    reporting_db    = wp.get("reporting_db",    True)
    high_compliance = wp.get("high_compliance", False)
    data_gb = int(metrics.get("data_size_gb", 2100))
    s3_gb  = int(metrics.get("s3_size_gb",  5900))

    nodes = [
        {
            "role_key": "pgsql_primary", "category": "PGSQL Database",
            "label": "Linux Nodes – Database server (Primary)",
            "nodes": 2, "vcpu_per_node": 32, "ram_per_node": 128,
            "storage_per_node_gb": 300, "instance_family": "Memory Intensive",
            "pricing_model": None,
            "reasoning": "2 primary DB nodes per HA reference architecture",
        },
        {
            "role_key": "pgsql_cluster", "category": "PGSQL Database",
            "label": "Linux Nodes – Cluster (etcd+haproxy, pgbackrest)",
            "nodes": 4, "vcpu_per_node": 2, "ram_per_node": 8,
            "storage_per_node_gb": 100, "instance_family": "Memory Intensive",
            "pricing_model": None,
            "reasoning": "Fixed 4-node coordination cluster",
        },
        {
            "role_key": "pgsql_san", "category": "PGSQL Database",
            "label": "Storage: SAN (Primary DB)",
            "nodes": 2, "vcpu_per_node": 0, "ram_per_node": 0,
            "storage_per_node_gb": data_gb, "instance_family": "10K IOPS",
            "pricing_model": None,
            "reasoning": f"SAN = data_size_gb ({data_gb} GB)",
        },
        {
            "role_key": "s3", "category": "S3",
            "label": "S3 Storage + Replication",
            "nodes": 1, "vcpu_per_node": 0, "ram_per_node": 0,
            "storage_per_node_gb": s3_gb, "instance_family": "Cloud Storage Service",
            "pricing_model": "On Demand",
            "reasoning": f"S3 = s3_size_gb ({s3_gb} GB)",
        },
    ]

    # Reporting DB: ONLY included when checkbox is checked
    if reporting_db:
        nodes += [
            {
                "role_key": "pgsql_reporting", "category": "PGSQL Database – Reporting",
                "label": "Linux Nodes – Database server (Reporting)",
                "nodes": 1, "vcpu_per_node": 32, "ram_per_node": 128,
                "storage_per_node_gb": 300, "instance_family": "Memory Intensive",
                "pricing_model": None,
                "reasoning": "Reporting DB server – user opted in",
            },
            {
                "role_key": "pgsql_reporting_san", "category": "PGSQL Database – Reporting",
                "label": "Storage: SAN (Reporting DB)",
                "nodes": 1, "vcpu_per_node": 0, "ram_per_node": 0,
                "storage_per_node_gb": data_gb, "instance_family": "10K IOPS",
                "pricing_model": None,
                "reasoning": "Reporting SAN – user opted in",
            },
        ]

    # High Compliance: WAF + CloudTrail ONLY when checkbox is checked
    if high_compliance:
        nodes += [
            {
                "role_key": "waf_shield", "category": "Security & Compliance",
                "label": "WAF + AWS Shield Advanced",
                "nodes": 1, "vcpu_per_node": 0, "ram_per_node": 0,
                "storage_per_node_gb": 0, "instance_family": "Managed Service",
                "pricing_model": "On Demand",
                "reasoning": "High compliance / audit – user opted in",
            },
            {
                "role_key": "cloudtrail_audit", "category": "Security & Compliance",
                "label": "CloudTrail + Config Audit Logs",
                "nodes": 1, "vcpu_per_node": 0, "ram_per_node": 0,
                "storage_per_node_gb": 0, "instance_family": "Managed Service",
                "pricing_model": "On Demand",
                "reasoning": "High compliance / audit – user opted in",
            },
        ]

    return nodes

# ── Public API ────────────────────────────────────────────────────────────

def distribute_nodes(
    metrics:          dict,
    workload_profile: dict,
    use_llm:          bool = True,
) -> dict:
    """
    Main entry point called by app pages.

    workload_profile example:
    {
        "workload_type":   "banking_crm",   # banking_crm | retail | sme
        "peak_load":       "high",          # normal | high | very_high
        "mobile_heavy":    True,
        "reporting_db":    True,
        "high_compliance": True,
        "notes":           "Heavy mobile, compliance logging required"
    }

    Returns dict with keys:
        worker_nodes, db_nodes, fixed_roles, summary
    """
    baseline = _rule_based_distribution(metrics, workload_profile)
    baseline_repr = ", ".join(r["role_key"] + "=" + str(r["nodes"]) for r in baseline)
    print(f"[node_distributor] Baseline: [{baseline_repr}]")

    llm_used   = False
    confidence = "rule-based"
    notes      = ""

    cache_key = _cache_key(metrics, workload_profile)

    if use_llm and os.getenv("GROQ_API_KEY"):
        if cache_key in _DISTRIBUTION_CACHE:
            worker_nodes, confidence, notes = _DISTRIBUTION_CACHE[cache_key]
            llm_used   = True
            confidence = confidence + " (cached)"
            print(f"[node_distributor] Cache hit — skipping LLM call.")
        else:
            worker_nodes, confidence, notes = _llm_adjust(baseline, metrics, workload_profile)
            _DISTRIBUTION_CACHE[cache_key] = (worker_nodes, confidence, notes)
            llm_used = True
            print(f"[node_distributor] LLM done. confidence={confidence}. Cached for future calls.")
    else:
        worker_nodes = baseline
        if use_llm:
            notes = "LLM skipped: GROQ_API_KEY not set in .env"

    return {
        "worker_nodes": worker_nodes,
        "db_nodes":     _db_nodes(metrics, workload_profile),
        "fixed_roles":  FIXED_ROLES,
        "summary": {
            "total_worker_nodes": sum(r["nodes"] for r in worker_nodes),
            "total_db_nodes":     sum(r["nodes"] for r in _db_nodes(metrics, workload_profile)),
            "llm_used":           llm_used,
            "confidence":         confidence,
            "notes":              notes,
            "workload_profile":   workload_profile,
        },
    }