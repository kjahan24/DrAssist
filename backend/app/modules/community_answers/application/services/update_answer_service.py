"""`UpdateAnswerService` — the author (or a community moderator/admin)
may edit an answer's own content — see
`_authorization.ensure_can_author_action` for the exact rule.

Persists the `CommunityAnswerRevision` `CommunityAnswer.update_content`
may return, in the same transaction as the answer's own update — see
that method's own docstring for when a revision is (and isn't) created.
"""

from app.modules.community.public.interfaces import CommunityQueryPort
from app.modules.community_answers.application.dto import UpdateAnswerInput, UpdateAnswerOutput
from app.modules.community_answers.application.services._authorization import (
    ensure_can_author_action,
)
from app.modules.community_answers.domain.exceptions import AnswerNotFoundError
from app.modules.community_answers.domain.repositories import (
    CommunityAnswerRepository,
    CommunityAnswerRevisionRepository,
)
from app.modules.community_answers.domain.value_objects import AnswerBody, AnswerSummary
from app.shared.application.unit_of_work import UnitOfWork


class UpdateAnswerService:
    def __init__(
        self,
        *,
        answer_repository: CommunityAnswerRepository,
        answer_revision_repository: CommunityAnswerRevisionRepository,
        community_query_port: CommunityQueryPort,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._answers = answer_repository
        self._revisions = answer_revision_repository
        self._communities = community_query_port
        self._uow = unit_of_work

    async def execute(self, input_dto: UpdateAnswerInput) -> UpdateAnswerOutput:
        answer = await self._answers.get_by_id(input_dto.answer_id)
        if answer is None:
            raise AnswerNotFoundError(input_dto.answer_id)

        member = await self._communities.get_membership(
            answer.community_id, input_dto.acting_user_id
        )
        ensure_can_author_action(
            member,
            community_id=answer.community_id,
            user_id=input_dto.acting_user_id,
            author_id=answer.author_id,
        )

        revision = answer.update_content(
            body=AnswerBody(input_dto.body) if input_dto.body is not None else None,
            summary=AnswerSummary(input_dto.summary) if input_dto.summary is not None else None,
            regenerate_summary=input_dto.regenerate_summary,
            updated_by=input_dto.acting_user_id,
        )

        await self._answers.add(answer)
        events = list(answer.pull_events())
        if revision is not None:
            await self._revisions.add(revision)
            events.extend(revision.pull_events())

        self._uow.collect_events(events)
        await self._uow.commit()

        return UpdateAnswerOutput(
            answer_id=answer.id, status=answer.status, revision_number=answer.revision_number
        )
