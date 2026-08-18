"""`CastVoteService` — upvotes, downvotes, switches, or idempotently
no-ops, all through this one entry point, exactly matching this task's
own FEATURES list ("Upvote", "Downvote", "Vote switching") without
three separate service classes for what is, structurally, one
`(user_id, target_type, target_id)` row.

Cross-module reads only, never a private repository import: resolves
the target via `_target_resolution.resolve_engagement_target`, requires
it to exist, belong to the acting user's own organization ("Tenant
isolation"), and be `PUBLISHED` ("Users cannot vote on deleted/invalid
content").

Three outcomes for an existing vote on the same target, dispatched by
comparing `vote_type`:
- no existing vote: a new `Vote` row is created (this task's own
  "Prevent duplicate votes" — enforced doubly, here at the application
  layer and again by the database's own unique constraint on
  `(user_id, target_type, target_id)` as a concurrency safety net).
- an existing vote with the *same* direction: a pure no-op — re-casting
  an upvote you already made must not create a duplicate row or raise
  an error (idempotent, matching this task's own DOMAIN RULES framing of
  "duplicate" prevention as silent, not an error condition).
- an existing vote with a *different* direction: `Vote.switch()` flips
  it in place — "Vote switching."
"""

from app.modules.community_answers.public.interfaces import AnswerQueryPort
from app.modules.community_comments.public.interfaces import CommentQueryPort
from app.modules.community_engagement.application.dto import CastVoteInput, CastVoteOutput
from app.modules.community_engagement.application.services._target_resolution import (
    resolve_engagement_target,
)
from app.modules.community_engagement.domain.entities import Vote
from app.modules.community_engagement.domain.exceptions import (
    VoteTargetNotAcceptingVotesError,
    VoteTargetNotFoundError,
)
from app.modules.community_engagement.domain.repositories import VoteRepository
from app.modules.community_posts.public.interfaces import PostQueryPort
from app.modules.community_questions.public.interfaces import QuestionQueryPort
from app.shared.application.unit_of_work import UnitOfWork


class CastVoteService:
    def __init__(
        self,
        *,
        vote_repository: VoteRepository,
        post_query_port: PostQueryPort,
        question_query_port: QuestionQueryPort,
        answer_query_port: AnswerQueryPort,
        comment_query_port: CommentQueryPort,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._votes = vote_repository
        self._posts = post_query_port
        self._questions = question_query_port
        self._answers = answer_query_port
        self._comments = comment_query_port
        self._uow = unit_of_work

    async def execute(self, input_dto: CastVoteInput) -> CastVoteOutput:
        resolved = await resolve_engagement_target(
            input_dto.target_type,
            input_dto.target_id,
            post_query_port=self._posts,
            question_query_port=self._questions,
            answer_query_port=self._answers,
            comment_query_port=self._comments,
        )
        if resolved is None or resolved.organization_id != input_dto.organization_id:
            raise VoteTargetNotFoundError(input_dto.target_id)
        if not resolved.is_published:
            raise VoteTargetNotAcceptingVotesError(input_dto.target_id)

        existing = await self._votes.get_vote(
            input_dto.user_id, input_dto.target_type, input_dto.target_id
        )

        if existing is not None and existing.vote_type == input_dto.vote_type:
            return CastVoteOutput(
                vote_id=existing.id,
                target_type=existing.target_type,
                target_id=existing.target_id,
                vote_type=existing.vote_type,
            )

        if existing is not None:
            existing.switch(input_dto.vote_type)
            await self._votes.add(existing)
            self._uow.collect_events(existing.pull_events())
            await self._uow.commit()
            return CastVoteOutput(
                vote_id=existing.id,
                target_type=existing.target_type,
                target_id=existing.target_id,
                vote_type=existing.vote_type,
            )

        vote = Vote.create(
            user_id=input_dto.user_id,
            organization_id=input_dto.organization_id,
            target_type=input_dto.target_type,
            target_id=input_dto.target_id,
            vote_type=input_dto.vote_type,
        )
        await self._votes.add(vote)
        self._uow.collect_events(vote.pull_events())
        await self._uow.commit()
        return CastVoteOutput(
            vote_id=vote.id,
            target_type=vote.target_type,
            target_id=vote.target_id,
            vote_type=vote.vote_type,
        )
