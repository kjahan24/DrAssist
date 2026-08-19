"""Unit tests for `AnalyzeMisinformationService`, using in-memory fakes."""

from uuid import uuid4

from app.modules.community_ai.application.dto import AnalyzeMisinformationInput
from app.modules.community_ai.application.services.analyze_misinformation_service import (
    AnalyzeMisinformationService,
)
from app.modules.community_ai.domain.enums import AIAnalysisStatus, CommunityContentTargetType
from app.modules.community_ai.domain.events import HighRiskMisinformationDetected
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
    make_misinformation_assessment,
    make_post_summary,
)


def _seeded() -> (
    tuple[
        AnalyzeMisinformationService,
        FakeAICommunityAnalysisRepository,
        FakePostQueryPort,
        FakeCommunityAIGeneratorPort,
        FakeUnitOfWork,
    ]
):
    analyses = FakeAICommunityAnalysisRepository()
    generator = FakeCommunityAIGeneratorPort()
    posts = FakePostQueryPort()
    uow = FakeUnitOfWork()
    service = AnalyzeMisinformationService(
        analysis_repository=analyses,
        generator=generator,
        post_query_port=posts,
        question_query_port=FakeQuestionQueryPort(),
        answer_query_port=FakeAnswerQueryPort(),
        comment_query_port=FakeCommentQueryPort(),
        community_query_port=FakeCommunityQueryPort(),
        moderation_query_port=FakeModerationQueryPort(),
        unit_of_work=uow,
    )
    return service, analyses, posts, generator, uow


class TestAnalyzeMisinformation:
    async def test_low_risk_result_does_not_record_a_high_risk_event(self) -> None:
        from app.modules.community_ai.domain.enums import MisinformationRiskLevel

        service, _, posts, generator, uow = _seeded()
        org_id, post_id = uuid4(), uuid4()
        posts.add_post(make_post_summary(post_id=post_id, organization_id=org_id))
        generator.misinformation_result = make_misinformation_assessment(
            risk_level=MisinformationRiskLevel.LOW, recommended_for_moderation_review=False
        )

        output = await service.execute(
            AnalyzeMisinformationInput(
                organization_id=org_id,
                requester_id=uuid4(),
                target_type=CommunityContentTargetType.POST,
                target_id=post_id,
            )
        )

        assert output.status is AIAnalysisStatus.COMPLETED
        assert not any(
            isinstance(event, HighRiskMisinformationDetected) for event in uow.published_events
        )

    async def test_high_risk_result_records_a_high_risk_event_without_writing_to_moderation(
        self,
    ) -> None:
        from app.modules.community_ai.domain.enums import MisinformationRiskLevel

        service, _, posts, generator, uow = _seeded()
        org_id, post_id = uuid4(), uuid4()
        posts.add_post(make_post_summary(post_id=post_id, organization_id=org_id))
        generator.misinformation_result = make_misinformation_assessment(
            risk_level=MisinformationRiskLevel.HIGH, recommended_for_moderation_review=True
        )

        output = await service.execute(
            AnalyzeMisinformationInput(
                organization_id=org_id,
                requester_id=uuid4(),
                target_type=CommunityContentTargetType.POST,
                target_id=post_id,
            )
        )

        assert output.status is AIAnalysisStatus.COMPLETED
        escalations = [
            event
            for event in uow.published_events
            if isinstance(event, HighRiskMisinformationDetected)
        ]
        assert len(escalations) == 1
        assert escalations[0].analysis_id == output.analysis_id
        assert escalations[0].risk_level is MisinformationRiskLevel.HIGH

    async def test_critical_risk_result_also_escalates(self) -> None:
        from app.modules.community_ai.domain.enums import MisinformationRiskLevel

        service, _, posts, generator, uow = _seeded()
        org_id, post_id = uuid4(), uuid4()
        posts.add_post(make_post_summary(post_id=post_id, organization_id=org_id))
        generator.misinformation_result = make_misinformation_assessment(
            risk_level=MisinformationRiskLevel.CRITICAL, recommended_for_moderation_review=True
        )

        await service.execute(
            AnalyzeMisinformationInput(
                organization_id=org_id,
                requester_id=uuid4(),
                target_type=CommunityContentTargetType.POST,
                target_id=post_id,
            )
        )

        assert any(
            isinstance(event, HighRiskMisinformationDetected) for event in uow.published_events
        )
