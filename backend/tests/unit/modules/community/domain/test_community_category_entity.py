"""Tests for the `CommunityCategory` aggregate root."""

from app.modules.community.domain.entities import CommunityCategory
from app.modules.community.domain.events import CommunityCategoryCreated
from app.modules.community.domain.value_objects import CommunityCategoryName, CommunitySlug


def _name() -> CommunityCategoryName:
    return CommunityCategoryName("Oncology")


def _slug() -> CommunitySlug:
    return CommunitySlug("oncology")


class TestCommunityCategoryCreate:
    def test_sets_required_fields(self) -> None:
        category = CommunityCategory.create(name=_name(), slug=_slug())
        assert category.name == _name()
        assert category.slug == _slug()

    def test_defaults_description_to_none(self) -> None:
        category = CommunityCategory.create(name=_name(), slug=_slug())
        assert category.description is None

    def test_accepts_explicit_description(self) -> None:
        category = CommunityCategory.create(
            name=_name(), slug=_slug(), description="Cancer care and treatment."
        )
        assert category.description == "Cancer care and treatment."

    def test_defaults_to_active(self) -> None:
        category = CommunityCategory.create(name=_name(), slug=_slug())
        assert category.is_active is True

    def test_assigns_a_unique_id(self) -> None:
        first = CommunityCategory.create(name=_name(), slug=_slug())
        second = CommunityCategory.create(
            name=CommunityCategoryName("Dermatology"), slug=CommunitySlug("dermatology")
        )
        assert first.id != second.id

    def test_records_a_community_category_created_event(self) -> None:
        category = CommunityCategory.create(name=_name(), slug=_slug())
        events = category.pull_events()
        assert len(events) == 1
        event = events[0]
        assert isinstance(event, CommunityCategoryCreated)
        assert event.category_id == category.id
        assert event.name == "Oncology"

    def test_pull_events_drains_the_queue(self) -> None:
        category = CommunityCategory.create(name=_name(), slug=_slug())
        category.pull_events()
        assert category.pull_events() == []


class TestCommunityCategoryDeactivate:
    def test_sets_is_active_false(self) -> None:
        category = CommunityCategory.create(name=_name(), slug=_slug())
        category.deactivate()
        assert category.is_active is False

    def test_updates_updated_at_timestamp(self) -> None:
        category = CommunityCategory.create(name=_name(), slug=_slug())
        before = category.updated_at
        category.deactivate()
        assert category.updated_at >= before

    def test_deactivating_an_already_inactive_category_stays_inactive(self) -> None:
        category = CommunityCategory.create(name=_name(), slug=_slug())
        category.deactivate()
        category.deactivate()
        assert category.is_active is False


class TestCommunityCategoryActivate:
    def test_sets_is_active_true(self) -> None:
        category = CommunityCategory.create(name=_name(), slug=_slug())
        category.deactivate()
        category.activate()
        assert category.is_active is True

    def test_updates_updated_at_timestamp(self) -> None:
        category = CommunityCategory.create(name=_name(), slug=_slug())
        category.deactivate()
        before = category.updated_at
        category.activate()
        assert category.updated_at >= before

    def test_activating_an_already_active_category_stays_active(self) -> None:
        category = CommunityCategory.create(name=_name(), slug=_slug())
        category.activate()
        assert category.is_active is True
