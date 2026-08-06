"""Tests for the `CommunityPostTag` aggregate root."""

from uuid import uuid4

import pytest

from app.modules.community_posts.domain.entities import CommunityPostTag
from app.modules.community_posts.domain.events import CommunityPostTagAssigned
from app.modules.community_posts.domain.exceptions import PostTagRequiredError, PostTagTooLongError
from app.modules.community_posts.domain.value_objects import PostId


def _post_id() -> PostId:
    return PostId(uuid4())


class TestCommunityPostTagCreate:
    def test_sets_required_fields(self) -> None:
        post_id = _post_id()
        assignment = CommunityPostTag.create(post_id=post_id, tag="diabetes")
        assert assignment.post_id == post_id
        assert assignment.tag == "diabetes"

    def test_normalizes_to_lowercase(self) -> None:
        assignment = CommunityPostTag.create(post_id=_post_id(), tag="Diabetes")
        assert assignment.tag == "diabetes"

    def test_strips_surrounding_whitespace(self) -> None:
        assignment = CommunityPostTag.create(post_id=_post_id(), tag="  diabetes  ")
        assert assignment.tag == "diabetes"

    @pytest.mark.parametrize("raw", ["", "   "])
    def test_blank_tag_raises(self, raw: str) -> None:
        with pytest.raises(PostTagRequiredError):
            CommunityPostTag.create(post_id=_post_id(), tag=raw)

    def test_tag_over_max_length_raises(self) -> None:
        with pytest.raises(PostTagTooLongError):
            CommunityPostTag.create(post_id=_post_id(), tag="a" * 51)

    def test_tag_at_max_length_boundary_is_valid(self) -> None:
        tag = "a" * 50
        assignment = CommunityPostTag.create(post_id=_post_id(), tag=tag)
        assert assignment.tag == tag

    def test_assigns_a_unique_id(self) -> None:
        post_id = _post_id()
        first = CommunityPostTag.create(post_id=post_id, tag="diabetes")
        second = CommunityPostTag.create(post_id=post_id, tag="oncology")
        assert first.id != second.id

    def test_records_a_community_post_tag_assigned_event(self) -> None:
        post_id = _post_id()
        assignment = CommunityPostTag.create(post_id=post_id, tag="diabetes")
        events = assignment.pull_events()
        assert len(events) == 1
        event = events[0]
        assert isinstance(event, CommunityPostTagAssigned)
        assert event.post_tag_id == assignment.id
        assert event.post_id == post_id.value
        assert event.tag == "diabetes"

    def test_pull_events_drains_the_queue(self) -> None:
        assignment = CommunityPostTag.create(post_id=_post_id(), tag="diabetes")
        assignment.pull_events()
        assert assignment.pull_events() == []
