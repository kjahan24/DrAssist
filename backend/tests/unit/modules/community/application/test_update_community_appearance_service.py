"""Unit tests for `UpdateCommunityAppearanceService`, using in-memory fakes."""

from uuid import uuid4

import pytest

from app.modules.community.application.dto import UpdateCommunityAppearanceInput
from app.modules.community.application.services.update_community_appearance_service import (
    UpdateCommunityAppearanceService,
)
from app.modules.community.domain.entities import Community, CommunityMember
from app.modules.community.domain.enums import CommunityRole
from app.modules.community.domain.events import CommunityAppearanceUpdated
from app.modules.community.domain.exceptions import (
    CommunityMediaEmptyError,
    CommunityMembershipNotFoundError,
    CommunityNotFoundError,
    InsufficientCommunityRoleError,
)
from app.modules.community.domain.value_objects import CommunityId, CommunityName, CommunitySlug
from tests.unit.modules.community.application.fakes import (
    FakeCommunityMemberRepository,
    FakeCommunityRepository,
    FakeStoragePort,
    FakeUnitOfWork,
)


async def _seeded(
    role: CommunityRole = CommunityRole.OWNER,
) -> tuple[
    UpdateCommunityAppearanceService,
    FakeCommunityRepository,
    Community,
    CommunityMember,
    FakeStoragePort,
    FakeUnitOfWork,
]:
    communities = FakeCommunityRepository()
    members = FakeCommunityMemberRepository()
    storage = FakeStoragePort()
    uow = FakeUnitOfWork()
    service = UpdateCommunityAppearanceService(
        community_repository=communities,
        community_member_repository=members,
        storage_port=storage,
        unit_of_work=uow,
    )

    community = Community.create(
        organization_id=uuid4(), slug=CommunitySlug("oncology"), name=CommunityName("Oncology")
    )
    await communities.add(community)

    acting_user_id = uuid4()
    member = CommunityMember.create(
        community_id=CommunityId(community.id), user_id=acting_user_id, role=role
    )
    await members.add(member)

    return service, communities, community, member, storage, uow


class TestUpdateCommunityAppearance:
    async def test_uploads_an_avatar(self) -> None:
        service, communities, community, member, storage, _ = await _seeded()
        output = await service.execute(
            UpdateCommunityAppearanceInput(
                community_id=community.id,
                acting_user_id=member.user_id,
                avatar_data=b"fake-image-bytes",
                avatar_content_type="image/png",
                avatar_filename="avatar.png",
            )
        )
        assert output.avatar_storage_path == f"{community.id}/avatar/avatar.png"
        stored = await communities.get_by_id(community.id)
        assert stored is not None
        assert stored.avatar_storage_path == f"{community.id}/avatar/avatar.png"
        assert storage.objects[("community-media", f"{community.id}/avatar/avatar.png")] == (
            b"fake-image-bytes"
        )

    async def test_uploads_a_banner(self) -> None:
        service, communities, community, member, _, _ = await _seeded()
        output = await service.execute(
            UpdateCommunityAppearanceInput(
                community_id=community.id,
                acting_user_id=member.user_id,
                banner_data=b"fake-banner-bytes",
                banner_content_type="image/png",
                banner_filename="banner.png",
            )
        )
        assert output.banner_storage_path == f"{community.id}/banner/banner.png"

    async def test_clear_avatar_removes_an_existing_avatar(self) -> None:
        service, _, community, member, _, _ = await _seeded()
        await service.execute(
            UpdateCommunityAppearanceInput(
                community_id=community.id,
                acting_user_id=member.user_id,
                avatar_data=b"fake-image-bytes",
                avatar_filename="avatar.png",
            )
        )
        output = await service.execute(
            UpdateCommunityAppearanceInput(
                community_id=community.id, acting_user_id=member.user_id, clear_avatar=True
            )
        )
        assert output.avatar_storage_path is None

    async def test_clear_banner_removes_an_existing_banner(self) -> None:
        service, _, community, member, _, _ = await _seeded()
        await service.execute(
            UpdateCommunityAppearanceInput(
                community_id=community.id,
                acting_user_id=member.user_id,
                banner_data=b"fake-banner-bytes",
                banner_filename="banner.png",
            )
        )
        output = await service.execute(
            UpdateCommunityAppearanceInput(
                community_id=community.id, acting_user_id=member.user_id, clear_banner=True
            )
        )
        assert output.banner_storage_path is None

    async def test_empty_avatar_bytes_raises(self) -> None:
        service, _, community, member, _, _ = await _seeded()
        with pytest.raises(CommunityMediaEmptyError):
            await service.execute(
                UpdateCommunityAppearanceInput(
                    community_id=community.id,
                    acting_user_id=member.user_id,
                    avatar_data=b"",
                    avatar_filename="avatar.png",
                )
            )

    async def test_empty_banner_bytes_raises(self) -> None:
        service, _, community, member, _, _ = await _seeded()
        with pytest.raises(CommunityMediaEmptyError):
            await service.execute(
                UpdateCommunityAppearanceInput(
                    community_id=community.id,
                    acting_user_id=member.user_id,
                    banner_data=b"",
                    banner_filename="banner.png",
                )
            )

    async def test_unknown_community_raises(self) -> None:
        service, _, _, member, _, _ = await _seeded()
        with pytest.raises(CommunityNotFoundError):
            await service.execute(
                UpdateCommunityAppearanceInput(community_id=uuid4(), acting_user_id=member.user_id)
            )

    async def test_acting_user_with_no_membership_raises(self) -> None:
        service, _, community, _, _, _ = await _seeded()
        with pytest.raises(CommunityMembershipNotFoundError):
            await service.execute(
                UpdateCommunityAppearanceInput(community_id=community.id, acting_user_id=uuid4())
            )

    async def test_member_role_is_insufficient(self) -> None:
        service, _, community, member, _, _ = await _seeded(role=CommunityRole.MEMBER)
        with pytest.raises(InsufficientCommunityRoleError):
            await service.execute(
                UpdateCommunityAppearanceInput(
                    community_id=community.id, acting_user_id=member.user_id
                )
            )

    async def test_moderator_role_is_insufficient(self) -> None:
        service, _, community, member, _, _ = await _seeded(role=CommunityRole.MODERATOR)
        with pytest.raises(InsufficientCommunityRoleError):
            await service.execute(
                UpdateCommunityAppearanceInput(
                    community_id=community.id, acting_user_id=member.user_id
                )
            )

    async def test_admin_role_is_sufficient(self) -> None:
        service, _, community, member, _, _ = await _seeded(role=CommunityRole.ADMIN)
        output = await service.execute(
            UpdateCommunityAppearanceInput(
                community_id=community.id,
                acting_user_id=member.user_id,
                avatar_data=b"fake-image-bytes",
                avatar_filename="avatar.png",
            )
        )
        assert output.avatar_storage_path is not None

    async def test_commits_the_unit_of_work(self) -> None:
        service, _, community, member, _, uow = await _seeded()
        await service.execute(
            UpdateCommunityAppearanceInput(
                community_id=community.id,
                acting_user_id=member.user_id,
                avatar_data=b"fake-image-bytes",
                avatar_filename="avatar.png",
            )
        )
        assert uow.committed is True

    async def test_publishes_a_community_appearance_updated_event(self) -> None:
        service, _, community, member, _, uow = await _seeded()
        await service.execute(
            UpdateCommunityAppearanceInput(
                community_id=community.id,
                acting_user_id=member.user_id,
                avatar_data=b"fake-image-bytes",
                avatar_filename="avatar.png",
            )
        )
        assert any(isinstance(e, CommunityAppearanceUpdated) for e in uow.published_events)
