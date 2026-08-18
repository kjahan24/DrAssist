"""Tests for the `SavedContent` aggregate root."""

from uuid import uuid4

from app.modules.community_engagement.domain.entities import SavedContent
from app.modules.community_engagement.domain.enums import EngagementTargetType
from app.modules.community_engagement.domain.events import ContentSaved, ContentUnsaved


def _saved(**overrides: object) -> SavedContent:
    defaults: dict[str, object] = {
        "user_id": uuid4(),
        "organization_id": uuid4(),
        "target_type": EngagementTargetType.ANSWER,
        "target_id": uuid4(),
    }
    defaults.update(overrides)
    return SavedContent.create(**defaults)  # type: ignore[arg-type]


class TestSavedContentCreate:
    def test_sets_required_fields(self) -> None:
        user_id = uuid4()
        organization_id = uuid4()
        target_id = uuid4()
        saved = SavedContent.create(
            user_id=user_id,
            organization_id=organization_id,
            target_type=EngagementTargetType.QUESTION,
            target_id=target_id,
        )
        assert saved.user_id == user_id
        assert saved.organization_id == organization_id
        assert saved.target_type is EngagementTargetType.QUESTION
        assert saved.target_id == target_id

    def test_assigns_a_unique_id(self) -> None:
        first = _saved()
        second = _saved()
        assert first.id != second.id

    def test_records_a_content_saved_event(self) -> None:
        user_id = uuid4()
        target_id = uuid4()
        saved = _saved(user_id=user_id, target_id=target_id)
        events = saved.pull_events()
        assert len(events) == 1
        event = events[0]
        assert isinstance(event, ContentSaved)
        assert event.saved_content_id == saved.id
        assert event.user_id == user_id
        assert event.target_id == target_id

    def test_pull_events_drains_the_queue(self) -> None:
        saved = _saved()
        saved.pull_events()
        assert saved.pull_events() == []


class TestSavedContentMarkRemoved:
    def test_records_a_content_unsaved_event(self) -> None:
        user_id = uuid4()
        target_id = uuid4()
        saved = _saved(user_id=user_id, target_id=target_id)
        saved.pull_events()
        saved.mark_removed()
        events = saved.pull_events()
        assert len(events) == 1
        event = events[0]
        assert isinstance(event, ContentUnsaved)
        assert event.saved_content_id == saved.id
        assert event.user_id == user_id
        assert event.target_id == target_id
