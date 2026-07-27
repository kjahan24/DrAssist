"""Raw refresh-token generation and hashing.

Deliberately **not** bcrypt (`password_hashing.py`): a refresh token is
already a high-entropy, randomly generated value — not a user-chosen
secret — so it needs no slow, salted KDF to resist brute force. A fast
SHA-256 digest of the raw token is sufficient and is what gets persisted
(`refresh_tokens.token_hash`); the raw value is returned to the client
exactly once, at issuance, and is never stored or logged.
"""

import hashlib
import secrets

_RAW_TOKEN_BYTES = 32  # 256 bits of entropy


def generate_raw_refresh_token() -> str:
    """A new, URL-safe, high-entropy refresh token value."""
    return secrets.token_urlsafe(_RAW_TOKEN_BYTES)


def hash_refresh_token(raw_token: str) -> str:
    """The stable digest of `raw_token`, persisted in place of the raw value."""
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
