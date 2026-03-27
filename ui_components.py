"""
ui_components.py
─────────────────────────────────────────────────────────────
Reusable Streamlit UI rendering functions.
Nothing here calls backend logic — it only renders data
passed in as arguments.

Sections:
  - render_pricing_results()    → full pricing dashboard
  - render_node_distribution()  → cloud sizing table
  - render_metrics_cards()      → extracted Excel metrics
  - render_summary_table()      → yearly assumptions table
  - build_summary_dataframe()   → helper to build the 20-row df
─────────────────────────────────────────────────────────────
"""

import json
import pandas as pd
import streamlit as st

def _metric(col, label, value):
    """Themed metric card replacing st.metric()"""
    col.markdown(f"""
    <div style="background:var(--surface);border:1.5px solid var(--border);
                border-top:3px solid var(--accent);border-radius:12px;
                padding:1rem 1.25rem;box-shadow:var(--shadow);
                margin-bottom:0.5rem;">
      <div style="font-size:0.72rem;font-weight:600;text-transform:uppercase;
                  letter-spacing:0.08em;color:var(--text2);margin-bottom:0.4rem;">{label}</div>
      <div style="font-size:1.5rem;font-weight:800;color:var(--text);line-height:1;">{value}</div>
    </div>""", unsafe_allow_html=True)




# ── Number formatter ──────────────────────────────────────────────────────

def fmt(n):
    if isinstance(n, (int, float)):
        if n >= 1_000_000:
            return f"{n / 1_000_000:,.2f}M"
        if n >= 1_000:
            return f"{n / 1_000:,.0f}K"
        return f"{n:,}"
    return str(n)


# ── Yearly summary table builder ──────────────────────────────────────────

def build_summary_dataframe(
    years_list,
    named_users, concurrent, customers,
    leads_list, cases_list, mobile, product_holdings,
    activities_per_customer, activities_per_lead, activities_per_case,
    documents_per_customer, documents_per_lead, documents_per_case,
    YOY_NAMED_USERS, YOY_CONCURRENT, YOY_CUSTOMERS,
    YOY_LEADS, YOY_CASES, YOY_PRODUCT_HOLD,
    YOY_MOBILE=None,   # independent mobile growth rate; falls back to YOY_NAMED_USERS if not supplied
) -> pd.DataFrame:
    mobile_yoy = YOY_MOBILE if YOY_MOBILE is not None else YOY_NAMED_USERS
    rows = [
        {"S.No.": 1,  "Assumptions for sizing": "Total Number of named Users",
         **{y: fmt(v) for y, v in zip(years_list, named_users)},
         "YoY Growth %": f"{YOY_NAMED_USERS*100:.0f}%"},
        {"S.No.": 2,  "Assumptions for sizing": "Number of concurrent users",
         **{y: fmt(v) for y, v in zip(years_list, concurrent)},
         "YoY Growth %": f"{YOY_CONCURRENT*100:.0f}%"},
        {"S.No.": 3,  "Assumptions for sizing": "Total no. of customers (Retail+Wholesale+SME/MSME)",
         **{y: fmt(v) for y, v in zip(years_list, customers)},
         "YoY Growth %": f"{YOY_CUSTOMERS*100:.0f}%"},
        {"S.No.": 4,  "Assumptions for sizing": "Number of Activities per customer",
         **{y: activities_per_customer for y in years_list}, "YoY Growth %": "0%"},
        {"S.No.": 5,  "Assumptions for sizing": "Number of Leads",
         **{y: fmt(v) for y, v in zip(years_list, leads_list)},
         "YoY Growth %": f"{YOY_LEADS*100:.0f}%"},
        {"S.No.": 6,  "Assumptions for sizing": "Number of Activities per Lead",
         **{y: activities_per_lead for y in years_list}, "YoY Growth %": "0%"},
        {"S.No.": 7,  "Assumptions for sizing": "Number of Service Requests (Cases)",
         **{y: fmt(v) for y, v in zip(years_list, cases_list)},
         "YoY Growth %": f"{YOY_CASES*100:.0f}%"},
        {"S.No.": 8,  "Assumptions for sizing": "Number of Activities per Case",
         **{y: activities_per_case for y in years_list}, "YoY Growth %": "0%"},
        {"S.No.": 9,  "Assumptions for sizing": "Number of Campaigns",
         **{y: 50 for y in years_list}, "YoY Growth %": "0%"},
        {"S.No.": 10, "Assumptions for sizing": "Number of Product Holdings per customer",
         **{y: fmt(v) for y, v in zip(years_list, product_holdings)},
         "YoY Growth %": f"{YOY_PRODUCT_HOLD*100:.0f}%"},
        {"S.No.": 11, "Assumptions for sizing": "Number of Concurrent Mobile Users",
         **{y: fmt(v) for y, v in zip(years_list, mobile)},
         "YoY Growth %": f"{mobile_yoy*100:.0f}%"},
        {"S.No.": 12, "Assumptions for sizing": "Number of documents per customer",
         **{y: documents_per_customer for y in years_list}, "YoY Growth %": "0%"},
        {"S.No.": 13, "Assumptions for sizing": "Number of documents per Lead",
         **{y: documents_per_lead for y in years_list}, "YoY Growth %": "0%"},
        {"S.No.": 14, "Assumptions for sizing": "Number of documents per Case",
         **{y: documents_per_case for y in years_list}, "YoY Growth %": "0%"},
        {"S.No.": 15, "Assumptions for sizing": "Total Num of Documents",
         **{y: fmt(documents_per_customer + documents_per_lead + documents_per_case)
            for y in years_list}, "YoY Growth %": "0%"},
        {"S.No.": 16, "Assumptions for sizing": "Size of document",
         **{y: "256 KB" for y in years_list}, "YoY Growth %": "0%"},
        {"S.No.": 17, "Assumptions for sizing": "Number of Emails (Lead/Case)",
         **{y: fmt(int((leads_list[i] + cases_list[i]) * 0.05))
            for i, y in enumerate(years_list)}, "YoY Growth %": "0%"},
        {"S.No.": 18, "Assumptions for sizing": "Number of Escalations",
         **{y: fmt(int((customers[i] + leads_list[i] + cases_list[i]) * 0.10))
            for i, y in enumerate(years_list)}, "YoY Growth %": "0%"},
        {"S.No.": 19, "Assumptions for sizing": "Number of API calls/SMS",
         **{y: fmt(int(leads_list[i] + cases_list[i]))
            for i, y in enumerate(years_list)}, "YoY Growth %": "0%"},
        {"S.No.": 20, "Assumptions for sizing": "Number of SLAs hit",
         **{y: fmt(int(customers[i] + leads_list[i] + cases_list[i]))
            for i, y in enumerate(years_list)}, "YoY Growth %": "0%"},
    ]
    df = pd.DataFrame(rows)
    for col in years_list:
        df[col] = df[col].astype(str)
    return df


# ── Render yearly summary table ───────────────────────────────────────────

def render_summary_table(df: pd.DataFrame, years_list: list):
    st.subheader("📊 Assumptions for Sizing – Yearly Summary")
    st.dataframe(
        df,
        column_config={
            "S.No.":                    st.column_config.NumberColumn("S.No.", width="small"),
            "Assumptions for sizing":   st.column_config.TextColumn("Assumptions for sizing", width="large"),
            "YoY Growth %":             st.column_config.TextColumn("YoY %", width="small"),
        },
        hide_index=True,
        use_container_width=True,
    )
    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        "📥 Download as CSV", csv,
        "yearly_assumptions.csv", "text/csv",
        use_container_width=True,
    )


# ── Render extracted metrics cards ───────────────────────────────────────

def render_metrics_cards(metrics: dict):
    with st.expander("🔬 Extracted Metrics from Excel", expanded=False):
        c1, c2, c3, c4 = st.columns(4)
        _metric(c1, "Worker Nodes", int(metrics.get("total_workernodes", 0)))
        _metric(c2, "Total vCPUs", int(metrics.get("total_vcpus_workernode", 0)))
        _metric(c3, "Total RAM (GB)", int(metrics.get("total_memory_workernode_gb", 0)))
        _metric(c4, "S3 Size (GB)", int(metrics.get("s3_size_gb", 0)))
        _metric(c1, "Data Size (GB)", int(metrics.get("data_size_gb", 0)))
        _metric(c2, "SQL RAM (GB)", int(metrics.get("sql_server_ram_gb", 0)))
        _metric(c3, "Oracle RAM (GB)", int(metrics.get("oracle_ram_gb", 0)))
        _metric(c4, "Postgres RAM", int(metrics.get("postgres_ram_gb", 0)))


# ── Render node distribution table ───────────────────────────────────────

def render_node_distribution(distribution: dict):
    st.markdown("### 🖥️ Cloud Sizing – Node Distribution")

    summary = distribution.get("summary", {})
    s1, s2, s3, s4 = st.columns(4)
    _metric(s1, "Total Worker Nodes", summary.get("total_worker_nodes", 0))
    _metric(s2, "Total DB Nodes", summary.get("total_db_nodes", 0))
    _metric(s3, "LLM Used", "✅ Yes" if summary.get("llm_used") else "📋 Rules only")
    _metric(s4, "Confidence", summary.get("confidence", "—").capitalize())

    notes = summary.get("notes", "")
    if notes:
        is_quota = "quota" in notes.lower() or "resource_exhausted" in notes.lower() or "429" in notes
        is_missing_key = "not set" in notes.lower() or "not installed" in notes.lower()
        if is_quota:
            st.warning(
                "⚠️ **Gemini free-tier quota exhausted** — all available models were tried.  \n"
                "Rule-based node distribution was used instead.  \n"
                "💡 **Options:** Wait until tomorrow for quota reset, or upgrade to a paid Gemini plan.",
                icon="⚠️",
            )
        elif is_missing_key:
            st.info(f"ℹ️ {notes}")
        elif "failed" in notes.lower():
            st.warning(f"⚠️ AI distribution failed — using rules instead. Details: `{notes[:120]}`")
        else:
            st.info(f"💬 {notes}")

    # Combine all roles into one table
    all_roles = (
        distribution.get("worker_nodes", [])
        + distribution.get("db_nodes", [])
        + distribution.get("fixed_roles", [])
    )

    rows = []
    for r in all_roles:
        rows.append({
            "Category":      r.get("category", "—"),
            "Service/Role":  r.get("label", "—"),
            "Nodes":         r.get("nodes", 0),
            "Instance Type": r.get("instance_family", "—"),
            "vCPU/node":     r.get("vcpu_per_node", "—"),
            "RAM/node (GB)": r.get("ram_per_node", "—"),
            "Storage/node":  f"{r.get('storage_per_node_gb', 0)} GB" if r.get("storage_per_node_gb") else "—",
            "Pricing Model": r.get("pricing_model") or "—",
            "Reasoning":     r.get("reasoning", "—"),
        })

    df = pd.DataFrame(rows)
    st.dataframe(
        df,
        column_config={
            "Category":      st.column_config.TextColumn("Category",      width="medium"),
            "Service/Role":  st.column_config.TextColumn("Service/Role",  width="large"),
            "Nodes":         st.column_config.NumberColumn("Nodes",        width="small"),
            "Instance Type": st.column_config.TextColumn("Instance Type", width="medium"),
            "vCPU/node":     st.column_config.TextColumn("vCPU/node",     width="small"),
            "RAM/node (GB)": st.column_config.TextColumn("RAM/node (GB)", width="small"),
            "Storage/node":  st.column_config.TextColumn("Storage/node",  width="small"),
            "Pricing Model": st.column_config.TextColumn("Pricing Model", width="medium"),
            "Reasoning":     st.column_config.TextColumn("Reasoning",     width="large"),
        },
        hide_index=True,
        use_container_width=True,
    )


# ── Render full pricing results dashboard ────────────────────────────────

def render_pricing_results(pricing: dict, updated_file: str = None):
    st.markdown("---")
    st.markdown("## 💰 AWS Cost Estimate")

    # ── KPI row ──────────────────────────────────────────────────────────
    k1, k2, k3 = st.columns(3)
    for col, label, icon, value in [
        (k1, "Monthly (USD)",  "📅", f"${pricing['total_monthly_usd']:,.2f}"),
        (k2, "Annual (USD)",   "📆", f"${pricing['total_annual_usd']:,.2f}"),
        (k3, "3-Year (USD)",   "🗓️", f"${pricing['total_3year_usd']:,.2f}"),
    ]:
        col.markdown(f"""
        <div style="background:var(--surface);border:1.5px solid var(--border);
                    border-top:3px solid var(--accent);border-radius:12px;
                    padding:1.2rem 1.5rem;box-shadow:var(--shadow);">
          <div style="font-size:0.75rem;font-weight:600;text-transform:uppercase;
                      letter-spacing:0.08em;color:var(--text2);margin-bottom:0.5rem;">
            {icon} {label}
          </div>
          <div style="font-size:1.8rem;font-weight:800;color:var(--text);letter-spacing:-0.02em;">
            {value}
          </div>
        </div>""", unsafe_allow_html=True)

    st.markdown("")

    # ── Category spend bars ───────────────────────────────────────────────
    cat_totals = pricing.get("category_totals", {})
    if cat_totals:
        st.markdown("#### Spend by Category")
        cat_df = pd.DataFrame([
            {"Category": k, "Monthly (USD)": v}
            for k, v in sorted(cat_totals.items(), key=lambda x: -x[1])
        ])
        st.dataframe(
            cat_df,
            column_config={
                "Category": st.column_config.TextColumn("Category", width="medium"),
                "Monthly (USD)": st.column_config.ProgressColumn(
                    "Monthly (USD)", format="$%.2f",
                    min_value=0, max_value=max(cat_totals.values()) * 1.1,
                    width="large",
                ),
            },
            hide_index=True, use_container_width=True,
        )

    st.markdown("")

    # ── Detailed role breakdown ───────────────────────────────────────────
    st.markdown("#### Detailed Service Breakdown")
    total = pricing["total_monthly_usd"]
    rows  = []
    for r in pricing.get("priced_roles", []):
        monthly = r.get("monthly_usd", 0)
        pct     = (monthly / total * 100) if total > 0 else 0
        rows.append({
            "Category":      r.get("category", "—"),
            "Service":       r.get("label", "—"),
            "Config":        r.get("note", "—"),
            "Instance":      r.get("instance_type", "—"),
            "Hourly (USD)":  f"${r['hourly_usd']:.4f}" if r.get("hourly_usd") else "—",
            "Monthly (USD)": monthly,
            "% of Total":    round(pct, 1),
            "Source":        "✅ API" if r.get("from_api") else "📋 Est.",
        })

    detail_df = pd.DataFrame(rows)
    st.dataframe(
        detail_df,
        column_config={
            "Category":      st.column_config.TextColumn("Category",     width="small"),
            "Service":       st.column_config.TextColumn("Service",      width="large"),
            "Config":        st.column_config.TextColumn("Config",       width="large"),
            "Instance":      st.column_config.TextColumn("Instance",     width="medium"),
            "Hourly (USD)":  st.column_config.TextColumn("Hourly",       width="small"),
            "Monthly (USD)": st.column_config.NumberColumn("Monthly (USD)", format="$%.2f", width="small"),
            "% of Total":    st.column_config.ProgressColumn("% Total",
                                format="%.1f%%", min_value=0, max_value=100, width="small"),
            "Source":        st.column_config.TextColumn("Source",       width="small"),
        },
        hide_index=True, use_container_width=True,
    )

    # ── Total banner ─────────────────────────────────────────────────────
    a = pricing.get("assumptions", {})
    st.markdown(
        f"""<div style="background:var(--surface2);border-left:4px solid var(--accent);
                    padding:14px 20px;border-radius:10px;margin-top:12px;box-shadow:var(--shadow);">
          <span style="font-size:15px;font-weight:600;color:var(--text);">
            Total Estimated Monthly Cost:
          </span>
          <span style="font-size:22px;font-weight:800;color:var(--accent);margin-left:12px;">
            ${pricing['total_monthly_usd']:,.2f}
          </span>
          &nbsp;&nbsp;
          <span style="font-size:13px;color:var(--text2);">
            {a.get('region','—')} · {a.get('deployment','—')} · {a.get('pricing_date','—')}
          </span>
        </div>""",
        unsafe_allow_html=True,
    )

    # ── Warnings ─────────────────────────────────────────────────────────
    if pricing.get("warnings"):
        with st.expander("⚠️ Warnings"):
            for w in pricing["warnings"]:
                st.warning(w)

    # ── Assumptions ──────────────────────────────────────────────────────
    with st.expander("📋 Pricing Assumptions"):
        cols = st.columns(3)
        cols[0].markdown(f"**Region:** `{a.get('region','—')}`")
        cols[1].markdown(f"**Hours/month:** `{a.get('hours_per_month','—')}`")
        cols[2].markdown(f"**Deployment:** `{a.get('deployment','—')}`")
        cols[0].markdown(f"**OS:** `{a.get('os','—')}`")
        cols[1].markdown(f"**EBS type:** `{a.get('ebs_type','—')}`")
        cols[2].markdown(f"**Pricing date:** `{a.get('pricing_date','—')}`")

    # ── Downloads ────────────────────────────────────────────────────────
    st.markdown("")
    dl1, dl2 = st.columns(2)
    if updated_file:
        try:
            with open(updated_file, "rb") as f:
                dl1.download_button(
                    "📥 Download Sizing Report (XLSX)", f,
                    file_name="updated_estimate.xlsx",
                    key="dl_xlsx", use_container_width=True,
                )
        except Exception:
            pass

    price_json = json.dumps(pricing, indent=2)
    dl2.download_button(
        "📥 Download Pricing JSON", price_json,
        file_name="aws_pricing.json", mime="application/json",
        key="dl_json", use_container_width=True,
    )

# ── Render 5-year inflation forecast ─────────────────────────────────────

def render_inflation_forecast(pricing: dict):
    forecast = pricing.get("inflation_forecast", {})
    if not forecast:
        return

    st.markdown("#### 📈 5-Year Cost Forecast (with Inflation)")
    rate = pricing.get("inflation_rate", 0.04)
    st.caption(f"AWS service cost inflation assumed at **{rate*100:.0f}% per year** (industry average). Base = Year 1 monthly × 12.")

    rows = []
    base_annual = pricing["total_annual_usd"]
    for yr in range(1, 6):
        d = forecast.get(f"year_{yr}", {})
        rows.append({
            "Year":             f"Year {yr}",
            "Annual Cost (USD)": d.get("annual_usd", 0),
            "vs Base":           f"+{d.get('vs_base_pct', 0):.1f}%",
            "Multiplier":        f"{d.get('multiplier', 1):.4f}×",
        })

    rows.append({
        "Year":              "5-Year Total",
        "Annual Cost (USD)": forecast.get("five_year_total", 0),
        "vs Base":           "—",
        "Multiplier":        "—",
    })

    df = pd.DataFrame(rows)
    max_val = max(r["Annual Cost (USD)"] for r in rows if isinstance(r["Annual Cost (USD)"], (int, float)))
    st.dataframe(
        df,
        column_config={
            "Year":              st.column_config.TextColumn("Year",             width="small"),
            "Annual Cost (USD)": st.column_config.ProgressColumn(
                "Annual Cost (USD)", format="$%.0f", min_value=0, max_value=max_val * 1.1, width="large"
            ),
            "vs Base":           st.column_config.TextColumn("vs Base",          width="small"),
            "Multiplier":        st.column_config.TextColumn("Inflation Factor", width="small"),
        },
        hide_index=True, use_container_width=True,
    )

    five_yr = forecast.get("five_year_total", 0)
    flat_5yr = pricing["total_annual_usd"] * 5
    extra = five_yr - flat_5yr
    st.markdown(
        f"""<div style="background:var(--surface2);border-left:4px solid var(--warning);
                    padding:12px 18px;border-radius:10px;margin-top:8px;box-shadow:var(--shadow);">
          <span style="font-weight:600;color:var(--text);font-size:0.95rem;">5-Year Total with {rate*100:.0f}% Inflation:</span>
          <span style="font-size:20px;font-weight:800;color:var(--warning);margin-left:10px;">
            ${five_yr:,.0f}
          </span>
          <span style="font-size:12px;color:var(--text3);margin-left:12px;">
            (+${extra:,.0f} vs flat pricing)
          </span>
        </div>""",
        unsafe_allow_html=True,
    )
    st.markdown("")


# ── Render DB selection ───────────────────────────────────────────────────

def render_db_selection(pricing: dict):
    db = pricing.get("db_selection", {})
    if not db:
        return

    st.markdown("#### 🗄️ Database Hosting Recommendation")

    dbs = [
        ("PostgreSQL",         db.get("postgres", {}),    "🟢"),
        ("SQL Server",         db.get("sql_server", {}),  "🟡"),
        ("Oracle",             db.get("oracle", {}),      "🟡"),
        ("ElastiCache (Redis)", db.get("elasticache", {}), "🔵"),
    ]

    cols = st.columns(4)
    for i, (name, info, icon) in enumerate(dbs):
        hosting  = info.get("hosting", "—")
        monthly  = info.get("monthly", 0)
        reason   = info.get("reason", "—")
        note     = info.get("note", "—")
        bg_color = "#e8f5e9" if "Self" in hosting else "#fff8e6" if "RDS" in hosting else "#e3f2fd"

        cols[i].markdown(
            f"""<div style="background:var(--surface); border-radius:12px; padding:14px;
                           border:1px solid var(--border); min-height:200px; 
                           display:flex; flex-direction:column;
                           box-shadow:var(--shadow); transition: all 0.2s ease;">
              <div style="font-size:13px; font-weight:700; color:var(--text); margin-bottom: 2px;">{icon} {name}</div>
              <div style="font-size:11px; color:var(--text2); margin-top:2px; margin-bottom: 6px;">
                <b>Hosting:</b> {hosting}
              </div>
              <div style="font-size:17px; font-weight:800; color:var(--accent); margin-bottom: 6px;">
                ${monthly:,.0f}<span style="font-size:10px; font-weight:400;">/mo</span>
              </div>
              <div style="font-size:9.5px; color:var(--text2); line-height: 1.35; flex-grow: 1;">{reason}</div>
              <div style="font-size:9px; color:var(--text3); margin-top:8px; font-style:italic; line-height: 1.2;">{note}</div>
            </div>""",
            unsafe_allow_html=True,
        )

    st.markdown("")
    st.info(f"💡 **Summary:** {db.get('summary', '')}", icon="ℹ️")
    st.markdown("")

# ── Render Pre-Prod/SIT/UAT + DR environment pricing ─────────────────────

def render_env_pricing(env_pricing: dict, client_mode: str = "saas"):
    st.markdown("---")
    st.markdown("## 🌐 Additional Environments")

    db_type = env_pricing.get("db_type", "PostgreSQL")
    db_note = env_pricing.get("db_note", "")
    is_saas = env_pricing.get("is_saas", True)

    st.info(f"**DB Type:** {db_type}  |  {db_note}", icon="🗄️")

    # For on-prem, only show DR tab
    if client_mode == "saas":
        tab1, tab2 = st.tabs(["🧪 Pre-Prod / SIT / UAT", "🛡️ DR (Disaster Recovery)"])
    else:
        tab1 = None
        tab2_only = st.container()

    # ── Pre-Prod / SIT / UAT (SaaS only) ─────────────────────────────────
    if client_mode == "saas":
     with tab1:
        preprod = env_pricing.get("preprod_sit_uat", {})
        if not preprod:
            st.info("No Pre-Prod / SIT / UAT environments selected.")
        else:
            env_mult  = preprod.get("env_multiplier", 1)
            env_names = preprod.get("env_names", [])
            base_mo   = round(preprod.get("monthly_usd", 0) / env_mult, 2) if env_mult else preprod.get("monthly_usd", 0)
            base_yr   = round(preprod.get("annual_usd",  0) / env_mult, 2) if env_mult else preprod.get("annual_usd",  0)

            if env_mult > 1:
                st.info(
                    f"**{env_mult} environments selected:** {', '.join(env_names)}  \n"
                    f"Base cost per environment: **${base_mo:,.2f}/mo** · **${base_yr:,.2f}/yr**  \n"
                    f"Total = base × {env_mult} = **${preprod['monthly_usd']:,.2f}/mo**",
                    icon="ℹ️",
                )
            p1, p2 = st.columns(2)
            _metric(p1, "Total Monthly Cost", f"${preprod['monthly_usd']:,.2f}")
            _metric(p2, "Total Annual Cost",  f"${preprod['annual_usd']:,.2f}")

            st.markdown("**Category Breakdown** *(base environment cost)*")
            cat_df = pd.DataFrame([
                {"Category": k, "Monthly (USD)": v}
                for k, v in sorted(preprod.get("category_totals", {}).items(), key=lambda x: -x[1])
            ])
            if not cat_df.empty:
                st.dataframe(
                    cat_df,
                    column_config={
                        "Category":      st.column_config.TextColumn("Category", width="medium"),
                        "Monthly (USD)": st.column_config.ProgressColumn(
                            "Monthly (USD)", format="$%.2f", min_value=0,
                            max_value=max(cat_df["Monthly (USD)"]) * 1.1, width="large"
                        ),
                    },
                    hide_index=True, use_container_width=True,
                )

            with st.expander("📋 Role-by-Role Breakdown"):
                rows = []
                for r in preprod.get("priced_roles", []):
                    if r.get("monthly_usd", 0) > 0:
                        rows.append({
                            "Category":      r.get("category", "—"),
                            "Service":       r.get("label", "—"),
                            "Nodes":         r.get("nodes", "—"),
                            "Instance":      r.get("instance_type", "—"),
                            "Monthly (USD)": r.get("monthly_usd", 0),
                            "Note":          r.get("note", "—"),
                        })
                if rows:
                    st.dataframe(pd.DataFrame(rows),
                        column_config={"Monthly (USD)": st.column_config.NumberColumn("Monthly (USD)", format="$%.2f")},
                        hide_index=True, use_container_width=True)

    # ── DR (both modes) ───────────────────────────────────────────────────
    dr_container = tab2 if client_mode == "saas" else tab2_only
    with dr_container:
        dr = env_pricing.get("dr", {})
        if not dr:
            st.info("DR not included.")
        else:
            d1, d2, d3 = st.columns(3)
            _metric(d1, "DR Monthly", f"${dr['monthly_usd']:,.2f}")
            _metric(d2, "DR Annual", f"${dr['annual_usd']:,.2f}")
            five_yr = dr.get("five_year_forecast", {}).get("five_year_total", 0)
            _metric(d3, "DR 5-Year Total", f"${five_yr:,.2f}")

            st.markdown("**DR 5-Year Inflation Forecast**")
            forecast = dr.get("five_year_forecast", {})
            rows = []
            for yr in range(1, 6):
                d = forecast.get(f"year_{yr}", {})
                rows.append({
                    "Year":              f"Year {yr}",
                    "Annual DR Cost":    d.get("annual_usd", 0),
                    "Inflation Factor":  f"{d.get('multiplier', 1):.4f}×",
                })
            rows.append({
                "Year": "5-Year Total",
                "Annual DR Cost": five_yr,
                "Inflation Factor": "—",
            })
            df = pd.DataFrame(rows)
            max_v = max(r["Annual DR Cost"] for r in rows if isinstance(r["Annual DR Cost"], (int,float)))
            st.dataframe(
                df,
                column_config={
                    "Year":           st.column_config.TextColumn("Year", width="small"),
                    "Annual DR Cost": st.column_config.ProgressColumn(
                        "Annual DR Cost", format="$%.0f", min_value=0, max_value=max_v*1.1, width="large"
                    ),
                    "Inflation Factor": st.column_config.TextColumn("Inflation Factor", width="small"),
                },
                hide_index=True, use_container_width=True,
            )

            with st.expander("📋 DR Role-by-Role Breakdown"):
                rows2 = []
                for r in dr.get("priced_roles", []):
                    if r.get("monthly_usd", 0) > 0:
                        rows2.append({
                            "Category":      r.get("category", "—"),
                            "Service":       r.get("label", "—"),
                            "Nodes":         r.get("nodes", "—"),
                            "Instance":      r.get("instance_type", "—"),
                            "Monthly (USD)": r.get("monthly_usd", 0),
                            "Note":          r.get("note", "—"),
                        })
                if rows2:
                    st.dataframe(pd.DataFrame(rows2),
                        column_config={"Monthly (USD)": st.column_config.NumberColumn("Monthly (USD)", format="$%.2f")},
                        hide_index=True, use_container_width=True)

    # ── Combined summary banner ───────────────────────────────────────────
    combined = env_pricing.get("combined_monthly", 0)
    prod_monthly = 0  # will be added by caller context if needed
    
    pp_names = env_pricing.get("preprod_sit_uat", {}).get("env_names", []) if env_pricing.get("preprod_sit_uat") else []
    has_dr = env_pricing.get("dr") is not None
    
    parts = pp_names.copy()
    if has_dr:
        parts.append("DR")
        
    lbl = " + ".join(parts) + " Combined Monthly:" if parts else "Combined Monthly:"
    
    st.markdown(
        f"""<div style="background:var(--surface2);border-left:4px solid var(--accent);
                    padding:12px 18px;border-radius:10px;margin-top:10px;box-shadow:var(--shadow);">
          <span style="font-weight:600;font-size:14px;color:var(--text);">
            {lbl}
          </span>
          <span style="font-size:20px;font-weight:800;color:var(--accent);margin-left:10px;">
            ${combined:,.2f}
          </span>
          <span style="font-size:12px;color:var(--text3);margin-left:12px;">
            (not included in Production cost above)
          </span>
        </div>""",
        unsafe_allow_html=True,
    )
    st.markdown("")