# Configuration Management, Logging Architecture, Exception Handling

These three are `app/core/` concerns (per `02_layer_responsibilities.md`):
process-wide, zero domain knowledge, depended on by every module. All three
already exist in the Turn 1 project foundation — this document specifies
how the modular monolith's 13 modules extend them consistently rather than
each inventing its own variant.

## Configuration management

`app/core/config.py`'s nested `Settings` groups (existing:
`DatabaseSettings`, `RedisSettings`, `QdrantSettings`, `MinioSettings`,
`GeminiSettings`, `WhisperSettings`, `PaddleOCRSettings`, `JWTSettings`,
`ObservabilitySettings`, each independently `.env`-sourced) remain the
single source of truth. Rules for how modules consume it:

- **No module defines its own `Settings` class.** A module that needs
  configuration (e.g. Notification needing an SMTP host, or a per-module
  feature flag) adds a field to the relevant existing settings group, or —
  if the module genuinely introduces a new external dependency — a new
  settings group added to `core/config.py` alongside the existing ones,
  never a parallel settings mechanism.
- **Modules receive configuration through their `container.py`**, not by
  importing `get_settings()` directly deep inside a use case. The module's
  composition root reads settings once at startup and passes only the
  specific values a component needs into its constructor — this keeps use
  cases and infrastructure adapters unaware that "configuration" as a
  concept exists, which is what makes them easy to unit test (construct
  with plain values, no `Settings` object required).
- **Per-tenant configuration** (an organization's timezone, feature flags,
  notification preferences) is **not** environment configuration — it's
  application data (`organizations.settings JSONB`, per
  `../database/01_identity_and_access.md`), read through the Organization
  module's repository like any other domain data, never through
  `core/config.py`.

## Logging architecture

`app/core/logging.py`'s `structlog` configuration (existing) is extended
with two conventions specific to the modular monolith:

- **Every log line carries `request_id`, `organization_id`, and `user_id`**
  when available, via `structlog.contextvars` bound by
  `RequestIDMiddleware` and `TenantContextMiddleware`
  (`05_dependency_injection_and_lifecycle.md`) — a module's logging calls
  never need to pass these explicitly; they're ambient for the duration of
  the request.
- **Loggers are named by module and layer**
  (`get_logger("modules.patient.application.record_allergy")`), not
  generically — this is what makes it possible to filter production logs
  down to one module's behavior without a request ID in hand yet (e.g.
  "show me every Application-layer log from the AI module in the last
  hour").
- **What gets logged where:** Infrastructure logs technical events
  (a query took 400ms, a retry happened, an external API call failed).
  Application logs business-meaningful events at the use-case boundary
  (a use case started/completed/failed, with its Input DTO's non-PHI
  fields). Domain code does not log at all — it raises exceptions; logging
  a domain rule violation is the calling layer's job, once, at the point
  it's handled (avoids the same error being logged three times as it
  propagates).
- **PHI is never logged**, at any layer — see `07_security_layer.md`. This
  is enforced by convention (log calls pass IDs and enums, not patient
  names/notes/results) and reviewed at PR time; it's a rule this
  document's own logging examples follow (every example above logs IDs,
  not clinical content).

## Exception handling

`app/core/exceptions.py`'s `AppError` hierarchy (existing:
`NotFoundError`, `ValidationError`, `UnauthorizedError`, `ForbiddenError`,
`ConflictError`, `ServiceUnavailableError`, each carrying an HTTP
`status_code` and `error_code`) remains the **only** hierarchy that
translates to an HTTP response — the shared exception handler middleware
(`app/middlewares/error_handler.py`, existing) needs exactly one place to
look.

**How module-specific and layer-specific exceptions fit under it:**

| Layer | Exception style | Example | Relationship to `AppError` |
|---|---|---|---|
| Domain (`modules/<name>/domain/exceptions.py`) | One exception class per broken invariant, named for the rule, not the HTTP outcome | `DuplicateMedicalRecordNumberError`, `InvalidVisitStatusTransitionError` | Does **not** subclass `AppError` — domain exceptions carry no HTTP knowledge; they subclass a plain `DomainError` base (`app/shared/domain/`) |
| Application (`modules/<name>/application/exceptions.py` or inline) | Wraps/translates a domain exception, or represents a use-case-level failure (e.g. a cross-module existence check failed) | `PatientNotEligibleError` | Subclasses `AppError` (e.g. `ConflictError`, `NotFoundError`) — this is the translation point from domain vocabulary to HTTP-shaped vocabulary |
| Infrastructure | Wraps third-party exceptions (a DB connection error, an AI provider timeout) | — | Subclasses `ServiceUnavailableError` or similar, so a downstream outage surfaces as a clean `503`, never a raw `psycopg2`/`httpx` traceback reaching the client |

**Why domain exceptions don't carry HTTP status codes:** the domain layer
doesn't know it's being used by an HTTP API — the same
`InvalidVisitStatusTransitionError` should be raised identically whether
triggered via the API, a Celery task, or a future gRPC endpoint after
microservices extraction. The Application layer (or, for infrastructure-
originated failures, the Infrastructure layer) is where "this domain
problem means HTTP 409" is decided — a decision that belongs with the
delivery mechanism, not the business rule.

**Global fallback:** any exception that is *not* an `AppError` subclass by
the time it reaches the outermost handler (a bug, an unexpected library
exception) is caught by the existing catch-all handler, logged at `error`
level with the full traceback (server-side only), and returned to the
client as a generic `500` with no internal detail leaked — already
implemented in the Turn 1 scaffold and unchanged by the modular monolith
restructuring.
