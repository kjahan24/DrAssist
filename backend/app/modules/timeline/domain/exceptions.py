"""Domain exceptions for the Personal Health Timeline module.

Defined locally rather than imported from the owning modules — the same
"no module exposes a not-found error a peer module is allowed to import"
reasoning `app.modules.appointment.domain.exceptions` and
`app.modules.documents.domain.exceptions` already establish for this
codebase.

`VisitOwnershipMismatchError`/`AppointmentOwnershipMismatchError` protect
against a cross-patient data leak: if a caller supplies a `visit_id`/
`appointment_id` filter alongside `patient_id`, that visit/appointment
must actually belong to the requested patient — otherwise a
narrower-scoped source fetch (e.g. `list_documents_for_visit`) could
return another patient's records under this patient's timeline. See
`application/services/timeline_query_service.py`.
"""

from uuid import UUID

from app.shared.domain.exceptions import DomainError


class PatientNotFoundError(DomainError):
    def __init__(self, patient_id: UUID) -> None:
        super().__init__(f"no patient found with id {patient_id}")
        self.patient_id = patient_id


class VisitOwnershipMismatchError(DomainError):
    def __init__(self, visit_id: UUID) -> None:
        super().__init__(f"visit {visit_id} does not belong to this patient")
        self.visit_id = visit_id


class AppointmentOwnershipMismatchError(DomainError):
    def __init__(self, appointment_id: UUID) -> None:
        super().__init__(f"appointment {appointment_id} does not belong to this patient")
        self.appointment_id = appointment_id
