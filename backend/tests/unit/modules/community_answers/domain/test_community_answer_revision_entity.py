"""Tests for the `CommunityAnswerRevision` aggregate root — see its own
docstring: append-only and immutable, no mutating methods beyond
`.create()`."""

from uuid import uuid4

from app.modules.community_answers.domain.entities import CommunityAnswerRevision
from app.modules.community_answers.domain.events import CommunityAnswerRevisionCreated
from app.modules.community_answers.domain.value_objects import AnswerId


class TestCommunityAnswerRevisionCreate:
    def test_sets_required_fields(self) -> None:
        answer_id = AnswerId(uuid4())
        author_id = uuid4()
        revision = CommunityAnswerRevision.create(
            answer_id=answer_id,
            revision_number=1,
            previous_body="The previous body text.",
            author_id=author_id,
        )
        assert revision.answer_id == answer_id
        assert revision.revision_number == 1
        assert revision.previous_body == "The previous body text."
        assert revision.author_id == author_id

    def test_assigns_a_unique_id(self) -> None:
        first = CommunityAnswerRevision.create(
            answer_id=AnswerId(uuid4()),
            revision_number=1,
            previous_body="body",
            author_id=uuid4(),
        )
        second = CommunityAnswerRevision.create(
            answer_id=AnswerId(uuid4()),
            revision_number=1,
            previous_body="body",
            author_id=uuid4(),
        )
        assert first.id != second.id

    def test_records_a_community_answer_revision_created_event(self) -> None:
        answer_id = AnswerId(uuid4())
        revision = CommunityAnswerRevision.create(
            answer_id=answer_id, revision_number=3, previous_body="body", author_id=uuid4()
        )
        events = revision.pull_events()
        assert len(events) == 1
        event = events[0]
        assert isinstance(event, CommunityAnswerRevisionCreated)
        assert event.revision_id == revision.id
        assert event.answer_id == answer_id.value
        assert event.revision_number == 3

    def test_pull_events_drains_the_queue(self) -> None:
        revision = CommunityAnswerRevision.create(
            answer_id=AnswerId(uuid4()), revision_number=1, previous_body="body", author_id=uuid4()
        )
        revision.pull_events()
        assert revision.pull_events() == []

    def test_has_no_public_mutating_methods_beyond_create(self) -> None:
        """Structural enforcement of "revision history must be
        immutable" — the class only ever exposes `create`, `record_event`,
        `pull_events`, and `touch` (inherited), nothing that changes
        `previous_body`/`revision_number`/`answer_id`/`author_id` once
        set."""
        own_methods = {
            name
            for name in vars(CommunityAnswerRevision)
            if not name.startswith("_") and callable(getattr(CommunityAnswerRevision, name))
        }
        assert own_methods == {"create"}
