"""Unit tests for `RemoveContentService`, using in-memory fakes."""

from uuid import uuid4

import pytest

from app.modules.community.public.dto import CommunityRole
from app.modules.community_moderation.application.dto import ContentModerationInput
from app.modules.community_moderation.application.services.remove_content_service import (
    RemoveContentService,
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
    make_member_summary,
    make_post_summary,
)


def _seeded() -> (
    tuple[
        RemoveContentService,
        FakeModerationActionRepository,
        FakePostQueryPort,
        FakeCommunityQueryPort,
        FakeUnitOfWork,
    ]
):
    actions = FakeModerationActionRepository()
    posts = FakePostQueryPort()
    communities = FakeCommunityQueryPort()
    uow = FakeUnitOfWork()
    service = RemoveContentService(
        action_repository=actions,
        post_query_port=posts,
        question_query_port=FakeQuestionQueryPort(),
        answer_query_port=FakeAnswerQueryPort(),
        comment_query_port=FakeCommentQueryPort(),
        community_query_port=communities,
        user_query_port=FakeUserQueryPort(),
        unit_of_work=uow,
    )
    return service, actions, posts, communities, uow


class TestRemoveContent:
    async def test_records_a_remove_action(self) -> None:
        service, _, posts, communities, _ = _seeded()
        org_id, community_id, post_id, moderator_id = uuid4(), uuid4(), uuid4(), uuid4()
        posts.add_post(
            make_post_summary(post_id=post_id, community_id=community_id, organization_id=org_id)
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
                target_type=ModerationTargetType.POST,
                target_id=post_id,
                reason="Medical misinformation.",
            )
        )
        assert output.action_type is ModerationActionType.REMOVE
        assert output.new_state == ContentModerationStatus.REMOVED.value
        assert output.previous_state == ContentModerationStatus.ACTIVE.value

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
                    target_type=ModerationTargetType.POST,
                    target_id=uuid4(),
                    reason="Doesn't exist.",
                )
            )

    async def test_member_without_moderator_rank_raises(self) -> None:
        service, _, posts, communities, _ = _seeded()
        org_id, community_id, post_id, member_id = uuid4(), uuid4(), uuid4(), uuid4()
        posts.add_post(
            make_post_summary(post_id=post_id, community_id=community_id, organization_id=org_id)
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
                    target_type=ModerationTargetType.POST,
                    target_id=post_id,
                    reason="Not authorized.",
                )
            )

    async def test_commits_the_unit_of_work(self) -> None:
        service, _, posts, communities, uow = _seeded()
        org_id, community_id, post_id, moderator_id = uuid4(), uuid4(), uuid4(), uuid4()
        posts.add_post(
            make_post_summary(post_id=post_id, community_id=community_id, organization_id=org_id)
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
                target_type=ModerationTargetType.POST,
                target_id=post_id,
                reason="Policy violation.",
            )
        )
        assert uow.committed is True

    async def test_does_not_mutate_the_underlying_post(self) -> None:
        """Disclosed scope boundary — see `entities.py`'s own module
        docstring: `RemoveContentService` records the moderation decision
        as an audit-trail entry; it never reaches into
        `community_posts`' own aggregate or repository."""
        service, _, posts, communities, _ = _seeded()
        org_id, community_id, post_id, moderator_id = uuid4(), uuid4(), uuid4(), uuid4()
        summary = make_post_summary(
            post_id=post_id, community_id=community_id, organization_id=org_id
        )
        posts.add_post(summary)
        communities.add_membership(
            make_member_summary(
                community_id=community_id, user_id=moderator_id, role=CommunityRole.MODERATOR
            )
        )
        await service.execute(
            ContentModerationInput(
                organization_id=org_id,
                actor_id=moderator_id,
                target_type=ModerationTargetType.POST,
                target_id=post_id,
                reason="Policy violation.",
            )
        )
        reloaded = await posts.get_post_summary(post_id)
        assert reloaded is not None
        assert reloaded.status == summary.status
