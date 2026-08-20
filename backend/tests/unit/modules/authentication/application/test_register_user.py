"""Unit tests for `RegisterUser`, using in-memory fakes."""

import pytest

from app.core.security.password_hashing import verify_password
from app.modules.authentication.application.dto import RegisterUserInput
from app.modules.authentication.application.use_cases.register_user import RegisterUser
from app.modules.authentication.domain.enums import UserStatus
from app.modules.authentication.domain.events import UserRegistered
from app.modules.authentication.domain.exceptions import DuplicateEmailError
from tests.unit.modules.authentication.application.fakes import (
    FakeOrganizationProvisioningPort,
    FakeUnitOfWork,
    FakeUserRepository,
)


def _seeded() -> (
    tuple[RegisterUser, FakeUserRepository, FakeOrganizationProvisioningPort, FakeUnitOfWork]
):
    users = FakeUserRepository()
    organizations = FakeOrganizationProvisioningPort()
    uow = FakeUnitOfWork()
    use_case = RegisterUser(
        user_repository=users, organization_provisioning_port=organizations, unit_of_work=uow
    )
    return use_case, users, organizations, uow


def _input(**overrides: object) -> RegisterUserInput:
    defaults: dict[str, object] = {
        "email": "new.doctor@example.com",
        "password": "StrongPass1",
        "first_name": "Ada",
        "last_name": "Lovelace",
    }
    defaults.update(overrides)
    return RegisterUserInput(**defaults)  # type: ignore[arg-type]


class TestRegisterUser:
    async def test_provisions_a_new_organization_for_the_user(self) -> None:
        use_case, _, organizations, _ = _seeded()

        output = await use_case.execute(_input())

        assert len(organizations.provisioned) == 1
        assert organizations.provisioned[0].organization_id == output.organization_id
        assert "Ada Lovelace" in organizations.provisioned[0].name

    async def test_persists_the_user_under_the_new_organization(self) -> None:
        use_case, users, _, _ = _seeded()

        output = await use_case.execute(_input())

        stored = await users.get_by_id(output.user_id)
        assert stored is not None
        assert stored.organization_id == output.organization_id
        assert str(stored.email) == "new.doctor@example.com"
        assert stored.first_name == "Ada"
        assert stored.last_name == "Lovelace"

    async def test_activates_the_user_immediately(self) -> None:
        use_case, users, _, _ = _seeded()

        output = await use_case.execute(_input())

        stored = await users.get_by_id(output.user_id)
        assert stored is not None
        assert stored.status is UserStatus.ACTIVE

    async def test_never_stores_the_plaintext_password(self) -> None:
        use_case, users, _, _ = _seeded()

        output = await use_case.execute(_input(password="StrongPass1"))

        stored = await users.get_by_id(output.user_id)
        assert stored is not None
        assert stored.password_hash.value != "StrongPass1"
        assert verify_password("StrongPass1", stored.password_hash.value)

    async def test_commits_and_publishes_user_registered_event(self) -> None:
        use_case, _, _, uow = _seeded()

        output = await use_case.execute(_input())

        assert uow.committed is True
        assert any(
            isinstance(event, UserRegistered) and event.user_id == output.user_id
            for event in uow.published_events
        )

    async def test_raises_duplicate_email_when_already_registered_anywhere(self) -> None:
        use_case, *_ = _seeded()
        await use_case.execute(_input(email="taken@example.com"))

        with pytest.raises(DuplicateEmailError):
            await use_case.execute(_input(email="taken@example.com"))

    async def test_email_uniqueness_check_is_case_insensitive(self) -> None:
        use_case, *_ = _seeded()
        await use_case.execute(_input(email="Taken@Example.com"))

        with pytest.raises(DuplicateEmailError):
            await use_case.execute(_input(email="taken@example.com"))
