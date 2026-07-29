"""The Prescription module's public port — the only contract another
module may depend on. See
`docs/backend-architecture/03_module_architecture.md` and
`10_module_communication.md`.

Never import from `app.modules.prescriptions.domain`, `.application`
(beyond this package), or `.infrastructure` from outside this module —
this file and `dto.py` are the entire allowed surface today. This port is
the contract every future medication-aware module (Drug Interaction
Engine, Drug Allergy Checking, Medication History, Medication
Reconciliation, Pharmacy Integration, ePrescription, AI Prescription
Review, Refill Requests) is expected to depend on to read a patient's
prescribed medications — the same shape
`app.modules.soap_notes.public.interfaces.SOAPNoteQueryPort` already
establishes for its own sibling place under `ClinicalNote`.
`list_prescriptions_for_patient` in particular exists for Medication
History/Medication Reconciliation specifically — see
`application/services/prescription_query_service.py`'s own docstring.
"""

from abc import ABC, abstractmethod
from uuid import UUID

from app.modules.prescriptions.public.dto import PrescriptionSummaryDTO


class PrescriptionQueryPort(ABC):
    @abstractmethod
    async def prescription_exists_for_clinical_note(self, clinical_note_id: UUID) -> bool: ...

    @abstractmethod
    async def get_prescription_summary(
        self, clinical_note_id: UUID
    ) -> PrescriptionSummaryDTO | None: ...

    @abstractmethod
    async def list_prescriptions_for_patient(
        self, patient_id: UUID
    ) -> list[PrescriptionSummaryDTO]: ...
