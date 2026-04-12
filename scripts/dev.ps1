# scripts/dev.ps1 — Start backend + frontend in development mode
#
# Usage:  .\scripts\dev.ps1

$Root = Split-Path -Parent $PSScriptRoot
$ErrorActionPreference = "Stop"

Write-Host "Starting Smart File Organizer AI (DEV MODE)" -ForegroundColor Cyan
Write-Host "Backend  → http://localhost:8765" -ForegroundColor Yellow
Write-Host "Frontend → http://localhost:5173" -ForegroundColor Yellow
Write-Host ""

# Activate Python venv if present
$VenvActivate = "$Root\.venv\Scripts\Activate.ps1"
if (Test-Path $VenvActivate) {
    & $VenvActivate
}

# Start FastAPI backend in background
Write-Host "[1/2] Starting FastAPI backend..." -ForegroundColor Green
$BackendJob = Start-Job -ScriptBlock {
    param($root)
    Set-Location $root
    & python -m uvicorn backend.main:app --host 127.0.0.1 --port 8765 --reload
} -ArgumentList $Root

# Brief pause to let the backend boot
Start-Sleep -Seconds 3

# Start Vite dev server + Electron
Write-Host "[2/2] Starting Electron + Vite..." -ForegroundColor Green
Push-Location "$Root\frontend"
$env:NODE_ENV = "development"
npm run dev

# On exit, clean up backend job
Stop-Job -Job $BackendJob -ErrorAction SilentlyContinue
Remove-Job -Job $BackendJob -ErrorAction SilentlyContinue
Pop-Location
