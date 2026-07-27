#!/usr/bin/env bash
# Apply pending Alembic migrations against the running backend container.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

docker compose exec backend alembic upgrade head
