"""Unit tests for `CommunityAIFacade` — exercised through
`CommunityAIQueryPort` exactly as a future consumer module would call it,
per `docs/backend-architecture/12_testing_architecture.md`'s "Contract
tests" framing."""

from uuid import uuid4

from app.modules.community_ai.domain.entities import AICommunityAnalysis
from app.modules.community_ai.domain.enums import AIAnalysisType, CommunityContentTargetType
from app.modules.community_ai.public.facade import CommunityAIFacade
from app.modules.community_ai.public.interfaces import CommunityAIQueryPort
from tests.unit.modules.community_ai.application.fakes import FakeAICommunityAnalysisRepository


def _facade() -> tuple[CommunityAIFacade, FakeAICommunityAnalysisRepository]:
    repository = FakeAICommunityAnalysisRepository()
    return CommunityAIFacade(analysis_repository=repository), repository


class TestCommunityAIFacade:
    def test_is_a_community_ai_query_port(self) -> None:
        facade, _ = _facade()
        assert isinstance(facade, CommunityAIQueryPort)

    async def test_returns_none_when_no_analysis_exists_yet(self) -> None:
        facade, _ = _facade()
        result = await facade.get_latest_completed_analysis(
            CommunityContentTargetType.POST,
            uuid4(),
            AIAnalysisType.SUMMARY,
            organization_id=uuid4(),
        )
        assert result is None

    async def test_returns_none_for_an_analysis_that_has_not_completed_yet(self) -> None:
        facade, repository = _facade()
        org_id, target_id = uuid4(), uuid4()
        pending = AICommunityAnalysis.request(
            organization_id=org_id,
            analysis_type=AIAnalysisType.SUMMARY,
            target_type=CommunityContentTargetType.POST,
            target_id=target_id,
        )
        await repository.add(pending)

        result = await facade.get_latest_completed_analysis(
            CommunityContentTargetType.POST,
            target_id,
            AIAnalysisType.SUMMARY,
            organization_id=org_id,
        )
        assert result is None

    async def test_returns_none_for_a_completed_analysis_belonging_to_another_organization(
        self,
    ) -> None:
        facade, repository = _facade()
        target_id = uuid4()
        completed = AICommunityAnalysis.request(
            organization_id=uuid4(),
            analysis_type=AIAnalysisType.SUMMARY,
            target_type=CommunityContentTargetType.POST,
            target_id=target_id,
        )
        completed.mark_processing()
        completed.mark_completed(
            result={"key_points": []}, confidence_score=None, ai_provider="mock", ai_model="mock"
        )
        await repository.add(completed)

        result = await facade.get_latest_completed_analysis(
            CommunityContentTargetType.POST,
            target_id,
            AIAnalysisType.SUMMARY,
            organization_id=uuid4(),
        )
        assert result is None

    async def test_returns_the_completed_analysis_for_the_owning_organization(self) -> None:
        facade, repository = _facade()
        org_id, target_id = uuid4(), uuid4()
        completed = AICommunityAnalysis.request(
            organization_id=org_id,
            analysis_type=AIAnalysisType.SUMMARY,
            target_type=CommunityContentTargetType.POST,
            target_id=target_id,
        )
        completed.mark_processing()
        completed.mark_completed(
            result={"key_points": ["A"]},
            confidence_score=None,
            ai_provider="mock",
            ai_model="mock",
        )
        await repository.add(completed)

        result = await facade.get_latest_completed_analysis(
            CommunityContentTargetType.POST,
            target_id,
            AIAnalysisType.SUMMARY,
            organization_id=org_id,
        )
        assert result is not None
        assert result.analysis_id == completed.id
