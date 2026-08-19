"""Unit tests for `LockContentService`, using in-memory fakes."""

from uuid import uuid4

import pytest

from app.modules.community.public.dto import CommunityRole
from app.modules.community_moderation.application.dto import ContentModerationInput
from app.modules.community_moderation.application.services.lock_content_service import (
    LockContentService,
)
from app.modules.community_moderation.domain.enums import (
    ContentModerationStatus,
    ModerationActionType,
    ModerationTargetType,
)
from app.modules.community_moderation.domain.exceptions import (
    ContentActionTargetNotFoundError,
    InsufficientModeratorRoleError,
)
from tests.unit.modules.community_moderation.application.fakes import (
    FakeAnswerQueryPort,
    FakeCommentQueryPort,
    FakeCommunityQueryPort,
    FakeModerationActionRepository,
    FakePostQueryPort,
    FakeQuestionQueryPort,
    FakeUnitOfWork,
    FakeUserQueryPort,
    make_comment_summary,
    make_member_summary,
)


def _seeded() -> (
    tuple[
        LockContentService,
        FakeModerationActionRepository,
        FakeCommentQueryPort,
        FakeCommunityQueryPort,
        FakeUnitOfWork,
    ]
):
    actions = FakeModerationActionRepository()
    comments = FakeCommentQueryPort()
    communities = FakeCommunityQueryPort()
    uow = FakeUnitOfWork()
    service = LockContentService(
        action_repository=actions,
        post_query_port=FakePostQueryPort(),
        question_query_port=FakeQuestionQueryPort(),
        answer_query_port=FakeAnswerQueryPort(),
        comment_query_port=comments,
        community_query_port=communities,
        user_query_port=FakeUserQueryPort(),
        unit_of_work=uow,
    )
    return service, actions, comments, communities, uow


class TestLockContent:
    async def test_records_a_lock_action_on_a_comment(self) -> None:
        service, _, comments, communities, _ = _seeded()
        org_id, community_id, comment_id, moderator_id = uuid4(), uuid4(), uuid4(), uuid4()
        comments.add_comment(
            make_comment_summary(
                comment_id=comment_id, community_id=community_id, organization_id=org_id
            )
        )
        communities.add_membership(
            make_member_summary(
                community_id=community_id, user_id=moderator_id, role=CommunityRole.MODERATOR
            )
        )
        output = await service.execute(
            ContentModerationInput(
                organization_id=org_id,
                actor_id=moderator_id,
                target_type=ModerationTargetType.COMMENT,
                target_id=comment_id,
                reason="Heated thread, locking further replies.",
            )
        )
        assert output.action_type is ModerationActionType.LOCK
        assert output.new_state == ContentModerationStatus.LOCKED.value

    async def test_unknown_target_raises(self) -> None:
        service, _, _, communities, _ = _seeded()
        org_id, community_id, moderator_id = uuid4(), uuid4(), uuid4()
        communities.add_membership(
            make_member_summary(
                community_id=community_id, user_id=moderator_id, role=CommunityRole.MODERATOR
            )
        )
        with pytest.raises(ContentActionTargetNotFoundError):
            await service.execute(
                ContentModerationInput(
                    organization_id=org_id,
                    actor_id=moderator_id,
                    target_type=ModerationTargetType.COMMENT,
                    target_id=uuid4(),
                    reason="Doesn't exist.",
                )
            )

    async def test_member_without_moderator_rank_raises(self) -> None:
        service, _, comments, communities, _ = _seeded()
        org_id, community_id, comment_id, member_id = uuid4(), uuid4(), uuid4(), uuid4()
        comments.add_comment(
            make_comment_summary(
                comment_id=comment_id, community_id=community_id, organization_id=org_id
            )
        )
        communities.add_membership(
            make_member_summary(
                community_id=community_id, user_id=member_id, role=CommunityRole.MEMBER
            )
        )
        with pytest.raises(InsufficientModeratorRoleError):
            await service.execute(
                ContentModerationInput(
                    organization_id=org_id,
                    actor_id=member_id,
                    target_type=ModerationTargetType.COMMENT,
                    target_id=comment_id,
                    reason="Not authorized.",
                )
            )

    async def test_commits_the_unit_of_work(self) -> None:
        service, _, comments, communities, uow = _seeded()
        org_id, community_id, comment_id, moderator_id = uuid4(), uuid4(), uuid4(), uuid4()
        comments.add_comment(
            make_comment_summary(
                comment_id=comment_id, community_id=community_id, organization_id=org_id
            )
        )
        communities.add_membership(
            make_member_summary(
                community_id=community_id, user_id=moderator_id, role=CommunityRole.MODERATOR
            )
        )
        await service.execute(
            ContentModerationInput(
                organization_id=org_id,
                actor_id=moderator_id,
                target_type=ModerationTargetType.COMMENT,
                target_id=comment_id,
                reason="Locked.",
            )
        )
        assert uow.committed is True
