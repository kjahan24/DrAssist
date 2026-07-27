#!/usr/bin/env pwsh
# Apply pending Alembic migrations against the running backend container.
$ErrorActionPreference = "Stop"
Set-Location "$PSScriptRoot/.."

docker compose exec backend alembic upgrade head
