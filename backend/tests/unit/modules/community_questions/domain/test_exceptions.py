"""Tests for the Community Questions module's domain exceptions."""

from uuid import uuid4

from app.modules.community_questions.domain.exceptions import (
    CommunityNotFoundForQuestionError,
    DocumentNotFoundForQuestionError,
    DuplicateQuestionAttachmentError,
    DuplicateQuestionFollowerError,
    DuplicateQuestionSlugError,
    DuplicateQuestionTagError,
    DuplicateQuestionTopicError,
    InsufficientQuestionRoleError,
    InvalidQuestionSlugError,
    QuestionAlreadyArchivedError,
    QuestionAlreadyClosedError,
    QuestionAlreadyDeletedError,
    QuestionAlreadyPublishedError,
    QuestionAttachmentNotFoundError,
    QuestionBodyRequiredError,
    QuestionFollowerNotFoundError,
    QuestionMembershipRequiredError,
    QuestionNotClosedError,
    QuestionNotFoundError,
    QuestionNotViewableError,
    QuestionSummaryRequiredError,
    QuestionSummaryTooLongError,
    QuestionTagNotFoundError,
    QuestionTagRequiredError,
    QuestionTagTooLongError,
    QuestionTitleRequiredError,
    QuestionTitleTooLongError,
    QuestionTopicNotFoundError,
    TopicNotFoundForQuestionError,
)
from app.shared.domain.exceptions import DomainError


class TestQuestionTitleRequiredError:
    def test_is_a_domain_error(self) -> None:
        assert isinstance(QuestionTitleRequiredError(), DomainError)

    def test_message(self) -> None:
        assert "blank" in str(QuestionTitleRequiredError())


class TestQuestionTitleTooLongError:
    def test_is_a_domain_error(self) -> None:
        assert isinstance(QuestionTitleTooLongError(300), DomainError)

    def test_message_includes_max_length(self) -> None:
        error = QuestionTitleTooLongError(300)
        assert "300" in str(error)
        assert error.max_length == 300


class TestInvalidQuestionSlugError:
    def test_is_a_domain_error(self) -> None:
        assert isinstance(InvalidQuestionSlugError("bad slug"), DomainError)

    def test_message_includes_the_bad_value(self) -> None:
        error = InvalidQuestionSlugError("Bad Slug!")
        assert "Bad Slug!" in str(error)
        assert error.value == "Bad Slug!"


class TestDuplicateQuestionSlugError:
    def test_is_a_domain_error(self) -> None:
        assert isinstance(DuplicateQuestionSlugError(uuid4(), "hypertension-tips"), DomainError)

    def test_message_includes_community_id_and_slug(self) -> None:
        community_id = uuid4()
        error = DuplicateQuestionSlugError(community_id, "hypertension-tips")
        assert str(community_id) in str(error)
        assert "hypertension-tips" in str(error)
        assert error.slug == "hypertension-tips"


class TestQuestionSummaryRequiredError:
    def test_is_a_domain_error(self) -> None:
        assert isinstance(QuestionSummaryRequiredError(), DomainError)

    def test_message(self) -> None:
        assert "blank" in str(QuestionSummaryRequiredError())


class TestQuestionSummaryTooLongError:
    def test_is_a_domain_error(self) -> None:
        assert isinstance(QuestionSummaryTooLongError(500), DomainError)

    def test_message_includes_max_length(self) -> None:
        error = QuestionSummaryTooLongError(500)
        assert "500" in str(error)
        assert error.max_length == 500


class TestQuestionBodyRequiredError:
    def test_is_a_domain_error(self) -> None:
        assert isinstance(QuestionBodyRequiredError(), DomainError)

    def test_message(self) -> None:
        assert "blank" in str(QuestionBodyRequiredError())


class TestQuestionNotFoundError:
    def test_is_a_domain_error(self) -> None:
        assert isinstance(QuestionNotFoundError(uuid4()), DomainError)

    def test_message_includes_id(self) -> None:
        question_id = uuid4()
        error = QuestionNotFoundError(question_id)
        assert str(question_id) in str(error)
        assert error.question_id == question_id


class TestQuestionAlreadyPublishedError:
    def test_is_a_domain_error(self) -> None:
        assert isinstance(QuestionAlreadyPublishedError(uuid4()), DomainError)

    def test_message_includes_id(self) -> None:
        question_id = uuid4()
        error = QuestionAlreadyPublishedError(question_id)
        assert str(question_id) in str(error)
        assert error.question_id == question_id


class TestQuestionAlreadyArchivedError:
    def test_is_a_domain_error(self) -> None:
        assert isinstance(QuestionAlreadyArchivedError(uuid4()), DomainError)

    def test_message_includes_id(self) -> None:
        question_id = uuid4()
        error = QuestionAlreadyArchivedError(question_id)
        assert str(question_id) in str(error)
        assert error.question_id == question_id


class TestQuestionAlreadyClosedError:
    def test_is_a_domain_error(self) -> None:
        assert isinstance(QuestionAlreadyClosedError(uuid4()), DomainError)

    def test_message_includes_id(self) -> None:
        question_id = uuid4()
        error = QuestionAlreadyClosedError(question_id)
        assert str(question_id) in str(error)
        assert error.question_id == question_id


class TestQuestionNotClosedError:
    def test_is_a_domain_error(self) -> None:
        assert isinstance(QuestionNotClosedError(uuid4()), DomainError)

    def test_message_includes_id(self) -> None:
        question_id = uuid4()
        error = QuestionNotClosedError(question_id)
        assert str(question_id) in str(error)
        assert error.question_id == question_id


class TestQuestionAlreadyDeletedError:
    def test_is_a_domain_error(self) -> None:
        assert isinstance(QuestionAlreadyDeletedError(uuid4()), DomainError)

    def test_message_includes_id(self) -> None:
        question_id = uuid4()
        error = QuestionAlreadyDeletedError(question_id)
        assert str(question_id) in str(error)
        assert error.question_id == question_id


class TestCommunityNotFoundForQuestionError:
    def test_is_a_domain_error(self) -> None:
        assert isinstance(CommunityNotFoundForQuestionError(uuid4()), DomainError)

    def test_message_includes_id(self) -> None:
        community_id = uuid4()
        error = CommunityNotFoundForQuestionError(community_id)
        assert str(community_id) in str(error)
        assert error.community_id == community_id


class TestTopicNotFoundForQuestionError:
    def test_is_a_domain_error(self) -> None:
        assert isinstance(TopicNotFoundForQuestionError(uuid4()), DomainError)

    def test_message_includes_id(self) -> None:
        topic_id = uuid4()
        error = TopicNotFoundForQuestionError(topic_id)
        assert str(topic_id) in str(error)
        assert error.topic_id == topic_id


class TestDocumentNotFoundForQuestionError:
    def test_is_a_domain_error(self) -> None:
        assert isinstance(DocumentNotFoundForQuestionError(uuid4()), DomainError)

    def test_message_includes_id(self) -> None:
        document_id = uuid4()
        error = DocumentNotFoundForQuestionError(document_id)
        assert str(document_id) in str(error)
        assert error.document_id == document_id


class TestInsufficientQuestionRoleError:
    def test_is_a_domain_error(self) -> None:
        assert isinstance(InsufficientQuestionRoleError(uuid4(), uuid4()), DomainError)

    def test_message_includes_both_ids(self) -> None:
        community_id, user_id = uuid4(), uuid4()
        error = InsufficientQuestionRoleError(community_id, user_id)
        assert str(community_id) in str(error)
        assert str(user_id) in str(error)


class TestQuestionMembershipRequiredError:
    def test_is_a_domain_error(self) -> None:
        assert isinstance(QuestionMembershipRequiredError(uuid4(), uuid4()), DomainError)

    def test_message_includes_both_ids(self) -> None:
        community_id, user_id = uuid4(), uuid4()
        error = QuestionMembershipRequiredError(community_id, user_id)
        assert str(community_id) in str(error)
        assert str(user_id) in str(error)


class TestQuestionNotViewableError:
    def test_is_a_domain_error(self) -> None:
        assert isinstance(QuestionNotViewableError(uuid4()), DomainError)

    def test_message_includes_id(self) -> None:
        question_id = uuid4()
        error = QuestionNotViewableError(question_id)
        assert str(question_id) in str(error)
        assert error.question_id == question_id


class TestQuestionTagRequiredError:
    def test_is_a_domain_error(self) -> None:
        assert isinstance(QuestionTagRequiredError(), DomainError)

    def test_message(self) -> None:
        assert "blank" in str(QuestionTagRequiredError())


class TestQuestionTagTooLongError:
    def test_is_a_domain_error(self) -> None:
        assert isinstance(QuestionTagTooLongError(50), DomainError)

    def test_message_includes_max_length(self) -> None:
        error = QuestionTagTooLongError(50)
        assert "50" in str(error)
        assert error.max_length == 50


class TestDuplicateQuestionTagError:
    def test_is_a_domain_error(self) -> None:
        assert isinstance(DuplicateQuestionTagError(uuid4(), "diabetes"), DomainError)

    def test_message_includes_id_and_tag(self) -> None:
        question_id = uuid4()
        error = DuplicateQuestionTagError(question_id, "diabetes")
        assert str(question_id) in str(error)
        assert "diabetes" in str(error)


class TestQuestionTagNotFoundError:
    def test_is_a_domain_error(self) -> None:
        assert isinstance(QuestionTagNotFoundError(uuid4()), DomainError)

    def test_message_includes_id(self) -> None:
        tag_id = uuid4()
        error = QuestionTagNotFoundError(tag_id)
        assert str(tag_id) in str(error)
        assert error.tag_id == tag_id


class TestDuplicateQuestionTopicError:
    def test_is_a_domain_error(self) -> None:
        assert isinstance(DuplicateQuestionTopicError(uuid4(), uuid4()), DomainError)

    def test_message_includes_both_ids(self) -> None:
        question_id, topic_id = uuid4(), uuid4()
        error = DuplicateQuestionTopicError(question_id, topic_id)
        assert str(question_id) in str(error)
        assert str(topic_id) in str(error)


class TestQuestionTopicNotFoundError:
    def test_is_a_domain_error(self) -> None:
        assert isinstance(QuestionTopicNotFoundError(uuid4()), DomainError)

    def test_message_includes_id(self) -> None:
        question_topic_id = uuid4()
        error = QuestionTopicNotFoundError(question_topic_id)
        assert str(question_topic_id) in str(error)
        assert error.question_topic_id == question_topic_id


class TestDuplicateQuestionAttachmentError:
    def test_is_a_domain_error(self) -> None:
        assert isinstance(DuplicateQuestionAttachmentError(uuid4(), uuid4()), DomainError)

    def test_message_includes_both_ids(self) -> None:
        question_id, document_id = uuid4(), uuid4()
        error = DuplicateQuestionAttachmentError(question_id, document_id)
        assert str(question_id) in str(error)
        assert str(document_id) in str(error)


class TestQuestionAttachmentNotFoundError:
    def test_is_a_domain_error(self) -> None:
        assert isinstance(QuestionAttachmentNotFoundError(uuid4()), DomainError)

    def test_message_includes_id(self) -> None:
        attachment_id = uuid4()
        error = QuestionAttachmentNotFoundError(attachment_id)
        assert str(attachment_id) in str(error)
        assert error.attachment_id == attachment_id


class TestDuplicateQuestionFollowerError:
    def test_is_a_domain_error(self) -> None:
        assert isinstance(DuplicateQuestionFollowerError(uuid4(), uuid4()), DomainError)

    def test_message_includes_both_ids(self) -> None:
        question_id, user_id = uuid4(), uuid4()
        error = DuplicateQuestionFollowerError(question_id, user_id)
        assert str(question_id) in str(error)
        assert str(user_id) in str(error)


class TestQuestionFollowerNotFoundError:
    def test_is_a_domain_error(self) -> None:
        assert isinstance(QuestionFollowerNotFoundError(uuid4(), uuid4()), DomainError)

    def test_message_includes_both_ids(self) -> None:
        question_id, user_id = uuid4(), uuid4()
        error = QuestionFollowerNotFoundError(question_id, user_id)
        assert str(question_id) in str(error)
        assert str(user_id) in str(error)
