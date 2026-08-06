"""Tests for the `CommunityPost` aggregate root."""

from uuid import uuid4

from app.modules.community_posts.domain.entities import CommunityPost
from app.modules.community_posts.domain.enums import PostStatus, PostType, PostVisibility
from app.modules.community_posts.domain.events import (
    CommunityPostArchived,
    CommunityPostCreated,
    CommunityPostFeaturedChanged,
    CommunityPostLockedChanged,
    CommunityPostPinnedChanged,
    CommunityPostPublished,
    CommunityPostUpdated,
)
from app.modules.community_posts.domain.exceptions import (
    PostAlreadyArchivedError,
    PostAlreadyPublishedError,
    PostBodyRequiredError,
)
from app.modules.community_posts.domain.value_objects import PostExcerpt, PostSlug, PostTitle


def _post(**overrides: object) -> CommunityPost:
    defaults: dict[str, object] = {
        "community_id": uuid4(),
        "organization_id": uuid4(),
        "author_id": uuid4(),
        "title": PostTitle("Cardiac Arrhythmia Tips"),
        "body": "This is the body of the post about cardiac arrhythmia.",
    }
    defaults.update(overrides)
    return CommunityPost.create(**defaults)  # type: ignore[arg-type]


class TestCommunityPostCreate:
    def test_sets_required_fields(self) -> None:
        community_id = uuid4()
        organization_id = uuid4()
        author_id = uuid4()
        post = CommunityPost.create(
            community_id=community_id,
            organization_id=organization_id,
            author_id=author_id,
            title=PostTitle("Test Post"),
            body="Some body text.",
        )
        assert post.community_id == community_id
        assert post.organization_id == organization_id
        assert post.author_id == author_id

    def test_defaults_to_draft_status(self) -> None:
        post = _post()
        assert post.status is PostStatus.DRAFT

    def test_defaults_to_public_visibility(self) -> None:
        post = _post()
        assert post.visibility is PostVisibility.PUBLIC

    def test_defaults_to_discussion_type(self) -> None:
        post = _post()
        assert post.post_type is PostType.DISCUSSION

    def test_accepts_explicit_post_type(self) -> None:
        post = _post(post_type=PostType.CLINICAL_CASE)
        assert post.post_type is PostType.CLINICAL_CASE

    def test_generates_a_slug_from_the_title(self) -> None:
        post = _post(title=PostTitle("Cardiac Arrhythmia Tips"))
        assert str(post.slug) == "cardiac-arrhythmia-tips"

    def test_accepts_an_explicit_slug(self) -> None:
        post = _post(slug=PostSlug("custom-slug"))
        assert str(post.slug) == "custom-slug"

    def test_generates_an_excerpt_from_the_body(self) -> None:
        post = _post(body="A short body for excerpt generation.")
        assert str(post.excerpt) == "A short body for excerpt generation."

    def test_accepts_an_explicit_excerpt(self) -> None:
        excerpt = PostExcerpt("Custom excerpt text.")
        post = _post(excerpt=excerpt)
        assert post.excerpt == excerpt

    def test_blank_body_raises(self) -> None:
        try:
            _post(body="   ")
            raised = False
        except PostBodyRequiredError:
            raised = True
        assert raised is True

    def test_computes_read_time_from_body(self) -> None:
        post = _post(body="word " * 400)  # 400 words / 200 wpm = 2 minutes
        assert post.read_time_minutes == 2

    def test_read_time_minimum_is_one(self) -> None:
        post = _post(body="Short.")
        assert post.read_time_minutes == 1

    def test_defaults_to_not_anonymous(self) -> None:
        post = _post()
        assert post.is_anonymous is False

    def test_accepts_is_anonymous(self) -> None:
        post = _post(is_anonymous=True)
        assert post.is_anonymous is True

    def test_defaults_to_not_pinned_locked_or_featured(self) -> None:
        post = _post()
        assert post.is_pinned is False
        assert post.is_locked is False
        assert post.is_featured is False

    def test_defaults_counters_to_zero(self) -> None:
        post = _post()
        assert post.view_count == 0
        assert post.bookmark_count == 0
        assert post.share_count == 0

    def test_defaults_featured_image_to_none(self) -> None:
        post = _post()
        assert post.featured_image_document_id is None

    def test_accepts_featured_image_document_id(self) -> None:
        document_id = uuid4()
        post = _post(featured_image_document_id=document_id)
        assert post.featured_image_document_id == document_id

    def test_defaults_published_at_to_none(self) -> None:
        post = _post()
        assert post.published_at is None

    def test_updated_by_defaults_to_author_id(self) -> None:
        author_id = uuid4()
        post = _post(author_id=author_id)
        assert post.updated_by == author_id

    def test_assigns_a_unique_id(self) -> None:
        first = _post()
        second = _post()
        assert first.id != second.id

    def test_records_a_community_post_created_event(self) -> None:
        author_id = uuid4()
        community_id = uuid4()
        post = _post(author_id=author_id, community_id=community_id, title=PostTitle("Hello"))
        events = post.pull_events()
        assert len(events) == 1
        event = events[0]
        assert isinstance(event, CommunityPostCreated)
        assert event.post_id == post.id
        assert event.community_id == community_id
        assert event.author_id == author_id
        assert event.title == "Hello"

    def test_pull_events_drains_the_queue(self) -> None:
        post = _post()
        post.pull_events()
        assert post.pull_events() == []


class TestCommunityPostUpdateContent:
    def test_updates_the_title(self) -> None:
        post = _post()
        new_title = PostTitle("New Title")
        post.update_content(title=new_title)
        assert post.title == new_title

    def test_updates_the_body_and_recomputes_read_time(self) -> None:
        post = _post(body="short body")
        post.update_content(body="word " * 400)
        assert post.read_time_minutes == 2

    def test_blank_body_raises(self) -> None:
        post = _post()
        try:
            post.update_content(body="   ")
            raised = False
        except PostBodyRequiredError:
            raised = True
        assert raised is True

    def test_editing_body_leaves_existing_excerpt_unchanged(self) -> None:
        original_excerpt = PostExcerpt("Hand-written excerpt.")
        post = _post(excerpt=original_excerpt)
        post.update_content(body="A completely different body now.")
        assert post.excerpt == original_excerpt

    def test_regenerate_excerpt_true_rederives_from_new_body(self) -> None:
        post = _post(excerpt=PostExcerpt("Old excerpt."))
        post.update_content(body="A brand new body for the post.", regenerate_excerpt=True)
        assert str(post.excerpt) == "A brand new body for the post."

    def test_explicit_excerpt_overrides_regenerate_flag(self) -> None:
        explicit = PostExcerpt("Explicit excerpt.")
        post = _post()
        post.update_content(body="New body content.", excerpt=explicit, regenerate_excerpt=True)
        assert post.excerpt == explicit

    def test_updates_post_type(self) -> None:
        post = _post()
        post.update_content(post_type=PostType.RESEARCH)
        assert post.post_type is PostType.RESEARCH

    def test_updates_visibility(self) -> None:
        post = _post()
        post.update_content(visibility=PostVisibility.PRIVATE)
        assert post.visibility is PostVisibility.PRIVATE

    def test_updates_is_anonymous(self) -> None:
        post = _post()
        post.update_content(is_anonymous=True)
        assert post.is_anonymous is True

    def test_updates_featured_image(self) -> None:
        post = _post()
        document_id = uuid4()
        post.update_content(featured_image_document_id=document_id)
        assert post.featured_image_document_id == document_id

    def test_clear_featured_image_removes_it(self) -> None:
        post = _post(featured_image_document_id=uuid4())
        post.update_content(clear_featured_image=True)
        assert post.featured_image_document_id is None

    def test_clear_featured_image_takes_precedence(self) -> None:
        post = _post()
        post.update_content(featured_image_document_id=uuid4(), clear_featured_image=True)
        assert post.featured_image_document_id is None

    def test_no_arguments_leaves_fields_unchanged(self) -> None:
        post = _post()
        original_title = post.title
        post.update_content()
        assert post.title == original_title

    def test_updates_updated_by(self) -> None:
        post = _post()
        updater_id = uuid4()
        post.update_content(updated_by=updater_id)
        assert post.updated_by == updater_id

    def test_updates_updated_at_timestamp(self) -> None:
        post = _post()
        before = post.updated_at
        post.update_content(title=PostTitle("New Title"))
        assert post.updated_at >= before

    def test_records_a_community_post_updated_event(self) -> None:
        post = _post()
        post.pull_events()
        post.update_content(title=PostTitle("New Title"))
        events = post.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], CommunityPostUpdated)
        assert events[0].post_id == post.id


class TestCommunityPostPublish:
    def test_sets_status_to_published(self) -> None:
        post = _post()
        post.publish()
        assert post.status is PostStatus.PUBLISHED

    def test_sets_published_at(self) -> None:
        post = _post()
        post.publish()
        assert post.published_at is not None

    def test_already_published_raises(self) -> None:
        post = _post()
        post.publish()
        try:
            post.publish()
            raised = False
        except PostAlreadyPublishedError:
            raised = True
        assert raised is True

    def test_records_a_community_post_published_event(self) -> None:
        community_id = uuid4()
        post = _post(community_id=community_id)
        post.pull_events()
        post.publish()
        events = post.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], CommunityPostPublished)
        assert events[0].post_id == post.id
        assert events[0].community_id == community_id

    def test_republishing_an_archived_post_succeeds(self) -> None:
        post = _post()
        post.publish()
        post.archive()
        post.publish()
        assert post.status is PostStatus.PUBLISHED


class TestCommunityPostArchive:
    def test_sets_status_to_archived(self) -> None:
        post = _post()
        post.archive()
        assert post.status is PostStatus.ARCHIVED

    def test_already_archived_raises(self) -> None:
        post = _post()
        post.archive()
        try:
            post.archive()
            raised = False
        except PostAlreadyArchivedError:
            raised = True
        assert raised is True

    def test_records_a_community_post_archived_event(self) -> None:
        post = _post()
        post.pull_events()
        post.archive()
        events = post.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], CommunityPostArchived)
        assert events[0].post_id == post.id

    def test_archiving_a_draft_post_succeeds(self) -> None:
        post = _post()
        post.archive()
        assert post.status is PostStatus.ARCHIVED


class TestCommunityPostSetPinned:
    def test_sets_pinned_true(self) -> None:
        post = _post()
        post.set_pinned(True)
        assert post.is_pinned is True

    def test_sets_pinned_false(self) -> None:
        post = _post()
        post.set_pinned(True)
        post.set_pinned(False)
        assert post.is_pinned is False

    def test_records_a_community_post_pinned_changed_event(self) -> None:
        post = _post()
        post.pull_events()
        post.set_pinned(True)
        events = post.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], CommunityPostPinnedChanged)
        assert events[0].is_pinned is True

    def test_setting_the_same_value_is_a_no_op(self) -> None:
        post = _post()
        post.pull_events()
        post.set_pinned(False)
        assert post.pull_events() == []


class TestCommunityPostSetLocked:
    def test_sets_locked_true(self) -> None:
        post = _post()
        post.set_locked(True)
        assert post.is_locked is True

    def test_records_a_community_post_locked_changed_event(self) -> None:
        post = _post()
        post.pull_events()
        post.set_locked(True)
        events = post.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], CommunityPostLockedChanged)
        assert events[0].is_locked is True

    def test_setting_the_same_value_is_a_no_op(self) -> None:
        post = _post()
        post.pull_events()
        post.set_locked(False)
        assert post.pull_events() == []


class TestCommunityPostSetFeatured:
    def test_sets_featured_true(self) -> None:
        post = _post()
        post.set_featured(True)
        assert post.is_featured is True

    def test_records_a_community_post_featured_changed_event(self) -> None:
        post = _post()
        post.pull_events()
        post.set_featured(True)
        events = post.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], CommunityPostFeaturedChanged)
        assert events[0].is_featured is True

    def test_setting_the_same_value_is_a_no_op(self) -> None:
        post = _post()
        post.pull_events()
        post.set_featured(False)
        assert post.pull_events() == []
