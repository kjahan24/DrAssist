"""Integration tests for `SqlAlchemyAICommunityAnalysisRepository` against
a real PostgreSQL instance: round-trip persistence, `get_by_target`
idempotency lookups, `list_analyses` filtering/cursor pagination, and the
`(target_type, target_id, analysis_type)` unique constraint that backs
"one row per target, mutated in place, never a second row"."""

from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from tests.integration.modules.community_ai._helpers import persist_organization

from app.modules.community_ai.domain.entities import AICommunityAnalysis
from app.modules.community_ai.domain.enums import (
    AIAnalysisStatus,
    AIAnalysisType,
    CommunityContentTargetType,
)
from app.modules.community_ai.infrastructure.repositories import (
    SqlAlchemyAICommunityAnalysisRepository,
)


class TestAICommunityAnalysisRoundTrip:
    async def test_save_and_reload_a_completed_analysis(self, db_session: AsyncSession) -> None:
        organization = await persist_organization(db_session)
        repo = SqlAlchemyAICommunityAnalysisRepository(db_session)
        target_id = uuid4()
        analysis = AICommunityAnalysis.request(
            organization_id=organization.id,
            analysis_type=AIAnalysisType.SUMMARY,
            target_type=CommunityContentTargetType.POST,
            target_id=target_id,
        )
        analysis.mark_processing()
        analysis.mark_completed(
            result={"key_points": ["A"]},
            confidence_score=0.87,
            ai_provider="mock",
            ai_model="mock-model",
            latency_ms=42.0,
        )

        await repo.add(analysis)
        await db_session.commit()

        reloaded = await repo.get_by_id(analysis.id)
        assert reloaded is not None
        assert reloaded.organization_id == organization.id
        assert reloaded.status is AIAnalysisStatus.COMPLETED
        assert reloaded.result == {"key_points": ["A"]}
        assert reloaded.confidence_score == 0.87
        assert reloaded.ai_provider == "mock"
        assert reloaded.ai_model == "mock-model"
        assert reloaded.latency_ms == 42.0

    async def test_reruns_the_same_row_in_place_via_add(self, db_session: AsyncSession) -> None:
        organization = await persist_organization(db_session)
        repo = SqlAlchemyAICommunityAnalysisRepository(db_session)
        target_id = uuid4()
        analysis = AICommunityAnalysis.request(
            organization_id=organization.id,
            analysis_type=AIAnalysisType.MISINFORMATION,
            target_type=CommunityContentTargetType.QUESTION,
            target_id=target_id,
        )
        analysis.mark_processing()
        await repo.add(analysis)
        await db_session.commit()

        analysis.mark_completed(
            result={"risk_level": "low"},
            confidence_score=0.5,
            ai_provider="mock",
            ai_model="mock-model",
        )
        await repo.add(analysis)
        await db_session.commit()

        found = await repo.get_by_target(
            CommunityContentTargetType.QUESTION, target_id, AIAnalysisType.MISINFORMATION
        )
        assert found is not None
        assert found.id == analysis.id
        assert found.status is AIAnalysisStatus.COMPLETED


class TestGetByTarget:
    async def test_returns_none_when_never_analyzed(self, db_session: AsyncSession) -> None:
        repo = SqlAlchemyAICommunityAnalysisRepository(db_session)
        result = await repo.get_by_target(
            CommunityContentTargetType.POST, uuid4(), AIAnalysisType.SUMMARY
        )
        assert result is None


class TestListAnalyses:
    async def test_filters_by_organization_and_analysis_type(
        self, db_session: AsyncSession
    ) -> None:
        organization = await persist_organization(db_session)
        other_organization = await persist_organization(db_session)
        repo = SqlAlchemyAICommunityAnalysisRepository(db_session)

        mine = AICommunityAnalysis.request(
            organization_id=organization.id,
            analysis_type=AIAnalysisType.SUMMARY,
            target_type=CommunityContentTargetType.POST,
            target_id=uuid4(),
        )
        other_type = AICommunityAnalysis.request(
            organization_id=organization.id,
            analysis_type=AIAnalysisType.MISINFORMATION,
            target_type=CommunityContentTargetType.POST,
            target_id=uuid4(),
        )
        theirs = AICommunityAnalysis.request(
            organization_id=other_organization.id,
            analysis_type=AIAnalysisType.SUMMARY,
            target_type=CommunityContentTargetType.POST,
            target_id=uuid4(),
        )
        for a in (mine, other_type, theirs):
            await repo.add(a)
        await db_session.commit()

        results, _ = await repo.list_analyses(
            organization_id=organization.id, analysis_type=AIAnalysisType.SUMMARY
        )
        assert [r.id for r in results] == [mine.id]

    async def test_respects_cursor_pagination(self, db_session: AsyncSession) -> None:
        organization = await persist_organization(db_session)
        repo = SqlAlchemyAICommunityAnalysisRepository(db_session)
        for _ in range(3):
            analysis = AICommunityAnalysis.request(
                organization_id=organization.id,
                analysis_type=AIAnalysisType.SUMMARY,
                target_type=CommunityContentTargetType.POST,
                target_id=uuid4(),
            )
            await repo.add(analysis)
            await db_session.commit()

        first_page, next_cursor = await repo.list_analyses(organization_id=organization.id, limit=2)
        assert len(first_page) == 2
        assert next_cursor is not None

        second_page, second_cursor = await repo.list_analyses(
            organization_id=organization.id, cursor=next_cursor, limit=2
        )
        assert len(second_page) == 1
        assert second_cursor is None


class TestUniqueConstraint:
    async def test_a_second_distinct_row_for_the_same_target_and_type_violates_the_constraint(
        self, db_session: AsyncSession
    ) -> None:
        organization = await persist_organization(db_session)
        repo = SqlAlchemyAICommunityAnalysisRepository(db_session)
        target_id = uuid4()

        first = AICommunityAnalysis.request(
            organization_id=organization.id,
            analysis_type=AIAnalysisType.SUMMARY,
            target_type=CommunityContentTargetType.POST,
            target_id=target_id,
        )
        await repo.add(first)
        await db_session.commit()

        second = AICommunityAnalysis.request(
            organization_id=organization.id,
            analysis_type=AIAnalysisType.SUMMARY,
            target_type=CommunityContentTargetType.POST,
            target_id=target_id,
        )
        await repo.add(second)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()
