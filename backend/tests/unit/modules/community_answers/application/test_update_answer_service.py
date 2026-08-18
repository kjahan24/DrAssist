"""Unit tests for `UpdateAnswerService`, using in-memory fakes."""

from uuid import uuid4

import pytest

from app.modules.community.public.dto import CommunityRole
from app.modules.community_answers.application.dto import UpdateAnswerInput
from app.modules.community_answers.application.services.update_answer_service import (
    UpdateAnswerService,
)
from app.modules.community_answers.domain.entities import CommunityAnswer
from app.modules.community_answers.domain.exceptions import (
    AnswerNotFoundError,
    InsufficientAnswerRoleError,
)
from app.modules.community_answers.domain.value_objects import AnswerBody
from tests.unit.modules.community_answers.application.fakes import (
    FakeCommunityAnswerRepository,
    FakeCommunityAnswerRevisionRepository,
    FakeCommunityQueryPort,
    FakeUnitOfWork,
    make_member_summary,
)


def _seeded() -> (
    tuple[
        UpdateAnswerService,
        FakeCommunityAnswerRepository,
        FakeCommunityAnswerRevisionRepository,
        FakeCommunityQueryPort,
        FakeUnitOfWork,
    ]
):
    answers = FakeCommunityAnswerRepository()
    revisions = FakeCommunityAnswerRevisionRepository()
    communities = FakeCommunityQueryPort()
    uow = FakeUnitOfWork()
    service = UpdateAnswerService(
        answer_repository=answers,
        answer_revision_repository=revisions,
        community_query_port=communities,
        unit_of_work=uow,
    )
    return service, answers, revisions, communities, uow


async def _seed_answer(
    answers: FakeCommunityAnswerRepository,
    *,
    author_id: object,
    community_id: object,
    published: bool = False,
) -> CommunityAnswer:
    answer = CommunityAnswer.create(
        question_id=uuid4(),
        community_id=community_id,  # type: ignore[arg-type]
        organization_id=uuid4(),
        topic_id=uuid4(),
        author_id=author_id,  # type: ignore[arg-type]
        body=AnswerBody("Original body."),
    )
    if published:
        answer.publish()
    answer.pull_events()
    await answers.add(answer)
    return answer


class TestUpdateAnswer:
    async def test_updates_the_body(self) -> None:
        service, answers, _, communities, _ = _seeded()
        author_id, community_id = uuid4(), uuid4()
        answer = await _seed_answer(answers, author_id=author_id, community_id=community_id)
        communities.add_membership(
            make_member_summary(community_id=community_id, user_id=author_id)
        )

        await service.execute(
            UpdateAnswerInput(answer_id=answer.id, acting_user_id=author_id, body="New body.")
        )
        stored = await answers.get_by_id(answer.id)
        assert stored is not None
        assert str(stored.body) == "New body."

    async def test_editing_a_draft_creates_no_revision(self) -> None:
        service, answers, revisions, communities, _ = _seeded()
        author_id, community_id = uuid4(), uuid4()
        answer = await _seed_answer(answers, author_id=author_id, community_id=community_id)
        communities.add_membership(
            make_member_summary(community_id=community_id, user_id=author_id)
        )

        output = await service.execute(
            UpdateAnswerInput(answer_id=answer.id, acting_user_id=author_id, body="New body.")
        )
        assert output.revision_number == 1
        stored_revisions = await revisions.list_by_answer(answer.id)
        assert stored_revisions == []

    async def test_editing_a_published_answer_creates_a_revision(self) -> None:
        service, answers, revisions, communities, _ = _seeded()
        author_id, community_id = uuid4(), uuid4()
        answer = await _seed_answer(
            answers, author_id=author_id, community_id=community_id, published=True
        )
        communities.add_membership(
            make_member_summary(community_id=community_id, user_id=author_id)
        )

        await service.execute(
            UpdateAnswerInput(answer_id=answer.id, acting_user_id=author_id, body="Edited body.")
        )
        stored_revisions = await revisions.list_by_answer(answer.id)
        assert len(stored_revisions) == 1
        assert stored_revisions[0].previous_body == "Original body."

    async def test_editing_a_published_answer_increments_revision_number(self) -> None:
        service, answers, _, communities, _ = _seeded()
        author_id, community_id = uuid4(), uuid4()
        answer = await _seed_answer(
            answers, author_id=author_id, community_id=community_id, published=True
        )
        communities.add_membership(
            make_member_summary(community_id=community_id, user_id=author_id)
        )

        output = await service.execute(
            UpdateAnswerInput(answer_id=answer.id, acting_user_id=author_id, body="Edited body.")
        )
        assert output.revision_number == 2

    async def test_moderator_may_update_another_authors_answer(self) -> None:
        service, answers, _, communities, _ = _seeded()
        author_id, moderator_id, community_id = uuid4(), uuid4(), uuid4()
        answer = await _seed_answer(answers, author_id=author_id, community_id=community_id)
        communities.add_membership(
            make_member_summary(
                community_id=community_id, user_id=moderator_id, role=CommunityRole.MODERATOR
            )
        )

        await service.execute(
            UpdateAnswerInput(
                answer_id=answer.id, acting_user_id=moderator_id, body="Moderated edit."
            )
        )
        stored = await answers.get_by_id(answer.id)
        assert stored is not None
        assert str(stored.body) == "Moderated edit."

    async def test_plain_member_cannot_update_another_authors_answer(self) -> None:
        service, answers, _, communities, _ = _seeded()
        author_id, other_id, community_id = uuid4(), uuid4(), uuid4()
        answer = await _seed_answer(answers, author_id=author_id, community_id=community_id)
        communities.add_membership(make_member_summary(community_id=community_id, user_id=other_id))

        with pytest.raises(InsufficientAnswerRoleError):
            await service.execute(
                UpdateAnswerInput(answer_id=answer.id, acting_user_id=other_id, body="Not allowed.")
            )

    async def test_unknown_answer_raises(self) -> None:
        service, _, _, _, _ = _seeded()
        with pytest.raises(AnswerNotFoundError):
            await service.execute(
                UpdateAnswerInput(answer_id=uuid4(), acting_user_id=uuid4(), body="Body.")
            )

    async def test_commits_the_unit_of_work(self) -> None:
        service, answers, _, communities, uow = _seeded()
        author_id, community_id = uuid4(), uuid4()
        answer = await _seed_answer(answers, author_id=author_id, community_id=community_id)
        communities.add_membership(
            make_member_summary(community_id=community_id, user_id=author_id)
        )

        await service.execute(
            UpdateAnswerInput(answer_id=answer.id, acting_user_id=author_id, body="New body.")
        )
        assert uow.committed is True
