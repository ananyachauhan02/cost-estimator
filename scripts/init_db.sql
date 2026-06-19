-- =============================================================================
-- Cost Estimator — Database Initialization Script
-- PostgreSQL 15+
-- Run once on first deploy. Safe to re-run (uses IF NOT EXISTS).
-- =============================================================================

-- ── Extensions ────────────────────────────────────────────────────────────────
CREATE EXTENSION IF NOT EXISTS pgcrypto;  -- used for gen_random_uuid() if needed

-- ── Users ─────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
    id            SERIAL PRIMARY KEY,
    name          VARCHAR,
    email         VARCHAR NOT NULL UNIQUE,
    password_hash VARCHAR NOT NULL,
    role          VARCHAR NOT NULL DEFAULT 'viewer',
    created_at    TIMESTAMP DEFAULT NOW()
);

-- ── Clients ───────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS clients (
    id         SERIAL PRIMARY KEY,
    name       VARCHAR NOT NULL,
    sector     VARCHAR DEFAULT 'Banking',
    created_at TIMESTAMP DEFAULT NOW()
);

-- ── Estimates ─────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS estimates (
    id                         SERIAL PRIMARY KEY,
    client_id                  INTEGER REFERENCES clients(id) ON DELETE SET NULL,
    version                    INTEGER DEFAULT 1,
    customer_name              VARCHAR NOT NULL,
    estimate_date              TIMESTAMP DEFAULT NOW(),
    client_mode                VARCHAR DEFAULT 'saas',
    db_type                    VARCHAR DEFAULT 'PostgreSQL',
    years                      INTEGER NOT NULL,
    created_at                 TIMESTAMP DEFAULT NOW(),

    -- Sizing metrics
    total_workernodes          FLOAT,
    total_vcpus_workernode     FLOAT,
    total_memory_workernode_gb FLOAT,
    postgres_ram_gb            FLOAT,
    sql_server_ram_gb          FLOAT,
    oracle_ram_gb              FLOAT,
    data_size_gb               FLOAT,
    s3_size_gb                 FLOAT,

    -- Pricing totals
    total_monthly_usd          FLOAT,
    total_annual_usd           FLOAT,
    total_5year_usd            FLOAT,

    -- JSON blobs
    all_metrics                JSONB,
    pricing_json               JSONB,
    distribution_json          JSONB,
    env_pricing_json           JSONB,

    -- Binary file attachments
    cloud_sizing_file          BYTEA,
    aws_pricing_file           BYTEA,

    notes                      TEXT DEFAULT ''
);

-- ── Indexes ───────────────────────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_users_email         ON users(email);
CREATE INDEX IF NOT EXISTS idx_clients_name        ON clients(name);
CREATE INDEX IF NOT EXISTS idx_estimates_client_id ON estimates(client_id);
CREATE INDEX IF NOT EXISTS idx_estimates_created   ON estimates(created_at DESC);

-- ── Seed: Default Admin User ──────────────────────────────────────────────────
-- Credentials: admin@businessnext.com / admin123
-- Hash generated via: bcrypt.hashpw(b'admin123', bcrypt.gensalt())
INSERT INTO users (name, email, password_hash, role)
SELECT 'System Admin', 'admin@businessnext.com', '$2b$12$ubvqP72Ch2YarbPrGILnwu8bpLfyf2WjgCVqrksEIcnTHSnBt0DMO', 'admin'
WHERE NOT EXISTS (
    SELECT 1 FROM users WHERE email = 'admin@businessnext.com'
);

-- ── Seed: Sample Clients ──────────────────────────────────────────────────────
INSERT INTO clients (name, sector)
SELECT 'SBI Bank',      'Banking'
WHERE NOT EXISTS (SELECT 1 FROM clients WHERE name = 'SBI Bank');

INSERT INTO clients (name, sector)
SELECT 'HDFC Bank',     'Banking'
WHERE NOT EXISTS (SELECT 1 FROM clients WHERE name = 'HDFC Bank');

INSERT INTO clients (name, sector)
SELECT 'ICICI Bank',    'Banking'
WHERE NOT EXISTS (SELECT 1 FROM clients WHERE name = 'ICICI Bank');

INSERT INTO clients (name, sector)
SELECT 'Bajaj Allianz', 'Insurance'
WHERE NOT EXISTS (SELECT 1 FROM clients WHERE name = 'Bajaj Allianz');

INSERT INTO clients (name, sector)
SELECT 'Emirates NBD',  'Banking'
WHERE NOT EXISTS (SELECT 1 FROM clients WHERE name = 'Emirates NBD');

-- ── Done ──────────────────────────────────────────────────────────────────────
DO $$
BEGIN
    RAISE NOTICE '✅ Cost Estimator DB initialized successfully.';
END
$$;
