"""
database.py — Full storage: users, clients, estimates, pricing, distribution, env pricing, Excel files
"""
import os
from datetime import datetime
from dotenv import load_dotenv
from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, JSON, LargeBinary, String, Text, create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

load_dotenv()

DB_USER = os.getenv("DB_USER", "costuser")
DB_PASS = os.getenv("DB_PASS", "12345abcde")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "costdb")
DATABASE_URL = f"postgresql+psycopg2://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

engine       = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base         = declarative_base()


# ── Models ────────────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id            = Column(Integer, primary_key=True, index=True)
    name          = Column(String, nullable=True)
    email         = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    role          = Column(String, default="viewer", nullable=False)
    created_at    = Column(DateTime, default=datetime.utcnow)


class Client(Base):
    __tablename__ = "clients"

    id         = Column(Integer, primary_key=True, index=True)
    name       = Column(String, nullable=False, index=True)
    sector     = Column(String, default="Banking")
    created_at = Column(DateTime, default=datetime.utcnow)


class Estimate(Base):
    __tablename__ = "estimates"

    id            = Column(Integer, primary_key=True, index=True)
    client_id     = Column(Integer, ForeignKey("clients.id"), nullable=True, index=True)
    version       = Column(Integer, default=1)
    customer_name = Column(String, nullable=False, index=True)
    estimate_date = Column(DateTime, default=datetime.utcnow)
    client_mode   = Column(String, default="saas")
    db_type       = Column(String, default="PostgreSQL")
    years         = Column(Integer, nullable=False)
    created_at    = Column(DateTime, default=datetime.utcnow)

    total_workernodes          = Column(Float)
    total_vcpus_workernode     = Column(Float)
    total_memory_workernode_gb = Column(Float)
    postgres_ram_gb            = Column(Float)
    sql_server_ram_gb          = Column(Float)
    oracle_ram_gb              = Column(Float)
    data_size_gb               = Column(Float)
    s3_size_gb                = Column(Float)

    all_metrics       = Column(JSON)
    pricing_json      = Column(JSON)
    distribution_json = Column(JSON)
    env_pricing_json  = Column(JSON)

    total_monthly_usd = Column(Float)
    total_annual_usd  = Column(Float)
    total_5year_usd   = Column(Float)

    cloud_sizing_file = Column(LargeBinary)
    aws_pricing_file  = Column(LargeBinary)
    notes             = Column(Text, default="")


# ── Init ──────────────────────────────────────────────────────────────────

def init_db():
    Base.metadata.create_all(bind=engine)
    print("[database] Tables created or already exist.")
    
    # Simple migration for existing DB users table
    try:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS role VARCHAR DEFAULT 'viewer'"))
            conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS name VARCHAR"))
    except Exception as e:
        print(f"[database] Migration skipped/failed: {e}")
        
    _seed_defaults()


def _seed_defaults():
    """Seed a default admin user and sample clients if they don't exist."""
    try:
        import bcrypt
    except ImportError:
        print("[database] bcrypt not installed — skipping seed.")
        return

    db = SessionLocal()
    try:
        # Default admin user
        if not db.query(User).filter(User.email == "admin@businessnext.com").first():
            hashed = bcrypt.hashpw(b"admin123", bcrypt.gensalt()).decode()
            db.add(User(email="admin@businessnext.com", name="System Admin", role="admin", password_hash=hashed))
            print("[database] Seeded default admin user.")

        # Sample clients (only seed if the table is completely empty)
        if db.query(Client).count() == 0:
            sample_clients = [
                ("SBI Bank",         "Banking"),
                ("HDFC Bank",        "Banking"),
                ("ICICI Bank",       "Banking"),
                ("Bajaj Allianz",    "Insurance"),
                ("Emirates NBD",     "Banking"),
            ]
            for name, sector in sample_clients:
                db.add(Client(name=name, sector=sector))
            db.commit()
            print("[database] Sample clients seeded.")
    except Exception as e:
        db.rollback()
        print(f"[database] Seed failed: {e}")
    finally:
        db.close()


# ── User helpers ──────────────────────────────────────────────────────────

def create_user(email: str, password: str, name: str = None, role: str = "viewer") -> int:
    import bcrypt
    db = SessionLocal()
    try:
        hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        user = User(email=email, name=name, role=role, password_hash=hashed)
        db.add(user); db.commit(); db.refresh(user)
        return user.id
    except Exception as e:
        db.rollback(); raise
    finally:
        db.close()


def verify_user(email: str, password: str):
    """Return User dict on success, None on failure."""
    import bcrypt
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        if not user:
            return None
        if bcrypt.checkpw(password.encode(), user.password_hash.encode()):
            role = user.role if user.role else "viewer" # Fallback just in case
            return {"id": user.id, "email": user.email, "name": user.name, "role": role}
        return None
    finally:
        db.close()

def get_all_users():
    db = SessionLocal()
    try:
        users = db.query(User).order_by(User.id).all()
        return [{"id": u.id, "email": u.email, "name": u.name, "role": u.role, "created_at": u.created_at} for u in users]
    finally:
        db.close()

def update_user(user_id: int, role: str, name: str = None) -> bool:
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user: return False
        user.role = role
        user.name = name
        db.commit()
        return True
    except Exception:
        db.rollback(); return False
    finally:
        db.close()

def delete_user(user_id: int) -> bool:
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user: return False
        db.delete(user)
        db.commit()
        return True
    except Exception:
        db.rollback(); return False
    finally:
        db.close()


# ── Client helpers ────────────────────────────────────────────────────────

def get_all_clients():
    db = SessionLocal()
    try:
        # Expire all cached objects in this session to force a fresh DB read
        db.expire_all()
        clients = db.query(Client).order_by(Client.created_at.asc()).all()
        result = []
        for c in clients:
            count = db.query(Estimate).filter(Estimate.client_id == c.id).count()
            last  = db.query(Estimate.created_at).filter(
                        Estimate.client_id == c.id
                    ).order_by(Estimate.created_at.desc()).first()
            result.append({
                "id": c.id, "name": c.name, "sector": c.sector,
                "created_at": c.created_at,
                "estimate_count": count,
                "last_estimate": last[0] if last else None,
            })
        return result
    finally:
        db.close()


def create_client(name: str, sector: str = "Banking") -> int:
    db = SessionLocal()
    try:
        client = Client(name=name, sector=sector)
        db.add(client); db.commit(); db.refresh(client)
        return client.id
    except Exception as e:
        db.rollback(); raise
    finally:
        db.close()


def get_client_by_id(client_id: int):
    db = SessionLocal()
    try:
        c = db.query(Client).filter(Client.id == client_id).first()
        if not c:
            return None
        return {"id": c.id, "name": c.name, "sector": c.sector}
    finally:
        db.close()


def delete_client(client_id: int) -> bool:
    print(f"DEBUG: delete_client called with client_id={client_id}")
    db = SessionLocal()
    try:
        # First delete all associated estimates to satisfy foreign key constraints
        db.query(Estimate).filter(Estimate.client_id == client_id).delete()
        
        # Then delete the client
        deleted = db.query(Client).filter(Client.id == client_id).delete()
        db.commit()
        return deleted > 0
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()


# ── Estimate helpers ──────────────────────────────────────────────────────

def get_estimates_by_client(client_id: int):
    db = SessionLocal()
    try:
        rows = db.query(
            Estimate.id, Estimate.version, Estimate.customer_name,
            Estimate.estimate_date, Estimate.client_mode, Estimate.db_type,
            Estimate.years, Estimate.total_monthly_usd, Estimate.total_annual_usd,
            Estimate.total_5year_usd, Estimate.total_workernodes,
            Estimate.created_at, Estimate.notes,
        ).filter(Estimate.client_id == client_id).order_by(Estimate.version.desc()).all()
        return [r._asdict() for r in rows]
    finally:
        db.close()


def save_estimate(customer_name, estimate_date, years, metrics,
                  client_mode="saas", db_type="PostgreSQL",
                  pricing=None, distribution=None, env_pricing=None,
                  cloud_sizing_path=None, aws_pricing_path=None,
                  notes="", client_id=None):
    db = SessionLocal()
    try:
        cloud_bytes   = open(cloud_sizing_path, "rb").read() if cloud_sizing_path and os.path.exists(cloud_sizing_path) else None
        pricing_bytes = open(aws_pricing_path, "rb").read()  if aws_pricing_path  and os.path.exists(aws_pricing_path)  else None
        monthly = pricing.get("total_monthly_usd", 0) if pricing else 0
        annual  = pricing.get("total_annual_usd",  0) if pricing else 0
        five_yr = pricing.get("inflation_forecast", {}).get("five_year_total", 0) if pricing else 0

        # Auto-increment version per client
        version = 1
        if client_id:
            last = db.query(Estimate.version).filter(
                Estimate.client_id == client_id
            ).order_by(Estimate.version.desc()).first()
            if last:
                version = last[0] + 1

        row = Estimate(
            client_id=client_id, version=version,
            customer_name=customer_name, estimate_date=estimate_date,
            client_mode=client_mode, db_type=db_type, years=years,
            total_workernodes=metrics.get("total_workernodes"),
            total_vcpus_workernode=metrics.get("total_vcpus_workernode"),
            total_memory_workernode_gb=metrics.get("total_memory_workernode_gb"),
            postgres_ram_gb=metrics.get("postgres_ram_gb"),
            sql_server_ram_gb=metrics.get("sql_server_ram_gb"),
            oracle_ram_gb=metrics.get("oracle_ram_gb"),
            data_size_gb=metrics.get("data_size_gb"),
            s3_size_gb=metrics.get("s3_size_gb"),
            all_metrics=metrics, pricing_json=pricing,
            distribution_json=distribution, env_pricing_json=env_pricing,
            total_monthly_usd=monthly, total_annual_usd=annual, total_5year_usd=five_yr,
            cloud_sizing_file=cloud_bytes, aws_pricing_file=pricing_bytes, notes=notes,
        )
        db.add(row); db.commit(); db.refresh(row)
        print(f"[database] Saved estimate id={row.id} v{version} for '{customer_name}'")
        return row.id
    except Exception as e:
        db.rollback(); print(f"[database] Save failed: {e}"); raise
    finally:
        db.close()


def get_all_estimates():
    db = SessionLocal()
    try:
        rows = db.query(
            Estimate.id, Estimate.customer_name, Estimate.estimate_date,
            Estimate.client_mode, Estimate.db_type, Estimate.years,
            Estimate.total_monthly_usd, Estimate.total_annual_usd,
            Estimate.total_5year_usd, Estimate.total_workernodes,
            Estimate.created_at, Estimate.notes,
        ).order_by(Estimate.created_at.desc()).all()
        return [r._asdict() for r in rows]
    finally:
        db.close()


def get_estimate_by_id(estimate_id):
    db = SessionLocal()
    try:
        row = db.query(Estimate).filter(Estimate.id == estimate_id).first()
        if not row:
            return None
        return {
            "id": row.id, "customer_name": row.customer_name,
            "estimate_date": row.estimate_date, "client_mode": row.client_mode,
            "db_type": row.db_type, "years": row.years, "created_at": row.created_at,
            "version": row.version, "client_id": row.client_id,
            "total_monthly_usd": row.total_monthly_usd, "total_annual_usd": row.total_annual_usd,
            "total_5year_usd": row.total_5year_usd, "total_workernodes": row.total_workernodes,
            "notes": row.notes, "all_metrics": row.all_metrics,
            "pricing_json": row.pricing_json, "distribution_json": row.distribution_json,
            "env_pricing_json": row.env_pricing_json,
        }
    finally:
        db.close()


def get_estimate_files(estimate_id):
    db = SessionLocal()
    try:
        row = db.query(Estimate.customer_name, Estimate.cloud_sizing_file, Estimate.aws_pricing_file
                       ).filter(Estimate.id == estimate_id).first()
        if not row:
            return {}
        return {"customer_name": row.customer_name,
                "cloud_sizing": row.cloud_sizing_file,
                "aws_pricing": row.aws_pricing_file}
    finally:
        db.close()


def delete_estimate(estimate_id):
    db = SessionLocal()
    try:
        row = db.query(Estimate).filter(Estimate.id == estimate_id).first()
        if not row:
            return False
        db.delete(row); db.commit(); return True
    except Exception as e:
        db.rollback(); print(f"[database] Delete failed: {e}"); return False
    finally:
        db.close()

def reset_user_password(user_id: int, new_password: str) -> bool:
    import bcrypt
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user: return False
        hashed = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()
        user.password_hash = hashed
        db.commit()
        return True
    except Exception:
        db.rollback()
        return False
    finally:
        db.close()
    return False
