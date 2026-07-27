#!/usr/bin/env bash
# First-time environment bootstrap: copies env templates and builds images.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

echo "==> Copying environment templates (skipped if already present)"
[ -f .env ] || cp .env.example .env
[ -f backend/.env ] || cp backend/.env.example backend/.env
[ -f frontend/.env ] || cp frontend/.env.example frontend/.env

echo "==> Generating frontend/package-lock.json (required by 'npm ci' in Dockerfiles)"
if [ ! -f frontend/package-lock.json ]; then
  ( cd frontend && npm install )
fi

echo "==> Building Docker images"
docker compose build

echo "==> Setup complete."
echo "    1. Edit .env (and backend/.env, frontend/.env) with real secrets."
echo "    2. Run 'make dev' or './scripts/dev.sh' to start the stack."
