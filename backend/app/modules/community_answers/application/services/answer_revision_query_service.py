"""`AnswerRevisionQueryService` — read-only access to an answer's own
revision history (this task's own REVISION HISTORY section). No
create/remove methods here: revisions are created automatically, as a
side effect of `CommunityAnswer.update_content`, persisted by
`UpdateAnswerService` — see those two's own docstrings. There is
deliberately no `CommunityAnswerRevisionRepository.remove` for this
service to ever call — see that repository's own docstring: revision
history is immutable, full stop.
"""

from uuid import UUID

from app.modules.community_answers.application.dto import AnswerRevisionSummaryDTO
from app.modules.community_answers.application.services._summary_mappers import (
    answer_revision_to_summary,
)
from app.modules.community_answers.domain.repositories import CommunityAnswerRevisionRepository


class AnswerRevisionQueryService:
    def __init__(self, *, answer_revision_repository: CommunityAnswerRevisionRepository) -> None:
        self._revisions = answer_revision_repository

    async def list_revisions(
        self, answer_id: UUID, *, offset: int = 0, limit: int = 20
    ) -> list[AnswerRevisionSummaryDTO]:
        revisions = await self._revisions.list_by_answer(answer_id, offset=offset, limit=limit)
        return [answer_revision_to_summary(r) for r in revisions]
