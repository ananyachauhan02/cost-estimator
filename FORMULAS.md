# BusinessNext Cost Estimator — Formula Reference

> All formulas extracted directly from source code (aws_pricer.py, gcp_pricer.py, env_pricer.py, excel_exporter.py, node_distributor.py). Last audited: April 2026.

---

## 1. Sizing Template Inputs & Outputs

### 1.1 User Inputs Written to Excel (`excel_handler.py`)

| Field | Excel Cell | Notes |
|---|---|---|
| `named_users` | `Customer Volumes!D3` | Year 1 base |
| `concurrent_users` | `Customer Volumes!D4` | Auto = 30% of named users |
| `total_customers` | `Customer Volumes!D5` | Year 1 base |
| `leads` | `Customer Volumes!D7` | Year 1 base |
| `cases` | `Customer Volumes!D9` | Year 1 base |
| `mobile_users` | `Customer Volumes!D13` | Year 1 base |
| `yoy_named_users` | `Customer Volumes!I3` | Decimal e.g. 0.05 |
| `yoy_concurrent` | `Customer Volumes!I4` | Same rate as named users |
| `yoy_customers` | `Customer Volumes!I5` | Decimal |
| `yoy_leads` | `Customer Volumes!I7` | Decimal |
| `yoy_cases` | `Customer Volumes!I9` | Decimal |
| `yoy_mobile` | `Customer Volumes!I13` | Decimal |

### 1.2 Metrics Extracted from Recalculated Excel (`excel_handler.py`)

| Field | Excel Cell | Description |
|---|---|---|
| `total_vcpus_workernode` | `Server size!C6` | Total vCPUs across all worker nodes |
| `total_memory_workernode_gb` | `Server size!C7` | Total RAM (GB) across all worker nodes |
| `total_workernodes` | `Server size!C18` | Total number of worker nodes |
| `sql_server_ram_gb` | `Server size!C23` | RAM required for SQL Server DB |
| `oracle_ram_gb` | `Server size!C24` | RAM required for Oracle DB |
| `postgres_ram_gb` | `Server size!C25` | RAM required for PostgreSQL DB |
| `data_size_gb` | `Server size!C35` | Total data size in GB |
| `s3_size_gb` | `Server size!C36` | Total S3 object storage in GB |

### 1.3 Derived Metrics (computed in Python, not from Excel)

```
concurrent_users     = named_users × 0.30
total_named_users    = passed directly from UI input
```

---

## 2. Node Distribution Formulas (`node_distributor.py`)

### 2.1 Worker Node Role Ratios

Each scalable role receives a fixed fraction of `total_workernodes`:

| Role | Base Ratio | Min Nodes | Per-Node Spec |
|---|---|---|---|
| Web / Mobile / WebAPI | 45% | 2 | 16 vCPU / 32 GB / 256 GB EBS |
| Grafana & Prometheus | 22% | 1 | 8 vCPU / 16 GB / 512 GB EBS |
| EFK Logging | 22% | 1 | 8 vCPU / 16 GB / 1024 GB EBS |

```
role_nodes = max(min_nodes, round(total_workernodes × base_ratio))
```

**Mobile boost** (applied to Web/Mobile/WebAPI only):
```
boost = 1  if (mobile_heavy = True OR mobile_users > 3000)  else 0
web_nodes = max(2, round(total_workernodes × 0.45) + boost)
```

**Rounding drift correction** (ensures total always equals `total_workernodes`):
```
drift = total_workernodes - sum(allocated_nodes)
web_nodes += drift   # remainder absorbed by largest tier
```

### 2.2 Fixed Infrastructure Roles (never scaled)

| Role | Nodes | Spec |
|---|---|---|
| EKS Managed Control Plane | 1 | Managed service |
| ElastiCache (Redis) | 2 | 4 vCPU / 16 GB |
| ALB (Internal + External) | 2 | Managed service |
| Bastion Host | 1 | 2 vCPU / 4 GB / 300 GB EBS |
| NAT Gateway | 2 | Managed service (1 per AZ) |
| ECR Image Registry | 1 | 512 GB storage |
| Backup (S3) | 1 | 5120 GB |

### 2.3 DB Nodes (all environments, always fixed per architecture)

| Role | Nodes | Spec |
|---|---|---|
| Primary DB nodes | 2 | 32 vCPU / 128 GB / 300 GB EBS |
| Cluster (etcd + haproxy / RAC / Always On) | 4 | 2 vCPU / 8 GB / 100 GB EBS |
| SAN storage (Primary) | 2 | `data_size_gb` GB per node (io2) |
| S3 storage | 1 | `s3_size_gb` GB |
| Reporting DB (optional) | 1 | 32 vCPU / 128 GB / 300 GB EBS |
| Reporting SAN (optional) | 1 | `data_size_gb` GB (io2) |

---

## 3. EC2 Instance Selection (`aws_pricer.py`)

### 3.1 Instance Family Selection

```
if (RAM_GB / vCPU) > 8:
    family = "r5"   # memory-optimised
else:
    family = "m5"   # general purpose
```

### 3.2 Instance Size Lookup Table

| vCPU ≤ | RAM ≤ (GB) | Size |
|---|---|---|
| 2 | 8 | large |
| 4 | 16 | xlarge |
| 8 | 32 | 2xlarge |
| 16 | 64 | 4xlarge |
| 32 | 128 | 8xlarge |
| 48 | 192 | 12xlarge |
| 64 | 256 | 16xlarge |

Result: `{family}.{size}` e.g. `r5.4xlarge`

### 3.3 Regional Price Multipliers

All fallback prices are based on `us-east-1 = 1.000`. Final price:

```
adjusted_hourly = base_hourly × region_multiplier
```

Key multipliers: `ap-northeast-1` (Tokyo) = 1.120 · `eu-central-1` (Frankfurt) = 1.090 · `me-south-1` (Bahrain) = 1.150 · `sa-east-1` (São Paulo) = 1.200.

---

## 4. AWS Cost Formulas (`aws_pricer.py`)

### 4.1 Constants

| Constant | Value | Source |
|---|---|---|
| `HOURS_PER_MONTH` | 730 | Industry standard (365 × 24 / 12) |
| `EBS_GP3_PER_GB` | $0.08 / GB / month | AWS On-Demand |
| `EBS_IO2_PER_GB` | $0.125 / GB / month | AWS On-Demand (SAN equivalent) |
| `S3_PER_GB` | $0.023 / GB / month | AWS S3 Standard |
| `ECR_PER_GB` | $0.10 / GB / month | AWS ECR |
| `ALB_BASE_MONTHLY` | $16.43 / month | Per ALB base charge |
| `NAT_BASE_MONTHLY` | $32.00 / month | 2× NAT gateways base |
| `NAT_PER_GB` | $0.045 / GB | Data processed through NAT |
| `CLOUDWATCH_PER_NODE` | $3.50 / node / month | Per-node monitoring |
| EKS control plane | $73.00 / month | $0.10/hr × 730 |

### 4.2 Compute Node Monthly Cost

```
compute_monthly  = hourly_rate × node_count × 730
storage_monthly  = storage_gb_per_node × node_count × EBS_GP3_PER_GB × region_multiplier
monthly_usd      = compute_monthly + storage_monthly
```

### 4.3 SAN / Database Storage Cost (io2)

```
monthly_usd = storage_gb_per_node × node_count × EBS_IO2_PER_GB × region_multiplier
```

### 4.4 S3 Object Storage Cost

```
monthly_usd = total_s3_gb × S3_PER_GB  ($0.023/GB)
```

### 4.5 NAT Gateway Cost

```
egress_cost  = data_size_gb × 0.10 × NAT_PER_GB   (10% of data assumed egress)
monthly_usd  = NAT_BASE_MONTHLY + egress_cost
             = $32.00 + (data_gb × 0.10 × $0.045)
```

### 4.6 ElastiCache Cost

```
monthly_usd = hourly_rate × node_count × 730
```

| Instance | Hourly (fallback) |
|---|---|
| `cache.r6g.large` | $0.166 |
| `cache.r6g.xlarge` | $0.332 |
| `cache.r6g.2xlarge` | $0.665 |

### 4.7 CloudWatch Monitoring Cost

```
monthly_usd = $10.00 (base) + (total_nodes × $3.50)
```
where `total_nodes = total_worker_nodes + total_db_nodes`

### 4.8 Database Hosting Cost Estimates

**PostgreSQL (Self-Hosted EC2):**
```
monthly_usd = hourly_rate(instance) × 2 × 730   (2 primary nodes)
```

**SQL Server (AWS RDS Managed):**
```
monthly_usd = sql_server_ram_gb × $26.00
```

**Oracle (AWS RDS Managed):**
```
monthly_usd = oracle_ram_gb × $22.00
```

### 4.9 Total Monthly / Annual / 3-Year

```
total_monthly_usd = sum of all priced roles' monthly_usd
total_annual_usd  = total_monthly_usd × 12
total_3year_usd   = total_monthly_usd × 36
```

---

## 5. Inflation Forecast (`aws_pricer.py`, `env_pricer.py`)

### 5.1 Annual Forecast Formula

Applied from Year 1 (base = no inflation), compounding 4% per year:

```
inflation_rate  = 0.04
multiplier(yr)  = (1 + 0.04) ^ (yr - 1)
monthly(yr)     = total_monthly_usd × multiplier(yr)
annual(yr)      = monthly(yr) × 12
cumulative      = Σ annual(yr)  for yr in [1..5]
five_year_total = cumulative
```

| Year | Multiplier |
|---|---|
| 1 | 1.0000 (base) |
| 2 | 1.0400 |
| 3 | 1.0816 |
| 4 | 1.1249 |
| 5 | 1.1699 |

---

## 6. PUPM (Price Per User Per Month) Formulas (`excel_exporter.py`, `pdf_report.py`)

### 6.1 Security / Fixed Monthly Costs

These are fixed INR-to-USD conversions applied every year:

| Line Item | Monthly (USD) | Basis |
|---|---|---|
| Airtel SOC | $500.00 | Fixed infrastructure for SOC machines |
| SOC Machines | $416.67 | Rs 30,000 / unit / year ÷ 12 |
| Req 4 – Antivirus & EDR | $36.11 | Rs 2,600 / unit / year ÷ 12 |
| Req 6 – Data Discovery | $55.56 | Rs 4,000 / unit / year ÷ 12 |
| Req 7 – DLP | $0.00 | Not currently charged |

### 6.2 PUPM Calculation Chain (Year by Year)

```
── Input costs (monthly, inflated per year) ──
prod_dc    = total_monthly_usd × inflation_multiplier(yr)
prod_dr    = dr_monthly_usd   × inflation_multiplier(yr)   [if DR selected]
preprod    = preprod_monthly  × inflation_multiplier(yr)   [if Pre-Prod selected]

── Fixed security additions ──
security   = airtel_soc + soc_machines + req4 + req6 + req7
           = $500.00 + $416.67 + $36.11 + $55.56 + $0.00
           = $1,008.34 / month

── Step 1: Total Usage (monthly) ──
total_usage = prod_dc + prod_dr + preprod + security

── Step 2: Business Support ──
business_support = total_usage × 0.039127   (3.91%)

── Step 3: Total Platform Cost (annual) ──
total_platform_yr = (total_usage + business_support) × 12

── Step 4: Buffer ──
buffer = total_platform_yr × 0.05   (5%)

── Step 5: Total AWS Cost (annual) ──
total_aws = total_platform_yr + buffer

── Step 6: Managed Services ──
managed_services = total_aws × 0.30   (30%)

── Step 7: One-Time Costs (Year 1 only) ──
one_time = perf_testing + migration + managed_svc_setup
         = $5,000 + $5,000 + $1,000  (defaults)

── Step 8: Total Cost ──
total_cost = total_aws + managed_services + one_time

── Step 9: Discount ──
discounted_cost = total_cost × (1 - 0.11)   (11% discount)

── Step 10: PUPM ──
named_users_yr = named_users_y1 × (1.05 ^ (yr - 1))   (+5% YOY growth)
PUPM           = discounted_cost / 12 / named_users_yr
```

### 6.3 Summary of Rates

| Rate | Value | Applied To |
|---|---|---|
| Business Support | 3.91% | Total Monthly Usage |
| Buffer | 5.00% | Total Platform Annual Cost |
| Managed Services | 30.00% | Total AWS Annual Cost |
| Discount | 11.00% | Total Cost |
| User YOY Growth | 5.00% | Named Users each year |
| Inflation | 4.00% | All cloud costs from Year 2 |

---

## 7. Additional Environments (`env_pricer.py`)

### 7.1 Scaling Factors

```
DR_SCALE      = 0.60   # DR = 60% of Production (Pilot Light / Warm Standby)
PREPROD_SCALE = 0.40   # Pre-Prod/SIT/UAT = 40% of Production
```

### 7.2 Environment Node Sizing Formulas

All values are derived from actual production `metrics`:

```
── Worker nodes ──
env_worker_nodes  = max(1, ceil(prod_worker_nodes × scale))
env_vcpu_per_node = max(4, prod_vcpu_per_node)     [unchanged, same spec]
env_ram_per_node  = max(16, prod_ram_per_node)     [unchanged, same spec]

── Database ──
env_db_ram   = max(32, ceil(prod_db_ram  × scale / 8) × 8)   [rounded to 8GB]
env_db_vcpu  = max(4,  ceil(prod_db_vcpu × scale / 2) × 2)   [rounded to 2 vCPU]
env_db_nodes = 2  (DR, Multi-AZ)  or  1  (Pre-Prod, Single-AZ)

── Storage ──
env_data_gb  = max(300,  ceil(data_size_gb × scale))
env_s3_gb    = max(500,  ceil(s3_size_gb   × scale))
backup_gb    = max(1000, ceil((data_gb + s3_gb) × scale))
```

### 7.3 Environment Cost Formulas (same as Production)

```
worker_cost = hourly × env_worker_nodes × 730
              + worker_storage_gb × env_worker_nodes × EBS_GP3 × region_mult

db_cost     = hourly × env_db_nodes × 730
              + 300 × env_db_nodes × EBS_GP3 × region_mult

san_cost    = env_data_gb × env_db_nodes × EBS_IO2 × region_mult

s3_cost     = env_s3_gb × S3_PER_GB

cache_cost  = ELASTICACHE_HOURLY × cache_nodes × 730 × region_mult

backup_cost = backup_gb × S3_PER_GB
```

### 7.4 DR 5-Year Inflation Forecast

```
multiplier(yr) = (1 + 0.04) ^ yr           [Note: starts at yr=1, so Year 1 = 1.04×]
annual_dr(yr)  = dr_monthly × 12 × multiplier(yr)
five_year_total = Σ annual_dr(yr)  for yr in [1..5]
```

> Note: DR inflation starts from Year 1 (not Year 0), so even Year 1 includes one step of inflation. Production forecast starts from Year 1 at the base rate (multiplier = 1.0).

---

## 8. GCP Cost Formulas (`gcp_pricer.py`)

### 8.1 GCE Instance Pricing

```
── n2-standard (general purpose, RAM/vCPU ≤ 8) ──
hourly = vCPU × $0.0475  +  RAM_GB × $0.00638

── n2-highmem (memory-optimised, RAM/vCPU > 8) ──
hourly = vCPU × $0.0475  +  RAM_GB × $0.00913

final_hourly = hourly × region_multiplier
```

Valid n2 vCPU sizes: 2, 4, 8, 16, 32, 48, 64, 80, 96 (rounded up to nearest valid size).

### 8.2 GCP Storage Pricing

| Storage Type | Rate | AWS Equivalent |
|---|---|---|
| Persistent Disk SSD | $0.17 / GB / month | EBS gp3 |
| Persistent Disk Extreme | $0.125 / GB / month | EBS io2 (SAN) |
| Persistent Disk Standard | $0.04 / GB / month | EBS sc1 |

```
pd_ssd_monthly   = storage_gb × $0.17
pd_extreme_monthly = storage_gb × $0.125
```

### 8.3 GCP Managed Services

| Service | Rate | Notes |
|---|---|---|
| GKE Cluster | $73.00 / month | Standard cluster fee |
| Memorystore Redis (5GB) | $0.147 / hr | $0.049 × 3 |
| Memorystore Redis (16GB) | $0.245 / hr | $0.049 × 5 |
| Memorystore Redis (32GB) | $0.490 / hr | $0.049 × 10 |
| Cloud Load Balancing | $35.00 / month | Internal + External |
| Cloud NAT | $32.00 / month | Regional |
| Artifact Registry (ECR equivalent) | $0.10 / GB / month | |
| Cloud Armor Advanced | $200.00 / month | WAF |
| Cloud SQL (Postgres) | $0.0564/vCPU/hr + $0.0095/GB/hr | Enterprise tier |
| Cloud Logging + Monitoring | $10.00 base + $3.50/node/month | |

### 8.4 GCP Compute Monthly Formula

```
compute_monthly  = hourly × node_count × 730
storage_monthly  = storage_gb × node_count × (PD_SSD_PER_GB × 730) × region_mult
monthly_usd      = compute_monthly + storage_monthly
```

### 8.5 AWS vs GCP Comparison

```
diff_monthly  = abs(aws_monthly - gcp_monthly)
cheaper_cloud = "AWS" if aws_monthly ≤ gcp_monthly else "GCP"

aws_5year     = sum of aws inflation forecast years 1-5
gcp_5year     = sum of gcp inflation forecast years 1-5
diff_5year    = abs(aws_5year - gcp_5year)

pct_diff(a, b) = (a - b) / b × 100   [% difference a vs b]
```

---

## 9. On-Premise Sizing (`excel_exporter.py`)

### 9.1 Per-Year Infrastructure Growth

```
worker_nodes(yr) = ceil(base_workers × (1.05 ^ (yr - 1)))   [+5%/yr]
data_gb(yr)      = base_data_gb × (1.10 ^ (yr - 1))         [+10%/yr]
s3_gb(yr)        = base_s3_gb   × (1.10 ^ (yr - 1))         [+10%/yr]
db_vcpu(yr)      = max(base_db_vcpu, ceil(base_db_vcpu × (data_gb(yr) / base_data_gb)))
db_ram(yr)       = db_vcpu(yr) × 16   [16 GB per vCPU]
```

### 9.2 NFS Storage Formula

```
nfs_gb = data_gb + s3_gb
       + (worker_nodes × 256)      [256 GB per worker node]
       + (infra_nodes  × 256)      [256 GB per infra node]
       + IMAGE_REGISTRY_GB          [1024 GB constant]
```

### 9.3 Fixed On-Prem Node Specs

| Role | CPU Cores | RAM (GB) | Storage (GB) |
|---|---|---|---|
| Bootstrap machine | 2 | 16 | 256 |
| Bastion host | 2 | 16 | 256 |
| Master nodes (×3, constant) | 4 each | 16 each | 256 each |
| Worker nodes (Linux/RHEL) | 8 each | 32 each | 256 each |
| Infra nodes (Grafana/EFK/Redis) | 4 each | 32 each | 256 each |
| DB Windows/Linux nodes | derived | derived | 300 each |
| Archival SAN (PROD only) | — | — | 5000 GB |
| Image Registry | — | — | 1024 GB |

---

## 10. YOY Growth Arrays (`3_Estimator.py`)

Applied in the UI for the 5-year summary table — distinct from the cloud inflation rate:

```
named_users(yr)   = named_users_y1  × (1 + yoy_named_users) ^ (yr - 1)
concurrent(yr)    = concurrent_y1   × (1 + yoy_named_users) ^ (yr - 1)
mobile(yr)        = mobile_y1       × (1 + yoy_mobile)      ^ (yr - 1)
customers(yr)     = customers_y1    × (1 + yoy_customers)   ^ (yr - 1)
leads(yr)         = leads_y1        × (1 + yoy_leads)       ^ (yr - 1)
cases(yr)         = cases_y1        × (1 + yoy_cases)       ^ (yr - 1)
product_hold(yr)  = 1               × (1 + 0.05)            ^ (yr - 1)
```

Default YOY rates (user-configurable):

| Metric | Default Rate |
|---|---|
| Named Users | 5% |
| Concurrent Users | 5% (inherits named users rate) |
| Mobile Users | 5% |
| Total Customers | 10% |
| Leads | 10% |
| Cases | 5% |
| Product Holdings | 5% (fixed) |
