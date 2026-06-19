#!/bin/bash

# =============================================================================
# Cost Estimator — Local Development Setup
# Handles: Python venv, dependencies, DB (via Docker), and app startup
# =============================================================================

set -e

VENV_DIR="venv"
PYTHON="python3"

# ── Helper ────────────────────────────────────────────────────────────────────
print_step() {
    echo ""
    echo "======================================"
    echo "  $1"
    echo "======================================"
}

# ── Step 1: Check Python ──────────────────────────────────────────────────────
print_step "Checking Python installation"
if ! command -v $PYTHON &> /dev/null; then
    echo "❌ Python3 not found. Please install Python 3.10 or higher."
    exit 1
fi
PYTHON_VERSION=$($PYTHON --version 2>&1)
echo "✅ Found: $PYTHON_VERSION"

# ── Step 2: Create Virtual Environment ───────────────────────────────────────
print_step "Setting up virtual environment"
if [ -d "$VENV_DIR" ]; then
    echo "ℹ️  Virtual environment already exists at ./$VENV_DIR — skipping creation."
else
    $PYTHON -m venv $VENV_DIR
    echo "✅ Created virtual environment at ./$VENV_DIR"
fi

# ── Step 3: Activate venv ─────────────────────────────────────────────────────
print_step "Activating virtual environment"
source $VENV_DIR/bin/activate
echo "✅ Activated: $(which python)"

# ── Step 4: Upgrade pip ───────────────────────────────────────────────────────
print_step "Upgrading pip"
pip install --upgrade pip --quiet
echo "✅ pip upgraded"

# ── Step 5: Install Dependencies ─────────────────────────────────────────────
print_step "Installing dependencies from requirements.txt"
pip install -r requirements.txt
echo "✅ All packages installed"

# ── Step 6: Start PostgreSQL via Docker (optional) ───────────────────────────
print_step "Starting PostgreSQL database"
if command -v docker &> /dev/null || command -v sudo docker &> /dev/null; then

    DC=""
    if docker compose version &> /dev/null 2>&1; then
        DC="docker compose"
    elif sudo docker compose version &> /dev/null 2>&1; then
        DC="sudo docker compose"
    fi

    if [ -n "$DC" ]; then
        echo "Starting only the DB service via docker compose..."
        $DC up -d db
        echo "✅ PostgreSQL is running on localhost:5432"
    else
        echo "⚠️  docker compose not found. Please start PostgreSQL manually."
    fi
else
    echo "⚠️  Docker not found. Make sure PostgreSQL is running on localhost:5432"
fi

# ── Step 7: Set local DB environment variables ───────────────────────────────
print_step "Configuring environment variables"
export DB_HOST=localhost
export DB_PORT=5432
export DB_USER=costuser
export DB_PASS=12345abcde
export DB_NAME=costdb
echo "✅ DB env vars set (DB_HOST=localhost, DB_NAME=costdb)"

# ── Step 8: Run the App ───────────────────────────────────────────────────────
print_step "Starting Streamlit application"
echo "Access the app at: http://localhost:8501"
echo "Press Ctrl+C to stop."
echo ""
streamlit run app.py --server.port=8501 --server.address=localhost
