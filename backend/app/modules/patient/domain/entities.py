"""Patient module aggregate root: `Patient`.

A single aggregate for this foundation task — see
`app.modules.patient.container` for the module's scope note. All
mutation goes through named methods that enforce the aggregate's
invariants and record domain events; nothing here performs I/O beyond
reading the wall clock for the "date of birth cannot be in the future"
check (the same precedent `AggregateRoot.touch()` already establishes for
timestamps).
"""

from dataclasses import dataclass
from datetime import date
from uuid import UUID

from app.modules.patient.domain.enums import BloodGroup, Gender, MaritalStatus, PatientStatus
from app.modules.patient.domain.events import (
    PatientDetailsUpdated,
    PatientRegistered,
    PatientStatusChanged,
)
from app.modules.patient.domain.exceptions import (
    FirstNameRequiredError,
    FutureDateOfBirthError,
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
