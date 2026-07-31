"""The Documents module's public port — the only contract another module
may depend on. See `docs/backend-architecture/03_module_architecture.md`
and `10_module_communication.md`.

Never import from `app.modules.documents.domain`, `.application` (beyond
this package), or `.infrastructure` from outside this module — this file
and `dto.py` are the entire allowed surface today. Future modules that
need to know a patient's/visit's uploaded documents (Personal Health
Timeline, Patient Portal, Family/Caregiver Access, Medical Community
attachments, ...) are expected to depend on this port, the same way this
module itself depends on `PatientQueryPort`/`VisitQueryPort`/
`AppointmentQueryPort`.
"""

from abc import ABC, abstractmethod
from uuid import UUID

from app.modules.documents.public.dto import MedicalDocumentSummaryDTO


class DocumentQueryPort(ABC):
    @abstractmethod
    async def document_exists(self, document_id: UUID) -> bool: ...

    @abstractmethod
    async def get_document_summary(self, document_id: UUID) -> MedicalDocumentSummaryDTO | None: ...

    @abstractmethod
    async def list_documents_for_patient(
        self, patient_id: UUID
    ) -> list[MedicalDocumentSummaryDTO]: ...

    @abstractmethod
    async def list_documents_for_visit(self, visit_id: UUID) -> list[MedicalDocumentSummaryDTO]: ...

    @abstractmethod
    async def list_documents_for_appointment(
        self, appointment_id: UUID
    ) -> list[MedicalDocumentSummaryDTO]: ...
