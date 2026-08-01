"""Public enums — re-exported from the domain layer, not redefined, so
there is exactly one definition of each. Mirrors the established
`public/enums.py` re-export pattern (e.g.
`app.modules.schedule.public.enums`,
`app.modules.patient_history.public.enums`).

Needed because `timeline`'s query service and DTOs use `DocumentCategory`
as a field/parameter type when summarizing a `MedicalDocument` event —
before this file existed, the only way to reference the type was to
import directly from `app.modules.documents.domain.enums`, which
`docs/backend-architecture/10_module_communication.md` (Mechanism 1)
explicitly forbids ("never, under any circumstance" depend on a target
module's `domain/`).
"""

from app.modules.documents.domain.enums import DocumentCategory

__all__ = ["DocumentCategory"]
