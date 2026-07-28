"""Unit tests for the `AddInsurance` use case."""

from datetime import date
from uuid import uuid4

import pytest

from app.modules.patient.application.dto import AddInsuranceInput
from app.modules.patient.application.use_cases.add_insurance import AddInsurance
from app.modules.patient.domain.entities import Patient
from app.modules.patient.domain.enums import Gender, InsuranceStatus
from app.modules.patient.domain.events import InsuranceAdded
from app.modules.patient.domain.exceptions import (
    InvalidInsuranceDateRangeError,
    PatientNotFoundError,
)
from tests.unit.modules.patient.application.fakes import (
    FakeInsuranceRepository,
    FakePatientRepository,
    FakeUnitOfWork,
)


def _make_patient() -> Patient:
    return Patient.register(
        organization_id=uuid4(),
        patient_number="PAT-001",
        first_name="Jane",
        last_name="Doe",
        gender=Gender.FEMALE,
        date_of_birth=date(1990, 1, 1),
    )


@pytest.fixture
def insurance_repository() -> FakeInsuranceRepository:
    return FakeInsuranceRepository()


@pytest.fixture
def patient_repository() -> FakePatientRepository:
    return FakePatientRepository()


@pytest.fixture
def unit_of_work() -> FakeUnitOfWork:
    return FakeUnitOfWork()


@pytest.fixture
def use_case(
    insurance_repository: FakeInsuranceRepository,
    patient_repository: FakePatientRepository,
    unit_of_work: FakeUnitOfWork,
) -> AddInsurance:
    return AddInsurance(
        insurance_repository=insurance_repository,
        patient_repository=patient_repository,
        unit_of_work=unit_of_work,
    )


class TestAddInsurance:
    async def test_adds_insurance_for_existing_patient(
        self,
        use_case: AddInsurance,
        patient_repository: FakePatientRepository,
        insurance_repository: FakeInsuranceRepository,
        unit_of_work: FakeUnitOfWork,
    ) -> None:
        patient = _make_patient()
        await patient_repository.add(patient)

        output = await use_case.execute(
            AddInsuranceInput(
                patient_id=patient.id,
                provider_name="Acme Health",
                policy_number="POL-001",
                effective_date=date(2026, 1, 1),
                expiry_date=date(2027, 1, 1),
            )
        )

        stored = await insurance_repository.get_by_id(output.insurance_id)
        assert stored is not None
        assert stored.organization_id == patient.organization_id
        assert stored.status is InsuranceStatus.ACTIVE
        assert unit_of_work.committed is True
        assert any(isinstance(e, InsuranceAdded) for e in unit_of_work.published_events)

    async def test_unknown_patient_raises(self, use_case: AddInsurance) -> None:
        with pytest.raises(PatientNotFoundError):
            await use_case.execute(
                AddInsuranceInput(
                    patient_id=uuid4(),
                    provider_name="Acme Health",
                    policy_number="POL-001",
                    effective_date=date(2026, 1, 1),
                    expiry_date=date(2027, 1, 1),
                )
            )

    async def test_expiry_before_effective_date_is_rejected(
        self, use_case: AddInsurance, patient_repository: FakePatientRepository
    ) -> None:
        patient = _make_patient()
        await patient_repository.add(patient)

        with pytest.raises(InvalidInsuranceDateRangeError):
            await use_case.execute(
                AddInsuranceInput(
                    patient_id=patient.id,
                    provider_name="Acme Health",
                    policy_number="POL-001",
                    effective_date=date(2027, 1, 1),
                    expiry_date=date(2026, 1, 1),
                )
            )
