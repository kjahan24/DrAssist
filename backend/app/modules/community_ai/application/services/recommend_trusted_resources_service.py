"""`RecommendTrustedResourcesService` — produces ranked
`TrustedResourceRecommendation`s drawn only from
`TrustedResourceCatalogPort`'s own known, curated catalog — see
`application/ports.py`'s own docstring for why this structurally
satisfies "Do NOT fabricate medical sources" rather than merely
instructing the model not to. Idempotency/failure handling mirrors
`generate_discussion_summary_service.py`'s own docstring exactly."""

from app.modules.community.public.interfaces import CommunityQueryPort
from app.modules.community_ai.application.dto import (
    AICommunityAnalysisSummaryDTO,
    RecommendTrustedResourcesInput,
)
from app.modules.community_ai.application.ports import (
    CommunityAIGeneratorPort,
    TrustedResourceCatalogPort,
)
from app.modules.community_ai.application.services._analysis_lifecycle import (
    get_or_start_analysis,
)
from app.modules.community_ai.application.services._authorization import (
    ensure_can_access_target,
    ensure_not_moderated,
)
from app.modules.community_ai.application.services._result_serialization import (
    resource_recommendations_to_dict,
)
from app.modules.community_ai.application.services._summary_mappers import analysis_to_summary
from app.modules.community_ai.application.services._target_resolution import (
    resolve_analysis_target,
)
from app.modules.community_ai.domain.enums import AIAnalysisType
from app.modules.community_ai.domain.exceptions import AnalysisTargetNotFoundError
from app.modules.community_ai.domain.repositories import AICommunityAnalysisRepository
from app.modules.community_answers.public.interfaces import AnswerQueryPort
from app.modules.community_comments.public.interfaces import CommentQueryPort
from app.modules.community_moderation.public.interfaces import ModerationQueryPort
from app.modules.community_posts.public.interfaces import PostQueryPort
from app.modules.community_questions.public.interfaces import QuestionQueryPort
from app.shared.application.unit_of_work import UnitOfWork


class RecommendTrustedResourcesService:
    def __init__(
        self,
        *,
        analysis_repository: AICommunityAnalysisRepository,
        generator: CommunityAIGeneratorPort,
        catalog: TrustedResourceCatalogPort,
        post_query_port: PostQueryPort,
        question_query_port: QuestionQueryPort,
        answer_query_port: AnswerQueryPort,
        comment_query_port: CommentQueryPort,
        community_query_port: CommunityQueryPort,
        moderation_query_port: ModerationQueryPort,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._analyses = analysis_repository
        self._generator = generator
        self._catalog = catalog
        self._posts = post_query_port
        self._questions = question_query_port
        self._answers = answer_query_port
        self._comments = comment_query_port
        self._communities = community_query_port
        self._moderation = moderation_query_port
        self._uow = unit_of_work

    async def execute(
        self, input_dto: RecommendTrustedResourcesInput
    ) -> AICommunityAnalysisSummaryDTO:
        resolved = await resolve_analysis_target(
            input_dto.target_type,
            input_dto.target_id,
            post_query_port=self._posts,
            question_query_port=self._questions,
            answer_query_port=self._answers,
            comment_query_port=self._comments,
        )
        if resolved is None or not resolved.is_published:
            raise AnalysisTargetNotFoundError(input_dto.target_id)
        await ensure_can_access_target(
            resolved,
            target_id=input_dto.target_id,
            requester_id=input_dto.requester_id,
            requester_organization_id=input_dto.organization_id,
            community_query_port=self._communities,
        )
        await ensure_not_moderated(
            input_dto.target_type, input_dto.target_id, moderation_query_port=self._moderation
        )

        analysis, is_cached = await get_or_start_analysis(
            repository=self._analyses,
            organization_id=input_dto.organization_id,
            analysis_type=AIAnalysisType.RESOURCE_RECOMMENDATION,
            target_type=input_dto.target_type,
            target_id=input_dto.target_id,
        )
        if is_cached:
            return analysis_to_summary(analysis)

        self._uow.collect_events(analysis.pull_events())
        await self._uow.commit()

        catalog_sources = await self._catalog.list_sources()

        try:
            recommendations, metadata = await self._generator.generate_resource_recommendations(
                title=resolved.title, text=resolved.text, catalog=catalog_sources
            )
        except Exception as exc:
            analysis.mark_failed(str(exc))
            await self._analyses.add(analysis)
            self._uow.collect_events(analysis.pull_events())
            await self._uow.commit()
            raise

        analysis.mark_completed(
            result=resource_recommendations_to_dict(recommendations),
            confidence_score=None,
            ai_provider=metadata.provider,
            ai_model=metadata.model,
            latency_ms=metadata.latency_ms,
        )
        await self._analyses.add(analysis)
        self._uow.collect_events(analysis.pull_events())
        await self._uow.commit()
        return analysis_to_summary(analysis)
