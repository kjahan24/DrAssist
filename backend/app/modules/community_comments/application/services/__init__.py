"""Application services for the Community Comments module.

This task's own APPLICATION section names `CreateComment`/`UpdateComment`/
`DeleteComment`/`RestoreComment`/`PublishComment`/`ArchiveComment` and
`CreateReply`/`UpdateReply`/`DeleteReply`/`RestoreReply` as fourteen
distinct use cases. `Create*` genuinely differs between the two (a
top-level comment resolves a Post/Question/Answer target; a reply
resolves its parent comment instead — see `create_comment_service`/
`create_reply_service`'s own docstrings), so both get their own service
class. `Update`/`Delete`/`Restore`/`Publish`/`Archive`, once a row
already exists, have **no reply-specific behavior at all** — a reply is
a `CommunityComment` row like any other (see that entity's own module
docstring), so `UpdateCommentService`/`DeleteCommentService`/
`RestoreCommentService`/`PublishCommentService`/`ArchiveCommentService`
operate uniformly on either. Introducing five byte-identical
`UpdateReplyService`/`DeleteReplyService`/... classes purely to mirror
the task's own vocabulary would be the kind of premature/duplicate
abstraction this project's own conventions warn against; the
presentation layer's own route naming (`PATCH /community-comments/{id}`
serving both "Comment CRUD" and "Reply CRUD" from the API section) is
where that vocabulary distinction actually shows up instead.
"""
