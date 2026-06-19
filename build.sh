#!/bin/bash

# =============================================================================
# Cost Estimator — Docker Build & Run Script
# Supports semantic versioning: MAJOR.MINOR.PATCH.BUILD  (e.g. 1.0.0.3)
# Usage:
#   ./build.sh              → auto-increments build number (1.0.0.1 → 1.0.0.2)
#   ./build.sh --version    → show current version, no build
#   ./build.sh --major      → bump major  (1.0.0.x → 2.0.0.1)
#   ./build.sh --minor      → bump minor  (1.0.0.x → 1.1.0.1)
#   ./build.sh --patch      → bump patch  (1.0.0.x → 1.0.1.1)
#   ./build.sh --no-bump    → build with current version, don't increment
# =============================================================================

set -e

IMAGE_NAME="cost-estimator"
CONTAINER_NAME="cost-estimator-app"
VERSION_FILE="VERSION"

# ── Determine sudo prefix ─────────────────────────────────────────────────────
if docker info > /dev/null 2>&1; then
    DC="docker compose"
    DK="docker"
elif sudo docker info > /dev/null 2>&1; then
    DC="sudo docker compose"
    DK="sudo docker"
    echo "⚠️  Using sudo for Docker. Run 'sudo usermod -aG docker \$USER' to avoid this."
else
    echo "❌ Cannot connect to Docker daemon. Run: sudo systemctl start docker"
    exit 1
fi

# ── Read current version ──────────────────────────────────────────────────────
if [ ! -f "$VERSION_FILE" ]; then
    echo "1.0.0.1" > "$VERSION_FILE"
fi

CURRENT_VERSION=$(cat "$VERSION_FILE" | tr -d '[:space:]')

# Parse into parts: MAJOR.MINOR.PATCH.BUILD
IFS='.' read -r MAJOR MINOR PATCH BUILD <<< "$CURRENT_VERSION"

# ── Handle flags ──────────────────────────────────────────────────────────────
BUMP="build"   # default: bump build number only

for arg in "$@"; do
    case $arg in
        --version)
            echo "Current image version: $CURRENT_VERSION"
            exit 0
            ;;
        --major)   BUMP="major" ;;
        --minor)   BUMP="minor" ;;
        --patch)   BUMP="patch" ;;
        --no-bump) BUMP="none"  ;;
        *)
            echo "Unknown option: $arg"
            echo "Usage: $0 [--version | --major | --minor | --patch | --no-bump]"
            exit 1
            ;;
    esac
done

# ── Compute new version ───────────────────────────────────────────────────────
case $BUMP in
    major)
        MAJOR=$((MAJOR + 1)); MINOR=0; PATCH=0; BUILD=1
        ;;
    minor)
        MINOR=$((MINOR + 1)); PATCH=0; BUILD=1
        ;;
    patch)
        PATCH=$((PATCH + 1)); BUILD=1
        ;;
    build)
        BUILD=$((BUILD + 1))
        ;;
    none)
        : # keep current version
        ;;
esac

NEW_VERSION="${MAJOR}.${MINOR}.${PATCH}.${BUILD}"
FULL_IMAGE="${IMAGE_NAME}:${NEW_VERSION}"
LATEST_IMAGE="${IMAGE_NAME}:latest"

# ── Show version info ─────────────────────────────────────────────────────────
echo ""
echo "======================================"
echo "  Version:  $CURRENT_VERSION  →  $NEW_VERSION"
echo "  Image:    $FULL_IMAGE"
echo "======================================"

# ── Build Docker image ────────────────────────────────────────────────────────
echo ""
echo "======================================"
echo "  Building Docker image"
echo "======================================"
$DK build \
    --build-arg APP_VERSION="$NEW_VERSION" \
    -t "$FULL_IMAGE" \
    -t "$LATEST_IMAGE" \
    .

echo "✅ Tagged as:"
echo "   • $FULL_IMAGE"
echo "   • $LATEST_IMAGE"

# ── Save new version to file ──────────────────────────────────────────────────
if [ "$BUMP" != "none" ]; then
    echo "$NEW_VERSION" > "$VERSION_FILE"
    echo ""
    echo "📝 VERSION file updated → $NEW_VERSION"
fi

# ── Stop old containers ───────────────────────────────────────────────────────
echo ""
echo "======================================"
echo "  Stopping old containers (if any)"
echo "======================================"
$DC down --remove-orphans 2>/dev/null || true

# ── Start services via docker compose ────────────────────────────────────────
echo ""
echo "======================================"
echo "  Starting services"
echo "======================================"
APP_VERSION="$NEW_VERSION" $DC up -d

echo ""
echo "======================================"
echo "✅ App is running at: http://localhost:8501"
echo "   Version: $NEW_VERSION"
echo "======================================"
echo ""
echo "  Useful commands:"
echo "  • View app logs  : $DC logs -f app"
echo "  • Check version  : ./build.sh --version"
echo "  • Bump minor     : ./build.sh --minor"
echo "  • Bump patch     : ./build.sh --patch"
echo "  • Stop all       : $DC down"
