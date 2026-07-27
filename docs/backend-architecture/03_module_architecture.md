# Module Architecture — the 13 Bounded Contexts

Each module follows the internal shape from `02_layer_responsibilities.md`
(`domain/ → application/ → infrastructure/ → api/`, plus a `public/`
package). This document specifies, per module: what it owns, its domain
model shape, its representative use cases, its public interface, and its
dependency relationships to other modules. Table/column-level schema detail
already exists in `../database/`; this document does not repeat it, only
references which tables each module owns.

**Aggregate reference rule (applies to every module below):** an aggregate
references another module's aggregate **by ID only** — never by holding an
object reference to it. `ClinicalNote` stores `visit_id: UUID`, never a
`Visit` object. This keeps every module's transaction/locking scope
independent of every other module's, which is both good DDD practice in a
monolith and the specific property that makes later extraction to separate
databases (per module) a data-migration problem, not a redesign problem.

---

## Dependency summary (see full graph in `05_dependency_injection_and_lifecycle.md`)

| Tier | Modules | Depends on (via `public/`) |
|---|---|---|
| 0 — Foundational | Organization, File Storage, Audit | Nothing else in `modules/` |
| 1 — Identity | Authentication | Organization |
| 2 — Directory | Doctor, Patient | Authentication, Organization |
| 3 — Encounter | Visit | Patient, Doctor, Organization |
| 4 — Clinical content | Clinical Note, SOAP Note, Lab Report, AI | Visit, Patient, Doctor (existence checks only); Clinical Note/SOAP Note also call AI |
| 5 — Read-side / reactive sinks | Patient History, Notification, Audit (event consumption) | Subscribe to events from all tiers above; Notification also queries Authentication/Patient for contact info |

No cycles exist in this graph — a hard architectural constraint enforced by
`import-linter` (see `11_standards_and_conventions.md`).

---

## 1. Authentication

**Responsibility:** identity, credentials, sessions, and RBAC for every
human actor in the system (staff users; patients only if portal login is
enabled).

**Owns (tables):** `users`, `roles`, `permissions`, `role_permissions`,
`user_roles`, `auth_sessions`, `auth_password_reset_tokens`,
`auth_email_verification_tokens`, `auth_login_attempts`
(`../database/01_identity_and_access.md`).

| Domain model | |
|---|---|
| Aggregate roots | `User`, `Role`, `AuthSession` |
| Notable value objects | `EmailAddress` (shared), `HashedPassword`, `PermissionCode` |
| Domain events published | `UserRegistered`, `UserLoggedIn`, `UserRoleAssigned`, `UserDeactivated`, `PasswordResetRequested` |

**Representative use cases:** `RegisterUser`, `AuthenticateUser`,
`RefreshAccessToken`, `RevokeSession` (logout / logout-everywhere),
`RequestPasswordReset`, `ResetPassword`, `VerifyEmailAddress`,
`AssignRoleToUser`, `CreateCustomRole`, `RecordLoginAttempt`.

**Infrastructure specifics:** password hashing and JWT encode/decode are
technically implemented in `core/security/` (shared primitives, per
`02_layer_responsibilities.md`) but *invoked* from this module's
infrastructure adapters — Authentication is the only module that calls
them for credential purposes. Failed-login counters use the shared Redis
client for fast rate-limit checks, with `auth_login_attempts` as the
durable record.

**Public interface (`public/`):**

| Kind | Name | Purpose |
|---|---|---|
| Query | `UserQueryPort.user_exists(user_id)` | Existence check for other modules validating a `created_by`/actor reference |
| Query | `UserQueryPort.get_user_summary(user_id)` | Name/email/status for display in other modules' read models |
| Query | `PermissionCheckPort.has_permission(user_id, permission_code)` | The RBAC enforcement point every module's API dependencies call |
| Event | `UserRegistered`, `UserRoleAssigned`, `UserDeactivated` | Consumed by Notification (welcome email, role-change alert), Audit |

**Depends on:** Organization (`OrganizationQueryPort.organization_exists`
— a user cannot be created for a nonexistent/suspended tenant).
**Depended on by:** every other module, directly or via `PermissionCheckPort`.

---

## 2. Organization

**Responsibility:** tenant identity and physical/virtual locations — the
root of the multi-tenant boundary described in `../database/00_overview.md`.

**Owns (tables):** `organizations`, `organization_locations`.

| Domain model | |
|---|---|
| Aggregate roots | `Organization`, `OrganizationLocation` |

`OrganizationLocation` is modeled as its **own** aggregate root rather than
a child entity of `Organization`, deliberately: locations are added,
edited, and deactivated independently and don't need to be loaded/locked
together with the parent organization for any invariant this system
enforces. Keeping `Organization` small avoids that row becoming a
write-contention hotspot as an org's location list grows.

**Representative use cases:** `ProvisionOrganization` (tenant onboarding),
`UpdateOrganizationSettings`, `AddLocation`, `DeactivateLocation`,
`SuspendOrganization`.

**Public interface:**

| Kind | Name | Purpose |
|---|---|---|
| Query | `OrganizationQueryPort.organization_exists(org_id)` / `is_active(org_id)` | Guard used by every tenant-scoped module before creating data |
| Query | `OrganizationQueryPort.get_default_timezone(org_id)` | Used by Visit for scheduling display |
| Event | `OrganizationCreated`, `OrganizationSuspended` | Consumed by Audit; `OrganizationSuspended` fans out to disable dependent write paths |

**Depends on:** nothing else in `modules/`. **Depended on by:** almost
every module (foundational, tier 0).

---

## 3. Doctor

**Responsibility:** clinical-staff professional profile — licensing,
specialties, and prescribing/documentation privileges layered onto an
Authentication `User`.

**Owns (tables):** `doctors`, `doctor_specialties`, `specialties`
(the global specialty catalog is owned here since `DoctorSpecialty` is its
only consumer).

| Domain model | |
|---|---|
| Aggregate roots | `Doctor` (child entity: `DoctorSpecialty`) |

**Representative use cases:** `OnboardDoctor` (creates the `User` via
Authentication's use case, then the `Doctor` profile — an example of one
use case orchestrating two modules through their public interfaces, not
their internals), `UpdateLicenseInformation`, `AssignSpecialty`,
`SetAcceptingPatients`, `DeactivateDoctor`.

**Public interface:**

| Kind | Name | Purpose |
|---|---|---|
| Query | `DoctorQueryPort.doctor_exists(doctor_id)` / `is_accepting_patients(doctor_id)` | Used by Visit when scheduling |
| Query | `DoctorQueryPort.get_doctor_summary(doctor_id)` | Name/specialty for display in Visit, LabReport, PatientHistory |
| Event | `DoctorOnboarded`, `DoctorDeactivated` | Consumed by Audit, Notification |

**Depends on:** Authentication (`UserQueryPort`, plus calling
`RegisterUser` during onboarding), Organization. **Depended on by:**
Visit, Lab Report (`ordering_doctor_id`), Patient (`prescribed_by`/
`diagnosed_by`, validated via `DoctorQueryPort`, not a hard object
reference).

---

## 4. Patient

**Responsibility:** patient demographic identity and the longitudinal
clinical facts that outlive any single visit — contacts, allergies,
medications, conditions.

**Owns (tables):** `patients`, `patient_contacts`, `patient_allergies`,
`patient_medications`, `patient_conditions`, `condition_codes` (global
ICD-10 catalog, owned here as Patient is its primary consumer).

| Domain model | |
|---|---|
| Aggregate root | `Patient` |
| Child entities (within the `Patient` aggregate) | `PatientContact`, `PatientAllergy`, `PatientMedication`, `PatientCondition` |

These four are modeled as children of the `Patient` aggregate, unlike
`OrganizationLocation` above — the distinguishing factor is that domain
rules genuinely span them (e.g. recording a new medication should be able
to check it against the patient's already-loaded allergy list in the same
operation), so they share a consistency boundary and are loaded/saved
through the `Patient` repository as one unit.

**Representative use cases:** `RegisterPatient`, `UpdatePatientDemographics`,
`AddPatientContact`, `RecordAllergy`, `ResolveAllergy`,
`PrescribeMedication`, `DiscontinueMedication`, `DiagnoseCondition`,
`ResolveCondition`, `AnonymizePatient` (the right-to-erasure path from
`../database/09_best_practices_and_performance.md §1.3`).

**Public interface:**

| Kind | Name | Purpose |
|---|---|---|
| Query | `PatientQueryPort.patient_exists(patient_id)` / `get_patient_summary(patient_id)` | Used by Visit, Clinical Note, SOAP Note, Lab Report, AI |
| Query | `PatientQueryPort.get_active_allergies(patient_id)` / `get_active_medications(patient_id)` | Used by AI (safety-context for generation), Notification |
| Query | `ConditionCodeLookupPort.search(query)` | Used by SOAP Note / AI for coding-assist suggestions |
| Event | `PatientRegistered`, `PatientAllergyRecorded`, `PatientMedicationPrescribed`, `PatientConditionDiagnosed`, `PatientAnonymized` | Consumed by Patient History, Audit, Notification |

**Depends on:** Organization, Authentication (optional portal `user_id`
link), Doctor (soft reference via `DoctorQueryPort` for
`prescribed_by`/`diagnosed_by`). **Depended on by:** Visit, Clinical Note,
SOAP Note, Lab Report, AI, Patient History, Notification.

---

## 5. Visit

**Responsibility:** the clinical encounter — the central coordination
point binding patient, doctor, location, and time, and the vitals captured
during it.

**Owns (tables):** `visits`, `vital_signs`.

| Domain model | |
|---|---|
| Aggregate root | `Visit` (child entity: `VitalSigns`, one-to-many) |
| Domain events published | `VisitScheduled`, `VisitCheckedIn`, `VisitStarted`, `VisitCompleted`, `VisitCancelled`, `VitalSignsRecorded` |

**Representative use cases:** `ScheduleVisit`, `CheckInPatient`,
`StartVisit`, `RecordVitalSigns`, `CompleteVisit`, `CancelVisit`,
`MarkNoShow`, `RescheduleVisit`.

**Public interface:**

| Kind | Name | Purpose |
|---|---|---|
| Query | `VisitQueryPort.visit_exists(visit_id)` / `get_visit_summary(visit_id)` | Used by Clinical Note, SOAP Note, Lab Report, AI |
| Query | `VisitQueryPort.get_active_visit_for_patient(patient_id)` | Used by AI to attach an ambient-scribe session to the in-progress visit |
| Event | all of the above | Consumed heavily by Patient History and Notification (appointment reminders, check-in alerts) |

**Depends on:** Patient (`patient_exists`), Doctor (`doctor_exists`,
`is_accepting_patients`), Organization (location validation).
**Depended on by:** Clinical Note, SOAP Note, AI, Lab Report (optional
`visit_id`), Patient History, Notification.

---

## 6. Clinical Note

**Responsibility:** free-text clinical documentation authored against a
visit (progress notes, consultation notes, discharge summaries, addenda).

**Owns (tables):** `clinical_notes`.

| Domain model | |
|---|---|
| Aggregate root | `ClinicalNote` |
| Domain events published | `ClinicalNoteCreated`, `ClinicalNoteSubmittedForReview`, `ClinicalNoteFinalized` |

**Representative use cases:** `CreateClinicalNote`, `UpdateDraftNote`,
`SubmitNoteForReview`, `FinalizeNote`, `AddAddendum`,
`RequestAIAssistedDraft` (calls the AI module's public command port and
returns immediately — the note stays in `draft` until the AI module's
async result event arrives; see `09_ai_gateway_and_storage.md`).

**Public interface:**

| Kind | Name | Purpose |
|---|---|---|
| Query | `ClinicalNoteQueryPort.get_notes_for_visit(visit_id)` / `get_notes_for_patient(patient_id)` | Used by Patient History |
| Event | `ClinicalNoteFinalized` | Consumed by Patient History, Audit |

**Depends on:** Visit, Patient, Authentication (author identity), AI
(command call for drafting; subscribes to `EmbeddingGenerated` and
`AISessionCompleted` to update its own `is_ai_generated`/`embedding_id`
fields — see `09_ai_gateway_and_storage.md` for why AI never writes into
another module's table directly). **Depended on by:** Patient History,
Audit.

---

## 7. SOAP Note

**Responsibility:** the structured Subjective/Objective/Assessment/Plan
encounter summary — one per visit.

**Owns (tables):** `soap_notes`.

| Domain model | |
|---|---|
| Aggregate root | `SoapNote` |
| Domain events published | `SoapNoteCreated`, `SoapNoteFinalized` |

**Representative use cases:** `CreateSoapNote`, `UpdateSoapSection`,
`RequestAIDraftFromTranscript`, `RequestCodingSuggestions`,
`FinalizeSoapNote`.

**Public interface:**

| Kind | Name | Purpose |
|---|---|---|
| Query | `SoapNoteQueryPort.get_soap_note_for_visit(visit_id)` | Used by Patient History, Lab Report (context for interpretation) |
| Event | `SoapNoteFinalized` | Consumed by Patient History, Audit |

**Depends on:** Visit, Patient, Authentication, AI, Patient
(`ConditionCodeLookupPort` for coding suggestions). **Depended on by:**
Patient History, Audit.

---

## 8. Patient History

**Responsibility:** the pre-computed, read-optimized timeline of a
patient's clinical events — architecturally distinct from the other
modules in that it has **no independent write-side business rules**; it is
this system's first CQRS-style read projection. Its only "domain rule" is
translation (event → timeline row), not clinical policy.

**Owns (tables):** `patient_timeline_events`.

**How it's populated:** subscribes to domain events from **every** clinical
module — `VisitCompleted`, `ClinicalNoteFinalized`, `SoapNoteFinalized`,
`PatientAllergyRecorded`, `PatientMedicationPrescribed`,
`PatientConditionDiagnosed`, `LabResultRecorded`, `AISessionCompleted`,
`AttachmentUploaded` — and, inside the *same transaction* as the
subscribing handler, inserts the corresponding `patient_timeline_events`
row (the outbox-adjacent pattern documented in
`../database/04_ai_features.md`). This is the module whose entire purpose
is demonstrated by, and dependent on, the event-driven module
communication model in `10_module_communication.md`.

**Representative use cases:** `ProjectTimelineEvent` (internal, invoked by
event subscribers only — never called directly by the API), `GetPatientTimeline`
(the one query use case external callers actually invoke).

**Public interface:** `PatientHistoryQueryPort.get_timeline(patient_id,
pagination)`. **No commands** — this module never accepts a write request
from a human actor, only from other modules' events.

**Depends on:** every clinical module's events (subscription, not a
compile-time `public/` import — see `10_module_communication.md` for why
subscribing to an event is not the same kind of dependency as calling a
port). **Depended on by:** nothing (leaf/read-side).

---

## 9. Lab Report

**Responsibility:** ordered/received lab reports and their individual
result line items.

**Owns (tables):** `lab_reports`, `lab_results`, `lab_test_catalog` (global
LOINC catalog, owned here).

| Domain model | |
|---|---|
| Aggregate root | `LabReport` (child entity: `LabResult`) |
| Domain events published | `LabReportOrdered`, `LabResultRecorded`, `CriticalLabResultFlagged`, `LabReportFinalized` |

`LabResult` is a child of `LabReport` (not its own aggregate) because a
report's overall status is derived from the state of all its results —
that invariant needs both loaded together.

**Representative use cases:** `OrderLabReport`, `RecordSpecimenCollection`,
`RecordLabResult`, `FinalizeLabReport`, `CancelLabReport`. Recording a
result whose `abnormal_flag` is `critical_low`/`critical_high` triggers
`CriticalLabResultFlagged` in the same use case — this is a domain rule
(the entity/domain service decides "is this critical"), not something the
use case hardcodes.

**Public interface:**

| Kind | Name | Purpose |
|---|---|---|
| Query | `LabReportQueryPort.get_reports_for_patient(patient_id)` / `get_pending_reports(org_id)` | Used by Patient History, ops dashboards |
| Event | `CriticalLabResultFlagged` | Consumed by Notification (urgent alert to ordering doctor), Patient History |

**Depends on:** Patient, Visit (optional), Doctor. **Depended on by:**
Patient History, AI (future interpretation), Notification, Audit.

---

## 10. AI

**Responsibility:** a **generic**, domain-agnostic gateway to the
platform's AI capabilities (text generation, speech-to-text, OCR,
embeddings) — it does not know what a "SOAP note" is, only that it was
asked to summarize some text or transcribe some audio on behalf of a given
`source_table`/`source_id`. This genericity is deliberate: it's what lets
every clinical module reuse the same AI infrastructure without the AI
module accumulating per-caller special cases.

**Owns (tables):** `ai_sessions`, `conversation_transcripts`.

| Domain model | |
|---|---|
| Aggregate root | `AiSession` (child entity: `ConversationTranscript` segments) |
| Domain events published | `AISessionStarted`, `AISessionCompleted`, `AISessionFailed`, `EmbeddingGenerated` |

**Representative use cases:** `StartAISession`, `IngestTranscriptSegment`
(called repeatedly during a streaming ambient-scribe recording),
`CompleteAISession`, `RequestTextSummarization`, `RequestCodingAssist`,
`GenerateEmbedding`. Full Gateway design (provider abstraction, resilience,
cost tracking, async orchestration) is in `09_ai_gateway_and_storage.md`.

**Public interface:**

| Kind | Name | Purpose |
|---|---|---|
| Command | `AISessionCommandPort.start_session(...)` / `request_summarization(text, source_ref)` | Called by Clinical Note, SOAP Note |
| Query | `AISessionQueryPort.get_session_status(session_id)` | Polled or used for status display |
| Event | `AISessionCompleted`, `EmbeddingGenerated` | Consumed by whichever module owns `source_table`/`source_id` — it updates its own row; AI never writes into another module's table |

**Depends on:** Patient, Visit (existence checks only, via query ports —
not structurally coupled to their internals). **Depended on by:** Clinical
Note, SOAP Note, Lab Report (future), Patient History.

---

## 11. Audit

**Responsibility:** the compliance sink — "what changed" (via the
database-trigger-populated `audit_logs`, see
`../database/06_audit_and_activity.md`) and "who accessed what" (via this
module's own write path, `activity_logs`).

**Owns (tables):** `audit_logs` (mostly read-only from the application's
perspective — populated by DB trigger, not application code),
`activity_logs` (written directly by this module).

**Representative use cases:** `RecordActivity` (called by an API dependency
on sensitive read routes — "log that user X viewed patient Y's chart"),
`GetAuditTrailForRecord`, `GetActivityLogForUser` (compliance-officer
queries).

**Special role in the dependency graph:** Audit is the one module
permitted to subscribe to **every** domain event published anywhere in the
system, for supplementary structured audit context. No other module ever
depends on Audit's `public/` interface for its own business operation —
Audit is a pure sink, never a source. If Audit is unavailable, no other
module's core function should be blocked (activity logging is fire-and-
forget via a queue, not a synchronous dependency — see
`08_background_workers.md`).

**Depends on:** nothing for its core write path (the caller supplies
`user_id`/`resource_type`/`resource_id` directly). **Depended on by:**
nothing (leaf, tier 0 by absence of dependents rather than absence of
dependencies).

---

## 12. File Storage

**Responsibility:** a **generic** attachment/object-storage capability
(MinIO-backed), analogous in spirit to the AI module's genericity —
File Storage does not know what a "lab report" or "doctor signature" is,
only `owner_type`/`owner_id`/bytes.

**Owns (tables):** `attachments`.

| Domain model | |
|---|---|
| Aggregate root | `Attachment` |
| Domain events published | `AttachmentUploadRequested`, `AttachmentUploaded`, `AttachmentDeleted`, `AttachmentVirusDetected` |

**Representative use cases:** `RequestUploadUrl` (issues a MinIO presigned
URL), `ConfirmUpload` (records metadata, enqueues a virus-scan task),
`RequestDownloadUrl`, `DeleteAttachment`, `ReconcileOrphanedObjects`
(scheduled — see `../database/09_best_practices_and_performance.md §1.3`).
Full design in `09_ai_gateway_and_storage.md`.

**Public interface:**

| Kind | Name | Purpose |
|---|---|---|
| Command | `FileStorageCommandPort.request_upload_url(owner_type, owner_id, filename, content_type)` | Called by Patient (photo), Doctor (signature), Organization (logo), Lab Report (scanned reports), Clinical/SOAP Note |
| Query | `FileStorageQueryPort.list_attachments(owner_type, owner_id)` / `get_download_url(attachment_id)` | Same callers |
| Event | `AttachmentVirusDetected` | Consumed by Notification (urgent), Audit |

**Depends on:** nothing in `modules/` (deliberately decoupled — this is
what keeps it trivially reusable and, later, trivially extractable; see
`13_microservices_migration_path.md`). **Depended on by:** Patient,
Doctor, Organization, Lab Report, Clinical Note, SOAP Note.

---

## 13. Notification

**Responsibility:** turning events from every other module into outbound
communication (email, SMS, push, in-app) — the system's primary example of
a **reactive**, event-driven module with almost no inbound commands.

**Owns:** `Notification`, `NotificationTemplate` (module-local persistence
— not part of the 22-table clinical schema in `../database/`, since
notification delivery state is operational data, not clinical record data;
schema for this module is intentionally out of scope for this document set
and would be specified when the module is implemented).

| Domain model | |
|---|---|
| Aggregate roots | `Notification`, `NotificationTemplate` |
| Notable value object | `NotificationChannel` (email / sms / push / in_app) |
| Domain events published | `NotificationQueued`, `NotificationSent`, `NotificationDeliveryFailed` |

**Representative use cases:** `SendNotification` (explicit synchronous-ish
trigger, e.g. "send password reset email now"), `RenderAndQueueNotification`
(the handler behind most event subscriptions), `RecordDeliveryStatus`
(provider webhook callback).

**Reacts to (event subscriptions):** `UserRegistered` (welcome),
`PasswordResetRequested`, `VisitScheduled`/`VisitCheckedIn` (reminders),
`CriticalLabResultFlagged` (urgent), `AISessionCompleted`,
`AttachmentVirusDetected` (urgent), `UserRoleAssigned`.

**Public interface:** `NotificationCommandPort.send_notification(...)` —
used sparingly, by Authentication only, for flows that need a guaranteed
send rather than best-effort event reaction.

**Depends on:** Authentication (`UserQueryPort` for staff contact info),
Patient (`PatientQueryPort` for patient-facing contact info).
**Depended on by:** nothing (leaf).
