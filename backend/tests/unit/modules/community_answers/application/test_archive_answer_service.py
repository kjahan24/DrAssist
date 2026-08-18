"""Unit tests for `ArchiveAnswerService`, using in-memory fakes."""

from uuid import uuid4

import pytest

from app.modules.community_answers.application.dto import ArchiveAnswerInput
from app.modules.community_answers.application.services.archive_answer_service import (
    ArchiveAnswerService,
)
from app.modules.community_answers.domain.entities import CommunityAnswer
from app.modules.community_answers.domain.enums import AnswerStatus
from app.modules.community_answers.domain.exceptions import (
    AnswerAlreadyArchivedError,
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
        ArchiveAnswerService, FakeCommunityAnswerRepository, FakeCommunityQueryPort, FakeUnitOfWork
    ]
):
    answers = FakeCommunityAnswerRepository()
    communities = FakeCommunityQueryPort()
    uow = FakeUnitOfWork()
    service = ArchiveAnswerService(
        answer_repository=answers, community_query_port=communities, unit_of_work=uow
    )
    return service, answers, communities, uow


async def _seed_answer(
    answers: FakeCommunityAnswerRepository,
    *,
    author_id: object,
    community_id: object,
    best_answer: bool = False,
) -> CommunityAnswer:
    answer = CommunityAnswer.create(
        question_id=uuid4(),
        community_id=community_id,  # type: ignore[arg-type]
        organization_id=uuid4(),
        topic_id=uuid4(),
        author_id=author_id,  # type: ignore[arg-type]
        body=AnswerBody("Body."),
    )
    if best_answer:
        answer.publish()
        answer.mark_as_best()
    answer.pull_events()
    await answers.add(answer)
    return answer


class TestArchiveAnswer:
    async def test_sets_status_to_archived(self) -> None:
        service, answers, communities, _ = _seeded()
        author_id, community_id = uuid4(), uuid4()
        answer = await _seed_answer(answers, author_id=author_id, community_id=community_id)
        communities.add_membership(
            make_member_summary(community_id=community_id, user_id=author_id)
        )

        output = await service.execute(
            ArchiveAnswerInput(answer_id=answer.id, acting_user_id=author_id)
        )
        assert output.status is AnswerStatus.ARCHIVED

    async def test_already_archived_raises(self) -> None:
        service, answers, communities, _ = _seeded()
        author_id, community_id = uuid4(), uuid4()
        answer = await _seed_answer(answers, author_id=author_id, community_id=community_id)
        communities.add_membership(
            make_member_summary(community_id=community_id, user_id=author_id)
        )
        await service.execute(ArchiveAnswerInput(answer_id=answer.id, acting_user_id=author_id))

        with pytest.raises(AnswerAlreadyArchivedError):
            await service.execute(ArchiveAnswerInput(answer_id=answer.id, acting_user_id=author_id))

    async def test_archiving_the_best_answer_clears_the_best_flag(self) -> None:
        service, answers, communities, _ = _seeded()
        author_id, community_id = uuid4(), uuid4()
        answer = await _seed_answer(
            answers, author_id=author_id, community_id=community_id, best_answer=True
        )
        communities.add_membership(
            make_member_summary(community_id=community_id, user_id=author_id)
        )

        output = await service.execute(
            ArchiveAnswerInput(answer_id=answer.id, acting_user_id=author_id)
        )
        assert output.is_best_answer is False

    async def test_plain_member_cannot_archive_another_authors_answer(self) -> None:
        service, answers, communities, _ = _seeded()
        author_id, other_id, community_id = uuid4(), uuid4(), uuid4()
        answer = await _seed_answer(answers, author_id=author_id, community_id=community_id)
        communities.add_membership(make_member_summary(community_id=community_id, user_id=other_id))

        with pytest.raises(InsufficientAnswerRoleError):
            await service.execute(ArchiveAnswerInput(answer_id=answer.id, acting_user_id=other_id))

    async def test_unknown_answer_raises(self) -> None:
        service, _, _, _ = _seeded()
        with pytest.raises(AnswerNotFoundError):
            await service.execute(ArchiveAnswerInput(answer_id=uuid4(), acting_user_id=uuid4()))

    async def test_commits_the_unit_of_work(self) -> None:
        service, answers, communities, uow = _seeded()
        author_id, community_id = uuid4(), uuid4()
        answer = await _seed_answer(answers, author_id=author_id, community_id=community_id)
        communities.add_membership(
            make_member_summary(community_id=community_id, user_id=author_id)
        )

        await service.execute(ArchiveAnswerInput(answer_id=answer.id, acting_user_id=author_id))
        assert uow.committed is True
