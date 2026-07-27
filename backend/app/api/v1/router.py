"""v1 API route aggregator.

Aggregates each module's own `api/router.py`. The Authentication module's
router is included but currently registers no endpoints itself (see
`app.modules.authentication.container` for why) — it's wired in now so
the module is present in the app/OpenAPI schema from day one, and so
future endpoint modules only need to register into
`app.modules.authentication.api.router.router`, not touch this file
again.
"""

from fastapi import APIRouter

from app.modules.authentication.api.router import router as authentication_router

api_router = APIRouter()
api_router.include_router(authentication_router, prefix="/auth", tags=["authentication"])
