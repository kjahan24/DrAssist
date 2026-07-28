"""`AddPatientContact` — a contact always belongs to an existing patient.
When added as primary, any previously-primary contact of the same
`contact_type` for that patient is unset first, so "one primary contact
per contact type" holds without requiring the caller to manage it — the
same pattern
`app.modules.doctor.application.use_cases.add_doctor_specialization.AddDoctorSpecialization`
established for "one primary per parent" invariants."""

from app.modules.patient.application.dto import AddPatientContactInput, AddPatientContactOutput
from app.modules.patient.domain.entities import PatientContact
from app.modules.patient.domain.exceptions import PatientNotFoundError
from app.modules.patient.domain.repositories import PatientContactRepository, PatientRepository
from app.shared.application.unit_of_work import UnitOfWork
from app.shared.application.use_case import UseCase
from app.shared.domain.common_value_objects import EmailAddress, PhoneNumber


class AddPatientContact(UseCase[AddPatientContactInput, AddPatientContactOutput]):
    def __init__(
        self,
        *,
        patient_contact_repository: PatientContactRepository,
        patient_repository: PatientRepository,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._contacts = patient_contact_repository
        self._patients = patient_repository
        self._uow = unit_of_work

    async def execute(self, input_dto: AddPatientContactInput) -> AddPatientContactOutput:
        patient = await self._patients.get_by_id(input_dto.patient_id)
        if patient is None:
            raise PatientNotFoundError(input_dto.patient_id)

        if input_dto.is_primary:
            await self._contacts.unset_primary_for_patient_and_type(
                patient.id, input_dto.contact_type
            )

        contact = PatientContact.create(
            organization_id=patient.organization_id,
            patient_id=patient.id,
            contact_type=input_dto.contact_type,
            phone_number=PhoneNumber(input_dto.phone_number),
            email=EmailAddress(input_dto.email) if input_dto.email else None,
            is_primary=input_dto.is_primary,
            is_verified=input_dto.is_verified,
        )
        await self._contacts.add(contact)
        self._uow.collect_events(contact.pull_events())
        await self._uow.commit()

        return AddPatientContactOutput(
            contact_id=contact.id,
            patient_id=contact.patient_id,
            contact_type=contact.contact_type,
            is_primary=contact.is_primary,
        )
