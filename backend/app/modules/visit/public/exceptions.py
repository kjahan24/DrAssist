"""Public exceptions — re-exported from the domain layer, not redefined,
so there is exactly one definition of each. Mirrors the established
`public/enums.py` re-export pattern (e.g.
`app.modules.schedule.public.enums`).

Needed because several peer modules' use cases resolve a `visit_id`
through `VisitQueryPort` and raise `PatientVisitNotFoundError` when it is
missing — before this file existed, the only way to do that was to
import directly from `app.modules.visit.domain.exceptions`, which
`docs/backend-architecture/10_module_communication.md` (Mechanism 1)
explicitly forbids ("never, under any circumstance" depend on a target
module's `domain/`). This re-export closes that gap without changing
the exception type itself, so every existing
`except PatientVisitNotFoundError` or `isinstance` check anywhere in the
app keeps matching exactly as before.
"""

from app.modules.visit.domain.exceptions import PatientVisitNotFoundError

__all__ = ["PatientVisitNotFoundError"]
