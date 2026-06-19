# Intelligent BusinessNext AWS Cost Estimation Platform
## Proposal & Architecture Overview

**An Automated, Formula-Driven, Streamlit + LLM-Powered Cloud Costing Solution with Built-in AI Chatbot**

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Problem Statement](#2-problem-statement)
3. [Current Workflow — What You Already Have](#3-current-workflow--what-you-already-have)
4. [Intelligent Features Already Integrated](#4-intelligent-features-already-integrated)
5. [Core Architecture — Step by Step](#5-core-architecture--step-by-step)
6. [Professional Outputs](#6-professional-outputs)
7. [Key Benefits](#7-key-benefits)
8. [Future Enhancements Roadmap](#8-future-enhancements-roadmap)
9. [Conclusion](#9-conclusion)

---

## 1. Executive Summary

This document presents the **Intelligent BusinessNext Cost Estimation Platform** — a fully automated, intelligent system that combines a modern Streamlit web interface, real-time cloud pricing APIs, PostgreSQL persistence, LLM-powered node sizing, and an **integrated AI Chatbot** for interactive "what-if" analysis.

The platform:

- Accepts inputs via a clean, user-friendly web UI
- Reads and fully recalculates your `Sizing_Template.xlsx` automatically
- Extracts key metrics (S3 size, data size, vCPUs, RAM, storage, etc.)
- Uses an LLM to intelligently recommend optimal node distribution and instance types
- Calculates accurate monthly pricing using live AWS and GCP Pricing API data
- Prices additional environments (Dev, QA, DR, UAT, etc.) automatically
- Generates inflation-adjusted 1-year, 3-year, and 5-year cost forecasts
- Provides an **AI Chatbot** that answers "what-if" questions and explains every number
- Exports professional Excel and PDF reports with full cost breakdowns

---

## 2. Problem Statement

Cloud cost estimation for enterprise platforms like BusinessNext is a complex, multi-layered challenge:

- **Manual Excel maintenance** is error-prone and time-consuming — any change to inputs cascades through hundreds of formulas that must be re-evaluated by hand.
- **Pricing volatility** means AWS instance costs change frequently; static spreadsheets quickly become inaccurate.
- **Multi-cloud complexity** — comparing AWS vs. GCP deployments requires separate calculations that are hard to reconcile.
- **Environment sprawl** — estimating costs for Production, Dev, QA, UAT, and DR environments separately is repetitive and inconsistent.
- **Communication gap** — stakeholders cannot ask ad-hoc questions about costs or explore "what-if" scenarios without involving a technical team member.
- **No audit trail** — estimates are created, modified, and shared informally with no structured version history per client.

A purpose-built, intelligent estimation platform eliminates all of these pain points.

---

## 3. Current Workflow — What You Already Have

The existing workflow begins with a **Sizing Template (`Sizing_Template.xlsx`)** — a detailed Excel workbook containing complex formulas that model the BusinessNext infrastructure stack.

**Current manual steps:**
1. Open the Excel file
2. Manually enter customer-specific parameters (number of users, transaction volume, module selection, DB type, etc.)
3. Wait for Excel to recalculate hundreds of interdependent formulas
4. Extract key metrics manually (vCPUs, RAM, storage, node counts)
5. Cross-reference with AWS pricing pages (manually) to compute cost estimates
6. Repeat for each environment (Production, Dev, QA, DR...)
7. Build a Word or PowerPoint presentation from scratch for the client
8. Re-do everything if any input changes

This process is **slow, inconsistent, and not scalable** across multiple clients and sales cycles.

---

## 4. Intelligent Features Already Integrated

The following capabilities are **live in the platform today**:

### 🔐 Authentication & Client Management
- Secure login with email + password (bcrypt-hashed credentials in PostgreSQL)
- Multi-client support: create, manage, and delete client profiles
- Each client has an isolated estimate history with full versioning

### 📊 Excel Auto-Recalculation
- Upload or use the pre-configured `Sizing_Template.xlsx`
- Platform writes your input parameters directly into the Excel file using `openpyxl`
- Triggers full formula recalculation (via LibreOffice headless) — no need to open Excel manually
- Extracts all derived metrics automatically: worker nodes, vCPUs, RAM, storage, DB RAM, S3 size

### 🤖 LLM-Powered Node Distribution
- Extracted metrics are passed to an LLM (via the `node_distributor` module)
- The LLM recommends the optimal distribution of workloads across AWS EC2 instance families
- Produces a structured node plan: instance type, quantity, vCPUs per node, RAM per node
- Handles both **SaaS (PostgreSQL)** and **On-Premise** deployment modes

### ☁️ Real-Time AWS Pricing
- Fetches live pricing from the **AWS Pricing API** (`aws_pricer` module)
- Supports all major AWS regions (us-east-1, ap-south-1, eu-west-1, etc.)
- Calculates On-Demand and Reserved Instance pricing for EC2, RDS, EBS, S3, CloudWatch
- Produces itemized monthly and annual cost breakdowns

### 🌐 GCP Pricing & Multi-Cloud Comparison
- Mirrors the AWS pricing flow for **Google Cloud Platform** (`gcp_pricer` module)
- Supports major GCP regions
- Builds a side-by-side **AWS vs. GCP comparison** with cost delta and recommendations

### 🌍 Multi-Environment Pricing
- Automatically prices additional environments beyond Production:
  - Development, QA, UAT, Staging, DR (Disaster Recovery)
- Each environment applies configurable resource multipliers
- Consolidated view of total infrastructure cost across all environments (`env_pricer` module)

### 📈 Inflation-Adjusted Forecasting
- Calculates projected costs over 1, 3, and 5 years
- Applies configurable annual inflation / AWS pricing drift rates
- Visual forecast charts rendered in the UI

### 💬 AI Chatbot
- Integrated conversational AI (`chatbot` module) embedded directly in the Estimator page
- Answers questions like:
  - *"Why is the DR environment costing more than QA?"*
  - *"What happens if we switch from PostgreSQL to SQL Server?"*
  - *"Can we reduce cost by using Reserved Instances?"*
- Contextually aware — has full access to the current estimate's numbers

### 💾 PostgreSQL Persistence
- All estimates are saved to a PostgreSQL database (`database` module using SQLAlchemy)
- Stores: client info, input parameters, computed metrics, pricing results, file paths
- Full estimate history per client with version tracking
- Estimate files (Excel, PDF) stored and retrievable from the Estimates page

---

## 5. Core Architecture — Step by Step

```
┌─────────────────────────────────────────────────────────────────────┐
│                    BusinessNext Cost Estimator                      │
│                     (Streamlit Web Application)                     │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
          ┌────────────────▼────────────────┐
          │           app.py                │
          │    Login + Session Management   │
          │    (bcrypt auth, PostgreSQL)     │
          └────────────────┬────────────────┘
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
┌───────▼──────┐  ┌────────▼───────┐  ┌───────▼──────────┐
│   Clients    │  │   Estimates    │  │    Estimator     │
│  (page 1)    │  │   (page 2)     │  │    (page 3)      │
│              │  │                │  │                  │
│ Client CRUD  │  │ History View   │  │ Core Engine      │
│ Hover Cards  │  │ Load/Compare   │  │ (Full Flow)      │
└──────────────┘  └────────────────┘  └───────┬──────────┘
                                              │
              ┌───────────────────────────────▼───────────────────────┐
              │                  Estimator Engine                      │
              ├────────────────┬────────────────┬──────────────────────┤
              │  excel_handler │ node_distribut │    aws_pricer        │
              │  ─────────────  ─────────────── │    gcp_pricer        │
              │  Write inputs  │ LLM node plan  │    env_pricer        │
              │  Recalculate   │ Instance types │    (live pricing)    │
              │  Extract KPIs  │                │                      │
              └────────────────┴────────────────┴──────────────────────┘
                           │                              │
              ┌────────────▼──────────┐   ┌──────────────▼────────────┐
              │    excel_exporter     │   │       pdf_report           │
              │    ───────────────    │   │       ──────────           │
              │  Cloud Sizing .xlsx   │   │  Professional PDF          │
              │  AWS Pricing  .xlsx   │   │  with charts & tables      │
              └───────────────────────┘   └────────────────────────────┘
                           │
              ┌────────────▼──────────────────────────────────────────┐
              │                   PostgreSQL Database                  │
              │          (clients, estimates, files, users)            │
              └───────────────────────────────────────────────────────┘
                           │
              ┌────────────▼──────────────────────────────────────────┐
              │                     AI Chatbot                        │
              │         (LLM with full estimate context)               │
              └───────────────────────────────────────────────────────┘
```

### Step-by-Step Flow

| Step | Action | Module |
|---|---|---|
| 1 | User logs in | `app.py` + `database.py` |
| 2 | Select / create a client | `1_Clients.py` |
| 3 | Enter sizing parameters (users, modules, DB type, region) | `3_Estimator.py` |
| 4 | Platform writes parameters into Excel template | `excel_handler.py` |
| 5 | Excel recalculates via LibreOffice headless | `excel_handler.py` |
| 6 | Key metrics extracted from workbook | `excel_handler.py` |
| 7 | LLM distributes workload across instance types | `node_distributor.py` |
| 8 | Live AWS pricing fetched and applied | `aws_pricer.py` |
| 9 | Live GCP pricing fetched and compared | `gcp_pricer.py` |
| 10 | Additional environment costs calculated | `env_pricer.py` |
| 11 | Inflation-adjusted forecast computed | `3_Estimator.py` |
| 12 | Excel reports generated (Cloud Sizing, Cloud Pricing, Updated Estimate) | `excel_exporter.py` |
| 13 | PDF report generated | `pdf_report.py` |
| 14 | Estimate saved to PostgreSQL | `database.py` |
| 15 | AI Chatbot available for Q&A | `chatbot.py` |

---

## 6. Professional Outputs

The platform generates two categories of deliverables:

### 📁 Excel Reports
| Report | Contents |
|---|---|
| **Original Estimate Form** (`updated_estimate.xlsx`) | The original user input Excel form, pre-filled and recalculated. |
| **Cloud Sizing Report** (`cloud_sizing.xlsx`) | Pure infrastructure specifications without pricing. Includes worker node specs, vCPU & RAM distribution, storage plan, DB sizing, and per-environment resource tables. |
| **Pricing Report** (`cloud_pricing.xlsx`) | Itemized financial breakdown for all environments. Includes EC2, RDS, EBS, S3 costs; monthly/annual/5-year totals; and AI service pricing. |

### 📄 PDF Report
A fully formatted PDF (`<client>_CostEstimate.pdf`) including:
- Executive summary with total cost highlight
- Infrastructure sizing overview
- AWS vs GCP comparison chart
- Environment breakdown table
- Inflation-adjusted forecast graph
- Methodology notes and assumptions

---

## 7. Key Benefits

| Benefit | Details |
|---|---|
| ⚡ **Speed** | Full estimate generated in under 2 minutes vs. hours of manual work |
| 🎯 **Accuracy** | Live API pricing eliminates stale spreadsheet data |
| 🔄 **Repeatability** | Any parameter change triggers a clean, full recalculation |
| 👥 **Multi-Client** | Unlimited clients, each with full estimate version history |
| ☁️ **Multi-Cloud** | AWS and GCP side-by-side with cost delta |
| 🌍 **Multi-Environment** | Production + Dev + QA + UAT + DR — all automatically priced |
| 🧠 **Intelligent Sizing** | Auto-selects optimal VM instance families (preferring AMD memory-optimized) while minimizing costly memory over-provisioning via a dynamic CPU compromise logic |
| 📊 **Professional Reports** | Client-ready Excel and PDF outputs, no manual formatting |
| 💬 **AI Chatbot** | Stakeholders can self-serve with "what-if" questions |
| 🔐 **Secure** | Role-based login, bcrypt hashing, session management |
| 📈 **Forecasting** | 1/3/5-year inflation-adjusted projections for budgeting |

---

## 8. Future Enhancements Roadmap

### Near-Term (0–3 months)
- [ ] **Azure pricing** — add a third cloud provider comparison
- [ ] **Saved comparison snapshots** — compare two estimates side-by-side
- [ ] **Email delivery** — auto-email generated reports to stakeholders
- [ ] **Draft / Approved status** on estimates for workflow control

### Mid-Term (3–6 months)
- [ ] **Custom instance catalog** — allow administrators to define preferred instance families
- [ ] **Bulk import** — upload a CSV of clients and batch-generate estimates
- [ ] **Shared links** — generate a read-only shareable URL for a specific estimate
- [ ] **Slack / Teams integration** — notify teams when a new estimate is created

### Long-Term (6–12 months)
- [ ] **Actual vs. Estimated reconciliation** — import real AWS bills and compare to estimates
- [ ] **ML-based pricing prediction** — predict future AWS price changes using historical trends
- [ ] **Multi-user collaboration** — multiple users can comment and annotate on an estimate
- [ ] **White-label theming** — per-client branded PDF and Excel output

---

## 9. Conclusion

The **BusinessNext Intelligent AWS Cost Estimation Platform** transforms what was a manual, error-prone, multi-hour process into a fully automated, repeatable, and auditable workflow — all delivered through a clean, modern web interface.

By combining:
- **Streamlit** for a fast, browser-based UI
- **Excel recalculation** to preserve your existing formula investment
- **LLM-powered node distribution** for intelligent sizing
- **Live AWS & GCP Pricing APIs** for always-accurate costs
- **PostgreSQL** for structured client and estimate persistence
- **AI Chatbot** for interactive stakeholder Q&A
- **Professional report generation** (Excel + PDF)

…the platform empowers the BusinessNext pre-sales and solutions engineering teams to deliver accurate, credible, and visually polished cost proposals — in minutes, not days.

---

*Document last updated: March 2026*
*Platform: BusinessNext Cost Estimator v1.0*
*Built with: Python 3.12 · Streamlit · PostgreSQL · SQLAlchemy · OpenPyXL · LibreOffice Headless*
