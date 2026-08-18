"""Unit tests for `DeleteAnswerService`, using in-memory fakes."""

from uuid import uuid4

import pytest

from app.modules.community_answers.application.dto import DeleteAnswerInput
from app.modules.community_answers.application.services.delete_answer_service import (
    DeleteAnswerService,
)
from app.modules.community_answers.domain.entities import CommunityAnswer
from app.modules.community_answers.domain.enums import AnswerStatus
from app.modules.community_answers.domain.exceptions import (
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
        DeleteAnswerService, FakeCommunityAnswerRepository, FakeCommunityQueryPort, FakeUnitOfWork
    ]
):
    answers = FakeCommunityAnswerRepository()
    communities = FakeCommunityQueryPort()
    uow = FakeUnitOfWork()
    service = DeleteAnswerService(
        answer_repository=answers, community_query_port=communities, unit_of_work=uow
    )
    return service, answers, communities, uow


async def _seed_answer(
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
    await answers.add(answer)
    return answer


class TestDeleteAnswer:
    async def test_sets_status_to_deleted(self) -> None:
        service, answers, communities, _ = _seeded()
        author_id, community_id = uuid4(), uuid4()
        answer = await _seed_answer(answers, author_id=author_id, community_id=community_id)
        communities.add_membership(
            make_member_summary(community_id=community_id, user_id=author_id)
        )

        await service.execute(DeleteAnswerInput(answer_id=answer.id, acting_user_id=author_id))
        stored = await answers.get_by_id(answer.id)
        assert stored is not None
        assert stored.status is AnswerStatus.DELETED

    async def test_plain_member_cannot_delete_another_authors_answer(self) -> None:
        service, answers, communities, _ = _seeded()
        author_id, other_id, community_id = uuid4(), uuid4(), uuid4()
        answer = await _seed_answer(answers, author_id=author_id, community_id=community_id)
        communities.add_membership(make_member_summary(community_id=community_id, user_id=other_id))

        with pytest.raises(InsufficientAnswerRoleError):
            await service.execute(DeleteAnswerInput(answer_id=answer.id, acting_user_id=other_id))

    async def test_unknown_answer_raises(self) -> None:
        service, _, _, _ = _seeded()
        with pytest.raises(AnswerNotFoundError):
            await service.execute(DeleteAnswerInput(answer_id=uuid4(), acting_user_id=uuid4()))

    async def test_commits_the_unit_of_work(self) -> None:
        service, answers, communities, uow = _seeded()
        author_id, community_id = uuid4(), uuid4()
        answer = await _seed_answer(answers, author_id=author_id, community_id=community_id)
        communities.add_membership(
            make_member_summary(community_id=community_id, user_id=author_id)
        )

        await service.execute(DeleteAnswerInput(answer_id=answer.id, acting_user_id=author_id))
        assert uow.committed is True
