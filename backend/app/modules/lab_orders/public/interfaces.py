"""The Lab Orders module's public port — the only contract another module
may depend on. See `docs/backend-architecture/03_module_architecture.md`
and `10_module_communication.md`.

Never import from `app.modules.lab_orders.domain`, `.application`
(beyond this package), or `.infrastructure` from outside this module —
this file and `dto.py` are the entire allowed surface today. This port is
the contract every future lab-aware module (LIS, HL7/FHIR, Lab Results,
AI Lab Interpretation, Clinical Decision Support, Notifications) is
expected to depend on to read a patient's ordered tests — the same shape
`app.modules.clinical_notes.public.interfaces.ClinicalNoteQueryPort`
already establishes for its own one-to-many place under `Visit`.
`is_editable` is what every one of those future consumers is expected to
check before attaching a result or otherwise writing to a lab order.
"""

from abc import ABC, abstractmethod
from uuid import UUID

from app.modules.lab_orders.public.dto import LabOrderSummaryDTO


class LabOrderQueryPort(ABC):
    @abstractmethod
    async def lab_order_exists(self, lab_order_id: UUID) -> bool: ...

    @abstractmethod
    async def is_editable(self, lab_order_id: UUID) -> bool: ...

    @abstractmethod
    async def get_lab_order_summary(self, lab_order_id: UUID) -> LabOrderSummaryDTO | None: ...

    @abstractmethod
    async def list_lab_orders_for_clinical_note(
        self, clinical_note_id: UUID
    ) -> list[LabOrderSummaryDTO]: ...

    @abstractmethod
    async def list_lab_orders_for_patient(self, patient_id: UUID) -> list[LabOrderSummaryDTO]: ...
