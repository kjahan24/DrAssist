"""The Attachments module's public port — the only contract another
module may depend on. See
`docs/backend-architecture/03_module_architecture.md` (Attachments) and
`10_module_communication.md`.

Never import from `app.modules.attachments.domain`, `.application`
(beyond this package), or `.infrastructure` from outside this module —
this file and `dto.py` are the entire allowed surface today. Future
modules that need to know a visit's attached files (Clinical Notes, SOAP
Notes, Billing, ...) are expected to depend on this port, the same way
this module itself depends on `VisitQueryPort`.
"""

from abc import ABC, abstractmethod
from uuid import UUID

from app.modules.attachments.public.dto import AttachmentSummaryDTO


class AttachmentQueryPort(ABC):
    @abstractmethod
    async def attachment_exists(self, attachment_id: UUID) -> bool: ...

    @abstractmethod
    async def list_attachments_for_visit(self, visit_id: UUID) -> list[AttachmentSummaryDTO]: ...
