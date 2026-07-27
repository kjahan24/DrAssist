"""Unit tests for `app.core.security.jwt`."""

from datetime import timedelta
from uuid import uuid4

import pytest

from app.core.security.jwt import (
    ExpiredTokenError,
    InvalidTokenError,
    TokenType,
    decode_token,
    encode_token,
)

SECRET_KEY = "unit-test-secret-key"
ALGORITHM = "HS256"


def _issue_access_token(**overrides: object) -> str:
    defaults: dict[str, object] = {
        "subject": str(uuid4()),
        "organization_id": str(uuid4()),
        "token_type": TokenType.ACCESS,
        "expires_delta": timedelta(minutes=30),
        "secret_key": SECRET_KEY,
        "algorithm": ALGORITHM,
    }
    defaults.update(overrides)
    return encode_token(**defaults)  # type: ignore[arg-type]


class TestEncodeDecodeRoundTrip:
    def test_decoded_claims_match_what_was_encoded(self) -> None:
        subject = str(uuid4())
        org_id = str(uuid4())
        session_id = str(uuid4())
        token = encode_token(
            subject=subject,
            organization_id=org_id,
            token_type=TokenType.ACCESS,
            expires_delta=timedelta(minutes=15),
            secret_key=SECRET_KEY,
            algorithm=ALGORITHM,
            session_id=session_id,
        )

        claims = decode_token(token, secret_key=SECRET_KEY, algorithm=ALGORITHM)

        assert claims.subject == subject
        assert claims.organization_id == org_id
        assert claims.token_type is TokenType.ACCESS
        assert claims.session_id == session_id
        assert claims.expires_at > claims.issued_at

    def test_extra_claims_are_preserved(self) -> None:
        token = _issue_access_token(extra_claims={"custom": "value"})
        claims = decode_token(token, secret_key=SECRET_KEY, algorithm=ALGORITHM)
        assert claims.extra["custom"] == "value"

    def test_reserved_claim_names_cannot_be_overridden_via_extra(self) -> None:
        subject = str(uuid4())
        token = encode_token(
            subject=subject,
            organization_id=str(uuid4()),
            token_type=TokenType.ACCESS,
            expires_delta=timedelta(minutes=5),
            secret_key=SECRET_KEY,
            algorithm=ALGORITHM,
            extra_claims={"sub": "attacker-controlled-value"},
        )
        claims = decode_token(token, secret_key=SECRET_KEY, algorithm=ALGORITHM)
        assert claims.subject == subject  # not overridden by extra_claims


class TestExpectedType:
    def test_decoding_with_matching_expected_type_succeeds(self) -> None:
        token = _issue_access_token()
        claims = decode_token(
            token, secret_key=SECRET_KEY, algorithm=ALGORITHM, expected_type=TokenType.ACCESS
        )
        assert claims.token_type is TokenType.ACCESS

    def test_decoding_with_mismatched_expected_type_raises(self) -> None:
        token = _issue_access_token()
        with pytest.raises(InvalidTokenError):
            decode_token(
                token, secret_key=SECRET_KEY, algorithm=ALGORITHM, expected_type=TokenType.REFRESH
            )


class TestExpiry:
    def test_expired_token_raises_expired_token_error(self) -> None:
        token = _issue_access_token(expires_delta=timedelta(seconds=-1))
        with pytest.raises(ExpiredTokenError):
            decode_token(token, secret_key=SECRET_KEY, algorithm=ALGORITHM)


class TestTamperingAndBadInput:
    def test_wrong_secret_key_raises_invalid_token_error(self) -> None:
        token = _issue_access_token()
        with pytest.raises(InvalidTokenError):
            decode_token(token, secret_key="a-different-secret", algorithm=ALGORITHM)

    def test_garbage_input_raises_invalid_token_error(self) -> None:
        with pytest.raises(InvalidTokenError):
            decode_token("not.a.jwt", secret_key=SECRET_KEY, algorithm=ALGORITHM)

    def test_tampered_payload_raises_invalid_token_error(self) -> None:
        token = _issue_access_token()
        header, payload, signature = token.split(".")
        tampered = f"{header}.{payload}x.{signature}"
        with pytest.raises(InvalidTokenError):
            decode_token(tampered, secret_key=SECRET_KEY, algorithm=ALGORITHM)
