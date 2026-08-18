"""Module composition root.

The one place `CommentQueryPort` gets bound to its concrete
implementation (`CommentFacade`), and the repository interface gets
bound to its SQLAlchemy implementation. Any future module's own
dependency wiring calls `build_comment_facade(session)` rather than
constructing `CommentFacade` (or the repository) directly — the same
per-request factory shape `app.modules.community_answers.container
.build_answer_facade` already establishes for itself.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.community_comments.infrastructure.repositories import (
    SqlAlchemyCommunityCommentRepository,
)
from app.modules.community_comments.public.facade import CommentFacade


def build_comment_facade(session: AsyncSession) -> CommentFacade:
    """Construct a `CommentFacade` wired to `session`."""
    comment_repository = SqlAlchemyCommunityCommentRepository(session)
    return CommentFacade(comment_repository=comment_repository)
