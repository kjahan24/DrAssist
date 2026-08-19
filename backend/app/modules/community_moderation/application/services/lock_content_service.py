"""`LockContentService` — a moderator marks content read-only/no-further-
engagement (`ModerationActionType.LOCK`), regardless of whether the
underlying content module itself has its own `is_locked` concept (only
`community_posts` does today — see `entities.py`'s own module docstring
for why this action is recorded here rather than requiring one everywhere)."""

from app.modules.authentication.public.interfaces import UserQueryPort
from app.modules.community.public.interfaces import CommunityQueryPort
from app.modules.community_answers.public.interfaces import AnswerQueryPort
from app.modules.community_comments.public.interfaces import CommentQueryPort
from app.modules.community_moderation.application.dto import (
    ContentModerationInput,
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
from app.modules.community_moderation.domain.repositories import ModerationActionRepository
from app.modules.community_posts.public.interfaces import PostQueryPort
from app.modules.community_questions.public.interfaces import QuestionQueryPort
from app.shared.application.unit_of_work import UnitOfWork


class LockContentService:
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

    async def execute(self, input_dto: ContentModerationInput) -> ModerationActionSummaryDTO:
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

        action = ModerationAction.record(
            organization_id=input_dto.organization_id,
            actor_id=input_dto.actor_id,
            action_type=ModerationActionType.LOCK,
            target_type=input_dto.target_type,
            target_id=input_dto.target_id,
            reason=input_dto.reason,
            report_id=input_dto.report_id,
            moderator_note=input_dto.moderator_note,
            previous_state=previous_state.value,
            new_state=ContentModerationStatus.LOCKED.value,
        )
        await self._actions.add(action)
        await self._uow.commit()
        return action_to_summary(action)
