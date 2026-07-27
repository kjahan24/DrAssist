# SQLAlchemy Model Folder Structure

This is a **structural mapping only** — file layout and what each file is
responsible for. No model code is included here; implementation happens
against the existing Clean Architecture scaffold at
`backend/app/infrastructure/database/` (see `../ARCHITECTURE.md`).

## Directory layout

```
backend/app/infrastructure/database/
├── base.py                      # Declarative Base, naming convention, shared mixins (exists)
├── session.py                   # Engine + session factory (exists)
├── mixins/
│   ├── __init__.py
│   ├── uuid_pk.py                # UUIDPrimaryKeyMixin — id column
│   ├── audit_columns.py          # AuditColumnsMixin — created_at/updated_at/created_by/updated_by
│   ├── soft_delete.py            # SoftDeleteMixin — deleted_at + is_active hybrid property
│   └── tenant_scoped.py          # TenantScopedMixin — organization_id column + FK
├── enums/
│   ├── __init__.py
│   ├── identity_enums.py         # organization_type, organization_status, location_type, user_status
│   ├── clinical_enums.py         # sex, blood_type, marital_status, contact_type, allergen_type,
│   │                              #   allergy_severity, clinical_status, medication_route/status
│   ├── encounter_enums.py        # visit_type, visit_status, clinical_note_type, content_review_status
│   ├── ai_enums.py                # ai_session_type/status, speaker_role, timeline_event_type
│   └── lab_enums.py               # lab_report_status, lab_result_status, lab_abnormal_flag,
│                                    #   attachment_owner_type, virus_scan_status, audit_action, activity_type
└── models/
    ├── __init__.py                # Imports every model module below — required for Alembic autogenerate
    │
    ├── identity/
    │   ├── __init__.py
    │   ├── organization.py         # Organization
    │   ├── organization_location.py# OrganizationLocation
    │   ├── user.py                 # User
    │   ├── role.py                 # Role
    │   ├── permission.py           # Permission
    │   ├── role_permission.py      # RolePermission
    │   └── user_role.py            # UserRole
    │
    ├── auth/
    │   ├── __init__.py
    │   ├── auth_session.py          # AuthSession
    │   ├── password_reset_token.py  # AuthPasswordResetToken
    │   ├── email_verification_token.py # AuthEmailVerificationToken
    │   └── login_attempt.py         # AuthLoginAttempt
    │
    ├── clinical_master/
    │   ├── __init__.py
    │   ├── specialty.py              # Specialty
    │   ├── doctor.py                 # Doctor
    │   ├── doctor_specialty.py       # DoctorSpecialty
    │   ├── condition_code.py         # ConditionCode
    │   ├── patient.py                # Patient
    │   ├── patient_contact.py        # PatientContact
    │   ├── patient_allergy.py        # PatientAllergy
    │   ├── patient_medication.py     # PatientMedication
    │   └── patient_condition.py      # PatientCondition
    │
    ├── encounters/
    │   ├── __init__.py
    │   ├── visit.py                  # Visit
    │   ├── vital_signs.py            # VitalSigns
    │   ├── clinical_note.py          # ClinicalNote
    │   └── soap_note.py              # SoapNote
    │
    ├── ai/
    │   ├── __init__.py
    │   ├── ai_session.py             # AiSession
    │   ├── conversation_transcript.py# ConversationTranscript
    │   └── patient_timeline_event.py # PatientTimelineEvent
    │
    ├── labs/
    │   ├── __init__.py
    │   ├── lab_test_catalog.py       # LabTestCatalog
    │   ├── lab_report.py             # LabReport
    │   └── lab_result.py             # LabResult
    │
    ├── files/
    │   ├── __init__.py
    │   └── attachment.py             # Attachment
    │
    └── audit/
        ├── __init__.py
        ├── audit_log.py              # AuditLog  (mapped read-mostly; inserts happen via DB trigger, not the ORM)
        └── activity_log.py           # ActivityLog (ORM-inserted directly by the app)
```

## Mapping rules

1. **One file per table**, file name = `snake_case(singular table concept)`,
   class name = `PascalCase`. Join tables get their own file even though
   they're small (`role_permission.py`, `user_role.py`,
   `doctor_specialty.py`) — consistent with every table being a first-class
   entity (see naming conventions in `00_overview.md`).
2. **Every model class composes the shared mixins** in a fixed order:
   `TenantScopedMixin` (if applicable) → `UUIDPrimaryKeyMixin` →
   `AuditColumnsMixin` → `SoftDeleteMixin`. This mirrors the "standard
   columns on every table" rule and means no model hand-declares `id`,
   `created_at`, `updated_at`, `created_by`, `updated_by`, or `deleted_at` —
   only its own domain-specific columns.
3. **Global/reference tables** (`Permission`, `Specialty`, `ConditionCode`,
   `LabTestCatalog`) omit `TenantScopedMixin`.
4. **Append-only tables** (`AuditLog`, `ActivityLog`, `AuthLoginAttempt`,
   `ConversationTranscript`, `PatientTimelineEvent`) still compose
   `AuditColumnsMixin`/`SoftDeleteMixin` for column-shape consistency with
   the rest of the schema, but are documented (via a shared
   `ImmutableMixin`/docstring convention) as insert-only from the
   application/repository layer — the actual enforcement is the
   `reject_mutation()` database trigger from `06_audit_and_activity.md`,
   not application discipline alone.
5. **Enums map to `sqlalchemy.Enum` with `native_enum=True`**, pointing at
   the Postgres type created by the corresponding Alembic migration (see
   `08_migration_strategy.md`) rather than letting SQLAlchemy manage enum
   DDL — the migration is the source of truth for the type, matching the
   "no schema drift between Alembic and the DB" principle.
6. **`models/__init__.py` imports every module** transitively (each
   sub-package's `__init__.py` imports its models; the top-level
   `models/__init__.py` imports every sub-package). This is required for
   `Base.metadata` to see every table when Alembic's `env.py` runs
   `--autogenerate` — a model that isn't imported here is invisible to
   migration generation regardless of how correctly it's written.
7. **Relationships (`relationship()`)** are declared only for the
   *primary*, strictly-typed foreign keys documented per table. Polymorphic
   references (`Attachment.owner_id`, `PatientTimelineEvent.source_id`,
   `AuditLog.record_id`) are **not** modeled as `relationship()` — they have
   no single target class, consistent with there being no DB-level FK for
   them either (see `00_overview.md`).

## Where this plugs into Clean Architecture

Per `../ARCHITECTURE.md`, these SQLAlchemy models are **infrastructure**,
not domain. They are the persistence mapping the concrete repository
implementations (`app/infrastructure/repositories/`) translate to/from the
framework-free domain entities in `app/domain/entities/`. No use case or API
code should import from `app/infrastructure/database/models/` directly.
