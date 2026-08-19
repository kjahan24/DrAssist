"""`AnalyzeMisinformationService` — produces a `MisinformationAssessment`
for a post/question/answer/thread. Idempotency/failure handling mirrors
`generate_discussion_summary_service.py`'s own docstring exactly.

**Moderation integration, and its deliberate limit**: a `HIGH`/`CRITICAL`
result additionally records a `HighRiskMisinformationDetected` event and
sets `recommended_for_moderation_review=True` on the stored assessment —
this is the entirety of "route into the existing moderation workflow."
This service makes **no write call into `community_moderation` at all**
(it has no public command port to call — see
`app.modules.community_moderation.public.interfaces.ModerationQueryPort`,
read-only, three methods, by that module's own Phase 5.9 design). "Never
automatically remove content solely because AI flagged it" and "moderation
remains human-controlled" (this task's own MODERATION INTEGRATION section)
are satisfied structurally, not just by omission: flagged analyses are
discoverable via `ListAIAnalysesService` (filterable by `analysis_type`
and, once completed, a caller can filter for `HIGH`/`CRITICAL` results
client-side), and a human moderator takes any actual action — removal,
restriction, a formal report — through `community_moderation`'s own,
separate, already-built API, exactly as they would for a human-filed
report. Programmatically filing a `CommunityReport`/`ModerationAction` on
the AI's own behalf would require inventing an "AI actor" identity
`CommunityReport.reporter_id`/`ModerationAction.actor_id` (both
non-nullable `users.id` foreign keys) has no concept of today — out of
scope for this task, and safer left that way.
"""

from app.modules.community.public.interfaces import CommunityQueryPort
from app.modules.community_ai.application.dto import (
    AICommunityAnalysisSummaryDTO,
    AnalyzeMisinformationInput,
)
from app.modules.community_ai.application.ports import CommunityAIGeneratorPort
from app.modules.community_ai.application.services._analysis_lifecycle import (
    get_or_start_analysis,
)
from app.modules.community_ai.application.services._authorization import (
    ensure_can_access_target,
    ensure_not_moderated,
)
from app.modules.community_ai.application.services._result_serialization import (
    misinformation_assessment_to_dict,
)
from app.modules.community_ai.application.services._summary_mappers import analysis_to_summary
from app.modules.community_ai.application.services._target_resolution import (
    resolve_analysis_target,
)
from app.modules.community_ai.domain.enums import AIAnalysisType, MisinformationRiskLevel
from app.modules.community_ai.domain.events import HighRiskMisinformationDetected
from app.modules.community_ai.domain.exceptions import AnalysisTargetNotFoundError
from app.modules.community_ai.domain.repositories import AICommunityAnalysisRepository
from app.modules.community_answers.public.interfaces import AnswerQueryPort
from app.modules.community_comments.public.interfaces import CommentQueryPort
from app.modules.community_moderation.public.interfaces import ModerationQueryPort
from app.modules.community_posts.public.interfaces import PostQueryPort
from app.modules.community_questions.public.interfaces import QuestionQueryPort
from app.shared.application.unit_of_work import UnitOfWork

_ESCALATED_RISK_LEVELS = frozenset({MisinformationRiskLevel.HIGH, MisinformationRiskLevel.CRITICAL})


class AnalyzeMisinformationService:
    def __init__(
        self,
        *,
        analysis_repository: AICommunityAnalysisRepository,
        generator: CommunityAIGeneratorPort,
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
        self._posts = post_query_port
        self._questions = question_query_port
        self._answers = answer_query_port
        self._comments = comment_query_port
        self._communities = community_query_port
        self._moderation = moderation_query_port
        self._uow = unit_of_work

    async def execute(self, input_dto: AnalyzeMisinformationInput) -> AICommunityAnalysisSummaryDTO:
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
            analysis_type=AIAnalysisType.MISINFORMATION,
            target_type=input_dto.target_type,
            target_id=input_dto.target_id,
        )
        if is_cached:
            return analysis_to_summary(analysis)

        self._uow.collect_events(analysis.pull_events())
        await self._uow.commit()

        try:
            assessment, metadata = await self._generator.generate_misinformation_assessment(
                title=resolved.title, text=resolved.text
            )
        except Exception as exc:
            analysis.mark_failed(str(exc))
            await self._analyses.add(analysis)
            self._uow.collect_events(analysis.pull_events())
            await self._uow.commit()
            raise

        analysis.mark_completed(
            result=misinformation_assessment_to_dict(assessment),
            confidence_score=assessment.confidence_score,
            ai_provider=metadata.provider,
            ai_model=metadata.model,
            latency_ms=metadata.latency_ms,
        )
        await self._analyses.add(analysis)
        events = analysis.pull_events()
        if assessment.risk_level in _ESCALATED_RISK_LEVELS:
            events.append(
                HighRiskMisinformationDetected(
                    analysis_id=analysis.id,
                    target_type=analysis.target_type,
                    target_id=analysis.target_id,
                    risk_level=assessment.risk_level,
                )
            )
        self._uow.collect_events(events)
        await self._uow.commit()
        return analysis_to_summary(analysis)
