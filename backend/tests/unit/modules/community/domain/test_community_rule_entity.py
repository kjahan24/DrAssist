"""Tests for the `CommunityRule` aggregate root."""

from uuid import uuid4

from app.modules.community.domain.entities import CommunityRule
from app.modules.community.domain.events import (
    CommunityRuleCreated,
    CommunityRuleEnabledChanged,
    CommunityRuleUpdated,
)
from app.modules.community.domain.value_objects import CommunityId, CommunityRuleTitle


def _community_id() -> CommunityId:
    return CommunityId(uuid4())


def _title() -> CommunityRuleTitle:
    return CommunityRuleTitle("Be respectful")


class TestCommunityRuleCreate:
    def test_sets_required_fields(self) -> None:
        community_id = _community_id()
        rule = CommunityRule.create(community_id=community_id, title=_title())
        assert rule.community_id == community_id
        assert rule.title == _title()

    def test_defaults_description_to_none(self) -> None:
        rule = CommunityRule.create(community_id=_community_id(), title=_title())
        assert rule.description is None

    def test_accepts_explicit_description(self) -> None:
        rule = CommunityRule.create(
            community_id=_community_id(), title=_title(), description="No harassment."
        )
        assert rule.description == "No harassment."

    def test_defaults_position_to_zero(self) -> None:
        rule = CommunityRule.create(community_id=_community_id(), title=_title())
        assert rule.position == 0

    def test_accepts_explicit_position(self) -> None:
        rule = CommunityRule.create(community_id=_community_id(), title=_title(), position=3)
        assert rule.position == 3

    def test_defaults_to_enabled(self) -> None:
        rule = CommunityRule.create(community_id=_community_id(), title=_title())
        assert rule.is_enabled is True

    def test_assigns_a_unique_id(self) -> None:
        community_id = _community_id()
        first = CommunityRule.create(community_id=community_id, title=_title())
        second = CommunityRule.create(
            community_id=community_id, title=CommunityRuleTitle("No spam")
        )
        assert first.id != second.id

    def test_records_a_community_rule_created_event(self) -> None:
        community_id = _community_id()
        rule = CommunityRule.create(community_id=community_id, title=_title())
        events = rule.pull_events()
        assert len(events) == 1
        event = events[0]
        assert isinstance(event, CommunityRuleCreated)
        assert event.rule_id == rule.id
        assert event.community_id == community_id.value
        assert event.title == "Be respectful"

    def test_pull_events_drains_the_queue(self) -> None:
        rule = CommunityRule.create(community_id=_community_id(), title=_title())
        rule.pull_events()
        assert rule.pull_events() == []


class TestCommunityRuleUpdateDetails:
    def test_updates_title(self) -> None:
        rule = CommunityRule.create(community_id=_community_id(), title=_title())
        new_title = CommunityRuleTitle("No self-promotion")
        rule.update_details(title=new_title)
        assert rule.title == new_title

    def test_updates_description(self) -> None:
        rule = CommunityRule.create(community_id=_community_id(), title=_title())
        rule.update_details(description="Updated description.")
        assert rule.description == "Updated description."

    def test_no_arguments_leaves_fields_unchanged(self) -> None:
        rule = CommunityRule.create(
            community_id=_community_id(), title=_title(), description="Original."
        )
        rule.update_details()
        assert rule.title == _title()
        assert rule.description == "Original."

    def test_updates_updated_at_timestamp(self) -> None:
        rule = CommunityRule.create(community_id=_community_id(), title=_title())
        before = rule.updated_at
        rule.update_details(title=CommunityRuleTitle("New title"))
        assert rule.updated_at >= before

    def test_records_a_community_rule_updated_event(self) -> None:
        community_id = _community_id()
        rule = CommunityRule.create(community_id=community_id, title=_title())
        rule.pull_events()
        rule.update_details(title=CommunityRuleTitle("New title"))
        events = rule.pull_events()
        assert len(events) == 1
        event = events[0]
        assert isinstance(event, CommunityRuleUpdated)
        assert event.rule_id == rule.id
        assert event.community_id == community_id.value


class TestCommunityRuleSetEnabled:
    def test_disables_an_enabled_rule(self) -> None:
        rule = CommunityRule.create(community_id=_community_id(), title=_title())
        rule.set_enabled(False)
        assert rule.is_enabled is False

    def test_enables_a_disabled_rule(self) -> None:
        rule = CommunityRule.create(community_id=_community_id(), title=_title())
        rule.set_enabled(False)
        rule.set_enabled(True)
        assert rule.is_enabled is True

    def test_records_a_community_rule_enabled_changed_event(self) -> None:
        community_id = _community_id()
        rule = CommunityRule.create(community_id=community_id, title=_title())
        rule.pull_events()
        rule.set_enabled(False)
        events = rule.pull_events()
        assert len(events) == 1
        event = events[0]
        assert isinstance(event, CommunityRuleEnabledChanged)
        assert event.rule_id == rule.id
        assert event.community_id == community_id.value
        assert event.is_enabled is False

    def test_setting_the_same_value_is_a_no_op_and_records_no_event(self) -> None:
        rule = CommunityRule.create(community_id=_community_id(), title=_title())
        rule.pull_events()
        rule.set_enabled(True)
        assert rule.pull_events() == []


class TestCommunityRuleReposition:
    def test_updates_position(self) -> None:
        rule = CommunityRule.create(community_id=_community_id(), title=_title(), position=0)
        rule.reposition(5)
        assert rule.position == 5

    def test_updates_updated_at_timestamp(self) -> None:
        rule = CommunityRule.create(community_id=_community_id(), title=_title())
        before = rule.updated_at
        rule.reposition(2)
        assert rule.updated_at >= before

    def test_records_no_domain_event(self) -> None:
        """Deliberately silent — `ManageCommunityRulesService.reorder()`
        constructs a single `CommunityRulesReordered` event covering the
        whole batch itself rather than each repositioned rule recording
        its own (see that service's own docstring)."""
        rule = CommunityRule.create(community_id=_community_id(), title=_title())
        rule.pull_events()
        rule.reposition(2)
        assert rule.pull_events() == []
