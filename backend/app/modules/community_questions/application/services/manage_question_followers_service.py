"""`ManageQuestionFollowersService` — follow/unfollow/list a question's
own followers, backing this task's own "Follower Count" FEATURES bullet
and the `CommunityQuestionFollower` entity this task's own DOMAIN section
names. Not named in this task's own APPLICATION list — the same "add
what's genuinely required" precedent
`app.modules.community_posts.application.services.manage_post_topics_service
.ManagePostTopicsService` establishes for itself; unlike that precedent,
this service is entirely new (no `community_posts` analog exists), since
Posts has no follower concept.

Authorization: `follow`/`unfollow` reuse `_authorization.ensure_can_view`
rather than `ensure_can_author_action`/`ensure_is_moderator` — following
is a lightweight engagement action available to anyone who can see the
question (the same bar `GetQuestionService.get_by_id` already enforces
for reading it), not an authoring or moderation action. `list_followers`
performs no authorization check, matching every other `list_*` method in
this module's sibling `Manage*Service`s.

`follow`/`unfollow` touch two aggregates in one transaction: the new (or
removed) `CommunityQuestionFollower` row, and `CommunityQuestion.follower
_count` on the parent aggregate — see `CommunityQuestion
.increment_follower_count`/`.decrement_follower_count`'s own docstrings
for why only one of the two calls records a domain event.
"""

from uuid import UUID

from app.modules.community.public.interfaces import CommunityQueryPort
from app.modules.community_questions.application.dto import (
    FollowQuestionInput,
    QuestionFollowerSummaryDTO,
    UnfollowQuestionInput,
)
from app.modules.community_questions.application.services._authorization import ensure_can_view
from app.modules.community_questions.application.services._summary_mappers import (
    question_follower_to_summary,
)
from app.modules.community_questions.domain.entities import CommunityQuestionFollower
from app.modules.community_questions.domain.exceptions import (
    DuplicateQuestionFollowerError,
    QuestionFollowerNotFoundError,
    QuestionNotFoundError,
)
from app.modules.community_questions.domain.repositories import (
    CommunityQuestionFollowerRepository,
    CommunityQuestionRepository,
)
from app.modules.community_questions.domain.value_objects import QuestionId
from app.shared.application.unit_of_work import UnitOfWork


class ManageQuestionFollowersService:
    def __init__(
        self,
        *,
        question_follower_repository: CommunityQuestionFollowerRepository,
        question_repository: CommunityQuestionRepository,
        community_query_port: CommunityQueryPort,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._followers = question_follower_repository
        self._questions = question_repository
        self._communities = community_query_port
        self._uow = unit_of_work

    async def follow(self, input_dto: FollowQuestionInput) -> QuestionFollowerSummaryDTO:
        question = await self._questions.get_by_id(input_dto.question_id)
        if question is None:
            raise QuestionNotFoundError(input_dto.question_id)

        member = await self._communities.get_membership(
            question.community_id, input_dto.acting_user_id
        )
        ensure_can_view(question, member, user_id=input_dto.acting_user_id)

        if await self._followers.is_following(input_dto.question_id, input_dto.acting_user_id):
            raise DuplicateQuestionFollowerError(input_dto.question_id, input_dto.acting_user_id)

        follower = CommunityQuestionFollower.create(
            question_id=QuestionId(input_dto.question_id), user_id=input_dto.acting_user_id
        )
        question.increment_follower_count()

        await self._followers.add(follower)
        await self._questions.add(question)
        self._uow.collect_events(follower.pull_events())
        await self._uow.commit()

        return question_follower_to_summary(follower)

    async def list_followers(self, question_id: UUID) -> list[QuestionFollowerSummaryDTO]:
        followers = await self._followers.list_by_question(question_id)
        return [question_follower_to_summary(f) for f in followers]

    async def unfollow(self, input_dto: UnfollowQuestionInput) -> None:
        question = await self._questions.get_by_id(input_dto.question_id)
        if question is None:
            raise QuestionNotFoundError(input_dto.question_id)

        member = await self._communities.get_membership(
            question.community_id, input_dto.acting_user_id
        )
        ensure_can_view(question, member, user_id=input_dto.acting_user_id)

        follower = await self._followers.get_by_question_and_user(
            input_dto.question_id, input_dto.acting_user_id
        )
        if follower is None:
            raise QuestionFollowerNotFoundError(input_dto.question_id, input_dto.acting_user_id)

        await self._followers.remove(follower.id)
        question.decrement_follower_count(user_id=input_dto.acting_user_id)

        await self._questions.add(question)
        self._uow.collect_events(question.pull_events())
        await self._uow.commit()
