"""Shared get-or-start-analysis helper for every AI-generating service
(`GenerateDiscussionSummaryService`/`RecommendTrustedResourcesService`/
`AnalyzeMisinformationService`/`FindSimilarDiscussionsService`) — factored
out once so all four share one idempotency implementation, mirroring
`app.modules.community_moderation.application.services._content_actions
.resolve_and_authorize_content_target`'s identical role.

A fresh `COMPLETED` row for the exact same `(target_type, target_id,
analysis_type)` is returned as-is, with no AI call made — this is what
"Avoid unnecessary repeated AI calls" (this task's own CACHING/PERFORMANCE
section) is built on: the persisted row itself is the cache, since no
Redis-backed caching layer exists anywhere in this codebase for AI
results to reuse (confirmed absent — see `application/ports.py`'s own
docstring). A `PENDING`/`FAILED` row (or no row at all) is transitioned to
`PROCESSING` and handed back for the caller to actually run generation
against and then persist via `mark_completed()`/`mark_failed()`.
"""

from uuid import UUID

from app.modules.community_ai.domain.entities import AICommunityAnalysis
from app.modules.community_ai.domain.enums import (
    AIAnalysisStatus,
    AIAnalysisType,
    CommunityContentTargetType,
)
from app.modules.community_ai.domain.repositories import AICommunityAnalysisRepository


async def get_or_start_analysis(
    *,
    repository: AICommunityAnalysisRepository,
    organization_id: UUID,
    analysis_type: AIAnalysisType,
    target_type: CommunityContentTargetType,
    target_id: UUID,
) -> tuple[AICommunityAnalysis, bool]:
    """Returns `(analysis, is_cached_result)`. When `is_cached_result` is
    `True`, `analysis` is an already-`COMPLETED` row the caller should
    return unchanged, with no AI call. When `False`, `analysis` has just
    been transitioned to `PROCESSING` (and staged via `repository.add`,
    left for the caller to `unit_of_work.commit()` alongside its own
    collected events) and is ready for the caller to run generation
    against."""
    existing = await repository.get_by_target(target_type, target_id, analysis_type)
    if existing is not None and existing.status is AIAnalysisStatus.COMPLETED:
        return existing, True

    analysis = (
        existing
        if existing is not None
        else AICommunityAnalysis.request(
            organization_id=organization_id,
            analysis_type=analysis_type,
            target_type=target_type,
            target_id=target_id,
        )
    )
    analysis.mark_processing()
    await repository.add(analysis)
    return analysis, False
