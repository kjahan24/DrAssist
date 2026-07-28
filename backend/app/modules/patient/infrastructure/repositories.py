"""Concrete SQLAlchemy repository implementation.

`add()` is "upsert": look up the row by id, create it if missing, then
overwrite its mapped columns from the domain entity's current in-memory
state — see the identical pattern (and rationale) in
`app.modules.doctor.infrastructure.repositories`.

No repository calls `session.commit()` — that is exclusively the
`UnitOfWork`'s responsibility.
"""

from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.patient.domain.entities import (
    EmergencyContact,
    Insurance,
    Patient,
    PatientAllergy,
    PatientContact,
    PatientMedication,
)
from app.modules.patient.domain.enums import AllergyStatus, ContactType
from app.modules.patient.domain.repositories import (
    EmergencyContactRepository,
    InsuranceRepository,
    PatientAllergyRepository,
    PatientContactRepository,
    PatientMedicationRepository,
    PatientRepository,
)
from app.modules.patient.infrastructure.mappers import (
    apply_emergency_contact_to_model,
    apply_insurance_to_model,
    apply_patient_allergy_to_model,
    apply_patient_contact_to_model,
    apply_patient_medication_to_model,
    apply_patient_to_model,
    emergency_contact_to_domain,
    insurance_to_domain,
    patient_allergy_to_domain,
    patient_contact_to_domain,
    patient_medication_to_domain,
    patient_to_domain,
)
from app.modules.patient.infrastructure.models import (
    EmergencyContactModel,
    InsuranceModel,
    PatientAllergyModel,
    PatientContactModel,
    PatientMedicationModel,
    PatientModel,
)


class SqlAlchemyPatientRepository(PatientRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, patient_id: UUID) -> Patient | None:
        model = await self._session.get(PatientModel, patient_id)
        if model is None or model.deleted_at is not None:
            return None
        return patient_to_domain(model)

    async def get_by_patient_number(
        self, *, organization_id: UUID, patient_number: str
    ) -> Patient | None:
        stmt = select(PatientModel).where(
            PatientModel.organization_id == organization_id,
            PatientModel.patient_number == patient_number.strip(),
            PatientModel.deleted_at.is_(None),
        )
        model = (await self._session.execute(stmt)).scalar_one_or_none()
        return patient_to_domain(model) if model is not None else None

    async def list_by_organization(
        self, organization_id: UUID, *, offset: int = 0, limit: int = 20
    ) -> list[Patient]:
        stmt = (
            select(PatientModel)
            .where(
                PatientModel.organization_id == organization_id,
                PatientModel.deleted_at.is_(None),
            )
            .order_by(PatientModel.created_at)
            .offset(offset)
            .limit(limit)
        )
        models = (await self._session.execute(stmt)).scalars().all()
        return [patient_to_domain(model) for model in models]

    async def add(self, patient: Patient) -> None:
        model = await self._session.get(PatientModel, patient.id)
        if model is None:
            model = PatientModel()
            self._session.add(model)
        apply_patient_to_model(patient, model)


class SqlAlchemyPatientContactRepository(PatientContactRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, contact_id: UUID) -> PatientContact | None:
        model = await self._session.get(PatientContactModel, contact_id)
        if model is None or model.deleted_at is not None:
            return None
        return patient_contact_to_domain(model)

    async def list_by_patient(self, patient_id: UUID) -> list[PatientContact]:
        stmt = (
            select(PatientContactModel)
            .where(
                PatientContactModel.patient_id == patient_id,
                PatientContactModel.deleted_at.is_(None),
            )
            .order_by(PatientContactModel.created_at)
        )
        models = (await self._session.execute(stmt)).scalars().all()
        return [patient_contact_to_domain(model) for model in models]

    async def unset_primary_for_patient_and_type(
        self, patient_id: UUID, contact_type: ContactType
    ) -> None:
        stmt = (
            update(PatientContactModel)
            .where(
                PatientContactModel.patient_id == patient_id,
                PatientContactModel.contact_type == contact_type,
                PatientContactModel.is_primary.is_(True),
                PatientContactModel.deleted_at.is_(None),
            )
            .values(is_primary=False)
        )
        await self._session.execute(stmt)

    async def add(self, contact: PatientContact) -> None:
        model = await self._session.get(PatientContactModel, contact.id)
        if model is None:
            model = PatientContactModel()
            self._session.add(model)
        apply_patient_contact_to_model(contact, model)


class SqlAlchemyEmergencyContactRepository(EmergencyContactRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, contact_id: UUID) -> EmergencyContact | None:
        model = await self._session.get(EmergencyContactModel, contact_id)
        if model is None or model.deleted_at is not None:
            return None
        return emergency_contact_to_domain(model)

    async def list_by_patient(self, patient_id: UUID) -> list[EmergencyContact]:
        stmt = (
            select(EmergencyContactModel)
            .where(
                EmergencyContactModel.patient_id == patient_id,
                EmergencyContactModel.deleted_at.is_(None),
            )
            .order_by(EmergencyContactModel.created_at)
        )
        models = (await self._session.execute(stmt)).scalars().all()
        return [emergency_contact_to_domain(model) for model in models]

    async def unset_primary_for_patient(self, patient_id: UUID) -> None:
        stmt = (
            update(EmergencyContactModel)
            .where(
                EmergencyContactModel.patient_id == patient_id,
                EmergencyContactModel.is_primary.is_(True),
                EmergencyContactModel.deleted_at.is_(None),
            )
            .values(is_primary=False)
        )
        await self._session.execute(stmt)

    async def add(self, contact: EmergencyContact) -> None:
        model = await self._session.get(EmergencyContactModel, contact.id)
        if model is None:
            model = EmergencyContactModel()
            self._session.add(model)
        apply_emergency_contact_to_model(contact, model)


class SqlAlchemyInsuranceRepository(InsuranceRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, insurance_id: UUID) -> Insurance | None:
        model = await self._session.get(InsuranceModel, insurance_id)
        if model is None or model.deleted_at is not None:
            return None
        return insurance_to_domain(model)

    async def list_by_patient(self, patient_id: UUID) -> list[Insurance]:
        stmt = (
            select(InsuranceModel)
            .where(
                InsuranceModel.patient_id == patient_id,
                InsuranceModel.deleted_at.is_(None),
            )
            .order_by(InsuranceModel.created_at)
        )
        models = (await self._session.execute(stmt)).scalars().all()
        return [insurance_to_domain(model) for model in models]

    async def add(self, insurance: Insurance) -> None:
        model = await self._session.get(InsuranceModel, insurance.id)
        if model is None:
            model = InsuranceModel()
            self._session.add(model)
        apply_insurance_to_model(insurance, model)


class SqlAlchemyPatientAllergyRepository(PatientAllergyRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, allergy_id: UUID) -> PatientAllergy | None:
        model = await self._session.get(PatientAllergyModel, allergy_id)
        if model is None or model.deleted_at is not None:
            return None
        return patient_allergy_to_domain(model)

    async def list_by_patient(self, patient_id: UUID) -> list[PatientAllergy]:
        stmt = (
            select(PatientAllergyModel)
            .where(
                PatientAllergyModel.patient_id == patient_id,
                PatientAllergyModel.deleted_at.is_(None),
            )
            .order_by(PatientAllergyModel.created_at)
        )
        models = (await self._session.execute(stmt)).scalars().all()
        return [patient_allergy_to_domain(model) for model in models]

    async def get_active_by_patient_and_allergen(
        self, *, patient_id: UUID, allergen_name: str
    ) -> PatientAllergy | None:
        stmt = select(PatientAllergyModel).where(
            PatientAllergyModel.patient_id == patient_id,
            PatientAllergyModel.allergen_name == allergen_name.strip(),
            PatientAllergyModel.status == AllergyStatus.ACTIVE,
            PatientAllergyModel.deleted_at.is_(None),
        )
        model = (await self._session.execute(stmt)).scalar_one_or_none()
        return patient_allergy_to_domain(model) if model is not None else None

    async def add(self, allergy: PatientAllergy) -> None:
        model = await self._session.get(PatientAllergyModel, allergy.id)
        if model is None:
            model = PatientAllergyModel()
            self._session.add(model)
        apply_patient_allergy_to_model(allergy, model)


class SqlAlchemyPatientMedicationRepository(PatientMedicationRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, medication_id: UUID) -> PatientMedication | None:
        model = await self._session.get(PatientMedicationModel, medication_id)
        if model is None or model.deleted_at is not None:
            return None
        return patient_medication_to_domain(model)

    async def list_by_patient(self, patient_id: UUID) -> list[PatientMedication]:
        stmt = (
            select(PatientMedicationModel)
            .where(
                PatientMedicationModel.patient_id == patient_id,
                PatientMedicationModel.deleted_at.is_(None),
            )
            .order_by(PatientMedicationModel.created_at)
        )
        models = (await self._session.execute(stmt)).scalars().all()
        return [patient_medication_to_domain(model) for model in models]

    async def add(self, medication: PatientMedication) -> None:
        model = await self._session.get(PatientMedicationModel, medication.id)
        if model is None:
            model = PatientMedicationModel()
            self._session.add(model)
        apply_patient_medication_to_model(medication, model)
