"""The Lab Results module's public port — the only contract another
module may depend on. See
`docs/backend-architecture/03_module_architecture.md` and
`10_module_communication.md`.

Never import from `app.modules.lab_results.domain`, `.application`
(beyond this package), or `.infrastructure` from outside this module —
this file and `dto.py` are the entire allowed surface today. This port is
the contract every future results-aware module (AI Lab Interpretation,
Clinical Reasoning, Differential Diagnosis, ICD-10 Coding, FHIR
DiagnosticReport, HL7 ORU Messages, LIS, Patient Timeline) is expected to
depend on to read a patient's reported test results — the same shape
`app.modules.prescriptions.public.interfaces.PrescriptionQueryPort`
already establishes for its own one-to-one place under a parent
document. `is_editable` is what every one of those future consumers is
expected to check before writing an interpretation or otherwise
attaching data to a lab result.
"""

from abc import ABC, abstractmethod
from uuid import UUID

from app.modules.lab_results.public.dto import LabResultSummaryDTO


class LabResultQueryPort(ABC):
    @abstractmethod
    async def lab_result_exists_for_lab_order(self, lab_order_id: UUID) -> bool: ...

    @abstractmethod
    async def is_editable(self, lab_order_id: UUID) -> bool: ...

    @abstractmethod
    async def get_lab_result_summary(self, lab_order_id: UUID) -> LabResultSummaryDTO | None: ...

    @abstractmethod
    async def list_lab_results_for_patient(self, patient_id: UUID) -> list[LabResultSummaryDTO]: ...
