"""Unit tests for `PinAnswerService`, using in-memory fakes."""

from uuid import uuid4

import pytest

from app.modules.community.public.dto import CommunityRole
from app.modules.community_answers.application.dto import SetAnswerPinnedInput
from app.modules.community_answers.application.services.pin_answer_service import PinAnswerService
from app.modules.community_answers.domain.entities import CommunityAnswer
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
    tuple[PinAnswerService, FakeCommunityAnswerRepository, FakeCommunityQueryPort, FakeUnitOfWork]
):
    answers = FakeCommunityAnswerRepository()
    communities = FakeCommunityQueryPort()
    uow = FakeUnitOfWork()
    service = PinAnswerService(
        answer_repository=answers, community_query_port=communities, unit_of_work=uow
    )
    return service, answers, communities, uow


async def _seed_answer(
    answers: FakeCommunityAnswerRepository, *, community_id: object
) -> CommunityAnswer:
    answer = CommunityAnswer.create(
        question_id=uuid4(),
        community_id=community_id,  # type: ignore[arg-type]
        organization_id=uuid4(),
        topic_id=uuid4(),
        author_id=uuid4(),
        body=AnswerBody("Body."),
    )
    await answers.add(answer)
    return answer


class TestPinAnswer:
    async def test_moderator_can_pin_an_answer(self) -> None:
        service, answers, communities, _ = _seeded()
        moderator_id, community_id = uuid4(), uuid4()
        answer = await _seed_answer(answers, community_id=community_id)
        communities.add_membership(
            make_member_summary(
                community_id=community_id, user_id=moderator_id, role=CommunityRole.MODERATOR
            )
        )

        await service.execute(
            SetAnswerPinnedInput(answer_id=answer.id, acting_user_id=moderator_id, pinned=True)
        )
        stored = await answers.get_by_id(answer.id)
        assert stored is not None
        assert stored.is_pinned is True

    async def test_plain_member_cannot_pin(self) -> None:
        service, answers, communities, _ = _seeded()
        member_id, community_id = uuid4(), uuid4()
        answer = await _seed_answer(answers, community_id=community_id)
        communities.add_membership(
            make_member_summary(community_id=community_id, user_id=member_id)
        )

        with pytest.raises(InsufficientAnswerRoleError):
            await service.execute(
                SetAnswerPinnedInput(answer_id=answer.id, acting_user_id=member_id, pinned=True)
            )

    async def test_unknown_answer_raises(self) -> None:
        service, _, _, _ = _seeded()
        with pytest.raises(AnswerNotFoundError):
            await service.execute(
                SetAnswerPinnedInput(answer_id=uuid4(), acting_user_id=uuid4(), pinned=True)
            )

    async def test_commits_the_unit_of_work(self) -> None:
        service, answers, communities, uow = _seeded()
        moderator_id, community_id = uuid4(), uuid4()
        answer = await _seed_answer(answers, community_id=community_id)
        communities.add_membership(
            make_member_summary(
                community_id=community_id, user_id=moderator_id, role=CommunityRole.MODERATOR
            )
        )

        await service.execute(
            SetAnswerPinnedInput(answer_id=answer.id, acting_user_id=moderator_id, pinned=True)
        )
        assert uow.committed is True
