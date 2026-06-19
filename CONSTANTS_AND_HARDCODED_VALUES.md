# Hardcoded Constants & Configuration Values Used in Sizing and Pricing

**Purpose:** This document lists all the constant values and hardcoded ratios/multipliers used throughout the estimation platform to help identify inconsistencies and clarify pricing assumptions.

**Last Updated:** June 16, 2026

---

## Table of Contents

1. [General Infrastructure Constants](#1-general-infrastructure-constants)
2. [Environment Scaling Factors](#2-environment-scaling-factors)
3. [Node Distribution Rules](#3-node-distribution-rules)
4. [AWS EC2 Pricing Constants](#4-aws-ec2-pricing-constants)
5. [AWS Storage & Network Constants](#5-aws-storage--network-constants)
6. [GCP Pricing Constants](#6-gcp-pricing-constants)
7. [Forecast & Inflation Constants](#7-forecast--inflation-constants)
8. [Instance Selection Logic](#8-instance-selection-logic)
9. [Database Sizing Constants](#9-database-sizing-constants)
10. [Regional Multipliers](#10-regional-multipliers)
11. [Excel Export Architecture](#11-excel-export-architecture)

---

## 1. General Infrastructure Constants

| Constant | Value | Module | Purpose |
|----------|-------|--------|---------|
| `HOURS_PER_MONTH` | `730` | aws_pricer.py, env_pricer.py, gcp_pricer.py | Convert hourly rates to monthly (365 days × 24 hrs / 12 months) |
| `BASTION_INSTANCE` | `t3a.medium` (fixed) | aws_pricer.py, env_pricer.py | **Policy**: Bastion always uses AMD t3a.medium — never resolved dynamically |
| `EKS_WORKER_FAMILY` | `Memory Intensive` (fixed) | node_distributor.py, env_pricer.py | **Policy**: All EKS worker nodes select from r5/r6a memory-optimised family |
| `DB_NODE_FAMILY` | `Memory Intensive` (fixed) | node_distributor.py | **Policy**: All DB primary/reporting nodes select from r5/r6a memory-optimised family |

---

## 2. Environment Scaling Factors

These multipliers determine what percentage of Production resources are allocated to each environment.

| Environment | Scale Factor | Module | Notes |
|---|---|---|---|
| **Production** | `1.0` (baseline) | All | All calculations based on this |
| **DR (Disaster Recovery)** | `0.60` | env_pricer.py | 60% of Production compute; "Pilot Light" or "Warm Standby" mode |
| **Pre-Prod / SIT / UAT** | `0.40` | env_pricer.py | 40% of Production compute |

**Location:** [env_pricer.py](env_pricer.py#L25-L27)

```python
DR_SCALE       = 0.60   # DR = 60% of prod compute
PREPROD_SCALE  = 0.40   # Pre-Prod = 40% of prod compute
```

**Important Note:** These are hardcoded values. Any change to environment strategy requires code modification and redeployment.

---

## 3. Node Distribution Rules

The platform uses rule-based distribution to determine how many nodes are allocated to each workload role. The following "base ratios" are **hardcoded** and apply a percentage of total worker nodes to each role.

### 3.1 Scalable Worker Roles

> **Policy (June 2026):** All EKS worker nodes are now **Memory Intensive** → instance family resolves to r5 / r6a only.
> RAM-per-node spec has been raised accordingly: web tier 32→64 GB, monitoring/logging 16→32 GB.

| Role | Base Ratio | Min Nodes | vCPU/Node | RAM/Node | Storage/Node | Instance Family | Reserved? |
|---|---|---|---|---|---|---|---|
| **web_mobile_webapi** | `0.45` (45%) | 2 | 16 | **64 GB** | 256 GB | **Memory Intensive (r5/r6a)** | 3-Year RI |
| **graphana_prometheus** | `0.22` (22%) | 1 | 8 | **32 GB** | 512 GB | **Memory Intensive (r5/r6a)** | 3-Year RI |
| **efk_logging** | `0.22` (22%) | 1 | 8 | **32 GB** | 1024 GB | **Memory Intensive (r5/r6a)** | 3-Year RI |

**Calculation Example:**
- If total worker nodes = 9
- web_mobile_webapi nodes = max(2, round(9 × 0.45)) = max(2, 4) = **4 nodes**
- graphana_prometheus nodes = max(1, round(9 × 0.22)) = max(1, 2) = **2 nodes**
- efk_logging nodes = max(1, round(9 × 0.22)) = max(1, 2) = **2 nodes**

**Mobile User Boost:**
- If `mobile_users > 3000` OR `mobile_heavy=True` in workload profile
- web_mobile_webapi nodes get a **+1 boost**

**Location:** [node_distributor.py](node_distributor.py#L56-L82)

### 3.2 Fixed Infrastructure Roles (Always Present)

| Role | Nodes | vCPU/Node | RAM/Node | Storage | Instance Family | Notes |
|---|---|---|---|---|---|---|
| **Managed K8s** | 1 | 0 | 0 | 0 | K8s Service | Always present, no compute charge |
| **ElastiCache** | 2 | 4 | 16 GB | 0 | Memory Optimized | Standard 2-node cache cluster (HA) |
| **ALB (Load Balancer)** | 2 | 0 | 0 | 0 | ALB | 1 internal + 1 external |
| **Bastion Host** | 1 | 2 | 4 GB | 300 GB | **t3a.medium (fixed)** | **Policy**: always AMD t3a.medium @ $0.0376/hr |
| **NAT Gateway** | 2 | 0 | 0 | 0 | NAT | One per Availability Zone |
| **ECR (Image Registry)** | 1 | 0 | 0 | 512 GB | Managed Service | Container image storage |
| **Backup Storage** | 1 | 0 | 0 | 5120 GB | Cloud Storage | DB & infrastructure logs backup |

**Location:** [node_distributor.py](node_distributor.py#L85-L127)

---

## 4. AWS EC2 Pricing Constants

### 4.1 Hourly Pricing Fallback (On-Demand, USD/hr)

These values are used when the AWS Pricing API is unavailable. **Last updated March 2026.**

| Instance Type | Hourly Rate (USD) | Category |
|---|---|---|
| **General Purpose (m5)** | | |
| m5.large | $0.096 | General |
| m5.xlarge | $0.192 | General |
| m5.2xlarge | $0.384 | General |
| m5.4xlarge | $0.768 | General |
| m5.8xlarge | $1.536 | General |
| m5.12xlarge | $2.304 | General |
| **Compute Intensive Intel (c6i)** | | |
| c6i.large | $0.085 | Compute |
| c6i.xlarge | $0.170 | Compute |
| c6i.2xlarge | $0.340 | Compute |
| c6i.4xlarge | $0.680 | Compute |
| c6i.8xlarge | $1.360 | Compute |
| c6i.12xlarge | $2.040 | Compute |
| c6i.16xlarge | $2.720 | Compute |
| **Compute Intensive AMD (c6a)** | | |
| c6a.large | $0.085 | Compute |
| c6a.xlarge | $0.170 | Compute |
| c6a.2xlarge | $0.340 | Compute |
| c6a.4xlarge | $0.680 | Compute |
| c6a.8xlarge | $1.360 | Compute |
| c6a.12xlarge | $2.040 | Compute |
| c6a.16xlarge | $2.720 | Compute |
| **Memory Optimized Intel (r5)** | | |
| r5.large | $0.126 | Memory |
| r5.xlarge | $0.252 | Memory |
| r5.2xlarge | $0.504 | Memory |
| r5.4xlarge | $1.008 | Memory |
| r5.8xlarge | $2.016 | Memory |
| r5.12xlarge | $3.024 | Memory |
| r5.16xlarge | $4.032 | Memory (BYOL) |
| **Memory Optimized AMD (r6a)** | | |
| r6a.large | $0.110 | Memory AMD |
| r6a.xlarge | $0.220 | Memory AMD |
| r6a.2xlarge | $0.440 | Memory AMD |
| r6a.4xlarge | $0.880 | Memory AMD |
| r6a.8xlarge | $1.760 | Memory AMD |
| r6a.12xlarge | $2.640 | Memory AMD |
| r6a.16xlarge | $3.520 | Memory AMD |
| **Burstable** | | |
| t3.medium | $0.0416 | Bastion / Dev |
| **ElastiCache (Redis)** | | |
| cache.r6g.large | $0.166 | Redis |
| cache.r6g.xlarge | $0.332 | Redis |
| cache.r6g.2xlarge | $0.665 | Redis |

**Location:** [aws_pricer.py](aws_pricer.py#L65-L103)

### 4.2 Storage Pricing (On-Demand, Monthly)

| Service | Unit | Rate | Notes |
|---|---|---|---|
| **S3 Standard** | per GB/month | $0.023 | General purpose storage |
| **EBS GP3** | per GB/month | $0.08 | General-purpose SSD storage per node |

**Location:** [aws_pricer.py](aws_pricer.py#L97-L100)

### 4.3 Network & Managed Services (Monthly)

| Service | Cost | Notes |
|---|---|---|
| **Application Load Balancer (ALB)** | $16.43/node | Per ALB instance; 2 nodes by default |
| **NAT Gateway** | $32.00 base + $0.045/GB egress | Base covers ~2 gateways; data surcharge applied on 10% of data_gb |
| **CloudWatch** | $3.50/node + $10.00 base | Monitoring per node; base is always charged |
| **EKS (Managed Kubernetes)** | $73.00 | Control plane monthly cost (~$0.10/hr) |
| **ECR (Image Registry)** | $0.10/GB/month | Artifact Registry storage |
| **ElastiCache (per node)** | $0.166/hr (`cache.r6g.large`) | env_pricer default; production uses `_cache_instance()` to select |

**Location:** [aws_pricer.py](aws_pricer.py#L112-L115) · [env_pricer.py](env_pricer.py#L59-L64)

### 4.4 EC2 Instance Selection Logic

The system uses a **multi-family preference** approach (`_preferred_families()` → `_instance_candidates()`):

```python
# RAM:vCPU ratio determines family preference
ram_to_vcpu = ram_gb / vcpu
is_memory  = "memory" in hint or ram_to_vcpu > 8
is_compute = "compute" in hint or ram_to_vcpu <= 2

# Priority order per workload type (AMD preferred):
# Memory-Intensive:  [r6a, r5]
# Compute-Intensive: [c6a, c6i, m6a, m5]
# General / Default: [r6a, r5] # Default fallback to Memory AMD
# AMD/BYOL:          [r6a, r5] or [c6a, c6i, m6a, m5]
# Intel-explicit:    [r5, r6a] or [c6i, c6a, m5, m6a]

# CPU Compromise Logic
# The system allows selecting an instance with up to 50% less CPU than the required target 
# IF it prevents over-provisioning memory. Memory must ALWAYS match or exceed the requirement.
# Example: If requirement is 16 vCPU / 64 GB RAM, it will select r6a.2xlarge (8 vCPU / 64 GB RAM)
# instead of r6a.4xlarge (16 vCPU / 128 GB RAM) because `8 * 2 >= 16`.
```

#### Instance Size Tables (vCPU → RAM per family)

| Family | 2vCPU | 4vCPU | 8vCPU | 16vCPU | 32vCPU | 48vCPU | 64vCPU |
|---|---|---|---|---|---|---|---|
| **c6i / c6a** | 4 GB | 8 GB | 16 GB | 32 GB | 64 GB | 96 GB | 128 GB |
| **m5** | 8 GB | 16 GB | 32 GB | 64 GB | 128 GB | 192 GB | 256 GB |
| **r5 / r6a** | 16 GB | 32 GB | 64 GB | 128 GB | 256 GB | 384 GB | 512 GB |

**Location:** [aws_pricer.py](aws_pricer.py#L121-L184)

---

## 5. AWS Storage & Network Constants

### 5.1 S3 Instance Selection

| S3 Size (GB) | Assigned Instance |
|---|---|
| ≤ 100 GB | s3.t3.medium |
| ≤ 500 GB | s3.c5.large |
| > 500 GB | s3.c5.2xlarge |

**Location:** [aws_pricer.py](aws_pricer.py#L124-L126)

### 5.2 Cache Instance Selection

| Cache Size (GB) | Assigned Instance |
|---|---|
| ≤ 16 GB | cache.r6g.large |
| ≤ 32 GB | cache.r6g.xlarge |
| > 32 GB | cache.r6g.2xlarge |

**Location:** [aws_pricer.py](aws_pricer.py#L129-L131)

---

## 6. GCP Pricing Constants

### 6.1 GCP Compute Fallback Pricing (Component-Based, USD/hr)

GCP pricing is calculated per-component (vCPU + RAM separately), not per named instance.

| Component | Rate | Notes |
|---|---|---|
| `GCE_VCPU_HOUR` | $0.0475/vCPU/hr | n2-standard family |
| `GCE_RAM_HOUR_STD` | $0.00638/GB/hr | n2-standard RAM |
| `GCE_RAM_HOUR_HM` | $0.00913/GB/hr | n2-highmem RAM |

Resulting GCE machine types selected:
- `n2-highmem-{v}` when RAM:vCPU > 8 (memory workloads)
- `n2-standard-{v}` otherwise
- Valid sizes: 2, 4, 8, 16, 32, 48, 64, 80, 96 vCPUs

**Location:** [gcp_pricer.py](gcp_pricer.py#L82-L84) · `_gce_instance()`

### 6.2 GCP Storage Pricing

| Storage Type | Rate | Notes |
|---|---|---|
| **PD SSD** (`PD_SSD_PER_GB`) | $0.17/GB/month | All compute + SAN/DB nodes |
| **PD Standard** (`PD_STANDARD_PER_GB`) | $0.04/GB/month | Backup (Nearline equivalent) |

**Location:** [gcp_pricer.py](gcp_pricer.py#L85-L87)

### 6.3 GCP Managed Services

| Service | Constant | Value | Notes |
|---|---|---|---|
| **GKE Cluster** | `GKE_CLUSTER_FEE` | $73.00/month | Standard cluster management |
| **Memorystore Redis 1 GB** | `MEMORYSTORE_HOURLY["1gb"]` | $0.049/hr | Standard tier |
| **Memorystore Redis 5 GB** | `MEMORYSTORE_HOURLY["5gb"]` | $0.147/hr | ×3 |
| **Memorystore Redis 16 GB** | `MEMORYSTORE_HOURLY["16gb"]` | $0.245/hr | ×5 |
| **Memorystore Redis 32 GB** | `MEMORYSTORE_HOURLY["32gb"]` | $0.490/hr | ×10 |
| **Cloud SQL per vCPU** | `CLOUD_SQL_PER_VCPU` | $0.0564/hr | Enterprise Postgres |
| **Cloud SQL per GB RAM** | `CLOUD_SQL_PER_GB` | $0.0095/hr | Enterprise Postgres |
| **Cloud Armor Advanced** | `CLOUD_ARMOR_MONTHLY` | $200.00/month | WAF + DDoS |
| **Cloud Logging per node** | `CLOUD_LOGGING_PER_NODE` | $3.50/node/month | Equivalent to CloudWatch |
| **Cloud Load Balancing** | — | $35.00/month | HTTPS LB approx |
| **Cloud NAT** | — | $32.00/month | Per gateway |

**Location:** [gcp_pricer.py](gcp_pricer.py#L88-L98)

---

## 7. Forecast & Inflation Constants

### 7.1 Inflation Rate (Used for Multi-Year Forecasting)

| Parameter | Value | Scope | Formula |
|---|---|---|---|
| **INFLATION_RATE** | `0.04` (4% annually) | All modules | Year N Cost = Base Cost × $(1.04)^{N-1}$ |

**Location:** 
- [aws_pricer.py](aws_pricer.py#L454)
- [env_pricer.py](env_pricer.py#L25)
- [gcp_pricer.py](gcp_pricer.py#L395)

**Example Calculation (5-Year Forecast):**
- Year 1 (base): $100,000
- Year 2: $100,000 × 1.04 = $104,000
- Year 3: $100,000 × 1.04² = $108,160
- Year 4: $100,000 × 1.04³ = $112,486
- Year 5: $100,000 × 1.04⁴ = $116,985

**Note:** This 4% inflation rate applies uniformly to all services. No differentiation between EC2, storage, or managed services.

### 7.2 Reserved Instance Discounts (PLANNED but NOT FULLY IMPLEMENTED)

The current codebase marks all nodes as "Reserved 3 Yr" in pricing models, but **does not apply actual discount multipliers** to the hourly rates. All pricing uses On-Demand rates.

| RI Type | Theoretical Discount | Current Implementation | Status |
|---|---|---|---|
| 1-Year Reserved | ~30-40% | Not applied | TODO |
| 3-Year Reserved | ~50-60% | Not applied | TODO |

**Location:** [node_distributor.py](node_distributor.py#L68)

---

## 8. Instance Selection Logic

### 8.1 Production DB Node Sizing — `_db_nodes()` (node_distributor.py)

Primary DB node specs are now **derived from metrics**, not hardcoded.

```python
# Step 1 — read total DB RAM from Excel metrics
total_db_ram  = metrics.get("postgres_ram_gb" | "oracle_ram_gb" | "sql_server_ram_gb")

# Step 2 — divide by 2 (always 2 primary nodes) to get raw per-node RAM
raw_ram_per_node = total_db_ram / 2

# Step 3 — apply 1.5× headroom (buffer pools, OS page cache, replica overhead)
effective_ram = raw_ram_per_node * 1.5

# Step 4 — snap UP to nearest Memory-Intensive tier
_MEM_TIERS = [(8, 32), (16, 64), (32, 128), (48, 192), (64, 256)]
vcpu_per_node, ram_per_node = first tier where effective_ram <= tier_ram
```

**DB Tier Snap Table:**

| Raw per-node RAM | After 1.5× | Selected Tier (vCPU / RAM) |
|---|---|---|
| ≤ 21 GB | ≤ 32 GB | 8 vCPU / 32 GB |
| 22–43 GB | ≤ 64 GB | **16 vCPU / 64 GB** |
| 44–85 GB | ≤ 128 GB | **32 vCPU / 128 GB** |
| 86–128 GB | ≤ 192 GB | 48 vCPU / 192 GB |
| 129–171 GB | ≤ 256 GB | 64 vCPU / 256 GB |

> Example: `postgres_ram_gb = 56` → 28 GB/node raw × 1.5 = 42 GB → **16 vCPU / 64 GB** ✅

**Location:** [node_distributor.py](node_distributor.py#L291-L311) · `_db_nodes()`

### 8.2 DB vCPU for Environment Environments (Pre-Prod/DR) — `env_pricer.py`

For environments, DB vCPU is derived from total DB RAM with a ratio formula:

```python
prod_db_vcpu = max(4, prod_db_ram // 4)  # 1 vCPU per 4 GB RAM, min 4
```

| Parameter | Formula | Min Value |
|---|---|---|
| **Pre-Prod DB RAM** | `ceil(prod_db_ram × 0.40 / 8) × 8` | 32 GB |
| **Pre-Prod DB vCPU** | `ceil(prod_db_vcpu × 0.40 / 2) × 2` | 4 vCPU |
| **DR DB RAM** | `prod_db_ram` (always full prod) | same as prod |
| **DR DB vCPU** | `prod_db_vcpu` (always full prod) | same as prod |

**Location:** [env_pricer.py](env_pricer.py#L150-L195)

---

## 9. Database Sizing Constants

### 9.1 Excel Template Default Extraction Values

When metrics cannot be extracted from the Excel template, these defaults are used:

| Metric | Default | Purpose |
|---|---|---|
| **total_workernodes** | 9 | Worker node count |
| **postgres_ram_gb** | 128 | PostgreSQL instance RAM |
| **oracle_ram_gb** | 128 | Oracle instance RAM |
| **sql_server_ram_gb** | 128 | SQL Server instance RAM |
| **data_size_gb** | 2100 | Business data size |
| **s3_size_gb** | 5900 | S3 / object storage size |

**Location:** [env_pricer.py](env_pricer.py#L130-L145)

### 9.2 Environment Storage Scaling

| Storage Type | Pre-Prod Scale | DR (Pilot-Light 50%) | DR (Full 100%) | Minimum |
|---|---|---|---|---|
| **Worker Node Storage** | 256 GB (if scale≥0.55) else 300 GB | 128 GB | 256 GB | – |
| **Data Storage (EBS/SAN)** | `max(300, ceil(prod_data × 0.40))` | `prod_data` (full) | `prod_data` (full) | 300 GB |
| **S3 Storage** | `max(500, ceil(prod_s3 × 0.40))` | `max(500, ceil(prod_s3 × 0.50))` | `max(500, ceil(prod_s3 × 1.0))` | 500 GB |
| **Backup Storage** | `max(1000, ceil((data+s3) × 0.40))` | `max(1000, ceil((data+s3) × 0.50))` | `max(1000, (data+s3))` | 1000 GB |

> **DR SAN always at full production**: DB data is never scaled down in DR — only compute and S3 are.

**Location:** [env_pricer.py](env_pricer.py#L181-L196)

---

## 10. Regional Multipliers

All AWS regions have a **cost multiplier relative to us-east-1** (baseline = 1.0).

### 10.1 Americas

| Region | Label | Multiplier |
|---|---|---|
| us-east-1 | US East (N. Virginia) | 1.000 |
| us-east-2 | US East (Ohio) | 0.990 |
| us-west-1 | US West (N. California) | 1.090 |
| us-west-2 | US West (Oregon) | 1.000 |
| ca-central-1 | Canada (Central) | 1.030 |
| ca-west-1 | Canada West (Calgary) | 1.030 |
| sa-east-1 | South America (São Paulo) | 1.200 |

### 10.2 Europe

| Region | Label | Multiplier |
|---|---|---|
| eu-central-1 | Europe (Frankfurt) | 1.090 |
| eu-central-2 | Europe (Zurich) | 1.150 |
| eu-west-1 | Europe (Ireland) | 1.050 |
| eu-west-2 | Europe (London) | 1.090 |
| eu-west-3 | Europe (Paris) | 1.090 |
| eu-north-1 | Europe (Stockholm) | 1.060 |
| eu-south-1 | Europe (Milan) | 1.090 |
| eu-south-2 | Europe (Spain) | 1.090 |

### 10.3 Asia Pacific

| Region | Label | Multiplier |
|---|---|---|
| ap-south-1 | Asia Pacific (Mumbai) | 1.080 |
| ap-south-2 | Asia Pacific (Hyderabad) | 1.080 |
| ap-northeast-1 | Asia Pacific (Tokyo) | 1.120 |
| ap-northeast-2 | Asia Pacific (Seoul) | 1.120 |
| ap-northeast-3 | Asia Pacific (Osaka) | 1.120 |
| ap-southeast-1 | Asia Pacific (Singapore) | 1.100 |
| ap-southeast-2 | Asia Pacific (Sydney) | 1.130 |
| ap-southeast-3 | Asia Pacific (Jakarta) | 1.100 |
| ap-southeast-4 | Asia Pacific (Melbourne) | 1.130 |
| ap-east-1 | Asia Pacific (Hong Kong) | 1.180 |

### 10.4 Middle East & Africa (AWS)

| Region | Label | Multiplier |
|---|---|---|
| me-south-1 | Middle East (Bahrain) | 1.150 |
| me-central-1 | Middle East (UAE) | 1.150 |
| af-south-1 | Africa (Cape Town) | 1.200 |
| il-central-1 | Israel (Tel Aviv) | 1.160 |

**Location:** [aws_pricer.py](aws_pricer.py#L23-L62)

### 10.5 GCP Regional Multipliers (vs. us-central1 = 1.000)

| Region | Label | Multiplier |
|---|---|---|
| us-central1 | US Central (Iowa) | 1.000 |
| us-east1 | US East (South Carolina) | 1.000 |
| us-east4 | US East (N. Virginia) | 1.010 |
| us-west2 | US West (Los Angeles) | 1.090 |
| us-west4 | US West (Las Vegas) | 1.040 |
| northamerica-northeast1 | Canada (Montréal) | 1.030 |
| southamerica-east1 | South America (São Paulo) | 1.210 |
| europe-west1 | Europe (Belgium) | 1.050 |
| europe-west2 | Europe (London) | 1.110 |
| europe-west3 | Europe (Frankfurt) | 1.100 |
| europe-west6 | Europe (Zurich) | 1.150 |
| asia-south1 | Asia Pacific (Mumbai) | 1.080 |
| asia-southeast1 | Asia Pacific (Singapore) | 1.100 |
| asia-northeast1 | Asia Pacific (Tokyo) | 1.130 |
| asia-northeast3 | Asia Pacific (Seoul) | 1.130 |
| australia-southeast1 | Asia Pacific (Sydney) | 1.140 |
| asia-east2 | Asia Pacific (Hong Kong) | 1.180 |
| me-west1 | Middle East (Tel Aviv) | 1.160 |
| me-central1 | Middle East (Doha) | 1.160 |
| me-central2 | Middle East (Dammam) | 1.160 |
| af-south1 | Africa (Johannesburg) | 1.200 |

**Location:** [gcp_pricer.py](gcp_pricer.py#L25-L76)

---

## Summary of Known Constraints & Open Items

### ✅ RESOLVED: DB Node Machine Sizing (June 2026)
- **Previous State:** Primary DB nodes always hardcoded to `32 vCPU / 128 GB` regardless of actual requirements
- **Fix Applied:** `_db_nodes()` now reads `postgres_ram_gb` (or oracle/sql_server), divides by 2 nodes, applies 1.5× headroom, and snaps to the nearest memory tier
- **Impact:** Correctly prices smaller configs (e.g., 56 GB total → 16vCPU/64GB per node, not 32vCPU/128GB)

### ⚠️ Issue 1: No Reserved Instance Discounts Applied
- **Current State:** All node distribution marked as "Reserved 3 Yr" but pricing uses On-Demand rates
- **Impact:** Estimates are 30-60% **higher** than what customers would actually pay with RIs
- **Recommendation:** Implement RI discount multipliers (e.g., 0.35-0.40 for 3-year reserved)

### ⚠️ Issue 2: Hardcoded Inflation Rate (4%)
- **Current State:** Fixed 4% annually applied uniformly across all services
- **Impact:** May not reflect actual AWS pricing trends (historically 2-6% per service)
- **Recommendation:** Make configurable per service type (EC2 vs. Storage vs. Managed Services)

### ⚠️ Issue 3: Environment Scaling Not Flexible
- **Current State:** DR compute = user-selected 50% or 100%; Pre-Prod = 40% (hardcoded `PREPROD_SCALE`)
- **Impact:** Pre-Prod scale cannot be adjusted without code change
- **Recommendation:** Add UI control for Pre-Prod scale factor

### ⚠️ Issue 4: Rule-Based Node Distribution Ratios (45%, 22%, 22%)
- **Current State:** Hardcoded percentage allocations for each workload role; LLM can adjust but uses same baseline
- **Impact:** May not match actual customer workload profiles
- **Recommendation:** Allow ratio customization in UI as an advanced option

### ⚠️ Issue 5: Storage Per Node Not Configurable
- **Current State:** Worker storage = 256 GB (production), 128 GB (pilot-light DR); fixed
- **Recommendation:** Derive from `data_size_gb / total_worker_nodes` or expose as UI input

### ℹ️ Note: Fallback Pricing Vintage
- **Current State:** Marked "March 2026 estimates"
- **Recommendation:** Auto-refresh fallback pricing quarterly

---

## Configuration Recommendations

To make the platform more flexible and less hardcode-heavy, consider:

1. **Create a `CONFIG.yaml` or similar file** for all constants
2. **Database-backed settings** for each client (allow overrides)
3. **Admin UI** to adjust inflation rates, environment scales, RI discounts
4. **Audit trail** logging when constants are changed (for compliance)
5. **API call** to fetch latest AWS/GCP pricing at estimate generation time (not just fallback)

---

## 11. AI Services Infrastructure Constants

Source: `MayBank Hardware Sizing - AI.xlsx` (8 sheets)
Module: `ai_sizer.py`

### 11.1 Kubernetes Cluster Configurations (per AI type × environment)

| AI Type | Environment | Worker Nodes | Cores/Node | RAM/Node (GB) | Storage/Node (GB) | Total Cores | Total RAM | Total Storage |
|---|---|---|---|---|---|---|---|---|
| **Agentic AI** | Production | 9 | 16 | 32 | 1,024 | 144 | 288 GB | 9,216 GB |
| **Agentic AI** | UAT / Pre-Prod | 5 | 16 | 32 | 800 | 80 | 160 GB | 4,000 GB |
| **Agentic AI** | Training | 5 | 16 | 32 | 800 | 80 | 160 GB | 4,000 GB |
| **Agentic AI** | DR (100%) | 9 | 16 | 32 | 1,024 | 144 | 288 GB | 9,216 GB |
| **Agentic AI** | DR (50%) | 5 | 16 | 32 | 800 | 80 | 160 GB | 4,000 GB |
| **Predictive AI** | Production | 2 | 8 | 16 | 250 | 16 | 32 GB | 500 GB |
| **Predictive AI** | UAT / Pre-Prod | 2 | 8 | 16 | 250 | 16 | 32 GB | 500 GB |
| **Predictive AI** | Training | 4 | 16 | 32 | 500 | 64 | 128 GB | 2,000 GB |
| **GenAI** | Production | 2 | 16 | 32 | 200 | 32 | 64 GB | 400 GB |
| **GenAI** | UAT / Pre-Prod | 2 | 8 | 16 | 200 | 16 | 32 GB | 400 GB |
| **GenAI** | Training | 2 | 8 | 16 | 200 | 16 | 32 GB | 400 GB |

**Source sheets:** Agentic AI Prod, Agentic AI UAT, Predictive Prod, Predictive Training Env, GenAi Prod, GenAi Training

### 11.2 Service Pod Requirements (Production Baseline)

#### Agentic AI Services (Production)

| Service | Category | CPU/Pod | RAM/Pod (GB) | Pods (Prod) | Pods (UAT) | Total CPU (Prod) | Total RAM (Prod) | Storage |
|---|---|---|---|---|---|---|---|---|
| Minio | Common | 2 | 4 | 4 | 4 | 8 | 16 GB | 200 GB |
| Config-service | Common | 2 | 4 | 4 | 2 | 8 | 16 GB | — |
| MCP Server | Common | 2 | 4 | 4 | 2 | 8 | 16 GB | — |
| businessnext-crmmeta | Agent | 2 | 4 | 4 | 2 | 8 | 16 GB | — |
| businessnext-runtime | Agent | 2 | 4 | 4 | 2 | 8 | 16 GB | — |
| businessnext-sessionmanager | Agent | 2 | 4 | 4 | 2 | 8 | 16 GB | — |
| **Agent Hub** | Agent | 8 | 12 | **8** | 3 | **64** | **96 GB** | — |
| **datanext-guardrails-service** | Agent | 4 | 8 | **6** | 3 | **24** | **48 GB** | — |

#### Predictive AI Services (Production)

| Service | Category | CPU/Pod | RAM/Pod (GB) | Pods | Total CPU | Total RAM | Storage |
|---|---|---|---|---|---|---|---|
| Minio | Common | 2 | 4 | 2 | 4 | 8 GB | 400 GB |
| AI Evaluator | Predictive | 2 | 4 | 3 | 6 | 12 GB | — |

#### Predictive AI Services (Training)

| Service | Category | CPU/Pod | RAM/Pod (GB) | Pods | Total CPU | Total RAM | Storage |
|---|---|---|---|---|---|---|---|
| Config-service | Data Platform | 1 | 2 | 1 | 1 | 2 GB | — |
| Dataflowengine | Data Platform | 2 | 4 | 1 | 2 | 4 GB | — |
| Datastore | Data Platform | 1 | 2 | 1 | 1 | 2 GB | — |
| Runtime | Data Platform | 1 | 2 | 1 | 1 | 2 GB | — |
| Scheduler | Data Platform | 1 | 2 | 1 | 1 | 2 GB | — |
| Apache Spark (Job Manager) | Data Platform | 1 | 2 | 1 | 1 | 2 GB | — |
| **Apache Spark (Worker Node)** | Data Platform | 8 | 16 | **3** | **24** | **48 GB** | — |
| Minio | Predictive+DataPlatform | 4 | 8 | 1 | 4 | 8 GB | 400 GB |
| Hive Meta Store | Data Platform | 2 | 4 | 1 | 2 | 4 GB | — |
| Trino Master | Data Platform | 1 | 2 | 1 | 1 | 2 GB | — |
| Trino Worker | Data Platform | 4 | 8 | 2 | 8 | 16 GB | — |
| AI Trainer | Predictive | 8 | 16 | 2 | 16 | 32 GB | — |
| AI Evaluator | Predictive | 2 | 4 | 1 | 2 | 4 GB | — |

#### GenAI Services (Production)

| Service | Category | CPU/Pod | RAM/Pod (GB) | Pods | Total CPU | Total RAM | Storage |
|---|---|---|---|---|---|---|---|
| Minio | Common | 2 | 4 | 2 | 4 | 8 GB | 500 GB |
| Config-service | Common | 1 | 2 | 3 | 3 | 6 GB | — |
| Datanext GenAI | Worknext | 4 | 8 | 4 | 16 | 32 GB | — |

### 11.3 Database Constants

| Constant | Value | Source Sheet | Notes |
|---|---|---|---|
| `MILVUS_PODS` | 3 | Agentic AI UAT + Prod | Vector DB pod count (same in UAT and Prod) |
| `MILVUS_CPU_PER_POD` | 8 | Template | Vector DB CPU per pod |
| `MILVUS_RAM_PER_POD` | 16 GB | Template | Vector DB RAM per pod |
| `MILVUS_TOTAL_RAM` | 48 GB | Calculated | 3 × 16 GB |
| `MILVUS_TOTAL_CPU` | 24 | Calculated | 3 × 8 |
| `MILVUS_STORAGE_GB` | 200 GB | Template | Persistent storage for Milvus |
| `CRM_DB_STORAGE_PROD` | 800 GB | Agentic AI Prod | CRM SQL DB storage (production) |
| `CRM_DB_STORAGE_UAT` | 500 GB | Agentic AI UAT | CRM SQL DB storage (UAT) |
| `CRM_DB_STORAGE_TRAINING` | 100 GB | GenAI/Predictive Training | Minimal training DB storage |
| GenAI CRM DB (Prod) | 300 GB | GenAI Prod sheet | GenAI production CRM DB |

### 11.4 Bedrock & GPU Constants

| Constant | Value | Notes |
|---|---|---|
| `BEDROCK_MONTHLY_DEFAULT` | $3,000 | User-adjustable; default for Bedrock LLM API monthly cost |
| GPU Hardware | None | All LLM inference via AWS Bedrock — no self-hosted GPU nodes |
| GPU Model | Bedrock (Managed) | AWS manages GPU infrastructure; billing is token-based |

### 11.5 Environment Scaling Ratios (AI Services)

| Environment | Scale vs Prod | Basis |
|---|---|---|
| **Production** | 1.0× | Full template spec |
| **UAT / Pre-Prod** | ~0.55× | 5/9 nodes for Agentic; same for Predictive |
| **Training** | ~0.44× | 4/9 nodes (Predictive heavy — Spark cluster); 2 nodes (GenAI) |
| **DR (100%)** | 1.0× | Full production mirror |
| **DR (50%)** | ~0.55× | Pilot-light — matches UAT footprint |

### 11.6 Pricing Estimates (AI Workbook — SaaS Only)

Approximate on-demand EC2 hourly rates used in `_build_ai_pricing_sheet()`:

| AI Type | Environment | Instance Family | Hourly Rate |
|---|---|---|---|
| Agentic AI | Prod / DR-Full | m5.4xlarge (16 vCPU) | $0.768/hr |
| Agentic AI | UAT / DR-Half | m5.4xlarge (16 vCPU) | $0.768/hr |
| Predictive AI | Prod / UAT | m5.2xlarge (8 vCPU) | $0.384/hr |
| Predictive AI | Training | m5.4xlarge (16 vCPU) | $0.768/hr |
| GenAI | Prod / DR-Full | m5.4xlarge (16 vCPU) | $0.768/hr |
| GenAI | UAT / Training / DR-Half | m5.2xlarge (8 vCPU) | $0.384/hr |

Storage: EBS GP3 at $0.08/GB/month · Inflation: 4%/year (same as platform default)

---

## 11. Excel Export Architecture

As of the recent reporting refactor, the platform generates three distinct Excel workbooks to separate infrastructure specifications from financial forecasting.

| Workbook | Output File | Purpose | Contents |
|---|---|---|---|
| **1. User Template** | `updated_estimate.xlsx` | Raw recalculation | Original macro-enabled sizing template populated with user inputs (users, growth, etc.) |
| **2. Cloud Sizing** | `cloud_sizing.xlsx` | Infrastructure specs (No Pricing) | Prod Sizing, Pre-Prod Sizing, DR Sizing, ClickHouse Sizing, AI Sizing |
| **3. Cloud Pricing** | `cloud_pricing.xlsx` | Financial forecasts (SaaS only) | Pricing Summary, Prod Pricing, Pre-Prod Pricing, DR Pricing, PUPM, AWS/GCP comparisons |

**Key Design Decisions:**
- **Strict Separation:** `cloud_sizing.xlsx` contains zero pricing data, making it suitable for client IT departments to review infrastructure requirements without seeing financial data.
- **Sizing Standardization:** All sizing sheets share a standardized column set: `Category | Role | Nodes | Instance Type | vCPU (Per Node) | RAM (Per Node) | Storage (GB)`.
- **Pricing Aggregation:** The `Pricing Summary` sheet provides a cumulative dashboard of all selected environments and AI components.

**Location:** `excel_exporter.py`

---

**Document End**
