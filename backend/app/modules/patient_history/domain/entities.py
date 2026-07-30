"""Patient History module aggregate root: `PatientHistory`.

`PatientHistory` is the patient's longitudinal Electronic Medical
Record — **not** a duplicate of `Visit`, **not** `ClinicalNote` itself,
and not a live view over other modules' tables: it is an independent,
append-only ledger of *approved* clinical facts, each row a durable copy
recording that one clinical artifact (a Clinical Note, SOAP Note,
Prescription, Lab Order, Lab Result, Differential Diagnosis, ICD-10 Code,
or the Doctor Review itself) was part of a physician-approved encounter.

**"Only Approved Doctor Reviews may create Patient History"** — every
record carries `doctor_review_id`, and `organization_id`/`patient_id`/
`visit_id` are derived from that review's own linked encounter (never
independently caller-supplied), the same "true by construction"
technique every prior child-document module in this codebase uses; the
*approval-status* check itself is I/O (it must ask the Doctor Review
module whether that specific review is `Approved`), so it lives in
`application/use_cases/create_patient_history.py`, not here.

**"History records are immutable" / "Patient History is append-only"**
— unlike every other aggregate in this codebase, `PatientHistory` has no
`update_details()` (or any other mutator) at all. `create()` is the only
way this aggregate's state is ever set; nothing here can ever change a
record after it exists. There is therefore no `ensure_editable()`
either — there is no state in which this aggregate *is* editable to
guard against.

**"Duplicate history records for the same source are prohibited"** is a
cross-row invariant (checked against sibling rows keyed by
`(reference_type, reference_id)`), so it cannot live in `__post_init__`
— it is enforced by the application layer before construction (and
backed by a database-level partial unique index — see
`infrastructure/models.py`), the identical "query first, then construct"
technique `app.modules.icd10_coding.application.use_cases
.create_icd10_coding.CreateICD10Coding` already uses for its own
duplicate-code prevention.

**`reference_id` has no value object and no database foreign key**: it
is a *polymorphic* reference — `reference_type` says which of eight
different tables it points into, and Postgres has no native way to
express "this UUID column references one of N different tables"; "Every
history record references its originating clinical artifact" and
"Reference validation" are therefore enforced exclusively at the
application layer, by `PatientHistoryReferenceValidator` dispatching on
`reference_type` to the correct peer module's public port — see that
service's own docstring.

`created_from_review` is always `True` here: this task implements
exactly one creation path (an approved Doctor Review), so `create()`
hard-codes it rather than accepting it as a parameter — accepting a
caller-supplied `False` would silently imply a second, unimplemented
creation path this task never asked for. The column still exists (and
is still a plain, independently-settable field on the row) precisely so
a *future* non-review creation path — manual chart entry, a data import,
Patient Portal-submitted history — can set it to `False` without a
schema change; see `container.py`'s scope note.

All mutation goes through named methods that enforce the aggregate's
invariants and record domain events; nothing here performs I/O. Since
this aggregate has no mutator beyond `create()`, that is also the only
method that records an event (`PatientHistoryCreated`).
"""

from dataclasses import dataclass
from datetime import date
from uuid import UUID

from app.modules.patient_history.domain.enums import HistoryType, ReferenceType
from app.modules.patient_history.domain.events import PatientHistoryCreated
from app.modules.patient_history.domain.exceptions import SummaryRequiredError
from app.shared.domain.entity import AggregateRoot


@dataclass(kw_only=True, eq=False)
class PatientHistory(AggregateRoot):
    organization_id: UUID
    patient_id: UUID
    visit_id: UUID
    doctor_review_id: UUID
    history_type: HistoryType
    reference_type: ReferenceType
    reference_id: UUID
    encounter_date: date
    summary: str
    created_from_review: bool = True

    def __post_init__(self) -> None:
        if not self.summary or not self.summary.strip():
            raise SummaryRequiredError()
        self.summary = self.summary.strip()

    @classmethod
    def create(
        cls,
        *,
        organization_id: UUID,
        patient_id: UUID,
        visit_id: UUID,
        doctor_review_id: UUID,
        history_type: HistoryType,
        reference_type: ReferenceType,
        reference_id: UUID,
        encounter_date: date,
        summary: str,
    ) -> "PatientHistory":
        history = cls(
            organization_id=organization_id,
            patient_id=patient_id,
            visit_id=visit_id,
            doctor_review_id=doctor_review_id,
            history_type=history_type,
            reference_type=reference_type,
            reference_id=reference_id,
            encounter_date=encounter_date,
            summary=summary,
            created_from_review=True,
        )
        history.record_event(
            PatientHistoryCreated(
                patient_history_id=history.id,
                organization_id=organization_id,
                patient_id=patient_id,
                reference_type=reference_type.value,
                reference_id=reference_id,
            )
        )
        return history
