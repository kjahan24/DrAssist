"""Tests for the Community Answers module's domain exceptions."""

from uuid import uuid4

from app.modules.community_answers.domain.exceptions import (
    AnswerAlreadyArchivedError,
    AnswerAlreadyBestAnswerError,
    AnswerAlreadyDeletedError,
    AnswerAlreadyPublishedError,
    AnswerAttachmentNotFoundError,
    AnswerBodyRequiredError,
    AnswerBodyTooLongError,
    AnswerCannotBeRestoredError,
    AnswerDoesNotBelongToQuestionError,
    AnswerMembershipRequiredError,
    AnswerNotBestAnswerError,
    AnswerNotFoundError,
    AnswerNotPublishedForBestAnswerError,
    AnswerNotViewableError,
    AnswerSummaryRequiredError,
    AnswerSummaryTooLongError,
    DocumentNotFoundForAnswerError,
    DuplicateAnswerAttachmentError,
    InsufficientAnswerRoleError,
    InsufficientBestAnswerRoleError,
    QuestionNotAcceptingAnswersError,
    QuestionNotFoundForAnswerError,
    QuestionNotViewableForAnswerError,
)
from app.shared.domain.exceptions import DomainError


class TestAnswerBodyRequiredError:
    def test_is_a_domain_error(self) -> None:
        assert isinstance(AnswerBodyRequiredError(), DomainError)

    def test_message(self) -> None:
        assert "blank" in str(AnswerBodyRequiredError())


class TestAnswerBodyTooLongError:
    def test_is_a_domain_error(self) -> None:
        assert isinstance(AnswerBodyTooLongError(20000), DomainError)

    def test_message_includes_max_length(self) -> None:
        error = AnswerBodyTooLongError(20000)
        assert "20000" in str(error)
        assert error.max_length == 20000


class TestAnswerSummaryRequiredError:
    def test_is_a_domain_error(self) -> None:
        assert isinstance(AnswerSummaryRequiredError(), DomainError)

    def test_message(self) -> None:
        assert "blank" in str(AnswerSummaryRequiredError())


class TestAnswerSummaryTooLongError:
    def test_is_a_domain_error(self) -> None:
        assert isinstance(AnswerSummaryTooLongError(500), DomainError)

    def test_message_includes_max_length(self) -> None:
        error = AnswerSummaryTooLongError(500)
        assert "500" in str(error)
        assert error.max_length == 500


class TestAnswerNotFoundError:
    def test_is_a_domain_error(self) -> None:
        assert isinstance(AnswerNotFoundError(uuid4()), DomainError)

    def test_message_includes_id(self) -> None:
        answer_id = uuid4()
        error = AnswerNotFoundError(answer_id)
        assert str(answer_id) in str(error)
        assert error.answer_id == answer_id


class TestAnswerAlreadyPublishedError:
    def test_is_a_domain_error(self) -> None:
        assert isinstance(AnswerAlreadyPublishedError(uuid4()), DomainError)

    def test_message_includes_id(self) -> None:
        answer_id = uuid4()
        error = AnswerAlreadyPublishedError(answer_id)
        assert str(answer_id) in str(error)
        assert error.answer_id == answer_id


class TestAnswerAlreadyArchivedError:
    def test_is_a_domain_error(self) -> None:
        assert isinstance(AnswerAlreadyArchivedError(uuid4()), DomainError)

    def test_message_includes_id(self) -> None:
        answer_id = uuid4()
        error = AnswerAlreadyArchivedError(answer_id)
        assert str(answer_id) in str(error)
        assert error.answer_id == answer_id


class TestAnswerAlreadyDeletedError:
    def test_is_a_domain_error(self) -> None:
        assert isinstance(AnswerAlreadyDeletedError(uuid4()), DomainError)

    def test_message_includes_id(self) -> None:
        answer_id = uuid4()
        error = AnswerAlreadyDeletedError(answer_id)
        assert str(answer_id) in str(error)
        assert error.answer_id == answer_id


class TestAnswerCannotBeRestoredError:
    def test_is_a_domain_error(self) -> None:
        assert isinstance(AnswerCannotBeRestoredError(uuid4()), DomainError)

    def test_message_includes_id(self) -> None:
        answer_id = uuid4()
        error = AnswerCannotBeRestoredError(answer_id)
        assert str(answer_id) in str(error)
        assert error.answer_id == answer_id


class TestQuestionNotFoundForAnswerError:
    def test_is_a_domain_error(self) -> None:
        assert isinstance(QuestionNotFoundForAnswerError(uuid4()), DomainError)

    def test_message_includes_id(self) -> None:
        question_id = uuid4()
        error = QuestionNotFoundForAnswerError(question_id)
        assert str(question_id) in str(error)
        assert error.question_id == question_id


class TestQuestionNotAcceptingAnswersError:
    def test_is_a_domain_error(self) -> None:
        assert isinstance(QuestionNotAcceptingAnswersError(uuid4()), DomainError)

    def test_message_includes_id(self) -> None:
        question_id = uuid4()
        error = QuestionNotAcceptingAnswersError(question_id)
        assert str(question_id) in str(error)
        assert error.question_id == question_id


class TestQuestionNotViewableForAnswerError:
    def test_is_a_domain_error(self) -> None:
        assert isinstance(QuestionNotViewableForAnswerError(uuid4()), DomainError)

    def test_message_includes_id(self) -> None:
        question_id = uuid4()
        error = QuestionNotViewableForAnswerError(question_id)
        assert str(question_id) in str(error)
        assert error.question_id == question_id


class TestDocumentNotFoundForAnswerError:
    def test_is_a_domain_error(self) -> None:
        assert isinstance(DocumentNotFoundForAnswerError(uuid4()), DomainError)

    def test_message_includes_id(self) -> None:
        document_id = uuid4()
        error = DocumentNotFoundForAnswerError(document_id)
        assert str(document_id) in str(error)
        assert error.document_id == document_id


class TestInsufficientAnswerRoleError:
    def test_is_a_domain_error(self) -> None:
        assert isinstance(InsufficientAnswerRoleError(uuid4(), uuid4()), DomainError)

    def test_message_includes_both_ids(self) -> None:
        community_id, user_id = uuid4(), uuid4()
        error = InsufficientAnswerRoleError(community_id, user_id)
        assert str(community_id) in str(error)
        assert str(user_id) in str(error)


class TestAnswerMembershipRequiredError:
    def test_is_a_domain_error(self) -> None:
        assert isinstance(AnswerMembershipRequiredError(uuid4(), uuid4()), DomainError)

    def test_message_includes_both_ids(self) -> None:
        community_id, user_id = uuid4(), uuid4()
        error = AnswerMembershipRequiredError(community_id, user_id)
        assert str(community_id) in str(error)
        assert str(user_id) in str(error)


class TestAnswerNotViewableError:
    def test_is_a_domain_error(self) -> None:
        assert isinstance(AnswerNotViewableError(uuid4()), DomainError)

    def test_message_includes_id(self) -> None:
        answer_id = uuid4()
        error = AnswerNotViewableError(answer_id)
        assert str(answer_id) in str(error)
        assert error.answer_id == answer_id


class TestInsufficientBestAnswerRoleError:
    def test_is_a_domain_error(self) -> None:
        assert isinstance(InsufficientBestAnswerRoleError(uuid4(), uuid4()), DomainError)

    def test_message_includes_both_ids(self) -> None:
        question_id, user_id = uuid4(), uuid4()
        error = InsufficientBestAnswerRoleError(question_id, user_id)
        assert str(question_id) in str(error)
        assert str(user_id) in str(error)


class TestAnswerNotPublishedForBestAnswerError:
    def test_is_a_domain_error(self) -> None:
        assert isinstance(AnswerNotPublishedForBestAnswerError(uuid4()), DomainError)

    def test_message_includes_id(self) -> None:
        answer_id = uuid4()
        error = AnswerNotPublishedForBestAnswerError(answer_id)
        assert str(answer_id) in str(error)
        assert error.answer_id == answer_id


class TestAnswerAlreadyBestAnswerError:
    def test_is_a_domain_error(self) -> None:
        assert isinstance(AnswerAlreadyBestAnswerError(uuid4()), DomainError)

    def test_message_includes_id(self) -> None:
        answer_id = uuid4()
        error = AnswerAlreadyBestAnswerError(answer_id)
        assert str(answer_id) in str(error)
        assert error.answer_id == answer_id


class TestAnswerNotBestAnswerError:
    def test_is_a_domain_error(self) -> None:
        assert isinstance(AnswerNotBestAnswerError(uuid4()), DomainError)

    def test_message_includes_id(self) -> None:
        answer_id = uuid4()
        error = AnswerNotBestAnswerError(answer_id)
        assert str(answer_id) in str(error)
        assert error.answer_id == answer_id


class TestAnswerDoesNotBelongToQuestionError:
    def test_is_a_domain_error(self) -> None:
        assert isinstance(AnswerDoesNotBelongToQuestionError(uuid4(), uuid4()), DomainError)

    def test_message_includes_both_ids(self) -> None:
        answer_id, question_id = uuid4(), uuid4()
        error = AnswerDoesNotBelongToQuestionError(answer_id, question_id)
        assert str(answer_id) in str(error)
        assert str(question_id) in str(error)
        assert error.answer_id == answer_id
        assert error.question_id == question_id


class TestDuplicateAnswerAttachmentError:
    def test_is_a_domain_error(self) -> None:
        assert isinstance(DuplicateAnswerAttachmentError(uuid4(), uuid4()), DomainError)

    def test_message_includes_both_ids(self) -> None:
        answer_id, document_id = uuid4(), uuid4()
        error = DuplicateAnswerAttachmentError(answer_id, document_id)
        assert str(answer_id) in str(error)
        assert str(document_id) in str(error)


class TestAnswerAttachmentNotFoundError:
    def test_is_a_domain_error(self) -> None:
        assert isinstance(AnswerAttachmentNotFoundError(uuid4()), DomainError)

    def test_message_includes_id(self) -> None:
        attachment_id = uuid4()
        error = AnswerAttachmentNotFoundError(attachment_id)
        assert str(attachment_id) in str(error)
        assert error.attachment_id == attachment_id
