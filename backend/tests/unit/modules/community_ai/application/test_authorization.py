"""Unit tests for `_authorization.ensure_can_access_target`/`ensure_not_moderated`."""

from uuid import uuid4

import pytest

from app.modules.community.public.dto import CommunityRole
from app.modules.community_ai.application.services._authorization import (
    ensure_can_access_target,
    ensure_not_moderated,
)
from app.modules.community_ai.application.services._target_resolution import (
    ResolvedAnalysisTarget,
)
from app.modules.community_ai.domain.enums import CommunityContentTargetType
from app.modules.community_ai.domain.exceptions import AnalysisTargetNotFoundError
from app.modules.community_moderation.public.dto import ModerationTargetType
from tests.unit.modules.community_ai.application.fakes import (
    FakeCommunityQueryPort,
    FakeModerationQueryPort,
    make_member_summary,
)


def _target(**overrides: object) -> ResolvedAnalysisTarget:
    defaults: dict[str, object] = {
        "organization_id": uuid4(),
        "community_id": uuid4(),
        "title": "Title",
        "text": "Text",
        "author_id": uuid4(),
        "is_anonymous": False,
        "visibility_value": "public",
        "is_published": True,
    }
    defaults.update(overrides)
    return ResolvedAnalysisTarget(**defaults)  # type: ignore[arg-type]


class TestEnsureCanAccessTarget:
    async def test_raises_not_found_for_a_cross_organization_target(self) -> None:
        target = _target(organization_id=uuid4())
        with pytest.raises(AnalysisTargetNotFoundError):
            await ensure_can_access_target(
                target,
                target_id=uuid4(),
                requester_id=uuid4(),
                requester_organization_id=uuid4(),
                community_query_port=FakeCommunityQueryPort(),
            )

    async def test_allows_public_content_for_any_requester_in_the_same_org(self) -> None:
        org_id = uuid4()
        target = _target(organization_id=org_id, visibility_value="public")
        await ensure_can_access_target(
            target,
            target_id=uuid4(),
            requester_id=uuid4(),
            requester_organization_id=org_id,
            community_query_port=FakeCommunityQueryPort(),
        )

    async def test_members_only_content_requires_active_membership(self) -> None:
        org_id, community_id, requester_id = uuid4(), uuid4(), uuid4()
        target = _target(
            organization_id=org_id, community_id=community_id, visibility_value="members_only"
        )
        communities = FakeCommunityQueryPort()

        with pytest.raises(AnalysisTargetNotFoundError):
            await ensure_can_access_target(
                target,
                target_id=uuid4(),
                requester_id=requester_id,
                requester_organization_id=org_id,
                community_query_port=communities,
            )

        communities.add_membership(
            make_member_summary(community_id=community_id, user_id=requester_id)
        )
        await ensure_can_access_target(
            target,
            target_id=uuid4(),
            requester_id=requester_id,
            requester_organization_id=org_id,
            community_query_port=communities,
        )

    async def test_private_content_allows_the_author(self) -> None:
        org_id, author_id = uuid4(), uuid4()
        target = _target(organization_id=org_id, visibility_value="private", author_id=author_id)
        await ensure_can_access_target(
            target,
            target_id=uuid4(),
            requester_id=author_id,
            requester_organization_id=org_id,
            community_query_port=FakeCommunityQueryPort(),
        )

    async def test_private_content_allows_a_moderator(self) -> None:
        org_id, community_id, moderator_id = uuid4(), uuid4(), uuid4()
        target = _target(
            organization_id=org_id, community_id=community_id, visibility_value="private"
        )
        communities = FakeCommunityQueryPort()
        communities.add_membership(
            make_member_summary(
                community_id=community_id, user_id=moderator_id, role=CommunityRole.MODERATOR
            )
        )

        await ensure_can_access_target(
            target,
            target_id=uuid4(),
            requester_id=moderator_id,
            requester_organization_id=org_id,
            community_query_port=communities,
        )

    async def test_private_content_denies_an_ordinary_member(self) -> None:
        org_id, community_id, member_id = uuid4(), uuid4(), uuid4()
        target = _target(
            organization_id=org_id, community_id=community_id, visibility_value="private"
        )
        communities = FakeCommunityQueryPort()
        communities.add_membership(
            make_member_summary(community_id=community_id, user_id=member_id)
        )

        with pytest.raises(AnalysisTargetNotFoundError):
            await ensure_can_access_target(
                target,
                target_id=uuid4(),
                requester_id=member_id,
                requester_organization_id=org_id,
                community_query_port=communities,
            )

    async def test_comment_thread_target_with_no_visibility_value_is_authorized_like_public(
        self,
    ) -> None:
        org_id = uuid4()
        target = _target(organization_id=org_id, visibility_value=None, author_id=None)
        await ensure_can_access_target(
            target,
            target_id=uuid4(),
            requester_id=uuid4(),
            requester_organization_id=org_id,
            community_query_port=FakeCommunityQueryPort(),
        )


class TestEnsureNotModerated:
    async def test_passes_for_active_content(self) -> None:
        await ensure_not_moderated(
            CommunityContentTargetType.POST,
            uuid4(),
            moderation_query_port=FakeModerationQueryPort(),
        )

    async def test_raises_not_found_for_removed_content(self) -> None:
        target_id = uuid4()
        moderation = FakeModerationQueryPort()
        moderation.set_content_status(ModerationTargetType.POST, target_id, "removed")

        with pytest.raises(AnalysisTargetNotFoundError):
            await ensure_not_moderated(
                CommunityContentTargetType.POST, target_id, moderation_query_port=moderation
            )

    async def test_raises_not_found_for_restricted_content(self) -> None:
        target_id = uuid4()
        moderation = FakeModerationQueryPort()
        moderation.set_content_status(ModerationTargetType.QUESTION, target_id, "restricted")

        with pytest.raises(AnalysisTargetNotFoundError):
            await ensure_not_moderated(
                CommunityContentTargetType.QUESTION, target_id, moderation_query_port=moderation
            )
