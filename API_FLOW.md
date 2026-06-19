# BusinessNext Cost Estimator — API Flow & Architecture Reference

> Documents every external API call, internal data flow, module dependency chain, and session state lifecycle. Last audited: April 2026.

---

## 1. High-Level Architecture

```
Browser / Streamlit UI
        │
        ▼
┌─────────────────────────────────────────────────────────┐
│                   app.py  (entry point)                  │
│  Auth → Page routing → Sidebar logo → Logout             │
└────────────────────┬────────────────────────────────────┘
                     │  st.navigation()
        ┌────────────┼──────────────────┐
        ▼            ▼                  ▼
  1_Clients.py  2_Estimates.py   3_Estimator.py   4_Admin.py
        │                              │
        │                              │ orchestrates
        ▼                              ▼
  database.py                ┌─────────────────────┐
  (PostgreSQL via             │  excel_handler.py    │
   SQLAlchemy)                │  node_distributor.py │
                              │  aws_pricer.py       │
                              │  gcp_pricer.py       │
                              │  env_pricer.py       │
                              │  excel_exporter.py   │
                              │  pdf_report.py       │
                              │  chatbot.py          │
                              └─────────────────────┘
```

---

## 2. Authentication Flow

### 2.1 Login Sequence

```
User submits email + password (app.py login_ui)
    │
    ▼
database.verify_user(email, password)
    │  SELECT from users WHERE email = ?
    │  bcrypt.checkpw(password, stored_hash)
    │
    ├─ SUCCESS → st.session_state.logged_in = True
    │            st.session_state.user = {id, email, name, role}
    │            st.rerun() → routes to 1_Clients.py
    │
    └─ FAIL    → st.error("Invalid email or password")
```

### 2.2 Role-Based Access (rbac.py)

```
Roles:   admin > estimator > viewer

Permissions:
  admin      → view_all, create_client, delete_client,
                create_estimate, delete_estimate, manage_users
  estimator  → view_all, create_client, create_estimate
  viewer     → view_all

require(action) → calls st.stop() if role lacks permission
can(action)     → returns bool, used for conditional UI elements
```

---

## 3. Main Estimation Pipeline (`3_Estimator.py`)

When the user clicks **Generate**, 7 sequential steps run in order:

```
Step 1: excel_handler.write_and_recalculate()
    │   Copy Sizing_Template.xlsx
    │   Write UI inputs to blue cells
    │   LibreOffice headless --convert-to xlsx (recalculates formulas)
    ▼
Step 2: excel_handler.extract_metrics()
    │   openpyxl load_workbook(data_only=True)
    │   Read OUTPUT_CELL_MAP cells → Python dict
    ▼
Step 3: node_distributor.distribute_nodes()
    │   Rule-based baseline → role ratios × total_workernodes
    │   [Optional] Groq LLM adjustment (GROQ_API_KEY env var)
    │   Return: {worker_nodes, db_nodes, fixed_roles, summary}
    ▼
Step 4a [SaaS only]: aws_pricer.calculate_pricing()
    │   boto3 AWS Pricing API (us-east-1 endpoint)
    │   Fallback: hardcoded EC2_FALLBACK dict
    │   Return: {priced_roles, category_totals, monthly, annual, forecast}
    ▼
Step 4b [SaaS only]: gcp_pricer.calculate_gcp_pricing()
    │   GCP Cloud Billing Catalog API (if GOOGLE_CLOUD_PROJECT set)
    │   Fallback: hardcoded GCE price constants
    │   Return: {priced_roles, monthly, annual, forecast}
    │
    │   gcp_pricer.build_comparison(aws, gcp)
    │   Return: {summary, category_comparison, yearly_comparison}
    ▼
Step 5 [SaaS + env selected]: env_pricer.price_additional_environments()
    │   Derives Pre-Prod (40%) and DR (60%) from production metrics
    │   AWS Pricing API or fallback for env instance prices
    │   Return: {preprod_sit_uat, dr, combined_monthly}
    ▼
Step 6: excel_exporter.generate_excel_reports()
    │   Workbook 1: cloud_sizing.xlsx (always - Prod Sizing, Pre-Prod Sizing, DR Sizing)
    │   Workbook 2: cloud_pricing.xlsx (SaaS only - Cumulative Summary, Prod Pricing, Pre-Prod Pricing, DR Pricing)
    │   Workbook 3+4: onprem_openshift/kubeadm sizing (On-Prem only)
    │   Uses openpyxl — no external APIs
    ▼
Step 7: pdf_report.generate_pdf_report()
    │   ReportLab BaseDocTemplate
    │   Sections: Cover, Exec Summary, Node Distribution,
    │             AWS Cost Breakdown, 5-Year Forecast,
    │             Environment Pricing, PUPM Analysis,
    │             GCP Pricing, AWS vs GCP Comparison,
    │             Notes & Assumptions
    ▼
database.save_estimate()
    │   INSERT into estimates table
    │   Stores: metrics JSON, pricing JSON, distribution JSON,
    │           env_pricing JSON, Excel file bytes (BLOB),
    │           cost figures as indexed Float columns
    └── Returns estimate ID
```

---

## 4. External API Integrations

### 4.1 AWS Pricing API (`aws_pricer.py`)

**Client initialisation:**
```python
boto3.client("pricing", region_name="us-east-1")
# AWS Pricing API is only available in us-east-1 globally
```

**EC2 price fetch:**
```
POST https://pricing.us-east-1.amazonaws.com/

ServiceCode: "AmazonEC2"
Filters:
  instanceType  = {instance_type}   e.g. "r5.4xlarge"
  regionCode    = {region}          e.g. "ap-south-1"
  tenancy       = "Shared"
  operatingSystem = "Linux"
  preInstalledSw  = "NA"
  capacitystatus  = "Used"

Response path:
  PriceList[0] → terms.OnDemand → priceDimensions → pricePerUnit.USD
```

**ElastiCache price fetch:**
```
ServiceCode: "AmazonElastiCache"
Filters:
  instanceType = {instance_type}   e.g. "cache.r6g.large"
  regionCode   = {region}
  cacheEngine  = "Redis"
```

**Fallback behaviour:**
- If `boto3` is unavailable or throws: use `EC2_FALLBACK` dict × `region_multiplier`
- If API returns empty PriceList: use fallback
- Warning added to result: `"No prices fetched from AWS API — using fallback rates."`

**AWS IAM permissions required:**
```json
{
  "Effect": "Allow",
  "Action": ["pricing:GetProducts"],
  "Resource": "*"
}
```

### 4.2 GCP Cloud Billing Catalog API (`gcp_pricer.py`)

**Activation condition:**
```python
os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("GCP_PROJECT")
# AND google-cloud-billing library installed
```

**If not available:** uses hardcoded March 2026 fallback constants (n2 vCPU/RAM hourly rates). All current deployments use fallback.

### 4.3 Groq LLM API (`node_distributor.py`)

**Activation condition:**
```python
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
use_llm = True   # UI toggle must be on
```

**API call:**
```
POST https://api.groq.com/openai/v1/chat/completions

Model cascade (tried in order):
  1. llama-3.3-70b-versatile   (1,000 req/day free tier)
  2. llama-3.1-8b-instant      (14,400 req/day free tier)
  3. gemma2-9b-it              (14,400 req/day free tier)

Parameters:
  temperature = 0   (deterministic — same inputs → same output)
  max_tokens  = 1500

System prompt: "AWS cloud architect — respond with raw JSON only"
User prompt:   Sizing metrics + workload profile + rule-based baseline
               + hard constraints (total must equal N nodes)
```

**Retry logic:**
```
max_retries = 3 per model
Backoff: 3s → 6s → 12s on rate limit (HTTP 429)
On quota exhaustion: skip to next model
On all models failing: use rule-based baseline (no LLM)
```

**In-process cache:**
```python
_DISTRIBUTION_CACHE: dict = {}
key = SHA256(relevant_metrics + workload_profile)
# Same inputs within one process → cached result, zero API calls
```

**Response parsing:**
```
JSON extracted from response string
Strip ```json fences if present
Validate: distribution list + total_nodes_allocated + confidence + notes
Fallback to baseline on any parse error
```

### 4.4 Anthropic Claude API (Artifact / in-browser only)

Used in `businessnext_ui.html` (standalone HTML prototype only, not in the live Streamlit app):
```javascript
POST https://api.anthropic.com/v1/messages
model: "claude-sonnet-4-20250514"
max_tokens: 1000
```
This is the in-browser demo only — the production Streamlit app uses Groq for LLM features.

---

## 5. Database API (`database.py`)

**Connection:**
```python
DATABASE_URL = f"postgresql+psycopg2://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
engine = create_engine(DATABASE_URL)
```

**Tables:**

| Table | Key Columns |
|---|---|
| `users` | id, email, password_hash (bcrypt), role, name, created_at |
| `clients` | id, name, sector, created_at |
| `estimates` | id, client_id (FK), version, customer_name, client_mode, db_type, years, all_metrics (JSON), pricing_json (JSON), distribution_json (JSON), env_pricing_json (JSON), total_monthly_usd, total_annual_usd, total_5year_usd, cloud_sizing_file (BLOB), aws_pricing_file (BLOB) |

**Key operations:**

```python
verify_user(email, password)           → dict | None
create_user(email, password, name, role) → int (user_id)
get_all_users()                        → list[dict]
update_user(user_id, role, name)       → bool
delete_user(user_id)                   → bool
reset_user_password(user_id, new_pw)   → bool

get_all_clients()                      → list[dict] (with estimate counts)
create_client(name, sector)            → int (client_id)
get_client_by_id(client_id)            → dict | None
delete_client(client_id)               → bool (cascades to estimates)

save_estimate(...)                     → int (estimate_id)
get_estimates_by_client(client_id)     → list[dict]
get_estimate_by_id(estimate_id)        → dict | None
get_estimate_files(estimate_id)        → {cloud_sizing: bytes, aws_pricing: bytes}
delete_estimate(estimate_id)           → bool
```

**Version auto-increment:**
```python
# On save: find max version for client_id, increment by 1
last = db.query(Estimate.version).filter(Estimate.client_id == client_id)
         .order_by(Estimate.version.desc()).first()
version = (last[0] + 1) if last else 1
```

---

## 6. Excel Processing (`excel_handler.py`)

### 6.1 Write Phase

```
1. shutil.copy(Sizing_Template.xlsx → reports/updated_estimate.xlsx)
2. openpyxl.load_workbook(dst, data_only=False)
3. For each input field: ws[coord] = value
4. wb.save(dst)
```

### 6.2 LibreOffice Recalculation Phase

```bash
libreoffice --headless --norestore \
  --convert-to xlsx \
  reports/updated_estimate.xlsx \
  --outdir /tmp/{tempdir}
```

- Timeout: 120 seconds
- On `FileNotFoundError`: skip recalculation, warn that formula cache may be stale
- On success: copy `/tmp/{tempdir}/updated_estimate.xlsx` back to `reports/`

### 6.3 Read Phase

```
openpyxl.load_workbook(dst, data_only=True)
# data_only=True reads cached formula results, not formula strings
For each OUTPUT_CELL_MAP entry: float(ws[coord].value)
```

---

## 7. Chatbot API Flow (`chatbot.py`)

```
User types question or clicks suggested question
    │
    ▼
_build_context(pricing, distribution, metrics)
    │   Serialises: top 10 priced roles, node distribution,
    │               sizing metrics, inflation forecast,
    │               db_selection, assumptions
    │   → JSON string injected into system prompt
    ▼
_call_groq(messages, context)
    │   POST https://api.groq.com/openai/v1/chat/completions
    │   Model cascade: llama-3.3-70b → llama-3.1-8b → gemma2-9b
    │   temperature = 0.3   (slightly creative for conversational responses)
    │   max_tokens  = 800
    │   Full conversation history sent every call (no server-side memory)
    ▼
Response appended to st.session_state.chat_history
st.rerun() → chat display updated
```

**Context included in every call:**
- Monthly / annual / 3-year cost
- Category cost breakdown
- Top 10 most expensive services
- Node distribution summary
- Sizing metrics (nodes, vCPUs, RAM, data GB)
- Pricing assumptions (region, OS, EBS type)
- 5-year inflation forecast
- DB hosting recommendations

---

## 8. Report Generation APIs

### 8.1 Excel Exporter (`excel_exporter.py`)

**No external APIs.** Uses `openpyxl` only.

Workbooks generated per mode:

| Mode | Workbook | Sheets |
|---|---|---|
| SaaS | `cloud_sizing.xlsx` | Sizing configuration without pricing data: Prod Sizing · Pre-Prod/SIT/UAT Sizing · DR Sizing |
| SaaS | `cloud_pricing.xlsx` | Detailed cost breakdowns: Cumulative Summary · Prod Pricing · Pre-Prod Pricing · DR Pricing · PUPM Summary · GCP Pricing · Comparison |
| On-Prem | `cloud_sizing.xlsx` | Cloud Sizing only (no pricing sheets) |
| On-Prem | `onprem_openshift_{db}_sizing.xlsx` | Data · PROD-1Yr…NYr · [DR] · [PRE-PROD] · [UAT] · [SIT] |
| On-Prem | `onprem_kubeadm_{db}_sizing.xlsx` | Same sheets as OpenShift, different cluster label |

### 8.2 PDF Report (`pdf_report.py`)

**No external APIs.** Uses `ReportLab` only.

```
generate_pdf_report(pricing, distribution, metrics, env_pricing,
                    customer, client_mode, output_path,
                    gcp_pricing, comparison)
    │
    ▼
BaseDocTemplate(A4, NumberedCanvas)
    │
    ├── Cover page (full-bleed canvas graphics)
    ├── Section 1: Executive Summary + KPI strip
    ├── Section 2: Node Distribution table
    ├── Section 3: AWS Cost Breakdown [SaaS only]
    ├── Section 4: 5-Year Forecast [SaaS only]
    ├── Section 5: Environment Pricing [if env_pricing]
    ├── Section 6: PUPM Analysis [SaaS only]
    ├── Section 7: GCP Pricing [if gcp_pricing]
    ├── Section 8: AWS vs GCP Comparison [if comparison]
    └── Final:     Notes, Assumptions, Scope, Legal Disclaimer
```

**NumberedCanvas:** Custom canvas subclass that stamps header + footer on every page after the cover. Tracks page numbers via `showPage()` override, writes total page count on `save()`.

---

## 9. Session State Lifecycle (`3_Estimator.py`)

All results are stored in `st.session_state` so they survive reruns:

| Key | Type | Set When | Cleared When |
|---|---|---|---|
| `logged_in` | bool | Successful login | Logout |
| `user` | dict | Login | Logout |
| `selected_client` | dict | Client card clicked | New client selected |
| `client_mode` | str | Mode button clicked | Clear Results |
| `last_updated_file` | str | Step 1 complete | Clear Results |
| `last_metrics` | dict | Step 2 complete | Clear Results |
| `last_distribution` | dict | Step 3 complete | Clear Results |
| `last_pricing` | dict | Step 4a complete | Clear Results |
| `gcp_pricing` | dict | Step 4b complete | Clear Results |
| `comparison` | dict | Step 4b complete | Clear Results |
| `env_pricing` | dict | Step 5 complete | Clear Results |
| `cloud_sizing_xlsx` | str (path) | Step 6 complete | Clear Results |
| `cloud_pricing_xlsx` | str (path) | Step 6 complete | Clear Results |
| `onprem_sizing_xlsx` | str (path) | Step 6 complete | Clear Results |
| `pdf_report_path` | str (path) | Step 7 complete | Clear Results |
| `last_saved_id` | int | DB save complete | Clear Results |
| `customer_name_snap` | str | Generate clicked | Never (persists across mode switches) |
| `show_summary` | bool | Summary button | Hide Summary / Clear |
| `summary_df` | DataFrame | Summary button | Hide Summary / Clear |
| `load_estimate` | dict | Estimate loaded from DB | New generation |
| `selected_aws_region` | str | Region dropdown changed | Never |
| `selected_gcp_region` | str | Region dropdown changed | Never |
| `selected_dr_region` | str | DR region dropdown | Never |

---

## 10. Module Dependency Map

```
app.py
├── database.py          (SQLAlchemy + bcrypt)
└── theme.py             (CSS injection, no deps)

1_Clients.py
├── database.py
├── rbac.py
└── theme.py

2_Estimates.py
├── database.py
├── rbac.py
└── theme.py

3_Estimator.py
├── database.py
├── excel_handler.py     → openpyxl, subprocess (LibreOffice)
├── node_distributor.py  → groq (optional), json, hashlib
├── aws_pricer.py        → boto3, json
├── gcp_pricer.py        → google-cloud-billing (optional)
├── env_pricer.py        → boto3 (via aws_pricer), math
├── excel_exporter.py    → openpyxl
├── pdf_report.py        → reportlab
├── chatbot.py           → groq
├── rbac.py
├── theme.py
└── ui_components.py     → pandas, streamlit

4_Admin.py
├── database.py
├── rbac.py
└── theme.py
```

---

## 11. Environment Variables

| Variable | Required | Used In | Purpose |
|---|---|---|---|
| `DB_USER` | Yes | database.py | PostgreSQL username |
| `DB_PASS` | Yes | database.py | PostgreSQL password |
| `DB_HOST` | Yes | database.py | PostgreSQL host |
| `DB_PORT` | No | database.py | Default: 5432 |
| `DB_NAME` | Yes | database.py | Database name |
| `GROQ_API_KEY` | No | node_distributor.py, chatbot.py | LLM node distribution + chatbot |
| `GOOGLE_CLOUD_PROJECT` | No | gcp_pricer.py | Enable GCP Billing API |
| `GCP_PROJECT` | No | gcp_pricer.py | Alternative GCP project env var |
| `AWS_ACCESS_KEY_ID` | No | aws_pricer.py | Enable live AWS Pricing API |
| `AWS_SECRET_ACCESS_KEY` | No | aws_pricer.py | Enable live AWS Pricing API |
| `AWS_DEFAULT_REGION` | No | aws_pricer.py | Defaults to us-east-1 |

**Without AWS credentials:** all pricing uses `EC2_FALLBACK` hardcoded dict × region multiplier. A warning is shown in the UI.

**Without Groq key:** node distribution uses rule-based ratios only. The LLM toggle is hidden.

---

## 12. Data Flow Diagram (SaaS Mode, Full Run)

```
UI Inputs
(named_users, customers, leads, cases, mobile, YOY rates, region, db_type)
    │
    ▼
excel_handler.write_and_recalculate()
    │  Writes to: Customer Volumes!D3-D13, I3-I13
    │  LibreOffice recalculates Server size sheet
    ▼
excel_handler.extract_metrics()
    │  Reads: Server size!C6, C7, C18, C23-C25, C35-C36
    │  Output: {total_workernodes, vcpus, ram, db_ram, data_gb, s3_gb}
    ▼
node_distributor.distribute_nodes(metrics, workload_profile, db_type)
    │  Rule: role_nodes = max(min, round(total × ratio))
    │  LLM: Groq API adjusts distribution (if key set)
    │  Output: {worker_nodes[], db_nodes[], fixed_roles[], summary{}}
    ▼
aws_pricer.calculate_pricing(distribution, metrics, region)
    │  AWS Pricing API → hourly rates per instance type
    │  Formula: monthly = hourly × nodes × 730 + storage × nodes × rate
    │  Output: {priced_roles[], category_totals{}, monthly, annual, forecast{}}
    │
    ├──► gcp_pricer.calculate_gcp_pricing(distribution, metrics, gcp_region)
    │    GCE pricing: hourly = vCPU × $0.0475 + RAM × $0.00638 or $0.00913
    │    Output: {priced_roles[], monthly, annual, forecast{}}
    │
    ├──► gcp_pricer.build_comparison(aws_pricing, gcp_pricing)
    │    Output: {summary{}, category_comparison[], yearly_comparison[]}
    │
    └──► env_pricer.price_additional_environments(db_type, metrics, regions)
         DR: 60% scale of production metrics
         Pre-Prod: 40% scale of production metrics
         Output: {preprod_sit_uat{}, dr{five_year_forecast{}}, combined_monthly}
    ▼
excel_exporter.generate_excel_reports(...)
    │  cloud_sizing.xlsx      — node architecture (no pricing)
    │  cloud_pricing.xlsx     — costs + PUPM + GCP + comparison
    ▼
pdf_report.generate_pdf_report(...)
    │  8-section A4 PDF with cover, tables, charts
    ▼
database.save_estimate(...)
    │  All JSON blobs + XLSX bytes stored in PostgreSQL
    ▼
UI renders:
    render_metrics_cards()
    render_node_distribution()
    cost_banner()
    render_db_selection()
    render_pricing_results()
    render_inflation_forecast()
    render_env_pricing()
    AWS vs GCP comparison metrics
    Download buttons (XLSX × 2, PDF × 1)
    render_chatbot()
```
