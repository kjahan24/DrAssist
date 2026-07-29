"""The SOAP Notes module's public port — the only contract another
module may depend on. See
`docs/backend-architecture/03_module_architecture.md` (SOAP Notes) and
`10_module_communication.md`.

Never import from `app.modules.soap_notes.domain`, `.application`
(beyond this package), or `.infrastructure` from outside this module —
this file and `dto.py` are the entire allowed surface today. Future
modules that need a visit's/patient's SOAP documentation (Prescription,
Lab Orders, Lab Results, Clinical Reasoning, Differential Diagnosis,
ICD-10 Coding, Doctor Review, AI Copilot, Clinical Timeline) are expected
to depend on this port — keyed by `clinical_note_id`, the same one-to-one
parent key `SOAPNote` itself uses, since none of them exist without a
clinical note either.
"""

from abc import ABC, abstractmethod
from uuid import UUID

from app.modules.soap_notes.public.dto import SOAPNoteSummaryDTO


class SOAPNoteQueryPort(ABC):
    @abstractmethod
    async def soap_note_exists_for_clinical_note(self, clinical_note_id: UUID) -> bool: ...

    @abstractmethod
    async def get_soap_note_summary(self, clinical_note_id: UUID) -> SOAPNoteSummaryDTO | None: ...
