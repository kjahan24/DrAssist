"""Module composition root.

The one place `QuestionQueryPort` gets bound to its concrete
implementation (`QuestionFacade`), and the repository interface gets
bound to its SQLAlchemy implementation. Any future module's own
dependency wiring calls `build_question_facade(session)` rather than
constructing `QuestionFacade` (or the repository) directly — the same
per-request factory shape
`app.modules.community_posts.container.build_post_facade` already
establishes for itself.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.community_questions.infrastructure.repositories import (
    SqlAlchemyCommunityQuestionRepository,
)
from app.modules.community_questions.public.facade import QuestionFacade


def build_question_facade(session: AsyncSession) -> QuestionFacade:
    """Construct a `QuestionFacade` wired to `session`."""
    question_repository = SqlAlchemyCommunityQuestionRepository(session)
    return QuestionFacade(question_repository=question_repository)
