"""Value objects specific to the Family / Caregiver Access module.

`InvitationTokenHash` validates *shape* only — exactly 64 hexadecimal
characters, the fixed, unambiguous length of a SHA-256 digest. This is
the module-local "hex-digest value object" pattern
`app.modules.documents.domain.value_objects.Sha256Checksum` and
`app.modules.attachments.domain.value_objects.Sha256Checksum` already
establish twice in this codebase — domain code never imports across
module boundaries, so each module that needs this exact format
constraint defines its own copy.

The entity field itself is named `invitation_token` (per this task's own
Entity spec), but its *value* is always this hash, never the raw,
presentable token — see `app.core.security.invitation_token_hashing`
and `application/use_cases/invite_caregiver.py` for where the raw value
is generated and returned to the caller exactly once, and
`domain/entities.py`'s own module docstring for the full security
reasoning (mirrors `RefreshToken.token_hash`).
"""

import re
from dataclasses import dataclass

from app.modules.family_access.domain.exceptions import InvalidInvitationTokenHashError
from app.shared.domain.value_object import ValueObject

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True, slots=True)
class InvitationTokenHash(ValueObject):
    value: str

    def __post_init__(self) -> None:
        normalized = self.value.strip().lower()
        if not _SHA256_PATTERN.match(normalized):
            raise InvalidInvitationTokenHashError(self.value)
        object.__setattr__(self, "value", normalized)

    def __str__(self) -> str:
        return self.value
