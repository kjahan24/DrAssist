"""Data Transfer Objects for the AI Clinical Copilot module's application
layer.

`ClinicalContext` is an application-layer, not domain-layer, type
specifically because it bundles other modules' `public/` summary DTOs
directly (Patient, Prescription, Visit, Clinical Note, SOAP Note, Lab
Result, Timeline) — exactly the kind of cross-module composition every
other module's own use cases already do at the application layer (e.g.
`app.modules.family_access.application.use_cases.invite_caregiver` importing
`PatientSummaryDTO`/`UserSummaryDTO`), never inside `domain/`, per that
layer's purity rule.

`ClinicalContext.medications` is sourced from
`app.modules.prescriptions.public.interfaces.PrescriptionQueryPort`, not a
`patient_medications` read — the Patient module's own
`PatientMedicationSummaryDTO` exists in its `application/dto.py` but was
never re-exported past its `public/` boundary (only allergies and medical
conditions were, by the Personal Health Timeline task); per this task's
"never modify completed modules" rule, this module cannot add that
exposure itself. `PrescriptionQueryPort` already documents itself as the
contract "every future medication-aware module... AI Prescription
Review... is expected to depend on" for exactly this purpose, so this is
the correct source, not a workaround.
"""

from dataclasses import dataclass
from uuid import UUID

from app.modules.ai_copilot.domain.enums import CopilotOutputFormat
from app.modules.ai_copilot.domain.value_objects import AISession
from app.modules.clinical_notes.public.dto import ClinicalNoteSummaryDTO
from app.modules.lab_results.public.dto import LabResultSummaryDTO
from app.modules.patient.public.dto import (
    PatientAllergySummaryDTO,
    PatientMedicalConditionSummaryDTO,
    PatientSummaryDTO,
)
from app.modules.prescriptions.public.dto import PrescriptionSummaryDTO
from app.modules.soap_notes.public.dto import SOAPNoteSummaryDTO
from app.modules.timeline.public.dto import TimelineEventDTO
from app.modules.visit.public.dto import VisitSummaryDTO


@dataclass(frozen=True, slots=True)
class ClinicalContext:
    patient: PatientSummaryDTO
    allergies: tuple[PatientAllergySummaryDTO, ...]
    medications: tuple[PrescriptionSummaryDTO, ...]
    conditions: tuple[PatientMedicalConditionSummaryDTO, ...]
    visits: tuple[VisitSummaryDTO, ...]
    clinical_notes: tuple[ClinicalNoteSummaryDTO, ...]
    soap_notes: tuple[SOAPNoteSummaryDTO, ...]
    lab_results: tuple[LabResultSummaryDTO, ...]
    timeline_events: tuple[TimelineEventDTO, ...]


@dataclass(frozen=True, slots=True)
class AIResponse:
    output_format: CopilotOutputFormat
    raw_text: str
    parsed_content: object
    session: AISession

    @property
    def request_id(self) -> UUID:
        """Alias for `session.request_id` — see `AppointmentSummaryDTO.id`'s
        own docstring in `app.modules.appointment.application.dto` for the
        general "expose the natural key at the top level too" reasoning
        this follows."""
        return self.session.request_id
