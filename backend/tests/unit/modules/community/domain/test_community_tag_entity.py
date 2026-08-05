"""Tests for the `CommunityTag` aggregate root."""

from app.modules.community.domain.entities import CommunityTag
from app.modules.community.domain.events import CommunityTagCreated
from app.modules.community.domain.value_objects import CommunityTagName


def _name() -> CommunityTagName:
    return CommunityTagName("diabetes")


class TestCommunityTagCreate:
    def test_sets_the_name(self) -> None:
        tag = CommunityTag.create(name=_name())
        assert tag.name == _name()

    def test_assigns_a_unique_id(self) -> None:
        first = CommunityTag.create(name=_name())
        second = CommunityTag.create(name=CommunityTagName("oncology"))
        assert first.id != second.id

    def test_records_a_community_tag_created_event(self) -> None:
        tag = CommunityTag.create(name=_name())
        events = tag.pull_events()
        assert len(events) == 1
        event = events[0]
        assert isinstance(event, CommunityTagCreated)
        assert event.tag_id == tag.id
        assert event.name == "diabetes"

    def test_pull_events_drains_the_queue(self) -> None:
        tag = CommunityTag.create(name=_name())
        tag.pull_events()
        assert tag.pull_events() == []
