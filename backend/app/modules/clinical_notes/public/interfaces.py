"""The Clinical Notes module's public port — the only contract another
module may depend on. See
`docs/backend-architecture/03_module_architecture.md` (Clinical Notes)
and `10_module_communication.md`.

Never import from `app.modules.clinical_notes.domain`, `.application`
(beyond this package), or `.infrastructure` from outside this module —
this file and `dto.py` are the entire allowed surface today. This port
is the primary contract every future clinical-document module (SOAP
Note, Prescription, Lab Order, Lab Result, Imaging Report, Clinical
Reasoning, Differential Diagnosis, ICD-10/CPT Coding, AI Copilot, Doctor
Review, Clinical Timeline) is expected to depend on to confirm a
clinical note exists — and, for Clinical Timeline specifically,
`list_clinical_notes_for_patient` — before attaching to it, the same way
this module itself depends on `VisitQueryPort`.
"""

from abc import ABC, abstractmethod
from uuid import UUID

from app.modules.clinical_notes.public.dto import ClinicalNoteSummaryDTO


class ClinicalNoteQueryPort(ABC):
    @abstractmethod
    async def clinical_note_exists(self, clinical_note_id: UUID) -> bool: ...

    @abstractmethod
    async def get_clinical_note_summary(
        self, clinical_note_id: UUID
    ) -> ClinicalNoteSummaryDTO | None: ...

    @abstractmethod
    async def list_clinical_notes_for_visit(
        self, visit_id: UUID
    ) -> list[ClinicalNoteSummaryDTO]: ...

    @abstractmethod
    async def list_clinical_notes_for_patient(
        self, patient_id: UUID
    ) -> list[ClinicalNoteSummaryDTO]: ...
