"""Patient module aggregate roots: `Patient`, `PatientContact`,
`EmergencyContact`, `Insurance`.

`PatientContact`, `EmergencyContact`, and `Insurance` are modeled as their
own aggregates (many-to-one with `Patient`), the same reasoning
`DoctorLicense`/`DoctorSpecialization`/`DoctorSchedule` are independent of
`Doctor` in `app.modules.doctor.domain.entities` — each aggregate
reference to `Patient` is by ID only (never an object reference), see
`docs/backend-architecture/03_module_architecture.md`. All mutation goes
through named methods that enforce the aggregate's invariants and record
domain events; nothing here performs I/O beyond reading the wall clock for
date-range checks (the same precedent `AggregateRoot.touch()` already
establishes for timestamps).
"""

from dataclasses import dataclass
from datetime import date
from uuid import UUID

from app.modules.patient.domain.enums import (
    BloodGroup,
    ContactType,
    Gender,
    InsuranceStatus,
    MaritalStatus,
    PatientStatus,
)
from app.modules.patient.domain.events import (
    EmergencyContactAdded,
    EmergencyContactUpdated,
    InsuranceAdded,
    InsuranceStatusChanged,
    InsuranceUpdated,
    PatientContactAdded,
    PatientContactUpdated,
    PatientDetailsUpdated,
    PatientRegistered,
    PatientStatusChanged,
)
from app.modules.patient.domain.exceptions import (
    EmergencyContactNameRequiredError,
    EmergencyContactRelationshipRequiredError,
    FirstNameRequiredError,
    FutureDateOfBirthError,
    InsurancePolicyNumberRequiredError,
    InsuranceProviderNameRequiredError,
    InvalidInsuranceDateRangeError,
    LastNameRequiredError,
    PatientNumberRequiredError,
)
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
