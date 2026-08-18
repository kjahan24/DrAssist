"""Domain exceptions for the Community Comments module.

Naming follows the codebase-wide convention `app.middlewares.error_handler
._map_domain_error` relies on: a name containing "NotFound" maps to 404; a
name containing "Duplicate"/"AlreadyExists"/"Transition"/"Immutable"/
"Inactive" maps to 409; everything else maps to 422 (well-formed request,
semantically invalid). See that module's own docstring for the full
heuristic.
"""

from uuid import UUID

from app.shared.domain.exceptions import DomainError


class CommentBodyRequiredError(DomainError):
    def __init__(self) -> None:
        super().__init__("Comment body must not be blank.")


class CommentBodyTooLongError(DomainError):
    def __init__(self, max_length: int) -> None:
        self.max_length = max_length
        super().__init__(f"Comment body must be at most {max_length} characters.")


class CommentNotFoundError(DomainError):
    def __init__(self, comment_id: UUID) -> None:
        self.comment_id = comment_id
        super().__init__(f"No comment found with id {comment_id}.")


class CommentAlreadyPublishedError(DomainError):
    def __init__(self, comment_id: UUID) -> None:
        self.comment_id = comment_id
        super().__init__(f"Comment {comment_id} is already published.")


class CommentAlreadyArchivedError(DomainError):
    def __init__(self, comment_id: UUID) -> None:
        self.comment_id = comment_id
        super().__init__(f"Comment {comment_id} is already archived.")


class CommentAlreadyDeletedError(DomainError):
    def __init__(self, comment_id: UUID) -> None:
        self.comment_id = comment_id
        super().__init__(f"Comment {comment_id} is already deleted.")


class CommentCannotBeRestoredError(DomainError):
    def __init__(self, comment_id: UUID) -> None:
        self.comment_id = comment_id
        super().__init__(
            f"Comment {comment_id} is not archived or deleted, so it cannot be restored."
        )


class TargetNotFoundForCommentError(DomainError):
    def __init__(self, target_id: UUID) -> None:
        self.target_id = target_id
        super().__init__(f"No comment target found with id {target_id}.")


class TargetNotAcceptingCommentsError(DomainError):
    def __init__(self, target_id: UUID) -> None:
        self.target_id = target_id
        super().__init__(f"Target {target_id} is not open to new comments.")


class TargetNotViewableForCommentError(DomainError):
    def __init__(self, target_id: UUID) -> None:
        self.target_id = target_id
        super().__init__(f"Target {target_id} is not viewable by this caller.")


class ParentCommentNotFoundError(DomainError):
    def __init__(self, parent_comment_id: UUID) -> None:
        self.parent_comment_id = parent_comment_id
        super().__init__(f"No parent comment found with id {parent_comment_id}.")


class ParentCommentNotAcceptingRepliesError(DomainError):
    def __init__(self, parent_comment_id: UUID) -> None:
        self.parent_comment_id = parent_comment_id
        super().__init__(f"Parent comment {parent_comment_id} is not open to new replies.")


class MaxCommentDepthExceededError(DomainError):
    def __init__(self, parent_comment_id: UUID, max_depth: int) -> None:
        self.parent_comment_id = parent_comment_id
        self.max_depth = max_depth
        super().__init__(
            f"Replying to comment {parent_comment_id} would exceed the maximum "
            f"nesting depth of {max_depth}."
        )


class DocumentNotFoundForCommentError(DomainError):
    def __init__(self, document_id: UUID) -> None:
        self.document_id = document_id
        super().__init__(f"No document found with id {document_id}.")


class InsufficientCommentRoleError(DomainError):
    def __init__(self, community_id: UUID, user_id: UUID) -> None:
        self.community_id = community_id
        self.user_id = user_id
        super().__init__(
            f"User {user_id} is not the comment's author and does not hold a "
            f"moderating role in community {community_id}."
        )


class CommentMembershipRequiredError(DomainError):
    def __init__(self, community_id: UUID, user_id: UUID) -> None:
        self.community_id = community_id
        self.user_id = user_id
        super().__init__(f"User {user_id} has no membership in community {community_id}.")


class CommentNotViewableError(DomainError):
    def __init__(self, comment_id: UUID) -> None:
        self.comment_id = comment_id
        super().__init__(f"Comment {comment_id} is not viewable by this caller.")


class DuplicateCommentAttachmentError(DomainError):
    def __init__(self, comment_id: UUID, document_id: UUID) -> None:
        self.comment_id = comment_id
        self.document_id = document_id
        super().__init__(f"Comment {comment_id} already has attachment {document_id}.")


class CommentAttachmentNotFoundError(DomainError):
    def __init__(self, attachment_id: UUID) -> None:
        self.attachment_id = attachment_id
        super().__init__(f"No comment attachment found with id {attachment_id}.")
