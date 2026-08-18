"""Unit tests for `FeatureAnswerService`, using in-memory fakes."""

from uuid import uuid4

import pytest

from app.modules.community.public.dto import CommunityRole
from app.modules.community_answers.application.dto import SetAnswerFeaturedInput
from app.modules.community_answers.application.services.feature_answer_service import (
    FeatureAnswerService,
)
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
    tuple[
        FeatureAnswerService, FakeCommunityAnswerRepository, FakeCommunityQueryPort, FakeUnitOfWork
    ]
):
    answers = FakeCommunityAnswerRepository()
    communities = FakeCommunityQueryPort()
    uow = FakeUnitOfWork()
    service = FeatureAnswerService(
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


class TestFeatureAnswer:
    async def test_moderator_can_feature_an_answer(self) -> None:
        service, answers, communities, _ = _seeded()
        moderator_id, community_id = uuid4(), uuid4()
        answer = await _seed_answer(answers, community_id=community_id)
        communities.add_membership(
            make_member_summary(
                community_id=community_id, user_id=moderator_id, role=CommunityRole.MODERATOR
            )
        )

        await service.execute(
            SetAnswerFeaturedInput(answer_id=answer.id, acting_user_id=moderator_id, featured=True)
        )
        stored = await answers.get_by_id(answer.id)
        assert stored is not None
        assert stored.is_featured is True

    async def test_authors_answer_still_requires_moderator_role(self) -> None:
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
        await answers.add(answer)
        communities.add_membership(
            make_member_summary(community_id=community_id, user_id=author_id)
        )

        with pytest.raises(InsufficientAnswerRoleError):
            await service.execute(
                SetAnswerFeaturedInput(answer_id=answer.id, acting_user_id=author_id, featured=True)
            )

    async def test_plain_member_cannot_feature(self) -> None:
        service, answers, communities, _ = _seeded()
        member_id, community_id = uuid4(), uuid4()
        answer = await _seed_answer(answers, community_id=community_id)
        communities.add_membership(
            make_member_summary(community_id=community_id, user_id=member_id)
        )

        with pytest.raises(InsufficientAnswerRoleError):
            await service.execute(
                SetAnswerFeaturedInput(answer_id=answer.id, acting_user_id=member_id, featured=True)
            )

    async def test_unknown_answer_raises(self) -> None:
        service, _, _, _ = _seeded()
        with pytest.raises(AnswerNotFoundError):
            await service.execute(
                SetAnswerFeaturedInput(answer_id=uuid4(), acting_user_id=uuid4(), featured=True)
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
            SetAnswerFeaturedInput(answer_id=answer.id, acting_user_id=moderator_id, featured=True)
        )
        assert uow.committed is True
