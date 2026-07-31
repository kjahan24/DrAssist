"""Shared fixtures for HTTP-level (router) API tests.

`db_session` requires a real, migrated PostgreSQL instance reachable via
`DATABASE_URL` — see the identical fixture (and rationale for a per-test
engine) in `tests.integration.modules.organization.conftest`.

`authenticated_client`/`authenticated_client_for_other_org` are this
package's own addition: no prior test in this codebase exercises the
app through HTTP with an authenticated principal (see `tests/conftest.py`'s
own `client` fixture, which is wired but was never used by any test).
Rather than issuing/decoding a real JWT, `live_server` overrides
`app.api.deps.get_current_user` *once*, for the whole session, with a
function that reads the caller's organization id from a test-only
`X-Test-Principal-Org-Id` header — every router's `CurrentUser`
annotation resolves through that exact callable, so overriding it once
covers all ~140 endpoints uniformly. The per-request header (rather than
a per-client `dependency_overrides` assignment) is deliberate: two tests
needing *simultaneously* distinct callers (`authenticated_client` and
`authenticated_client_for_other_org`, used together for cross-tenant
isolation tests) would otherwise both mutate the same global
`app.dependency_overrides` dict — whichever fixture's setup ran last
would silently win for *every* request from *either* client, which is
exactly what broke the first version of this fixture (confirmed: a
cross-tenant test asserting 404 got 200, because both "different-org"
clients ended up resolving to the same principal). Reading identity from
the request itself avoids that shared-mutable-state race entirely.
`unauthenticated_client` sends no such header, so the override raises
`UnauthorizedError` exactly like the real `get_current_user` does for a
request with no bearer token.

`live_server` runs the real app via a real `uvicorn` server bound to a
loopback socket — *not* `httpx.ASGITransport`. `ASGITransport` doesn't
drive an ASGI app's send/receive callables with true concurrency, and
this app's three custom middlewares
(`AuthenticationContextMiddleware`/`LoggingMiddleware`/
`RequestIDMiddleware`) all subclass Starlette's `BaseHTTPMiddleware`,
which spawns its own `anyio` task group per request to stream the
response — stacking three of those under `ASGITransport`'s synchronous
emulation reliably produced `RuntimeError: Task ... attached to a
different loop`. The server runs in a genuinely separate OS thread with
its own event loop (`uvicorn.Server.run()`, not `.serve()` awaited
in-process) — running it as a bare task on the *same* loop as the test
client self-deadlocks (confirmed: every request timed out), the same
reason `TestClient`/`pytest-httpserver`-style tooling always uses a
background thread for a "real" server rather than sharing the caller's
loop. Every async fixture here is `loop_scope="session"`, and every test
*module* in this package must carry its own
`pytestmark = pytest.mark.asyncio(loop_scope="session")` for the same
reason — see `test_health_api.py` for the smallest example. Two things
that look like they should apply that mark package-wide do *not*, both
confirmed by directly comparing `id(asyncio.get_running_loop())` between
`live_server` and a real test: (1) a bare `pytestmark` assignment in this
package's `__init__.py` is never read — pytest only honors `pytestmark`
as an attribute of the *test module itself*, not a package's
`__init__.py`; (2) adding the marker from a `pytest_collection_modifyitems`
hook in this `conftest.py` does not work either, even though the marker
visibly attaches to each item — pytest-asyncio decides and caches a
test's loop scope during its own earlier collection hook, before
`pytest_collection_modifyitems` (a later, standard pytest hook) ever
runs, so the added marker arrives too late to change anything. Without
the mark, a test runs on pytest-asyncio's normal per-function loop while
`live_server` (and everything chained from it) runs on the session loop;
closing `live_server`'s connection from the test's own, already-closed
loop raised `RuntimeError: Event loop is closed`, and touching
`db_session`'s asyncpg connections from mismatched loops produced
`RuntimeError: Task ... attached to a different loop` plus asyncpg
`InternalClientError: got result for unknown protocol state 3`.

`live_server`'s `uvicorn.Config` pins `loop="asyncio"` explicitly — this
is not cosmetic. `uvicorn[standard]` bundles `uvloop`, and `Config`'s
default `loop="auto"` picks it when installed; `uvicorn.loops.uvloop
.uvloop_setup()` calls `uvloop.install()`, which replaces the *process-
wide* `asyncio` event-loop policy (`asyncio.set_event_loop_policy(...)`),
not just the background thread's own loop. Confirmed by direct
reproduction: with the default policy swapped, pytest-asyncio's
*main*-thread bookkeeping (`asyncio.get_event_loop()`, called internally
by `pytest_asyncio.plugin`) started raising `RuntimeError: There is no
current event loop in thread 'MainThread'` from inside uvloop's own
`EventLoopPolicy.get_event_loop()` — the main thread never had a
uvloop-managed loop bound in that policy's thread-local storage, only
the server thread did. That misattribution is what surfaced downstream
as `RuntimeError: Task ... attached to a different loop` plus asyncpg
`InternalClientError: got result for unknown protocol state 3` on
`db_session`'s connections, cascading into every test after the first
one to exercise both `db_session` and `live_server` together. Forcing
`loop="asyncio"` keeps uvicorn on the stock policy pytest-asyncio
already manages, and the failure reproduced zero times across repeated
runs once this was set — confirmed by an isolated repro script before
this fix and after (see the investigation, not retained in-tree).
"""

import asyncio
import threading
from collections.abc import AsyncIterator
from uuid import UUID, uuid4

import pytest_asyncio
import uvicorn
from fastapi import Request
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.core.exceptions import UnauthorizedError

# Guarantees every module's ORM classes are registered on `Base.metadata`
# before any session is used — see the identical import in
# `app/infrastructure/database/session.py` for why this is required.
from app.infrastructure.database import models  # noqa: F401
from app.modules.authentication.application.dto import AuthenticatedPrincipalDTO
from app.modules.authentication.domain.entities import User
from app.modules.organization.domain.entities import Organization
from tests.integration.api._helpers import persist_organization, persist_user

_TEST_PRINCIPAL_ORG_HEADER = "X-Test-Principal-Org-Id"


@pytest_asyncio.fixture(loop_scope="session")
async def db_session() -> AsyncIterator[AsyncSession]:
    settings = get_settings()
    engine = create_async_engine(str(settings.database.url), pool_pre_ping=True)
    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    try:
        async with session_factory() as session:
            yield session
    finally:
        await engine.dispose()


@pytest_asyncio.fixture(loop_scope="session")
async def test_organization(db_session: AsyncSession) -> Organization:
    return await persist_organization(db_session)


@pytest_asyncio.fixture(loop_scope="session")
async def other_organization(db_session: AsyncSession) -> Organization:
    """A second, distinct organization — for cross-tenant isolation tests."""
    return await persist_organization(db_session, name="Other Test Org")


async def _override_get_current_user(request: Request) -> AuthenticatedPrincipalDTO:
    organization_id = request.headers.get(_TEST_PRINCIPAL_ORG_HEADER)
    if organization_id is None:
        raise UnauthorizedError("missing or malformed Authorization header")
    return AuthenticatedPrincipalDTO(
        user_id=uuid4(),
        organization_id=UUID(organization_id),
        session_id=uuid4(),
        email="api-test-principal@example.com",
        permissions=frozenset(),
    )


@pytest_asyncio.fixture(loop_scope="session", scope="session")
async def live_server() -> AsyncIterator[str]:
    """Runs `app.main.app` via a real `uvicorn` server on a loopback
    socket, in a background OS thread with its own event loop — see this
    module's own docstring for why (not `ASGITransport`, not an in-process
    task on the test's own loop). `lifespan="off"`: this app's own
    `lifespan()` only calls `configure_event_subscriptions`, which every
    use case under test already wires directly (no background
    delivery/consumer exists yet — see e.g.
    `app.modules.notification.container`'s own scope note), so skipping
    it changes nothing these tests exercise."""
    from app.main import app

    app.dependency_overrides[get_current_user] = _override_get_current_user
    config = uvicorn.Config(
        app,
        host="127.0.0.1",
        port=0,
        lifespan="off",
        log_level="warning",
        loop="asyncio",
    )
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    try:
        while not server.started:
            await asyncio.sleep(0.01)
        port = server.servers[0].sockets[0].getsockname()[1]
        yield f"http://127.0.0.1:{port}"
    finally:
        server.should_exit = True
        thread.join(timeout=5)
        app.dependency_overrides.pop(get_current_user, None)


@pytest_asyncio.fixture(loop_scope="session")
async def authenticated_client(
    live_server: str, test_organization: Organization
) -> AsyncIterator[AsyncClient]:
    """An `AsyncClient` authenticated as a principal in `test_organization`."""
    headers = {_TEST_PRINCIPAL_ORG_HEADER: str(test_organization.id)}
    async with AsyncClient(base_url=live_server, headers=headers) as ac:
        yield ac


@pytest_asyncio.fixture(loop_scope="session")
async def authenticated_client_for_other_org(
    live_server: str, other_organization: Organization
) -> AsyncIterator[AsyncClient]:
    """A second authenticated client, scoped to `other_organization` — for
    cross-tenant isolation tests that need two distinct callers."""
    headers = {_TEST_PRINCIPAL_ORG_HEADER: str(other_organization.id)}
    async with AsyncClient(base_url=live_server, headers=headers) as ac:
        yield ac


@pytest_asyncio.fixture(loop_scope="session")
async def unauthenticated_client(live_server: str) -> AsyncIterator[AsyncClient]:
    """A plain client with no auth header — for testing that endpoints
    genuinely require `CurrentUser`."""
    async with AsyncClient(base_url=live_server) as ac:
        yield ac


@pytest_asyncio.fixture(loop_scope="session")
async def test_user(db_session: AsyncSession, test_organization: Organization) -> User:
    return await persist_user(db_session, organization_id=test_organization.id)
