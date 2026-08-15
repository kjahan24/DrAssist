"""Domain exceptions for the Community Questions module.

Naming follows the codebase-wide convention `app.middlewares.error_handler
._map_domain_error` relies on: a name containing "NotFound" maps to 404; a
name containing "Duplicate"/"AlreadyExists"/"Transition"/"Immutable"/
"Inactive" maps to 409; everything else maps to 422 (well-formed request,
semantically invalid). See that module's own docstring for the full
heuristic.
"""

from uuid import UUID

from app.shared.domain.exceptions import DomainError


class QuestionTitleRequiredError(DomainError):
    def __init__(self) -> None:
        super().__init__("Question title must not be blank.")


class QuestionTitleTooLongError(DomainError):
    def __init__(self, max_length: int) -> None:
        self.max_length = max_length
        super().__init__(f"Question title must be at most {max_length} characters.")


class InvalidQuestionSlugError(DomainError):
    def __init__(self, value: str) -> None:
        self.value = value
        super().__init__(f"Invalid question slug: {value!r}.")


class DuplicateQuestionSlugError(DomainError):
    def __init__(self, community_id: UUID, slug: str) -> None:
        self.community_id = community_id
        self.slug = slug
        super().__init__(
            f"A question with slug {slug!r} already exists in community {community_id}."
        )


class QuestionSummaryRequiredError(DomainError):
    def __init__(self) -> None:
        super().__init__("Question summary must not be blank.")


class QuestionSummaryTooLongError(DomainError):
    def __init__(self, max_length: int) -> None:
        self.max_length = max_length
        super().__init__(f"Question summary must be at most {max_length} characters.")


class QuestionBodyRequiredError(DomainError):
    def __init__(self) -> None:
        super().__init__("Question body must not be blank.")


class QuestionNotFoundError(DomainError):
    def __init__(self, question_id: UUID) -> None:
        self.question_id = question_id
        super().__init__(f"No question found with id {question_id}.")


class QuestionAlreadyPublishedError(DomainError):
    def __init__(self, question_id: UUID) -> None:
        self.question_id = question_id
        super().__init__(f"Question {question_id} is already published.")


class QuestionAlreadyArchivedError(DomainError):
    def __init__(self, question_id: UUID) -> None:
        self.question_id = question_id
        super().__init__(f"Question {question_id} is already archived.")


class QuestionAlreadyClosedError(DomainError):
    def __init__(self, question_id: UUID) -> None:
        self.question_id = question_id
        super().__init__(f"Question {question_id} is already closed.")


class QuestionNotClosedError(DomainError):
    def __init__(self, question_id: UUID) -> None:
        self.question_id = question_id
        super().__init__(f"Question {question_id} is not closed, so it cannot be reopened.")


class QuestionAlreadyDeletedError(DomainError):
    def __init__(self, question_id: UUID) -> None:
        self.question_id = question_id
        super().__init__(f"Question {question_id} is already deleted.")


class CommunityNotFoundForQuestionError(DomainError):
    def __init__(self, community_id: UUID) -> None:
        self.community_id = community_id
        super().__init__(f"No community found with id {community_id}.")


class TopicNotFoundForQuestionError(DomainError):
    def __init__(self, topic_id: UUID) -> None:
        self.topic_id = topic_id
        super().__init__(f"No topic found with id {topic_id}.")


class DocumentNotFoundForQuestionError(DomainError):
    def __init__(self, document_id: UUID) -> None:
        self.document_id = document_id
        super().__init__(f"No document found with id {document_id}.")


class InsufficientQuestionRoleError(DomainError):
    def __init__(self, community_id: UUID, user_id: UUID) -> None:
        self.community_id = community_id
        self.user_id = user_id
        super().__init__(
            f"User {user_id} is not the question's author and does not hold a "
            f"moderating role in community {community_id}."
        )


class QuestionMembershipRequiredError(DomainError):
    def __init__(self, community_id: UUID, user_id: UUID) -> None:
        self.community_id = community_id
        self.user_id = user_id
        super().__init__(f"User {user_id} has no membership in community {community_id}.")


class QuestionNotViewableError(DomainError):
    def __init__(self, question_id: UUID) -> None:
        self.question_id = question_id
        super().__init__(f"Question {question_id} is not viewable by this caller.")


class QuestionTagRequiredError(DomainError):
    def __init__(self) -> None:
        super().__init__("Question tag must not be blank.")


class QuestionTagTooLongError(DomainError):
    def __init__(self, max_length: int) -> None:
        self.max_length = max_length
        super().__init__(f"Question tag must be at most {max_length} characters.")


class DuplicateQuestionTagError(DomainError):
    def __init__(self, question_id: UUID, tag: str) -> None:
        self.question_id = question_id
        self.tag = tag
        super().__init__(f"Question {question_id} already has tag {tag!r}.")


class QuestionTagNotFoundError(DomainError):
    def __init__(self, tag_id: UUID) -> None:
        self.tag_id = tag_id
        super().__init__(f"No question tag found with id {tag_id}.")


class DuplicateQuestionTopicError(DomainError):
    def __init__(self, question_id: UUID, topic_id: UUID) -> None:
        self.question_id = question_id
        self.topic_id = topic_id
        super().__init__(f"Question {question_id} is already assigned to topic {topic_id}.")


class QuestionTopicNotFoundError(DomainError):
    def __init__(self, question_topic_id: UUID) -> None:
        self.question_topic_id = question_topic_id
        super().__init__(f"No question-topic assignment found with id {question_topic_id}.")


class DuplicateQuestionAttachmentError(DomainError):
    def __init__(self, question_id: UUID, document_id: UUID) -> None:
        self.question_id = question_id
        self.document_id = document_id
        super().__init__(f"Question {question_id} already has attachment {document_id}.")


class QuestionAttachmentNotFoundError(DomainError):
    def __init__(self, attachment_id: UUID) -> None:
        self.attachment_id = attachment_id
        super().__init__(f"No question attachment found with id {attachment_id}.")


class DuplicateQuestionFollowerError(DomainError):
    def __init__(self, question_id: UUID, user_id: UUID) -> None:
        self.question_id = question_id
        self.user_id = user_id
        super().__init__(f"User {user_id} is already following question {question_id}.")


class QuestionFollowerNotFoundError(DomainError):
    def __init__(self, question_id: UUID, user_id: UUID) -> None:
        self.question_id = question_id
        self.user_id = user_id
        super().__init__(f"User {user_id} is not following question {question_id}.")
