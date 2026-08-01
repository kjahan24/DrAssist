# Architecture Review: `DoctorSchedule` Ownership, and Boundary Cleanup

This document records the findings and decisions of a full Architecture
Review & Cleanup pass over the backend. It is scoped narrowly, by design:
the review's mandate was to fix only architecture issues that are
already documented, proven, safe, and backward compatible — not to add
features, redesign modules, or refactor for style. Every change described
below is either a documentation/metadata change with zero runtime
behavior change, or a mechanical import-path correction that preserves
the exact same exception/enum types at every call site.

## 1. `DoctorSchedule` ownership (the review's primary known issue)

### The overlap

Two unrelated classes share the name `DoctorSchedule`:

| | `app.modules.doctor.domain.entities.DoctorSchedule` | `app.modules.schedule.domain.entities.DoctorSchedule` |
|---|---|---|
| Fields | `doctor_id`, `day_of_week`, `start_time`, `end_time`, `break_start`, `break_end`, `is_available` | `organization_id`, `doctor_id`, `weekday`, `start_time`, `end_time`, `slot_duration_minutes`, `is_active` |
| Table | `doctor_schedules` | `doctor_availabilities` (deliberately not `doctor_schedules`, to avoid a hard table-name collision) |
| Multi-tenancy | None — no `organization_id` | Tenant-scoped — `organization_id` derived from the linked `Doctor` |
| Slot generation | No concept of appointment slot size | `slot_duration_minutes` — the field a future Appointment Booking module needs to generate bookable slots |
| CRUD surface | Create-only (`AddDoctorSchedule`) | Full lifecycle (`CreateDoctorSchedule`/`UpdateDoctorSchedule`/`ActivateDoctorSchedule`/`DeactivateDoctorSchedule`), plus a sibling `DoctorTimeOff` aggregate |
| REST endpoints | `POST/GET /api/v1/doctors/{doctor_id}/schedule` | 10 endpoints under `/api/v1/schedule/...` |
| FK delete behavior | `doctor_id → doctors.id ON DELETE CASCADE` | `organization_id`/`doctor_id` both `ON DELETE RESTRICT` |

Both implementations are live, fully tested, and shipped — neither is
dead code. The overlap was already self-documented across five places in
the codebase (`schedule/domain/entities.py`, `schedule/container.py`,
`schedule/api/router.py`, `doctor/application/dto.py`'s
`DoctorScheduleEntrySummaryDTO`, and the
`0dc952d8d776_create_doctor_availabilities_and_time_off_tables` migration
docstring), each explicitly deferring reconciliation to "a future task."
This review is that task.

Cross-checked against the original architecture blueprint
(`03_module_architecture.md`): it never mentions a "Schedule" or
"Availability" module at all, and lists Doctor's owned tables as only
`doctors`, `doctor_specialties`, `specialties` — no schedule table. Both
`DoctorSchedule` implementations are scope creep relative to the
original 13-module plan; the Schedule module was added later, as its own
top-level module, entirely outside that original document.

Neither implementation is consumed by any third module. `DoctorQueryPort`
(Doctor's public port) exposes no schedule-related method. `ScheduleQueryPort`
and `build_schedule_facade` have zero consumers outside
`app.modules.schedule` itself. Appointment — the module that would most
plausibly need either — explicitly does not build slot-conflict checking
against doctor availability at all (its own `container.py` scope note
says so); its own conflict-checking is limited to organization-match,
with no time-overlap check against Appointment rows or either
`DoctorSchedule` implementation.

### Decision

**`app.modules.schedule`'s `DoctorSchedule`/`DoctorTimeOff` are the
canonical, go-forward owner of "doctor schedule/availability."** It alone
satisfies this codebase's own load-bearing multi-tenancy convention
(`organization_id` on every business table) and alone carries
`slot_duration_minutes`, which the module's own scope note names as
exactly what a future Appointment Booking module needs to generate
bookable slots.

**`app.modules.doctor`'s `DoctorSchedule` is now formally deprecated but
intentionally retained, unmigrated, and fully backward compatible.**
Removing a live, shipped, public REST API without a confirmed
zero-consumer guarantee would violate this review's own rules 5–7
("never modify public APIs unless absolutely necessary," "preserve
backward compatibility," "preserve database compatibility"). No table,
migration, repository, or route was touched, renamed, or removed.

### What changed (all additive, zero behavior change)

- `app/modules/doctor/domain/entities.py` — `DoctorSchedule` now has a
  class docstring recording the deprecation and pointing to this
  document.
- `app/modules/doctor/api/router.py` — the two schedule endpoints
  (`POST`/`GET /{doctor_id}/schedule`) now carry `deprecated=True`,
  which only changes their OpenAPI-documented status (surfaced by
  Swagger UI as a strikethrough) — no request/response shape, status
  code, or behavior changed.
- `app/modules/doctor/api/schemas.py` — corrected a stale docstring
  claiming "Not yet wired to any route" (the router has had live
  endpoints since an earlier REST APIs task); documented the deprecated
  schedule schemas.
- `app/modules/schedule/api/schemas.py` — corrected the identical stale
  "not yet wired to any route" claim.
- `app/modules/schedule/container.py` — its existing, detailed "pre-existing
  naming collision" scope note now records that the reconciliation
  decision it deferred has been made, by this document.

## 2. Cross-module `domain.exceptions`/`domain.enums` boundary leaks

### Finding

A background architecture pass (regex import search over
`app/modules/**/*.py`) found 32 places where a use case in one module
imported and raised a peer module's raw `domain.exceptions` type
directly — e.g. `attachments.application.use_cases.upload_attachment`
importing `app.modules.doctor.domain.exceptions.DoctorNotFoundError`.
`docs/backend-architecture/10_module_communication.md` (Mechanism 1)
states a calling module must "never, under any circumstance" depend on
a target module's `domain/`; several offending call sites even cited
that same document, incorrectly, as justification for the pattern they
were violating. Two further, narrower instances of the same problem were
found: `app/api/deps.py` importing `AuthenticatedPrincipalDTO`/
`AuthenticationError` from `authentication.application.*` instead of an
available (DTO) or missing (exceptions) `public/` path, and `timeline`
importing `DocumentCategory` from `documents.domain.enums` because
`documents` had no `public/enums.py` to import it from instead.

### Fix

Applied the same re-export pattern this codebase already uses for
cross-module enums (e.g. `app.modules.schedule.public.enums`,
`app.modules.patient_history.public.enums`) to exceptions: added a thin
`public/exceptions.py` to each owning module (`doctor`, `visit`,
`clinical_notes`, `organization`, `authentication`, `patient`) and
`public/enums.py` to `documents`, each re-exporting — not redefining —
the existing type. A re-export is the same class object under a new
import path, so this closes all 32 (plus the 2 related) violations with
**zero runtime behavior change**: every `except`/`isinstance` check
anywhere in the app still matches exactly as before. All ~26 consumer
files were repointed to import from the new `public.*` path instead of
`domain.*`/`application.*`; docstrings that had mis-cited
`10_module_communication.md` as justification for the old, direct
import were corrected to describe the new, compliant path instead.

## 3. Other findings reviewed and not acted on

- **Event subscription wiring is a permanent no-op**
  (`app/core/container.py`'s `configure_event_subscriptions`), meaning
  every published domain event currently reaches zero subscribers — the
  structural reason `audit_log` and `notification` have no external
  callers today. Its stale docstring (claiming Patient History,
  Notification, and Audit are still "future modules") was corrected.
  Actually wiring subscriptions was **not** implemented: it requires
  writing new reactive business logic (which module reacts to which
  event, and how), which is new feature work, not an architecture fix,
  and squarely excluded by this review's own rules.
- **`app/modules/audit_log/domain/entities.py`'s `AuditLog.created_at`**
  computes an in-memory value that is never mapped onto `AuditLogModel`
  by `infrastructure/mappers.py` — the actual persisted value always
  comes from the database's `server_default=func.now()`. Documented with
  an inline comment; not changed, since the only real fixes (making the
  mapper persist it, or requiring it at construction) would each change
  either the stored value or the entity's public constructor.
- **Triplicated `ReviewStatus`/`ReasoningSource`/`DiagnosisSource`/
  `CodingSource`-shaped enums** across `clinical_reasoning`/
  `differential_diagnosis`/`icd10_coding`, and several other same-shape
  enum pairs (`Gender`, `Severity`/`Priority`, `AppointmentType`/
  `VisitType`) — match this codebase's own already-accepted convention
  of intentional per-module enum duplication for DDD bounded-context
  vocabulary independence. Not a defect.
- **`InvitationTokenHash` (family_access)** is a third near-identical
  copy of the `Sha256Checksum` pattern (`attachments`, `documents`) —
  crosses this codebase's own documented "third module needs it, promote
  to shared" threshold, but doing so now means touching three already-shipped
  modules' domain layers for a code-quality-only benefit. Reported, not
  fixed.
- **`timeline`/`patient_history` omit `vital_signs`/`chief_complaints`/
  `diagnosis`/`procedures`/`attachments`** as aggregation sources. Both
  modules' source lists were explicit, enumerated scope in their own
  founding tasks — not an oversight. Extending either would be new
  feature work.
- **8 unused exceptions in `app/modules/authentication/domain/exceptions.py`**
  are self-documented in that file's own module docstring as reserved for
  the login/register flows a prior task explicitly excluded — intentional
  forward-declaration, not dead code.
- **`11_standards_and_conventions.md` claims `import-linter` enforces
  module boundaries in CI today** — no `import-linter` configuration
  exists anywhere in the repository. This is itself stale/aspirational
  documentation. Adding real CI enforcement is infrastructure/tooling
  work, out of scope for this review; noted here for a future task.
- Zero cyclic dependencies, zero `app/core/` → `app/modules/` imports,
  zero domain-layer I/O or ORM-type leakage, zero application-layer
  FastAPI imports, and no unsafe shared mutable state in
  `app/core/container.py` — all confirmed clean, no action needed.
