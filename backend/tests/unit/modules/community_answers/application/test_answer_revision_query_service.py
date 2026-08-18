"""Unit tests for `AnswerRevisionQueryService` — read-only, no
create/remove seam; see `CommunityAnswerRevisionRepository`'s own
docstring for why."""

from uuid import uuid4

from app.modules.community_answers.application.services.answer_revision_query_service import (
    AnswerRevisionQueryService,
)
from app.modules.community_answers.domain.entities import CommunityAnswerRevision
from app.modules.community_answers.domain.value_objects import AnswerId
from tests.unit.modules.community_answers.application.fakes import (
    FakeCommunityAnswerRevisionRepository,
)


class TestListRevisions:
    async def test_returns_empty_list_for_an_answer_with_no_revisions(self) -> None:
        revisions = FakeCommunityAnswerRevisionRepository()
        service = AnswerRevisionQueryService(answer_revision_repository=revisions)

        result = await service.list_revisions(uuid4())
        assert result == []

    async def test_lists_revisions_for_an_answer(self) -> None:
        revisions = FakeCommunityAnswerRevisionRepository()
        service = AnswerRevisionQueryService(answer_revision_repository=revisions)
        answer_id = uuid4()
        revision = CommunityAnswerRevision.create(
            answer_id=AnswerId(answer_id),
            revision_number=1,
            previous_body="Old body.",
            author_id=uuid4(),
        )
        await revisions.add(revision)

        result = await service.list_revisions(answer_id)
        assert len(result) == 1
        assert result[0].previous_body == "Old body."

    async def test_only_returns_revisions_for_the_requested_answer(self) -> None:
        revisions = FakeCommunityAnswerRevisionRepository()
        service = AnswerRevisionQueryService(answer_revision_repository=revisions)
        answer_id, other_answer_id = uuid4(), uuid4()
        await revisions.add(
            CommunityAnswerRevision.create(
                answer_id=AnswerId(answer_id),
                revision_number=1,
                previous_body="Mine.",
                author_id=uuid4(),
            )
        )
        await revisions.add(
            CommunityAnswerRevision.create(
                answer_id=AnswerId(other_answer_id),
                revision_number=1,
                previous_body="Not mine.",
                author_id=uuid4(),
            )
        )

        result = await service.list_revisions(answer_id)
        assert len(result) == 1
        assert result[0].previous_body == "Mine."

    async def test_orders_by_revision_number_descending(self) -> None:
        revisions = FakeCommunityAnswerRevisionRepository()
        service = AnswerRevisionQueryService(answer_revision_repository=revisions)
        answer_id = uuid4()
        for number in (1, 2, 3):
            await revisions.add(
                CommunityAnswerRevision.create(
                    answer_id=AnswerId(answer_id),
                    revision_number=number,
                    previous_body=f"body {number}",
                    author_id=uuid4(),
                )
            )

        result = await service.list_revisions(answer_id)
        assert [r.revision_number for r in result] == [3, 2, 1]

    async def test_respects_limit_and_offset(self) -> None:
        revisions = FakeCommunityAnswerRevisionRepository()
        service = AnswerRevisionQueryService(answer_revision_repository=revisions)
        answer_id = uuid4()
        for number in range(1, 4):
            await revisions.add(
                CommunityAnswerRevision.create(
                    answer_id=AnswerId(answer_id),
                    revision_number=number,
                    previous_body=f"body {number}",
                    author_id=uuid4(),
                )
            )

        result = await service.list_revisions(answer_id, offset=1, limit=1)
        assert len(result) == 1
