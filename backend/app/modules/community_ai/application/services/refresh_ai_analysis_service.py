"""`RefreshAIAnalysisService` — force-reruns an existing analysis
regardless of its current status, unlike every `Generate*`/`Find*`
service's own idempotent "return the `COMPLETED` row unchanged" default
path (see `_analysis_lifecycle.py`'s own docstring). `AICommunityAnalysis
.mark_processing()` is explicitly allowed from `COMPLETED`/`FAILED` for
exactly this reason — the same row is mutated in place, never a second
row inserted for the same target.

Re-resolves and re-authorizes the target before refreshing (not just
trusting the analysis row's own stored `organization_id`/`target_type`/
`target_id`) — the target's visibility/moderation status may have changed
since the analysis was first requested, and "AI analysis must never
become a side-channel" applies just as much to a refresh as to the
original request.

Dispatches on `analysis.analysis_type` to the matching generation
strategy — this is the one service in the module that legitimately needs
all four ports (`CommunityAIGeneratorPort`, `SimilarDiscussionSearchPort`,
`TrustedResourceCatalogPort`) injected together, since "refresh whichever
kind of analysis this row already is" is inherently generic across all
four `AIAnalysisType` members.
"""

from app.modules.community.public.interfaces import CommunityQueryPort
from app.modules.community_ai.application.dto import (
    AICommunityAnalysisSummaryDTO,
    RefreshAIAnalysisInput,
)
from app.modules.community_ai.application.ports import (
    CommunityAIGeneratorPort,
    SimilarDiscussionSearchPort,
    TrustedResourceCatalogPort,
)
from app.modules.community_ai.application.services._authorization import (
    ensure_can_access_target,
    ensure_not_moderated,
)
from app.modules.community_ai.application.services._result_serialization import (
    misinformation_assessment_to_dict,
    resource_recommendations_to_dict,
    similar_discussions_to_dict,
    summary_to_dict,
)
from app.modules.community_ai.application.services._summary_mappers import analysis_to_summary
from app.modules.community_ai.application.services._target_resolution import (
    ResolvedAnalysisTarget,
    resolve_analysis_target,
)
from app.modules.community_ai.domain.entities import AICommunityAnalysis
from app.modules.community_ai.domain.enums import AIAnalysisType, MisinformationRiskLevel
from app.modules.community_ai.domain.events import HighRiskMisinformationDetected
from app.modules.community_ai.domain.exceptions import (
    AnalysisNotFoundError,
    AnalysisTargetNotFoundError,
)
from app.modules.community_ai.domain.repositories import AICommunityAnalysisRepository
from app.modules.community_answers.public.interfaces import AnswerQueryPort
from app.modules.community_comments.public.interfaces import CommentQueryPort
from app.modules.community_moderation.public.interfaces import ModerationQueryPort
from app.modules.community_posts.public.interfaces import PostQueryPort
from app.modules.community_questions.public.interfaces import QuestionQueryPort
from app.shared.application.unit_of_work import UnitOfWork
from app.shared.domain.domain_event import DomainEvent

_ESCALATED_RISK_LEVELS = frozenset({MisinformationRiskLevel.HIGH, MisinformationRiskLevel.CRITICAL})
_MAX_INDEXED_CANDIDATES = 50


class RefreshAIAnalysisService:
    def __init__(
        self,
        *,
        analysis_repository: AICommunityAnalysisRepository,
        generator: CommunityAIGeneratorPort,
        search_port: SimilarDiscussionSearchPort,
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
        self._search = search_port
        self._catalog = catalog
        self._posts = post_query_port
        self._questions = question_query_port
        self._answers = answer_query_port
        self._comments = comment_query_port
        self._communities = community_query_port
        self._moderation = moderation_query_port
        self._uow = unit_of_work

    async def execute(self, input_dto: RefreshAIAnalysisInput) -> AICommunityAnalysisSummaryDTO:
        analysis = await self._analyses.get_by_id(input_dto.analysis_id)
        if analysis is None or analysis.organization_id != input_dto.organization_id:
            raise AnalysisNotFoundError(input_dto.analysis_id)

        resolved = await resolve_analysis_target(
            analysis.target_type,
            analysis.target_id,
            post_query_port=self._posts,
            question_query_port=self._questions,
            answer_query_port=self._answers,
            comment_query_port=self._comments,
        )
        if resolved is None or not resolved.is_published:
            raise AnalysisTargetNotFoundError(analysis.target_id)
        await ensure_can_access_target(
            resolved,
            target_id=analysis.target_id,
            requester_id=input_dto.requester_id,
            requester_organization_id=input_dto.organization_id,
            community_query_port=self._communities,
        )
        await ensure_not_moderated(
            analysis.target_type, analysis.target_id, moderation_query_port=self._moderation
        )

        analysis.mark_processing()
        await self._analyses.add(analysis)
        self._uow.collect_events(analysis.pull_events())
        await self._uow.commit()

        try:
            extra_events = await self._regenerate(analysis, resolved)
        except Exception as exc:
            analysis.mark_failed(str(exc))
            await self._analyses.add(analysis)
            self._uow.collect_events(analysis.pull_events())
            await self._uow.commit()
            raise

        await self._analyses.add(analysis)
        events = analysis.pull_events()
        events.extend(extra_events)
        self._uow.collect_events(events)
        await self._uow.commit()
        return analysis_to_summary(analysis)

    async def _regenerate(
        self, analysis: AICommunityAnalysis, resolved: ResolvedAnalysisTarget
    ) -> list[DomainEvent]:
        if analysis.analysis_type is AIAnalysisType.SUMMARY:
            summary, metadata = await self._generator.generate_summary(
                title=resolved.title, text=resolved.text
            )
            analysis.mark_completed(
                result=summary_to_dict(summary),
                confidence_score=None,
                ai_provider=metadata.provider,
                ai_model=metadata.model,
                latency_ms=metadata.latency_ms,
            )
            return []

        if analysis.analysis_type is AIAnalysisType.MISINFORMATION:
            assessment, metadata = await self._generator.generate_misinformation_assessment(
                title=resolved.title, text=resolved.text
            )
            analysis.mark_completed(
                result=misinformation_assessment_to_dict(assessment),
                confidence_score=assessment.confidence_score,
                ai_provider=metadata.provider,
                ai_model=metadata.model,
                latency_ms=metadata.latency_ms,
            )
            if assessment.risk_level in _ESCALATED_RISK_LEVELS:
                return [
                    HighRiskMisinformationDetected(
                        analysis_id=analysis.id,
                        target_type=analysis.target_type,
                        target_id=analysis.target_id,
                        risk_level=assessment.risk_level,
                    )
                ]
            return []

        if analysis.analysis_type is AIAnalysisType.RESOURCE_RECOMMENDATION:
            catalog_sources = await self._catalog.list_sources()
            recommendations, metadata = await self._generator.generate_resource_recommendations(
                title=resolved.title, text=resolved.text, catalog=catalog_sources
            )
            analysis.mark_completed(
                result=resource_recommendations_to_dict(recommendations),
                confidence_score=None,
                ai_provider=metadata.provider,
                ai_model=metadata.model,
                latency_ms=metadata.latency_ms,
            )
            return []

        # AIAnalysisType.SIMILAR_DISCUSSIONS
        source_text = f"{resolved.title or ''}\n\n{resolved.text}".strip()
        await self._search.index_target(
            target_type=analysis.target_type,
            target_id=analysis.target_id,
            organization_id=analysis.organization_id,
            text=source_text,
        )
        candidates = await self._search.find_similar(
            target_type=analysis.target_type,
            target_id=analysis.target_id,
            organization_id=analysis.organization_id,
            limit=_MAX_INDEXED_CANDIDATES,
        )
        validated = []
        for candidate in candidates:
            candidate_resolved = await resolve_analysis_target(
                candidate.target_type,
                candidate.target_id,
                post_query_port=self._posts,
                question_query_port=self._questions,
                answer_query_port=self._answers,
                comment_query_port=self._comments,
            )
            if (
                candidate_resolved is None
                or candidate_resolved.organization_id != analysis.organization_id
                or not candidate_resolved.is_published
            ):
                continue
            try:
                await ensure_not_moderated(
                    candidate.target_type,
                    candidate.target_id,
                    moderation_query_port=self._moderation,
                )
            except AnalysisTargetNotFoundError:
                continue
            validated.append(candidate)
        analysis.mark_completed(
            result=similar_discussions_to_dict(tuple(validated)),
            confidence_score=None,
            ai_provider="vector_search",
            ai_model="embedding",
        )
        return []
