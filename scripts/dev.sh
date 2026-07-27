#!/usr/bin/env bash
# Start the full stack in development mode (hot reload via docker-compose.override.yml).
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

docker compose up --build
