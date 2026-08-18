"""Unit tests for `SearchCommentsService` — the general-purpose,
cursor-paginated, full-filter view (`query` optional, also backing the
"my drafts" management view)."""

from uuid import uuid4

from app.modules.community_comments.application.dto import SearchCommentsInput
from app.modules.community_comments.application.services.search_comments_service import (
    SearchCommentsService,
)
from app.modules.community_comments.domain.entities import CommunityComment
from app.modules.community_comments.domain.enums import CommentStatus, CommentTargetType
from app.modules.community_comments.domain.value_objects import CommentBody
from tests.unit.modules.community_comments.application.fakes import FakeCommunityCommentRepository


def _make_comment(**overrides: object) -> CommunityComment:
    defaults: dict[str, object] = {
        "target_type": CommentTargetType.POST,
        "target_id": uuid4(),
        "community_id": uuid4(),
        "organization_id": uuid4(),
        "topic_id": None,
        "author_id": uuid4(),
        "body": CommentBody("Body."),
    }
    defaults.update(overrides)
    return CommunityComment.create(**defaults)  # type: ignore[arg-type]


class TestSearchComments:
    async def test_finds_a_match_in_the_body(self) -> None:
        comments = FakeCommunityCommentRepository()
        service = SearchCommentsService(comment_repository=comments)
        org_id = uuid4()
        matching = _make_comment(organization_id=org_id, body=CommentBody("Hypertension advice."))
        other = _make_comment(organization_id=org_id, body=CommentBody("Something unrelated."))
        await comments.add(matching)
        await comments.add(other)

        result = await service.search(
            SearchCommentsInput(organization_id=org_id, query="hypertension")
        )
        assert [i.comment_id for i in result.items] == [matching.id]

    async def test_query_is_optional(self) -> None:
        comments = FakeCommunityCommentRepository()
        service = SearchCommentsService(comment_repository=comments)
        org_id = uuid4()
        await comments.add(_make_comment(organization_id=org_id))

        result = await service.search(SearchCommentsInput(organization_id=org_id))
        assert len(result.items) == 1

    async def test_backs_a_my_drafts_view_via_author_and_status_filters(self) -> None:
        comments = FakeCommunityCommentRepository()
        service = SearchCommentsService(comment_repository=comments)
        org_id, author_id = uuid4(), uuid4()
        my_draft = _make_comment(organization_id=org_id, author_id=author_id)
        my_published = _make_comment(organization_id=org_id, author_id=author_id)
        my_published.publish()
        someone_elses_draft = _make_comment(organization_id=org_id)
        await comments.add(my_draft)
        await comments.add(my_published)
        await comments.add(someone_elses_draft)

        result = await service.search(
            SearchCommentsInput(
                organization_id=org_id, author_id=author_id, status=(CommentStatus.DRAFT,)
            )
        )
        assert [i.comment_id for i in result.items] == [my_draft.id]

    async def test_filters_by_target(self) -> None:
        comments = FakeCommunityCommentRepository()
        service = SearchCommentsService(comment_repository=comments)
        org_id, target_id = uuid4(), uuid4()
        matching = _make_comment(
            organization_id=org_id, target_type=CommentTargetType.ANSWER, target_id=target_id
        )
        other = _make_comment(organization_id=org_id)
        await comments.add(matching)
        await comments.add(other)

        result = await service.search(
            SearchCommentsInput(
                organization_id=org_id, target_type=CommentTargetType.ANSWER, target_id=target_id
            )
        )
        assert [i.comment_id for i in result.items] == [matching.id]

    async def test_top_level_only_excludes_replies(self) -> None:
        comments = FakeCommunityCommentRepository()
        service = SearchCommentsService(comment_repository=comments)
        org_id = uuid4()
        parent = _make_comment(organization_id=org_id)
        reply = CommunityComment.create_reply(
            parent=parent, author_id=uuid4(), body=CommentBody("Reply.")
        )
        await comments.add(parent)
        await comments.add(reply)

        result = await service.search(
            SearchCommentsInput(organization_id=org_id, top_level_only=True)
        )
        assert [i.comment_id for i in result.items] == [parent.id]

    async def test_excludes_deleted_comments_by_default(self) -> None:
        comments = FakeCommunityCommentRepository()
        service = SearchCommentsService(comment_repository=comments)
        org_id = uuid4()
        deleted = _make_comment(organization_id=org_id)
        deleted.delete()
        live = _make_comment(organization_id=org_id)
        await comments.add(deleted)
        await comments.add(live)

        result = await service.search(SearchCommentsInput(organization_id=org_id))
        assert deleted.id not in [i.comment_id for i in result.items]

    async def test_include_deleted_true_includes_deleted_comments(self) -> None:
        comments = FakeCommunityCommentRepository()
        service = SearchCommentsService(comment_repository=comments)
        org_id = uuid4()
        deleted = _make_comment(organization_id=org_id)
        deleted.delete()
        await comments.add(deleted)

        result = await service.search(
            SearchCommentsInput(organization_id=org_id, include_deleted=True)
        )
        assert deleted.id in [i.comment_id for i in result.items]

    async def test_returns_a_next_cursor_when_more_results_remain(self) -> None:
        comments = FakeCommunityCommentRepository()
        service = SearchCommentsService(comment_repository=comments)
        org_id = uuid4()
        for _ in range(3):
            await comments.add(_make_comment(organization_id=org_id))

        result = await service.search(SearchCommentsInput(organization_id=org_id, limit=2))
        assert len(result.items) == 2
        assert result.next_cursor is not None

    async def test_sort_order_ascending_reverses_the_default_order(self) -> None:
        comments = FakeCommunityCommentRepository()
        service = SearchCommentsService(comment_repository=comments)
        org_id = uuid4()
        first = _make_comment(organization_id=org_id)
        second = _make_comment(organization_id=org_id)
        await comments.add(first)
        await comments.add(second)

        descending = await service.search(
            SearchCommentsInput(organization_id=org_id, sort_order="desc")
        )
        ascending = await service.search(
            SearchCommentsInput(organization_id=org_id, sort_order="asc")
        )
        assert [i.comment_id for i in ascending.items] == list(
            reversed([i.comment_id for i in descending.items])
        )
