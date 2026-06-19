"""
chatbot.py
─────────────────────────────────────────────────────────────
Estimate-aware chatbot powered by Groq (llama-3.3-70b).
Knows the full pricing result, node distribution, and metrics
so it can answer questions like:
  - "Why is compute so expensive?"
  - "What if we add 5000 more users?"
  - "Which service costs the most?"
  - "Can we reduce cost by switching to reserved?"
  - "Re-run with r5.8xlarge for DB nodes"
─────────────────────────────────────────────────────────────
"""

from __future__ import annotations
import json
import re
import os
import streamlit as st
from dotenv import load_dotenv
load_dotenv(override=True)


GROQ_MODELS = ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "gemma2-9b-it"]

# ── Direct key mappings (proposal key → session state widget key) ─────────
# These are mode-independent keys that map 1:1.
_DIRECT_KEY_MAP = {
    # Sizing inputs
    "named_users":      "in_named_users",
    "concurrent_users": "in_concurrent_users",
    "mobile_users":     "in_mobile_users",
    "total_customers":  "in_total_customers",
    "leads":            "in_leads",
    "cases":            "in_cases",
    # Workload profile
    "workload_type":    "in_workload_type",
    "peak_load":        "in_peak_load",
    "mobile_heavy":     "in_mobile_heavy",
    "reporting_db":     "in_reporting_db",
    "high_compliance":  "in_high_compliance",
    "workload_notes":   "in_workload_notes",
    # Database (on-prem only, harmless if set in SaaS)
    "db_type":          "in_db_type",
    # Forecast
    "forecast_years":   "in_forecast_years",
    # One-time costs
    "perf_testing_cost":  "in_perf_testing",
    "migration_cost":     "in_migration_cost",
    "managed_svc_cost":   "in_managed_svc",
}

_PROPOSAL_LABELS = {
    "named_users":      "Named Users (Y1)",
    "concurrent_users": "Concurrent Users (Y1)",
    "mobile_users":     "Mobile Users (Y1)",
    "total_customers":  "Total Customers (Y1)",
    "leads":            "Leads (Y1)",
    "cases":            "Cases (Y1)",
    "workload_type":    "Workload Type",
    "peak_load":        "Peak Load",
    "mobile_heavy":     "Mobile-Heavy Workload",
    "reporting_db":     "Reporting DB Required",
    "high_compliance":  "High Compliance / Audit",
    "workload_notes":   "Workload Notes",
    "db_type":          "Database Type",
    "forecast_years":   "Forecast Years",
    "perf_testing_cost":  "Performance Testing ($)",
    "migration_cost":     "Migration Cost ($)",
    "managed_svc_cost":   "Managed Services ($)",
    "include_preprod":  "Include Pre-Prod",
    "include_sit":      "Include SIT",
    "include_uat":      "Include UAT",
    "include_dr":       "Include DR",
    "dr_scale":         "DR Scale (%)",
    "aws_region":       "AWS Region",
    "gcp_region":       "GCP Region",
    "dr_region":        "DR Region",
    "instance_overrides": "Instance Type Overrides",
    # ClickHouse
    "include_clickhouse":  "Include ClickHouse (OLAP Analytics DB)",
    "ch_data_multiplier":  "ClickHouse Data Multiplier",
}

SYSTEM_PROMPT = """You are an expert infrastructure sizing consultant embedded inside a cost estimation tool for BusinessNext deployments.

You have access to the full estimate context below. Answer questions about infrastructure sizing, node distribution, architecture, and optimisation suggestions. Be specific with numbers. If a user asks about cost reduction, suggest concrete changes to sizing or architecture. Keep responses concise (3-5 sentences max unless a detailed breakdown is asked for).

Always cite specific numbers from the estimate when relevant. If the user asks something not in the estimate, say so clearly.

IMPORTANT — PROPOSING INPUT CHANGES:
If the user asks you to re-run, update, or simulate the estimate with different inputs
(e.g. "re-run with 30000 users", "switch to Oracle", "use r5.8xlarge for DB", "change region to eu-west-1"),
you MUST include a JSON proposal block at the END of your reply, fenced exactly like this:

```proposed_changes
{{
  "named_users": 30000
}}
```

AVAILABLE PROPOSAL KEYS (only include keys that should CHANGE — omit unchanged ones):

Sizing inputs (integers):
  named_users, concurrent_users, mobile_users, total_customers, leads, cases

Workload profile:
  workload_type  — one of: "banking_crm", "retail_crm", "sme_crm", "insurance_crm"
  peak_load      — one of: "normal", "high", "very_high"
  mobile_heavy   — true or false
  reporting_db   — true or false  (not applicable for PostgreSQL)
  high_compliance — true or false
  workload_notes — free-text string (instructions for the node distributor AI)

Database & config:
  db_type        — one of: "PostgreSQL", "SQL Server", "Oracle"  (on-prem only; SaaS is locked to PostgreSQL)
  forecast_years — integer 3–7

ClickHouse (optional OLAP analytics DB, applies to both SaaS and On-Prem):
  include_clickhouse — true or false  (adds a self-hosted ClickHouse cluster)
  ch_data_multiplier — float 1.0–5.0  (analytics data = multiplier × transactional DB size; default 2.0)

Environments (booleans):
  include_preprod, include_sit, include_uat, include_dr — true or false
  dr_scale       — 50 or 100  (percent of production)

Regions (SaaS only):
  aws_region — e.g. "us-east-1", "eu-west-1", "ap-south-1"
  gcp_region — e.g. "us-central1", "europe-west3", "asia-south1"
  dr_region  — e.g. "us-west-2"

One-time costs (SaaS only, integers):
  perf_testing_cost, migration_cost, managed_svc_cost

Instance type overrides (advanced — use to change which EC2 instance type is used):
  instance_overrides — a JSON object mapping role keys to instance type strings.
  Available role keys: "web_mobile_webapi", "graphana_prometheus", "efk_logging",
    "pgsql_primary", "mssql_primary", "oracle_primary", "elasticache", "bastion"
  Available instance types: c6i.*, c6a.*, m5.*, r5.*, r6a.* families
    (e.g. "c6i.4xlarge", "r5.8xlarge", "m5.2xlarge")
  For elasticache: "cache.r6g.large", "cache.r6g.xlarge", "cache.r6g.2xlarge"
  Example: {{"instance_overrides": {{"web_mobile_webapi": "c6i.8xlarge", "pgsql_primary": "r5.8xlarge"}}}}

RULES:
- Only include keys whose values should CHANGE. Omit keys that stay the same.
- All numeric values must be plain integers (no commas, no quotes) except instance type strings.
- Booleans must be JSON true/false (not strings).
- Always explain what you are changing and why BEFORE the JSON block.
- If the user is just asking a question and NOT requesting changes, do NOT include the block.

ESTIMATE CONTEXT:
{context}
"""


def _build_context(pricing: dict | None, distribution: dict, metrics: dict, client_mode: str = "saas", env_pricing: dict | None = None, db_type: str = "PostgreSQL") -> str:
    """Serialize the full estimate into a compact string for the LLM context.
    
    Args:
        pricing: SaaS cloud pricing dict (for SaaS deployments)
        distribution: Node distribution result
        metrics: Sizing metrics
        client_mode: "saas" or "onprem"
        env_pricing: Environment pricing dict (for on-prem deployments)
        db_type: Database type (PostgreSQL, SQL Server, Oracle)
    """
    ctx = {
        "client_mode": client_mode,
        "db_type": db_type,
        "node_distribution": {
            "total_worker_nodes": distribution["summary"]["total_worker_nodes"],
            "total_db_nodes":     distribution["summary"]["total_db_nodes"],
            "llm_confidence":     distribution["summary"]["confidence"],
            "worker_roles": [
                {"role": r["label"], "role_key": r.get("role_key", ""), "nodes": r["nodes"],
                 "vcpu": r["vcpu_per_node"], "ram": r["ram_per_node"],
                 "instance_type": r.get("instance_type", "")}
                for r in distribution.get("worker_nodes", [])
            ],
        },
        "sizing_metrics": {
            "total_workernodes":          metrics.get("total_workernodes"),
            "total_vcpus_workernode":     metrics.get("total_vcpus_workernode"),
            "total_memory_workernode_gb": metrics.get("total_memory_workernode_gb"),
            "postgres_ram_gb":            metrics.get("postgres_ram_gb"),
            "sql_server_ram_gb":          metrics.get("sql_server_ram_gb"),
            "oracle_ram_gb":              metrics.get("oracle_ram_gb"),
            "data_size_gb":               metrics.get("data_size_gb"),
            "s3_size_gb":                 metrics.get("s3_size_gb"),
            "mobile_users":               metrics.get("mobile_users"),
        },
    }

    # Add pricing data based on deployment mode
    if client_mode == "saas" and pricing:
        # SaaS: Use cloud pricing
        ctx.update({
            "monthly_cost_usd":  pricing.get("total_monthly_usd"),
            "annual_cost_usd":   pricing.get("total_annual_usd"),
            "three_year_usd":    pricing.get("total_3year_usd"),
            "category_totals":   pricing.get("category_totals", {}),
            "top_services": [
                {
                    "label":    r.get("label"),
                    "role_key": r.get("role_key", ""),
                    "category": r.get("category"),
                    "monthly":  r.get("monthly_usd"),
                    "instance": r.get("instance_type"),
                    "note":     r.get("note"),
                }
                for r in sorted(
                    pricing.get("priced_roles", []),
                    key=lambda x: x.get("monthly_usd", 0),
                    reverse=True,
                )[:10]
            ],
            "assumptions":        pricing.get("assumptions", {}),
            "inflation_forecast": pricing.get("inflation_forecast", {}),
            "db_selection":       pricing.get("db_selection", {}),
        })
    elif client_mode == "onprem" and env_pricing:
        # On-Prem: Use environment pricing
        ctx.update({
            "deployment_type": "On-Premise Self-Hosted",
            "database_note": env_pricing.get("db_note", ""),
            "deployment_mode": env_pricing.get("deployment", "onprem"),
            "preprod_monthly": env_pricing.get("preprod_sit_uat", {}).get("monthly_usd"),
            "preprod_annual": env_pricing.get("preprod_sit_uat", {}).get("annual_usd"),
            "dr_monthly": env_pricing.get("dr", {}).get("monthly_usd"),
            "dr_annual": env_pricing.get("dr", {}).get("annual_usd"),
            "dr_five_year": env_pricing.get("dr", {}).get("five_year_forecast", {}).get("five_year_total"),
            "combined_monthly": env_pricing.get("combined_monthly"),
            "db_components": [
                {
                    "label": r.get("label"),
                    "category": r.get("category"),
                    "nodes": r.get("nodes"),
                    "instance_type": r.get("instance_type"),
                    "monthly": r.get("monthly_usd"),
                    "note": r.get("note"),
                }
                for r in env_pricing.get("preprod_sit_uat", {}).get("priced_roles", [])
                if "Database" in r.get("category", "") or "database" in r.get("label", "").lower()
            ][:5]
        })
    else:
        ctx["note"] = "Pricing data not available for this estimate."

    # Add ClickHouse context if enabled
    ch_sizing = distribution.get("clickhouse_nodes")
    if ch_sizing and ch_sizing.get("enabled"):
        db_cl  = ch_sizing.get("db_cluster", {})
        kp_cl  = ch_sizing.get("keeper_cluster", {})
        ch_sum = ch_sizing.get("summary", {})
        ctx["clickhouse_cluster"] = {
            "enabled":            True,
            "ch_data_gb":         ch_sizing.get("ch_data_gb"),
            "ch_data_multiplier": ch_sizing.get("ch_data_multiplier"),
            "volume_factor":      ch_sizing.get("volume_factor"),
            "db_cluster": {
                "num_shards":          db_cl.get("num_shards"),
                "replicas_per_shard":  db_cl.get("replicas_per_shard"),
                "total_nodes":         db_cl.get("total_nodes"),
                "vcpu_per_node":       db_cl.get("vcpu_per_node"),
                "ram_per_node":        db_cl.get("ram_per_node"),
                "storage_per_node_gb": db_cl.get("storage_per_node_gb"),
            },
            "keeper_cluster": {
                "total_nodes":   kp_cl.get("total_nodes"),
                "vcpu_per_node": kp_cl.get("vcpu_per_node"),
                "ram_per_node":  kp_cl.get("ram_per_node"),
                "storage_per_node_gb": kp_cl.get("storage_per_node_gb"),
            },
            "summary": ch_sum,
        }
    else:
        ctx["clickhouse_cluster"] = {"enabled": False}

    return json.dumps(ctx, indent=2)


def _call_groq(messages: list, context: str) -> str:
    """Call Groq API with automatic key rotation (GROQ_API_KEY → _2 → _3)."""
    from groq_client import groq_completion, any_key_available

    if not any_key_available():
        return "❌ No Groq API key configured in .env (GROQ_API_KEY / GROQ_API_KEY_2 / GROQ_API_KEY_3)"

    system = SYSTEM_PROMPT.format(context=context)
    full_messages = [{"role": "system", "content": system}] + messages

    try:
        content, model_used, key_used = groq_completion(
            messages=full_messages,
            models=GROQ_MODELS,
            temperature=0.3,
            max_tokens=1200,
        )
        return content
    except RuntimeError as e:
        err = str(e)
        if "looping" in err.lower() or "loop" in err.lower():
            return (
                "⚠️ The AI model flagged this response for repetitive content across all available models. "
                "This can happen when the estimate context is very large or the question triggers a repetitive pattern.\n\n"
                "**Try rephrasing your question** — for example, ask something more specific like:\n"
                "- *\"What is the total monthly cost?\"*\n"
                "- *\"Which service is most expensive?\"*\n"
                "- *\"Re-run with 20000 named users\"*"
            )
        return f"❌ {e}"
    except Exception as e:
        return f"❌ Groq error: {e}"


# ── Proposal parsing helpers ─────────────────────────────────────────────────
_PROPOSAL_RE = re.compile(
    r"```proposed_changes\s*\n(\{.*?\})\s*\n```",
    re.DOTALL,
)


def _extract_proposed_changes(reply: str) -> dict | None:
    """Return the proposed-changes dict if present in the assistant reply, else None."""
    m = _PROPOSAL_RE.search(reply)
    if not m:
        return None
    try:
        return json.loads(m.group(1))
    except (json.JSONDecodeError, ValueError):
        return None


def _display_text_without_proposal(reply: str) -> str:
    """Return the reply with the raw proposal fence removed for display."""
    return _PROPOSAL_RE.sub("", reply).rstrip()


def _apply_changes_and_retrigger(changes: dict):
    """Stage proposed changes and trigger a rerun.

    Streamlit does not allow modifying a widget's session-state key after the
    widget has already been instantiated in the current script run.  Since the
    chatbot renders *after* all input widgets, we cannot write directly.

    Instead we store the raw proposal in ``st.session_state._pending_changes``
    and set the retrigger flag.  The Estimator page applies these changes
    *before* widgets render on the next rerun (see ``apply_pending_changes()``
    in ``3_Estimator.py``).
    """
    st.session_state._pending_changes = changes
    st.session_state.chatbot_retrigger = True
    st.rerun()


def render_chatbot(pricing: dict | None, distribution: dict, metrics: dict, client_mode: str = "saas", env_pricing: dict | None = None, db_type: str = "PostgreSQL"):
    # Session state for chat history
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    if "chat_context" not in st.session_state:
        st.session_state.chat_context = _build_context(pricing, distribution, metrics, client_mode, env_pricing, db_type)

    if not st.session_state.chat_history:
        # Welcome message
        with st.chat_message("assistant", avatar="🤖"):
            st.markdown(
                f"Hello! I am your AI architect. Ask me anything about this **{'On-Premise' if client_mode == 'onprem' else 'SaaS'}** deployment. "
                "You can also instruct me to update inputs (like named users, databases, or regions) and I'll automatically adjust the estimate."
            )
            
            # Show suggestions as small pills
            st.markdown("<br><span style='font-size:12px; color:var(--text3);'>Try asking:</span>", unsafe_allow_html=True)
            suggestions = (
                ["What is the total infrastructure requirement?", "Re-run with double the current users.", "Switch database to Oracle and retrigger."]
                if client_mode == "onprem" else
                ["What is the most expensive service?", "How can we reduce monthly cost by 20%?", "Re-run with 30000 named users."]
            )
            
            cols = st.columns(3)
            for i, suggestion in enumerate(suggestions):
                if cols[i].button(suggestion, key=f"sugg_{i}", use_container_width=True):
                    st.session_state.chat_history.append({"role": "user", "content": suggestion})
                    with st.spinner("Thinking…"):
                        reply = _call_groq(st.session_state.chat_history, st.session_state.chat_context)
                    st.session_state.chat_history.append({"role": "assistant", "content": reply})
                    st.rerun()

    # Display chat history
    for idx, msg in enumerate(st.session_state.chat_history):
        avatar = "🤖" if msg["role"] == "assistant" else "👤"
        with st.chat_message(msg["role"], avatar=avatar):
            if msg["role"] == "assistant":
                proposal = _extract_proposed_changes(msg["content"])
                display_text = _display_text_without_proposal(msg["content"])
                st.markdown(display_text)

                if proposal:
                    st.markdown("---")
                    st.markdown(
                        "<div style='background:var(--bg2); border-left:3px solid var(--accent); padding:10px 14px; border-radius:6px; margin-bottom:8px;'>"
                        "<div style='font-size:12px; font-weight:700; color:var(--accent); margin-bottom:4px;'>📝 Proposed Configuration Update</div>",
                        unsafe_allow_html=True
                    )
                    for prop_key, value in proposal.items():
                        label = _PROPOSAL_LABELS.get(prop_key, prop_key)
                        display_val = json.dumps(value) if isinstance(value, dict) else str(value)
                        st.markdown(f"<div style='font-size:12px;'><strong>{label}:</strong> <code>{display_val}</code></div>", unsafe_allow_html=True)
                    st.markdown("</div>", unsafe_allow_html=True)

                    is_last_proposal = not any(
                        _extract_proposed_changes(m["content"])
                        for m in st.session_state.chat_history[idx + 1:]
                        if m["role"] == "assistant"
                    )
                    if is_last_proposal:
                        if st.button("✅ Approve & Retrigger", key=f"approve_{idx}", type="primary"):
                            _apply_changes_and_retrigger(proposal)
            else:
                st.markdown(msg["content"])

    # Chat input
    if user_input := st.chat_input("Message the AI Architect..."):
        st.session_state.chat_history.append({"role": "user", "content": user_input})
        with st.chat_message("user", avatar="👤"):
            st.markdown(user_input)
        with st.chat_message("assistant", avatar="🤖"):
            with st.spinner("Thinking…"):
                reply = _call_groq(st.session_state.chat_history, st.session_state.chat_context)
                st.markdown(_display_text_without_proposal(reply))
        st.session_state.chat_history.append({"role": "assistant", "content": reply})
        st.rerun()

    # Clear chat option
    if st.session_state.chat_history:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🗑️ Clear Chat History", type="secondary"):
            st.session_state.chat_history = []
            st.session_state.chat_context = _build_context(pricing, distribution, metrics, client_mode, env_pricing, db_type)
            st.rerun()
