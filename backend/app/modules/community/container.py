"""Module composition root.

The one place `CommunityQueryPort` gets bound to its concrete
implementation (`CommunityFacade`), and repository interfaces get bound
to their SQLAlchemy implementations. Any future module's own dependency
wiring calls `build_community_facade(session)` rather than constructing
`CommunityFacade` (or any repository) directly.

**Why this is a per-request factory, not an `lru_cache` singleton** —
this task's own CREATE section says to build `container.py` "following
the same architecture as previous AI modules," which every prior AI
module (Phase 4) satisfies with an `lru_cache`-decorated singleton
factory, since none of those modules owns a database session or any
per-request state. Community is a genuinely different kind of module: it
persists real rows through a real `AsyncSession`/`UnitOfWork`, exactly
like every other DB-backed module already in this codebase (Organization,
Patient, Doctor, ...). Rule 1 ("follow the existing... style already
established throughout DrAssist") settles the conflict in favor of
*that* precedent for a module that actually needs a session: this
`container.py` follows `app.modules.organization.container`'s own shape
instead — a `build_<module>_facade(session)` factory, constructed once
per request (or per Celery task), so every repository it builds shares
that same session/transaction. The six required top-level files
(`domain/application/infrastructure/presentation/public/container.py`)
are unchanged from what the task asked for; only the *contents* of
`container.py` adapt to this module's own, different runtime shape.

Scope note — this task builds the Community module's **foundation**
only: `Community`/`CommunityMember` entities, repositories,
`CreateCommunityService` (which provisions the creator's `OWNER`
membership atomically), `UpdateCommunityService`, `DeleteCommunityService`
(added to satisfy this task's own explicit "CRUD endpoints" requirement,
which its APPLICATION service list otherwise omits), `GetCommunityService`,
`ListCommunitiesService`, `JoinCommunityService`, `LeaveCommunityService`,
and the public query facade. It deliberately does not build Posts,
Questions, Answers, Comments, Replies, Votes, Reputation, or AI features
— those are separate, future modules, per this task's own explicit
exclusion list — and does not modify any completed backend module.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.community.application.services.community_query_service import (
    CommunityMembershipQueryService,
    GetCommunityService,
)
from app.modules.community.infrastructure.repositories import (
    SqlAlchemyCommunityMemberRepository,
    SqlAlchemyCommunityRepository,
)
from app.modules.community.public.facade import CommunityFacade


def build_community_facade(session: AsyncSession) -> CommunityFacade:
    """Construct a `CommunityFacade` wired to `session`.

    Called once per request (or per Celery task) — every repository it
    builds shares `session`, so they participate in the same transaction
    as the rest of that request's work.
    """
    community_repository = SqlAlchemyCommunityRepository(session)
    community_member_repository = SqlAlchemyCommunityMemberRepository(session)

    query_service = GetCommunityService(community_repository=community_repository)
    membership_query_service = CommunityMembershipQueryService(
        community_member_repository=community_member_repository
    )

    return CommunityFacade(
        query_service=query_service, membership_query_service=membership_query_service
    )
