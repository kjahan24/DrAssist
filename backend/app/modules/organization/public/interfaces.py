"""The Organization module's public port — the only contract another
module may depend on. See
`docs/backend-architecture/03_module_architecture.md` (Organization) and
`10_module_communication.md`.

Never import from `app.modules.organization.domain`, `.application`
(beyond this package), or `.infrastructure` from outside this module —
this file and `dto.py` are the entire allowed surface today.
"""

from abc import ABC, abstractmethod
from uuid import UUID

from app.modules.organization.public.dto import OrganizationSummaryDTO


class OrganizationQueryPort(ABC):
    @abstractmethod
    async def organization_exists(self, organization_id: UUID) -> bool: ...

    @abstractmethod
    async def is_active(self, organization_id: UUID) -> bool: ...

    @abstractmethod
    async def get_organization_summary(
        self, organization_id: UUID
    ) -> OrganizationSummaryDTO | None: ...

    @abstractmethod
    async def get_default_timezone(self, organization_id: UUID) -> str | None: ...


class OrganizationProvisioningPort(ABC):
    """Added for self-service user registration
    (`app.modules.authentication.application.use_cases.register_user`):
    that flow's own request has no organization field at all (the current
    frontend's Sign Up form collects only name/email/password — see that
    use case's own docstring), so registering a brand new user means
    provisioning a brand new tenant for them in the same step. This is a
    *write* capability, deliberately kept on its own narrow port rather
    than folded into the read-only `OrganizationQueryPort` above, mirroring
    the "one port per capability shape" precedent every other module's own
    `public/interfaces.py` already follows (e.g.
    `app.modules.community_moderation.public.interfaces
    .ModerationQueryPort` staying query-only while a distinct concern gets
    its own port).

    `organization_code` is not a caller-supplied parameter — a self-service
    signup has no meaningful code to offer, so the concrete implementation
    generates one internally (see `public/facade.py`); the tenant can
    rename/recode itself later via the module's own existing
    `UpdateOrganizationSettings` path.
    """

    @abstractmethod
    async def provision_organization(
        self, *, name: str, email: str | None = None
    ) -> OrganizationSummaryDTO:
        """Create a new organization (with its default settings) and
        return its summary. Never raises for a code collision — the
        generated code is effectively unique (see `public/facade.py`)."""
        ...
