# DrAssist — Database Design Documentation

Production-ready PostgreSQL schema for DrAssist, covering all 22 requested
modules across 33 tables. **Documentation only** — no API endpoints or
application/business logic; see `../ARCHITECTURE.md` for how this schema
plugs into the Clean Architecture backend.

## Read order

1. **[00_overview.md](00_overview.md)** — start here. ER diagrams,
   relationship explanation, multi-tenant strategy (RLS), naming
   conventions, full enum catalog, standard-columns policy.
2. **[01_identity_and_access.md](01_identity_and_access.md)** — Modules 1–4:
   Authentication, Organizations, Users, Roles & Permissions
3. **[02_clinical_master_data.md](02_clinical_master_data.md)** — Modules
   5–10: Doctors, Patients, Patient Contacts, Allergies, Medications,
   Conditions
4. **[03_encounters.md](03_encounters.md)** — Modules 11–14: Visits, Vital
   Signs, Clinical Notes, SOAP Notes
5. **[04_ai_features.md](04_ai_features.md)** — Modules 15–17: AI Sessions,
   Conversation Transcripts, Patient History Timeline
6. **[05_labs_and_attachments.md](05_labs_and_attachments.md)** — Modules
   18–20: Lab Reports, Lab Results, Attachments
7. **[06_audit_and_activity.md](06_audit_and_activity.md)** — Modules
   21–22: Audit Logs, Activity Logs (+ shared trigger functions)
8. **[07_sqlalchemy_structure.md](07_sqlalchemy_structure.md)** — model
   folder layout, mapping rules
9. **[08_migration_strategy.md](08_migration_strategy.md)** — Alembic
   sequencing, enum evolution, zero-downtime patterns, rollback rules
10. **[09_best_practices_and_performance.md](09_best_practices_and_performance.md)**
    — security, integrity, retention, indexing, partitioning, scaling

## Quick facts

| | |
|---|---|
| Tables | 33 (27 strictly tenant-scoped, 2 tenant-scoped with nullable `organization_id` for platform-level events, 4 global reference) |
| Primary keys | `UUID DEFAULT gen_random_uuid()` on every table, no exceptions |
| Multi-tenancy | Shared schema + `organization_id` + Row-Level Security |
| Enum types | 28 native `ENUM`s (see catalog in `00_overview.md`) |
| Soft delete | `deleted_at TIMESTAMPTZ`, partial unique indexes `WHERE deleted_at IS NULL` |
| Append-only tables | `audit_logs`, `activity_logs`, `auth_login_attempts`, `conversation_transcripts`, `patient_timeline_events` — trigger-enforced immutable |
| AI-readiness | Nullable `embedding_id` (Qdrant point ref) on `clinical_notes`, `soap_notes`, `conversation_transcripts`, `lab_results`; provenance fields (`is_ai_generated`, `ai_session_id`, `review_status`, `reviewed_by`) on AI-touchable clinical content |
