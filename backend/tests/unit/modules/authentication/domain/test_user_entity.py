"""Unit tests for the `User` aggregate's invariants — no I/O, no fakes needed."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from app.modules.authentication.domain.entities import User
from app.modules.authentication.domain.enums import UserStatus
from app.modules.authentication.domain.events import (
    PasswordChanged,
    UserActivated,
    UserDeactivated,
    UserLocked,
    UserLoginFailed,
    UserLoginSucceeded,
    UserRegistered,
)
from app.modules.authentication.domain.value_objects import HashedPassword
from app.shared.domain.common_value_objects import EmailAddress

VALID_HASH = "$2b$12$" + "a" * 53


def _make_user(**overrides: object) -> User:
    defaults: dict[str, object] = {
        "organization_id": uuid4(),
        "email": EmailAddress("doctor@example.com"),
        "password_hash": HashedPassword(VALID_HASH),
        "first_name": "Ada",
        "last_name": "Lovelace",
    }
    defaults.update(overrides)
    return User(**defaults)  # type: ignore[arg-type]


class TestRegister:
    def test_register_sets_invited_status_and_records_event(self) -> None:
        org_id = uuid4()
        user = User.register(
            organization_id=org_id,
            email=EmailAddress("new.doctor@example.com"),
            password_hash=HashedPassword(VALID_HASH),
            first_name="Grace",
            last_name="Hopper",
        )

        assert user.status is UserStatus.INVITED
        assert user.organization_id == org_id
        events = user.pull_events()
        assert len(events) == 1
        assert isinstance(events[0], UserRegistered)
        assert events[0].email == "new.doctor@example.com"

    def test_pull_events_drains_the_queue(self) -> None:
        user = User.register(
            organization_id=uuid4(),
            email=EmailAddress("a@example.com"),
            password_hash=HashedPassword(VALID_HASH),
            first_name="A",
            last_name="B",
        )
        assert len(user.pull_events()) == 1
        assert user.pull_events() == []


class TestIdentityEquality:
    def test_two_users_with_same_id_are_equal_even_if_fields_differ(self) -> None:
        shared_id = uuid4()
        user_a = _make_user(id=shared_id, first_name="Ada")
        user_b = _make_user(id=shared_id, first_name="Grace")
        assert user_a == user_b
        assert hash(user_a) == hash(user_b)

    def test_two_users_with_different_ids_are_not_equal(self) -> None:
        assert _make_user() != _make_user()


class TestActivation:
    def test_activate_transitions_status_and_records_event(self) -> None:
        user = _make_user(status=UserStatus.INVITED)
        user.activate()
        assert user.status is UserStatus.ACTIVE
        events = user.pull_events()
        assert any(isinstance(e, UserActivated) for e in events)

    def test_deactivate_records_event(self) -> None:
        user = _make_user(status=UserStatus.ACTIVE)
        user.deactivate()
        assert user.status is UserStatus.DEACTIVATED
        assert any(isinstance(e, UserDeactivated) for e in user.pull_events())


class TestLoginTracking:
    def test_login_success_resets_failure_count_and_lock(self) -> None:
        now = datetime.now(UTC)
        user = _make_user(failed_login_attempts=3, locked_until=now + timedelta(minutes=5))
        user.record_login_success(now=now)
        assert user.failed_login_attempts == 0
        assert user.locked_until is None
        assert user.last_login_at == now
        assert any(isinstance(e, UserLoginSucceeded) for e in user.pull_events())

    def test_login_failure_increments_counter(self) -> None:
        user = _make_user(failed_login_attempts=0)
        user.record_login_failure(now=datetime.now(UTC))
        assert user.failed_login_attempts == 1
        events = user.pull_events()
        assert any(isinstance(e, UserLoginFailed) for e in events)
        assert not any(isinstance(e, UserLocked) for e in events)

    def test_reaching_max_attempts_locks_the_account(self) -> None:
        now = datetime.now(UTC)
        user = _make_user(failed_login_attempts=User.MAX_FAILED_LOGIN_ATTEMPTS - 1)
        user.record_login_failure(now=now)

        assert user.failed_login_attempts == User.MAX_FAILED_LOGIN_ATTEMPTS
        assert user.locked_until == now + User.LOCKOUT_DURATION
        assert any(isinstance(e, UserLocked) for e in user.pull_events())

    def test_is_locked_true_while_locked_until_in_future(self) -> None:
        now = datetime.now(UTC)
        user = _make_user(locked_until=now + timedelta(minutes=1))
        assert user.is_locked(now=now) is True

    def test_is_locked_false_once_lock_expires(self) -> None:
        now = datetime.now(UTC)
        user = _make_user(locked_until=now - timedelta(seconds=1))
        assert user.is_locked(now=now) is False

    def test_is_locked_false_when_never_locked(self) -> None:
        user = _make_user(locked_until=None)
        assert user.is_locked(now=datetime.now(UTC)) is False


class TestCanAuthenticate:
    @pytest.mark.parametrize(
        "status", [UserStatus.INVITED, UserStatus.SUSPENDED, UserStatus.DEACTIVATED]
    )
    def test_non_active_statuses_cannot_authenticate(self, status: UserStatus) -> None:
        user = _make_user(status=status)
        assert user.can_authenticate(now=datetime.now(UTC)) is False

    def test_active_and_unlocked_can_authenticate(self) -> None:
        user = _make_user(status=UserStatus.ACTIVE, locked_until=None)
        assert user.can_authenticate(now=datetime.now(UTC)) is True

    def test_active_but_locked_cannot_authenticate(self) -> None:
        now = datetime.now(UTC)
        user = _make_user(status=UserStatus.ACTIVE, locked_until=now + timedelta(minutes=1))
        assert user.can_authenticate(now=now) is False


class TestPasswordChange:
    def test_change_password_updates_hash_and_records_event(self) -> None:
        user = _make_user()
        new_hash = HashedPassword("$2b$12$" + "b" * 53)
        user.change_password(new_hash)
        assert user.password_hash == new_hash
        assert any(isinstance(e, PasswordChanged) for e in user.pull_events())


class TestFullName:
    def test_full_name_combines_first_and_last(self) -> None:
        user = _make_user(first_name="Ada", last_name="Lovelace")
        assert user.full_name == "Ada Lovelace"
