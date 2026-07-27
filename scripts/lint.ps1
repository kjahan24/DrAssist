#!/usr/bin/env pwsh
# Run all linters/type-checkers for both backend and frontend.
$ErrorActionPreference = "Stop"
Set-Location "$PSScriptRoot/.."

Write-Host "==> Backend: ruff check"
docker compose exec backend ruff check .

Write-Host "==> Backend: mypy"
docker compose exec backend mypy app

Write-Host "==> Frontend: eslint"
docker compose exec frontend npm run lint

Write-Host "==> Frontend: tsc --noEmit"
docker compose exec frontend npm run typecheck
