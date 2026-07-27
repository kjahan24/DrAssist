# Security Layer

Security is not one module — it's a set of enforcement points threaded
through every layer. This document specifies each one. Authentication
*data* (users, sessions, roles) is owned by the Authentication module
(`03_module_architecture.md`); this document is about the mechanisms that
*use* that data to protect every request.

## 1. Authentication (identity verification)

- **Mechanism:** short-lived JWT access tokens + long-lived opaque refresh
  tokens, matching the `auth_sessions` design in
  `../database/01_identity_and_access.md`. Token encode/decode is a
  `core/security/jwt.py` primitive (technical, no domain knowledge);
  issuing/validating/revoking a *session* is an Authentication module
  concern.
- **Enforcement point:** a FastAPI dependency (`get_current_user`,
  extending the existing stub in `app/api/deps.py`), **not** global
  middleware. Reasoning: not every route requires authentication (login,
  password-reset request, health check), and expressing "all routes except
  these three" is more error-prone with middleware than opting in per
  router with `Depends(get_current_user)`. `TenantContextMiddleware`
  (`05_dependency_injection_and_lifecycle.md`) still runs globally to
  *decode* the token and populate context for RLS purposes — but it does
  not *reject* unauthenticated requests; rejection is `get_current_user`'s
  job, applied at the router level.
- **Refresh/rotation:** refresh tokens are single-use and rotated on every
  refresh (`auth_sessions.refresh_token_hash` replaced, old one revoked) —
  a reused (stolen, replayed) refresh token is detectable and triggers
  revocation of the entire session family.

## 2. Authorization (RBAC enforcement)

- **Mechanism:** every protected route declares the permission(s) it
  requires via a dependency, e.g. `Depends(require_permission("patients.write"))`
  (`core/security/permissions.py` defines the permission-string constants;
  the dependency itself calls Authentication's `PermissionCheckPort`).
- **Where the check happens:** as an API-layer dependency, resolved
  *before* the route handler and before the use case runs (see step 4 of
  the request lifecycle, `05_dependency_injection_and_lifecycle.md`) — a
  request that fails a permission check never reaches business logic, so
  application services never need to re-implement permission checks
  themselves. (Application services *do* still enforce data-scoping rules
  that aren't expressible as a single permission string — e.g. "a doctor
  can only view their own patients' notes" — those are Tier 2 validation,
  `04_repository_and_service_patterns.md`, not RBAC.)
- **Performance:** a user's effective permission set (union across all
  assigned roles, `../database/01_identity_and_access.md`) is computed
  once per login and cached in Redis, keyed by `user_id`, invalidated on
  `UserRoleAssigned`/role-permission-change events — so `PermissionCheckPort`
  is a cache read on the hot path, not a join query per request.

## 3. Multi-tenant isolation (defense in depth)

Two independent layers, deliberately redundant — a bug in one must not be
a data breach on its own:

| Layer | Mechanism | Failure mode it catches |
|---|---|---|
| Database | PostgreSQL Row-Level Security, `SET LOCAL app.current_organization_id` per transaction (`../database/00_overview.md`) | A query that forgot a tenant filter — the database itself refuses to return other tenants' rows, regardless of application code correctness |
| Application | `TenantContextMiddleware` resolves `organization_id` from the **JWT claim**, never from a client-supplied request field; every repository method that takes an `organization_id` receives it from this trusted context, not from request input | A client attempting to pass a different `organization_id` in a request body/query string to read another tenant's data — rejected before it ever becomes a query |

**The `organization_id` a repository uses is never client input.** This is
the single most important rule in this section: request payloads may
contain an `organization_id` field for other reasons (rare), but the value
actually used to scope a query always comes from the authenticated
session's tenant context, sourced from the JWT, which was itself only
issued after the user authenticated into that specific organization.

## 4. PHI / PII protection

- **At rest, column-level:** the two fields flagged in
  `../database/02_clinical_master_data.md` and `../database/01_identity_and_access.md`
  (`patients.national_id_number_encrypted`, `users.mfa_secret_encrypted`)
  are encrypted by the **application**, not the database, using
  `core/security/encryption.py` (envelope encryption via a KMS — the
  concrete provider is an infrastructure adapter behind a small
  `EncryptionPort`, following the same port/adapter shape as everything
  else). Encryption/decryption is called explicitly by the specific use
  cases that touch these fields — never automatic/transparent — so it
  stays auditable which code path handles the plaintext.
- **In transit:** TLS terminates at the ingress/load balancer
  (infrastructure concern, outside this codebase); internal service-to-
  service traffic (app ⇄ Postgres/Redis/Qdrant/MinIO) runs inside the
  private Docker network today, with TLS added there too once deployed
  beyond a single host.
- **In logs:** see `06_configuration_logging_exceptions.md` — PHI is never
  logged, at any layer, by convention and PR review.
- **Attachments:** `attachments.is_phi` (per `../database/05_labs_and_attachments.md`)
  drives which retention/access rules the File Storage module applies;
  presigned URLs are short-lived and scoped to one object.

## 5. Secrets management

`core/config.py`'s `Settings` classes are the **only** call sites that read
raw secrets (currently from environment variables / `.env`, per the Turn 1
scaffold). No module reads an environment variable directly. This
indirection means swapping the source (env vars today → a managed secrets
service like Vault/AWS Secrets Manager later) is a `core/config.py`-only
change — every module remains unaware of where a secret physically came
from, because it never asks for one; it asks its `container.py` for an
already-configured client.

## 6. Rate limiting & brute-force protection

- **Login attempts:** Redis-backed sliding-window counters keyed by
  `(email, ip_address)`, checked before Authentication's `AuthenticateUser`
  use case runs a password comparison — `auth_login_attempts` is the
  durable record (and DB-level source of truth for lockout status via
  `users.locked_until`), Redis is the fast pre-check that avoids hitting
  the DB for an already-locked-out actor.
- **General API rate limiting:** applied as a dependency (or, if uniform
  across all routes, middleware positioned after `TenantContextMiddleware`
  so limits can be tenant-aware) backed by the same Redis instance — not
  yet a named module, since it's a cross-cutting technical concern
  belonging in `core/`, not a bounded context with its own business rules.

## 7. Input security (beyond Pydantic validation)

- SQL injection: structurally prevented, not just "avoided" — repositories
  only ever build queries through SQLAlchemy's expression language;
  raw/string-interpolated SQL is disallowed by the coding standards
  (`11_standards_and_conventions.md`).
- File upload safety: `file_storage`'s `ConfirmUpload` use case triggers a
  virus-scan Celery task before an attachment is considered available for
  download (`attachments.virus_scan_status`, `08_background_workers.md`);
  an infected file publishes `AttachmentVirusDetected` and is quarantined,
  never silently served.
- Mass-assignment: API schemas (`api/schemas.py`) are explicit allow-lists
  of fields per endpoint's purpose — a request schema never simply mirrors
  the full domain entity, which would let a client set fields (like
  `status` or `organization_id`) it has no business setting directly.
