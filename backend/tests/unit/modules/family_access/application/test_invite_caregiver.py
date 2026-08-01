"""Unit tests for the `InviteCaregiver` use case, using in-memory fakes
for this module's own repository and the Patient/Authentication
modules' public ports."""

from uuid import uuid4

import pytest

from app.modules.family_access.application.dto import InviteCaregiverInput
from app.modules.family_access.application.use_cases.invite_caregiver import InviteCaregiver
from app.modules.family_access.domain.enums import AccessLevel, FamilyAccessStatus, Relationship
from app.modules.family_access.domain.events import FamilyAccessInvited
from app.modules.family_access.domain.exceptions import (
    CaregiverNotFoundError,
    DuplicateActiveAccessError,
    PatientNotFoundError,
)
from tests.unit.modules.family_access.application.fakes import (
    FakeFamilyAccessRepository,
    FakePatientQueryPort,
    FakeUnitOfWork,
    FakeUserQueryPort,
)


def _make_input(**overrides: object) -> InviteCaregiverInput:
    defaults: dict[str, object] = {
        "patient_id": uuid4(),
        "caregiver_user_id": uuid4(),
        "relationship": Relationship.SPOUSE,
        "access_level": AccessLevel.FULL_MEDICAL,
    }
    defaults.update(overrides)
    return InviteCaregiverInput(**defaults)  # type: ignore[arg-type]


@pytest.fixture
def family_access_repository() -> FakeFamilyAccessRepository:
    return FakeFamilyAccessRepository()


@pytest.fixture
def unit_of_work() -> FakeUnitOfWork:
    return FakeUnitOfWork()


def _use_case(
    family_access_repository: FakeFamilyAccessRepository,
    unit_of_work: FakeUnitOfWork,
    *,
    existing_patients: dict[object, object] | None = None,
    existing_users: dict[object, object] | None = None,
) -> InviteCaregiver:
    return InviteCaregiver(
        family_access_repository=family_access_repository,
        patient_query_port=FakePatientQueryPort(existing_patients=existing_patients),  # type: ignore[arg-type]
        user_query_port=FakeUserQueryPort(existing_users=existing_users),  # type: ignore[arg-type]
        unit_of_work=unit_of_work,
    )


class TestInviteCaregiver:
    async def test_invites_a_caregiver_for_an_existing_patient(
        self,
        family_access_repository: FakeFamilyAccessRepository,
        unit_of_work: FakeUnitOfWork,
    ) -> None:
        patient_id = uuid4()
        caregiver_user_id = uuid4()
        organization_id = uuid4()
        use_case = _use_case(
            family_access_repository,
            unit_of_work,
            existing_patients={patient_id: organization_id},
            existing_users={caregiver_user_id: organization_id},
        )

        output = await use_case.execute(
            _make_input(patient_id=patient_id, caregiver_user_id=caregiver_user_id)
        )

        stored = await family_access_repository.get_by_id(output.family_access_id)
        assert stored is not None
        assert stored.organization_id == organization_id
        assert stored.status is FamilyAccessStatus.PENDING
        assert unit_of_work.committed is True
        assert any(isinstance(e, FamilyAccessInvited) for e in unit_of_work.published_events)
        # The raw token is a URL-safe, high-entropy string — not the hash
        # persisted on the entity.
        assert output.invitation_token != str(stored.invitation_token)
        assert len(output.invitation_token) > 32

    async def test_unknown_patient_raises(
        self,
        family_access_repository: FakeFamilyAccessRepository,
        unit_of_work: FakeUnitOfWork,
    ) -> None:
        use_case = _use_case(family_access_repository, unit_of_work)

        with pytest.raises(PatientNotFoundError):
            await use_case.execute(_make_input(patient_id=uuid4()))

    async def test_unknown_caregiver_raises(
        self,
        family_access_repository: FakeFamilyAccessRepository,
        unit_of_work: FakeUnitOfWork,
    ) -> None:
        patient_id = uuid4()
        use_case = _use_case(
            family_access_repository,
            unit_of_work,
            existing_patients={patient_id: uuid4()},
        )

        with pytest.raises(CaregiverNotFoundError):
            await use_case.execute(_make_input(patient_id=patient_id, caregiver_user_id=uuid4()))

    async def test_caregiver_from_a_different_organization_raises(
        self,
        family_access_repository: FakeFamilyAccessRepository,
        unit_of_work: FakeUnitOfWork,
    ) -> None:
        patient_id = uuid4()
        caregiver_user_id = uuid4()
        use_case = _use_case(
            family_access_repository,
            unit_of_work,
            existing_patients={patient_id: uuid4()},
            existing_users={caregiver_user_id: uuid4()},
        )

        with pytest.raises(CaregiverNotFoundError):
            await use_case.execute(
                _make_input(patient_id=patient_id, caregiver_user_id=caregiver_user_id)
            )

    async def test_duplicate_active_access_is_rejected(
        self,
        family_access_repository: FakeFamilyAccessRepository,
        unit_of_work: FakeUnitOfWork,
    ) -> None:
        patient_id = uuid4()
        caregiver_user_id = uuid4()
        organization_id = uuid4()
        use_case = _use_case(
            family_access_repository,
            unit_of_work,
            existing_patients={patient_id: organization_id},
            existing_users={caregiver_user_id: organization_id},
        )
        await use_case.execute(
            _make_input(patient_id=patient_id, caregiver_user_id=caregiver_user_id)
        )

        with pytest.raises(DuplicateActiveAccessError):
            await use_case.execute(
                _make_input(patient_id=patient_id, caregiver_user_id=caregiver_user_id)
            )

    async def test_a_second_caregiver_for_the_same_patient_is_allowed(
        self,
        family_access_repository: FakeFamilyAccessRepository,
        unit_of_work: FakeUnitOfWork,
    ) -> None:
        patient_id = uuid4()
        first_caregiver = uuid4()
        second_caregiver = uuid4()
        organization_id = uuid4()
        use_case = _use_case(
            family_access_repository,
            unit_of_work,
            existing_patients={patient_id: organization_id},
            existing_users={first_caregiver: organization_id, second_caregiver: organization_id},
        )
        await use_case.execute(
            _make_input(patient_id=patient_id, caregiver_user_id=first_caregiver)
        )

        output = await use_case.execute(
            _make_input(patient_id=patient_id, caregiver_user_id=second_caregiver)
        )

        stored = await family_access_repository.get_by_id(output.family_access_id)
        assert stored is not None
        assert stored.caregiver_user_id == second_caregiver
