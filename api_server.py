"""
api_server.py — FastAPI REST bridge for the BusinessNext Cost Estimator.

Runs alongside the existing Streamlit app (port 8501) on port 8000.
Exposes:
  • Auth / Users / Clients / Estimates CRUD  (unchanged)
  • POST /api/generate-estimate  — runs the full sizing pipeline and saves the result
"""
import os
import re
import glob
import zipfile
import io
import traceback
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, StreamingResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel

import database as db

load_dotenv()

# ── JWT config ────────────────────────────────────────────────────────────────
SECRET_KEY = os.getenv("JWT_SECRET", "businessnext-secret-key-change-in-production")
ALGORITHM = "HS256"
TOKEN_EXPIRE_HOURS = 24

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
bearer_scheme = HTTPBearer(auto_error=False)

# ── App setup ─────────────────────────────────────────────────────────────────
app = FastAPI(title="BusinessNext Cost Estimator API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Auth helpers ──────────────────────────────────────────────────────────────

def create_token(user: dict) -> str:
    payload = {
        "sub": str(user["id"]),
        "email": user["email"],
        "name": user.get("name", ""),
        "role": user.get("role", "viewer"),
        "exp": datetime.utcnow() + timedelta(hours=TOKEN_EXPIRE_HOURS),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme)) -> dict:
    if not credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return decode_token(credentials.credentials)


def require_admin(user: dict = Depends(get_current_user)) -> dict:
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


# ── Request/Response schemas ──────────────────────────────────────────────────

class LoginRequest(BaseModel):
    email: str
    password: str

class CreateUserRequest(BaseModel):
    email: str
    password: str
    name: Optional[str] = None
    role: str = "viewer"

class UpdateUserRequest(BaseModel):
    role: str
    name: Optional[str] = None

class ResetPasswordRequest(BaseModel):
    new_password: str

class CreateClientRequest(BaseModel):
    name: str
    sector: str = "Banking"


class GenerateEstimateRequest(BaseModel):
    # ── Identity ─────────────────────────────────────────────────────────────
    clientId:         Optional[str]  = None
    clientName:       str            = "Bank"
    deployment:       str            = "SaaS"       # "SaaS" | "On-Premise"
    database:         str            = "PostgreSQL"

    # ── Year-1 base values ────────────────────────────────────────────────────
    namedUsers:              int   = 15500
    concurrentUsers:         int   = 4650
    concurrentMobileUsers:   int   = 0
    totalCustomers:          int   = 25786541
    numberOfLeads:           int   = 10700000
    serviceRequests:         int   = 20000

    # ── YoY growth (as integer percent, e.g. 5 = 5%) ─────────────────────────
    namedUsersYoy:           int   = 5
    concurrentUsersYoy:      int   = 5
    concurrentMobileUsersYoy:int   = 5
    totalCustomersYoy:       int   = 10
    numberOfLeadsYoy:        int   = 10
    serviceRequestsYoy:      int   = 5

    # ── Modules & environments ────────────────────────────────────────────────
    modules:         List[str] = ["CRM", "Analytics", "AI"]
    environments:    List[str] = ["SIT", "UAT", "DR"]
    drScale:         int       = 100    # 50 or 100 (percent)

    # ── Advanced services ─────────────────────────────────────────────────────
    clickhouseEnabled: bool  = False
    aiServicesEnabled: bool  = False

    # ── AI workload configuration ─────────────────────────────────────────────
    predictiveAi:    bool       = False
    predictiveTokens:int        = 100000
    predictiveEnvs:  List[str]  = ["prod"]
    genaiAi:         bool       = False
    genaiTokens:     int        = 50000
    genaiEnvs:       List[str]  = ["prod"]
    agenticAi:       bool       = False
    agenticTasks:    int        = 1000
    agenticEnvs:     List[str]  = ["prod"]
    bedrockMonthly:  float      = 3000.0

    # ── Detailed sizing assumptions ───────────────────────────────────────────
    docsPerCustomer:  int   = 2
    docsPerLead:      int   = 2
    docsPerCase:      int   = 1
    actsPerCustomer:  int   = 2
    actsPerLead:      int   = 2
    actsPerCase:      int   = 4
    pdfPerUser:       int   = 1
    docSizeMb:        float = 0.25

    # ── Financial parameters ──────────────────────────────────────────────────
    discountPercent:  int   = 0
    inflationPercent: int   = 4
    contractDuration: str   = "3 Year"
    awsRegion:        str   = "ap-south-1"

    # ── Cloud provider selection (SaaS only) ──────────────────────────────────
    cloudProviders:   List[str] = ["AWS"]   # ["AWS"], ["GCP"], or ["AWS", "GCP"]

    # ── One-time costs ────────────────────────────────────────────────────────
    perfTestingCost:  int   = 5000
    migrationCost:    int   = 5000
    managedSvcCost:   int   = 1000

    # ── Estimate label / notes ────────────────────────────────────────────────
    estimateNotes:    str   = ""   # optional short description entered by user in Step 1


# ── Auth endpoints ────────────────────────────────────────────────────────────

@app.post("/api/auth/login")
def login(body: LoginRequest):
    user = db.verify_user(body.email, body.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token = create_token(user)
    return {"token": token, "user": user}


@app.get("/api/auth/me")
def get_me(current_user: dict = Depends(get_current_user)):
    return current_user


# ── User endpoints (admin only) ───────────────────────────────────────────────

@app.get("/api/users")
def list_users(admin: dict = Depends(require_admin)):
    users = db.get_all_users()
    # Sanitise: remove password_hash, format dates
    return [
        {
            "id": u["id"],
            "name": u["name"] or "",
            "email": u["email"],
            "role": u["role"],
            "created_at": u["created_at"].isoformat() if u.get("created_at") else None,
            "status": "Active",
            "lastLogin": "N/A",
        }
        for u in users
    ]


@app.post("/api/users", status_code=201)
def create_user(body: CreateUserRequest, admin: dict = Depends(require_admin)):
    try:
        user_id = db.create_user(body.email, body.password, body.name, body.role)
        return {"id": user_id, "message": "User created successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not create user: {str(e)}")


@app.put("/api/users/{user_id}")
def update_user(user_id: int, body: UpdateUserRequest, admin: dict = Depends(require_admin)):
    success = db.update_user(user_id, body.role, body.name)
    if not success:
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": "User updated successfully"}


@app.delete("/api/users/{user_id}")
def delete_user(user_id: int, admin: dict = Depends(require_admin)):
    # Prevent deleting self
    if str(user_id) == admin.get("sub"):
        raise HTTPException(status_code=400, detail="Cannot delete your own account")
    success = db.delete_user(user_id)
    if not success:
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": "User deleted successfully"}


@app.post("/api/users/{user_id}/reset-password")
def reset_password(user_id: int, body: ResetPasswordRequest, admin: dict = Depends(require_admin)):
    success = db.reset_user_password(user_id, body.new_password)
    if not success:
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": "Password reset successfully"}


# ── Client endpoints ──────────────────────────────────────────────────────────

def _format_client(c: dict) -> dict:
    """Normalise a DB client dict to match the frontend's expected shape."""
    created = c.get("created_at")
    created_str = created.strftime("%Y-%m-%d") if isinstance(created, datetime) else str(created or "")
    last_est = c.get("last_estimate")
    last_str = last_est.strftime("%d %b %Y") if isinstance(last_est, datetime) else "Never"
    initials = "".join(w[0] for w in (c.get("name") or "").split()[:2]).upper()
    colors = [
        "from-blue-500 to-blue-700",
        "from-violet-500 to-violet-700",
        "from-emerald-500 to-emerald-700",
        "from-pink-500 to-pink-700",
        "from-amber-500 to-amber-700",
        "from-orange-500 to-orange-700",
    ]
    color = colors[c["id"] % len(colors)]
    return {
        "id": str(c["id"]),
        "name": c["name"],
        "industry": c.get("sector", "General"),
        "createdAt": created_str,
        "estimateCount": c.get("estimate_count", 0),
        "lastActivity": last_str,
        "status": "active",
        "logo": initials or "?",
        "color": color,
    }


@app.get("/api/clients")
def list_clients(current_user: dict = Depends(get_current_user)):
    clients = db.get_all_clients()
    return [_format_client(c) for c in clients]


@app.post("/api/clients", status_code=201)
def create_client(body: CreateClientRequest, current_user: dict = Depends(get_current_user)):
    if current_user.get("role") not in ("admin", "estimator"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    try:
        client_id = db.create_client(body.name, body.sector)
        new = db.get_client_by_id(client_id)
        if new:
            # Augment with dummy count for immediate display
            new["estimate_count"] = 0
            new["last_estimate"] = None
        return _format_client({**(new or {}), "id": client_id, "estimate_count": 0, "last_estimate": None})
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/clients/{client_id}")
def get_client(client_id: int, current_user: dict = Depends(get_current_user)):
    c = db.get_client_by_id(client_id)
    if not c:
        raise HTTPException(status_code=404, detail="Client not found")
    c["estimate_count"] = 0
    c["last_estimate"] = None
    return _format_client(c)


@app.delete("/api/clients/{client_id}")
def delete_client(client_id: int, current_user: dict = Depends(get_current_user)):
    if current_user.get("role") not in ("admin",):
        raise HTTPException(status_code=403, detail="Admin access required to delete clients")
    success = db.delete_client(client_id)
    if not success:
        raise HTTPException(status_code=404, detail="Client not found")
    return {"message": "Client deleted successfully"}


# ── Estimate endpoints ────────────────────────────────────────────────────────

def _format_estimate(e: dict, client_name: str = "") -> dict:
    date = e.get("estimate_date") or e.get("created_at")
    date_str = date.strftime("%d %b %Y") if isinstance(date, datetime) else str(date or "")
    # Resolve customer name: prefer explicit client_name arg, then customer_name column, then fallback
    cust = client_name or e.get("customer_name") or e.get("client_name") or "Unknown Client"
    pricing = e.get("pricing_json") or {}
    gcp_monthly = pricing.get("gcp_monthly") or ((e.get("total_monthly_usd") or 0) * 0.88)
    aws5y = e.get("total_5year_usd") or round((e.get("total_monthly_usd") or 0) * 12 * 5.633, 2)
    return {
        "id": str(e["id"]),
        "version": f"V{e.get('version', 1)}",
        "customerName": cust,
        "name": f"{e.get('client_mode', 'SaaS').upper()} – {date_str}",
        "deployment": "SaaS" if (e.get("client_mode") or "saas").lower() == "saas" else "On-Premise",
        "clientMode": e.get("client_mode", "saas"),
        "date": date_str,
        "generatedAt": date_str,
        "awsMonthlyCost": e.get("total_monthly_usd") or 0,
        "gcpMonthlyCost": gcp_monthly,
        "aws5YearTCO": aws5y,
        "status": "Completed",
        "dbType": e.get("db_type", "PostgreSQL"),
        "years": e.get("years", 3),
        "notes": e.get("notes", ""),
    }


@app.get("/api/clients/{client_id}/estimates")
def get_estimates(client_id: int, current_user: dict = Depends(get_current_user)):
    # Also fetch the client name so estimates carry the correct customer label
    client = db.get_client_by_id(client_id)
    client_name = (client or {}).get("name", "")
    rows = db.get_estimates_by_client(client_id)
    return [_format_estimate(r, client_name=client_name) for r in rows]


@app.get("/api/all-estimates")
def list_all_estimates(current_user: dict = Depends(get_current_user)):
    """Return all estimates across all clients — used by the AI Copilot for global context."""
    clients = db.get_all_clients()
    result = []
    for c in clients:
        rows = db.get_estimates_by_client(c["id"])
        for r in rows:
            est = _format_estimate(r, client_name=c.get("name", ""))
            est["clientId"] = str(c["id"])
            result.append(est)
    return result


@app.get("/api/estimates/{estimate_id}")
def get_estimate(estimate_id: int, current_user: dict = Depends(get_current_user)):
    row = db.get_estimate_by_id(estimate_id)
    if not row:
        raise HTTPException(status_code=404, detail="Estimate not found")

    pricing = row.get("pricing_json") or {}
    env_pricing = row.get("env_pricing_json") or {}

    return {
        "id": str(row["id"]),
        "clientId": str(row["client_id"]) if row.get("client_id") is not None else "",
        "customerName": row["customer_name"],
        "version": f"V{row.get('version', 1)}",
        "clientMode": row.get("client_mode", "saas"),
        "dbType": row.get("db_type", "PostgreSQL"),
        "generatedAt": row["estimate_date"].strftime("%d %b %Y %I:%M %p") if isinstance(row.get("estimate_date"), datetime) else "",
        "awsMonthlyCost": row.get("total_monthly_usd") or 0,
        "awsAnnualCost": row.get("total_annual_usd") or 0,
        "aws5YearTCO": row.get("total_5year_usd") or 0,
        # Real GCP pricing — embedded by Step 4b of the generation pipeline
        "gcpMonthlyCost": pricing.get("gcp_monthly") or (row.get("total_monthly_usd") or 0) * 0.88,
        "awsSavingsVsGcp": pricing.get("aws_savings_vs_gcp", 0),
        "savingsPercent": pricing.get("savings_percent", 0),
        "gcpRegion": (pricing.get("gcp") or {}).get("region", ""),
        "gcpPricedRoles": (pricing.get("gcp") or {}).get("priced_roles", []),  # real per-node GCP costs
        "gcpComparison": pricing.get("comparison", {}),    # category-level AWS vs GCP breakdown
        "costTrend": pricing.get("inflation_forecast", {}).get("yearly", []),
        "distribution": row.get("distribution_json") or {},
        "pricedRoles": pricing.get("priced_roles", []),   # real per-node production costs
        "environments": env_pricing,
        "metrics": row.get("all_metrics") or {},
        "cloudProviders": (row.get("all_metrics") or {}).get("cloud_providers", ["AWS"]),
    }


@app.delete("/api/estimates/{estimate_id}")
def delete_estimate(estimate_id: int, current_user: dict = Depends(get_current_user)):
    if current_user.get("role") not in ("admin", "estimator"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    success = db.delete_estimate(estimate_id)
    if not success:
        raise HTTPException(status_code=404, detail="Estimate not found")
    return {"message": "Estimate deleted"}


@app.get("/api/estimates/{estimate_id}/files/{file_type}")
def download_estimate_file(
    estimate_id: int,
    file_type: str,
    token: str | None = None,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
):
    """Download Excel files stored as BLOBs in the DB.
    Accepts JWT via Authorization header OR ?token= query param (for browser window.open).
    """
    # Resolve token from header or query param
    raw_token = None
    if credentials:
        raw_token = credentials.credentials
    elif token:
        raw_token = token

    if not raw_token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    # Verify the token (raises 401 on failure)
    decode_token(raw_token)

    files = db.get_estimate_files(estimate_id)
    if not files:
        raise HTTPException(status_code=404, detail="Estimate not found")

    customer = files.get("customer_name", "estimate")
    safe = customer.replace(" ", "_")

    # ── DB blob types ──────────────────────────────────────────────────────────
    if file_type == "sizing":
        data = files.get("cloud_sizing")
        if not data:
            raise HTTPException(status_code=404, detail="Cloud sizing file not yet available — run the estimate first")
        return Response(
            content=data,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f'attachment; filename="{safe}_cloud_sizing.xlsx"'},
        )

    if file_type == "pricing":
        data = files.get("aws_pricing")
        if not data:
            raise HTTPException(status_code=404, detail="AWS pricing file not yet available — run the estimate first")
        return Response(
            content=data,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f'attachment; filename="{safe}_aws_pricing.xlsx"'},
        )

    # ── On-disk types ──────────────────────────────────────────────────────────
    _reports = os.path.join(os.path.dirname(__file__), "reports")

    if file_type == "pdf":
        pdf_path = _find_pdf(customer)
        if not pdf_path:
            raise HTTPException(status_code=404, detail=f"No PDF report found for '{customer}'. Generate an estimate first.")
        with open(pdf_path, "rb") as f:
            return Response(
                content=f.read(),
                media_type="application/pdf",
                headers={"Content-Disposition": f'attachment; filename="{safe}_pricing_report.pdf"'},
            )

    if file_type == "updated-estimate":
        path = os.path.join(_reports, "updated_estimate.xlsx")
        if not os.path.exists(path):
            raise HTTPException(status_code=404, detail="Updated estimate sheet not available. Run the estimator pipeline first.")
        with open(path, "rb") as f:
            return Response(
                content=f.read(),
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                headers={"Content-Disposition": f'attachment; filename="{safe}_updated_estimate.xlsx"'},
            )

    if file_type == "gcp-sizing":
        _reports = os.path.join(os.path.dirname(__file__), "reports")
        path = os.path.join(_reports, "gcp_sizing.xlsx")
        if not os.path.exists(path):
            raise HTTPException(status_code=404, detail="GCP sizing file not available. Select GCP as a provider and re-run the estimate.")
        with open(path, "rb") as f:
            return Response(
                content=f.read(),
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                headers={"Content-Disposition": f'attachment; filename="{safe}_gcp_sizing.xlsx"'},
            )

    if file_type == "gcp-pricing":
        _reports = os.path.join(os.path.dirname(__file__), "reports")
        path = os.path.join(_reports, "gcp_pricing.xlsx")
        if not os.path.exists(path):
            raise HTTPException(status_code=404, detail="GCP pricing file not available. Select GCP as a provider and re-run the estimate.")
        with open(path, "rb") as f:
            return Response(
                content=f.read(),
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                headers={"Content-Disposition": f'attachment; filename="{safe}_gcp_pricing.xlsx"'},
            )

    if file_type == "ai-sizing":
        path = os.path.join(_reports, "ai_services_sizing_and_pricing.xlsx")
        if not os.path.exists(path):
            raise HTTPException(status_code=404, detail="AI Services workbook not available. Enable AI services (Predictive/GenAI/Agentic) and re-run the estimate.")
        with open(path, "rb") as f:
            return Response(
                content=f.read(),
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                headers={"Content-Disposition": f'attachment; filename="{safe}_ai_services_sizing_and_pricing.xlsx"'},
            )

    raise HTTPException(status_code=400, detail="file_type must be 'sizing', 'pricing', 'gcp-sizing', 'gcp-pricing', 'ai-sizing', 'pdf', or 'updated-estimate'")


REPORTS_DIR = os.path.join(os.path.dirname(__file__), "reports")


def _find_pdf(customer_name: str) -> str | None:
    """Find PDF on disk for a given customer name. Tries several name patterns."""
    # Exact match first: pricing_report_{Name}.pdf  (spaces → underscores)
    safe = customer_name.replace(" ", "_")
    for pattern in [
        f"pricing_report_{safe}.pdf",
        f"pricing_report_{safe.lower()}.pdf",
        "pricing_report.pdf",
    ]:
        path = os.path.join(REPORTS_DIR, pattern)
        if os.path.exists(path):
            return path
    # Fuzzy: find any PDF whose filename contains any word from the customer name
    words = [w for w in customer_name.split() if len(w) > 2]
    for pdf in glob.glob(os.path.join(REPORTS_DIR, "pricing_report_*.pdf")):
        fname = os.path.basename(pdf).lower()
        if any(w.lower() in fname for w in words):
            return pdf
    return None


@app.get("/api/estimates/{estimate_id}/download-all")
def download_all_files(
    estimate_id: int,
    token: str | None = None,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
):
    """Return a ZIP containing all report files for an estimate."""
    # Auth
    raw_token = credentials.credentials if credentials else token
    if not raw_token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    decode_token(raw_token)

    row = db.get_estimate_by_id(estimate_id)
    if not row:
        raise HTTPException(status_code=404, detail="Estimate not found")

    files_row = db.get_estimate_files(estimate_id)
    customer = row.get("customer_name", "estimate")
    safe_name = customer.replace(" ", "_")

    buf = io.BytesIO()
    added = 0
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        # 1. Cloud Sizing (from DB blob)
        if files_row.get("cloud_sizing"):
            zf.writestr(f"{safe_name}_cloud_sizing.xlsx", files_row["cloud_sizing"])
            added += 1

        # 2. AWS Pricing (from DB blob)
        if files_row.get("aws_pricing"):
            zf.writestr(f"{safe_name}_aws_pricing.xlsx", files_row["aws_pricing"])
            added += 1

        # 3. Updated Estimate Sheet (from disk)
        updated_path = os.path.join(REPORTS_DIR, "updated_estimate.xlsx")
        if os.path.exists(updated_path):
            with open(updated_path, "rb") as f:
                zf.writestr(f"{safe_name}_updated_estimate.xlsx", f.read())
            added += 1

        # 4a. AI Services Workbook (from disk — only when AI was enabled)
        ai_path = os.path.join(REPORTS_DIR, "ai_services_sizing_and_pricing.xlsx")
        if os.path.exists(ai_path):
            with open(ai_path, "rb") as f:
                zf.writestr(f"{safe_name}_ai_services_sizing_and_pricing.xlsx", f.read())
            added += 1

        # 5. PDF Report (from disk — match by customer name)
        pdf_path = _find_pdf(customer)
        if pdf_path:
            with open(pdf_path, "rb") as f:
                zf.writestr(f"{safe_name}_pricing_report.pdf", f.read())
            added += 1

    if added == 0:
        raise HTTPException(status_code=404, detail="No report files found for this estimate")

    buf.seek(0)
    return Response(
        content=buf.read(),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{safe_name}_reports.zip"'},
    )


@app.get("/api/estimates/{estimate_id}/files/pdf")
def download_pdf(
    estimate_id: int,
    token: str | None = None,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
):
    """Serve the PDF report from disk, matched by customer name."""
    raw_token = credentials.credentials if credentials else token
    if not raw_token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    decode_token(raw_token)

    row = db.get_estimate_by_id(estimate_id)
    if not row:
        raise HTTPException(status_code=404, detail="Estimate not found")

    pdf_path = _find_pdf(row["customer_name"])
    if not pdf_path:
        raise HTTPException(status_code=404, detail=f"No PDF found for '{row['customer_name']}'")

    with open(pdf_path, "rb") as f:
        data = f.read()
    safe = row["customer_name"].replace(" ", "_")
    return Response(
        content=data,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{safe}_pricing_report.pdf"'},
    )


@app.get("/api/estimates/{estimate_id}/files/updated-estimate")
def download_updated_estimate(
    estimate_id: int,
    token: str | None = None,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
):
    """Serve the updated_estimate.xlsx from disk."""
    raw_token = credentials.credentials if credentials else token
    if not raw_token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    decode_token(raw_token)

    row = db.get_estimate_by_id(estimate_id)
    if not row:
        raise HTTPException(status_code=404, detail="Estimate not found")

    path = os.path.join(REPORTS_DIR, "updated_estimate.xlsx")
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Updated estimate sheet not available")

    with open(path, "rb") as f:
        data = f.read()
    safe = row["customer_name"].replace(" ", "_")
    return Response(
        content=data,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{safe}_updated_estimate.xlsx"'},
    )


# ── Generate Estimate ─────────────────────────────────────────────────────────

@app.post("/api/generate-estimate", status_code=200)
def generate_estimate(
    body: GenerateEstimateRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Full estimation pipeline — mirrors the Streamlit generate button.

    Steps:
      1. write_and_recalculate  — populate Sizing_Template.xlsx with Y1 inputs
      2. extract_metrics        — read computed cell values back from Excel
      3. distribute_nodes       — AI/rule-based node assignment
      4. calculate_pricing      — AWS instance pricing
      5. price_additional_environments — Pre-Prod / DR pricing
      6. generate_excel_reports — cloud_sizing.xlsx + cloud_pricing.xlsx
      7. generate_pdf_report    — PDF pricing report
      8. save_estimate          — persist to PostgreSQL
    """
    # Lazy-import pipeline modules so the server starts even when pipeline deps
    # are not installed in the same virtualenv as the FastAPI layer.
    try:
        from excel_handler import write_and_recalculate, extract_metrics
        from node_distributor import distribute_nodes
        from aws_pricer import calculate_pricing
        from env_pricer import price_additional_environments
        from excel_exporter import generate_excel_reports
        from pdf_report import generate_pdf_report
    except ImportError as imp_err:
        raise HTTPException(
            status_code=503,
            detail=f"Pipeline modules not available: {imp_err}",
        )

    # ── Derive convenience variables ──────────────────────────────────────────
    client_mode   = "saas" if body.deployment.lower() in ("saas", "cloud") else "onprem"
    db_type       = body.database          # "PostgreSQL" / "SQL Server" / "Oracle"
    customer_name = body.clientName
    aws_region    = body.awsRegion         # e.g. "ap-south-1"
    dr_scale_frac = body.drScale / 100.0  # 50 → 0.5, 100 → 1.0

    # Environments → which non-prod envs are requested
    envs_lower    = [e.lower() for e in body.environments]
    include_dr    = any("dr" in e for e in envs_lower)
    include_preprod = any(e in envs_lower for e in ("preprod", "sit", "uat"))

    # Contract years
    years_map = {"1 Year": 1, "3 Year": 3, "5 Year": 5}
    years     = years_map.get(body.contractDuration, 3)

    # Client ID (integer)
    client_id_int: Optional[int] = None
    if body.clientId:
        try:
            client_id_int = int(body.clientId)
        except ValueError:
            pass

    # ─────────────────────────────────────────────────────────────────────────
    # STEP 1 — Write Y1 values into the Sizing Template and recalculate
    # ─────────────────────────────────────────────────────────────────────────
    inputs = {
        # Base values written to Customer Volumes sheet
        "named_users":      body.namedUsers,
        "concurrent_users": body.concurrentUsers,
        "total_customers":  body.totalCustomers,
        "leads":            body.numberOfLeads,
        "cases":            body.serviceRequests,
        "mobile_users":     body.concurrentMobileUsers,
        # YoY growth rates — written as fractions (e.g. 5% → 0.05)
        "yoy_named_users":  body.namedUsersYoy / 100.0,
        "yoy_concurrent":   body.concurrentUsersYoy / 100.0,
        "yoy_customers":    body.totalCustomersYoy / 100.0,
        "yoy_leads":        body.numberOfLeadsYoy / 100.0,
        "yoy_cases":        body.serviceRequestsYoy / 100.0,
        "yoy_mobile":       body.concurrentMobileUsersYoy / 100.0,
    }
    try:
        updated_file = write_and_recalculate(
            inputs=inputs,
            template_path="templates/Sizing_Template.xlsx",
            output_path="reports/updated_estimate.xlsx",
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Step 1 (Sizing Template): {exc}")

    # ─────────────────────────────────────────────────────────────────────────
    # STEP 2 — Extract computed metrics from the recalculated workbook
    # ─────────────────────────────────────────────────────────────────────────
    try:
        metrics = extract_metrics(updated_file)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Step 2 (Extract metrics): {exc}")

    # Augment with UI-level fields that are not in the Excel template
    metrics.update({
        "mobile_users":          body.concurrentMobileUsers,
        "db_type":               db_type,
        "client_mode":           client_mode,
        "customer_name":         customer_name,
        "total_named_users":     body.namedUsers,
        # One-time costs (passed through to PUPM sheet in Excel)
        "one_time_perf_testing": body.perfTestingCost,
        "one_time_migration":    body.migrationCost,
        "one_time_managed_svc":  body.managedSvcCost,
        # Sizing assumptions (used by excel_exporter PUPM sheet)
        "docs_per_customer":     body.docsPerCustomer,
        "docs_per_lead":         body.docsPerLead,
        "docs_per_case":         body.docsPerCase,
        "acts_per_customer":     body.actsPerCustomer,
        "acts_per_lead":         body.actsPerLead,
        "acts_per_case":         body.actsPerCase,
        "pdf_per_user":          body.pdfPerUser,
        "doc_size_mb":           body.docSizeMb,
        # Derived values
        "emails_auto":           int((body.numberOfLeads + body.serviceRequests) * 0.05),
        "escalations_auto":      int((body.totalCustomers + body.numberOfLeads + body.serviceRequests) * 0.10),
        # Financial
        "discount_percent":      body.discountPercent,
        "inflation_percent":     body.inflationPercent,
        "contract_duration":     body.contractDuration,
        # ── Full wizard form inputs (for Recalculate pre-fill) ────────────────
        "concurrent_users":          body.concurrentUsers,
        "named_users_yoy":           body.namedUsersYoy,
        "concurrent_users_yoy":      body.concurrentUsersYoy,
        "concurrent_mobile_users_yoy": body.concurrentMobileUsersYoy,
        "total_customers":           body.totalCustomers,
        "total_customers_yoy":       body.totalCustomersYoy,
        "number_of_leads":           body.numberOfLeads,
        "number_of_leads_yoy":       body.numberOfLeadsYoy,
        "service_requests":          body.serviceRequests,
        "service_requests_yoy":      body.serviceRequestsYoy,
        "modules":                   body.modules,
        "environments":              body.environments,
        "dr_scale":                  body.drScale,
        "clickhouse_enabled":        body.clickhouseEnabled,
        "ai_services_enabled":       body.aiServicesEnabled,
        "predictive_ai":             body.predictiveAi,
        "predictive_envs":           body.predictiveEnvs,
        "genai_ai":                  body.genaiAi,
        "genai_tokens":              body.genaiTokens,
        "genai_envs":                body.genaiEnvs,
        "agentic_ai":                body.agenticAi,
        "agentic_tasks":             body.agenticTasks,
        "agentic_envs":              body.agenticEnvs,
        "bedrock_monthly":           body.bedrockMonthly,
        "aws_region":                body.awsRegion,
        "cloud_providers":           body.cloudProviders if client_mode == "saas" else ["AWS"],
    })

    # ─────────────────────────────────────────────────────────────────────────
    # STEP 3 — Distribute nodes (with optional AI Services and ClickHouse)
    # ─────────────────────────────────────────────────────────────────────────
    # Map AI environment labels ("prod", "uat", etc.) from wizard to the
    # identifiers expected by ai_sizer.py (lowercase, no spaces)
    def _norm_ai_envs(envs: List[str]) -> List[str]:
        mapping = {
            "prod": "prod", "production": "prod",
            "uat": "uat", "preprod": "uat", "training": "training",
            "dr": "dr",
        }
        return list({mapping.get(e.lower(), e.lower()) for e in envs}) or ["prod"]

    workload_profile = {
        "workload_type":   "banking_crm",
        "peak_load":       "high",
        "mobile_heavy":    body.concurrentMobileUsers > 3000,
        "mobile_users":    body.concurrentMobileUsers,
        "reporting_db":    False,          # PostgreSQL is HA — no separate reporting DB
        "high_compliance": True,
        "db_type":         db_type,
        "client_mode":     client_mode,
        "notes":           "",
    }

    try:
        distribution = distribute_nodes(
            metrics=metrics,
            workload_profile=workload_profile,
            use_llm=True,                          # attempt LLM; falls back to rule-based
            db_type=db_type,
            include_clickhouse=body.clickhouseEnabled and "Analytics" in body.modules,
            ch_data_multiplier=2.0,
            include_predictive=body.predictiveAi and body.aiServicesEnabled and "AI" in body.modules,
            include_genai=body.genaiAi and body.aiServicesEnabled and "AI" in body.modules,
            include_agentic=body.agenticAi and body.aiServicesEnabled and "AI" in body.modules,
            predictive_envs=_norm_ai_envs(body.predictiveEnvs),
            genai_envs=_norm_ai_envs(body.genaiEnvs),
            agentic_envs=_norm_ai_envs(body.agenticEnvs),
            bedrock_monthly=body.bedrockMonthly,
            dr_scale=dr_scale_frac,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Step 3 (Node distribution): {exc}")

    ai_sizing = distribution.get("ai_nodes", {"enabled": False})

    # ─────────────────────────────────────────────────────────────────────────
    # STEP 4 — AWS pricing, then GCP pricing on equivalent services (SaaS only)
    # ─────────────────────────────────────────────────────────────────────────
    pricing     = None
    env_pricing = None

    # AWS region → nearest GCP region mapping
    _AWS_TO_GCP_REGION = {
        "us-east-1":      "us-east4",        # N. Virginia ↔ N. Virginia
        "us-east-2":      "us-east5",        # Ohio ↔ Columbus
        "us-west-1":      "us-west2",        # N. California ↔ Los Angeles
        "us-west-2":      "us-west1",        # Oregon ↔ Oregon
        "ap-south-1":     "asia-south1",     # Mumbai ↔ Mumbai
        "ap-south-2":     "asia-south2",     # Hyderabad ↔ Delhi
        "ap-southeast-1": "asia-southeast1", # Singapore ↔ Singapore
        "ap-southeast-2": "australia-southeast1",  # Sydney ↔ Sydney
        "ap-northeast-1": "asia-northeast1", # Tokyo ↔ Tokyo
        "ap-northeast-2": "asia-northeast3", # Seoul ↔ Seoul
        "ap-northeast-3": "asia-northeast2", # Osaka ↔ Osaka
        "eu-west-1":      "europe-west1",    # Ireland ↔ Belgium
        "eu-west-2":      "europe-west2",    # London ↔ London
        "eu-west-3":      "europe-west9",    # Paris ↔ Paris
        "eu-central-1":   "europe-west3",    # Frankfurt ↔ Frankfurt
        "eu-north-1":     "europe-north1",   # Stockholm ↔ Finland
        "sa-east-1":      "southamerica-east1",  # São Paulo ↔ São Paulo
        "ca-central-1":   "northamerica-northeast1",  # Canada ↔ Montréal
        "me-south-1":     "me-central1",     # Bahrain ↔ Doha
        "af-south-1":     "af-south1",       # Cape Town ↔ Johannesburg
    }
    gcp_region = _AWS_TO_GCP_REGION.get(aws_region, "us-central1")

    if client_mode == "saas":
        try:
            pricing = calculate_pricing(
                distribution=distribution,
                metrics=metrics,
                region=aws_region,
            )
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Step 4 (AWS pricing): {exc}")

        # ── Step 4b — GCP pricing on equivalent services ─────────────────────
        try:
            from gcp_pricer import calculate_gcp_pricing, build_comparison
            gcp_pricing = calculate_gcp_pricing(
                distribution=distribution,
                metrics=metrics,
                region=gcp_region,
            )
            comparison  = build_comparison(pricing, gcp_pricing)
            # Embed GCP data inside the pricing dict (no DB schema change needed)
            pricing["gcp"]        = gcp_pricing
            pricing["comparison"] = comparison
            # Surface flat keys for backward-compatible API reads
            aws_mo = pricing.get("total_monthly_usd", 0)
            gcp_mo = gcp_pricing.get("total_monthly_usd", 0)
            pricing["gcp_monthly"]        = round(gcp_mo, 2)
            pricing["aws_savings_vs_gcp"] = round((gcp_mo - aws_mo) * 12, 2)  # positive = AWS saves
            pricing["savings_percent"]    = round((gcp_mo - aws_mo) / gcp_mo * 100, 1) if gcp_mo else 0
        except Exception as gcp_exc:
            # Non-fatal — fall back to the 12% estimate if GCP pricer fails
            print(f"[api_server] WARNING Step 4b (GCP pricing) failed: {gcp_exc}")
            pricing.setdefault("gcp_monthly", round(pricing.get("total_monthly_usd", 0) * 0.88, 2))
            pricing.setdefault("aws_savings_vs_gcp", 0)
            pricing.setdefault("savings_percent", 12)


        # ─────────────────────────────────────────────────────────────────────
        # STEP 5 — Environment pricing (Pre-Prod / DR)
        # ─────────────────────────────────────────────────────────────────────
        if include_preprod or include_dr:
            try:
                env_pricing = price_additional_environments(
                    db_type=db_type,
                    deployment="saas",
                    metrics=metrics,
                    preprod_region=aws_region,
                    dr_region=aws_region,     # same region; can be extended later
                    dr_scale=dr_scale_frac,
                    distribution=distribution,
                )

                # If Pre-Prod was not requested, zero it out
                if not include_preprod:
                    env_pricing["preprod_sit_uat"] = None
                else:
                    # Tag with UI env names for display in reports
                    pp = env_pricing.get("preprod_sit_uat") or {}
                    if pp:
                        pp["env_names"] = [
                            e for e in body.environments
                            if e.lower() not in ("dr", "prod", "production")
                        ]
                        env_pricing["preprod_sit_uat"] = pp

                # If DR was not requested, zero it out
                if not include_dr:
                    env_pricing["dr"] = None

                # Recalculate combined_monthly cleanly
                pp_mo = (env_pricing.get("preprod_sit_uat") or {}).get("monthly_usd", 0)
                dr_mo = (env_pricing.get("dr")              or {}).get("monthly_usd", 0)
                env_pricing["combined_monthly"] = round(pp_mo + dr_mo, 2)

            except Exception as exc:
                # Non-fatal — log and continue without env pricing
                print(f"[api_server] WARNING Step 5 (env pricing) failed: {exc}")
                env_pricing = None

    # ─────────────────────────────────────────────────────────────────────────
    # STEP 6 — Generate Excel reports
    # ─────────────────────────────────────────────────────────────────────────
    cloud_sizing_path = None
    aws_pricing_path  = None
    try:
        excel_paths = generate_excel_reports(
            pricing=pricing,
            distribution=distribution,
            metrics=metrics,
            customer=customer_name,
            output_dir="reports",
            env_pricing=env_pricing,
            db_type=db_type,
            client_mode=client_mode,
            gcp_pricing=pricing.get("gcp") if pricing else None,
            comparison=pricing.get("comparison") if pricing else None,
            years=years,
            include_dr=include_dr,
            env_names=body.environments,
            dr_scale=dr_scale_frac,
            ai_sizing=ai_sizing,
            cloud_providers=body.cloudProviders if client_mode == "saas" else ["AWS"],
        )
        cloud_sizing_path = excel_paths.get("cloud_sizing")
        aws_pricing_path  = excel_paths.get("cloud_pricing")
    except Exception as exc:
        print(f"[api_server] WARNING Step 6 (Excel generation) failed: {exc}")
        # Non-fatal — the estimate can still be saved without the Excel files

    # ─────────────────────────────────────────────────────────────────────────
    # STEP 7 — Generate PDF report
    # ─────────────────────────────────────────────────────────────────────────
    pdf_path = None
    try:
        cname_safe = re.sub(r"[^a-zA-Z0-9_\-]", "_", customer_name)
        pdf_path = generate_pdf_report(
            pricing=pricing,
            distribution=distribution,
            metrics=metrics,
            env_pricing=env_pricing,
            customer=customer_name,
            client_mode=client_mode,
            output_path=f"reports/pricing_report_{cname_safe}.pdf",
            gcp_pricing=None,
            comparison=None,
            ai_sizing=ai_sizing,
        )
    except Exception as exc:
        print(f"[api_server] WARNING Step 7 (PDF generation) failed: {exc}")

    # ─────────────────────────────────────────────────────────────────────────
    # STEP 8 — Save to database
    # ─────────────────────────────────────────────────────────────────────────
    try:
        saved_id = db.save_estimate(
            customer_name=customer_name,
            estimate_date=datetime.utcnow(),
            years=years,
            metrics=metrics,
            client_mode=client_mode,
            db_type=db_type,
            pricing=pricing,
            distribution=distribution,
            env_pricing=env_pricing,
            cloud_sizing_path=cloud_sizing_path,
            aws_pricing_path=aws_pricing_path,
            client_id=client_id_int,
            notes=body.estimateNotes or "",
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Step 8 (Save estimate): {exc}")

    # ─────────────────────────────────────────────────────────────────────────
    # Return lightweight summary — frontend redirects to /results/{id}
    # ─────────────────────────────────────────────────────────────────────────
    monthly  = (pricing or {}).get("total_monthly_usd", 0)
    annual   = (pricing or {}).get("total_annual_usd",  0)
    five_yr  = (pricing or {}).get("inflation_forecast", {}).get("five_year_total", 0)
    pp_mo    = ((env_pricing or {}).get("preprod_sit_uat") or {}).get("monthly_usd", 0)
    dr_mo    = ((env_pricing or {}).get("dr") or {}).get("monthly_usd", 0)
    grand_monthly = round(monthly + pp_mo + dr_mo, 2)

    return {
        "success":        True,
        "estimateId":     str(saved_id),
        "customerName":   customer_name,
        "clientMode":     client_mode,
        "cloudProviders": body.cloudProviders if client_mode == "saas" else ["AWS"],
        "awsMonthlyCost": monthly,
        "awsAnnualCost":  annual,
        "aws5YearTCO":    five_yr,
        "grandMonthly":   grand_monthly,
        "grandAnnual":    round(grand_monthly * 12, 2),
        "environments": {
            "production":  {"monthly": monthly, "annual": annual},
            "preprod":     {"monthly": pp_mo,   "annual": round(pp_mo * 12, 2)} if pp_mo else None,
            "dr":          {"monthly": dr_mo,   "annual": round(dr_mo * 12, 2)} if dr_mo else None,
        },
        "metrics": {
            "workerNodes":  metrics.get("total_workernodes", 0),
            "totalVcpus":   metrics.get("total_vcpus_workernode", 0),
            "totalRamGb":   metrics.get("total_memory_workernode_gb", 0),
            "dataSizeGb":   metrics.get("data_size_gb", 0),
        },
        "aiEnabled":      ai_sizing.get("enabled", False),
        "pdfGenerated":   bool(pdf_path),
        "excelGenerated": bool(cloud_sizing_path),
    }


# ── On-Premise Sizing (separate pipeline — NO pricing, sizing only) ──────────

class GenerateOnpremEstimateRequest(BaseModel):
    """
    Request body for the On-Premise sizing pipeline.
    Entirely separate from GenerateEstimateRequest (SaaS) — does not affect
    or share validation/defaults with the SaaS estimate flow.
    """
    # ── Identity ─────────────────────────────────────────────────────────────
    clientId:         Optional[str]  = None
    clientName:       str            = "Bank"
    database:         str            = "SQL Server"   # "PostgreSQL" | "SQL Server" | "Oracle"
    cloud:            str            = "aws"           # "aws" | "gcp" | "kubeadm" | "openshift"
    region:           Optional[str] = None             # AWS/GCP region; ignored for kubeadm/openshift

    # ── Year-1 base values (same shape as SaaS, kept independent) ───────────
    namedUsers:              int   = 15500
    concurrentUsers:         int   = 4650
    concurrentMobileUsers:   int   = 0
    totalCustomers:          int   = 25786541
    numberOfLeads:           int   = 10700000
    serviceRequests:         int   = 20000

    namedUsersYoy:           int   = 5
    concurrentUsersYoy:      int   = 5
    concurrentMobileUsersYoy:int   = 5
    totalCustomersYoy:       int   = 10
    numberOfLeadsYoy:        int   = 10
    serviceRequestsYoy:      int   = 5

    # ── Environments & contract ──────────────────────────────────────────────
    environments:     List[str] = []          # e.g. ["DR"], ["Pre-Prod","UAT"]
    drScale:          int       = 100          # 50 or 100 (percent)
    contractDuration: str       = "3 Year"

    estimateNotes:    str   = ""


@app.post("/api/generate-onprem-estimate", status_code=200)
def generate_onprem_estimate(
    body: GenerateOnpremEstimateRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    On-Premise sizing pipeline. SIZING ONLY — no pricing is computed or
    returned anywhere in this route. Completely independent of
    /api/generate-estimate (SaaS) — shares only read-only helper modules.

    Steps:
      1. write_and_recalculate / extract_metrics — same Excel template as SaaS,
         reused because the worker-node sizing math is cloud-agnostic.
      2. distribute_nodes — reused as-is for worker-tier sizing (web/app/infra).
      3. onprem_sizer.size_onprem_database — NEW cloud-aware DB sizing
         (AWS self-hosted AMD-first BYOL / GCP managed Cloud SQL / Kubeadm &
         OpenShift generic self-hosted).
      4. excel_exporter.generate_onprem_excel — sizing-only workbook.
      5. database.save_estimate — persisted with client_mode="onprem",
         pricing=None.
    """
    try:
        from excel_handler import write_and_recalculate, extract_metrics
        from node_distributor import distribute_nodes
        from onprem_sizer import size_onprem_database
        from excel_exporter import generate_onprem_excel
    except ImportError as imp_err:
        raise HTTPException(status_code=503, detail=f"Pipeline modules not available: {imp_err}")

    db_type   = body.database
    cloud     = body.cloud.lower()
    customer_name = body.clientName

    if cloud not in ("aws", "gcp", "kubeadm", "openshift"):
        raise HTTPException(status_code=400, detail=f"Unsupported cloud option: {body.cloud!r}")

    envs_lower = [e.lower() for e in body.environments]
    include_dr = any("dr" in e for e in envs_lower)
    dr_scale_frac = body.drScale / 100.0

    years_map = {"1 Year": 1, "3 Year": 3, "5 Year": 5}
    years     = years_map.get(body.contractDuration, 3)

    client_id_int: Optional[int] = None
    if body.clientId:
        try:
            client_id_int = int(body.clientId)
        except ValueError:
            pass

    # ── STEP 1 — Same Excel template as SaaS (worker-node sizing is cloud-agnostic) ──
    inputs = {
        "named_users":      body.namedUsers,
        "concurrent_users": body.concurrentUsers,
        "total_customers":  body.totalCustomers,
        "leads":            body.numberOfLeads,
        "cases":            body.serviceRequests,
        "mobile_users":     body.concurrentMobileUsers,
        "yoy_named_users":  body.namedUsersYoy / 100.0,
        "yoy_concurrent":   body.concurrentUsersYoy / 100.0,
        "yoy_customers":    body.totalCustomersYoy / 100.0,
        "yoy_leads":        body.numberOfLeadsYoy / 100.0,
        "yoy_cases":        body.serviceRequestsYoy / 100.0,
        "yoy_mobile":       body.concurrentMobileUsersYoy / 100.0,
    }
    try:
        updated_file = write_and_recalculate(
            inputs=inputs,
            template_path="templates/Sizing_Template.xlsx",
            output_path=f"reports/updated_estimate_onprem_{cloud}.xlsx",
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Step 1 (Sizing Template): {exc}")

    try:
        metrics = extract_metrics(updated_file)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Step 2 (Extract metrics): {exc}")

    metrics.update({
        "mobile_users":      body.concurrentMobileUsers,
        "db_type":           db_type,
        "client_mode":       "onprem",
        "cloud":             cloud,
        "customer_name":     customer_name,
        "total_named_users": body.namedUsers,
    })

    # ── STEP 3 — Worker-tier distribution (reused as-is; cloud-agnostic) ─────
    workload_profile = {
        "workload_type":   "banking_crm",
        "peak_load":       "high",
        "mobile_heavy":    body.concurrentMobileUsers > 3000,
        "mobile_users":    body.concurrentMobileUsers,
        "reporting_db":    False,
        "high_compliance": True,
        "db_type":         db_type,
        "client_mode":     "onprem",
        "notes":           "",
    }
    try:
        distribution = distribute_nodes(
            metrics=metrics,
            workload_profile=workload_profile,
            use_llm=True,
            db_type=db_type,
            dr_scale=dr_scale_frac,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Step 3 (Node distribution): {exc}")

    # ── STEP 4 — Cloud-aware DB sizing (NEW — the whole point of this route) ─
    try:
        db_sizing = size_onprem_database(
            metrics=metrics,
            db_type=db_type,
            cloud=cloud,
            region=body.region,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Step 4 (On-Prem DB sizing): {exc}")

    # ── STEP 5 — Sizing-only Excel workbook ───────────────────────────────────
    onprem_sizing_path = None
    try:
        cluster_label = {"aws": "AWS", "gcp": "GCP", "kubeadm": "Kubeadm", "openshift": "OpenShift"}[cloud]
        db_slug = db_type.lower().replace(" ", "_")
        onprem_sizing_path = generate_onprem_excel(
            metrics=metrics,
            distribution=distribution,
            customer=customer_name,
            output_dir="reports",
            db_type=db_type,
            years=years,
            filename=f"onprem_{cloud}_{db_slug}_sizing.xlsx",
            cluster_name=cluster_label,
            include_dr=include_dr,
            env_names=body.environments,
            dr_scale=dr_scale_frac,
        )
    except Exception as exc:
        print(f"[api_server] WARNING Step 5 (On-Prem Excel) failed: {exc}")

    # ── STEP 6 — Save to database (pricing=None always) ──────────────────────
    try:
        saved_id = db.save_estimate(
            customer_name=customer_name,
            estimate_date=datetime.utcnow(),
            years=years,
            metrics=metrics,
            client_mode="onprem",
            db_type=db_type,
            pricing=None,
            distribution={**distribution, "onprem_db_sizing": db_sizing, "cloud": cloud},
            env_pricing=None,
            cloud_sizing_path=onprem_sizing_path,
            aws_pricing_path=None,
            client_id=client_id_int,
            notes=body.estimateNotes or "",
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Step 6 (Save estimate): {exc}")

    return {
        "success":       True,
        "estimateId":    str(saved_id),
        "customerName":  customer_name,
        "clientMode":    "onprem",
        "cloud":         cloud,
        "database":      db_type,
        "dbSizing":      db_sizing,
        "metrics": {
            "workerNodes": metrics.get("total_workernodes", 0),
            "totalVcpus":  metrics.get("total_vcpus_workernode", 0),
            "totalRamGb":  metrics.get("total_memory_workernode_gb", 0),
            "dataSizeGb":  metrics.get("data_size_gb", 0),
            "s3SizeGb":    metrics.get("s3_size_gb", 0),
        },
        "distribution":  distribution,
        "excelGenerated": bool(onprem_sizing_path),
    }


# ── Pricing Cache ─────────────────────────────────────────────────────────────

import json as _json
from pathlib import Path as _Path

_CACHE_FILE = _Path(__file__).parent / "pricing_cache.json"


def _load_pricing_cache() -> dict:
    try:
        return _json.loads(_cache_file_read())
    except Exception:
        return {}


def _cache_file_read() -> str:
    try:
        return _CACHE_FILE.read_text(encoding="utf-8")
    except Exception:
        return "{}"


def _save_pricing_cache(data: dict):
    _CACHE_FILE.write_text(
        _json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def _check_api_connectivity() -> dict:
    """
    Truthfully check whether AWS and GCP pricing API credentials are configured.
    Does NOT make a network call — just inspects env vars so it's instant.
    """
    aws_key    = os.getenv("AWS_ACCESS_KEY_ID", "").strip()
    aws_secret = os.getenv("AWS_SECRET_ACCESS_KEY", "").strip()
    gcp_key    = os.getenv("GCP_API_KEY", "").strip()

    aws_live = bool(aws_key and aws_secret and not aws_key.startswith("YOUR"))
    gcp_live = bool(gcp_key and not gcp_key.startswith("YOUR") and not gcp_key.startswith("AIzaSyXXX"))

    return {
        "aws": {
            "live_api_configured": aws_live,
            "source": "AWS Pricing API (boto3)" if aws_live else "Catalog fallback (March 2025)",
            "note": "Credentials present" if aws_live else "AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY not configured",
        },
        "gcp": {
            "live_api_configured": gcp_live,
            "source": "GCP Cloud Billing Catalog API" if gcp_live else "Catalog fallback (March 2026)",
            "note": "GCP_API_KEY present" if gcp_live else "GCP_API_KEY not configured — all GCP regions use catalog multipliers",
        },
    }


# ── AI Copilot Chat ───────────────────────────────────────────────────────────

class CopilotChatRequest(BaseModel):
    question:         str
    estimate_context: Optional[dict] = None   # single estimate the user is viewing
    all_estimates:    Optional[list] = []      # all estimates loaded globally


@app.post("/api/copilot/chat")
async def copilot_chat(
    body: CopilotChatRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    AI Cost Copilot — answers cloud cost questions using Groq LLaMA 3.3 70B.
    Incorporates estimate context (single or all) into a rich system prompt.
    Falls back to a rule-based response if Groq is unavailable.
    """
    import requests as _req

    groq_key = os.getenv("GROQ_API_KEY", "").strip()

    # ── Build context string ──────────────────────────────────────────────────
    ctx_lines = []

    if body.estimate_context:
        ec = body.estimate_context
        ctx_lines.append("=== ESTIMATE CONTEXT (User is currently viewing this estimate) ===")
        ctx_lines.append(f"Customer: {ec.get('customerName', 'N/A')} {ec.get('version', '')}")
        ctx_lines.append(f"Mode: {ec.get('clientMode', 'N/A')} | DB: {ec.get('dbType', 'N/A')}")
        ctx_lines.append(f"AWS Monthly: ${ec.get('awsMonthlyCost', 0):,.0f}")
        ctx_lines.append(f"GCP Monthly: ${ec.get('gcpMonthlyCost', 0):,.0f}")
        ctx_lines.append(f"AWS 5-Year TCO: ${ec.get('aws5YearTCO', 0):,.0f}")
        providers = ec.get("cloudProviders") or []
        if providers:
            ctx_lines.append(f"Cloud Providers: {', '.join(providers)}")
        metrics = ec.get("metrics") or {}
        if metrics:
            for k in ["total_named_users", "concurrent_users", "aws_region", "data_size_gb", "s3_size_gb"]:
                if metrics.get(k):
                    ctx_lines.append(f"  {k}: {metrics[k]}")
        ctx_lines.append("")

    if body.all_estimates:
        ests = body.all_estimates
        ctx_lines.append("=== ALL ESTIMATES IN PLATFORM ===")
        for i, e in enumerate(ests[:30], 1):
            aws_mo  = e.get('awsMonthlyCost', 0)
            gcp_mo  = e.get('gcpMonthlyCost', 0)
            tco     = e.get('aws5YearTCO', 0)
            diff    = aws_mo - gcp_mo
            cheaper = f"GCP cheaper by ${abs(diff):,.0f}/mo" if diff > 0 else f"AWS cheaper by ${abs(diff):,.0f}/mo"
            ctx_lines.append(
                f"{i}. {e.get('customerName','?')} {e.get('version','')} | "
                f"AWS ${aws_mo:,.0f}/mo | GCP ${gcp_mo:,.0f}/mo | {cheaper} | "
                f"5Y TCO ${tco:,.0f} | {e.get('clientMode','?')} | DB: {e.get('dbType','?')}"
            )
        ctx_lines.append("")

        # Pre-compute aggregate stats for the LLM
        total_monthly  = sum(e.get('awsMonthlyCost', 0) for e in ests)
        total_tco      = sum(e.get('aws5YearTCO', 0) for e in ests)
        avg_monthly    = total_monthly / len(ests) if ests else 0
        gcp_savings    = sum(max(0, e.get('awsMonthlyCost', 0) - e.get('gcpMonthlyCost', 0)) for e in ests)
        sorted_by_cost = sorted(ests, key=lambda x: x.get('awsMonthlyCost', 0), reverse=True)
        ctx_lines.append("=== PRE-COMPUTED AGGREGATE STATISTICS ===")
        ctx_lines.append(f"Total estimates: {len(ests)}")
        ctx_lines.append(f"Combined AWS monthly: ${total_monthly:,.0f}")
        ctx_lines.append(f"Average monthly per estimate: ${avg_monthly:,.0f}")
        ctx_lines.append(f"Total 5-year TCO (all): ${total_tco:,.0f}")
        ctx_lines.append(f"Potential GCP monthly savings (if all migrated): ${gcp_savings:,.0f}")
        ctx_lines.append("Ranked by AWS monthly cost (highest first):")
        for rank, e in enumerate(sorted_by_cost[:10], 1):
            ctx_lines.append(
                f"  #{rank} {e.get('customerName','?')} {e.get('version','')} — "
                f"${e.get('awsMonthlyCost',0):,.0f}/mo (AWS), "
                f"${e.get('gcpMonthlyCost',0):,.0f}/mo (GCP)"
            )
        ctx_lines.append("")

    context_block = "\n".join(ctx_lines) if ctx_lines else "No estimate data available."

    system_prompt = f"""You are a senior cloud FinOps advisor for BusinessNext, a financial-grade CRM platform.
You have deep expertise in AWS and GCP infrastructure pricing, sizing, and cost optimization.

USER ROLE: {current_user.get('role', 'user').upper()}

REAL PLATFORM DATA (use EXACT numbers from here in your responses):
{context_block}

RESPONSE STANDARDS — FOLLOW THESE STRICTLY:
1. ALWAYS use real numbers — never say "significant" without stating the actual dollar amount.
2. ALWAYS name specific estimates by their client name + version (e.g. "RHB V6"), never just "V6".
3. For ANY cost question, state: Monthly → Annual → 5-Year TCO.
4. For comparisons: show both values, the $ difference, and the % difference.
5. For optimization: give 3-5 specific actions, each with estimated $ savings per month.
6. Structure with bold headers, bullet points, and numbers.
7. If the user asks "which estimate" — look at the ranked list and name the #1 by client + version.
8. For questions about users/concurrency — use the metrics fields from context; if missing, say so clearly.
9. Compute and show math when relevant (e.g. "$10,372 × 12 = $124,464/yr × 5 = $622,320 5-year TCO").
10. DO NOT truncate. Give complete, thorough answers.
"""

    if not groq_key:
        q = body.question.lower()
        if body.all_estimates:
            ests = body.all_estimates
            sorted_e = sorted(ests, key=lambda x: x.get('awsMonthlyCost', 0), reverse=True)
            total = sum(e.get('awsMonthlyCost', 0) for e in ests)
            if any(kw in q for kw in ["highest", "most expensive", "top", "largest"]):
                top = sorted_e[0] if sorted_e else {}
                return {"answer": (
                    f"**Highest Monthly Cost: {top.get('customerName','?')} {top.get('version','')}**\n\n"
                    f"• AWS Monthly: **${top.get('awsMonthlyCost',0):,.0f}**\n"
                    f"• GCP Monthly: **${top.get('gcpMonthlyCost',0):,.0f}**\n"
                    f"• Annual (AWS): **${top.get('awsMonthlyCost',0)*12:,.0f}**\n"
                    f"• 5-Year TCO: **${top.get('aws5YearTCO',0):,.0f}**\n\n"
                    f"_Enable GROQ_API_KEY for full AI analysis._"
                )}
            return {"answer": (
                f"**Platform Overview ({len(ests)} estimates)**\n\n"
                f"• Combined AWS Monthly: **${total:,.0f}**\n"
                f"• Average per estimate: **${total // max(len(ests),1):,.0f}**\n"
                f"• Top estimate: **{sorted_e[0].get('customerName','?') if sorted_e else 'N/A'} — "
                f"${sorted_e[0].get('awsMonthlyCost',0):,.0f}/mo**\n\n"
                f"_Enable GROQ_API_KEY for detailed AI analysis._"
            )}
        if body.estimate_context:
            ec = body.estimate_context
            aws = ec.get('awsMonthlyCost', 0)
            return {"answer": (
                f"**{ec.get('customerName','?')} {ec.get('version','')}**\n\n"
                f"• AWS Monthly: **${aws:,.0f}** → Annual: **${aws*12:,.0f}**\n"
                f"• GCP Monthly: **${ec.get('gcpMonthlyCost',0):,.0f}**\n"
                f"• 5-Year TCO: **${ec.get('aws5YearTCO',0):,.0f}**\n"
                f"• Mode: {ec.get('clientMode','SaaS')} | DB: {ec.get('dbType','?')}\n\n"
                f"_Enable GROQ_API_KEY for full AI analysis._"
            )}
        return {"answer": "Configure **GROQ_API_KEY** in your .env to enable the AI Cost Copilot."}

    try:
        res = _req.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {groq_key}", "Content-Type": "application/json"},
            json={
                "model":       "llama-3.3-70b-versatile",
                "messages":    [
                    {"role": "system", "content": system_prompt},
                    {"role": "user",   "content": body.question},
                ],
                "temperature": 0.4,
                "max_tokens":  2000,
            },
            timeout=45,
        )
        res.raise_for_status()
        answer = res.json()["choices"][0]["message"]["content"].strip()
        return {"answer": answer, "model": "llama-3.3-70b-versatile"}
    except Exception as e:
        print(f"[copilot/chat] Groq error: {e}")
        return {"answer": f"I encountered an error processing your request. Please try again shortly. (Error: {str(e)[:100]})"}



@app.get("/api/pricing/status")
def get_pricing_status():
    """Return actual API connectivity status based on env credentials."""
    return _check_api_connectivity()



@app.get("/api/pricing/cache")
def get_pricing_cache():
    """Return pricing_cache.json contents enriched with live API status."""
    data = _load_pricing_cache()
    if not data:
        raise HTTPException(status_code=404, detail="pricing_cache.json not found")
    # Embed real-time connectivity so the frontend knows which regions are truly live
    data["api_status"] = _check_api_connectivity()
    return data


@app.post("/api/pricing/refresh")
async def refresh_pricing_cache(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)):
    """
    Refresh all regional pricing multipliers using Groq LLM (LLaMA 3.3 70B).
    Groq is asked to return the latest AWS and GCP on-demand pricing multipliers
    relative to each cloud's cheapest/base region. Results are validated and written
    to pricing_cache.json. Falls back to Python catalog if Groq is unavailable.
    Requires authentication.
    """
    import requests as _req

    get_current_user(credentials)   # auth check

    groq_key = os.getenv("GROQ_API_KEY", "").strip()
    now_iso  = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    now_date = datetime.utcnow().strftime("%B %Y")

    cache = _load_pricing_cache()
    if not cache:
        raise HTTPException(status_code=500, detail="Could not read pricing_cache.json")

    aws_live_set = set(cache.get("aws", {}).get("live_regions", []))
    gcp_live_set = set(cache.get("gcp", {}).get("live_regions", []))

    # ── Collect region IDs we need multipliers for ────────────────────────────
    try:
        from aws_machine_catalog import AWS_REGIONS as _AWS_REGIONS
        from gcp_pricer import GCP_REGIONS as _GCP_REGIONS
    except ImportError as e:
        raise HTTPException(status_code=500, detail=f"Could not import pricing catalogs: {e}")

    aws_saved_ids = [r for r in _AWS_REGIONS if r not in aws_live_set]
    gcp_saved_ids = [r for r in _GCP_REGIONS if r not in gcp_live_set]

    # ── Helper: call Groq chat completion ─────────────────────────────────────
    def _groq_chat(prompt: str, model: str = "llama-3.3-70b-versatile") -> str:
        resp = _req.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {groq_key}",
                "Content-Type":  "application/json",
            },
            json={
                "model":       model,
                "messages":    [{"role": "user", "content": prompt}],
                "temperature": 0.0,
                "max_tokens":  4096,
            },
            timeout=60,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()

    # ── Build prompt ──────────────────────────────────────────────────────────
    aws_list = "\n".join(aws_saved_ids)
    gcp_list = "\n".join(gcp_saved_ids)

    prompt = f"""You are a cloud pricing expert with up-to-date knowledge of AWS and GCP on-demand compute pricing.

Return ONLY a valid JSON object — no markdown, no explanation, no code fences.

The JSON must have this exact structure:
{{
  "aws": {{
    "<region-id>": {{ "multiplier": <float>, "label": "<human readable region name>" }},
    ...
  }},
  "gcp": {{
    "<region-id>": {{ "multiplier": <float>, "label": "<human readable region name>" }},
    ...
  }}
}}

Rules:
- Multipliers are relative to the cloud's cheapest on-demand compute region (us-east-1 for AWS, us-central1 for GCP = 1.000).
- Use 3 decimal places. Values typically range from 0.950 to 1.300.
- Use your most current pricing knowledge (today is approximately {now_date}).
- Include ONLY the regions listed below, nothing else.

AWS regions to price:
{aws_list}

GCP regions to price:
{gcp_list}
"""

    aws_saved: dict = {}
    gcp_saved: dict = {}
    source = "catalog"

    if groq_key:
        try:
            raw = _groq_chat(prompt)
            # Strip any accidental markdown fences
            raw = raw.strip()
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            parsed = _json.loads(raw)

            # Validate and build aws_saved
            for rid in aws_saved_ids:
                entry = parsed.get("aws", {}).get(rid)
                if entry and isinstance(entry.get("multiplier"), (int, float)):
                    mult = round(float(entry["multiplier"]), 3)
                    # Sanity-check: multiplier must be between 0.5 and 2.5
                    if 0.5 <= mult <= 2.5:
                        aws_saved[rid] = {
                            "label":      entry.get("label", _AWS_REGIONS.get(rid, {}).get("label", rid)),
                            "multiplier": mult,
                            "saved_at":   now_iso,
                        }

            # Validate and build gcp_saved
            for rid in gcp_saved_ids:
                entry = parsed.get("gcp", {}).get(rid)
                if entry and isinstance(entry.get("multiplier"), (int, float)):
                    mult = round(float(entry["multiplier"]), 3)
                    if 0.5 <= mult <= 2.5:
                        gcp_saved[rid] = {
                            "label":      entry.get("label", _GCP_REGIONS.get(rid, {}).get("label", rid)),
                            "multiplier": mult,
                            "saved_at":   now_iso,
                        }

            source = "groq-llm"
            print(f"[pricing/refresh] Groq returned {len(aws_saved)} AWS + {len(gcp_saved)} GCP regions")

        except Exception as groq_err:
            print(f"[pricing/refresh] Groq failed ({groq_err}), falling back to catalog")

    # Fill any missing regions from the Python catalog (fallback)
    for rid in aws_saved_ids:
        if rid not in aws_saved:
            info = _AWS_REGIONS.get(rid, {})
            aws_saved[rid] = {
                "label":      info.get("label", rid),
                "multiplier": round(info.get("multiplier", 1.0), 3),
                "saved_at":   now_iso,
            }

    for rid in gcp_saved_ids:
        if rid not in gcp_saved:
            info = _GCP_REGIONS.get(rid, {})
            gcp_saved[rid] = {
                "label":      info.get("label", rid),
                "multiplier": round(info.get("multiplier", 1.0), 3),
                "saved_at":   now_iso,
            }

    # ── Persist ───────────────────────────────────────────────────────────────
    cache.setdefault("aws", {})["saved_regions"] = aws_saved
    cache.setdefault("gcp", {})["saved_regions"] = gcp_saved
    cache.setdefault("meta", {})["saved_at"]      = now_iso
    cache["meta"]["pricing_date"]                 = now_date
    cache["meta"]["source"]                       = source

    _save_pricing_cache(cache)

    return {
        "status":            "ok",
        "source":            source,
        "refreshed_at":      now_iso,
        "pricing_date":      now_date,
        "aws_saved_count":   len(aws_saved),
        "gcp_saved_count":   len(gcp_saved),
        "groq_used":         source == "groq-llm",
    }


# ── Health check ──────────────────────────────────────────────────────────────

@app.get("/api/health")
def health():
    return {"status": "ok", "service": "BusinessNext API", "version": "1.0.0"}


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api_server:app", host="0.0.0.0", port=8000, reload=True)
