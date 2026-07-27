"""Permission code constants.

Pure string constants only — no logic, no import of any `app.modules.*`
package. `core/` may never depend on `modules/`
(`docs/backend-architecture/11_standards_and_conventions.md`); the actual
RBAC evaluation (does this user hold this permission) lives in the
Authentication module and is reached, from route code, via the
`require_permission` dependency in `app/api/deps.py` — *not* from here,
which is why that dependency (which does need to call into the
Authentication module's public facade) is placed at the `app/api/` layer
instead of in `core/security/`, correcting an inconsistency in the
original architecture draft (`docs/backend-architecture/07_security_layer.md`
described the dependency itself as living in this file; it does not, for
the layering reason above).

Codes follow the `<module>.<action>` convention from
`docs/database/01_identity_and_access.md`'s `permissions` catalog.
"""

from enum import StrEnum


class Permission(StrEnum):
    """Every permission code the platform currently defines.

    This is the Python-side mirror of the `permissions` table's seed data
    (module-owned reference data, per
    `docs/backend-architecture/03_module_architecture.md`) — new codes are
    added here *and* seeded into the table in the same change, so the two
    never drift.
    """

    USERS_READ = "users.read"
    USERS_WRITE = "users.write"
    ROLES_READ = "roles.read"
    ROLES_WRITE = "roles.write"
    PERMISSIONS_ASSIGN = "permissions.assign"
