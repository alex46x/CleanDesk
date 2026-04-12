# scripts/build.ps1 — Full Windows production build script
#
# Usage:
#   .\scripts\build.ps1          # Full build (backend + frontend + installer)
#   .\scripts\build.ps1 -Backend # Backend only
#   .\scripts\build.ps1 -Frontend # Frontend only
#
# Requirements:
#   - Python 3.11+  (in PATH)
#   - Node.js 20+   (in PATH)
#   - Rust 1.75+    (in PATH, via rustup)
#   - PyInstaller   (installed via pip)

param(
    [switch]$Backend,
    [switch]$Frontend,
    [switch]$RustEngine,
    [switch]$SkipTests
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot

function Write-Step {
    param([string]$Message)
    Write-Host "`n━━━ $Message ━━━" -ForegroundColor Cyan
}

function Write-Success {
    param([string]$Message)
    Write-Host "✓  $Message" -ForegroundColor Green
}

function Write-Fail {
    param([string]$Message)
    Write-Host "✗  $Message" -ForegroundColor Red
    exit 1
}

# Determine what to build
$BuildAll = -not ($Backend -or $Frontend -or $RustEngine)

# ───────────────────────────────────────────────────────────────────────────
# 0. Prerequisites check
# ───────────────────────────────────────────────────────────────────────────
Write-Step "Checking prerequisites"

if (-not (Get-Command python -ErrorAction SilentlyContinue)) { Write-Fail "Python not found" }
if (-not (Get-Command node   -ErrorAction SilentlyContinue)) { Write-Fail "Node.js not found" }
if (-not (Get-Command cargo  -ErrorAction SilentlyContinue)) { Write-Fail "Rust/Cargo not found" }

$PyVer  = (python --version 2>&1) -replace "Python ", ""
$NodeVer = (node --version)
$RustVer = (rustc --version)
Write-Success "Python $PyVer | Node $NodeVer | Rust: $RustVer"

# ───────────────────────────────────────────────────────────────────────────
# 1. Rust engine
# ───────────────────────────────────────────────────────────────────────────
if ($BuildAll -or $RustEngine) {
    Write-Step "Building Rust performance engine"
    Push-Location "$Root\rust_engine"

    cargo build --release
    if ($LASTEXITCODE -ne 0) { Write-Fail "Rust build failed" }

    # Copy compiled library to backend for bundling
    $lib = "target\release\smart_organizer_engine.dll"
    if (Test-Path $lib) {
        Copy-Item $lib "$Root\backend\smart_organizer_engine.pyd" -Force
        Write-Success "Rust engine built → backend/smart_organizer_engine.pyd"
    }

    cargo test --release
    if ($LASTEXITCODE -ne 0) { Write-Fail "Rust tests failed" }
    Write-Success "Rust tests passed"

    Pop-Location
}

# ───────────────────────────────────────────────────────────────────────────
# 2. Python backend
# ───────────────────────────────────────────────────────────────────────────
if ($BuildAll -or $Backend) {
    Write-Step "Setting up Python virtual environment"
    Push-Location $Root

    if (-not (Test-Path ".venv")) {
        python -m venv .venv
    }

    .\.venv\Scripts\Activate.ps1
    pip install --upgrade pip --quiet
    pip install -r backend\requirements.txt --quiet
    Write-Success "Python dependencies installed"

    # Run tests
    if (-not $SkipTests) {
        Write-Step "Running Python test suite"
        python -m pytest tests\ -v --tb=short
        if ($LASTEXITCODE -ne 0) { Write-Fail "Python tests failed" }
        Write-Success "All Python tests passed"
    }

    # Package with PyInstaller
    Write-Step "Packaging backend with PyInstaller"
    $SpecFile = "scripts\backend.spec"

    pyinstaller `
        --name smart_organizer_backend `
        --onefile `
        --noconfirm `
        --clean `
        --add-data "backend/data;data" `
        --hidden-import aiosqlite `
        --hidden-import watchdog.observers.polling `
        backend\main.py

    if ($LASTEXITCODE -ne 0) { Write-Fail "PyInstaller packaging failed" }
    Write-Success "Backend packaged → dist/smart_organizer_backend.exe"

    Pop-Location
}

# ───────────────────────────────────────────────────────────────────────────
# 3. Electron + React frontend
# ───────────────────────────────────────────────────────────────────────────
if ($BuildAll -or $Frontend) {
    Write-Step "Building React frontend"
    Push-Location "$Root\frontend"

    npm ci --prefer-offline
    if ($LASTEXITCODE -ne 0) { Write-Fail "npm install failed" }

    npm run build 2>&1
    if ($LASTEXITCODE -ne 0) { Write-Fail "Vite build failed" }
    Write-Success "React build complete → frontend/dist/"

    Write-Step "Packaging Electron app"
    npx electron-builder --win --publish never
    if ($LASTEXITCODE -ne 0) { Write-Fail "Electron Builder failed" }
    Write-Success "Electron installer → frontend/dist-electron/"

    Pop-Location
}

# ───────────────────────────────────────────────────────────────────────────
# Done
# ───────────────────────────────────────────────────────────────────────────
Write-Host "`n"
Write-Host "════════════════════════════════════════════════" -ForegroundColor Green
Write-Host "  Smart File Organizer AI — Build Complete ✓   " -ForegroundColor Green
Write-Host "════════════════════════════════════════════════" -ForegroundColor Green
Write-Host ""
Write-Host "  Backend exe : dist\smart_organizer_backend.exe"
Write-Host "  Electron pkg: frontend\dist-electron\"
Write-Host ""
