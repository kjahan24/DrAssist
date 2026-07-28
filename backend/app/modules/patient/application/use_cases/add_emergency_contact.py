"""`AddEmergencyContact` — an emergency contact always belongs to an
existing patient. When added as primary, any previously-primary emergency
contact for that patient is unset first, so "one primary emergency
contact" holds without requiring the caller to manage it."""

from app.modules.patient.application.dto import (
    AddEmergencyContactInput,
    AddEmergencyContactOutput,
)
from app.modules.patient.domain.entities import EmergencyContact
from app.modules.patient.domain.exceptions import PatientNotFoundError
from app.modules.patient.domain.repositories import EmergencyContactRepository, PatientRepository
from app.shared.application.unit_of_work import UnitOfWork
from app.shared.application.use_case import UseCase
from app.shared.domain.common_value_objects import EmailAddress, PhoneNumber


class AddEmergencyContact(UseCase[AddEmergencyContactInput, AddEmergencyContactOutput]):
    def __init__(
        self,
        *,
        emergency_contact_repository: EmergencyContactRepository,
        patient_repository: PatientRepository,
        unit_of_work: UnitOfWork,
    ) -> None:
        self._contacts = emergency_contact_repository
        self._patients = patient_repository
        self._uow = unit_of_work

    async def execute(self, input_dto: AddEmergencyContactInput) -> AddEmergencyContactOutput:
        patient = await self._patients.get_by_id(input_dto.patient_id)
        if patient is None:
            raise PatientNotFoundError(input_dto.patient_id)

        if input_dto.is_primary:
            await self._contacts.unset_primary_for_patient(patient.id)

        contact = EmergencyContact.create(
            organization_id=patient.organization_id,
            patient_id=patient.id,
            full_name=input_dto.full_name,
            relationship=input_dto.relationship,
            phone_number=PhoneNumber(input_dto.phone_number),
            email=EmailAddress(input_dto.email) if input_dto.email else None,
            address=input_dto.address,
            priority=input_dto.priority,
            is_primary=input_dto.is_primary,
        )
        await self._contacts.add(contact)
        self._uow.collect_events(contact.pull_events())
        await self._uow.commit()

        return AddEmergencyContactOutput(
            contact_id=contact.id,
            patient_id=contact.patient_id,
            full_name=contact.full_name,
            is_primary=contact.is_primary,
        )
