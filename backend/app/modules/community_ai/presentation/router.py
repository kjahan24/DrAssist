"""HTTP routes for the Community AI Features module.

Follows the pattern established in
`app.modules.community_moderation.presentation.router`. Every endpoint
depends on `CurrentUser`; `organization_id`/`requester_id` always come
from the authenticated principal, never a request body field, so a
caller can never request analysis "as" another tenant or user.

There is no `ensure_same_organization` call anywhere in this router,
matching `community_moderation`'s own precedent — every service already
enforces tenant isolation itself via `_authorization.py`'s explicit
`organization_id` comparison.

`summary`/`resources`/`misinformation`/`refresh` take no request body —
every field their Input DTOs need comes from the path and `CurrentUser`.
`similar` and the analyses list take `cursor`/`limit` (and, for the
list, `analysis_type`/`status`) as query parameters, matching
`community_moderation`'s own `list_reports` GET-with-query-params shape.
"""

from uuid import UUID

from fastapi import APIRouter, Query

from app.api.deps import CurrentUser
from app.modules.community_ai.application.dto import (
    AnalyzeMisinformationInput,
    FindSimilarDiscussionsInput,
    GenerateDiscussionSummaryInput,
    ListAIAnalysesInput,
    RecommendTrustedResourcesInput,
    RefreshAIAnalysisInput,
)
from app.modules.community_ai.domain.enums import (
    AIAnalysisStatus,
    AIAnalysisType,
    CommunityContentTargetType,
)
from app.modules.community_ai.presentation.dependencies import (
    AnalyzeMisinformationUseCase,
    FindSimilarDiscussionsUseCase,
    GenerateSummaryUseCase,
    GetAIAnalysisQS,
    ListAIAnalysesQS,
    RecommendTrustedResourcesUseCase,
    RefreshAIAnalysisUseCase,
)
from app.modules.community_ai.presentation.schemas import (
    AICommunityAnalysisFeedResponse,
    AICommunityAnalysisResponse,
    SimilarDiscussionFeedResponse,
    SimilarDiscussionResponse,
)

router = APIRouter()


@router.get("/health")
async def get_community_ai_health() -> dict[str, str]:
    return {"status": "ok", "module": "community_ai"}


# --- Discussion analysis ------------------------------------------------------------------


@router.post(
    "/discussions/{target_type}/{target_id}/summary", response_model=AICommunityAnalysisResponse
)
async def generate_discussion_summary(
    target_type: CommunityContentTargetType,
    target_id: UUID,
    use_case: GenerateSummaryUseCase,
    current_user: CurrentUser,
) -> AICommunityAnalysisResponse:
    output = await use_case.execute(
        GenerateDiscussionSummaryInput(
            organization_id=current_user.organization_id,
            requester_id=current_user.user_id,
            target_type=target_type,
            target_id=target_id,
        )
    )
    return AICommunityAnalysisResponse.model_validate(output)


@router.post(
    "/discussions/{target_type}/{target_id}/similar", response_model=SimilarDiscussionFeedResponse
)
async def find_similar_discussions(
    target_type: CommunityContentTargetType,
    target_id: UUID,
    use_case: FindSimilarDiscussionsUseCase,
    current_user: CurrentUser,
    cursor: str | None = None,
    limit: int = Query(default=10, ge=1, le=50),
) -> SimilarDiscussionFeedResponse:
    output = await use_case.execute(
        FindSimilarDiscussionsInput(
            organization_id=current_user.organization_id,
            requester_id=current_user.user_id,
            target_type=target_type,
            target_id=target_id,
            cursor=cursor,
            limit=limit,
        )
    )
    return SimilarDiscussionFeedResponse(
        analysis_id=output.analysis_id,
        items=[SimilarDiscussionResponse.model_validate(item) for item in output.items],
        next_cursor=output.next_cursor,
    )


@router.post(
    "/discussions/{target_type}/{target_id}/resources", response_model=AICommunityAnalysisResponse
)
async def recommend_trusted_resources(
    target_type: CommunityContentTargetType,
    target_id: UUID,
    use_case: RecommendTrustedResourcesUseCase,
    current_user: CurrentUser,
) -> AICommunityAnalysisResponse:
    output = await use_case.execute(
        RecommendTrustedResourcesInput(
            organization_id=current_user.organization_id,
            requester_id=current_user.user_id,
            target_type=target_type,
            target_id=target_id,
        )
    )
    return AICommunityAnalysisResponse.model_validate(output)


@router.post(
    "/discussions/{target_type}/{target_id}/misinformation",
    response_model=AICommunityAnalysisResponse,
)
async def analyze_misinformation(
    target_type: CommunityContentTargetType,
    target_id: UUID,
    use_case: AnalyzeMisinformationUseCase,
    current_user: CurrentUser,
) -> AICommunityAnalysisResponse:
    output = await use_case.execute(
        AnalyzeMisinformationInput(
            organization_id=current_user.organization_id,
            requester_id=current_user.user_id,
            target_type=target_type,
            target_id=target_id,
        )
    )
    return AICommunityAnalysisResponse.model_validate(output)


# --- Analysis status / refresh -------------------------------------------------------------


@router.get("/analyses/{analysis_id}", response_model=AICommunityAnalysisResponse)
async def get_ai_analysis(
    analysis_id: UUID, query_service: GetAIAnalysisQS, current_user: CurrentUser
) -> AICommunityAnalysisResponse:
    result = await query_service.get_analysis(
        analysis_id, organization_id=current_user.organization_id
    )
    return AICommunityAnalysisResponse.model_validate(result)


@router.get("/analyses", response_model=AICommunityAnalysisFeedResponse)
async def list_ai_analyses(
    query_service: ListAIAnalysesQS,
    current_user: CurrentUser,
    target_type: CommunityContentTargetType | None = None,
    target_id: UUID | None = None,
    analysis_type: AIAnalysisType | None = None,
    status_: AIAnalysisStatus | None = Query(default=None, alias="status"),
    cursor: str | None = None,
    limit: int = Query(default=20, ge=1, le=100),
) -> AICommunityAnalysisFeedResponse:
    result = await query_service.list_analyses(
        ListAIAnalysesInput(
            organization_id=current_user.organization_id,
            target_type=target_type,
            target_id=target_id,
            analysis_type=analysis_type,
            status=status_,
            cursor=cursor,
            limit=limit,
        )
    )
    return AICommunityAnalysisFeedResponse(
        items=[AICommunityAnalysisResponse.model_validate(a) for a in result.items],
        next_cursor=result.next_cursor,
    )


@router.post("/analyses/{analysis_id}/refresh", response_model=AICommunityAnalysisResponse)
async def refresh_ai_analysis(
    analysis_id: UUID, use_case: RefreshAIAnalysisUseCase, current_user: CurrentUser
) -> AICommunityAnalysisResponse:
    output = await use_case.execute(
        RefreshAIAnalysisInput(
            organization_id=current_user.organization_id,
            requester_id=current_user.user_id,
            analysis_id=analysis_id,
        )
    )
    return AICommunityAnalysisResponse.model_validate(output)
