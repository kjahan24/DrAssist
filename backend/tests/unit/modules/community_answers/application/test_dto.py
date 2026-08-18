"""Unit tests for the Community Answers module's application-layer
DTOs — construction, defaults, the `.id` alias properties, and
`CommunityAnswerSummaryDTO.author_id`'s optional (anonymous-maskable)
shape."""

from dataclasses import FrozenInstanceError
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from app.modules.community_answers.application.dto import (
    AddAnswerAttachmentInput,
    AnswerAttachmentSummaryDTO,
    AnswerFeedOutput,
    AnswerRevisionSummaryDTO,
    ArchiveAnswerInput,
    CommunityAnswerSummaryDTO,
    CreateAnswerInput,
    CreateAnswerOutput,
    DeleteAnswerInput,
    ListAnswersInput,
    ListAnswersOutput,
    ListAuthorAnswersInput,
    ListQuestionAnswersInput,
    MarkBestAnswerInput,
    PublishAnswerInput,
    RemoveAnswerAttachmentInput,
    RemoveBestAnswerInput,
    RestoreAnswerInput,
    SearchAnswersInput,
    SearchAnswersOutput,
    SetAnswerFeaturedInput,
    SetAnswerPinnedInput,
    UpdateAnswerInput,
    UpdateAnswerOutput,
)
from app.modules.community_answers.domain.enums import AnswerStatus, AnswerVisibility


class TestCreateAnswerDTOs:
    def test_create_answer_input_defaults(self) -> None:
        dto = CreateAnswerInput(question_id=uuid4(), author_id=uuid4(), body="Body")
        assert dto.summary is None
        assert dto.visibility is AnswerVisibility.PUBLIC
        assert dto.is_anonymous is False

    def test_create_answer_output(self) -> None:
        answer_id, question_id = uuid4(), uuid4()
        dto = CreateAnswerOutput(
            answer_id=answer_id, question_id=question_id, status=AnswerStatus.DRAFT
        )
        assert dto.answer_id == answer_id
        assert dto.question_id == question_id
        assert dto.status is AnswerStatus.DRAFT


class TestUpdateAnswerDTOs:
    def test_update_answer_input_defaults(self) -> None:
        dto = UpdateAnswerInput(answer_id=uuid4(), acting_user_id=uuid4())
        assert dto.body is None
        assert dto.summary is None
        assert dto.regenerate_summary is False

    def test_update_answer_output(self) -> None:
        dto = UpdateAnswerOutput(
            answer_id=uuid4(), status=AnswerStatus.PUBLISHED, revision_number=2
        )
        assert dto.status is AnswerStatus.PUBLISHED
        assert dto.revision_number == 2


class TestSimpleActionInputs:
    def test_delete_answer_input(self) -> None:
        answer_id, user_id = uuid4(), uuid4()
        dto = DeleteAnswerInput(answer_id=answer_id, acting_user_id=user_id)
        assert dto.answer_id == answer_id
        assert dto.acting_user_id == user_id

    def test_publish_answer_input(self) -> None:
        dto = PublishAnswerInput(answer_id=uuid4(), acting_user_id=uuid4())
        assert isinstance(dto.answer_id, UUID)

    def test_archive_answer_input(self) -> None:
        dto = ArchiveAnswerInput(answer_id=uuid4(), acting_user_id=uuid4())
        assert isinstance(dto.answer_id, UUID)

    def test_restore_answer_input(self) -> None:
        dto = RestoreAnswerInput(answer_id=uuid4(), acting_user_id=uuid4())
        assert isinstance(dto.answer_id, UUID)

    def test_set_answer_featured_input(self) -> None:
        dto = SetAnswerFeaturedInput(answer_id=uuid4(), acting_user_id=uuid4(), featured=True)
        assert dto.featured is True

    def test_set_answer_pinned_input(self) -> None:
        dto = SetAnswerPinnedInput(answer_id=uuid4(), acting_user_id=uuid4(), pinned=True)
        assert dto.pinned is True


class TestBestAnswerDTOs:
    def test_mark_best_answer_input(self) -> None:
        question_id, answer_id, user_id = uuid4(), uuid4(), uuid4()
        dto = MarkBestAnswerInput(
            question_id=question_id, answer_id=answer_id, acting_user_id=user_id
        )
        assert dto.question_id == question_id
        assert dto.answer_id == answer_id
        assert dto.acting_user_id == user_id

    def test_remove_best_answer_input(self) -> None:
        question_id, answer_id, user_id = uuid4(), uuid4(), uuid4()
        dto = RemoveBestAnswerInput(
            question_id=question_id, answer_id=answer_id, acting_user_id=user_id
        )
        assert dto.question_id == question_id
        assert dto.answer_id == answer_id


class TestCommunityAnswerSummaryDTO:
    def _make(self, **overrides: object) -> CommunityAnswerSummaryDTO:
        now = datetime.now(UTC)
        defaults: dict[str, object] = {
            "answer_id": uuid4(),
            "question_id": uuid4(),
            "community_id": uuid4(),
            "organization_id": uuid4(),
            "topic_id": uuid4(),
            "body": "Body",
            "summary": "Summary",
            "status": AnswerStatus.DRAFT,
            "visibility": AnswerVisibility.PUBLIC,
            "is_anonymous": False,
            "is_best_answer": False,
            "is_featured": False,
            "is_pinned": False,
            "view_count": 0,
            "share_count": 0,
            "revision_number": 1,
            "created_at": now,
            "updated_at": now,
        }
        defaults.update(overrides)
        return CommunityAnswerSummaryDTO(**defaults)  # type: ignore[arg-type]

    def test_id_alias_matches_answer_id(self) -> None:
        dto = self._make()
        assert dto.id == dto.answer_id

    def test_optional_fields_default_to_none(self) -> None:
        dto = self._make()
        assert dto.author_id is None
        assert dto.published_at is None
        assert dto.updated_by is None

    def test_is_immutable(self) -> None:
        dto = self._make()
        with pytest.raises(FrozenInstanceError):
            dto.body = "Changed"  # type: ignore[misc]

    def test_author_id_accepts_an_explicit_value_for_a_non_anonymous_answer(self) -> None:
        author_id = uuid4()
        dto = self._make(author_id=author_id, is_anonymous=False)
        assert dto.author_id == author_id

    def test_optional_fields_accept_explicit_values(self) -> None:
        updater_id = uuid4()
        now = datetime.now(UTC)
        dto = self._make(published_at=now, updated_by=updater_id)
        assert dto.published_at == now
        assert dto.updated_by == updater_id


class TestListAndSearchDTOs:
    def test_list_answers_input_defaults(self) -> None:
        org_id = uuid4()
        dto = ListAnswersInput(organization_id=org_id)
        assert dto.organization_id == org_id
        assert dto.question_id is None
        assert dto.best_answer_only is False
        assert dto.featured_only is False
        assert dto.pinned_only is False
        assert dto.sort_by == "created_at"
        assert dto.sort_order == "desc"
        assert dto.offset == 0
        assert dto.limit == 20

    def test_list_answers_input_accepts_all_filters(self) -> None:
        org_id, question_id, community_id, topic_id, author_id = (
            uuid4(),
            uuid4(),
            uuid4(),
            uuid4(),
            uuid4(),
        )
        now = datetime.now(UTC)
        dto = ListAnswersInput(
            organization_id=org_id,
            question_id=question_id,
            community_id=community_id,
            topic_id=topic_id,
            author_id=author_id,
            status=(AnswerStatus.PUBLISHED,),
            visibility=(AnswerVisibility.PRIVATE,),
            best_answer_only=True,
            featured_only=True,
            pinned_only=True,
            created_from=now,
            created_to=now,
            query="term",
            include_deleted=True,
            sort_by="view_count",
            sort_order="asc",
            offset=10,
            limit=5,
        )
        assert dto.question_id == question_id
        assert dto.community_id == community_id
        assert dto.topic_id == topic_id
        assert dto.author_id == author_id
        assert dto.best_answer_only is True
        assert dto.featured_only is True
        assert dto.pinned_only is True
        assert dto.include_deleted is True
        assert dto.sort_order == "asc"
        assert dto.offset == 10
        assert dto.limit == 5

    def test_list_answers_input_is_immutable(self) -> None:
        dto = ListAnswersInput(organization_id=uuid4())
        with pytest.raises(FrozenInstanceError):
            dto.limit = 99  # type: ignore[misc]

    def test_list_answers_output(self) -> None:
        dto = ListAnswersOutput(items=(), total=0)
        assert dto.items == ()
        assert dto.total == 0

    def test_search_answers_input_requires_query(self) -> None:
        org_id = uuid4()
        dto = SearchAnswersInput(organization_id=org_id, query="diabetes")
        assert dto.query == "diabetes"
        assert dto.offset == 0
        assert dto.limit == 20

    def test_search_answers_input_accepts_all_filters(self) -> None:
        org_id, question_id, community_id, topic_id, author_id = (
            uuid4(),
            uuid4(),
            uuid4(),
            uuid4(),
            uuid4(),
        )
        now = datetime.now(UTC)
        dto = SearchAnswersInput(
            organization_id=org_id,
            query="diabetes",
            question_id=question_id,
            community_id=community_id,
            topic_id=topic_id,
            author_id=author_id,
            status=(AnswerStatus.DRAFT,),
            visibility=(AnswerVisibility.MEMBERS_ONLY,),
            best_answer_only=True,
            featured_only=True,
            pinned_only=True,
            created_from=now,
            created_to=now,
            offset=5,
            limit=15,
        )
        assert dto.question_id == question_id
        assert dto.community_id == community_id
        assert dto.topic_id == topic_id
        assert dto.author_id == author_id
        assert dto.best_answer_only is True
        assert dto.offset == 5
        assert dto.limit == 15

    def test_search_answers_input_is_immutable(self) -> None:
        dto = SearchAnswersInput(organization_id=uuid4(), query="term")
        with pytest.raises(FrozenInstanceError):
            dto.query = "changed"  # type: ignore[misc]

    def test_search_answers_output(self) -> None:
        dto = SearchAnswersOutput(items=(), total=0)
        assert dto.total == 0


class TestFeedDTOs:
    def test_list_question_answers_input(self) -> None:
        org_id, question_id = uuid4(), uuid4()
        dto = ListQuestionAnswersInput(organization_id=org_id, question_id=question_id)
        assert dto.organization_id == org_id
        assert dto.question_id == question_id
        assert dto.cursor is None
        assert dto.limit == 20

    def test_list_author_answers_input(self) -> None:
        org_id, author_id = uuid4(), uuid4()
        dto = ListAuthorAnswersInput(organization_id=org_id, author_id=author_id)
        assert dto.organization_id == org_id
        assert dto.author_id == author_id

    def test_answer_feed_output_defaults(self) -> None:
        dto = AnswerFeedOutput(items=())
        assert dto.next_cursor is None


class TestAnswerRevisionDTO:
    def test_id_alias_matches_revision_id(self) -> None:
        revision_id = uuid4()
        dto = AnswerRevisionSummaryDTO(
            revision_id=revision_id,
            answer_id=uuid4(),
            revision_number=1,
            previous_body="Old body.",
            author_id=uuid4(),
            created_at=datetime.now(UTC),
        )
        assert dto.id == revision_id


class TestAnswerAttachmentDTOs:
    def test_id_alias_matches_attachment_id(self) -> None:
        attachment_id = uuid4()
        dto = AnswerAttachmentSummaryDTO(
            attachment_id=attachment_id, answer_id=uuid4(), document_id=uuid4()
        )
        assert dto.id == attachment_id

    def test_add_answer_attachment_input(self) -> None:
        document_id = uuid4()
        dto = AddAnswerAttachmentInput(
            answer_id=uuid4(), acting_user_id=uuid4(), document_id=document_id
        )
        assert dto.document_id == document_id

    def test_remove_answer_attachment_input(self) -> None:
        dto = RemoveAnswerAttachmentInput(
            answer_id=uuid4(), acting_user_id=uuid4(), attachment_id=uuid4()
        )
        assert isinstance(dto.attachment_id, UUID)
