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
─────────────────────────────────────────────────────────────
"""

from __future__ import annotations
import json
import os
import streamlit as st
from dotenv import load_dotenv
load_dotenv(override=True)


GROQ_MODELS = ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "gemma2-9b-it"]

SYSTEM_PROMPT = """You are an expert infrastructure sizing consultant embedded inside a cost estimation tool for BusinessNext deployments.

You have access to the full estimate context below. Answer questions about infrastructure sizing, node distribution, architecture, and optimisation suggestions. Be specific with numbers. If a user asks about cost reduction, suggest concrete changes to sizing or architecture. Keep responses concise (3-5 sentences max unless a detailed breakdown is asked for).

Always cite specific numbers from the estimate when relevant. If the user asks something not in the estimate, say so clearly.

ESTIMATE CONTEXT:
{context}
"""


def _build_context(pricing: dict | None, distribution: dict, metrics: dict, client_mode: str = "saas") -> str:
    """Serialize the full estimate into a compact string for the LLM context."""
    ctx = {
        "client_mode": client_mode,
        "node_distribution": {
            "total_worker_nodes": distribution["summary"]["total_worker_nodes"],
            "total_db_nodes":     distribution["summary"]["total_db_nodes"],
            "llm_confidence":     distribution["summary"]["confidence"],
            "worker_roles": [
                {"role": r["label"], "nodes": r["nodes"],
                 "vcpu": r["vcpu_per_node"], "ram": r["ram_per_node"]}
                for r in distribution.get("worker_nodes", [])
            ],
        },
        "sizing_metrics": {
            "total_workernodes":          metrics.get("total_workernodes"),
            "total_vcpus_workernode":     metrics.get("total_vcpus_workernode"),
            "total_memory_workernode_gb": metrics.get("total_memory_workernode_gb"),
            "postgres_ram_gb":            metrics.get("postgres_ram_gb"),
            "data_size_gb":               metrics.get("data_size_gb"),
            "s3_size_gb":                metrics.get("s3_size_gb"),
            "mobile_users":               metrics.get("mobile_users"),
        },
    }

    # Add pricing data only if available (SaaS mode)
    if pricing and client_mode == "saas":
        ctx.update({
            "monthly_cost_usd":  pricing.get("total_monthly_usd"),
            "annual_cost_usd":   pricing.get("total_annual_usd"),
            "three_year_usd":    pricing.get("total_3year_usd"),
            "category_totals":   pricing.get("category_totals", {}),
            "top_services": [
                {
                    "label":    r.get("label"),
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
    else:
        ctx["note"] = "This is an on-premise deployment. No cloud pricing data is available - this is sizing information only."

    return json.dumps(ctx, indent=2)


def _call_groq(messages: list, context: str) -> str:
    """Call Groq API with full conversation history."""
    try:
        from groq import Groq
    except ImportError:
        return "❌ groq package not installed. Run: `pip install groq`"

    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return "❌ GROQ_API_KEY not set in .env"

    client = Groq(api_key=api_key)
    system = SYSTEM_PROMPT.format(context=context)

    for model in GROQ_MODELS:
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=[{"role": "system", "content": system}] + messages,
                temperature=0.3,
                max_tokens=800,
            )
            return resp.choices[0].message.content
        except Exception as e:
            if "rate_limit" in str(e).lower() or "429" in str(e):
                continue
            return f"❌ Groq error: {e}"

    return "❌ All Groq models rate-limited. Try again in a moment."


def render_chatbot(pricing: dict | None, distribution: dict, metrics: dict, client_mode: str = "saas"):
    """
    Render the full chatbot UI inside the Streamlit app.
    Call this after the pricing results are available.
    """
    st.markdown("---")
    if client_mode == "onprem":
        st.markdown("## 💬 Ask About This Infrastructure Sizing")
        st.caption("Ask anything about infrastructure requirements, node distribution, architecture, or sizing scenarios.")
    else:
        st.markdown("## 💬 Ask About This Estimate")
        st.caption("Ask anything about costs, architecture, node distribution, optimisations, or what-if scenarios.")

    # Session state for chat history
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    if "chat_context" not in st.session_state:
        st.session_state.chat_context = _build_context(pricing, distribution, metrics, client_mode)

    # Suggested questions based on client mode
    if client_mode == "onprem":
        suggestions = [
            "What is the total infrastructure requirement?",
            "How many worker nodes do I need?",
            "What are the database sizing requirements?",
            "What storage capacity is needed?",
            "Explain the node distribution rationale.",
            "What would happen if I double the users?",
        ]
    else:
        suggestions = [
            "What is the most expensive service?",
            "How can we reduce monthly cost by 20%?",
            "What does the DB tier cost per month?",
            "What would happen if we doubled the users?",
            "Explain the node distribution rationale.",
            "What is the 5-year total with inflation?",
        ]

    st.markdown("**💡 Suggested questions:**")
    cols = st.columns(3)
    for i, suggestion in enumerate(suggestions):
        if cols[i % 3].button(suggestion, key=f"suggest_{i}", use_container_width=True):
            st.session_state.chat_history.append({"role": "user", "content": suggestion})
            with st.spinner("Thinking…"):
                reply = _call_groq(st.session_state.chat_history, st.session_state.chat_context)
            st.session_state.chat_history.append({"role": "assistant", "content": reply})
            st.rerun()

    # Chat history display
    chat_container = st.container(height=400, border=True)
    with chat_container:
        if not st.session_state.chat_history:
            if client_mode == "onprem":
                st.markdown(
                    "<div style='color:var(--text3);text-align:center;padding:40px;'>"
                    "Ask a question about your infrastructure sizing above ☝️</div>",
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    "<div style='color:var(--text3);text-align:center;padding:40px;'>"
                    "Ask a question about your estimate above ☝️</div>",
                    unsafe_allow_html=True,
                )
        for msg in st.session_state.chat_history:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

    # Input box — inline (not sticky)
    col_input, col_btn = st.columns([6, 1])
    with col_input:
        user_input_text = st.text_input("", placeholder="Ask about your estimate…", key="chat_input", label_visibility="collapsed")
    with col_btn:
        send = st.button("Send ➤", key="chat_send", use_container_width=True, type="primary")

    user_input = user_input_text if (send and user_input_text.strip()) else None
    if user_input:
        st.session_state.chat_history.append({"role": "user", "content": user_input})
        with st.spinner("Thinking…"):
            reply = _call_groq(st.session_state.chat_history, st.session_state.chat_context)
        st.session_state.chat_history.append({"role": "assistant", "content": reply})
        st.rerun()

    # Clear chat
    if st.session_state.chat_history:
        if st.button("🗑️ Clear Chat", key="clear_chat", type="secondary"):
            st.session_state.chat_history = []
            st.session_state.chat_context = _build_context(pricing, distribution, metrics, client_mode)
            st.rerun()