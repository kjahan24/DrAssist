"""Password hashing primitive.

Bcrypt via passlib's `CryptContext`, which also gives a migration path if
a future scheme change is ever needed (`deprecated="auto"` marks
old-scheme hashes for transparent re-hash on next successful verify — not
exercised yet, since only one scheme is configured today).

This is a plain technical utility, not a class behind a port interface —
per `docs/backend-architecture/04_repository_and_service_patterns.md`, a
formal interface earns its place only where more than one implementation
is plausible. Password hashing has exactly one implementation system-wide,
so the future `RegisterUser`/`AuthenticateUser` use cases (and, today,
this module's own tests) call these functions directly.
"""

from passlib.context import CryptContext

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain_password: str) -> str:
    """Return a bcrypt hash of `plain_password`. Never store the plaintext."""
    # passlib ships no type stubs, so its methods type-check as returning
    # `Any` — the `str()`/`bool()` wraps below satisfy strict mypy without
    # weakening this function's own declared, meaningful return type.
    return str(_pwd_context.hash(plain_password))


def verify_password(plain_password: str, password_hash: str) -> bool:
    """Constant-time comparison of a plaintext candidate against a stored hash."""
    return bool(_pwd_context.verify(plain_password, password_hash))


def needs_rehash(password_hash: str) -> bool:
    """True if `password_hash` was produced by a deprecated scheme/cost factor.

    Call after a successful `verify_password` and, if true, re-hash the
    already-verified plaintext and persist it — the standard "upgrade on
    login" pattern for rotating hashing cost factors over time.
    """
    return bool(_pwd_context.needs_update(password_hash))
