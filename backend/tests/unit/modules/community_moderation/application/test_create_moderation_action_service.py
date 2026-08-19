"""Unit tests for `CreateModerationActionService`, using in-memory fakes."""

from uuid import uuid4

import pytest

from app.modules.community.public.dto import CommunityRole
from app.modules.community_moderation.application.dto import CreateModerationActionInput
from app.modules.community_moderation.application.services.create_moderation_action_service import (  # noqa: E501
    CreateModerationActionService,
)
from app.modules.community_moderation.domain.enums import (
    ContentModerationStatus,
    ModerationActionType,
    ModerationTargetType,
)
from app.modules.community_moderation.domain.exceptions import (
    ContentActionTargetNotFoundError,
    InsufficientModeratorRoleError,
    UnsupportedModerationActionTypeError,
    UnsupportedModerationTargetTypeError,
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
        CreateModerationActionService,
        FakeModerationActionRepository,
        FakePostQueryPort,
        FakeCommunityQueryPort,
        FakeUnitOfWork,
    ]
):
    actions = FakeModerationActionRepository()
    posts = FakePostQueryPort()
    questions = FakeQuestionQueryPort()
    answers = FakeAnswerQueryPort()
    comments = FakeCommentQueryPort()
    communities = FakeCommunityQueryPort()
    users = FakeUserQueryPort()
    uow = FakeUnitOfWork()
    service = CreateModerationActionService(
        action_repository=actions,
        post_query_port=posts,
        question_query_port=questions,
        answer_query_port=answers,
        comment_query_port=comments,
        community_query_port=communities,
        user_query_port=users,
        unit_of_work=uow,
    )
    return service, actions, posts, communities, uow


class TestCreateModerationAction:
    async def test_records_a_restrict_action(self) -> None:
        service, actions, posts, communities, _ = _seeded()
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
            CreateModerationActionInput(
                organization_id=org_id,
                actor_id=moderator_id,
                action_type=ModerationActionType.RESTRICT,
                target_type=ModerationTargetType.POST,
                target_id=post_id,
                reason="Borderline content, restricting visibility.",
            )
        )
        assert output.action_type is ModerationActionType.RESTRICT
        assert output.new_state == ContentModerationStatus.RESTRICTED.value
        assert output.previous_state == ContentModerationStatus.ACTIVE.value

    async def test_second_action_uses_first_actions_new_state_as_previous(self) -> None:
        service, actions, posts, communities, _ = _seeded()
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
            CreateModerationActionInput(
                organization_id=org_id,
                actor_id=moderator_id,
                action_type=ModerationActionType.REMOVE,
                target_type=ModerationTargetType.POST,
                target_id=post_id,
                reason="Policy violation.",
            )
        )
        second = await service.execute(
            CreateModerationActionInput(
                organization_id=org_id,
                actor_id=moderator_id,
                action_type=ModerationActionType.RESTORE,
                target_type=ModerationTargetType.POST,
                target_id=post_id,
                reason="Appeal granted.",
            )
        )
        assert second.previous_state == ContentModerationStatus.REMOVED.value
        assert second.new_state == ContentModerationStatus.ACTIVE.value

    async def test_user_shaped_action_type_raises(self) -> None:
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
        with pytest.raises(UnsupportedModerationActionTypeError):
            await service.execute(
                CreateModerationActionInput(
                    organization_id=org_id,
                    actor_id=moderator_id,
                    action_type=ModerationActionType.WARN_USER,
                    target_type=ModerationTargetType.POST,
                    target_id=post_id,
                    reason="Wrong verb for content.",
                )
            )

    async def test_community_target_type_raises(self) -> None:
        service, _, _, communities, _ = _seeded()
        org_id, community_id, moderator_id = uuid4(), uuid4(), uuid4()
        communities.add_membership(
            make_member_summary(
                community_id=community_id, user_id=moderator_id, role=CommunityRole.MODERATOR
            )
        )
        with pytest.raises(UnsupportedModerationTargetTypeError):
            await service.execute(
                CreateModerationActionInput(
                    organization_id=org_id,
                    actor_id=moderator_id,
                    action_type=ModerationActionType.REMOVE,
                    target_type=ModerationTargetType.COMMUNITY,
                    target_id=community_id,
                    reason="Communities aren't content.",
                )
            )

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
                CreateModerationActionInput(
                    organization_id=org_id,
                    actor_id=moderator_id,
                    action_type=ModerationActionType.REMOVE,
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
                CreateModerationActionInput(
                    organization_id=org_id,
                    actor_id=member_id,
                    action_type=ModerationActionType.REMOVE,
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
            CreateModerationActionInput(
                organization_id=org_id,
                actor_id=moderator_id,
                action_type=ModerationActionType.APPROVE,
                target_type=ModerationTargetType.POST,
                target_id=post_id,
                reason="Reviewed, no issue.",
            )
        )
        assert uow.committed is True

    async def test_records_moderator_note_and_report_id(self) -> None:
        service, _, posts, communities, _ = _seeded()
        org_id, community_id, post_id, moderator_id, report_id = (
            uuid4(),
            uuid4(),
            uuid4(),
            uuid4(),
            uuid4(),
        )
        posts.add_post(
            make_post_summary(post_id=post_id, community_id=community_id, organization_id=org_id)
        )
        communities.add_membership(
            make_member_summary(
                community_id=community_id, user_id=moderator_id, role=CommunityRole.MODERATOR
            )
        )
        output = await service.execute(
            CreateModerationActionInput(
                organization_id=org_id,
                actor_id=moderator_id,
                action_type=ModerationActionType.LOCK,
                target_type=ModerationTargetType.POST,
                target_id=post_id,
                reason="Heated discussion.",
                report_id=report_id,
                moderator_note="Escalated internally.",
            )
        )
        assert output.report_id == report_id
        assert output.moderator_note == "Escalated internally."
