"""Tests for the `Community` aggregate root."""

from uuid import uuid4

from app.modules.community.domain.entities import Community
from app.modules.community.domain.enums import CommunityVisibility
from app.modules.community.domain.events import (
    CommunityAppearanceUpdated,
    CommunityCategoryAssigned,
    CommunityCreated,
    CommunityFeaturedChanged,
    CommunityUpdated,
    CommunityVerifiedChanged,
)
from app.modules.community.domain.value_objects import (
    CommunityDescription,
    CommunityName,
    CommunitySlug,
)


def _slug() -> CommunitySlug:
    return CommunitySlug("diabetes-support")


def _name() -> CommunityName:
    return CommunityName("Diabetes Support")


class TestCommunityCreate:
    def test_sets_required_fields(self) -> None:
        organization_id = uuid4()
        community = Community.create(organization_id=organization_id, slug=_slug(), name=_name())
        assert community.organization_id == organization_id
        assert community.slug == _slug()
        assert community.name == _name()

    def test_no_creator_leaves_created_by_and_updated_by_none(self) -> None:
        community = Community.create(organization_id=uuid4(), slug=_slug(), name=_name())
        assert community.created_by is None
        assert community.updated_by is None

    def test_defaults_to_public_visibility(self) -> None:
        community = Community.create(organization_id=uuid4(), slug=_slug(), name=_name())
        assert community.visibility is CommunityVisibility.PUBLIC

    def test_accepts_explicit_visibility(self) -> None:
        community = Community.create(
            organization_id=uuid4(),
            slug=_slug(),
            name=_name(),
            visibility=CommunityVisibility.PRIVATE,
        )
        assert community.visibility is CommunityVisibility.PRIVATE

    def test_defaults_description_to_none(self) -> None:
        community = Community.create(organization_id=uuid4(), slug=_slug(), name=_name())
        assert community.description is None

    def test_accepts_explicit_description(self) -> None:
        description = CommunityDescription("A support group.")
        community = Community.create(
            organization_id=uuid4(), slug=_slug(), name=_name(), description=description
        )
        assert community.description == description

    def test_created_by_sets_both_created_by_and_updated_by(self) -> None:
        creator_id = uuid4()
        community = Community.create(
            organization_id=uuid4(), slug=_slug(), name=_name(), created_by=creator_id
        )
        assert community.created_by == creator_id
        assert community.updated_by == creator_id

    def test_assigns_a_unique_id(self) -> None:
        first = Community.create(organization_id=uuid4(), slug=_slug(), name=_name())
        second = Community.create(
            organization_id=uuid4(), slug=CommunitySlug("other"), name=_name()
        )
        assert first.id != second.id

    def test_records_a_community_created_event(self) -> None:
        organization_id = uuid4()
        community = Community.create(organization_id=organization_id, slug=_slug(), name=_name())
        events = community.pull_events()
        assert len(events) == 1
        event = events[0]
        assert isinstance(event, CommunityCreated)
        assert event.community_id == community.id
        assert event.organization_id == organization_id
        assert event.slug == "diabetes-support"
        assert event.name == "Diabetes Support"

    def test_pull_events_drains_the_queue(self) -> None:
        community = Community.create(organization_id=uuid4(), slug=_slug(), name=_name())
        community.pull_events()
        assert community.pull_events() == []


class TestCommunityUpdateProfile:
    def test_updates_name(self) -> None:
        community = Community.create(organization_id=uuid4(), slug=_slug(), name=_name())
        new_name = CommunityName("Renamed Community")
        community.update_profile(name=new_name)
        assert community.name == new_name

    def test_updates_visibility(self) -> None:
        community = Community.create(organization_id=uuid4(), slug=_slug(), name=_name())
        community.update_profile(visibility=CommunityVisibility.VERIFIED_ONLY)
        assert community.visibility is CommunityVisibility.VERIFIED_ONLY

    def test_clear_description_takes_precedence_over_a_given_description(self) -> None:
        """`clear_description=True` wins even if `description` is also
        passed — documented precedence, not an expected real call
        shape (a caller wanting to set a new description passes
        `clear_description=False` (the default))."""
        community = Community.create(
            organization_id=uuid4(),
            slug=_slug(),
            name=_name(),
            description=CommunityDescription("Original."),
        )
        community.update_profile(
            description=CommunityDescription("New description."), clear_description=True
        )
        assert community.description is None

    def test_updates_description(self) -> None:
        community = Community.create(organization_id=uuid4(), slug=_slug(), name=_name())
        new_description = CommunityDescription("Updated description.")
        community.update_profile(description=new_description)
        assert community.description == new_description

    def test_clear_description_removes_an_existing_description(self) -> None:
        community = Community.create(
            organization_id=uuid4(),
            slug=_slug(),
            name=_name(),
            description=CommunityDescription("Original."),
        )
        community.update_profile(clear_description=True)
        assert community.description is None

    def test_no_arguments_leaves_fields_unchanged(self) -> None:
        community = Community.create(organization_id=uuid4(), slug=_slug(), name=_name())
        original_name = community.name
        original_visibility = community.visibility
        community.update_profile()
        assert community.name == original_name
        assert community.visibility == original_visibility

    def test_updates_updated_by(self) -> None:
        community = Community.create(organization_id=uuid4(), slug=_slug(), name=_name())
        updater_id = uuid4()
        community.update_profile(updated_by=updater_id)
        assert community.updated_by == updater_id

    def test_updates_updated_at_timestamp(self) -> None:
        community = Community.create(organization_id=uuid4(), slug=_slug(), name=_name())
        before = community.updated_at
        community.update_profile(name=CommunityName("New Name"))
        assert community.updated_at >= before

    def test_records_a_community_updated_event(self) -> None:
        community = Community.create(organization_id=uuid4(), slug=_slug(), name=_name())
        community.pull_events()
        community.update_profile(name=CommunityName("New Name"))
        events = community.pull_events()
        assert len(events) == 1
        event = events[0]
        assert isinstance(event, CommunityUpdated)
        assert event.community_id == community.id
        assert event.organization_id == community.organization_id

    def test_defaults_category_id_to_none(self) -> None:
        community = Community.create(organization_id=uuid4(), slug=_slug(), name=_name())
        assert community.category_id is None

    def test_assigns_a_category(self) -> None:
        community = Community.create(organization_id=uuid4(), slug=_slug(), name=_name())
        category_id = uuid4()
        community.update_profile(category_id=category_id)
        assert community.category_id == category_id

    def test_clear_category_takes_precedence_over_a_given_category(self) -> None:
        community = Community.create(organization_id=uuid4(), slug=_slug(), name=_name())
        community.update_profile(category_id=uuid4(), clear_category=True)
        assert community.category_id is None

    def test_clear_category_removes_an_existing_category(self) -> None:
        community = Community.create(organization_id=uuid4(), slug=_slug(), name=_name())
        community.update_profile(category_id=uuid4())
        community.update_profile(clear_category=True)
        assert community.category_id is None

    def test_no_category_arguments_leaves_category_unchanged(self) -> None:
        community = Community.create(organization_id=uuid4(), slug=_slug(), name=_name())
        category_id = uuid4()
        community.update_profile(category_id=category_id)
        community.update_profile(name=CommunityName("Renamed"))
        assert community.category_id == category_id

    def test_assigning_a_category_records_a_category_assigned_event(self) -> None:
        community = Community.create(organization_id=uuid4(), slug=_slug(), name=_name())
        community.pull_events()
        category_id = uuid4()
        community.update_profile(category_id=category_id)
        events = community.pull_events()
        category_events = [e for e in events if isinstance(e, CommunityCategoryAssigned)]
        assert len(category_events) == 1
        assert category_events[0].community_id == community.id
        assert category_events[0].category_id == category_id

    def test_clearing_a_category_records_a_category_assigned_event_with_none(self) -> None:
        community = Community.create(organization_id=uuid4(), slug=_slug(), name=_name())
        community.update_profile(category_id=uuid4())
        community.pull_events()
        community.update_profile(clear_category=True)
        events = community.pull_events()
        category_events = [e for e in events if isinstance(e, CommunityCategoryAssigned)]
        assert len(category_events) == 1
        assert category_events[0].category_id is None

    def test_no_category_change_records_no_category_assigned_event(self) -> None:
        community = Community.create(organization_id=uuid4(), slug=_slug(), name=_name())
        community.pull_events()
        community.update_profile(name=CommunityName("Renamed"))
        events = community.pull_events()
        assert not any(isinstance(e, CommunityCategoryAssigned) for e in events)


class TestCommunityUpdateAppearance:
    def test_defaults_avatar_and_banner_to_none(self) -> None:
        community = Community.create(organization_id=uuid4(), slug=_slug(), name=_name())
        assert community.avatar_storage_path is None
        assert community.banner_storage_path is None

    def test_sets_avatar_storage_path(self) -> None:
        community = Community.create(organization_id=uuid4(), slug=_slug(), name=_name())
        community.update_appearance(avatar_storage_path="communities/123/avatar/pic.png")
        assert community.avatar_storage_path == "communities/123/avatar/pic.png"

    def test_sets_banner_storage_path(self) -> None:
        community = Community.create(organization_id=uuid4(), slug=_slug(), name=_name())
        community.update_appearance(banner_storage_path="communities/123/banner/pic.png")
        assert community.banner_storage_path == "communities/123/banner/pic.png"

    def test_clear_avatar_takes_precedence_over_a_given_avatar(self) -> None:
        community = Community.create(organization_id=uuid4(), slug=_slug(), name=_name())
        community.update_appearance(avatar_storage_path="path/a.png", clear_avatar=True)
        assert community.avatar_storage_path is None

    def test_clear_avatar_removes_an_existing_avatar(self) -> None:
        community = Community.create(organization_id=uuid4(), slug=_slug(), name=_name())
        community.update_appearance(avatar_storage_path="path/a.png")
        community.update_appearance(clear_avatar=True)
        assert community.avatar_storage_path is None

    def test_clear_banner_takes_precedence_over_a_given_banner(self) -> None:
        community = Community.create(organization_id=uuid4(), slug=_slug(), name=_name())
        community.update_appearance(banner_storage_path="path/b.png", clear_banner=True)
        assert community.banner_storage_path is None

    def test_clear_banner_removes_an_existing_banner(self) -> None:
        community = Community.create(organization_id=uuid4(), slug=_slug(), name=_name())
        community.update_appearance(banner_storage_path="path/b.png")
        community.update_appearance(clear_banner=True)
        assert community.banner_storage_path is None

    def test_no_arguments_leaves_fields_unchanged(self) -> None:
        community = Community.create(organization_id=uuid4(), slug=_slug(), name=_name())
        community.update_appearance(avatar_storage_path="path/a.png")
        community.update_appearance()
        assert community.avatar_storage_path == "path/a.png"

    def test_updates_updated_at_timestamp(self) -> None:
        community = Community.create(organization_id=uuid4(), slug=_slug(), name=_name())
        before = community.updated_at
        community.update_appearance(avatar_storage_path="path/a.png")
        assert community.updated_at >= before

    def test_records_a_community_appearance_updated_event(self) -> None:
        community = Community.create(organization_id=uuid4(), slug=_slug(), name=_name())
        community.pull_events()
        community.update_appearance(avatar_storage_path="path/a.png")
        events = community.pull_events()
        assert len(events) == 1
        event = events[0]
        assert isinstance(event, CommunityAppearanceUpdated)
        assert event.community_id == community.id


class TestCommunitySetVerified:
    def test_defaults_to_not_verified(self) -> None:
        community = Community.create(organization_id=uuid4(), slug=_slug(), name=_name())
        assert community.is_verified is False

    def test_sets_verified_true(self) -> None:
        community = Community.create(organization_id=uuid4(), slug=_slug(), name=_name())
        community.set_verified(True)
        assert community.is_verified is True

    def test_sets_verified_false(self) -> None:
        community = Community.create(organization_id=uuid4(), slug=_slug(), name=_name())
        community.set_verified(True)
        community.set_verified(False)
        assert community.is_verified is False

    def test_records_a_community_verified_changed_event(self) -> None:
        community = Community.create(organization_id=uuid4(), slug=_slug(), name=_name())
        community.pull_events()
        community.set_verified(True)
        events = community.pull_events()
        assert len(events) == 1
        event = events[0]
        assert isinstance(event, CommunityVerifiedChanged)
        assert event.community_id == community.id
        assert event.is_verified is True

    def test_setting_the_same_value_is_a_no_op_and_records_no_event(self) -> None:
        community = Community.create(organization_id=uuid4(), slug=_slug(), name=_name())
        community.pull_events()
        community.set_verified(False)
        assert community.pull_events() == []


class TestCommunitySetFeatured:
    def test_defaults_to_not_featured(self) -> None:
        community = Community.create(organization_id=uuid4(), slug=_slug(), name=_name())
        assert community.is_featured is False

    def test_sets_featured_true(self) -> None:
        community = Community.create(organization_id=uuid4(), slug=_slug(), name=_name())
        community.set_featured(True)
        assert community.is_featured is True

    def test_sets_featured_false(self) -> None:
        community = Community.create(organization_id=uuid4(), slug=_slug(), name=_name())
        community.set_featured(True)
        community.set_featured(False)
        assert community.is_featured is False

    def test_records_a_community_featured_changed_event(self) -> None:
        community = Community.create(organization_id=uuid4(), slug=_slug(), name=_name())
        community.pull_events()
        community.set_featured(True)
        events = community.pull_events()
        assert len(events) == 1
        event = events[0]
        assert isinstance(event, CommunityFeaturedChanged)
        assert event.community_id == community.id
        assert event.is_featured is True

    def test_setting_the_same_value_is_a_no_op_and_records_no_event(self) -> None:
        community = Community.create(organization_id=uuid4(), slug=_slug(), name=_name())
        community.pull_events()
        community.set_featured(False)
        assert community.pull_events() == []
