"""Validation tests for the Authentication module's register/login
Pydantic v2 schemas — in particular, that `RegisterRequest.password`
enforces the exact same policy as `frontend/src/lib/auth/validation.ts`'s
`passwordSchema` (see `api/schemas.py`'s own docstring for why that
parity matters)."""

from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.modules.authentication.api.schemas import (
    AuthenticatedPrincipalResponse,
    LoginRequest,
    LoginResponse,
    RegisterRequest,
    RegisterResponse,
)


class TestRegisterRequest:
    def test_accepts_a_valid_payload(self) -> None:
        request = RegisterRequest(
            email="new.doctor@example.com",
            password="StrongPass1",
            first_name="Ada",
            last_name="Lovelace",
        )
        assert request.email == "new.doctor@example.com"

    @pytest.mark.parametrize(
        "password",
        [
            "short1A",  # < 8 chars
            "alllowercase1",  # no uppercase
            "ALLUPPERCASE1",  # no lowercase
            "NoDigitsHere",  # no digit
        ],
    )
    def test_rejects_a_password_that_fails_the_frontend_matching_policy(
        self, password: str
    ) -> None:
        with pytest.raises(ValidationError):
            RegisterRequest(
                email="new.doctor@example.com",
                password=password,
                first_name="Ada",
                last_name="Lovelace",
            )

    def test_rejects_an_invalid_email(self) -> None:
        with pytest.raises(ValidationError):
            RegisterRequest(
                email="not-an-email",
                password="StrongPass1",
                first_name="Ada",
                last_name="Lovelace",
            )

    def test_rejects_a_blank_first_name(self) -> None:
        with pytest.raises(ValidationError):
            RegisterRequest(
                email="new.doctor@example.com",
                password="StrongPass1",
                first_name="",
                last_name="Lovelace",
            )


class TestLoginRequest:
    def test_accepts_a_valid_payload(self) -> None:
        request = LoginRequest(email="doctor@example.com", password="anything")
        assert request.email == "doctor@example.com"

    def test_rejects_an_empty_password(self) -> None:
        with pytest.raises(ValidationError):
            LoginRequest(email="doctor@example.com", password="")

    def test_login_has_no_password_strength_requirement(self) -> None:
        """Unlike `RegisterRequest`, login must accept whatever password
        an already-existing account was created with, even one that
        predates a stricter policy — strength is only ever enforced at
        registration time."""
        request = LoginRequest(email="doctor@example.com", password="weak")
        assert request.password == "weak"


class TestLoginResponseShape:
    def test_matches_the_frontend_s_documented_wire_shape(self) -> None:
        """`frontend/src/app/(auth)/login/page.tsx`'s own `LoginResponse`
        TS interface expects exactly `{access_token, principal}`, and
        `frontend/src/types/index.ts`'s `AuthenticatedPrincipal` expects
        exactly these five principal fields."""
        response = LoginResponse(
            access_token="a.b.c",
            refresh_token="raw-refresh-token",
            principal=AuthenticatedPrincipalResponse(
                user_id=uuid4(),
                organization_id=uuid4(),
                session_id=uuid4(),
                email="doctor@example.com",
                permissions=["patients.read"],
            ),
        )
        dumped = response.model_dump(mode="json")
        assert set(dumped["principal"].keys()) == {
            "user_id",
            "organization_id",
            "session_id",
            "email",
            "permissions",
        }
        assert dumped["access_token"] == "a.b.c"


class TestRegisterResponseShape:
    def test_round_trips_from_attributes(self) -> None:
        class _FakeOutput:
            user_id = uuid4()
            organization_id = uuid4()
            email = "new.doctor@example.com"

        response = RegisterResponse.model_validate(_FakeOutput())
        assert response.email == "new.doctor@example.com"
