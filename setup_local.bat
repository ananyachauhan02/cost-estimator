@echo off
setlocal EnableDelayedExpansion

:: =============================================================================
:: Cost Estimator — Local Development Setup (Windows)
:: Mirrors setup_local.sh
:: Handles: Python venv, dependencies, DB (via Docker), and app startup
:: Run from the project root directory in Command Prompt or PowerShell.
:: =============================================================================

set VENV_DIR=venv

:: ── Step 1: Check Python ──────────────────────────────────────────────────────
echo.
echo ======================================
echo   Checking Python installation
echo ======================================
where python >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found in PATH.
    echo         Please install Python 3.10+ from https://www.python.org/downloads/
    echo         and ensure "Add Python to PATH" is checked during install.
    exit /b 1
)
python --version
echo [OK] Python found.

:: ── Step 2: Create Virtual Environment ───────────────────────────────────────
echo.
echo ======================================
echo   Setting up virtual environment
echo ======================================
if exist "%VENV_DIR%\" (
    echo [INFO] Virtual environment already exists at .\%VENV_DIR% -- skipping creation.
) else (
    python -m venv %VENV_DIR%
    echo [OK] Created virtual environment at .\%VENV_DIR%
)

:: ── Step 3: Activate venv ─────────────────────────────────────────────────────
echo.
echo ======================================
echo   Activating virtual environment
echo ======================================
call %VENV_DIR%\Scripts\activate.bat
if errorlevel 1 (
    echo [ERROR] Failed to activate virtual environment.
    exit /b 1
)
echo [OK] Virtual environment activated.

:: ── Step 4: Upgrade pip ───────────────────────────────────────────────────────
echo.
echo ======================================
echo   Upgrading pip
echo ======================================
python -m pip install --upgrade pip --quiet
echo [OK] pip upgraded.

:: ── Step 5: Install Dependencies ─────────────────────────────────────────────
echo.
echo ======================================
echo   Installing dependencies
echo ======================================
pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Dependency installation failed.
    exit /b 1
)
echo [OK] All packages installed.

:: ── Step 6: Start PostgreSQL via Docker (optional) ───────────────────────────
echo.
echo ======================================
echo   Starting PostgreSQL database
echo ======================================
where docker >nul 2>&1
if errorlevel 1 (
    echo [WARN] Docker not found. Make sure PostgreSQL is running on localhost:5432
) else (
    docker compose up -d db
    if errorlevel 1 (
        echo [WARN] Could not start DB via docker compose. Start PostgreSQL manually.
    ) else (
        echo [OK] PostgreSQL is running on localhost:5432
    )
)

:: ── Step 7: Set local DB environment variables ───────────────────────────────
echo.
echo ======================================
echo   Configuring environment variables
echo ======================================
set DB_HOST=localhost
set DB_PORT=5432
set DB_USER=costuser
set DB_PASS=12345abcde
set DB_NAME=costdb
echo [OK] DB env vars set (DB_HOST=localhost, DB_NAME=costdb)

:: Load .env file if present (basic key=value, no quotes needed)
if exist ".env" (
    echo [INFO] Loading variables from .env ...
    for /f "usebackq tokens=1,* delims==" %%K in (".env") do (
        set "LINE=%%K"
        if not "!LINE:~0,1!"=="#" (
            if not "%%K"=="" set "%%K=%%L"
        )
    )
    echo [OK] .env loaded.
)

:: ── Step 8: Run the App ───────────────────────────────────────────────────────
echo.
echo ======================================
echo   Starting Streamlit application
echo ======================================
echo Access the app at: http://localhost:8501
echo Press Ctrl+C to stop.
echo.
streamlit run app.py --server.port=8501 --server.address=localhost

endlocal
