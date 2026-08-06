"""Unit tests for the Community Posts module's application-layer DTOs —
construction, defaults, and the `.id` alias properties."""

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from app.modules.community_posts.application.dto import (
    AddPostAttachmentInput,
    ArchivePostInput,
    AssignPostTagInput,
    AssignPostTopicInput,
    BrowseAuthorPostsInput,
    BrowseCommunityFeedInput,
    BrowseTopicFeedInput,
    CommunityPostSummaryDTO,
    CreatePostInput,
    CreatePostOutput,
    DeletePostInput,
    ListPostsInput,
    ListPostsOutput,
    PostAttachmentSummaryDTO,
    PostFeedOutput,
    PostTagSummaryDTO,
    PostTopicSummaryDTO,
    PublishPostInput,
    RemovePostAttachmentInput,
    SearchPostsInput,
    SearchPostsOutput,
    SetPostFeaturedInput,
    SetPostLockedInput,
    SetPostPinnedInput,
    UnassignPostTagInput,
    UnassignPostTopicInput,
    UpdatePostInput,
    UpdatePostOutput,
)
from app.modules.community_posts.domain.enums import PostStatus, PostType, PostVisibility


class TestCreatePostDTOs:
    def test_create_post_input_defaults(self) -> None:
        dto = CreatePostInput(community_id=uuid4(), author_id=uuid4(), title="Title", body="Body")
        assert dto.slug is None
        assert dto.excerpt is None
        assert dto.post_type is PostType.DISCUSSION
        assert dto.visibility is PostVisibility.PUBLIC
        assert dto.is_anonymous is False
        assert dto.featured_image_document_id is None
        assert dto.topic_ids == ()
        assert dto.tags == ()

    def test_create_post_output(self) -> None:
        post_id = uuid4()
        dto = CreatePostOutput(
            post_id=post_id,
            community_id=uuid4(),
            slug="title",
            title="Title",
            status=PostStatus.DRAFT,
        )
        assert dto.post_id == post_id
        assert dto.status is PostStatus.DRAFT


class TestUpdatePostDTOs:
    def test_update_post_input_defaults(self) -> None:
        dto = UpdatePostInput(post_id=uuid4(), acting_user_id=uuid4())
        assert dto.title is None
        assert dto.body is None
        assert dto.regenerate_excerpt is False
        assert dto.clear_featured_image is False

    def test_update_post_output(self) -> None:
        dto = UpdatePostOutput(
            post_id=uuid4(),
            title="Title",
            status=PostStatus.DRAFT,
            visibility=PostVisibility.PUBLIC,
        )
        assert dto.status is PostStatus.DRAFT


class TestSimpleActionInputs:
    def test_delete_post_input(self) -> None:
        post_id, user_id = uuid4(), uuid4()
        dto = DeletePostInput(post_id=post_id, acting_user_id=user_id)
        assert dto.post_id == post_id
        assert dto.acting_user_id == user_id

    def test_publish_post_input(self) -> None:
        dto = PublishPostInput(post_id=uuid4(), acting_user_id=uuid4())
        assert isinstance(dto.post_id, UUID)

    def test_archive_post_input(self) -> None:
        dto = ArchivePostInput(post_id=uuid4(), acting_user_id=uuid4())
        assert isinstance(dto.post_id, UUID)

    def test_set_post_pinned_input(self) -> None:
        dto = SetPostPinnedInput(post_id=uuid4(), acting_user_id=uuid4(), pinned=True)
        assert dto.pinned is True

    def test_set_post_locked_input(self) -> None:
        dto = SetPostLockedInput(post_id=uuid4(), acting_user_id=uuid4(), locked=True)
        assert dto.locked is True

    def test_set_post_featured_input(self) -> None:
        dto = SetPostFeaturedInput(post_id=uuid4(), acting_user_id=uuid4(), featured=True)
        assert dto.featured is True


class TestCommunityPostSummaryDTO:
    def _make(self, **overrides: object) -> CommunityPostSummaryDTO:
        now = datetime.now(UTC)
        defaults: dict[str, object] = {
            "post_id": uuid4(),
            "community_id": uuid4(),
            "organization_id": uuid4(),
            "author_id": uuid4(),
            "slug": "title",
            "title": "Title",
            "body": "Body",
            "excerpt": "Excerpt",
            "post_type": PostType.DISCUSSION,
            "status": PostStatus.DRAFT,
            "visibility": PostVisibility.PUBLIC,
            "is_anonymous": False,
            "is_pinned": False,
            "is_locked": False,
            "is_featured": False,
            "read_time_minutes": 1,
            "view_count": 0,
            "bookmark_count": 0,
            "share_count": 0,
            "created_at": now,
            "updated_at": now,
        }
        defaults.update(overrides)
        return CommunityPostSummaryDTO(**defaults)  # type: ignore[arg-type]

    def test_id_alias_matches_post_id(self) -> None:
        dto = self._make()
        assert dto.id == dto.post_id

    def test_optional_fields_default_to_none(self) -> None:
        dto = self._make()
        assert dto.featured_image_document_id is None
        assert dto.published_at is None
        assert dto.updated_by is None

    def test_is_immutable(self) -> None:
        dto = self._make()
        with pytest.raises(FrozenInstanceError):
            dto.title = "Changed"  # type: ignore[misc]

    def test_optional_fields_accept_explicit_values(self) -> None:
        document_id, updater_id = uuid4(), uuid4()
        now = datetime.now(UTC)
        dto = self._make(
            featured_image_document_id=document_id, published_at=now, updated_by=updater_id
        )
        assert dto.featured_image_document_id == document_id
        assert dto.published_at == now
        assert dto.updated_by == updater_id


class TestListAndSearchDTOs:
    def test_list_posts_input_defaults(self) -> None:
        org_id = uuid4()
        dto = ListPostsInput(organization_id=org_id)
        assert dto.organization_id == org_id
        assert dto.community_id is None
        assert dto.pinned_only is False
        assert dto.featured_only is False
        assert dto.sort_by == "created_at"
        assert dto.sort_order == "desc"
        assert dto.offset == 0
        assert dto.limit == 20

    def test_list_posts_output(self) -> None:
        dto = ListPostsOutput(items=(), total=0)
        assert dto.items == ()
        assert dto.total == 0

    def test_list_posts_input_accepts_all_filters(self) -> None:
        org_id, community_id, topic_id, author_id = uuid4(), uuid4(), uuid4(), uuid4()
        now = datetime.now(UTC)
        dto = ListPostsInput(
            organization_id=org_id,
            community_id=community_id,
            topic_id=topic_id,
            author_id=author_id,
            post_type=(PostType.CLINICAL_CASE,),
            status=(PostStatus.PUBLISHED,),
            visibility=(PostVisibility.PRIVATE,),
            pinned_only=True,
            featured_only=True,
            created_from=now,
            created_to=now,
            query="term",
            include_deleted=True,
            sort_by="title",
            sort_order="asc",
            offset=10,
            limit=5,
        )
        assert dto.community_id == community_id
        assert dto.topic_id == topic_id
        assert dto.author_id == author_id
        assert dto.pinned_only is True
        assert dto.featured_only is True
        assert dto.include_deleted is True
        assert dto.sort_order == "asc"
        assert dto.offset == 10
        assert dto.limit == 5

    def test_list_posts_input_is_immutable(self) -> None:
        dto = ListPostsInput(organization_id=uuid4())
        with pytest.raises(FrozenInstanceError):
            dto.limit = 99  # type: ignore[misc]

    def test_search_posts_input_requires_query(self) -> None:
        org_id = uuid4()
        dto = SearchPostsInput(organization_id=org_id, query="diabetes")
        assert dto.query == "diabetes"
        assert dto.offset == 0
        assert dto.limit == 20

    def test_search_posts_input_accepts_all_filters(self) -> None:
        org_id, community_id, topic_id, author_id = uuid4(), uuid4(), uuid4(), uuid4()
        now = datetime.now(UTC)
        dto = SearchPostsInput(
            organization_id=org_id,
            query="diabetes",
            community_id=community_id,
            topic_id=topic_id,
            author_id=author_id,
            post_type=(PostType.RESEARCH,),
            status=(PostStatus.DRAFT,),
            visibility=(PostVisibility.MEMBERS_ONLY,),
            pinned_only=True,
            featured_only=True,
            created_from=now,
            created_to=now,
            offset=5,
            limit=15,
        )
        assert dto.community_id == community_id
        assert dto.topic_id == topic_id
        assert dto.author_id == author_id
        assert dto.pinned_only is True
        assert dto.featured_only is True
        assert dto.offset == 5
        assert dto.limit == 15

    def test_search_posts_input_is_immutable(self) -> None:
        dto = SearchPostsInput(organization_id=uuid4(), query="term")
        with pytest.raises(FrozenInstanceError):
            dto.query = "changed"  # type: ignore[misc]

    def test_search_posts_output(self) -> None:
        dto = SearchPostsOutput(items=(), total=0)
        assert dto.total == 0


class TestBrowseFeedDTOs:
    def test_browse_community_feed_input_has_no_organization_id_field(self) -> None:
        community_id = uuid4()
        dto = BrowseCommunityFeedInput(community_id=community_id)
        assert not hasattr(dto, "organization_id")
        assert dto.cursor is None
        assert dto.limit == 20

    def test_browse_topic_feed_input(self) -> None:
        org_id, topic_id = uuid4(), uuid4()
        dto = BrowseTopicFeedInput(organization_id=org_id, topic_id=topic_id)
        assert dto.organization_id == org_id
        assert dto.topic_id == topic_id

    def test_browse_author_posts_input(self) -> None:
        org_id, author_id = uuid4(), uuid4()
        dto = BrowseAuthorPostsInput(organization_id=org_id, author_id=author_id)
        assert dto.organization_id == org_id
        assert dto.author_id == author_id

    def test_post_feed_output_defaults(self) -> None:
        dto = PostFeedOutput(items=())
        assert dto.next_cursor is None


class TestPostTopicDTOs:
    def test_post_topic_summary_id_alias(self) -> None:
        post_topic_id = uuid4()
        dto = PostTopicSummaryDTO(post_topic_id=post_topic_id, post_id=uuid4(), topic_id=uuid4())
        assert dto.id == post_topic_id

    def test_assign_post_topic_input(self) -> None:
        post_id, user_id, topic_id = uuid4(), uuid4(), uuid4()
        dto = AssignPostTopicInput(post_id=post_id, acting_user_id=user_id, topic_id=topic_id)
        assert dto.topic_id == topic_id

    def test_unassign_post_topic_input(self) -> None:
        dto = UnassignPostTopicInput(post_id=uuid4(), acting_user_id=uuid4(), post_topic_id=uuid4())
        assert isinstance(dto.post_topic_id, UUID)


class TestPostTagDTOs:
    def test_post_tag_summary_id_alias(self) -> None:
        post_tag_id = uuid4()
        dto = PostTagSummaryDTO(post_tag_id=post_tag_id, post_id=uuid4(), tag="oncology")
        assert dto.id == post_tag_id

    def test_assign_post_tag_input(self) -> None:
        dto = AssignPostTagInput(post_id=uuid4(), acting_user_id=uuid4(), tag="oncology")
        assert dto.tag == "oncology"

    def test_unassign_post_tag_input(self) -> None:
        dto = UnassignPostTagInput(post_id=uuid4(), acting_user_id=uuid4(), post_tag_id=uuid4())
        assert isinstance(dto.post_tag_id, UUID)


class TestPostAttachmentDTOs:
    def test_post_attachment_summary_id_alias(self) -> None:
        attachment_id = uuid4()
        dto = PostAttachmentSummaryDTO(
            attachment_id=attachment_id, post_id=uuid4(), document_id=uuid4()
        )
        assert dto.id == attachment_id

    def test_add_post_attachment_input(self) -> None:
        document_id = uuid4()
        dto = AddPostAttachmentInput(
            post_id=uuid4(), acting_user_id=uuid4(), document_id=document_id
        )
        assert dto.document_id == document_id

    def test_remove_post_attachment_input(self) -> None:
        dto = RemovePostAttachmentInput(
            post_id=uuid4(), acting_user_id=uuid4(), attachment_id=uuid4()
        )
        assert isinstance(dto.attachment_id, UUID)
