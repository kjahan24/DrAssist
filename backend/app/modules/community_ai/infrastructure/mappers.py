"""ORM model <-> domain entity mapper for the Community AI Features
module. Mirrors `app.modules.community_moderation.infrastructure.mappers`'
own shape exactly for its one entity/model pair.
"""

from app.modules.community_ai.domain.entities import AICommunityAnalysis
from app.modules.community_ai.infrastructure.models import CommunityAIAnalysisModel


def analysis_to_domain(model: CommunityAIAnalysisModel) -> AICommunityAnalysis:
    return AICommunityAnalysis(
        id=model.id,
        created_at=model.created_at,
        updated_at=model.updated_at,
        organization_id=model.organization_id,
        analysis_type=model.analysis_type,
        target_type=model.target_type,
        target_id=model.target_id,
        status=model.status,
        result=dict(model.result) if model.result is not None else None,
        confidence_score=model.confidence_score,
        ai_provider=model.ai_provider,
        ai_model=model.ai_model,
        error_message=model.error_message,
        latency_ms=model.latency_ms,
    )


def apply_analysis_to_model(analysis: AICommunityAnalysis, model: CommunityAIAnalysisModel) -> None:
    model.id = analysis.id
    model.organization_id = analysis.organization_id
    model.analysis_type = analysis.analysis_type
    model.target_type = analysis.target_type
    model.target_id = analysis.target_id
    model.status = analysis.status
    model.result = dict(analysis.result) if analysis.result is not None else None
    model.confidence_score = analysis.confidence_score
    model.ai_provider = analysis.ai_provider
    model.ai_model = analysis.ai_model
    model.error_message = analysis.error_message
    model.latency_ms = analysis.latency_ms
