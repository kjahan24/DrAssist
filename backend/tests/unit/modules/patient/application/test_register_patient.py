"""Unit tests for the `RegisterPatient` use case, using in-memory fakes for
both this module's own repository and the Organization module's public
port."""

from datetime import date
from uuid import uuid4

import pytest

from app.modules.organization.domain.exceptions import OrganizationNotFoundError
from app.modules.patient.application.dto import RegisterPatientInput
from app.modules.patient.application.use_cases.register_patient import RegisterPatient
from app.modules.patient.domain.enums import Gender, PatientStatus
from app.modules.patient.domain.events import PatientRegistered
from app.modules.patient.domain.exceptions import DuplicatePatientNumberError
from app.shared.domain.common_value_objects.email_address import InvalidEmailAddressError
from tests.unit.modules.patient.application.fakes import (
    FakeOrganizationQueryPort,
    FakePatientRepository,
    FakeUnitOfWork,
)


def _make_input(**overrides: object) -> RegisterPatientInput:
    defaults: dict[str, object] = {
        "organization_id": uuid4(),
        "patient_number": "PAT-001",
        "first_name": "Jane",
        "last_name": "Doe",
        "gender": Gender.FEMALE,
        "date_of_birth": date(1990, 1, 1),
    }
    defaults.update(overrides)
    return RegisterPatientInput(**defaults)  # type: ignore[arg-type]


@pytest.fixture
def patient_repository() -> FakePatientRepository:
    return FakePatientRepository()


@pytest.fixture
def unit_of_work() -> FakeUnitOfWork:
    return FakeUnitOfWork()


def _use_case(
    patient_repository: FakePatientRepository,
    unit_of_work: FakeUnitOfWork,
    *,
    organization_id: object,
) -> RegisterPatient:
    return RegisterPatient(
        patient_repository=patient_repository,
        organization_query_port=FakeOrganizationQueryPort(
            existing_organization_ids={organization_id}  # type: ignore[arg-type]
        ),
        unit_of_work=unit_of_work,
    )


class TestRegisterPatient:
    async def test_registers_patient(
        self,
        patient_repository: FakePatientRepository,
        unit_of_work: FakeUnitOfWork,
    ) -> None:
        organization_id = uuid4()
        use_case = _use_case(patient_repository, unit_of_work, organization_id=organization_id)

        output = await use_case.execute(_make_input(organization_id=organization_id))

        stored = await patient_repository.get_by_id(output.patient_id)
        assert stored is not None
        assert stored.status is PatientStatus.ACTIVE
        assert unit_of_work.committed is True

    async def test_publishes_patient_registered_event(
        self,
        patient_repository: FakePatientRepository,
        unit_of_work: FakeUnitOfWork,
    ) -> None:
        organization_id = uuid4()
        use_case = _use_case(patient_repository, unit_of_work, organization_id=organization_id)

        await use_case.execute(_make_input(organization_id=organization_id))

        assert any(isinstance(e, PatientRegistered) for e in unit_of_work.published_events)

    async def test_unknown_organization_raises(
        self,
        patient_repository: FakePatientRepository,
        unit_of_work: FakeUnitOfWork,
    ) -> None:
        use_case = _use_case(patient_repository, unit_of_work, organization_id=uuid4())

        with pytest.raises(OrganizationNotFoundError):
            await use_case.execute(_make_input(organization_id=uuid4()))

    async def test_duplicate_patient_number_within_organization_is_rejected(
        self,
        patient_repository: FakePatientRepository,
        unit_of_work: FakeUnitOfWork,
    ) -> None:
        organization_id = uuid4()
        use_case = _use_case(patient_repository, unit_of_work, organization_id=organization_id)

        await use_case.execute(
            _make_input(organization_id=organization_id, patient_number="PAT-001")
        )

        with pytest.raises(DuplicatePatientNumberError):
            await use_case.execute(
                _make_input(organization_id=organization_id, patient_number="PAT-001")
            )

    async def test_same_patient_number_in_different_organizations_is_allowed(
        self,
        patient_repository: FakePatientRepository,
        unit_of_work: FakeUnitOfWork,
    ) -> None:
        org_a = uuid4()
        org_b = uuid4()
        use_case = RegisterPatient(
            patient_repository=patient_repository,
            organization_query_port=FakeOrganizationQueryPort(
                existing_organization_ids={org_a, org_b}
            ),
            unit_of_work=unit_of_work,
        )

        await use_case.execute(_make_input(organization_id=org_a, patient_number="PAT-001"))
        output_b = await use_case.execute(
            _make_input(organization_id=org_b, patient_number="PAT-001")
        )

        stored_b = await patient_repository.get_by_id(output_b.patient_id)
        assert stored_b is not None
        assert stored_b.organization_id == org_b

    async def test_invalid_email_format_is_rejected(
        self,
        patient_repository: FakePatientRepository,
        unit_of_work: FakeUnitOfWork,
    ) -> None:
        organization_id = uuid4()
        use_case = _use_case(patient_repository, unit_of_work, organization_id=organization_id)

        with pytest.raises(InvalidEmailAddressError):
            await use_case.execute(
                _make_input(organization_id=organization_id, email="not-an-email")
            )
