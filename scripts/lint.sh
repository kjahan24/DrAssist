#!/usr/bin/env bash
# Run all linters/type-checkers for both backend and frontend.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

echo "==> Backend: ruff check"
docker compose exec backend ruff check .

echo "==> Backend: mypy"
docker compose exec backend mypy app

echo "==> Frontend: eslint"
docker compose exec frontend npm run lint

echo "==> Frontend: tsc --noEmit"
docker compose exec frontend npm run typecheck
