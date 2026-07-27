#!/usr/bin/env pwsh
# Run all test suites for both backend and frontend.
$ErrorActionPreference = "Stop"
Set-Location "$PSScriptRoot/.."

Write-Host "==> Backend: pytest"
docker compose exec backend pytest

Write-Host "==> Frontend: vitest"
docker compose exec frontend npm run test
