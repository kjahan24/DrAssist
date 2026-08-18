"""Tests for the `CommunityAnswer` aggregate root."""

from uuid import uuid4

from app.modules.community_answers.domain.entities import CommunityAnswer, CommunityAnswerRevision
from app.modules.community_answers.domain.enums import AnswerStatus, AnswerVisibility
from app.modules.community_answers.domain.events import (
    CommunityAnswerArchived,
    CommunityAnswerBestRemoved,
    CommunityAnswerCreated,
    CommunityAnswerDeleted,
    CommunityAnswerFeaturedChanged,
    CommunityAnswerMarkedBest,
    CommunityAnswerPinnedChanged,
    CommunityAnswerPublished,
    CommunityAnswerRestored,
    CommunityAnswerUpdated,
)
from app.modules.community_answers.domain.exceptions import (
    AnswerAlreadyArchivedError,
    AnswerAlreadyBestAnswerError,
    AnswerAlreadyDeletedError,
    AnswerAlreadyPublishedError,
    AnswerBodyRequiredError,
    AnswerCannotBeRestoredError,
    AnswerNotBestAnswerError,
    AnswerNotPublishedForBestAnswerError,
)
from app.modules.community_answers.domain.value_objects import AnswerBody, AnswerSummary


def _answer(**overrides: object) -> CommunityAnswer:
    defaults: dict[str, object] = {
        "question_id": uuid4(),
        "community_id": uuid4(),
        "organization_id": uuid4(),
        "topic_id": uuid4(),
        "author_id": uuid4(),
        "body": AnswerBody("This is the body of the answer."),
    }
    defaults.update(overrides)
    return CommunityAnswer.create(**defaults)  # type: ignore[arg-type]


class TestCommunityAnswerCreate:
    def test_sets_required_fields(self) -> None:
        question_id = uuid4()
        community_id = uuid4()
        organization_id = uuid4()
        topic_id = uuid4()
        author_id = uuid4()
        answer = CommunityAnswer.create(
            question_id=question_id,
            community_id=community_id,
            organization_id=organization_id,
            topic_id=topic_id,
            author_id=author_id,
            body=AnswerBody("Some body text."),
        )
        assert answer.question_id == question_id
        assert answer.community_id == community_id
        assert answer.organization_id == organization_id
        assert answer.topic_id == topic_id
        assert answer.author_id == author_id

    def test_defaults_to_draft_status(self) -> None:
        answer = _answer()
        assert answer.status is AnswerStatus.DRAFT

    def test_defaults_to_public_visibility(self) -> None:
        answer = _answer()
        assert answer.visibility is AnswerVisibility.PUBLIC

    def test_accepts_explicit_visibility(self) -> None:
        answer = _answer(visibility=AnswerVisibility.PRIVATE)
        assert answer.visibility is AnswerVisibility.PRIVATE

    def test_generates_a_summary_from_the_body(self) -> None:
        answer = _answer(body=AnswerBody("A short body for summary generation."))
        assert str(answer.summary) == "A short body for summary generation."

    def test_accepts_an_explicit_summary(self) -> None:
        summary = AnswerSummary("Custom summary text.")
        answer = _answer(summary=summary)
        assert answer.summary == summary

    def test_blank_body_raises(self) -> None:
        try:
            AnswerBody("   ")
            raised = False
        except AnswerBodyRequiredError:
            raised = True
        assert raised is True

    def test_defaults_to_not_anonymous(self) -> None:
        answer = _answer()
        assert answer.is_anonymous is False

    def test_accepts_is_anonymous(self) -> None:
        answer = _answer(is_anonymous=True)
        assert answer.is_anonymous is True

    def test_defaults_to_not_best_featured_or_pinned(self) -> None:
        answer = _answer()
        assert answer.is_best_answer is False
        assert answer.is_featured is False
        assert answer.is_pinned is False

    def test_defaults_counters_to_zero(self) -> None:
        answer = _answer()
        assert answer.view_count == 0
        assert answer.share_count == 0

    def test_defaults_revision_number_to_one(self) -> None:
        answer = _answer()
        assert answer.revision_number == 1

    def test_defaults_published_at_to_none(self) -> None:
        answer = _answer()
        assert answer.published_at is None

    def test_updated_by_defaults_to_author_id(self) -> None:
        author_id = uuid4()
        answer = _answer(author_id=author_id)
        assert answer.updated_by == author_id

    def test_assigns_a_unique_id(self) -> None:
        first = _answer()
        second = _answer()
        assert first.id != second.id

    def test_records_a_community_answer_created_event(self) -> None:
        author_id = uuid4()
        question_id = uuid4()
        answer = _answer(author_id=author_id, question_id=question_id)
        events = answer.pull_events()
        assert len(events) == 1
        event = events[0]
        assert isinstance(event, CommunityAnswerCreated)
        assert event.answer_id == answer.id
        assert event.question_id == question_id
        assert event.author_id == author_id

    def test_pull_events_drains_the_queue(self) -> None:
        answer = _answer()
        answer.pull_events()
        assert answer.pull_events() == []


class TestCommunityAnswerUpdateContent:
    def test_updates_the_body(self) -> None:
        answer = _answer()
        new_body = AnswerBody("A brand new body.")
        answer.update_content(body=new_body)
        assert answer.body == new_body

    def test_editing_body_leaves_existing_summary_unchanged(self) -> None:
        original_summary = AnswerSummary("Hand-written summary.")
        answer = _answer(summary=original_summary)
        answer.update_content(body=AnswerBody("A completely different body now."))
        assert answer.summary == original_summary

    def test_regenerate_summary_true_rederives_from_new_body(self) -> None:
        answer = _answer(summary=AnswerSummary("Old summary."))
        answer.update_content(
            body=AnswerBody("A brand new body for the answer."), regenerate_summary=True
        )
        assert str(answer.summary) == "A brand new body for the answer."

    def test_explicit_summary_overrides_regenerate_flag(self) -> None:
        explicit = AnswerSummary("Explicit summary.")
        answer = _answer()
        answer.update_content(
            body=AnswerBody("New body content."), summary=explicit, regenerate_summary=True
        )
        assert answer.summary == explicit

    def test_no_arguments_leaves_fields_unchanged(self) -> None:
        answer = _answer()
        original_body = answer.body
        answer.update_content()
        assert answer.body == original_body

    def test_updates_updated_by(self) -> None:
        answer = _answer()
        updater_id = uuid4()
        answer.update_content(updated_by=updater_id)
        assert answer.updated_by == updater_id

    def test_updates_updated_at_timestamp(self) -> None:
        answer = _answer()
        before = answer.updated_at
        answer.update_content(body=AnswerBody("New body."))
        assert answer.updated_at >= before

    def test_records_a_community_answer_updated_event(self) -> None:
        answer = _answer()
        answer.pull_events()
        answer.update_content(body=AnswerBody("New body."))
        events = answer.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], CommunityAnswerUpdated)
        assert events[0].answer_id == answer.id

    def test_editing_a_draft_body_creates_no_revision(self) -> None:
        answer = _answer()
        revision = answer.update_content(body=AnswerBody("New body while still a draft."))
        assert revision is None

    def test_editing_a_draft_body_leaves_revision_number_unchanged(self) -> None:
        answer = _answer()
        answer.update_content(body=AnswerBody("New body while still a draft."))
        assert answer.revision_number == 1

    def test_editing_a_published_answer_body_creates_a_revision(self) -> None:
        original_body = AnswerBody("Original published body.")
        answer = _answer(body=original_body)
        answer.publish()
        revision = answer.update_content(body=AnswerBody("Edited published body."))
        assert isinstance(revision, CommunityAnswerRevision)
        assert revision.previous_body == str(original_body)

    def test_editing_a_published_answer_increments_revision_number(self) -> None:
        answer = _answer()
        answer.publish()
        answer.update_content(body=AnswerBody("Edited body."))
        assert answer.revision_number == 2

    def test_revision_captures_the_revision_number_before_incrementing(self) -> None:
        answer = _answer()
        answer.publish()
        revision = answer.update_content(body=AnswerBody("Edited body."))
        assert revision is not None
        assert revision.revision_number == 1

    def test_revision_author_defaults_to_the_answers_own_author(self) -> None:
        author_id = uuid4()
        answer = _answer(author_id=author_id)
        answer.publish()
        revision = answer.update_content(body=AnswerBody("Edited body."))
        assert revision is not None
        assert revision.author_id == author_id

    def test_revision_author_uses_explicit_updated_by_when_given(self) -> None:
        editor_id = uuid4()
        answer = _answer()
        answer.publish()
        revision = answer.update_content(body=AnswerBody("Edited body."), updated_by=editor_id)
        assert revision is not None
        assert revision.author_id == editor_id

    def test_editing_published_answer_with_unchanged_body_creates_no_revision(self) -> None:
        body = AnswerBody("Same body throughout.")
        answer = _answer(body=body)
        answer.publish()
        revision = answer.update_content(body=AnswerBody("Same body throughout."))
        assert revision is None

    def test_editing_summary_only_on_a_published_answer_creates_no_revision(self) -> None:
        answer = _answer()
        answer.publish()
        revision = answer.update_content(summary=AnswerSummary("New summary only."))
        assert revision is None

    def test_editing_an_archived_answers_body_creates_no_revision(self) -> None:
        answer = _answer()
        answer.publish()
        answer.archive()
        revision = answer.update_content(body=AnswerBody("Edited after archiving."))
        assert revision is None

    def test_three_consecutive_published_edits_create_three_ordered_revisions(self) -> None:
        answer = _answer(body=AnswerBody("v1"))
        answer.publish()
        first_revision = answer.update_content(body=AnswerBody("v2"))
        second_revision = answer.update_content(body=AnswerBody("v3"))
        third_revision = answer.update_content(body=AnswerBody("v4"))

        assert first_revision is not None and first_revision.previous_body == "v1"
        assert first_revision.revision_number == 1
        assert second_revision is not None and second_revision.previous_body == "v2"
        assert second_revision.revision_number == 2
        assert third_revision is not None and third_revision.previous_body == "v3"
        assert third_revision.revision_number == 3
        assert answer.revision_number == 4


class TestCommunityAnswerPublish:
    def test_sets_status_to_published(self) -> None:
        answer = _answer()
        answer.publish()
        assert answer.status is AnswerStatus.PUBLISHED

    def test_sets_published_at(self) -> None:
        answer = _answer()
        answer.publish()
        assert answer.published_at is not None

    def test_already_published_raises(self) -> None:
        answer = _answer()
        answer.publish()
        try:
            answer.publish()
            raised = False
        except AnswerAlreadyPublishedError:
            raised = True
        assert raised is True

    def test_records_a_community_answer_published_event(self) -> None:
        question_id = uuid4()
        answer = _answer(question_id=question_id)
        answer.pull_events()
        answer.publish()
        events = answer.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], CommunityAnswerPublished)
        assert events[0].answer_id == answer.id
        assert events[0].question_id == question_id

    def test_republishing_an_archived_answer_succeeds(self) -> None:
        answer = _answer()
        answer.publish()
        answer.archive()
        answer.publish()
        assert answer.status is AnswerStatus.PUBLISHED


class TestCommunityAnswerArchive:
    def test_sets_status_to_archived(self) -> None:
        answer = _answer()
        answer.archive()
        assert answer.status is AnswerStatus.ARCHIVED

    def test_already_archived_raises(self) -> None:
        answer = _answer()
        answer.archive()
        try:
            answer.archive()
            raised = False
        except AnswerAlreadyArchivedError:
            raised = True
        assert raised is True

    def test_records_a_community_answer_archived_event(self) -> None:
        answer = _answer()
        answer.pull_events()
        answer.archive()
        events = answer.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], CommunityAnswerArchived)
        assert events[0].answer_id == answer.id

    def test_archiving_a_draft_answer_succeeds(self) -> None:
        answer = _answer()
        answer.archive()
        assert answer.status is AnswerStatus.ARCHIVED

    def test_archiving_the_best_answer_clears_the_best_flag(self) -> None:
        answer = _answer()
        answer.publish()
        answer.mark_as_best()
        answer.archive()
        assert answer.is_best_answer is False

    def test_archiving_the_best_answer_emits_a_best_removed_event(self) -> None:
        question_id = uuid4()
        answer = _answer(question_id=question_id)
        answer.publish()
        answer.mark_as_best()
        answer.pull_events()
        answer.archive()
        events = answer.pull_events()
        best_removed_events = [e for e in events if isinstance(e, CommunityAnswerBestRemoved)]
        assert len(best_removed_events) == 1
        assert best_removed_events[0].answer_id == answer.id
        assert best_removed_events[0].question_id == question_id

    def test_archiving_the_best_answer_also_emits_the_archived_event(self) -> None:
        answer = _answer()
        answer.publish()
        answer.mark_as_best()
        answer.pull_events()
        answer.archive()
        events = answer.pull_events()
        assert any(isinstance(e, CommunityAnswerArchived) for e in events)

    def test_archiving_a_non_best_answer_emits_no_best_removed_event(self) -> None:
        answer = _answer()
        answer.pull_events()
        answer.archive()
        events = answer.pull_events()
        assert not any(isinstance(e, CommunityAnswerBestRemoved) for e in events)


class TestCommunityAnswerRestore:
    def test_restores_an_archived_answer_to_draft(self) -> None:
        answer = _answer()
        answer.archive()
        answer.restore()
        assert answer.status is AnswerStatus.DRAFT

    def test_restores_a_deleted_answer_to_draft(self) -> None:
        answer = _answer()
        answer.delete()
        answer.restore()
        assert answer.status is AnswerStatus.DRAFT

    def test_never_restores_directly_to_published(self) -> None:
        answer = _answer()
        answer.publish()
        answer.archive()
        answer.restore()
        assert answer.status is not AnswerStatus.PUBLISHED

    def test_restoring_a_draft_answer_raises(self) -> None:
        answer = _answer()
        try:
            answer.restore()
            raised = False
        except AnswerCannotBeRestoredError:
            raised = True
        assert raised is True

    def test_restoring_a_published_answer_raises(self) -> None:
        answer = _answer()
        answer.publish()
        try:
            answer.restore()
            raised = False
        except AnswerCannotBeRestoredError:
            raised = True
        assert raised is True

    def test_records_a_community_answer_restored_event(self) -> None:
        answer = _answer()
        answer.archive()
        answer.pull_events()
        answer.restore()
        events = answer.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], CommunityAnswerRestored)
        assert events[0].answer_id == answer.id


class TestCommunityAnswerDelete:
    def test_sets_status_to_deleted(self) -> None:
        answer = _answer()
        answer.delete()
        assert answer.status is AnswerStatus.DELETED

    def test_already_deleted_raises(self) -> None:
        answer = _answer()
        answer.delete()
        try:
            answer.delete()
            raised = False
        except AnswerAlreadyDeletedError:
            raised = True
        assert raised is True

    def test_records_a_community_answer_deleted_event(self) -> None:
        answer = _answer()
        answer.pull_events()
        answer.delete()
        events = answer.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], CommunityAnswerDeleted)
        assert events[0].answer_id == answer.id

    def test_deleting_a_published_answer_succeeds(self) -> None:
        answer = _answer()
        answer.publish()
        answer.delete()
        assert answer.status is AnswerStatus.DELETED

    def test_deleting_the_best_answer_clears_the_best_flag(self) -> None:
        answer = _answer()
        answer.publish()
        answer.mark_as_best()
        answer.delete()
        assert answer.is_best_answer is False

    def test_deleting_the_best_answer_emits_a_best_removed_event(self) -> None:
        question_id = uuid4()
        answer = _answer(question_id=question_id)
        answer.publish()
        answer.mark_as_best()
        answer.pull_events()
        answer.delete()
        events = answer.pull_events()
        best_removed_events = [e for e in events if isinstance(e, CommunityAnswerBestRemoved)]
        assert len(best_removed_events) == 1
        assert best_removed_events[0].question_id == question_id

    def test_deleting_a_non_best_answer_emits_no_best_removed_event(self) -> None:
        answer = _answer()
        answer.pull_events()
        answer.delete()
        events = answer.pull_events()
        assert not any(isinstance(e, CommunityAnswerBestRemoved) for e in events)


class TestCommunityAnswerSetFeatured:
    def test_sets_featured_true(self) -> None:
        answer = _answer()
        answer.set_featured(True)
        assert answer.is_featured is True

    def test_sets_featured_false(self) -> None:
        answer = _answer()
        answer.set_featured(True)
        answer.set_featured(False)
        assert answer.is_featured is False

    def test_records_a_community_answer_featured_changed_event(self) -> None:
        answer = _answer()
        answer.pull_events()
        answer.set_featured(True)
        events = answer.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], CommunityAnswerFeaturedChanged)
        assert events[0].is_featured is True

    def test_setting_the_same_value_is_a_no_op(self) -> None:
        answer = _answer()
        answer.pull_events()
        answer.set_featured(False)
        assert answer.pull_events() == []


class TestCommunityAnswerSetPinned:
    def test_sets_pinned_true(self) -> None:
        answer = _answer()
        answer.set_pinned(True)
        assert answer.is_pinned is True

    def test_sets_pinned_false(self) -> None:
        answer = _answer()
        answer.set_pinned(True)
        answer.set_pinned(False)
        assert answer.is_pinned is False

    def test_records_a_community_answer_pinned_changed_event(self) -> None:
        answer = _answer()
        answer.pull_events()
        answer.set_pinned(True)
        events = answer.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], CommunityAnswerPinnedChanged)
        assert events[0].is_pinned is True

    def test_setting_the_same_value_is_a_no_op(self) -> None:
        answer = _answer()
        answer.pull_events()
        answer.set_pinned(False)
        assert answer.pull_events() == []


class TestCommunityAnswerMarkAsBest:
    def test_marks_a_published_answer_as_best(self) -> None:
        answer = _answer()
        answer.publish()
        answer.mark_as_best()
        assert answer.is_best_answer is True

    def test_marking_a_draft_answer_as_best_raises(self) -> None:
        answer = _answer()
        try:
            answer.mark_as_best()
            raised = False
        except AnswerNotPublishedForBestAnswerError:
            raised = True
        assert raised is True

    def test_marking_an_archived_answer_as_best_raises(self) -> None:
        answer = _answer()
        answer.publish()
        answer.archive()
        try:
            answer.mark_as_best()
            raised = False
        except AnswerNotPublishedForBestAnswerError:
            raised = True
        assert raised is True

    def test_marking_an_already_best_answer_raises(self) -> None:
        answer = _answer()
        answer.publish()
        answer.mark_as_best()
        try:
            answer.mark_as_best()
            raised = False
        except AnswerAlreadyBestAnswerError:
            raised = True
        assert raised is True

    def test_records_a_community_answer_marked_best_event(self) -> None:
        question_id = uuid4()
        answer = _answer(question_id=question_id)
        answer.publish()
        answer.pull_events()
        answer.mark_as_best()
        events = answer.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], CommunityAnswerMarkedBest)
        assert events[0].answer_id == answer.id
        assert events[0].question_id == question_id


class TestCommunityAnswerLifecycleCycles:
    def test_archive_restore_publish_mark_best_full_cycle(self) -> None:
        answer = _answer()
        answer.publish()
        answer.archive()
        answer.restore()
        answer.publish()
        answer.mark_as_best()
        assert answer.status is AnswerStatus.PUBLISHED
        assert answer.is_best_answer is True

    def test_delete_then_restore_then_publish_again_succeeds(self) -> None:
        answer = _answer()
        answer.publish()
        answer.delete()
        answer.restore()
        answer.publish()
        assert answer.status is AnswerStatus.PUBLISHED

    def test_best_answer_flag_does_not_survive_a_delete_restore_publish_cycle(self) -> None:
        answer = _answer()
        answer.publish()
        answer.mark_as_best()
        answer.delete()
        answer.restore()
        answer.publish()
        assert answer.is_best_answer is False


class TestCommunityAnswerRemoveBest:
    def test_clears_the_best_flag(self) -> None:
        answer = _answer()
        answer.publish()
        answer.mark_as_best()
        answer.remove_best()
        assert answer.is_best_answer is False

    def test_removing_best_when_not_best_raises(self) -> None:
        answer = _answer()
        try:
            answer.remove_best()
            raised = False
        except AnswerNotBestAnswerError:
            raised = True
        assert raised is True

    def test_records_a_community_answer_best_removed_event(self) -> None:
        question_id = uuid4()
        answer = _answer(question_id=question_id)
        answer.publish()
        answer.mark_as_best()
        answer.pull_events()
        answer.remove_best()
        events = answer.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], CommunityAnswerBestRemoved)
        assert events[0].answer_id == answer.id
        assert events[0].question_id == question_id
