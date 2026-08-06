"""Module composition root.

The one place `PostQueryPort` gets bound to its concrete implementation
(`PostFacade`), and the repository interface gets bound to its
SQLAlchemy implementation. Any future module's own dependency wiring
calls `build_post_facade(session)` rather than constructing `PostFacade`
(or the repository) directly — the same per-request factory shape
`app.modules.community.container.build_community_facade`/
`app.modules.medical_topics.container.build_topic_facade` already
establish for themselves.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.community_posts.infrastructure.repositories import (
    SqlAlchemyCommunityPostRepository,
)
from app.modules.community_posts.public.facade import PostFacade


def build_post_facade(session: AsyncSession) -> PostFacade:
    """Construct a `PostFacade` wired to `session`."""
    post_repository = SqlAlchemyCommunityPostRepository(session)
    return PostFacade(post_repository=post_repository)
