"""Domain exceptions for the Community Answers module.

Naming follows the codebase-wide convention `app.middlewares.error_handler
._map_domain_error` relies on: a name containing "NotFound" maps to 404; a
name containing "Duplicate"/"AlreadyExists"/"Transition"/"Immutable"/
"Inactive" maps to 409; everything else maps to 422 (well-formed request,
semantically invalid). See that module's own docstring for the full
heuristic.
"""

from uuid import UUID

from app.shared.domain.exceptions import DomainError


class AnswerBodyRequiredError(DomainError):
    def __init__(self) -> None:
        super().__init__("Answer body must not be blank.")


class AnswerBodyTooLongError(DomainError):
    def __init__(self, max_length: int) -> None:
        self.max_length = max_length
        super().__init__(f"Answer body must be at most {max_length} characters.")


class AnswerSummaryRequiredError(DomainError):
    def __init__(self) -> None:
        super().__init__("Answer summary must not be blank.")


class AnswerSummaryTooLongError(DomainError):
    def __init__(self, max_length: int) -> None:
        self.max_length = max_length
        super().__init__(f"Answer summary must be at most {max_length} characters.")


class AnswerNotFoundError(DomainError):
    def __init__(self, answer_id: UUID) -> None:
        self.answer_id = answer_id
        super().__init__(f"No answer found with id {answer_id}.")


class AnswerAlreadyPublishedError(DomainError):
    def __init__(self, answer_id: UUID) -> None:
        self.answer_id = answer_id
        super().__init__(f"Answer {answer_id} is already published.")


class AnswerAlreadyArchivedError(DomainError):
    def __init__(self, answer_id: UUID) -> None:
        self.answer_id = answer_id
        super().__init__(f"Answer {answer_id} is already archived.")


class AnswerAlreadyDeletedError(DomainError):
    def __init__(self, answer_id: UUID) -> None:
        self.answer_id = answer_id
        super().__init__(f"Answer {answer_id} is already deleted.")


class AnswerCannotBeRestoredError(DomainError):
    def __init__(self, answer_id: UUID) -> None:
        self.answer_id = answer_id
        super().__init__(
            f"Answer {answer_id} is not archived or deleted, so it cannot be restored."
        )


class QuestionNotFoundForAnswerError(DomainError):
    def __init__(self, question_id: UUID) -> None:
        self.question_id = question_id
        super().__init__(f"No question found with id {question_id}.")


class QuestionNotAcceptingAnswersError(DomainError):
    def __init__(self, question_id: UUID) -> None:
        self.question_id = question_id
        super().__init__(f"Question {question_id} is not open to new answers.")


class QuestionNotViewableForAnswerError(DomainError):
    def __init__(self, question_id: UUID) -> None:
        self.question_id = question_id
        super().__init__(f"Question {question_id} is not viewable by this caller.")


class DocumentNotFoundForAnswerError(DomainError):
    def __init__(self, document_id: UUID) -> None:
        self.document_id = document_id
        super().__init__(f"No document found with id {document_id}.")


class InsufficientAnswerRoleError(DomainError):
    def __init__(self, community_id: UUID, user_id: UUID) -> None:
        self.community_id = community_id
        self.user_id = user_id
        super().__init__(
            f"User {user_id} is not the answer's author and does not hold a "
            f"moderating role in community {community_id}."
        )


class AnswerMembershipRequiredError(DomainError):
    def __init__(self, community_id: UUID, user_id: UUID) -> None:
        self.community_id = community_id
        self.user_id = user_id
        super().__init__(f"User {user_id} has no membership in community {community_id}.")


class AnswerNotViewableError(DomainError):
    def __init__(self, answer_id: UUID) -> None:
        self.answer_id = answer_id
        super().__init__(f"Answer {answer_id} is not viewable by this caller.")


class InsufficientBestAnswerRoleError(DomainError):
    def __init__(self, question_id: UUID, user_id: UUID) -> None:
        self.question_id = question_id
        self.user_id = user_id
        super().__init__(
            f"User {user_id} is not the question's author and does not hold a "
            f"moderating role in the question {question_id}'s own community, so "
            f"they may not select or clear its best answer."
        )


class AnswerNotPublishedForBestAnswerError(DomainError):
    def __init__(self, answer_id: UUID) -> None:
        self.answer_id = answer_id
        super().__init__(
            f"Answer {answer_id} must be published before it can become the best answer."
        )


class AnswerAlreadyBestAnswerError(DomainError):
    def __init__(self, answer_id: UUID) -> None:
        self.answer_id = answer_id
        super().__init__(f"Answer {answer_id} is already the best answer for its question.")


class AnswerNotBestAnswerError(DomainError):
    def __init__(self, answer_id: UUID) -> None:
        self.answer_id = answer_id
        super().__init__(f"Answer {answer_id} is not currently the best answer for its question.")


class AnswerDoesNotBelongToQuestionError(DomainError):
    def __init__(self, answer_id: UUID, question_id: UUID) -> None:
        self.answer_id = answer_id
        self.question_id = question_id
        super().__init__(f"Answer {answer_id} does not belong to question {question_id}.")


class DuplicateAnswerAttachmentError(DomainError):
    def __init__(self, answer_id: UUID, document_id: UUID) -> None:
        self.answer_id = answer_id
        self.document_id = document_id
        super().__init__(f"Answer {answer_id} already has attachment {document_id}.")


class AnswerAttachmentNotFoundError(DomainError):
    def __init__(self, attachment_id: UUID) -> None:
        self.attachment_id = attachment_id
        super().__init__(f"No answer attachment found with id {attachment_id}.")
