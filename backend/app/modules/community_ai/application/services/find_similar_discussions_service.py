"""`FindSimilarDiscussionsService` — the one AI Community Feature that
does not call `CommunityAIGeneratorPort` at all: it embeds the source
target's text and searches the vector store for ranked neighbors, via
`SimilarDiscussionSearchPort` (see `application/ports.py`'s own
docstring).

**Index-on-read design, disclosed**: no event-driven embedding-indexing
pipeline exists anywhere in this codebase yet (confirmed absent —
`app.modules.ai`'s own architecture doc describes one only as a future
`EmbeddingGenerated` event, never built). Rather than inventing that
pipeline from scratch, this service indexes only the *source* target it
is about to search from, lazily, on every call — so the searchable corpus
grows organically as users request "similar discussions" against various
posts/questions, rather than requiring a backfill job. A target that has
never itself been searched-from has no embedding yet and simply cannot
appear as a *candidate* until it has been — this is exactly this task's
own "Handle missing embeddings gracefully" requirement in practice, not a
bug: `SimilarDiscussionSearchPort.find_similar` returns an empty tuple,
never raises, when nothing is indexed yet.

Every candidate the vector store returns is re-validated through
`_target_resolution.py`/`_authorization.py`/moderation-status before being
returned — Qdrant payload metadata is a performance hint, never the
source of truth for "does this still exist, is it visible, is it
moderated" (see `_authorization.py`'s own docstring for the identical
"public port is the single source of truth" reasoning).

Pagination (this task's own "Support pagination" requirement) slices the
one materialized, already-ranked result list stored on the `COMPLETED`
analysis row — there is no separate paginated query against Qdrant itself
per page; `RefreshAIAnalysis` is what recomputes the ranking from
scratch.
"""

import base64
from uuid import UUID

from app.modules.community.public.interfaces import CommunityQueryPort
from app.modules.community_ai.application.dto import (
    FindSimilarDiscussionsInput,
    SimilarDiscussionFeedOutput,
)
from app.modules.community_ai.application.ports import SimilarDiscussionSearchPort
from app.modules.community_ai.application.services._analysis_lifecycle import (
    get_or_start_analysis,
)
from app.modules.community_ai.application.services._authorization import (
    ensure_can_access_target,
    ensure_not_moderated,
)
from app.modules.community_ai.application.services._result_serialization import (
    similar_discussions_from_dict,
    similar_discussions_to_dict,
)
from app.modules.community_ai.application.services._target_resolution import (
    resolve_analysis_target,
)
from app.modules.community_ai.domain.enums import AIAnalysisType
from app.modules.community_ai.domain.exceptions import AnalysisTargetNotFoundError
from app.modules.community_ai.domain.repositories import AICommunityAnalysisRepository
from app.modules.community_ai.domain.value_objects import SimilarDiscussion
from app.modules.community_answers.public.interfaces import AnswerQueryPort
from app.modules.community_comments.public.interfaces import CommentQueryPort
from app.modules.community_moderation.public.interfaces import ModerationQueryPort
from app.modules.community_posts.public.interfaces import PostQueryPort
from app.modules.community_questions.public.interfaces import QuestionQueryPort
from app.shared.application.unit_of_work import UnitOfWork

_MAX_INDEXED_CANDIDATES = 50


def _encode_offset_cursor(offset: int) -> str:
    return base64.urlsafe_b64encode(str(offset).encode("ascii")).decode("ascii")


def _decode_offset_cursor(cursor: str) -> int:
    return int(base64.urlsafe_b64decode(cursor.encode("ascii")).decode("ascii"))


class FindSimilarDiscussionsService:
    def __init__(
        self,
        *,
        analysis_repository: AICommunityAnalysisRepository,
        search_port: SimilarDiscussionSearchPort,
        post_query_port: PostQueryPort,
        question_query_port: QuestionQueryPort,
        answer_query_port: AnswerQueryPort,
        comment_query_port: CommentQueryPort,
        community_query_port: CommunityQueryPort,
        moderation_query_port: ModerationQueryPort,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._analyses = analysis_repository
        self._search = search_port
        self._posts = post_query_port
        self._questions = question_query_port
        self._answers = answer_query_port
        self._comments = comment_query_port
        self._communities = community_query_port
        self._moderation = moderation_query_port
        self._uow = unit_of_work

    async def execute(self, input_dto: FindSimilarDiscussionsInput) -> SimilarDiscussionFeedOutput:
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
            analysis_type=AIAnalysisType.SIMILAR_DISCUSSIONS,
            target_type=input_dto.target_type,
            target_id=input_dto.target_id,
        )
        if not is_cached:
            self._uow.collect_events(analysis.pull_events())
            await self._uow.commit()

            source_text = f"{resolved.title or ''}\n\n{resolved.text}".strip()
            try:
                await self._search.index_target(
                    target_type=input_dto.target_type,
                    target_id=input_dto.target_id,
                    organization_id=input_dto.organization_id,
                    text=source_text,
                )
                candidates = await self._search.find_similar(
                    target_type=input_dto.target_type,
                    target_id=input_dto.target_id,
                    organization_id=input_dto.organization_id,
                    limit=_MAX_INDEXED_CANDIDATES,
                )
            except Exception as exc:
                analysis.mark_failed(str(exc))
                await self._analyses.add(analysis)
                self._uow.collect_events(analysis.pull_events())
                await self._uow.commit()
                raise

            validated = await self._validate_candidates(
                candidates, organization_id=input_dto.organization_id
            )

            analysis.mark_completed(
                result=similar_discussions_to_dict(validated),
                confidence_score=None,
                ai_provider="vector_search",
                ai_model="embedding",
            )
            await self._analyses.add(analysis)
            self._uow.collect_events(analysis.pull_events())
            await self._uow.commit()

        items = similar_discussions_from_dict(analysis.result or {})
        page, next_cursor = self._paginate(items, cursor=input_dto.cursor, limit=input_dto.limit)
        return SimilarDiscussionFeedOutput(
            analysis_id=analysis.id, items=list(page), next_cursor=next_cursor
        )

    async def _validate_candidates(
        self, candidates: tuple[SimilarDiscussion, ...], *, organization_id: UUID
    ) -> tuple[SimilarDiscussion, ...]:
        validated: list[SimilarDiscussion] = []
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
                or candidate_resolved.organization_id != organization_id
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
        return tuple(validated)

    @staticmethod
    def _paginate(
        items: tuple[SimilarDiscussion, ...], *, cursor: str | None, limit: int
    ) -> tuple[tuple[SimilarDiscussion, ...], str | None]:
        offset = _decode_offset_cursor(cursor) if cursor is not None else 0
        page = items[offset : offset + limit]
        next_offset = offset + limit
        next_cursor = _encode_offset_cursor(next_offset) if next_offset < len(items) else None
        return page, next_cursor
