"""Public exceptions — re-exported, not redefined, so there is exactly
one definition of each. Mirrors the established `public/enums.py`
re-export pattern (e.g. `app.modules.schedule.public.enums`).

Two different source layers, both legitimately re-exported here:

- `UserNotFoundError` is a raw domain exception
  (`app.modules.authentication.domain.exceptions`) that
  `doctor.application.use_cases.onboard_doctor.OnboardDoctor` raises when
  the user it just resolved via the public facade turns out to be
  missing. Before this file existed, the only way to do that was to
  import directly from `.domain.exceptions`, which
  `docs/backend-architecture/10_module_communication.md` (Mechanism 1)
  explicitly forbids.
- `AuthenticationError` is already an *application*-layer exception
  (`app.modules.authentication.application.exceptions`) — see that
  file's own docstring: it is the module's deliberately generic,
  already-translated "not authenticated" signal for callers outside the
  module. `app/api/deps.py`'s `get_current_user` is exactly such a
  caller; it was previously importing it from `.application.exceptions`
  directly (also disallowed by `public/interfaces.py`'s own stated rule,
  which names `app/api/deps.py` specifically). Re-exporting it here gives
  that already-correct exception a boundary-compliant import path.

Neither re-export changes the exception type itself, so every existing
`except`/`isinstance` check anywhere in the app keeps matching exactly
as before.
"""

from app.modules.authentication.application.exceptions import AuthenticationError
from app.modules.authentication.domain.exceptions import UserNotFoundError

__all__ = ["AuthenticationError", "UserNotFoundError"]
