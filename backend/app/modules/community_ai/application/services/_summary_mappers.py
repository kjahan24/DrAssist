"""Maps `AICommunityAnalysis` to its application-layer summary DTO — kept
separate from the services themselves so every service and the public
facade share exactly one mapping definition, the same split every prior
module's own `_summary_mappers.py` establishes."""

from app.modules.community_ai.application.dto import AICommunityAnalysisSummaryDTO
from app.modules.community_ai.domain.entities import AICommunityAnalysis


def analysis_to_summary(analysis: AICommunityAnalysis) -> AICommunityAnalysisSummaryDTO:
    return AICommunityAnalysisSummaryDTO(
        analysis_id=analysis.id,
        organization_id=analysis.organization_id,
        analysis_type=analysis.analysis_type,
        target_type=analysis.target_type,
        target_id=analysis.target_id,
        status=analysis.status,
        created_at=analysis.created_at,
        updated_at=analysis.updated_at,
        result=analysis.result,
        confidence_score=analysis.confidence_score,
        ai_provider=analysis.ai_provider,
        ai_model=analysis.ai_model,
        error_message=analysis.error_message,
        latency_ms=analysis.latency_ms,
    )
