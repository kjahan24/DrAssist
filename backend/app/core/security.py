"""Security primitive contracts.

This module intentionally defines signatures only — no hashing, token, or
authentication logic is implemented here. It exists so the rest of the
codebase (dependencies, middlewares, services) has a stable import path to
code against while the concrete implementation is built out.
"""

from typing import Any


def hash_password(plain_password: str) -> str:
    raise NotImplementedError


def verify_password(plain_password: str, hashed_password: str) -> bool:
    raise NotImplementedError


def create_access_token(subject: str, claims: dict[str, Any] | None = None) -> str:
    raise NotImplementedError


def create_refresh_token(subject: str) -> str:
    raise NotImplementedError


def decode_token(token: str) -> dict[str, Any]:
    raise NotImplementedError
