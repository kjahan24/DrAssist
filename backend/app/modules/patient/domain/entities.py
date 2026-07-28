"""Patient module aggregate roots: `Patient`, `PatientContact`,
`EmergencyContact`, `Insurance`, `PatientAllergy`, `PatientMedication`,
`PatientMedicalCondition`.

`PatientContact`, `EmergencyContact`, `Insurance`, `PatientAllergy`,
`PatientMedication`, and `PatientMedicalCondition` are modeled as their
own aggregates (many-to-one with `Patient`), the same reasoning
`DoctorLicense`/`DoctorSpecialization`/`DoctorSchedule` are independent of
`Doctor` in `app.modules.doctor.domain.entities` — each aggregate
reference to `Patient` is by ID only (never an object reference), see
`docs/backend-architecture/03_module_architecture.md`.
`PatientAllergy.verified_by`/`PatientMedication.prescribed_by`/
`PatientMedicalCondition.diagnosed_by` are likewise ID-only references to
a `Doctor` in a *different* module — validated by the application layer
via the Doctor module's public `DoctorQueryPort` (see
`application/use_cases/record_patient_allergy.py`,
`application/use_cases/add_patient_medication.py`, and
`application/use_cases/add_patient_medical_condition.py`), never by
importing across `domain/` packages. All mutation goes through named
methods that enforce the aggregate's invariants and record domain
events; nothing here performs I/O beyond reading the wall clock for
date-range checks (the same precedent `AggregateRoot.touch()` already
establishes for timestamps).
"""

from dataclasses import dataclass
from datetime import date
from uuid import UUID

from app.modules.patient.domain.enums import (
    AdherenceStatus,
    AllergySeverity,
    AllergyStatus,
    AllergyType,
    BloodGroup,
    ConditionSeverity,
    ConditionStatus,
    ContactType,
    Gender,
    InsuranceStatus,
    MaritalStatus,
    PatientStatus,
    RouteOfAdministration,
)
from app.modules.patient.domain.events import (
    EmergencyContactAdded,
    EmergencyContactUpdated,
    InsuranceAdded,
    InsuranceStatusChanged,
    InsuranceUpdated,
    PatientAllergyRecorded,
    PatientAllergyStatusChanged,
    PatientAllergyUpdated,
    PatientAllergyVerified,
    PatientContactAdded,
    PatientContactUpdated,
    PatientDetailsUpdated,
    PatientMedicalConditionReactivated,
    PatientMedicalConditionRecorded,
    PatientMedicalConditionResolved,
    PatientMedicalConditionUpdated,
    PatientMedicationAdded,
    PatientMedicationDiscontinued,
    PatientMedicationResumed,
    PatientMedicationUpdated,
    PatientRegistered,
    PatientStatusChanged,
)
from app.modules.patient.domain.exceptions import (
    AllergenNameRequiredError,
    ConditionCategoryRequiredError,
    ConditionNameRequiredError,
    DosageRequiredError,
    EmergencyContactNameRequiredError,
    EmergencyContactRelationshipRequiredError,
    EndDateRequiredForCompletedMedicationError,
    FirstNameRequiredError,
    FutureDateOfBirthError,
    InsurancePolicyNumberRequiredError,
    InsuranceProviderNameRequiredError,
    InvalidInsuranceDateRangeError,
    InvalidMedicationDateRangeError,
    InvalidResolvedDateError,
    LastNameRequiredError,
    MedicationNameRequiredError,
    PatientNumberRequiredError,
    ResolvedDateRequiredForChronicConditionError,
    VerifiedDateRequiresVerifiedByError,
)
from app.modules.patient.domain.value_objects import ICD10Code
from app.shared.domain.common_value_objects import EmailAddress, PhoneNumber
from app.shared.domain.entity import AggregateRoot


@dataclass(kw_only=True, eq=False)
class Patient(AggregateRoot):
    organization_id: UUID
    patient_number: str
    first_name: str
    last_name: str
    gender: Gender
    date_of_birth: date
    middle_name: str | None = None
    preferred_name: str | None = None
    blood_group: BloodGroup | None = None
    marital_status: MaritalStatus | None = None
    national_id: str | None = None
    passport_number: str | None = None
    phone: PhoneNumber | None = None
    email: EmailAddress | None = None
    occupation: str | None = None
    nationality: str | None = None
    language: str | None = None
    religion: str | None = None
    address_line_1: str | None = None
    address_line_2: str | None = None
    city: str | None = None
    state: str | None = None
    postal_code: str | None = None
    country: str | None = None
    photo_url: str | None = None
    remarks: str | None = None
    status: PatientStatus = PatientStatus.ACTIVE

    def __post_init__(self) -> None:
        if not self.patient_number or not self.patient_number.strip():
            raise PatientNumberRequiredError()
        self.patient_number = self.patient_number.strip()

        if not self.first_name or not self.first_name.strip():
            raise FirstNameRequiredError()
        self.first_name = self.first_name.strip()

        if not self.last_name or not self.last_name.strip():
            raise LastNameRequiredError()
        self.last_name = self.last_name.strip()

        _validate_date_of_birth(self.date_of_birth)

    @classmethod
    def register(
        cls,
        *,
        organization_id: UUID,
        patient_number: str,
        first_name: str,
        last_name: str,
        gender: Gender,
        date_of_birth: date,
        middle_name: str | None = None,
        preferred_name: str | None = None,
        blood_group: BloodGroup | None = None,
        marital_status: MaritalStatus | None = None,
        national_id: str | None = None,
        passport_number: str | None = None,
        phone: PhoneNumber | None = None,
        email: EmailAddress | None = None,
        occupation: str | None = None,
        nationality: str | None = None,
        language: str | None = None,
        religion: str | None = None,
        address_line_1: str | None = None,
        address_line_2: str | None = None,
        city: str | None = None,
        state: str | None = None,
        postal_code: str | None = None,
        country: str | None = None,
        photo_url: str | None = None,
        remarks: str | None = None,
    ) -> "Patient":
        patient = cls(
            organization_id=organization_id,
            patient_number=patient_number,
            first_name=first_name,
            last_name=last_name,
            gender=gender,
            date_of_birth=date_of_birth,
            middle_name=middle_name,
            preferred_name=preferred_name,
            blood_group=blood_group,
            marital_status=marital_status,
            national_id=national_id,
            passport_number=passport_number,
            phone=phone,
            email=email,
            occupation=occupation,
            nationality=nationality,
            language=language,
            religion=religion,
            address_line_1=address_line_1,
            address_line_2=address_line_2,
            city=city,
            state=state,
            postal_code=postal_code,
            country=country,
            photo_url=photo_url,
            remarks=remarks,
        )
        patient.record_event(
            PatientRegistered(
                patient_id=patient.id,
                organization_id=organization_id,
                patient_number=patient.patient_number,
            )
        )
        return patient

    def update_details(
        self,
        *,
        first_name: str | None = None,
        middle_name: str | None = None,
        last_name: str | None = None,
        preferred_name: str | None = None,
        gender: Gender | None = None,
        date_of_birth: date | None = None,
        blood_group: BloodGroup | None = None,
        marital_status: MaritalStatus | None = None,
        national_id: str | None = None,
        passport_number: str | None = None,
        phone: PhoneNumber | None = None,
        email: EmailAddress | None = None,
        occupation: str | None = None,
        nationality: str | None = None,
        language: str | None = None,
        religion: str | None = None,
        address_line_1: str | None = None,
        address_line_2: str | None = None,
        city: str | None = None,
        state: str | None = None,
        postal_code: str | None = None,
        country: str | None = None,
        photo_url: str | None = None,
        remarks: str | None = None,
    ) -> None:
        if first_name is not None:
            if not first_name.strip():
                raise FirstNameRequiredError()
            self.first_name = first_name.strip()
        if middle_name is not None:
            self.middle_name = middle_name
        if last_name is not None:
            if not last_name.strip():
                raise LastNameRequiredError()
            self.last_name = last_name.strip()
        if preferred_name is not None:
            self.preferred_name = preferred_name
        if gender is not None:
            self.gender = gender
        if date_of_birth is not None:
            _validate_date_of_birth(date_of_birth)
            self.date_of_birth = date_of_birth
        if blood_group is not None:
            self.blood_group = blood_group
        if marital_status is not None:
            self.marital_status = marital_status
        if national_id is not None:
            self.national_id = national_id
        if passport_number is not None:
            self.passport_number = passport_number
        if phone is not None:
            self.phone = phone
        if email is not None:
            self.email = email
        if occupation is not None:
            self.occupation = occupation
        if nationality is not None:
            self.nationality = nationality
        if language is not None:
            self.language = language
        if religion is not None:
            self.religion = religion
        if address_line_1 is not None:
            self.address_line_1 = address_line_1
        if address_line_2 is not None:
            self.address_line_2 = address_line_2
        if city is not None:
            self.city = city
        if state is not None:
            self.state = state
        if postal_code is not None:
            self.postal_code = postal_code
        if country is not None:
            self.country = country
        if photo_url is not None:
            self.photo_url = photo_url
        if remarks is not None:
            self.remarks = remarks

        self.touch()
        self.record_event(
            PatientDetailsUpdated(patient_id=self.id, organization_id=self.organization_id)
        )

    def activate(self) -> None:
        self._set_status(PatientStatus.ACTIVE)

    def deactivate(self) -> None:
        self._set_status(PatientStatus.INACTIVE)

    def mark_deceased(self) -> None:
        self._set_status(PatientStatus.DECEASED)

    def _set_status(self, status: PatientStatus) -> None:
        if self.status is status:
            return
        self.status = status
        self.touch()
        self.record_event(
            PatientStatusChanged(
                patient_id=self.id, organization_id=self.organization_id, status=status.value
            )
        )


def _validate_date_of_birth(date_of_birth: date) -> None:
    if date_of_birth > date.today():
        raise FutureDateOfBirthError(date_of_birth)


@dataclass(kw_only=True, eq=False)
class PatientContact(AggregateRoot):
    organization_id: UUID
    patient_id: UUID
    contact_type: ContactType
    phone_number: PhoneNumber
    email: EmailAddress | None = None
    is_primary: bool = False
    is_verified: bool = False

    @classmethod
    def create(
        cls,
        *,
        organization_id: UUID,
        patient_id: UUID,
        contact_type: ContactType,
        phone_number: PhoneNumber,
        email: EmailAddress | None = None,
        is_primary: bool = False,
        is_verified: bool = False,
    ) -> "PatientContact":
        contact = cls(
            organization_id=organization_id,
            patient_id=patient_id,
            contact_type=contact_type,
            phone_number=phone_number,
            email=email,
            is_primary=is_primary,
            is_verified=is_verified,
        )
        contact.record_event(
            PatientContactAdded(
                contact_id=contact.id,
                patient_id=patient_id,
                contact_type=contact_type.value,
                is_primary=is_primary,
            )
        )
        return contact

    def update_details(
        self,
        *,
        contact_type: ContactType | None = None,
        phone_number: PhoneNumber | None = None,
        email: EmailAddress | None = None,
        is_verified: bool | None = None,
    ) -> None:
        if contact_type is not None:
            self.contact_type = contact_type
        if phone_number is not None:
            self.phone_number = phone_number
        if email is not None:
            self.email = email
        if is_verified is not None:
            self.is_verified = is_verified

        self.touch()
        self.record_event(PatientContactUpdated(contact_id=self.id, patient_id=self.patient_id))


@dataclass(kw_only=True, eq=False)
class EmergencyContact(AggregateRoot):
    organization_id: UUID
    patient_id: UUID
    full_name: str
    relationship: str
    phone_number: PhoneNumber
    email: EmailAddress | None = None
    address: str | None = None
    priority: int | None = None
    is_primary: bool = False

    def __post_init__(self) -> None:
        if not self.full_name or not self.full_name.strip():
            raise EmergencyContactNameRequiredError()
        self.full_name = self.full_name.strip()

        if not self.relationship or not self.relationship.strip():
            raise EmergencyContactRelationshipRequiredError()
        self.relationship = self.relationship.strip()

    @classmethod
    def create(
        cls,
        *,
        organization_id: UUID,
        patient_id: UUID,
        full_name: str,
        relationship: str,
        phone_number: PhoneNumber,
        email: EmailAddress | None = None,
        address: str | None = None,
        priority: int | None = None,
        is_primary: bool = False,
    ) -> "EmergencyContact":
        contact = cls(
            organization_id=organization_id,
            patient_id=patient_id,
            full_name=full_name,
            relationship=relationship,
            phone_number=phone_number,
            email=email,
            address=address,
            priority=priority,
            is_primary=is_primary,
        )
        contact.record_event(
            EmergencyContactAdded(
                contact_id=contact.id, patient_id=patient_id, is_primary=is_primary
            )
        )
        return contact

    def update_details(
        self,
        *,
        full_name: str | None = None,
        relationship: str | None = None,
        phone_number: PhoneNumber | None = None,
        email: EmailAddress | None = None,
        address: str | None = None,
        priority: int | None = None,
    ) -> None:
        if full_name is not None:
            if not full_name.strip():
                raise EmergencyContactNameRequiredError()
            self.full_name = full_name.strip()
        if relationship is not None:
            if not relationship.strip():
                raise EmergencyContactRelationshipRequiredError()
            self.relationship = relationship.strip()
        if phone_number is not None:
            self.phone_number = phone_number
        if email is not None:
            self.email = email
        if address is not None:
            self.address = address
        if priority is not None:
            self.priority = priority

        self.touch()
        self.record_event(EmergencyContactUpdated(contact_id=self.id, patient_id=self.patient_id))


@dataclass(kw_only=True, eq=False)
class Insurance(AggregateRoot):
    organization_id: UUID
    patient_id: UUID
    provider_name: str
    policy_number: str
    effective_date: date
    expiry_date: date
    member_id: str | None = None
    group_number: str | None = None
    coverage_type: str | None = None
    status: InsuranceStatus = InsuranceStatus.ACTIVE

    def __post_init__(self) -> None:
        if not self.provider_name or not self.provider_name.strip():
            raise InsuranceProviderNameRequiredError()
        self.provider_name = self.provider_name.strip()

        if not self.policy_number or not self.policy_number.strip():
            raise InsurancePolicyNumberRequiredError()
        self.policy_number = self.policy_number.strip()

        _validate_insurance_date_range(self.effective_date, self.expiry_date)

    @classmethod
    def create(
        cls,
        *,
        organization_id: UUID,
        patient_id: UUID,
        provider_name: str,
        policy_number: str,
        effective_date: date,
        expiry_date: date,
        member_id: str | None = None,
        group_number: str | None = None,
        coverage_type: str | None = None,
    ) -> "Insurance":
        insurance = cls(
            organization_id=organization_id,
            patient_id=patient_id,
            provider_name=provider_name,
            policy_number=policy_number,
            effective_date=effective_date,
            expiry_date=expiry_date,
            member_id=member_id,
            group_number=group_number,
            coverage_type=coverage_type,
        )
        insurance.record_event(
            InsuranceAdded(
                insurance_id=insurance.id,
                patient_id=patient_id,
                policy_number=insurance.policy_number,
            )
        )
        return insurance

    def is_expired(self, *, today: date) -> bool:
        return self.expiry_date < today

    def update_details(
        self,
        *,
        provider_name: str | None = None,
        policy_number: str | None = None,
        member_id: str | None = None,
        group_number: str | None = None,
        coverage_type: str | None = None,
        effective_date: date | None = None,
        expiry_date: date | None = None,
    ) -> None:
        if provider_name is not None:
            if not provider_name.strip():
                raise InsuranceProviderNameRequiredError()
            self.provider_name = provider_name.strip()
        if policy_number is not None:
            if not policy_number.strip():
                raise InsurancePolicyNumberRequiredError()
            self.policy_number = policy_number.strip()
        if member_id is not None:
            self.member_id = member_id
        if group_number is not None:
            self.group_number = group_number
        if coverage_type is not None:
            self.coverage_type = coverage_type
        if effective_date is not None or expiry_date is not None:
            new_effective_date = (
                effective_date if effective_date is not None else self.effective_date
            )
            new_expiry_date = expiry_date if expiry_date is not None else self.expiry_date
            _validate_insurance_date_range(new_effective_date, new_expiry_date)
            self.effective_date = new_effective_date
            self.expiry_date = new_expiry_date

        self.touch()
        self.record_event(InsuranceUpdated(insurance_id=self.id, patient_id=self.patient_id))

    def activate(self) -> None:
        self._set_status(InsuranceStatus.ACTIVE)

    def deactivate(self) -> None:
        self._set_status(InsuranceStatus.INACTIVE)

    def cancel(self) -> None:
        self._set_status(InsuranceStatus.CANCELLED)

    def _set_status(self, status: InsuranceStatus) -> None:
        if self.status is status:
            return
        self.status = status
        self.touch()
        self.record_event(
            InsuranceStatusChanged(
                insurance_id=self.id, patient_id=self.patient_id, status=status.value
            )
        )


def _validate_insurance_date_range(effective_date: date, expiry_date: date) -> None:
    if expiry_date <= effective_date:
        raise InvalidInsuranceDateRangeError()


@dataclass(kw_only=True, eq=False)
class PatientAllergy(AggregateRoot):
    organization_id: UUID
    patient_id: UUID
    allergy_type: AllergyType
    allergen_name: str
    severity: AllergySeverity
    reaction: str | None = None
    onset_date: date | None = None
    status: AllergyStatus = AllergyStatus.ACTIVE
    notes: str | None = None
    verified_by: UUID | None = None
    verified_date: date | None = None

    def __post_init__(self) -> None:
        if not self.allergen_name or not self.allergen_name.strip():
            raise AllergenNameRequiredError()
        self.allergen_name = self.allergen_name.strip()

        _validate_verification_pairing(
            verified_by=self.verified_by, verified_date=self.verified_date
        )

    @classmethod
    def create(
        cls,
        *,
        organization_id: UUID,
        patient_id: UUID,
        allergy_type: AllergyType,
        allergen_name: str,
        severity: AllergySeverity,
        reaction: str | None = None,
        onset_date: date | None = None,
        notes: str | None = None,
        verified_by: UUID | None = None,
        verified_date: date | None = None,
    ) -> "PatientAllergy":
        allergy = cls(
            organization_id=organization_id,
            patient_id=patient_id,
            allergy_type=allergy_type,
            allergen_name=allergen_name,
            severity=severity,
            reaction=reaction,
            onset_date=onset_date,
            notes=notes,
            verified_by=verified_by,
            verified_date=verified_date,
        )
        allergy.record_event(
            PatientAllergyRecorded(
                allergy_id=allergy.id,
                patient_id=patient_id,
                allergen_name=allergy.allergen_name,
                severity=severity.value,
            )
        )
        return allergy

    def update_details(
        self,
        *,
        allergy_type: AllergyType | None = None,
        allergen_name: str | None = None,
        severity: AllergySeverity | None = None,
        reaction: str | None = None,
        onset_date: date | None = None,
        notes: str | None = None,
    ) -> None:
        if allergy_type is not None:
            self.allergy_type = allergy_type
        if allergen_name is not None:
            if not allergen_name.strip():
                raise AllergenNameRequiredError()
            self.allergen_name = allergen_name.strip()
        if severity is not None:
            self.severity = severity
        if reaction is not None:
            self.reaction = reaction
        if onset_date is not None:
            self.onset_date = onset_date
        if notes is not None:
            self.notes = notes

        self.touch()
        self.record_event(PatientAllergyUpdated(allergy_id=self.id, patient_id=self.patient_id))

    def verify(self, *, verified_by: UUID, verified_date: date) -> None:
        self.verified_by = verified_by
        self.verified_date = verified_date
        self.touch()
        self.record_event(
            PatientAllergyVerified(
                allergy_id=self.id, patient_id=self.patient_id, verified_by=verified_by
            )
        )

    def resolve(self) -> None:
        self._set_status(AllergyStatus.RESOLVED)

    def reactivate(self) -> None:
        self._set_status(AllergyStatus.ACTIVE)

    def _set_status(self, status: AllergyStatus) -> None:
        if self.status is status:
            return
        self.status = status
        self.touch()
        self.record_event(
            PatientAllergyStatusChanged(
                allergy_id=self.id, patient_id=self.patient_id, status=status.value
            )
        )


def _validate_verification_pairing(*, verified_by: UUID | None, verified_date: date | None) -> None:
    if verified_date is not None and verified_by is None:
        raise VerifiedDateRequiresVerifiedByError()


@dataclass(kw_only=True, eq=False)
class PatientMedication(AggregateRoot):
    organization_id: UUID
    patient_id: UUID
    medication_name: str
    dosage: str
    route: RouteOfAdministration
    start_date: date
    prescribed_by: UUID | None = None
    generic_name: str | None = None
    brand_name: str | None = None
    dosage_unit: str | None = None
    frequency: str | None = None
    indication: str | None = None
    end_date: date | None = None
    is_current: bool = True
    adherence_status: AdherenceStatus = AdherenceStatus.TAKING
    instructions: str | None = None
    notes: str | None = None

    def __post_init__(self) -> None:
        if not self.medication_name or not self.medication_name.strip():
            raise MedicationNameRequiredError()
        self.medication_name = self.medication_name.strip()

        if not self.dosage or not self.dosage.strip():
            raise DosageRequiredError()
        self.dosage = self.dosage.strip()

        _validate_medication_date_range(self.start_date, self.end_date)
        _validate_completed_requires_end_date(
            is_current=self.is_current,
            adherence_status=self.adherence_status,
            end_date=self.end_date,
        )

    @classmethod
    def create(
        cls,
        *,
        organization_id: UUID,
        patient_id: UUID,
        medication_name: str,
        dosage: str,
        route: RouteOfAdministration,
        start_date: date,
        prescribed_by: UUID | None = None,
        generic_name: str | None = None,
        brand_name: str | None = None,
        dosage_unit: str | None = None,
        frequency: str | None = None,
        indication: str | None = None,
        end_date: date | None = None,
        is_current: bool = True,
        adherence_status: AdherenceStatus = AdherenceStatus.TAKING,
        instructions: str | None = None,
        notes: str | None = None,
    ) -> "PatientMedication":
        medication = cls(
            organization_id=organization_id,
            patient_id=patient_id,
            medication_name=medication_name,
            dosage=dosage,
            route=route,
            start_date=start_date,
            prescribed_by=prescribed_by,
            generic_name=generic_name,
            brand_name=brand_name,
            dosage_unit=dosage_unit,
            frequency=frequency,
            indication=indication,
            end_date=end_date,
            is_current=is_current,
            adherence_status=adherence_status,
            instructions=instructions,
            notes=notes,
        )
        medication.record_event(
            PatientMedicationAdded(
                medication_id=medication.id,
                patient_id=patient_id,
                medication_name=medication.medication_name,
            )
        )
        return medication

    def update_details(
        self,
        *,
        medication_name: str | None = None,
        generic_name: str | None = None,
        brand_name: str | None = None,
        dosage: str | None = None,
        dosage_unit: str | None = None,
        route: RouteOfAdministration | None = None,
        frequency: str | None = None,
        indication: str | None = None,
        start_date: date | None = None,
        instructions: str | None = None,
        notes: str | None = None,
    ) -> None:
        if medication_name is not None:
            if not medication_name.strip():
                raise MedicationNameRequiredError()
            self.medication_name = medication_name.strip()
        if generic_name is not None:
            self.generic_name = generic_name
        if brand_name is not None:
            self.brand_name = brand_name
        if dosage is not None:
            if not dosage.strip():
                raise DosageRequiredError()
            self.dosage = dosage.strip()
        if dosage_unit is not None:
            self.dosage_unit = dosage_unit
        if route is not None:
            self.route = route
        if frequency is not None:
            self.frequency = frequency
        if indication is not None:
            self.indication = indication
        if start_date is not None:
            _validate_medication_date_range(start_date, self.end_date)
            self.start_date = start_date
        if instructions is not None:
            self.instructions = instructions
        if notes is not None:
            self.notes = notes

        self.touch()
        self.record_event(
            PatientMedicationUpdated(medication_id=self.id, patient_id=self.patient_id)
        )

    def discontinue(
        self, *, end_date: date, adherence_status: AdherenceStatus = AdherenceStatus.STOPPED
    ) -> None:
        _validate_medication_date_range(self.start_date, end_date)
        self.is_current = False
        self.adherence_status = adherence_status
        self.end_date = end_date
        self.touch()
        self.record_event(
            PatientMedicationDiscontinued(
                medication_id=self.id, patient_id=self.patient_id, end_date=end_date
            )
        )

    def resume(self) -> None:
        if self.is_current and self.adherence_status is AdherenceStatus.TAKING:
            return
        self.is_current = True
        self.adherence_status = AdherenceStatus.TAKING
        self.end_date = None
        self.touch()
        self.record_event(
            PatientMedicationResumed(medication_id=self.id, patient_id=self.patient_id)
        )


def _validate_medication_date_range(start_date: date, end_date: date | None) -> None:
    if end_date is not None and end_date < start_date:
        raise InvalidMedicationDateRangeError()


def _validate_completed_requires_end_date(
    *, is_current: bool, adherence_status: AdherenceStatus, end_date: date | None
) -> None:
    if not is_current and adherence_status is AdherenceStatus.COMPLETED and end_date is None:
        raise EndDateRequiredForCompletedMedicationError()


@dataclass(kw_only=True, eq=False)
class PatientMedicalCondition(AggregateRoot):
    organization_id: UUID
    patient_id: UUID
    condition_name: str
    category: str
    severity: ConditionSeverity
    diagnosis_date: date
    diagnosed_by: UUID | None = None
    icd10_code: ICD10Code | None = None
    onset_date: date | None = None
    status: ConditionStatus = ConditionStatus.ACTIVE
    is_chronic: bool = False
    is_infectious: bool = False
    notes: str | None = None
    resolved_date: date | None = None

    def __post_init__(self) -> None:
        if not self.condition_name or not self.condition_name.strip():
            raise ConditionNameRequiredError()
        self.condition_name = self.condition_name.strip()

        if not self.category or not self.category.strip():
            raise ConditionCategoryRequiredError()
        self.category = self.category.strip()

        _validate_resolved_date(self.diagnosis_date, self.resolved_date)
        _validate_chronic_resolution(
            is_chronic=self.is_chronic, status=self.status, resolved_date=self.resolved_date
        )

    @classmethod
    def create(
        cls,
        *,
        organization_id: UUID,
        patient_id: UUID,
        condition_name: str,
        category: str,
        severity: ConditionSeverity,
        diagnosis_date: date,
        diagnosed_by: UUID | None = None,
        icd10_code: ICD10Code | None = None,
        onset_date: date | None = None,
        status: ConditionStatus = ConditionStatus.ACTIVE,
        is_chronic: bool = False,
        is_infectious: bool = False,
        notes: str | None = None,
        resolved_date: date | None = None,
    ) -> "PatientMedicalCondition":
        condition = cls(
            organization_id=organization_id,
            patient_id=patient_id,
            condition_name=condition_name,
            category=category,
            severity=severity,
            diagnosis_date=diagnosis_date,
            diagnosed_by=diagnosed_by,
            icd10_code=icd10_code,
            onset_date=onset_date,
            status=status,
            is_chronic=is_chronic,
            is_infectious=is_infectious,
            notes=notes,
            resolved_date=resolved_date,
        )
        condition.record_event(
            PatientMedicalConditionRecorded(
                condition_id=condition.id,
                patient_id=patient_id,
                condition_name=condition.condition_name,
            )
        )
        return condition

    def update_details(
        self,
        *,
        condition_name: str | None = None,
        category: str | None = None,
        severity: ConditionSeverity | None = None,
        diagnosis_date: date | None = None,
        icd10_code: ICD10Code | None = None,
        onset_date: date | None = None,
        is_infectious: bool | None = None,
        notes: str | None = None,
    ) -> None:
        if condition_name is not None:
            if not condition_name.strip():
                raise ConditionNameRequiredError()
            self.condition_name = condition_name.strip()
        if category is not None:
            if not category.strip():
                raise ConditionCategoryRequiredError()
            self.category = category.strip()
        if severity is not None:
            self.severity = severity
        if diagnosis_date is not None:
            _validate_resolved_date(diagnosis_date, self.resolved_date)
            self.diagnosis_date = diagnosis_date
        if icd10_code is not None:
            self.icd10_code = icd10_code
        if onset_date is not None:
            self.onset_date = onset_date
        if is_infectious is not None:
            self.is_infectious = is_infectious
        if notes is not None:
            self.notes = notes

        self.touch()
        self.record_event(
            PatientMedicalConditionUpdated(condition_id=self.id, patient_id=self.patient_id)
        )

    def resolve(self, *, resolved_date: date) -> None:
        _validate_resolved_date(self.diagnosis_date, resolved_date)
        self.status = ConditionStatus.RESOLVED
        self.resolved_date = resolved_date
        self.touch()
        self.record_event(
            PatientMedicalConditionResolved(
                condition_id=self.id, patient_id=self.patient_id, resolved_date=resolved_date
            )
        )

    def reactivate(self) -> None:
        if self.status is ConditionStatus.ACTIVE and self.resolved_date is None:
            return
        self.status = ConditionStatus.ACTIVE
        self.resolved_date = None
        self.touch()
        self.record_event(
            PatientMedicalConditionReactivated(condition_id=self.id, patient_id=self.patient_id)
        )


def _validate_resolved_date(diagnosis_date: date, resolved_date: date | None) -> None:
    if resolved_date is not None and resolved_date <= diagnosis_date:
        raise InvalidResolvedDateError()


def _validate_chronic_resolution(
    *, is_chronic: bool, status: ConditionStatus, resolved_date: date | None
) -> None:
    if is_chronic and status is ConditionStatus.RESOLVED and resolved_date is None:
        raise ResolvedDateRequiredForChronicConditionError()
