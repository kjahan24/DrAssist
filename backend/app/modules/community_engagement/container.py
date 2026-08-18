"""Module composition root.

The one place `EngagementQueryPort` gets bound to its concrete
implementation (`EngagementFacade`), and the repository interfaces get
bound to their SQLAlchemy implementations. Any future module's own
dependency wiring calls `build_engagement_facade(session)` rather than
constructing `EngagementFacade` (or any repository) directly — the same
per-request factory shape `app.modules.community_comments.container
.build_comment_facade` already establishes for itself.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.community_engagement.infrastructure.repositories import (
    SqlAlchemyVoteRepository,
)
from app.modules.community_engagement.public.facade import EngagementFacade


def build_engagement_facade(session: AsyncSession) -> EngagementFacade:
    """Construct an `EngagementFacade` wired to `session`."""
    vote_repository = SqlAlchemyVoteRepository(session)
    return EngagementFacade(vote_repository=vote_repository)
