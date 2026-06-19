@echo off
setlocal EnableDelayedExpansion

:: =============================================================================
:: Cost Estimator — Docker Build ^& Run Script (Windows)
:: Mirrors build.sh — supports semantic versioning: MAJOR.MINOR.PATCH.BUILD
:: Usage:
::   build.bat              -> auto-increments build number (1.0.0.1 -> 1.0.0.2)
::   build.bat --version    -> show current version, no build
::   build.bat --major      -> bump major  (1.0.0.x -> 2.0.0.1)
::   build.bat --minor      -> bump minor  (1.0.0.x -> 1.1.0.1)
::   build.bat --patch      -> bump patch  (1.0.0.x -> 1.0.1.1)
::   build.bat --no-bump    -> build with current version, don't increment
:: =============================================================================

set IMAGE_NAME=cost-estimator
set CONTAINER_NAME=cost-estimator-app
set VERSION_FILE=VERSION
set BUMP=build

:: ── Parse arguments ───────────────────────────────────────────────────────────
for %%A in (%*) do (
    if "%%A"=="--version"  set SHOW_VER=1
    if "%%A"=="--major"    set BUMP=major
    if "%%A"=="--minor"    set BUMP=minor
    if "%%A"=="--patch"    set BUMP=patch
    if "%%A"=="--no-bump"  set BUMP=none
)

:: ── Check Docker ──────────────────────────────────────────────────────────────
docker info >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Cannot connect to Docker daemon.
    echo         Make sure Docker Desktop is running.
    exit /b 1
)

:: ── Read current version ──────────────────────────────────────────────────────
if not exist "%VERSION_FILE%" (
    echo 1.0.0.1 > "%VERSION_FILE%"
)

set /p CURRENT_VERSION=<"%VERSION_FILE%"
:: Trim whitespace
for /f "tokens=* delims= " %%V in ("%CURRENT_VERSION%") do set CURRENT_VERSION=%%V

:: Parse MAJOR.MINOR.PATCH.BUILD
for /f "tokens=1-4 delims=." %%A in ("%CURRENT_VERSION%") do (
    set MAJOR=%%A
    set MINOR=%%B
    set PATCH=%%C
    set BUILD=%%D
)

:: ── Show version and exit if --version ────────────────────────────────────────
if defined SHOW_VER (
    echo Current image version: %CURRENT_VERSION%
    exit /b 0
)

:: ── Compute new version ───────────────────────────────────────────────────────
if "%BUMP%"=="major" (
    set /a MAJOR=MAJOR+1
    set MINOR=0
    set PATCH=0
    set BUILD=1
)
if "%BUMP%"=="minor" (
    set /a MINOR=MINOR+1
    set PATCH=0
    set BUILD=1
)
if "%BUMP%"=="patch" (
    set /a PATCH=PATCH+1
    set BUILD=1
)
if "%BUMP%"=="build" (
    set /a BUILD=BUILD+1
)

set NEW_VERSION=%MAJOR%.%MINOR%.%PATCH%.%BUILD%
set FULL_IMAGE=%IMAGE_NAME%:%NEW_VERSION%
set LATEST_IMAGE=%IMAGE_NAME%:latest

:: ── Show version info ─────────────────────────────────────────────────────────
echo.
echo ======================================
echo   Version:  %CURRENT_VERSION%  -^>  %NEW_VERSION%
echo   Image:    %FULL_IMAGE%
echo ======================================

:: ── Build Docker image ────────────────────────────────────────────────────────
echo.
echo ======================================
echo   Building Docker image
echo ======================================
docker build --build-arg APP_VERSION="%NEW_VERSION%" -t "%FULL_IMAGE%" -t "%LATEST_IMAGE%" .
if errorlevel 1 (
    echo [ERROR] Docker build failed.
    exit /b 1
)

echo [OK] Tagged as:
echo      - %FULL_IMAGE%
echo      - %LATEST_IMAGE%

:: ── Save new version to file ──────────────────────────────────────────────────
if not "%BUMP%"=="none" (
    echo %NEW_VERSION%> "%VERSION_FILE%"
    echo.
    echo [OK] VERSION file updated -^> %NEW_VERSION%
)

:: ── Stop old containers ───────────────────────────────────────────────────────
echo.
echo ======================================
echo   Stopping old containers (if any)
echo ======================================
docker compose down --remove-orphans 2>nul

:: ── Start services via docker compose ────────────────────────────────────────
echo.
echo ======================================
echo   Starting services
echo ======================================
set APP_VERSION=%NEW_VERSION%
docker compose up -d
if errorlevel 1 (
    echo [ERROR] docker compose up failed.
    exit /b 1
)

echo.
echo ======================================
echo [OK] App is running at: http://localhost:8501
echo      Version: %NEW_VERSION%
echo ======================================
echo.
echo   Useful commands:
echo   - View app logs  : docker compose logs -f app
echo   - Check version  : build.bat --version
echo   - Bump minor     : build.bat --minor
echo   - Bump patch     : build.bat --patch
echo   - Stop all       : docker compose down
echo.

endlocal
