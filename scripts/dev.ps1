#!/usr/bin/env pwsh
# Start the full stack in development mode (hot reload via docker-compose.override.yml).
$ErrorActionPreference = "Stop"
Set-Location "$PSScriptRoot/.."

docker compose up --build
