"""Read-only queries for the Patient module's six sub-resource aggregates
(`PatientContact`, `EmergencyContact`, `Insurance`, `PatientAllergy`,
`PatientMedication`, `PatientMedicalCondition`).

Added by the REST APIs task — see `application/dto.py`'s own "Sub-resource
read models" section for the full reasoning. Six small classes, one per
aggregate, each depending on only its own repository — deliberately not
folded into `PatientQueryService` (which would need six more required
constructor parameters, a breaking change for every existing caller) and
deliberately not one shared class with six repositories injected (same
problem, just moved). This mirrors the precedent
`app.modules.schedule.application.services` already sets: `DoctorSchedule`
and `DoctorTimeOff` get their own `DoctorScheduleQueryService`/
`DoctorTimeOffQueryService` rather than being merged into one class,
even though both live in the same module.
"""

from uuid import UUID

from app.modules.patient.application.dto import (
    EmergencyContactSummaryDTO,
    InsuranceSummaryDTO,
    PatientAllergySummaryDTO,
    PatientContactSummaryDTO,
    PatientMedicalConditionSummaryDTO,
    PatientMedicationSummaryDTO,
)
from app.modules.patient.domain.entities import (
    EmergencyContact,
    Insurance,
    PatientAllergy,
    PatientContact,
    PatientMedicalCondition,
    PatientMedication,
)
from app.modules.patient.domain.repositories import (
    EmergencyContactRepository,
    InsuranceRepository,
    PatientAllergyRepository,
    PatientContactRepository,
    PatientMedicalConditionRepository,
    PatientMedicationRepository,
)


class PatientContactQueryService:
    def __init__(self, *, patient_contact_repository: PatientContactRepository) -> None:
        self._contacts = patient_contact_repository

    async def get_contact_summary(self, contact_id: UUID) -> PatientContactSummaryDTO | None:
        contact = await self._contacts.get_by_id(contact_id)
        return _contact_to_summary(contact) if contact is not None else None

    async def list_contacts_for_patient(self, patient_id: UUID) -> list[PatientContactSummaryDTO]:
        contacts = await self._contacts.list_by_patient(patient_id)
        return [_contact_to_summary(contact) for contact in contacts]


def _contact_to_summary(contact: PatientContact) -> PatientContactSummaryDTO:
    return PatientContactSummaryDTO(
        contact_id=contact.id,
        organization_id=contact.organization_id,
        patient_id=contact.patient_id,
        contact_type=contact.contact_type,
        phone_number=str(contact.phone_number),
        email=str(contact.email) if contact.email is not None else None,
        is_primary=contact.is_primary,
        is_verified=contact.is_verified,
    )


class EmergencyContactQueryService:
    def __init__(self, *, emergency_contact_repository: EmergencyContactRepository) -> None:
        self._contacts = emergency_contact_repository

    async def get_contact_summary(self, contact_id: UUID) -> EmergencyContactSummaryDTO | None:
        contact = await self._contacts.get_by_id(contact_id)
        return _emergency_contact_to_summary(contact) if contact is not None else None

    async def list_contacts_for_patient(self, patient_id: UUID) -> list[EmergencyContactSummaryDTO]:
        contacts = await self._contacts.list_by_patient(patient_id)
        return [_emergency_contact_to_summary(contact) for contact in contacts]


def _emergency_contact_to_summary(contact: EmergencyContact) -> EmergencyContactSummaryDTO:
    return EmergencyContactSummaryDTO(
        contact_id=contact.id,
        organization_id=contact.organization_id,
        patient_id=contact.patient_id,
        full_name=contact.full_name,
        relationship=contact.relationship,
        phone_number=str(contact.phone_number),
        email=str(contact.email) if contact.email is not None else None,
        address=contact.address,
        priority=contact.priority,
        is_primary=contact.is_primary,
    )


class InsuranceQueryService:
    def __init__(self, *, insurance_repository: InsuranceRepository) -> None:
        self._insurance = insurance_repository

    async def get_insurance_summary(self, insurance_id: UUID) -> InsuranceSummaryDTO | None:
        insurance = await self._insurance.get_by_id(insurance_id)
        return _insurance_to_summary(insurance) if insurance is not None else None

    async def list_insurance_for_patient(self, patient_id: UUID) -> list[InsuranceSummaryDTO]:
        policies = await self._insurance.list_by_patient(patient_id)
        return [_insurance_to_summary(policy) for policy in policies]


def _insurance_to_summary(insurance: Insurance) -> InsuranceSummaryDTO:
    return InsuranceSummaryDTO(
        insurance_id=insurance.id,
        organization_id=insurance.organization_id,
        patient_id=insurance.patient_id,
        provider_name=insurance.provider_name,
        policy_number=insurance.policy_number,
        member_id=insurance.member_id,
        group_number=insurance.group_number,
        coverage_type=insurance.coverage_type,
        effective_date=insurance.effective_date,
        expiry_date=insurance.expiry_date,
        status=insurance.status,
    )


class PatientAllergyQueryService:
    def __init__(self, *, patient_allergy_repository: PatientAllergyRepository) -> None:
        self._allergies = patient_allergy_repository

    async def get_allergy_summary(self, allergy_id: UUID) -> PatientAllergySummaryDTO | None:
        allergy = await self._allergies.get_by_id(allergy_id)
        return _allergy_to_summary(allergy) if allergy is not None else None

    async def list_allergies_for_patient(self, patient_id: UUID) -> list[PatientAllergySummaryDTO]:
        allergies = await self._allergies.list_by_patient(patient_id)
        return [_allergy_to_summary(allergy) for allergy in allergies]


def _allergy_to_summary(allergy: PatientAllergy) -> PatientAllergySummaryDTO:
    return PatientAllergySummaryDTO(
        allergy_id=allergy.id,
        organization_id=allergy.organization_id,
        patient_id=allergy.patient_id,
        allergy_type=allergy.allergy_type,
        allergen_name=allergy.allergen_name,
        severity=allergy.severity,
        reaction=allergy.reaction,
        onset_date=allergy.onset_date,
        status=allergy.status,
        notes=allergy.notes,
        verified_by=allergy.verified_by,
        verified_date=allergy.verified_date,
    )


class PatientMedicationQueryService:
    def __init__(self, *, patient_medication_repository: PatientMedicationRepository) -> None:
        self._medications = patient_medication_repository

    async def get_medication_summary(
        self, medication_id: UUID
    ) -> PatientMedicationSummaryDTO | None:
        medication = await self._medications.get_by_id(medication_id)
        return _medication_to_summary(medication) if medication is not None else None

    async def list_medications_for_patient(
        self, patient_id: UUID
    ) -> list[PatientMedicationSummaryDTO]:
        medications = await self._medications.list_by_patient(patient_id)
        return [_medication_to_summary(medication) for medication in medications]


def _medication_to_summary(medication: PatientMedication) -> PatientMedicationSummaryDTO:
    return PatientMedicationSummaryDTO(
        medication_id=medication.id,
        organization_id=medication.organization_id,
        patient_id=medication.patient_id,
        prescribed_by=medication.prescribed_by,
        medication_name=medication.medication_name,
        generic_name=medication.generic_name,
        brand_name=medication.brand_name,
        dosage=medication.dosage,
        dosage_unit=medication.dosage_unit,
        route=medication.route,
        frequency=medication.frequency,
        indication=medication.indication,
        start_date=medication.start_date,
        end_date=medication.end_date,
        is_current=medication.is_current,
        adherence_status=medication.adherence_status,
        instructions=medication.instructions,
        notes=medication.notes,
    )


class PatientMedicalConditionQueryService:
    def __init__(
        self, *, patient_medical_condition_repository: PatientMedicalConditionRepository
    ) -> None:
        self._conditions = patient_medical_condition_repository

    async def get_condition_summary(
        self, condition_id: UUID
    ) -> PatientMedicalConditionSummaryDTO | None:
        condition = await self._conditions.get_by_id(condition_id)
        return _condition_to_summary(condition) if condition is not None else None

    async def list_conditions_for_patient(
        self, patient_id: UUID
    ) -> list[PatientMedicalConditionSummaryDTO]:
        conditions = await self._conditions.list_by_patient(patient_id)
        return [_condition_to_summary(condition) for condition in conditions]


def _condition_to_summary(
    condition: PatientMedicalCondition,
) -> PatientMedicalConditionSummaryDTO:
    return PatientMedicalConditionSummaryDTO(
        condition_id=condition.id,
        organization_id=condition.organization_id,
        patient_id=condition.patient_id,
        diagnosed_by=condition.diagnosed_by,
        condition_name=condition.condition_name,
        icd10_code=str(condition.icd10_code) if condition.icd10_code is not None else None,
        category=condition.category,
        severity=condition.severity,
        diagnosis_date=condition.diagnosis_date,
        onset_date=condition.onset_date,
        status=condition.status,
        is_chronic=condition.is_chronic,
        is_infectious=condition.is_infectious,
        notes=condition.notes,
        resolved_date=condition.resolved_date,
    )
