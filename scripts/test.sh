#!/usr/bin/env bash
# Run all test suites for both backend and frontend.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

echo "==> Backend: pytest"
docker compose exec backend pytest

echo "==> Frontend: vitest"
docker compose exec frontend npm run test
