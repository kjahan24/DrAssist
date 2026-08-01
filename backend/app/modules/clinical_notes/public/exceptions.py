"""Public exceptions — re-exported from the domain layer, not redefined,
so there is exactly one definition of each. Mirrors the established
`public/enums.py` re-export pattern (e.g.
`app.modules.schedule.public.enums`).

Needed because the `lab_orders`, `prescriptions`, and `soap_notes`
modules' write use cases check the parent clinical note's editability
and raise `ClinicalNoteNotEditableError` when it is locked — before this
file existed, the only way to do that was to import directly from
`app.modules.clinical_notes.domain.exceptions`, which
`docs/backend-architecture/10_module_communication.md` (Mechanism 1)
explicitly forbids ("never, under any circumstance" depend on a target
module's `domain/`). This re-export closes that gap without changing
the exception type itself, so every existing
`except ClinicalNoteNotEditableError` or `isinstance` check anywhere in
the app keeps matching exactly as before.
"""

from app.modules.clinical_notes.domain.exceptions import ClinicalNoteNotEditableError

__all__ = ["ClinicalNoteNotEditableError"]
