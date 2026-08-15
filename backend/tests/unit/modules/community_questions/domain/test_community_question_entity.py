"""Tests for the `CommunityQuestion` aggregate root."""

from uuid import uuid4

from app.modules.community_questions.domain.entities import CommunityQuestion
from app.modules.community_questions.domain.enums import (
    QuestionStatus,
    QuestionType,
    QuestionVisibility,
)
from app.modules.community_questions.domain.events import (
    CommunityQuestionArchived,
    CommunityQuestionClosed,
    CommunityQuestionCreated,
    CommunityQuestionDeleted,
    CommunityQuestionFeaturedChanged,
    CommunityQuestionPinnedChanged,
    CommunityQuestionPublished,
    CommunityQuestionReopened,
    CommunityQuestionUnfollowed,
    CommunityQuestionUpdated,
)
from app.modules.community_questions.domain.exceptions import (
    QuestionAlreadyArchivedError,
    QuestionAlreadyClosedError,
    QuestionAlreadyDeletedError,
    QuestionAlreadyPublishedError,
    QuestionBodyRequiredError,
    QuestionNotClosedError,
)
from app.modules.community_questions.domain.value_objects import (
    QuestionSlug,
    QuestionSummary,
    QuestionTitle,
)


def _question(**overrides: object) -> CommunityQuestion:
    defaults: dict[str, object] = {
        "community_id": uuid4(),
        "organization_id": uuid4(),
        "author_id": uuid4(),
        "primary_topic_id": uuid4(),
        "title": QuestionTitle("How should hypertension be managed?"),
        "body": "This is the body of the question about hypertension.",
    }
    defaults.update(overrides)
    return CommunityQuestion.create(**defaults)  # type: ignore[arg-type]


class TestCommunityQuestionCreate:
    def test_sets_required_fields(self) -> None:
        community_id = uuid4()
        organization_id = uuid4()
        author_id = uuid4()
        primary_topic_id = uuid4()
        question = CommunityQuestion.create(
            community_id=community_id,
            organization_id=organization_id,
            author_id=author_id,
            primary_topic_id=primary_topic_id,
            title=QuestionTitle("Test Question"),
            body="Some body text.",
        )
        assert question.community_id == community_id
        assert question.organization_id == organization_id
        assert question.author_id == author_id
        assert question.primary_topic_id == primary_topic_id

    def test_defaults_to_draft_status(self) -> None:
        question = _question()
        assert question.status is QuestionStatus.DRAFT

    def test_defaults_to_public_visibility(self) -> None:
        question = _question()
        assert question.visibility is QuestionVisibility.PUBLIC

    def test_defaults_to_general_type(self) -> None:
        question = _question()
        assert question.question_type is QuestionType.GENERAL

    def test_accepts_explicit_question_type(self) -> None:
        question = _question(question_type=QuestionType.CLINICAL)
        assert question.question_type is QuestionType.CLINICAL

    def test_generates_a_slug_from_the_title(self) -> None:
        question = _question(title=QuestionTitle("How To Manage Hypertension"))
        assert str(question.slug) == "how-to-manage-hypertension"

    def test_accepts_an_explicit_slug(self) -> None:
        question = _question(slug=QuestionSlug("custom-slug"))
        assert str(question.slug) == "custom-slug"

    def test_generates_a_summary_from_the_body(self) -> None:
        question = _question(body="A short body for summary generation.")
        assert str(question.summary) == "A short body for summary generation."

    def test_accepts_an_explicit_summary(self) -> None:
        summary = QuestionSummary("Custom summary text.")
        question = _question(summary=summary)
        assert question.summary == summary

    def test_blank_body_raises(self) -> None:
        try:
            _question(body="   ")
            raised = False
        except QuestionBodyRequiredError:
            raised = True
        assert raised is True

    def test_computes_read_time_from_body(self) -> None:
        question = _question(body="word " * 400)  # 400 words / 200 wpm = 2 minutes
        assert question.read_time_minutes == 2

    def test_read_time_minimum_is_one(self) -> None:
        question = _question(body="Short.")
        assert question.read_time_minutes == 1

    def test_defaults_to_not_anonymous(self) -> None:
        question = _question()
        assert question.is_anonymous is False

    def test_accepts_is_anonymous(self) -> None:
        question = _question(is_anonymous=True)
        assert question.is_anonymous is True

    def test_defaults_to_not_pinned_or_featured(self) -> None:
        question = _question()
        assert question.is_pinned is False
        assert question.is_featured is False

    def test_defaults_counters_to_zero(self) -> None:
        question = _question()
        assert question.view_count == 0
        assert question.follower_count == 0
        assert question.bookmark_count == 0
        assert question.share_count == 0

    def test_defaults_accepted_answer_id_to_none(self) -> None:
        question = _question()
        assert question.accepted_answer_id is None

    def test_defaults_published_at_to_none(self) -> None:
        question = _question()
        assert question.published_at is None

    def test_updated_by_defaults_to_author_id(self) -> None:
        author_id = uuid4()
        question = _question(author_id=author_id)
        assert question.updated_by == author_id

    def test_assigns_a_unique_id(self) -> None:
        first = _question()
        second = _question()
        assert first.id != second.id

    def test_records_a_community_question_created_event(self) -> None:
        author_id = uuid4()
        community_id = uuid4()
        question = _question(
            author_id=author_id, community_id=community_id, title=QuestionTitle("Hello")
        )
        events = question.pull_events()
        assert len(events) == 1
        event = events[0]
        assert isinstance(event, CommunityQuestionCreated)
        assert event.question_id == question.id
        assert event.community_id == community_id
        assert event.author_id == author_id
        assert event.title == "Hello"

    def test_pull_events_drains_the_queue(self) -> None:
        question = _question()
        question.pull_events()
        assert question.pull_events() == []


class TestCommunityQuestionUpdateContent:
    def test_updates_the_title(self) -> None:
        question = _question()
        new_title = QuestionTitle("New Title")
        question.update_content(title=new_title)
        assert question.title == new_title

    def test_updates_the_body_and_recomputes_read_time(self) -> None:
        question = _question(body="short body")
        question.update_content(body="word " * 400)
        assert question.read_time_minutes == 2

    def test_blank_body_raises(self) -> None:
        question = _question()
        try:
            question.update_content(body="   ")
            raised = False
        except QuestionBodyRequiredError:
            raised = True
        assert raised is True

    def test_editing_body_leaves_existing_summary_unchanged(self) -> None:
        original_summary = QuestionSummary("Hand-written summary.")
        question = _question(summary=original_summary)
        question.update_content(body="A completely different body now.")
        assert question.summary == original_summary

    def test_regenerate_summary_true_rederives_from_new_body(self) -> None:
        question = _question(summary=QuestionSummary("Old summary."))
        question.update_content(body="A brand new body for the question.", regenerate_summary=True)
        assert str(question.summary) == "A brand new body for the question."

    def test_explicit_summary_overrides_regenerate_flag(self) -> None:
        explicit = QuestionSummary("Explicit summary.")
        question = _question()
        question.update_content(body="New body content.", summary=explicit, regenerate_summary=True)
        assert question.summary == explicit

    def test_updates_question_type(self) -> None:
        question = _question()
        question.update_content(question_type=QuestionType.RESEARCH_QUESTION)
        assert question.question_type is QuestionType.RESEARCH_QUESTION

    def test_updates_visibility(self) -> None:
        question = _question()
        question.update_content(visibility=QuestionVisibility.PRIVATE)
        assert question.visibility is QuestionVisibility.PRIVATE

    def test_updates_is_anonymous(self) -> None:
        question = _question()
        question.update_content(is_anonymous=True)
        assert question.is_anonymous is True

    def test_no_arguments_leaves_fields_unchanged(self) -> None:
        question = _question()
        original_title = question.title
        question.update_content()
        assert question.title == original_title

    def test_updates_updated_by(self) -> None:
        question = _question()
        updater_id = uuid4()
        question.update_content(updated_by=updater_id)
        assert question.updated_by == updater_id

    def test_updates_updated_at_timestamp(self) -> None:
        question = _question()
        before = question.updated_at
        question.update_content(title=QuestionTitle("New Title"))
        assert question.updated_at >= before

    def test_records_a_community_question_updated_event(self) -> None:
        question = _question()
        question.pull_events()
        question.update_content(title=QuestionTitle("New Title"))
        events = question.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], CommunityQuestionUpdated)
        assert events[0].question_id == question.id


class TestCommunityQuestionPublish:
    def test_sets_status_to_published(self) -> None:
        question = _question()
        question.publish()
        assert question.status is QuestionStatus.PUBLISHED

    def test_sets_published_at(self) -> None:
        question = _question()
        question.publish()
        assert question.published_at is not None

    def test_already_published_raises(self) -> None:
        question = _question()
        question.publish()
        try:
            question.publish()
            raised = False
        except QuestionAlreadyPublishedError:
            raised = True
        assert raised is True

    def test_records_a_community_question_published_event(self) -> None:
        community_id = uuid4()
        question = _question(community_id=community_id)
        question.pull_events()
        question.publish()
        events = question.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], CommunityQuestionPublished)
        assert events[0].question_id == question.id
        assert events[0].community_id == community_id

    def test_republishing_an_archived_question_succeeds(self) -> None:
        question = _question()
        question.publish()
        question.archive()
        question.publish()
        assert question.status is QuestionStatus.PUBLISHED


class TestCommunityQuestionArchive:
    def test_sets_status_to_archived(self) -> None:
        question = _question()
        question.archive()
        assert question.status is QuestionStatus.ARCHIVED

    def test_already_archived_raises(self) -> None:
        question = _question()
        question.archive()
        try:
            question.archive()
            raised = False
        except QuestionAlreadyArchivedError:
            raised = True
        assert raised is True

    def test_records_a_community_question_archived_event(self) -> None:
        question = _question()
        question.pull_events()
        question.archive()
        events = question.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], CommunityQuestionArchived)
        assert events[0].question_id == question.id

    def test_archiving_a_draft_question_succeeds(self) -> None:
        question = _question()
        question.archive()
        assert question.status is QuestionStatus.ARCHIVED


class TestCommunityQuestionClose:
    def test_sets_status_to_closed(self) -> None:
        question = _question()
        question.publish()
        question.close()
        assert question.status is QuestionStatus.CLOSED

    def test_already_closed_raises(self) -> None:
        question = _question()
        question.publish()
        question.close()
        try:
            question.close()
            raised = False
        except QuestionAlreadyClosedError:
            raised = True
        assert raised is True

    def test_records_a_community_question_closed_event(self) -> None:
        question = _question()
        question.publish()
        question.pull_events()
        question.close()
        events = question.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], CommunityQuestionClosed)
        assert events[0].question_id == question.id

    def test_closing_a_draft_question_succeeds(self) -> None:
        question = _question()
        question.close()
        assert question.status is QuestionStatus.CLOSED


class TestCommunityQuestionReopen:
    def test_sets_status_to_published(self) -> None:
        question = _question()
        question.publish()
        question.close()
        question.reopen()
        assert question.status is QuestionStatus.PUBLISHED

    def test_not_closed_raises(self) -> None:
        question = _question()
        question.publish()
        try:
            question.reopen()
            raised = False
        except QuestionNotClosedError:
            raised = True
        assert raised is True

    def test_draft_question_cannot_be_reopened(self) -> None:
        question = _question()
        try:
            question.reopen()
            raised = False
        except QuestionNotClosedError:
            raised = True
        assert raised is True

    def test_records_a_community_question_reopened_event(self) -> None:
        question = _question()
        question.publish()
        question.close()
        question.pull_events()
        question.reopen()
        events = question.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], CommunityQuestionReopened)
        assert events[0].question_id == question.id


class TestCommunityQuestionDelete:
    def test_sets_status_to_deleted(self) -> None:
        question = _question()
        question.delete()
        assert question.status is QuestionStatus.DELETED

    def test_already_deleted_raises(self) -> None:
        question = _question()
        question.delete()
        try:
            question.delete()
            raised = False
        except QuestionAlreadyDeletedError:
            raised = True
        assert raised is True

    def test_records_a_community_question_deleted_event(self) -> None:
        question = _question()
        question.pull_events()
        question.delete()
        events = question.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], CommunityQuestionDeleted)
        assert events[0].question_id == question.id

    def test_deleting_a_published_question_succeeds(self) -> None:
        question = _question()
        question.publish()
        question.delete()
        assert question.status is QuestionStatus.DELETED


class TestCommunityQuestionSetPinned:
    def test_sets_pinned_true(self) -> None:
        question = _question()
        question.set_pinned(True)
        assert question.is_pinned is True

    def test_sets_pinned_false(self) -> None:
        question = _question()
        question.set_pinned(True)
        question.set_pinned(False)
        assert question.is_pinned is False

    def test_records_a_community_question_pinned_changed_event(self) -> None:
        question = _question()
        question.pull_events()
        question.set_pinned(True)
        events = question.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], CommunityQuestionPinnedChanged)
        assert events[0].is_pinned is True

    def test_setting_the_same_value_is_a_no_op(self) -> None:
        question = _question()
        question.pull_events()
        question.set_pinned(False)
        assert question.pull_events() == []


class TestCommunityQuestionSetFeatured:
    def test_sets_featured_true(self) -> None:
        question = _question()
        question.set_featured(True)
        assert question.is_featured is True

    def test_records_a_community_question_featured_changed_event(self) -> None:
        question = _question()
        question.pull_events()
        question.set_featured(True)
        events = question.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], CommunityQuestionFeaturedChanged)
        assert events[0].is_featured is True

    def test_setting_the_same_value_is_a_no_op(self) -> None:
        question = _question()
        question.pull_events()
        question.set_featured(False)
        assert question.pull_events() == []


class TestCommunityQuestionFollowerCount:
    def test_increment_increases_the_count_by_one(self) -> None:
        question = _question()
        question.increment_follower_count()
        assert question.follower_count == 1

    def test_increment_does_not_touch_updated_at(self) -> None:
        question = _question()
        before = question.updated_at
        question.increment_follower_count()
        assert question.updated_at == before

    def test_increment_does_not_record_an_event(self) -> None:
        question = _question()
        question.pull_events()
        question.increment_follower_count()
        assert question.pull_events() == []

    def test_decrement_decreases_the_count_by_one(self) -> None:
        question = _question()
        question.increment_follower_count()
        question.increment_follower_count()
        question.decrement_follower_count(user_id=uuid4())
        assert question.follower_count == 1

    def test_decrement_floors_at_zero(self) -> None:
        question = _question()
        question.decrement_follower_count(user_id=uuid4())
        assert question.follower_count == 0

    def test_decrement_does_not_touch_updated_at(self) -> None:
        question = _question()
        before = question.updated_at
        question.decrement_follower_count(user_id=uuid4())
        assert question.updated_at == before

    def test_decrement_records_a_community_question_unfollowed_event(self) -> None:
        question = _question()
        user_id = uuid4()
        question.pull_events()
        question.decrement_follower_count(user_id=user_id)
        events = question.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], CommunityQuestionUnfollowed)
        assert events[0].question_id == question.id
        assert events[0].user_id == user_id
