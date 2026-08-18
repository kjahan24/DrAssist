"""Module composition root.

The one place `AnswerQueryPort` gets bound to its concrete
implementation (`AnswerFacade`), and the repository interface gets bound
to its SQLAlchemy implementation. Any future module's own dependency
wiring calls `build_answer_facade(session)` rather than constructing
`AnswerFacade` (or the repository) directly — the same per-request
factory shape `app.modules.community_questions.container
.build_question_facade` already establishes for itself.
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.community_answers.infrastructure.repositories import (
    SqlAlchemyCommunityAnswerRepository,
)
from app.modules.community_answers.public.facade import AnswerFacade


def build_answer_facade(session: AsyncSession) -> AnswerFacade:
    """Construct an `AnswerFacade` wired to `session`."""
    answer_repository = SqlAlchemyCommunityAnswerRepository(session)
    return AnswerFacade(answer_repository=answer_repository)
