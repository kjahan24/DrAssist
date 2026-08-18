"""Unit tests for `RestoreAnswerService`, using in-memory fakes."""

from uuid import uuid4

import pytest

from app.modules.community_answers.application.dto import RestoreAnswerInput
from app.modules.community_answers.application.services.restore_answer_service import (
    RestoreAnswerService,
)
from app.modules.community_answers.domain.entities import CommunityAnswer
from app.modules.community_answers.domain.enums import AnswerStatus
from app.modules.community_answers.domain.exceptions import (
    AnswerCannotBeRestoredError,
    AnswerNotFoundError,
    InsufficientAnswerRoleError,
)
from app.modules.community_answers.domain.value_objects import AnswerBody
from tests.unit.modules.community_answers.application.fakes import (
    FakeCommunityAnswerRepository,
    FakeCommunityQueryPort,
    FakeUnitOfWork,
    make_member_summary,
)


def _seeded() -> (
    tuple[
        RestoreAnswerService, FakeCommunityAnswerRepository, FakeCommunityQueryPort, FakeUnitOfWork
    ]
):
    answers = FakeCommunityAnswerRepository()
    communities = FakeCommunityQueryPort()
    uow = FakeUnitOfWork()
    service = RestoreAnswerService(
        answer_repository=answers, community_query_port=communities, unit_of_work=uow
    )
    return service, answers, communities, uow


async def _seed_archived_answer(
    answers: FakeCommunityAnswerRepository, *, author_id: object, community_id: object
) -> CommunityAnswer:
    answer = CommunityAnswer.create(
        question_id=uuid4(),
        community_id=community_id,  # type: ignore[arg-type]
        organization_id=uuid4(),
        topic_id=uuid4(),
        author_id=author_id,  # type: ignore[arg-type]
        body=AnswerBody("Body."),
    )
    answer.archive()
    await answers.add(answer)
    return answer


class TestRestoreAnswer:
    async def test_restores_an_archived_answer_to_draft(self) -> None:
        service, answers, communities, _ = _seeded()
        author_id, community_id = uuid4(), uuid4()
        answer = await _seed_archived_answer(
            answers, author_id=author_id, community_id=community_id
        )
        communities.add_membership(
            make_member_summary(community_id=community_id, user_id=author_id)
        )

        output = await service.execute(
            RestoreAnswerInput(answer_id=answer.id, acting_user_id=author_id)
        )
        assert output.status is AnswerStatus.DRAFT

    async def test_restoring_a_published_answer_raises(self) -> None:
        service, answers, communities, _ = _seeded()
        author_id, community_id = uuid4(), uuid4()
        answer = CommunityAnswer.create(
            question_id=uuid4(),
            community_id=community_id,
            organization_id=uuid4(),
            topic_id=uuid4(),
            author_id=author_id,
            body=AnswerBody("Body."),
        )
        answer.publish()
        await answers.add(answer)
        communities.add_membership(
            make_member_summary(community_id=community_id, user_id=author_id)
        )

        with pytest.raises(AnswerCannotBeRestoredError):
            await service.execute(RestoreAnswerInput(answer_id=answer.id, acting_user_id=author_id))

    async def test_plain_member_cannot_restore_another_authors_answer(self) -> None:
        service, answers, communities, _ = _seeded()
        author_id, other_id, community_id = uuid4(), uuid4(), uuid4()
        answer = await _seed_archived_answer(
            answers, author_id=author_id, community_id=community_id
        )
        communities.add_membership(make_member_summary(community_id=community_id, user_id=other_id))

        with pytest.raises(InsufficientAnswerRoleError):
            await service.execute(RestoreAnswerInput(answer_id=answer.id, acting_user_id=other_id))

    async def test_unknown_answer_raises(self) -> None:
        service, _, _, _ = _seeded()
        with pytest.raises(AnswerNotFoundError):
            await service.execute(RestoreAnswerInput(answer_id=uuid4(), acting_user_id=uuid4()))

    async def test_commits_the_unit_of_work(self) -> None:
        service, answers, communities, uow = _seeded()
        author_id, community_id = uuid4(), uuid4()
        answer = await _seed_archived_answer(
            answers, author_id=author_id, community_id=community_id
        )
        communities.add_membership(
            make_member_summary(community_id=community_id, user_id=author_id)
        )

        await service.execute(RestoreAnswerInput(answer_id=answer.id, acting_user_id=author_id))
        assert uow.committed is True
