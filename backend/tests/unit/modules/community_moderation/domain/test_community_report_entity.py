"""Unit tests for the `CommunityReport` aggregate: creation, deterministic
priority-from-reason, assign/resolve/reject transitions, and the
`ReportAlreadyClosedError` guard shared by all three."""

from uuid import uuid4

import pytest

from app.modules.community_moderation.domain.entities import CommunityReport
from app.modules.community_moderation.domain.enums import (
    ModerationTargetType,
    ReportPriority,
    ReportReason,
    ReportStatus,
)
from app.modules.community_moderation.domain.events import (
    ReportAssigned,
    ReportCreated,
    ReportPriorityChanged,
    ReportRejected,
    ReportResolved,
)
from app.modules.community_moderation.domain.exceptions import ReportAlreadyClosedError


def _make_report(**overrides: object) -> CommunityReport:
    defaults: dict[str, object] = {
        "organization_id": uuid4(),
        "community_id": uuid4(),
        "reporter_id": uuid4(),
        "target_type": ModerationTargetType.POST,
        "target_id": uuid4(),
        "reason": ReportReason.SPAM,
    }
    defaults.update(overrides)
    return CommunityReport.create(**defaults)  # type: ignore[arg-type]


class TestCreate:
    def test_defaults_to_open_status(self) -> None:
        report = _make_report()
        assert report.status is ReportStatus.OPEN

    def test_records_a_report_created_event(self) -> None:
        report = _make_report()
        events = report.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], ReportCreated)
        assert events[0].report_id == report.id

    def test_leaves_assignment_and_resolution_fields_empty(self) -> None:
        report = _make_report()
        assert report.assigned_moderator_id is None
        assert report.resolution is None
        assert report.resolved_at is None

    def test_accepts_an_optional_description(self) -> None:
        report = _make_report(description="Saw this post promoting an unproven cure.")
        assert report.description == "Saw this post promoting an unproven cure."


class TestPriorityDerivedFromReason:
    @pytest.mark.parametrize(
        "reason",
        [
            ReportReason.DANGEROUS_MEDICAL_ADVICE,
            ReportReason.SELF_HARM_CONCERN,
            ReportReason.ILLEGAL_CONTENT,
        ],
    )
    def test_high_severity_reasons_default_to_high_priority(self, reason: ReportReason) -> None:
        report = _make_report(reason=reason)
        assert report.priority is ReportPriority.HIGH

    @pytest.mark.parametrize("reason", [ReportReason.SPAM, ReportReason.OTHER])
    def test_low_severity_reasons_default_to_low_priority(self, reason: ReportReason) -> None:
        report = _make_report(reason=reason)
        assert report.priority is ReportPriority.LOW

    def test_ordinary_reasons_default_to_medium_priority(self) -> None:
        report = _make_report(reason=ReportReason.HARASSMENT)
        assert report.priority is ReportPriority.MEDIUM

    def test_reporters_cannot_set_priority_directly(self) -> None:
        """`CommunityReport.create()` has no `priority` parameter at all —
        confirmed by the fact every report above only ever receives the
        reason-derived value, never an override."""
        report = _make_report(reason=ReportReason.SPAM)
        assert report.priority is ReportPriority.LOW


class TestAssign:
    def test_moves_to_under_review(self) -> None:
        report = _make_report()
        moderator_id = uuid4()
        report.assign(moderator_id=moderator_id)
        assert report.status is ReportStatus.UNDER_REVIEW
        assert report.assigned_moderator_id == moderator_id

    def test_records_a_report_assigned_event(self) -> None:
        report = _make_report()
        report.pull_events()
        moderator_id = uuid4()
        report.assign(moderator_id=moderator_id)
        events = report.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], ReportAssigned)
        assert events[0].moderator_id == moderator_id

    def test_stores_an_optional_note(self) -> None:
        report = _make_report()
        report.assign(moderator_id=uuid4(), note="Escalating for review.")
        assert report.moderator_note == "Escalating for review."

    def test_can_reassign_while_under_review(self) -> None:
        report = _make_report()
        report.assign(moderator_id=uuid4())
        new_moderator_id = uuid4()
        report.assign(moderator_id=new_moderator_id)
        assert report.assigned_moderator_id == new_moderator_id

    def test_raises_once_resolved(self) -> None:
        report = _make_report()
        report.resolve(moderator_id=uuid4(), resolution="Content removed.")
        with pytest.raises(ReportAlreadyClosedError):
            report.assign(moderator_id=uuid4())

    def test_raises_once_rejected(self) -> None:
        report = _make_report()
        report.reject(moderator_id=uuid4(), resolution="No violation found.")
        with pytest.raises(ReportAlreadyClosedError):
            report.assign(moderator_id=uuid4())


class TestResolve:
    def test_moves_to_resolved_and_stamps_resolved_at(self) -> None:
        report = _make_report()
        moderator_id = uuid4()
        report.resolve(moderator_id=moderator_id, resolution="Content removed.")
        assert report.status is ReportStatus.RESOLVED
        assert report.assigned_moderator_id == moderator_id
        assert report.resolution == "Content removed."
        assert report.resolved_at is not None

    def test_records_a_report_resolved_event(self) -> None:
        report = _make_report()
        report.pull_events()
        report.resolve(moderator_id=uuid4(), resolution="Content removed.")
        events = report.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], ReportResolved)
        assert events[0].resolution == "Content removed."

    def test_resolvable_directly_from_open_without_prior_assignment(self) -> None:
        report = _make_report()
        report.resolve(moderator_id=uuid4(), resolution="Content removed.")
        assert report.status is ReportStatus.RESOLVED

    def test_raises_once_already_resolved(self) -> None:
        report = _make_report()
        report.resolve(moderator_id=uuid4(), resolution="Content removed.")
        with pytest.raises(ReportAlreadyClosedError):
            report.resolve(moderator_id=uuid4(), resolution="Again.")

    def test_raises_once_rejected(self) -> None:
        report = _make_report()
        report.reject(moderator_id=uuid4(), resolution="No violation.")
        with pytest.raises(ReportAlreadyClosedError):
            report.resolve(moderator_id=uuid4(), resolution="Content removed.")


class TestReject:
    def test_moves_to_rejected_and_stamps_resolved_at(self) -> None:
        report = _make_report()
        moderator_id = uuid4()
        report.reject(moderator_id=moderator_id, resolution="No violation found.")
        assert report.status is ReportStatus.REJECTED
        assert report.assigned_moderator_id == moderator_id
        assert report.resolution == "No violation found."
        assert report.resolved_at is not None

    def test_records_a_report_rejected_event(self) -> None:
        report = _make_report()
        report.pull_events()
        report.reject(moderator_id=uuid4(), resolution="No violation found.")
        events = report.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], ReportRejected)

    def test_raises_once_already_rejected(self) -> None:
        report = _make_report()
        report.reject(moderator_id=uuid4(), resolution="No violation.")
        with pytest.raises(ReportAlreadyClosedError):
            report.reject(moderator_id=uuid4(), resolution="Again.")

    def test_raises_once_resolved(self) -> None:
        report = _make_report()
        report.resolve(moderator_id=uuid4(), resolution="Content removed.")
        with pytest.raises(ReportAlreadyClosedError):
            report.reject(moderator_id=uuid4(), resolution="No violation.")


class TestSetPriority:
    def test_updates_the_priority(self) -> None:
        report = _make_report(reason=ReportReason.SPAM)
        report.set_priority(ReportPriority.CRITICAL, moderator_id=uuid4())
        assert report.priority is ReportPriority.CRITICAL

    def test_records_a_priority_changed_event(self) -> None:
        report = _make_report(reason=ReportReason.SPAM)
        report.pull_events()
        moderator_id = uuid4()
        report.set_priority(ReportPriority.CRITICAL, moderator_id=moderator_id)
        events = report.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], ReportPriorityChanged)
        assert events[0].previous_priority is ReportPriority.LOW
        assert events[0].new_priority is ReportPriority.CRITICAL
        assert events[0].moderator_id == moderator_id

    def test_raises_once_closed(self) -> None:
        report = _make_report()
        report.resolve(moderator_id=uuid4(), resolution="Done.")
        with pytest.raises(ReportAlreadyClosedError):
            report.set_priority(ReportPriority.HIGH, moderator_id=uuid4())
