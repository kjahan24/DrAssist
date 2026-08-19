"""Unit tests for `ModerationAction` — the module's immutable audit
record. Confirms it truly has no mutation surface (only `record()`),
validates its `reason` requirement, and defaults `report_id`/
`moderator_note`/`previous_state`/`new_state` to `None`."""

from uuid import uuid4

import pytest

from app.modules.community_moderation.domain.entities import ModerationAction
from app.modules.community_moderation.domain.enums import (
    ModerationActionType,
    ModerationTargetType,
)
from app.modules.community_moderation.domain.exceptions import ModerationReasonRequiredError


def _make_action(**overrides: object) -> ModerationAction:
    defaults: dict[str, object] = {
        "organization_id": uuid4(),
        "actor_id": uuid4(),
        "action_type": ModerationActionType.REMOVE,
        "target_type": ModerationTargetType.POST,
        "target_id": uuid4(),
        "reason": "Violates community guidelines.",
    }
    defaults.update(overrides)
    return ModerationAction.record(**defaults)  # type: ignore[arg-type]


class TestRecord:
    def test_stores_every_field(self) -> None:
        organization_id, actor_id, target_id = uuid4(), uuid4(), uuid4()
        action = _make_action(
            organization_id=organization_id,
            actor_id=actor_id,
            target_id=target_id,
            action_type=ModerationActionType.LOCK,
        )
        assert action.organization_id == organization_id
        assert action.actor_id == actor_id
        assert action.target_id == target_id
        assert action.action_type is ModerationActionType.LOCK

    def test_defaults_optional_fields_to_none(self) -> None:
        action = _make_action()
        assert action.report_id is None
        assert action.moderator_note is None
        assert action.previous_state is None
        assert action.new_state is None

    def test_accepts_the_full_optional_field_set(self) -> None:
        report_id = uuid4()
        action = _make_action(
            report_id=report_id,
            moderator_note="Escalated by trust & safety.",
            previous_state="active",
            new_state="removed",
        )
        assert action.report_id == report_id
        assert action.moderator_note == "Escalated by trust & safety."
        assert action.previous_state == "active"
        assert action.new_state == "removed"

    def test_strips_surrounding_whitespace_from_reason(self) -> None:
        action = _make_action(reason="  Spam.  ")
        assert action.reason == "Spam."

    def test_blank_reason_raises(self) -> None:
        with pytest.raises(ModerationReasonRequiredError):
            _make_action(reason="   ")

    def test_empty_reason_raises(self) -> None:
        with pytest.raises(ModerationReasonRequiredError):
            _make_action(reason="")

    def test_records_no_domain_event(self) -> None:
        """`ModerationAction` *is* the record of something that already
        happened — it raises no event of its own, mirroring `AuditLog
        .record()`'s identical reasoning. It's an `Entity`, not an
        `AggregateRoot`, so it has no `pull_events()`/`record_event()` at
        all — confirmed by the absence of those attributes."""
        action = _make_action()
        assert not hasattr(action, "pull_events")
        assert not hasattr(action, "record_event")

    def test_has_no_updated_at(self) -> None:
        action = _make_action()
        assert not hasattr(action, "updated_at")

    def test_two_actions_are_distinct_entities(self) -> None:
        first = _make_action()
        second = _make_action()
        assert first.id != second.id
        assert first != second
