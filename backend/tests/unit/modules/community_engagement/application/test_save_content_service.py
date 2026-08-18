"""Unit tests for `SaveContentService`, using in-memory fakes."""

from uuid import uuid4

import pytest

from app.modules.community_answers.public.dto import AnswerStatus
from app.modules.community_engagement.application.dto import SaveContentInput
from app.modules.community_engagement.application.services.save_content_service import (
    SaveContentService,
)
from app.modules.community_engagement.domain.enums import EngagementTargetType
from app.modules.community_engagement.domain.events import ContentSaved
from app.modules.community_engagement.domain.exceptions import (
    SaveTargetNotAcceptingSavesError,
    SaveTargetNotFoundError,
    UnsupportedSaveTargetTypeError,
)
from tests.unit.modules.community_engagement.application.fakes import (
    FakeAnswerQueryPort,
    FakeCommentQueryPort,
    FakePostQueryPort,
    FakeQuestionQueryPort,
    FakeSavedContentRepository,
    FakeUnitOfWork,
    make_answer_summary,
)


def _seeded() -> (
    tuple[
        SaveContentService,
        FakeSavedContentRepository,
        FakePostQueryPort,
        FakeQuestionQueryPort,
        FakeAnswerQueryPort,
        FakeCommentQueryPort,
        FakeUnitOfWork,
    ]
):
    saved = FakeSavedContentRepository()
    posts = FakePostQueryPort()
    questions = FakeQuestionQueryPort()
    answers = FakeAnswerQueryPort()
    comments = FakeCommentQueryPort()
    uow = FakeUnitOfWork()
    service = SaveContentService(
        saved_content_repository=saved,
        post_query_port=posts,
        question_query_port=questions,
        answer_query_port=answers,
        comment_query_port=comments,
        unit_of_work=uow,
    )
    return service, saved, posts, questions, answers, comments, uow


class TestSaveContent:
    async def test_saves_an_answer(self) -> None:
        service, saved, _, _, answers, _, _ = _seeded()
        org_id, answer_id, user_id = uuid4(), uuid4(), uuid4()
        answers.add_answer(make_answer_summary(answer_id=answer_id, organization_id=org_id))

        output = await service.execute(
            SaveContentInput(
                target_type=EngagementTargetType.ANSWER,
                target_id=answer_id,
                user_id=user_id,
                organization_id=org_id,
            )
        )
        assert output.target_id == answer_id
        stored = await saved.get_saved(user_id, EngagementTargetType.ANSWER, answer_id)
        assert stored is not None

    async def test_comment_target_type_is_rejected(self) -> None:
        service, _, _, _, _, _, _ = _seeded()
        with pytest.raises(UnsupportedSaveTargetTypeError):
            await service.execute(
                SaveContentInput(
                    target_type=EngagementTargetType.COMMENT,
                    target_id=uuid4(),
                    user_id=uuid4(),
                    organization_id=uuid4(),
                )
            )

    async def test_unknown_target_raises(self) -> None:
        service, _, _, _, _, _, _ = _seeded()
        with pytest.raises(SaveTargetNotFoundError):
            await service.execute(
                SaveContentInput(
                    target_type=EngagementTargetType.ANSWER,
                    target_id=uuid4(),
                    user_id=uuid4(),
                    organization_id=uuid4(),
                )
            )

    async def test_cross_tenant_target_raises_not_found(self) -> None:
        service, _, _, _, answers, _, _ = _seeded()
        answer_id = uuid4()
        answers.add_answer(make_answer_summary(answer_id=answer_id, organization_id=uuid4()))

        with pytest.raises(SaveTargetNotFoundError):
            await service.execute(
                SaveContentInput(
                    target_type=EngagementTargetType.ANSWER,
                    target_id=answer_id,
                    user_id=uuid4(),
                    organization_id=uuid4(),
                )
            )

    async def test_draft_target_rejects_saving(self) -> None:
        service, _, _, _, answers, _, _ = _seeded()
        org_id, answer_id = uuid4(), uuid4()
        answers.add_answer(
            make_answer_summary(
                answer_id=answer_id, organization_id=org_id, status=AnswerStatus.DRAFT
            )
        )

        with pytest.raises(SaveTargetNotAcceptingSavesError):
            await service.execute(
                SaveContentInput(
                    target_type=EngagementTargetType.ANSWER,
                    target_id=answer_id,
                    user_id=uuid4(),
                    organization_id=org_id,
                )
            )

    async def test_idempotent_when_already_saved(self) -> None:
        service, saved, _, _, answers, _, uow = _seeded()
        org_id, answer_id, user_id = uuid4(), uuid4(), uuid4()
        answers.add_answer(make_answer_summary(answer_id=answer_id, organization_id=org_id))
        first = await service.execute(
            SaveContentInput(
                target_type=EngagementTargetType.ANSWER,
                target_id=answer_id,
                user_id=user_id,
                organization_id=org_id,
            )
        )

        uow.committed = False
        second = await service.execute(
            SaveContentInput(
                target_type=EngagementTargetType.ANSWER,
                target_id=answer_id,
                user_id=user_id,
                organization_id=org_id,
            )
        )
        assert second.saved_content_id == first.saved_content_id
        assert uow.committed is False
        results, _ = await saved.list_by_user(user_id)
        assert len(results) == 1

    async def test_commits_the_unit_of_work(self) -> None:
        service, _, _, _, answers, _, uow = _seeded()
        org_id, answer_id = uuid4(), uuid4()
        answers.add_answer(make_answer_summary(answer_id=answer_id, organization_id=org_id))

        await service.execute(
            SaveContentInput(
                target_type=EngagementTargetType.ANSWER,
                target_id=answer_id,
                user_id=uuid4(),
                organization_id=org_id,
            )
        )
        assert uow.committed is True

    async def test_publishes_a_content_saved_event(self) -> None:
        service, _, _, _, answers, _, uow = _seeded()
        org_id, answer_id = uuid4(), uuid4()
        answers.add_answer(make_answer_summary(answer_id=answer_id, organization_id=org_id))

        await service.execute(
            SaveContentInput(
                target_type=EngagementTargetType.ANSWER,
                target_id=answer_id,
                user_id=uuid4(),
                organization_id=org_id,
            )
        )
        assert any(isinstance(e, ContentSaved) for e in uow.published_events)
