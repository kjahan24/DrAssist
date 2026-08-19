"""Unit tests for `RefreshAIAnalysisService`, using in-memory fakes."""

from uuid import uuid4

import pytest

from app.modules.community_ai.application.dto import RefreshAIAnalysisInput
from app.modules.community_ai.application.services.refresh_ai_analysis_service import (
    RefreshAIAnalysisService,
)
from app.modules.community_ai.domain.entities import AICommunityAnalysis
from app.modules.community_ai.domain.enums import (
    AIAnalysisStatus,
    AIAnalysisType,
    CommunityContentTargetType,
)
from app.modules.community_ai.domain.exceptions import AnalysisNotFoundError
from tests.unit.modules.community_ai.application.fakes import (
    FakeAICommunityAnalysisRepository,
    FakeAnswerQueryPort,
    FakeCommentQueryPort,
    FakeCommunityAIGeneratorPort,
    FakeCommunityQueryPort,
    FakeModerationQueryPort,
    FakePostQueryPort,
    FakeQuestionQueryPort,
    FakeSimilarDiscussionSearchPort,
    FakeTrustedResourceCatalogPort,
    FakeUnitOfWork,
    make_post_summary,
)


def _seeded() -> (
    tuple[
        RefreshAIAnalysisService,
        FakeAICommunityAnalysisRepository,
        FakePostQueryPort,
        FakeCommunityAIGeneratorPort,
    ]
):
    analyses = FakeAICommunityAnalysisRepository()
    generator = FakeCommunityAIGeneratorPort()
    posts = FakePostQueryPort()
    service = RefreshAIAnalysisService(
        analysis_repository=analyses,
        generator=generator,
        search_port=FakeSimilarDiscussionSearchPort(),
        catalog=FakeTrustedResourceCatalogPort(),
        post_query_port=posts,
        question_query_port=FakeQuestionQueryPort(),
        answer_query_port=FakeAnswerQueryPort(),
        comment_query_port=FakeCommentQueryPort(),
        community_query_port=FakeCommunityQueryPort(),
        moderation_query_port=FakeModerationQueryPort(),
        unit_of_work=FakeUnitOfWork(),
    )
    return service, analyses, posts, generator


class TestRefreshAIAnalysis:
    async def test_reruns_a_completed_analysis_in_place_without_inserting_a_new_row(self) -> None:
        service, analyses, posts, generator = _seeded()
        org_id, post_id = uuid4(), uuid4()
        posts.add_post(make_post_summary(post_id=post_id, organization_id=org_id))
        existing = AICommunityAnalysis.request(
            organization_id=org_id,
            analysis_type=AIAnalysisType.SUMMARY,
            target_type=CommunityContentTargetType.POST,
            target_id=post_id,
        )
        existing.mark_processing()
        existing.mark_completed(
            result={"key_points": []},
            confidence_score=None,
            ai_provider="mock",
            ai_model="mock-model",
        )
        await analyses.add(existing)

        output = await service.execute(
            RefreshAIAnalysisInput(
                organization_id=org_id, requester_id=uuid4(), analysis_id=existing.id
            )
        )

        assert output.analysis_id == existing.id
        assert output.status is AIAnalysisStatus.COMPLETED
        assert generator.calls == ["generate_summary"]
        all_rows, _ = await analyses.list_analyses(organization_id=org_id)
        assert len(all_rows) == 1

    async def test_reruns_a_failed_analysis(self) -> None:
        service, analyses, posts, generator = _seeded()
        org_id, post_id = uuid4(), uuid4()
        posts.add_post(make_post_summary(post_id=post_id, organization_id=org_id))
        existing = AICommunityAnalysis.request(
            organization_id=org_id,
            analysis_type=AIAnalysisType.MISINFORMATION,
            target_type=CommunityContentTargetType.POST,
            target_id=post_id,
        )
        existing.mark_processing()
        existing.mark_failed("timed out")
        await analyses.add(existing)

        output = await service.execute(
            RefreshAIAnalysisInput(
                organization_id=org_id, requester_id=uuid4(), analysis_id=existing.id
            )
        )

        assert output.status is AIAnalysisStatus.COMPLETED
        assert generator.calls == ["generate_misinformation_assessment"]

    async def test_raises_not_found_for_an_unknown_analysis_id(self) -> None:
        service, *_ = _seeded()
        with pytest.raises(AnalysisNotFoundError):
            await service.execute(
                RefreshAIAnalysisInput(
                    organization_id=uuid4(), requester_id=uuid4(), analysis_id=uuid4()
                )
            )

    async def test_raises_not_found_when_the_analysis_belongs_to_a_different_organization(
        self,
    ) -> None:
        service, analyses, posts, _ = _seeded()
        post_id = uuid4()
        posts.add_post(make_post_summary(post_id=post_id, organization_id=uuid4()))
        existing = AICommunityAnalysis.request(
            organization_id=uuid4(),
            analysis_type=AIAnalysisType.SUMMARY,
            target_type=CommunityContentTargetType.POST,
            target_id=post_id,
        )
        await analyses.add(existing)

        with pytest.raises(AnalysisNotFoundError):
            await service.execute(
                RefreshAIAnalysisInput(
                    organization_id=uuid4(), requester_id=uuid4(), analysis_id=existing.id
                )
            )
