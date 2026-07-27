"""Application-layer exceptions for the Authentication module.

`AuthenticationError` is the single, deliberately generic exception the
public facade raises for *any* reason a token/session fails to validate
(expired, malformed, revoked, locked, deactivated account, ...) — callers
outside this module (the `get_current_user` dependency, and any future
module reached via the facade) don't need to know or handle the specific
domain reason, only "this principal is not authenticated." The specific
reason is still logged (see `services/token_validation_service.py`) for
observability; it's just not part of the public contract.
"""


class AuthenticationError(Exception):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason
