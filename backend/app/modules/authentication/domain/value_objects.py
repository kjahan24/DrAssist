"""Value objects specific to the Authentication module.

`EmailAddress` (used by `User`) is a *shared* value object — see
`app.shared.domain.common_value_objects.EmailAddress` — since other future
modules (Organization, Patient) need it too. These two are Authentication-
specific and stay local to this module's `domain/`.
"""

import re
from dataclasses import dataclass

from app.modules.authentication.domain.exceptions import InvalidPermissionCodeError
from app.shared.domain.exceptions import DomainError
from app.shared.domain.value_object import ValueObject

_PERMISSION_CODE_PATTERN = re.compile(r"^[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*$")
_BCRYPT_HASH_PREFIXES = ("$2a$", "$2b$", "$2y$")


class InvalidHashedPasswordError(DomainError):
    def __init__(self) -> None:
        super().__init__(
            "HashedPassword must be a bcrypt hash — got a value that doesn't look like "
            "one; this usually means plaintext was passed where a hash was expected"
        )


@dataclass(frozen=True, slots=True)
class HashedPassword(ValueObject):
    """Wraps an *already-hashed* password. The domain layer never sees, and
    never hashes, plaintext — hashing happens at the application boundary
    via `app.core.security.password_hashing.hash_password` before a
    `HashedPassword` is constructed. This is a structural guarantee: there
    is no code path by which a plaintext string can be assigned to
    `User.password_hash` without first passing through this validation.
    """

    value: str

    def __post_init__(self) -> None:
        if not self.value.startswith(_BCRYPT_HASH_PREFIXES):
            raise InvalidHashedPasswordError()


@dataclass(frozen=True, slots=True)
class PermissionCode(ValueObject):
    """A permission string in `module.action` form, e.g. `"patients.read"`."""

    value: str

    def __post_init__(self) -> None:
        normalized = self.value.strip().lower()
        if not _PERMISSION_CODE_PATTERN.match(normalized):
            raise InvalidPermissionCodeError(self.value)
        object.__setattr__(self, "value", normalized)

    def __str__(self) -> str:
        return self.value
