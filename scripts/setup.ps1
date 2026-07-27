#!/usr/bin/env pwsh
# First-time environment bootstrap: copies env templates and builds images.
$ErrorActionPreference = "Stop"
Set-Location "$PSScriptRoot/.."

Write-Host "==> Copying environment templates (skipped if already present)"
if (-not (Test-Path ".env")) { Copy-Item ".env.example" ".env" }
if (-not (Test-Path "backend/.env")) { Copy-Item "backend/.env.example" "backend/.env" }
if (-not (Test-Path "frontend/.env")) { Copy-Item "frontend/.env.example" "frontend/.env" }

Write-Host "==> Generating frontend/package-lock.json (required by 'npm ci' in Dockerfiles)"
if (-not (Test-Path "frontend/package-lock.json")) {
    Push-Location frontend
    npm install
    Pop-Location
}

Write-Host "==> Building Docker images"
docker compose build

Write-Host "==> Setup complete."
Write-Host "    1. Edit .env (and backend/.env, frontend/.env) with real secrets."
Write-Host "    2. Run 'make dev' or './scripts/dev.ps1' to start the stack."
