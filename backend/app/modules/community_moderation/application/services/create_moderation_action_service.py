"""`CreateModerationActionService` — the generic entry point for any
content-shaped moderation action (`APPROVE`/`REMOVE`/`RESTRICT`/`LOCK`/
`RESTORE`). `ReviewContent`/`RemoveContent`/`RestoreContent`/
`LockContent` are convenience wrappers around this exact same
resolve-authorize-record shape for the four most common verbs; this
service is also the only way to record a `RESTRICT` action — this task's
own APPLICATION section names four convenience services (`ReviewContent`,
`RemoveContent`, `RestoreContent`, `LockContent`) but not a fifth
`RestrictContent`, even though FEATURES lists "Restrict content" — so
`RESTRICT` is reached through this generic service instead of an unlisted
sixth one.
"""

from app.modules.authentication.public.interfaces import UserQueryPort
from app.modules.community.public.interfaces import CommunityQueryPort
from app.modules.community_answers.public.interfaces import AnswerQueryPort
from app.modules.community_comments.public.interfaces import CommentQueryPort
from app.modules.community_moderation.application.dto import (
    CreateModerationActionInput,
    ModerationActionSummaryDTO,
)
from app.modules.community_moderation.application.services._content_actions import (
    get_current_content_status,
    resolve_and_authorize_content_target,
)
from app.modules.community_moderation.application.services._summary_mappers import (
    action_to_summary,
)
from app.modules.community_moderation.domain.entities import ModerationAction
from app.modules.community_moderation.domain.enums import (
    ContentModerationStatus,
    ModerationActionType,
)
from app.modules.community_moderation.domain.exceptions import UnsupportedModerationActionTypeError
from app.modules.community_moderation.domain.repositories import ModerationActionRepository
from app.modules.community_posts.public.interfaces import PostQueryPort
from app.modules.community_questions.public.interfaces import QuestionQueryPort
from app.shared.application.unit_of_work import UnitOfWork

_TARGET_STATE: dict[ModerationActionType, ContentModerationStatus] = {
    ModerationActionType.APPROVE: ContentModerationStatus.ACTIVE,
    ModerationActionType.REMOVE: ContentModerationStatus.REMOVED,
    ModerationActionType.RESTRICT: ContentModerationStatus.RESTRICTED,
    ModerationActionType.LOCK: ContentModerationStatus.LOCKED,
    ModerationActionType.RESTORE: ContentModerationStatus.ACTIVE,
}


class CreateModerationActionService:
    def __init__(
        self,
        *,
        action_repository: ModerationActionRepository,
        post_query_port: PostQueryPort,
        question_query_port: QuestionQueryPort,
        answer_query_port: AnswerQueryPort,
        comment_query_port: CommentQueryPort,
        community_query_port: CommunityQueryPort,
        user_query_port: UserQueryPort,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._actions = action_repository
        self._posts = post_query_port
        self._questions = question_query_port
        self._answers = answer_query_port
        self._comments = comment_query_port
        self._communities = community_query_port
        self._users = user_query_port
        self._uow = unit_of_work

    async def execute(self, input_dto: CreateModerationActionInput) -> ModerationActionSummaryDTO:
        if input_dto.action_type not in _TARGET_STATE:
            raise UnsupportedModerationActionTypeError(input_dto.action_type)

        await resolve_and_authorize_content_target(
            input_dto.target_type,
            input_dto.target_id,
            organization_id=input_dto.organization_id,
            actor_id=input_dto.actor_id,
            post_query_port=self._posts,
            question_query_port=self._questions,
            answer_query_port=self._answers,
            comment_query_port=self._comments,
            community_query_port=self._communities,
            user_query_port=self._users,
        )
        previous_state = await get_current_content_status(
            self._actions, input_dto.target_type, input_dto.target_id
        )
        new_state = _TARGET_STATE[input_dto.action_type]

        action = ModerationAction.record(
            organization_id=input_dto.organization_id,
            actor_id=input_dto.actor_id,
            action_type=input_dto.action_type,
            target_type=input_dto.target_type,
            target_id=input_dto.target_id,
            reason=input_dto.reason,
            report_id=input_dto.report_id,
            moderator_note=input_dto.moderator_note,
            previous_state=previous_state.value,
            new_state=new_state.value,
        )
        await self._actions.add(action)
        await self._uow.commit()
        return action_to_summary(action)
