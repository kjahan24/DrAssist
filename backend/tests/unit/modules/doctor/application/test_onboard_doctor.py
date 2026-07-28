"""Unit tests for the `OnboardDoctor` use case, using in-memory fakes for
both this module's own repositories and the Organization/Authentication
modules' public ports."""

from datetime import date
from uuid import uuid4

import pytest

from app.modules.authentication.domain.exceptions import UserNotFoundError
from app.modules.doctor.application.dto import OnboardDoctorInput
from app.modules.doctor.application.use_cases.onboard_doctor import OnboardDoctor
from app.modules.doctor.domain.enums import DoctorStatus, Gender
from app.modules.doctor.domain.events import DoctorOnboarded, DoctorProfileCreated
from app.modules.doctor.domain.exceptions import (
    DuplicateEmployeeIdError,
    UserAlreadyHasDoctorProfileError,
)
from app.modules.organization.domain.exceptions import OrganizationNotFoundError
from tests.unit.modules.doctor.application.fakes import (
    FakeDoctorProfileRepository,
    FakeDoctorRepository,
    FakeOrganizationQueryPort,
    FakeUnitOfWork,
    FakeUserQueryPort,
)


def _make_input(**overrides: object) -> OnboardDoctorInput:
    defaults: dict[str, object] = {
        "organization_id": uuid4(),
        "user_id": uuid4(),
        "employee_id": "EMP-001",
        "joining_date": date(2026, 1, 1),
        "full_name": "Dr. Jane Doe",
        "gender": Gender.FEMALE,
        "date_of_birth": date(1985, 5, 1),
    }
    defaults.update(overrides)
    return OnboardDoctorInput(**defaults)  # type: ignore[arg-type]


@pytest.fixture
def doctor_repository() -> FakeDoctorRepository:
    return FakeDoctorRepository()


@pytest.fixture
def doctor_profile_repository() -> FakeDoctorProfileRepository:
    return FakeDoctorProfileRepository()


@pytest.fixture
def unit_of_work() -> FakeUnitOfWork:
    return FakeUnitOfWork()


class TestOnboardDoctor:
    def _use_case(
        self,
        doctor_repository: FakeDoctorRepository,
        doctor_profile_repository: FakeDoctorProfileRepository,
        unit_of_work: FakeUnitOfWork,
        *,
        organization_id: object,
        user_id: object,
    ) -> OnboardDoctor:
        return OnboardDoctor(
            doctor_repository=doctor_repository,
            doctor_profile_repository=doctor_profile_repository,
            organization_query_port=FakeOrganizationQueryPort(
                existing_organization_ids={organization_id}  # type: ignore[arg-type]
            ),
            user_query_port=FakeUserQueryPort(existing_user_ids={user_id}),  # type: ignore[arg-type]
            unit_of_work=unit_of_work,
        )

    async def test_onboards_doctor_and_creates_profile_together(
        self,
        doctor_repository: FakeDoctorRepository,
        doctor_profile_repository: FakeDoctorProfileRepository,
        unit_of_work: FakeUnitOfWork,
    ) -> None:
        organization_id = uuid4()
        user_id = uuid4()
        use_case = self._use_case(
            doctor_repository,
            doctor_profile_repository,
            unit_of_work,
            organization_id=organization_id,
            user_id=user_id,
        )

        output = await use_case.execute(
            _make_input(organization_id=organization_id, user_id=user_id)
        )

        stored_doctor = await doctor_repository.get_by_id(output.doctor_id)
        assert stored_doctor is not None
        assert stored_doctor.status is DoctorStatus.ACTIVE

        stored_profile = await doctor_profile_repository.get_by_doctor_id(output.doctor_id)
        assert stored_profile is not None
        assert stored_profile.id == output.profile_id
        assert unit_of_work.committed is True

    async def test_publishes_doctor_onboarded_and_profile_created_events(
        self,
        doctor_repository: FakeDoctorRepository,
        doctor_profile_repository: FakeDoctorProfileRepository,
        unit_of_work: FakeUnitOfWork,
    ) -> None:
        organization_id = uuid4()
        user_id = uuid4()
        use_case = self._use_case(
            doctor_repository,
            doctor_profile_repository,
            unit_of_work,
            organization_id=organization_id,
            user_id=user_id,
        )

        await use_case.execute(_make_input(organization_id=organization_id, user_id=user_id))

        assert any(isinstance(e, DoctorOnboarded) for e in unit_of_work.published_events)
        assert any(isinstance(e, DoctorProfileCreated) for e in unit_of_work.published_events)

    async def test_unknown_organization_raises(
        self,
        doctor_repository: FakeDoctorRepository,
        doctor_profile_repository: FakeDoctorProfileRepository,
        unit_of_work: FakeUnitOfWork,
    ) -> None:
        user_id = uuid4()
        use_case = self._use_case(
            doctor_repository,
            doctor_profile_repository,
            unit_of_work,
            organization_id=uuid4(),
            user_id=user_id,
        )

        with pytest.raises(OrganizationNotFoundError):
            await use_case.execute(_make_input(organization_id=uuid4(), user_id=user_id))

    async def test_unknown_user_raises(
        self,
        doctor_repository: FakeDoctorRepository,
        doctor_profile_repository: FakeDoctorProfileRepository,
        unit_of_work: FakeUnitOfWork,
    ) -> None:
        organization_id = uuid4()
        use_case = self._use_case(
            doctor_repository,
            doctor_profile_repository,
            unit_of_work,
            organization_id=organization_id,
            user_id=uuid4(),
        )

        with pytest.raises(UserNotFoundError):
            await use_case.execute(_make_input(organization_id=organization_id, user_id=uuid4()))

    async def test_user_can_have_at_most_one_doctor_profile(
        self,
        doctor_repository: FakeDoctorRepository,
        doctor_profile_repository: FakeDoctorProfileRepository,
        unit_of_work: FakeUnitOfWork,
    ) -> None:
        organization_id = uuid4()
        user_id = uuid4()
        use_case = self._use_case(
            doctor_repository,
            doctor_profile_repository,
            unit_of_work,
            organization_id=organization_id,
            user_id=user_id,
        )

        await use_case.execute(
            _make_input(organization_id=organization_id, user_id=user_id, employee_id="EMP-001")
        )

        with pytest.raises(UserAlreadyHasDoctorProfileError):
            await use_case.execute(
                _make_input(organization_id=organization_id, user_id=user_id, employee_id="EMP-002")
            )

    async def test_duplicate_employee_id_within_organization_is_rejected(
        self,
        doctor_repository: FakeDoctorRepository,
        doctor_profile_repository: FakeDoctorProfileRepository,
        unit_of_work: FakeUnitOfWork,
    ) -> None:
        organization_id = uuid4()
        first_user_id = uuid4()
        second_user_id = uuid4()
        use_case = OnboardDoctor(
            doctor_repository=doctor_repository,
            doctor_profile_repository=doctor_profile_repository,
            organization_query_port=FakeOrganizationQueryPort(
                existing_organization_ids={organization_id}
            ),
            user_query_port=FakeUserQueryPort(existing_user_ids={first_user_id, second_user_id}),
            unit_of_work=unit_of_work,
        )

        await use_case.execute(
            _make_input(
                organization_id=organization_id, user_id=first_user_id, employee_id="EMP-001"
            )
        )

        with pytest.raises(DuplicateEmployeeIdError):
            await use_case.execute(
                _make_input(
                    organization_id=organization_id,
                    user_id=second_user_id,
                    employee_id="EMP-001",
                )
            )
