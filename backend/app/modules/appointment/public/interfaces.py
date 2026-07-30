"""The Appointment module's public port — the only contract another
module may depend on. See
`docs/backend-architecture/03_module_architecture.md` and
`10_module_communication.md`.

Never import from `app.modules.appointment.domain`, `.application`
(beyond this package), or `.infrastructure` from outside this module —
this file and `dto.py` are the entire allowed surface today. This port
is the contract every future scheduling-aware module (Schedule/
Availability, Calendar, Notification, SMS Reminder, Email Reminder,
Queue Management, Telemedicine, Patient Portal, Google Calendar, Outlook
Calendar) is expected to depend on to read a patient's or doctor's
booked appointments — the same shape
`app.modules.doctor_review.public.interfaces.DoctorReviewQueryPort`
already establishes for its own place under `ClinicalNote`. `is_editable`
is what every one of those future consumers is expected to check before
writing to, or building on top of, an appointment record.
"""

from abc import ABC, abstractmethod
from uuid import UUID

from app.modules.appointment.public.dto import AppointmentSummaryDTO


class AppointmentQueryPort(ABC):
    @abstractmethod
    async def appointment_exists(self, appointment_id: UUID) -> bool: ...

    @abstractmethod
    async def is_editable(self, appointment_id: UUID) -> bool: ...

    @abstractmethod
    async def get_appointment_summary(
        self, appointment_id: UUID
    ) -> AppointmentSummaryDTO | None: ...

    @abstractmethod
    async def get_by_appointment_number(
        self, appointment_number: str
    ) -> AppointmentSummaryDTO | None: ...

    @abstractmethod
    async def list_appointments_for_patient(
        self, patient_id: UUID
    ) -> list[AppointmentSummaryDTO]: ...

    @abstractmethod
    async def list_appointments_for_doctor(
        self, doctor_id: UUID
    ) -> list[AppointmentSummaryDTO]: ...
