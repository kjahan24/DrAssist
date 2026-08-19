"""`CommunityAIFacade` — the one concrete implementation of
`CommunityAIQueryPort`. Constructed per-request by
`app.modules.community_ai.container.build_community_ai_facade`, bound to
that request's `AsyncSession`.
"""

from uuid import UUID

from app.modules.community_ai.application.services._summary_mappers import analysis_to_summary
from app.modules.community_ai.domain.enums import AIAnalysisStatus, AIAnalysisType
from app.modules.community_ai.domain.repositories import AICommunityAnalysisRepository
from app.modules.community_ai.public.dto import (
    AICommunityAnalysisSummaryDTO,
    CommunityContentTargetType,
)
from app.modules.community_ai.public.interfaces import CommunityAIQueryPort


class CommunityAIFacade(CommunityAIQueryPort):
    def __init__(self, *, analysis_repository: AICommunityAnalysisRepository) -> None:
        self._analyses = analysis_repository

    async def get_latest_completed_analysis(
        self,
        target_type: CommunityContentTargetType,
        target_id: UUID,
        analysis_type: AIAnalysisType,
        *,
        organization_id: UUID,
    ) -> AICommunityAnalysisSummaryDTO | None:
        analysis = await self._analyses.get_by_target(target_type, target_id, analysis_type)
        if (
            analysis is None
            or analysis.organization_id != organization_id
            or analysis.status is not AIAnalysisStatus.COMPLETED
        ):
            return None
        return analysis_to_summary(analysis)
