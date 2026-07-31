"""Health check endpoints — not owned by any business module, so they
live directly under `app/api/v1/endpoints/` rather than a module's own
`api/router.py`. No `CurrentUser` dependency: a load balancer/orchestrator
probing liveness has no bearer token.
"""

from fastapi import APIRouter
from sqlalchemy import text

from app.api.deps import DbSession
from app.core.exceptions import ServiceUnavailableError

router = APIRouter()


@router.get("/health")
async def get_liveness() -> dict[str, str]:
    """Liveness — the process is up and able to handle requests. No
    dependency check: a database outage should not make the process
    report itself as unhealthy to an orchestrator that would restart it."""
    return {"status": "ok"}


@router.get("/health/db")
async def get_readiness(session: DbSession) -> dict[str, str]:
    """Readiness — the database is reachable. Raises 503 (not 500) on
    failure: this is an expected, actionable "not ready yet" state, not
    an application bug."""
    try:
        await session.execute(text("SELECT 1"))
    except Exception as exc:
        raise ServiceUnavailableError("database is not reachable") from exc
    return {"status": "ok"}
