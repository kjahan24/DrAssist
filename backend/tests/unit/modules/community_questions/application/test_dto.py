"""Unit tests for the Community Questions module's application-layer
DTOs — construction, defaults, and the `.id` alias properties."""

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from app.modules.community_questions.application.dto import (
    AddQuestionAttachmentInput,
    ArchiveQuestionInput,
    AssignQuestionTagInput,
    AssignQuestionTopicInput,
    BrowseAuthorQuestionsInput,
    BrowseCommunityQuestionsInput,
    BrowseTopicQuestionsInput,
    CloseQuestionInput,
    CommunityQuestionSummaryDTO,
    CreateQuestionInput,
    CreateQuestionOutput,
    DeleteQuestionInput,
    FollowQuestionInput,
    ListQuestionsInput,
    ListQuestionsOutput,
    PublishQuestionInput,
    QuestionAttachmentSummaryDTO,
    QuestionFeedOutput,
    QuestionFollowerSummaryDTO,
    QuestionTagSummaryDTO,
    QuestionTopicSummaryDTO,
    RemoveQuestionAttachmentInput,
    ReopenQuestionInput,
    SearchQuestionsInput,
    SearchQuestionsOutput,
    SetQuestionFeaturedInput,
    SetQuestionPinnedInput,
    UnassignQuestionTagInput,
    UnassignQuestionTopicInput,
    UnfollowQuestionInput,
    UpdateQuestionInput,
    UpdateQuestionOutput,
)
from app.modules.community_questions.domain.enums import (
    QuestionStatus,
    QuestionType,
    QuestionVisibility,
)


class TestCreateQuestionDTOs:
    def test_create_question_input_defaults(self) -> None:
        dto = CreateQuestionInput(
            community_id=uuid4(),
            author_id=uuid4(),
            primary_topic_id=uuid4(),
            title="Title",
            body="Body",
        )
        assert dto.slug is None
        assert dto.summary is None
        assert dto.question_type is QuestionType.GENERAL
        assert dto.visibility is QuestionVisibility.PUBLIC
        assert dto.is_anonymous is False
        assert dto.secondary_topic_ids == ()
        assert dto.tags == ()

    def test_create_question_output(self) -> None:
        question_id = uuid4()
        dto = CreateQuestionOutput(
            question_id=question_id,
            community_id=uuid4(),
            slug="title",
            title="Title",
            status=QuestionStatus.DRAFT,
        )
        assert dto.question_id == question_id
        assert dto.status is QuestionStatus.DRAFT


class TestUpdateQuestionDTOs:
    def test_update_question_input_defaults(self) -> None:
        dto = UpdateQuestionInput(question_id=uuid4(), acting_user_id=uuid4())
        assert dto.title is None
        assert dto.body is None
        assert dto.regenerate_summary is False

    def test_update_question_output(self) -> None:
        dto = UpdateQuestionOutput(
            question_id=uuid4(),
            title="Title",
            status=QuestionStatus.DRAFT,
            visibility=QuestionVisibility.PUBLIC,
        )
        assert dto.status is QuestionStatus.DRAFT


class TestSimpleActionInputs:
    def test_delete_question_input(self) -> None:
        question_id, user_id = uuid4(), uuid4()
        dto = DeleteQuestionInput(question_id=question_id, acting_user_id=user_id)
        assert dto.question_id == question_id
        assert dto.acting_user_id == user_id

    def test_publish_question_input(self) -> None:
        dto = PublishQuestionInput(question_id=uuid4(), acting_user_id=uuid4())
        assert isinstance(dto.question_id, UUID)

    def test_archive_question_input(self) -> None:
        dto = ArchiveQuestionInput(question_id=uuid4(), acting_user_id=uuid4())
        assert isinstance(dto.question_id, UUID)

    def test_close_question_input(self) -> None:
        dto = CloseQuestionInput(question_id=uuid4(), acting_user_id=uuid4())
        assert isinstance(dto.question_id, UUID)

    def test_reopen_question_input(self) -> None:
        dto = ReopenQuestionInput(question_id=uuid4(), acting_user_id=uuid4())
        assert isinstance(dto.question_id, UUID)

    def test_set_question_pinned_input(self) -> None:
        dto = SetQuestionPinnedInput(question_id=uuid4(), acting_user_id=uuid4(), pinned=True)
        assert dto.pinned is True

    def test_set_question_featured_input(self) -> None:
        dto = SetQuestionFeaturedInput(question_id=uuid4(), acting_user_id=uuid4(), featured=True)
        assert dto.featured is True

    def test_follow_question_input(self) -> None:
        dto = FollowQuestionInput(question_id=uuid4(), acting_user_id=uuid4())
        assert isinstance(dto.question_id, UUID)

    def test_unfollow_question_input(self) -> None:
        dto = UnfollowQuestionInput(question_id=uuid4(), acting_user_id=uuid4())
        assert isinstance(dto.question_id, UUID)


class TestCommunityQuestionSummaryDTO:
    def _make(self, **overrides: object) -> CommunityQuestionSummaryDTO:
        now = datetime.now(UTC)
        defaults: dict[str, object] = {
            "question_id": uuid4(),
            "community_id": uuid4(),
            "organization_id": uuid4(),
            "author_id": uuid4(),
            "primary_topic_id": uuid4(),
            "slug": "title",
            "title": "Title",
            "body": "Body",
            "summary": "Summary",
            "question_type": QuestionType.GENERAL,
            "status": QuestionStatus.DRAFT,
            "visibility": QuestionVisibility.PUBLIC,
            "is_anonymous": False,
            "is_pinned": False,
            "is_featured": False,
            "read_time_minutes": 1,
            "view_count": 0,
            "follower_count": 0,
            "bookmark_count": 0,
            "share_count": 0,
            "created_at": now,
            "updated_at": now,
        }
        defaults.update(overrides)
        return CommunityQuestionSummaryDTO(**defaults)  # type: ignore[arg-type]

    def test_id_alias_matches_question_id(self) -> None:
        dto = self._make()
        assert dto.id == dto.question_id

    def test_optional_fields_default_to_none(self) -> None:
        dto = self._make()
        assert dto.accepted_answer_id is None
        assert dto.published_at is None
        assert dto.updated_by is None

    def test_is_immutable(self) -> None:
        dto = self._make()
        with pytest.raises(FrozenInstanceError):
            dto.title = "Changed"  # type: ignore[misc]

    def test_optional_fields_accept_explicit_values(self) -> None:
        answer_id, updater_id = uuid4(), uuid4()
        now = datetime.now(UTC)
        dto = self._make(accepted_answer_id=answer_id, published_at=now, updated_by=updater_id)
        assert dto.accepted_answer_id == answer_id
        assert dto.published_at == now
        assert dto.updated_by == updater_id


class TestListAndSearchDTOs:
    def test_list_questions_input_defaults(self) -> None:
        org_id = uuid4()
        dto = ListQuestionsInput(organization_id=org_id)
        assert dto.organization_id == org_id
        assert dto.community_id is None
        assert dto.pinned_only is False
        assert dto.featured_only is False
        assert dto.sort_by == "created_at"
        assert dto.sort_order == "desc"
        assert dto.offset == 0
        assert dto.limit == 20

    def test_list_questions_input_accepts_all_filters(self) -> None:
        org_id, community_id, topic_id, author_id = uuid4(), uuid4(), uuid4(), uuid4()
        now = datetime.now(UTC)
        dto = ListQuestionsInput(
            organization_id=org_id,
            community_id=community_id,
            topic_id=topic_id,
            author_id=author_id,
            question_type=(QuestionType.CLINICAL,),
            status=(QuestionStatus.PUBLISHED,),
            visibility=(QuestionVisibility.PRIVATE,),
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

    def test_list_questions_input_is_immutable(self) -> None:
        dto = ListQuestionsInput(organization_id=uuid4())
        with pytest.raises(FrozenInstanceError):
            dto.limit = 99  # type: ignore[misc]

    def test_list_questions_output(self) -> None:
        dto = ListQuestionsOutput(items=(), total=0)
        assert dto.items == ()
        assert dto.total == 0

    def test_search_questions_input_requires_query(self) -> None:
        org_id = uuid4()
        dto = SearchQuestionsInput(organization_id=org_id, query="diabetes")
        assert dto.query == "diabetes"
        assert dto.offset == 0
        assert dto.limit == 20

    def test_search_questions_input_accepts_all_filters(self) -> None:
        org_id, community_id, topic_id, author_id = uuid4(), uuid4(), uuid4(), uuid4()
        now = datetime.now(UTC)
        dto = SearchQuestionsInput(
            organization_id=org_id,
            query="diabetes",
            community_id=community_id,
            topic_id=topic_id,
            author_id=author_id,
            question_type=(QuestionType.RESEARCH_QUESTION,),
            status=(QuestionStatus.DRAFT,),
            visibility=(QuestionVisibility.MEMBERS_ONLY,),
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

    def test_search_questions_input_is_immutable(self) -> None:
        dto = SearchQuestionsInput(organization_id=uuid4(), query="term")
        with pytest.raises(FrozenInstanceError):
            dto.query = "changed"  # type: ignore[misc]

    def test_search_questions_output(self) -> None:
        dto = SearchQuestionsOutput(items=(), total=0)
        assert dto.total == 0


class TestBrowseFeedDTOs:
    def test_browse_community_questions_input_has_no_organization_id_field(self) -> None:
        community_id = uuid4()
        dto = BrowseCommunityQuestionsInput(community_id=community_id)
        assert not hasattr(dto, "organization_id")
        assert dto.cursor is None
        assert dto.limit == 20

    def test_browse_topic_questions_input(self) -> None:
        org_id, topic_id = uuid4(), uuid4()
        dto = BrowseTopicQuestionsInput(organization_id=org_id, topic_id=topic_id)
        assert dto.organization_id == org_id
        assert dto.topic_id == topic_id

    def test_browse_author_questions_input(self) -> None:
        org_id, author_id = uuid4(), uuid4()
        dto = BrowseAuthorQuestionsInput(organization_id=org_id, author_id=author_id)
        assert dto.organization_id == org_id
        assert dto.author_id == author_id

    def test_question_feed_output_defaults(self) -> None:
        dto = QuestionFeedOutput(items=())
        assert dto.next_cursor is None


class TestQuestionTopicDTOs:
    def test_question_topic_summary_id_alias(self) -> None:
        question_topic_id = uuid4()
        dto = QuestionTopicSummaryDTO(
            question_topic_id=question_topic_id, question_id=uuid4(), topic_id=uuid4()
        )
        assert dto.id == question_topic_id

    def test_assign_question_topic_input(self) -> None:
        question_id, user_id, topic_id = uuid4(), uuid4(), uuid4()
        dto = AssignQuestionTopicInput(
            question_id=question_id, acting_user_id=user_id, topic_id=topic_id
        )
        assert dto.topic_id == topic_id

    def test_unassign_question_topic_input(self) -> None:
        dto = UnassignQuestionTopicInput(
            question_id=uuid4(), acting_user_id=uuid4(), question_topic_id=uuid4()
        )
        assert isinstance(dto.question_topic_id, UUID)


class TestQuestionTagDTOs:
    def test_question_tag_summary_id_alias(self) -> None:
        question_tag_id = uuid4()
        dto = QuestionTagSummaryDTO(
            question_tag_id=question_tag_id, question_id=uuid4(), tag="oncology"
        )
        assert dto.id == question_tag_id

    def test_assign_question_tag_input(self) -> None:
        dto = AssignQuestionTagInput(question_id=uuid4(), acting_user_id=uuid4(), tag="oncology")
        assert dto.tag == "oncology"

    def test_unassign_question_tag_input(self) -> None:
        dto = UnassignQuestionTagInput(
            question_id=uuid4(), acting_user_id=uuid4(), question_tag_id=uuid4()
        )
        assert isinstance(dto.question_tag_id, UUID)


class TestQuestionAttachmentDTOs:
    def test_question_attachment_summary_id_alias(self) -> None:
        attachment_id = uuid4()
        dto = QuestionAttachmentSummaryDTO(
            attachment_id=attachment_id, question_id=uuid4(), document_id=uuid4()
        )
        assert dto.id == attachment_id

    def test_add_question_attachment_input(self) -> None:
        document_id = uuid4()
        dto = AddQuestionAttachmentInput(
            question_id=uuid4(), acting_user_id=uuid4(), document_id=document_id
        )
        assert dto.document_id == document_id

    def test_remove_question_attachment_input(self) -> None:
        dto = RemoveQuestionAttachmentInput(
            question_id=uuid4(), acting_user_id=uuid4(), attachment_id=uuid4()
        )
        assert isinstance(dto.attachment_id, UUID)


class TestQuestionFollowerDTOs:
    def test_question_follower_summary_id_alias(self) -> None:
        follower_id = uuid4()
        dto = QuestionFollowerSummaryDTO(
            follower_id=follower_id, question_id=uuid4(), user_id=uuid4()
        )
        assert dto.id == follower_id
