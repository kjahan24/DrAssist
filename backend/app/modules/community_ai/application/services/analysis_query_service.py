"""`GetAIAnalysisService`/`ListAIAnalysesService` — read-only analysis
queries, combined in one file since both are thin repository wrappers
with no state-mutating logic, mirroring
`app.modules.community_engagement.application.services.vote_query_service`
's identical pairing precedent.

Both are scoped to `organization_id` (tenant isolation) but deliberately
do **not** re-check the underlying target's own visibility/moderation
status the way `Generate*`/`Find*`/`RefreshAIAnalysis` do — an analysis
row's own `organization_id` already tracks the *acting requester's*
tenant at the time it was created (never the target's own, independently
re-derivable, visibility), so re-resolving the target on every list/get
call would be an unnecessary extra round-trip per row for a read path
this task's own AUTHORIZATION section does not ask to be that strict
about; the tenant check alone is what every other query-only service in
this codebase (e.g. `community_moderation.report_query_service`) already
settles for.
"""

from uuid import UUID

from app.modules.community_ai.application.dto import (
    AICommunityAnalysisSummaryDTO,
    AnalysisFeedOutput,
    ListAIAnalysesInput,
)
from app.modules.community_ai.application.services._summary_mappers import analysis_to_summary
from app.modules.community_ai.domain.exceptions import AnalysisNotFoundError
from app.modules.community_ai.domain.repositories import AICommunityAnalysisRepository


class GetAIAnalysisService:
    def __init__(self, *, analysis_repository: AICommunityAnalysisRepository) -> None:
        self._analyses = analysis_repository

    async def get_analysis(
        self, analysis_id: UUID, *, organization_id: UUID
    ) -> AICommunityAnalysisSummaryDTO:
        analysis = await self._analyses.get_by_id(analysis_id)
        if analysis is None or analysis.organization_id != organization_id:
            raise AnalysisNotFoundError(analysis_id)
        return analysis_to_summary(analysis)


class ListAIAnalysesService:
    def __init__(self, *, analysis_repository: AICommunityAnalysisRepository) -> None:
        self._analyses = analysis_repository

    async def list_analyses(self, input_dto: ListAIAnalysesInput) -> AnalysisFeedOutput:
        analyses, next_cursor = await self._analyses.list_analyses(
            organization_id=input_dto.organization_id,
            target_type=input_dto.target_type,
            target_id=input_dto.target_id,
            analysis_type=input_dto.analysis_type,
            status=input_dto.status,
            cursor=input_dto.cursor,
            limit=input_dto.limit,
        )
        return AnalysisFeedOutput(
            items=[analysis_to_summary(a) for a in analyses], next_cursor=next_cursor
        )
