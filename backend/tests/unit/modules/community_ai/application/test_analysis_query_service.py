"""Unit tests for `GetAIAnalysisService`/`ListAIAnalysesService`, using in-memory fakes."""

from uuid import uuid4

import pytest

from app.modules.community_ai.application.dto import ListAIAnalysesInput
from app.modules.community_ai.application.services.analysis_query_service import (
    GetAIAnalysisService,
    ListAIAnalysesService,
)
from app.modules.community_ai.domain.entities import AICommunityAnalysis
from app.modules.community_ai.domain.enums import AIAnalysisType, CommunityContentTargetType
from app.modules.community_ai.domain.exceptions import AnalysisNotFoundError
from tests.unit.modules.community_ai.application.fakes import FakeAICommunityAnalysisRepository


async def _add_analysis(
    repo: FakeAICommunityAnalysisRepository, *, organization_id: object, **overrides: object
) -> AICommunityAnalysis:
    analysis = AICommunityAnalysis.request(
        organization_id=organization_id,  # type: ignore[arg-type]
        analysis_type=overrides.get("analysis_type", AIAnalysisType.SUMMARY),  # type: ignore[arg-type]
        target_type=overrides.get(  # type: ignore[arg-type]
            "target_type", CommunityContentTargetType.POST
        ),
        target_id=overrides.get("target_id", uuid4()),  # type: ignore[arg-type]
    )
    await repo.add(analysis)
    return analysis


class TestGetAIAnalysis:
    async def test_returns_the_analysis_for_the_owning_organization(self) -> None:
        repo = FakeAICommunityAnalysisRepository()
        org_id = uuid4()
        analysis = await _add_analysis(repo, organization_id=org_id)
        service = GetAIAnalysisService(analysis_repository=repo)

        result = await service.get_analysis(analysis.id, organization_id=org_id)

        assert result.analysis_id == analysis.id

    async def test_raises_not_found_for_a_different_organization(self) -> None:
        repo = FakeAICommunityAnalysisRepository()
        analysis = await _add_analysis(repo, organization_id=uuid4())
        service = GetAIAnalysisService(analysis_repository=repo)

        with pytest.raises(AnalysisNotFoundError):
            await service.get_analysis(analysis.id, organization_id=uuid4())

    async def test_raises_not_found_for_an_unknown_id(self) -> None:
        service = GetAIAnalysisService(analysis_repository=FakeAICommunityAnalysisRepository())
        with pytest.raises(AnalysisNotFoundError):
            await service.get_analysis(uuid4(), organization_id=uuid4())


class TestListAIAnalyses:
    async def test_lists_only_the_requesting_organizations_analyses(self) -> None:
        repo = FakeAICommunityAnalysisRepository()
        org_id = uuid4()
        await _add_analysis(repo, organization_id=org_id)
        await _add_analysis(repo, organization_id=org_id)
        await _add_analysis(repo, organization_id=uuid4())
        service = ListAIAnalysesService(analysis_repository=repo)

        result = await service.list_analyses(ListAIAnalysesInput(organization_id=org_id))

        assert len(result.items) == 2
        assert all(item.organization_id == org_id for item in result.items)

    async def test_filters_by_analysis_type(self) -> None:
        repo = FakeAICommunityAnalysisRepository()
        org_id = uuid4()
        await _add_analysis(repo, organization_id=org_id, analysis_type=AIAnalysisType.SUMMARY)
        await _add_analysis(
            repo, organization_id=org_id, analysis_type=AIAnalysisType.MISINFORMATION
        )
        service = ListAIAnalysesService(analysis_repository=repo)

        result = await service.list_analyses(
            ListAIAnalysesInput(organization_id=org_id, analysis_type=AIAnalysisType.MISINFORMATION)
        )

        assert len(result.items) == 1
        assert result.items[0].analysis_type is AIAnalysisType.MISINFORMATION
