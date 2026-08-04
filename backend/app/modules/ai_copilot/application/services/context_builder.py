"""`ContextBuilder` — assembles a `ClinicalContext` for a patient (and,
optionally, a specific visit) from seven peer modules' public query ports
only, per this task's "Use existing public interfaces only" requirement:
`PatientQueryPort`, `PrescriptionQueryPort`, `VisitQueryPort`,
`ClinicalNoteQueryPort`, `SOAPNoteQueryPort`, `LabResultQueryPort`,
`TimelineQueryPort`.

`SOAPNoteQueryPort.get_soap_note_summary` is keyed by `clinical_note_id`,
not `patient_id` (SOAP Notes are one-to-one children of a Clinical Note,
not directly queryable by patient) — this builder resolves SOAP notes by
first listing the patient's recent clinical notes, then looking up each
one's SOAP note individually. There is no bulk/patient-level SOAP query
port to use instead.

`max_items_per_source` bounds every list-shaped section (most recent
first) — an LLM prompt has a finite context window, and a patient with
years of history could otherwise produce an unbounded prompt; this is
ordinary prompt-engineering hygiene, not a clinical judgment about which
history matters.
"""

from datetime import date
from uuid import UUID

from app.modules.ai_copilot.application.dto import ClinicalContext
from app.modules.ai_copilot.domain.exceptions import PatientNotFoundError
from app.modules.clinical_notes.public.interfaces import ClinicalNoteQueryPort
from app.modules.lab_results.public.interfaces import LabResultQueryPort
from app.modules.patient.public.interfaces import PatientQueryPort
from app.modules.prescriptions.public.interfaces import PrescriptionQueryPort
from app.modules.soap_notes.public.interfaces import SOAPNoteQueryPort
from app.modules.timeline.public.dto import TimelineFilterInput
from app.modules.timeline.public.interfaces import TimelineQueryPort
from app.modules.visit.public.interfaces import VisitQueryPort

_DEFAULT_MAX_ITEMS_PER_SOURCE = 10


class ContextBuilder:
    def __init__(
        self,
        *,
        patient_query_port: PatientQueryPort,
        prescription_query_port: PrescriptionQueryPort,
        visit_query_port: VisitQueryPort,
        clinical_note_query_port: ClinicalNoteQueryPort,
        soap_note_query_port: SOAPNoteQueryPort,
        lab_result_query_port: LabResultQueryPort,
        timeline_query_port: TimelineQueryPort,
        max_items_per_source: int = _DEFAULT_MAX_ITEMS_PER_SOURCE,
    ) -> None:
        self._patients = patient_query_port
        self._prescriptions = prescription_query_port
        self._visits = visit_query_port
        self._clinical_notes = clinical_note_query_port
        self._soap_notes = soap_note_query_port
        self._lab_results = lab_result_query_port
        self._timeline = timeline_query_port
        self._max_items = max_items_per_source

    async def build(self, patient_id: UUID, *, visit_id: UUID | None = None) -> ClinicalContext:
        patient = await self._patients.get_patient_summary(patient_id)
        if patient is None:
            raise PatientNotFoundError(patient_id)

        allergies = await self._patients.list_allergies_for_patient(patient_id)
        conditions = await self._patients.list_medical_conditions_for_patient(patient_id)
        medications = await self._prescriptions.list_prescriptions_for_patient(patient_id)
        visits = await self._visits.list_visits_for_patient(patient_id)
        clinical_notes = await self._clinical_notes.list_clinical_notes_for_patient(patient_id)
        lab_results = await self._lab_results.list_lab_results_for_patient(patient_id)

        recent_visits = sorted(visits, key=lambda v: v.visit_date or date.min, reverse=True)[
            : self._max_items
        ]
        recent_notes = sorted(clinical_notes, key=lambda n: n.encounter_datetime, reverse=True)[
            : self._max_items
        ]
        recent_labs = sorted(lab_results, key=lambda r: r.reported_at, reverse=True)[
            : self._max_items
        ]

        soap_notes = []
        for note in recent_notes:
            soap_note = await self._soap_notes.get_soap_note_summary(note.clinical_note_id)
            if soap_note is not None:
                soap_notes.append(soap_note)

        timeline_page = await self._timeline.get_patient_timeline(
            patient_id,
            filters=TimelineFilterInput(visit_id=visit_id),
            offset=0,
            limit=self._max_items,
        )

        return ClinicalContext(
            patient=patient,
            allergies=tuple(allergies[: self._max_items]),
            medications=tuple(medications[: self._max_items]),
            conditions=tuple(conditions[: self._max_items]),
            visits=tuple(recent_visits),
            clinical_notes=tuple(recent_notes),
            soap_notes=tuple(soap_notes),
            lab_results=tuple(recent_labs),
            timeline_events=tuple(timeline_page.items),
        )
