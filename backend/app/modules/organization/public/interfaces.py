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
