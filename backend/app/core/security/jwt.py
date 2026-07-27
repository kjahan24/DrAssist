"""JWT encode/decode primitives.

Pure technical utilities: no database access, no domain knowledge, no
`get_settings()` call inside — the caller (today, tests; once login exists,
the Authentication module's token-issuing use case and the
`get_current_user` dependency) passes in `secret_key`/`algorithm` and gets
back a token or a validated `TokenClaims`. Keeping these functions free of
implicit global state is what makes them trivially unit-testable. See
`docs/backend-architecture/07_security_layer.md §1`.
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Any
from uuid import uuid4

from jose import ExpiredSignatureError, JWTError, jwt


class TokenType(StrEnum):
    ACCESS = "access"
    REFRESH = "refresh"


class InvalidTokenError(Exception):
    """Raised for any token that fails signature, structure, or claim validation."""


class ExpiredTokenError(InvalidTokenError):
    """Raised specifically when the token's signature is valid but it has expired."""


@dataclass(frozen=True, slots=True)
class TokenClaims:
    subject: str
    organization_id: str
    token_type: TokenType
    issued_at: datetime
    expires_at: datetime
    jti: str
    session_id: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)


_RESERVED_CLAIM_KEYS = {"sub", "org", "type", "iat", "exp", "jti", "sid"}


def encode_token(
    *,
    subject: str,
    organization_id: str,
    token_type: TokenType,
    expires_delta: timedelta,
    secret_key: str,
    algorithm: str,
    session_id: str | None = None,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    """Encode and sign a JWT. `subject` is the user's `id` as a string."""
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": subject,
        "org": organization_id,
        "type": token_type.value,
        "iat": now,
        "exp": now + expires_delta,
        "jti": str(uuid4()),
    }
    if session_id is not None:
        payload["sid"] = session_id
    if extra_claims:
        payload.update({k: v for k, v in extra_claims.items() if k not in _RESERVED_CLAIM_KEYS})
    # python-jose ships no type stubs; jwt.encode type-checks as `Any`.
    return str(jwt.encode(payload, secret_key, algorithm=algorithm))


def decode_token(
    token: str,
    *,
    secret_key: str,
    algorithm: str,
    expected_type: TokenType | None = None,
) -> TokenClaims:
    """Verify signature and expiry, and return the parsed claims.

    Raises `ExpiredTokenError` for an expired-but-otherwise-valid token, or
    `InvalidTokenError` for any other failure (bad signature, malformed
    payload, wrong `token_type`).
    """
    try:
        payload = jwt.decode(token, secret_key, algorithms=[algorithm])
    except ExpiredSignatureError as exc:
        raise ExpiredTokenError("token has expired") from exc
    except JWTError as exc:
        raise InvalidTokenError(f"token could not be verified: {exc}") from exc

    try:
        token_type = TokenType(payload["type"])
        subject = str(payload["sub"])
        organization_id = str(payload["org"])
        issued_at = datetime.fromtimestamp(payload["iat"], tz=UTC)
        expires_at = datetime.fromtimestamp(payload["exp"], tz=UTC)
        jti = str(payload["jti"])
    except (KeyError, ValueError, TypeError) as exc:
        raise InvalidTokenError(f"token payload is malformed: {exc}") from exc

    if expected_type is not None and token_type is not expected_type:
        raise InvalidTokenError(
            f"expected a {expected_type.value!r} token, got {token_type.value!r}"
        )

    session_id = payload.get("sid")
    extra = {k: v for k, v in payload.items() if k not in _RESERVED_CLAIM_KEYS}

    return TokenClaims(
        subject=subject,
        organization_id=organization_id,
        token_type=token_type,
        issued_at=issued_at,
        expires_at=expires_at,
        jti=jti,
        session_id=str(session_id) if session_id is not None else None,
        extra=extra,
    )
