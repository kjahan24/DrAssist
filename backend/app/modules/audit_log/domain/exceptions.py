"""Domain exceptions for the Audit Log module.

Each names the invariant it protects, not the eventual HTTP outcome — see
`docs/backend-architecture/06_configuration_logging_exceptions.md`.

`ActorNotFoundError` is defined locally rather than reused from
`app.modules.authentication` — the same situation every prior
child-document module documents: Authentication exposes no "not found"
error a peer module is allowed to import, so a module that *references*
an existing row by id defines the exception locally.
"""

from uuid import UUID

from app.shared.domain.exceptions import DomainError


class EntityTypeRequiredError(DomainError):
    def __init__(self) -> None:
        super().__init__("entity_type must not be blank")


class ActorNotFoundError(DomainError):
    def __init__(self, actor_user_id: UUID) -> None:
        super().__init__(f"no user found with id {actor_user_id}")
        self.actor_user_id = actor_user_id


class ActorOrganizationMismatchError(DomainError):
    def __init__(self, actor_user_id: UUID, organization_id: UUID) -> None:
        super().__init__(f"actor {actor_user_id} does not belong to organization {organization_id}")
        self.actor_user_id = actor_user_id
        self.organization_id = organization_id


class AuditLogImmutableError(DomainError):
    """Raised by `AuditLogRepository.add()` if a row with the given id
    already exists — see that method's own docstring for why this is the
    concrete mechanism behind "the repository must reject update
    operations": `add()` is insert-only, never upsert, unlike every other
    module's own `add()`."""

    def __init__(self, audit_log_id: UUID) -> None:
        super().__init__(
            f"audit log {audit_log_id} already exists and cannot be modified — "
            "audit logs are immutable"
        )
        self.audit_log_id = audit_log_id
