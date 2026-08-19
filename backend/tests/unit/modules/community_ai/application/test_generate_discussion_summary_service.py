"""Unit tests for `GenerateDiscussionSummaryService`, using in-memory fakes."""

from uuid import uuid4

import pytest

from app.modules.community_ai.application.dto import GenerateDiscussionSummaryInput
from app.modules.community_ai.application.services.generate_discussion_summary_service import (
    GenerateDiscussionSummaryService,
)
from app.modules.community_ai.domain.enums import AIAnalysisStatus, CommunityContentTargetType
from app.modules.community_ai.domain.exceptions import AnalysisTargetNotFoundError
from tests.unit.modules.community_ai.application.fakes import (
    FakeAICommunityAnalysisRepository,
    FakeAnswerQueryPort,
    FakeCommentQueryPort,
    FakeCommunityAIGeneratorPort,
    FakeCommunityQueryPort,
    FakeModerationQueryPort,
    FakePostQueryPort,
    FakeQuestionQueryPort,
    FakeUnitOfWork,
    make_post_summary,
)


def _seeded() -> (
    tuple[
        GenerateDiscussionSummaryService,
        FakeAICommunityAnalysisRepository,
        FakePostQueryPort,
        FakeCommunityAIGeneratorPort,
        FakeModerationQueryPort,
        FakeUnitOfWork,
    ]
):
    analyses = FakeAICommunityAnalysisRepository()
    generator = FakeCommunityAIGeneratorPort()
    posts = FakePostQueryPort()
    moderation = FakeModerationQueryPort()
    uow = FakeUnitOfWork()
    service = GenerateDiscussionSummaryService(
        analysis_repository=analyses,
        generator=generator,
        post_query_port=posts,
        question_query_port=FakeQuestionQueryPort(),
        answer_query_port=FakeAnswerQueryPort(),
        comment_query_port=FakeCommentQueryPort(),
        community_query_port=FakeCommunityQueryPort(),
        moderation_query_port=moderation,
        unit_of_work=uow,
    )
    return service, analyses, posts, generator, moderation, uow


class TestGenerateDiscussionSummary:
    async def test_generates_and_persists_a_completed_summary(self) -> None:
        service, analyses, posts, generator, _, uow = _seeded()
        org_id, post_id = uuid4(), uuid4()
        posts.add_post(make_post_summary(post_id=post_id, organization_id=org_id))

        output = await service.execute(
            GenerateDiscussionSummaryInput(
                organization_id=org_id,
                requester_id=uuid4(),
                target_type=CommunityContentTargetType.POST,
                target_id=post_id,
            )
        )

        assert output.status is AIAnalysisStatus.COMPLETED
        assert output.result is not None
        assert generator.calls == ["generate_summary"]
        assert uow.committed is True
        stored = await analyses.get_by_id(output.analysis_id)
        assert stored is not None
        assert stored.status is AIAnalysisStatus.COMPLETED

    async def test_second_call_for_the_same_target_returns_the_cached_result_without_a_new_ai_call(
        self,
    ) -> None:
        service, _, posts, generator, _, _ = _seeded()
        org_id, post_id = uuid4(), uuid4()
        posts.add_post(make_post_summary(post_id=post_id, organization_id=org_id))
        input_dto = GenerateDiscussionSummaryInput(
            organization_id=org_id,
            requester_id=uuid4(),
            target_type=CommunityContentTargetType.POST,
            target_id=post_id,
        )

        first = await service.execute(input_dto)
        second = await service.execute(input_dto)

        assert second.analysis_id == first.analysis_id
        assert generator.calls == ["generate_summary"]

    async def test_raises_not_found_for_a_nonexistent_target(self) -> None:
        service, *_ = _seeded()
        with pytest.raises(AnalysisTargetNotFoundError):
            await service.execute(
                GenerateDiscussionSummaryInput(
                    organization_id=uuid4(),
                    requester_id=uuid4(),
                    target_type=CommunityContentTargetType.POST,
                    target_id=uuid4(),
                )
            )

    async def test_raises_not_found_for_a_target_belonging_to_a_different_organization(
        self,
    ) -> None:
        service, _, posts, _, _, _ = _seeded()
        post_id = uuid4()
        posts.add_post(make_post_summary(post_id=post_id, organization_id=uuid4()))

        with pytest.raises(AnalysisTargetNotFoundError):
            await service.execute(
                GenerateDiscussionSummaryInput(
                    organization_id=uuid4(),
                    requester_id=uuid4(),
                    target_type=CommunityContentTargetType.POST,
                    target_id=post_id,
                )
            )

    async def test_raises_not_found_for_a_moderated_target(self) -> None:
        from app.modules.community_moderation.public.dto import ModerationTargetType

        service, _, posts, _, moderation, _ = _seeded()
        org_id, post_id = uuid4(), uuid4()
        posts.add_post(make_post_summary(post_id=post_id, organization_id=org_id))
        moderation.set_content_status(ModerationTargetType.POST, post_id, "removed")

        with pytest.raises(AnalysisTargetNotFoundError):
            await service.execute(
                GenerateDiscussionSummaryInput(
                    organization_id=org_id,
                    requester_id=uuid4(),
                    target_type=CommunityContentTargetType.POST,
                    target_id=post_id,
                )
            )

    async def test_marks_the_analysis_failed_and_reraises_when_the_generator_errors(self) -> None:
        service, analyses, posts, generator, _, uow = _seeded()
        org_id, post_id = uuid4(), uuid4()
        posts.add_post(make_post_summary(post_id=post_id, organization_id=org_id))
        generator.raise_error = RuntimeError("provider unavailable")

        with pytest.raises(RuntimeError):
            await service.execute(
                GenerateDiscussionSummaryInput(
                    organization_id=org_id,
                    requester_id=uuid4(),
                    target_type=CommunityContentTargetType.POST,
                    target_id=post_id,
                )
            )

        stored_all, _ = await analyses.list_analyses(organization_id=org_id)
        assert len(stored_all) == 1
        assert stored_all[0].status is AIAnalysisStatus.FAILED
        assert uow.committed is True
