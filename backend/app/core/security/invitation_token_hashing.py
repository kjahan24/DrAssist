"""Raw invitation-token generation and hashing.

A sibling of `token_hashing.py` (refresh tokens), not a modification of
it: identical reasoning (a high-entropy, randomly generated value needs
no slow, salted KDF — a fast SHA-256 digest of the raw token is
sufficient and is what gets persisted, e.g.
`family_access_grants.invitation_token`; the raw value is handed back to
the caller exactly once, at invitation time, and is never stored or
logged), but a distinct, correctly-named pair of functions rather than
reusing `generate_raw_refresh_token`/`hash_refresh_token` under a
misleading name for an unrelated bounded context (invitations, not
sessions) — see `app.modules.family_access.container`'s own scope note.
"""

import hashlib
import secrets

_RAW_TOKEN_BYTES = 32  # 256 bits of entropy


def generate_raw_invitation_token() -> str:
    """A new, URL-safe, high-entropy invitation token value."""
    return secrets.token_urlsafe(_RAW_TOKEN_BYTES)


def hash_invitation_token(raw_token: str) -> str:
    """The stable digest of `raw_token`, persisted in place of the raw value."""
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
