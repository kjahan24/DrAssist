"""`SaveContentService` — "Save/unsave Post"/"Save/unsave Question"/
"Save/unsave Answer" (this task's own FEATURES list — no "Save/unsave
Comment"). `EngagementTargetType.COMMENT` is rejected up front
(`UnsupportedSaveTargetTypeError`), before any cross-module lookup, since
it is a pure input-shape check that needs no I/O — `Vote`/`SavedContent`
share one target-type vocabulary (`EngagementTargetType`) rather than
two nearly-identical enums; see that enum's own docstring.

Otherwise mirrors `CastVoteService` exactly: resolves the target via
`_target_resolution.resolve_engagement_target`, requires it to exist,
belong to the acting user's own organization, and be `PUBLISHED`: then
idempotently no-ops if already saved (this task's own "Follow/save
operations must be idempotent" DOMAIN rule) or creates a new
`SavedContent` row otherwise ("Prevent duplicate ... saves" — enforced
doubly, here and by the database's own unique constraint on
`(user_id, target_type, target_id)`).
"""

from app.modules.community_answers.public.interfaces import AnswerQueryPort
from app.modules.community_comments.public.interfaces import CommentQueryPort
from app.modules.community_engagement.application.dto import SaveContentInput, SaveContentOutput
from app.modules.community_engagement.application.services._target_resolution import (
    resolve_engagement_target,
)
from app.modules.community_engagement.domain.entities import SavedContent
from app.modules.community_engagement.domain.enums import EngagementTargetType
from app.modules.community_engagement.domain.exceptions import (
    SaveTargetNotAcceptingSavesError,
    SaveTargetNotFoundError,
    UnsupportedSaveTargetTypeError,
)
from app.modules.community_engagement.domain.repositories import SavedContentRepository
from app.modules.community_posts.public.interfaces import PostQueryPort
from app.modules.community_questions.public.interfaces import QuestionQueryPort
from app.shared.application.unit_of_work import UnitOfWork


class SaveContentService:
    def __init__(
        self,
        *,
        saved_content_repository: SavedContentRepository,
        post_query_port: PostQueryPort,
        question_query_port: QuestionQueryPort,
        answer_query_port: AnswerQueryPort,
        comment_query_port: CommentQueryPort,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._saved = saved_content_repository
        self._posts = post_query_port
        self._questions = question_query_port
        self._answers = answer_query_port
        self._comments = comment_query_port
        self._uow = unit_of_work

    async def execute(self, input_dto: SaveContentInput) -> SaveContentOutput:
        if input_dto.target_type is EngagementTargetType.COMMENT:
            raise UnsupportedSaveTargetTypeError(input_dto.target_type)

        resolved = await resolve_engagement_target(
            input_dto.target_type,
            input_dto.target_id,
            post_query_port=self._posts,
            question_query_port=self._questions,
            answer_query_port=self._answers,
            comment_query_port=self._comments,
        )
        if resolved is None or resolved.organization_id != input_dto.organization_id:
            raise SaveTargetNotFoundError(input_dto.target_id)
        if not resolved.is_published:
            raise SaveTargetNotAcceptingSavesError(input_dto.target_id)

        existing = await self._saved.get_saved(
            input_dto.user_id, input_dto.target_type, input_dto.target_id
        )
        if existing is not None:
            return SaveContentOutput(
                saved_content_id=existing.id,
                target_type=existing.target_type,
                target_id=existing.target_id,
            )

        saved = SavedContent.create(
            user_id=input_dto.user_id,
            organization_id=input_dto.organization_id,
            target_type=input_dto.target_type,
            target_id=input_dto.target_id,
        )
        await self._saved.add(saved)
        self._uow.collect_events(saved.pull_events())
        await self._uow.commit()
        return SaveContentOutput(
            saved_content_id=saved.id, target_type=saved.target_type, target_id=saved.target_id
        )
