# Hardcoded Constants & Configuration Values Used in Sizing and Pricing

**Purpose:** This document lists all the constant values and hardcoded ratios/multipliers used throughout the estimation platform to help identify inconsistencies and clarify pricing assumptions.

**Last Updated:** April 16, 2026

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

---

## 1. General Infrastructure Constants

| Constant | Value | Module | Purpose |
|----------|-------|--------|---------|
| `HOURS_PER_MONTH` | `730` | aws_pricer.py, env_pricer.py, gcp_pricer.py | Convert hourly rates to monthly (365 days × 24 hrs / 12 months) |

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

| Role | Base Ratio | Min Nodes | vCPU/Node | RAM/Node | Storage/Node | Instance Family | Reserved? |
|---|---|---|---|---|---|---|---|
| **web_mobile_webapi** | `0.45` (45%) | 2 | 16 | 32 GB | 256 GB | Compute Intensive | 3-Year RI |
| **graphana_prometheus** | `0.22` (22%) | 1 | 8 | 16 GB | 512 GB | Compute Intensive | 3-Year RI |
| **efk_logging** | `0.22` (22%) | 1 | 8 | 16 GB | 1024 GB | Compute Intensive | 3-Year RI |

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
| **Bastion Host** | 1 | 2 | 4 GB | 300 GB | General Purpose | SSH access gateway |
| **NAT Gateway** | 2 | 0 | 0 | 0 | NAT | One per Availability Zone |
| **ECR (Image Registry)** | 1 | 0 | 0 | 512 GB | Managed Service | Container image storage |
| **Backup Storage** | 1 | 0 | 0 | 5120 GB | Cloud Storage | DB & infrastructure logs backup |

**Location:** [node_distributor.py](node_distributor.py#L85-L127)

---

## 4. AWS EC2 Pricing Constants

### 4.1 Hourly Pricing Fallback (On-Demand, USD/hr)

These values are used when the AWS Pricing API is unavailable. **Last updated March 2026** and should be regularly verified.

| Instance Type | Hourly Rate (USD) | Category |
|---|---|---|
| **General Purpose** | | |
| t3.medium | $0.0416 | Burstable |
| m5.large | $0.096 | General |
| m5.xlarge | $0.192 | General |
| m5.2xlarge | $0.384 | General |
| m5.4xlarge | $0.768 | General |
| m5.8xlarge | $1.536 | General |
| m5.12xlarge | $2.304 | General |
| **Memory Optimized** | | |
| r5.large | $0.126 | Memory |
| r5.xlarge | $0.252 | Memory |
| r5.2xlarge | $0.504 | Memory |
| r5.4xlarge | $1.008 | Memory |
| r5.8xlarge | $2.016 | Memory |
| r5.12xlarge | $3.024 | Memory |
| r5.16xlarge | $4.032 | Memory |
| **ElastiCache** | | |
| cache.r6g.large | $0.166 | Redis |
| cache.r6g.xlarge | $0.332 | Redis |
| cache.r6g.2xlarge | $0.665 | Redis |

**Location:** [aws_pricer.py](aws_pricer.py#L78-L95)

### 4.2 Storage Pricing (On-Demand, Monthly)

| Service | Unit | Rate | Notes |
|---|---|---|---|
| **S3 Standard** | per GB/month | $0.023 | General purpose storage |
| **EBS GP3** | per GB/month | $0.08 | General-purpose SSD storage per node |
| **EBS IO2** | per GB/month | $0.125 | High IOPS SAN equivalent storage |

**Location:** [aws_pricer.py](aws_pricer.py#L97-L100)

### 4.3 Network & Managed Services (Monthly)

| Service | Cost | Notes |
|---|---|---|
| **Application Load Balancer (ALB)** | $16.43 | Base monthly cost (fixed) |
| **NAT Gateway** | $0.045 per GB + $32.00 base | Data processed + hourly charge |
| **CloudWatch** | $3.50 per node + $10.00 base | Monitoring per node |
| **EKS (Managed Kubernetes)** | $73.00 | Control plane monthly cost |

**Location:** [aws_pricer.py](aws_pricer.py#L100-L105)

### 4.4 EC2 Instance Selection Rules

When determining the best instance type for a given workload (vCPU + RAM), the system uses:

```python
ram_to_vcpu_ratio = ram_gb / vcpu

if ram_to_vcpu_ratio > 8:
    family = "r5"  # Memory-optimized
else:
    family = "m5"  # General-purpose compute
```

Then matches against predefined sizes:

| vCPU | RAM | Instance | 
|---|---|---|
| 2 | 8 GB | .large |
| 4 | 16 GB | .xlarge |
| 8 | 32 GB | .2xlarge |
| 16 | 64 GB | .4xlarge |
| 32 | 128 GB | .8xlarge |
| 48 | 192 GB | .12xlarge |
| 64 | 256 GB | .16xlarge |

**Location:** [aws_pricer.py](aws_pricer.py#L104-L120)

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

### 6.1 GCP Fallback Pricing (USD/month)

These are hardcoded fallback values used when GCP Pricing API is unavailable.

| Instance Type | Monthly Cost | Purpose |
|---|---|---|
| n2-standard-4 | $112.00 | General compute |
| n2-standard-8 | $224.00 | General compute |
| n2-highmem-8 | $256.00 | Memory-optimized |
| n2-highmem-16 | $512.00 | Memory-optimized |

**Location:** [gcp_pricer.py](gcp_pricer.py#L40-L65)

### 6.2 GCP Storage Pricing (USD/month per GB)

| Storage Type | Rate | Notes |
|---|---|---|
| **Standard Storage** | $0.020 | General purpose |
| **SSD Persistent Disk** | $0.170 | High performance |
| **Cloud SQL Storage** | $0.17 per GB | Relational DB storage |

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

### 8.1 DB Instance Selection (Postgres/Oracle/SQL Server)

When sizing database servers, the system uses:

```python
db_vcpu = max(4, prod_db_ram // 4)  # 1 vCPU per 4 GB RAM (minimum 4 vCPU)
```

For multi-AZ deployments:
```python
env_db_nodes = 2 if not single_az else 1
```

### 8.2 Environment DB Sizing (Pre-Prod/DR)

| Parameter | Formula | Min Value |
|---|---|---|
| **DB RAM** | `ceil(prod_db_ram × scale / 8) × 8` | 32 GB |
| **DB vCPU** | `ceil(prod_db_vcpu × scale / 2) × 2` | 4 vCPU |

Example (DR with scale=0.60):
- Production DB: 128 GB RAM, 32 vCPU
- DR DB RAM: ceil(128 × 0.60 / 8) × 8 = ceil(9.6) × 8 = **80 GB**
- DR DB vCPU: ceil(32 × 0.60 / 2) × 2 = ceil(9.6) × 2 = **20 vCPU**

**Location:** [env_pricer.py](env_pricer.py#L155-L162)

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

| Storage Type | Pre-Prod Scale | DR Scale | Minimum |
|---|---|---|---|
| **Worker Node Storage** | 300 GB | 256 GB | – |
| **Data Storage (EBS)** | `max(300, ceil(prod_data × 0.40))` | `max(300, ceil(prod_data × 0.60))` | 300 GB |
| **S3 Storage** | `max(500, ceil(prod_s3 × 0.40))` | `max(500, ceil(prod_s3 × 0.60))` | 500 GB |

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

### 10.4 Middle East & Africa

| Region | Label | Multiplier |
|---|---|---|
| me-south-1 | Middle East (Bahrain) | 1.150 |
| me-central-1 | Middle East (UAE) | 1.150 |
| af-south-1 | Africa (Cape Town) | 1.200 |
| il-central-1 | Israel (Tel Aviv) | 1.160 |

**Location:** [aws_pricer.py](aws_pricer.py#L23-L57)

---

## Summary of Common Inconsistencies Found

### ⚠️ Issue 1: No Reserved Instance Discounts Applied
- **Current State:** All node distribution marked as "Reserved 3 Yr" but pricing uses On-Demand rates
- **Impact:** Estimates are 30-60% **higher** than what customers would actually pay with RIs
- **Recommendation:** Implement RI discount multipliers (e.g., 0.35-0.40 for 3-year reserved)

### ⚠️ Issue 2: Hardcoded Inflation Rate (4%)
- **Current State:** Fixed 4% annually applied uniformly across all services
- **Impact:** May not reflect actual AWS pricing trends (historically 2-6% per service)
- **Recommendation:** Make configurable per service type (EC2 vs. Storage vs. Managed Services)

### ⚠️ Issue 3: Environment Scaling Not Flexible
- **Current State:** DR = 60%, Pre-Prod = 40% (hardcoded)
- **Impact:** Cannot accommodate different enterprise policies (e.g., "DR must be 100%", or "no Pre-Prod environment")
- **Recommendation:** Add UI controls to adjust environment scaling factors per estimate

### ⚠️ Issue 4: Rule-Based Node Distribution Ratios (45%, 22%, 22%)
- **Current State:** Hardcoded percentage allocations for each workload role
- **Impact:** May not match actual customer workload profiles
- **Recommendation:** Add optional LLM-based adjustment or allow ratio customization in UI

### ⚠️ Issue 5: Storage Per Node Values Not Configurable
- **Current State:** Worker storage = 256GB fixed; Pre-Prod worker storage = 300GB
- **Impact:** Doesn't scale with actual customer data volumes
- **Recommendation:** Derive storage per node from data_size_gb and total worker nodes

### ⚠️ Issue 6: Fallback Pricing is Outdated
- **Current State:** Marked "March 2026 estimates" — may drift from real API prices
- **Impact:** Estimates inaccurate if API is down or for extended periods
- **Recommendation:** Auto-update fallback pricing monthly or make it configurable

---

## Configuration Recommendations

To make the platform more flexible and less hardcode-heavy, consider:

1. **Create a `CONFIG.yaml` or similar file** for all constants
2. **Database-backed settings** for each client (allow overrides)
3. **Admin UI** to adjust inflation rates, environment scales, RI discounts
4. **Audit trail** logging when constants are changed (for compliance)
5. **API call** to fetch latest AWS/GCP pricing at estimate generation time (not just fallback)

---

**Document End**
