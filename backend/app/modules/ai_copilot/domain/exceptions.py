"""Domain exceptions for the AI Clinical Copilot module.

`PatientNotFoundError` is defined locally rather than imported from the
Patient module — the same "no module exposes a not-found error a peer
module is allowed to import; only its `public/` port is importable"
pattern `app.modules.family_access.domain.exceptions` and
`app.modules.appointment.domain.exceptions` already establish for this
codebase.

Errors originating from the AI Foundation module (`app.modules.ai`) —
timeouts, rate limits, authentication failures, provider unavailability —
are **not** wrapped or re-typed here and are allowed to propagate
unchanged out of `application/services/clinical_copilot_service.py`.
That module's own exception hierarchy
(`app.modules.ai.domain.exceptions.AIProviderError` and subclasses) lives
in `.domain`, not `.public` — this module is not permitted to import it
(`docs/backend-architecture/11_standards_and_conventions.md`'s module-
independence rule), so it structurally cannot `isinstance`-check or
re-wrap those errors without reaching past the AI module's public
boundary. A caller that needs to distinguish "AI Foundation failed" from
this module's own failures already has to reach `app.modules.ai.public`
to do so.
"""

from uuid import UUID

from app.shared.domain.exceptions import DomainError


class PatientNotFoundError(DomainError):
    def __init__(self, patient_id: UUID) -> None:
        super().__init__(f"no patient found with id {patient_id}")
        self.patient_id = patient_id


class InvalidAIRequestError(DomainError):
    def __init__(self, reason: str) -> None:
        super().__init__(f"invalid AI request: {reason}")
        self.reason = reason


class StructuredResponseParsingError(DomainError):
    def __init__(self, output_format: str, reason: str) -> None:
        super().__init__(f"could not parse {output_format} response: {reason}")
        self.output_format = output_format
        self.reason = reason


class AIResponseValidationError(DomainError):
    def __init__(self, reason: str) -> None:
        super().__init__(f"AI response failed validation: {reason}")
        self.reason = reason
