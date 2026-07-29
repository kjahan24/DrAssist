"""SOAP Notes module aggregate root: `SOAPNote`.

`SOAPNote` extends `ClinicalNote` — it does not replace it. It is a
one-to-one child of a specific `ClinicalNote` (`clinical_note_id`,
unique), the same one-to-one shape
`app.modules.vital_signs.domain.entities.VisitVitalSigns` uses for
`Visit`, just one level further down the hierarchy. `organization_id`,
`patient_id`, `visit_id`, and `doctor_id` are not independently
caller-supplied here at all — the application layer derives every one of
them from the referenced `ClinicalNote`'s own summary (see
`application/use_cases/create_soap_note.py`), which is *stronger* than
validating a match after the fact: "Patient, Visit, Doctor and
Organization must match the linked Clinical Note" cannot be violated,
because these fields are never independently trusted input to begin
with — the same reasoning `app.modules.clinical_notes.domain.entities`
already documents for deriving `organization_id` from `Visit` rather
than accepting it directly.

No value object wraps any field here: the four identity FKs above have
no invariant intrinsic to *themselves* (their consistency requirement is
against an external aggregate, not a relationship between two of this
entity's own fields — unlike `BloodPressure`/`Signature`, which validate
something wholly self-contained), and the seven SOAP text fields are
plain nullable strings with no stated format, the same reasoning
`app.modules.diagnosis.domain.entities` documents for `icd10_code`.

**This aggregate deliberately has no status field of its own** — "Clinical
Note status remains the source of truth for editability" is this
module's own business rule. `update_details()` therefore performs *no*
Draft/Signed/Locked check itself (contrast every prior module's
`update_details()`, which self-enforces its own status): that check
requires knowing the *parent* `ClinicalNote`'s current status, which
this domain layer cannot see (aggregates never reach across module
boundaries, and read the status via I/O). The read-only guard is
therefore enforced once, at the application layer, immediately before
`update_details()` is ever called — see
`application/use_cases/update_soap_note.py`. This also means the DB
schema carries no `CHECK` constraint mirroring "read-only when
Signed/Locked": a `CHECK` constraint can only see *this* table's own
row, never another table's `status` column, so — unlike every other
invariant in this codebase — this one has no database-level
enforcement layer at all; it exists exclusively in the application
layer. A future iteration could close this gap with a trigger, but
nothing in this task asks for one.

All mutation goes through named methods that enforce the aggregate's
invariants and record domain events; nothing here performs I/O.
"""

from dataclasses import dataclass
from uuid import UUID

from app.modules.soap_notes.domain.events import SOAPNoteCreated, SOAPNoteUpdated
from app.shared.domain.entity import AggregateRoot


@dataclass(kw_only=True, eq=False)
class SOAPNote(AggregateRoot):
    organization_id: UUID
    clinical_note_id: UUID
    patient_id: UUID
    visit_id: UUID
    doctor_id: UUID
    chief_complaint: str | None = None
    history_of_present_illness: str | None = None
    review_of_systems: str | None = None
    physical_examination: str | None = None
    vital_sign_summary: str | None = None
    assessment: str | None = None
    plan: str | None = None

    @classmethod
    def create(
        cls,
        *,
        organization_id: UUID,
        clinical_note_id: UUID,
        patient_id: UUID,
        visit_id: UUID,
        doctor_id: UUID,
        chief_complaint: str | None = None,
        history_of_present_illness: str | None = None,
        review_of_systems: str | None = None,
        physical_examination: str | None = None,
        vital_sign_summary: str | None = None,
        assessment: str | None = None,
        plan: str | None = None,
    ) -> "SOAPNote":
        soap_note = cls(
            organization_id=organization_id,
            clinical_note_id=clinical_note_id,
            patient_id=patient_id,
            visit_id=visit_id,
            doctor_id=doctor_id,
            chief_complaint=chief_complaint,
            history_of_present_illness=history_of_present_illness,
            review_of_systems=review_of_systems,
            physical_examination=physical_examination,
            vital_sign_summary=vital_sign_summary,
            assessment=assessment,
            plan=plan,
        )
        soap_note.record_event(
            SOAPNoteCreated(
                soap_note_id=soap_note.id,
                organization_id=organization_id,
                clinical_note_id=clinical_note_id,
            )
        )
        return soap_note

    def update_details(
        self,
        *,
        chief_complaint: str | None = None,
        history_of_present_illness: str | None = None,
        review_of_systems: str | None = None,
        physical_examination: str | None = None,
        vital_sign_summary: str | None = None,
        assessment: str | None = None,
        plan: str | None = None,
    ) -> None:
        """No editability guard here — see the module docstring for why
        that check belongs to the application layer, not this method."""
        if chief_complaint is not None:
            self.chief_complaint = chief_complaint
        if history_of_present_illness is not None:
            self.history_of_present_illness = history_of_present_illness
        if review_of_systems is not None:
            self.review_of_systems = review_of_systems
        if physical_examination is not None:
            self.physical_examination = physical_examination
        if vital_sign_summary is not None:
            self.vital_sign_summary = vital_sign_summary
        if assessment is not None:
            self.assessment = assessment
        if plan is not None:
            self.plan = plan

        self.touch()
        self.record_event(
            SOAPNoteUpdated(soap_note_id=self.id, clinical_note_id=self.clinical_note_id)
        )
