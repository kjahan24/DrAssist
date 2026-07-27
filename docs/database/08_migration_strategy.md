# Migration Strategy (Alembic)

Builds on the Alembic environment already scaffolded at
`backend/alembic/` (see `../ARCHITECTURE.md`). This document defines the
**ordering, sequencing, and operational rules** for turning this schema
design into real migrations.

## 1. Migration ordering (dependency-driven, not module-numbered)

The 22-module brief numbers modules for readability, but `CREATE TABLE`
order must follow foreign-key dependency order. Recommended migration
sequence (one logical migration per numbered step; steps may be split
further, but never reordered):

| # | Migration | Creates |
|---|---|---|
| 1 | `0001_extensions_and_functions` | `CREATE EXTENSION citext, pg_trgm`; `gen_random_uuid()` needs no extension (built into PG13+); `set_updated_at()`, `reject_mutation()`, `write_audit_log()` functions |
| 2 | `0002_enum_types` | Every `CREATE TYPE ... AS ENUM` from the enum catalog, in one migration so later migrations can reference any of them |
| 3 | `0003_organizations` | `organizations` (without `logo_attachment_id`), `organization_locations` |
| 4 | `0004_users` | `users` |
| 5 | `0005_auth` | `auth_sessions`, `auth_password_reset_tokens`, `auth_email_verification_tokens`, `auth_login_attempts` |
| 6 | `0006_rbac` | `permissions`, `roles`, `role_permissions`, `user_roles` (+ seed data, see §4) |
| 7 | `0007_reference_catalogs` | `specialties`, `condition_codes`, `lab_test_catalog` (+ seed data) |
| 8 | `0008_doctors` | `doctors`, `doctor_specialties` |
| 9 | `0009_patients` | `patients`, `patient_contacts`, `patient_allergies`, `patient_medications`, `patient_conditions` |
| 10 | `0010_visits` | `visits` |
| 11 | `0011_ai_sessions` | `ai_sessions` (before clinical_notes/soap_notes, which reference it) |
| 12 | `0012_encounters` | `vital_signs`, `clinical_notes`, `soap_notes` |
| 13 | `0013_conversation_transcripts` | `conversation_transcripts` |
| 14 | `0014_labs` | `lab_reports`, `lab_results` |
| 15 | `0015_attachments` | `attachments` |
| 16 | `0016_organizations_attachment_fks` | `ALTER TABLE organizations ADD COLUMN logo_attachment_id ...`; `ALTER TABLE users ADD COLUMN avatar_attachment_id ...`; `ALTER TABLE doctors ADD COLUMN signature_attachment_id ...`; `ALTER TABLE patients ADD COLUMN photo_attachment_id ...` — resolves the circular references noted per-table |
| 17 | `0017_patient_timeline_events` | `patient_timeline_events` |
| 18 | `0018_audit_logs` | `audit_logs` |
| 19 | `0019_activity_logs` | `activity_logs` |
| 20 | `0020_row_level_security` | `ENABLE ROW LEVEL SECURITY` + policies on every tenant-scoped table (see `00_overview.md`) |
| 21 | `0021_audit_triggers` | Attach `write_audit_log()` to every audited table; attach `reject_mutation()` to every append-only table; attach `set_updated_at()` to every table |

This is deliberately **more migrations, more granular**, rather than one
giant initial migration — each is independently reviewable, and a bad
migration can be identified and rolled back (`alembic downgrade -1`) without
reverting unrelated tables.

## 2. Alembic configuration specifics

- `alembic/env.py` already builds `target_metadata` from
  `app.infrastructure.database.base.Base.metadata` and imports
  `app.infrastructure.database.models` for autogenerate discovery (existing
  scaffold) — every new model file must be imported transitively from
  `models/__init__.py` or autogenerate will silently omit it.
- **Never fully trust `--autogenerate` for this schema.** It reliably
  detects new/dropped tables and columns, but it does **not** generate:
  - `CREATE TYPE ... AS ENUM` (must be hand-written, once, in `0002`)
  - Partial/expression indexes (`WHERE deleted_at IS NULL`)
  - `CHECK` constraints referencing multiple columns
  - `GENERATED ALWAYS AS` computed columns (`bmi`, `search_vector`)
  - RLS policies and `FORCE ROW LEVEL SECURITY`
  - Trigger creation/attachment

  Treat autogenerate as a first draft for simple column/table changes only;
  hand-review and hand-write every migration in this schema.
- Set `revision_environment = true` disabled (default) — this project does
  not need multi-environment revision resolution; a single linear history is
  enforced (see §5).

## 3. Enum evolution strategy

Adding a new enum value:

```sql
-- Safe: adding a value never breaks existing rows or queries.
ALTER TYPE visit_status_enum ADD VALUE IF NOT EXISTS 'rescheduled';
```

Constraints on `ALTER TYPE ... ADD VALUE`:
- Cannot run inside the same transaction block as a statement that *uses*
  the new value (PostgreSQL restriction) — so a migration that adds a value
  and then back-fills data with it must be split into two Alembic
  migrations (or use `op.execute()` with autocommit block —
  `with op.get_context().autocommit_block():`).
- **Removing or renaming** an enum value has no direct `ALTER TYPE`
  equivalent. The safe pattern: create a new type, migrate the column over
  with `USING` casting through `TEXT`, drop the old type. This is why the
  enum catalog in `00_overview.md` favors small, deliberately-chosen value
  sets — enum *churn* is the expensive case, not enum *use*.
- For value sets expected to change more than rarely, prefer the lookup
  table pattern already used for `specialties`/`condition_codes`/`lab_test_catalog`
  instead of adding a new enum type.

## 4. Reference/seed data

`permissions`, system `roles` (`organization_id IS NULL`), and the initial
`specialties`/`condition_codes`/`lab_test_catalog` rows are **data
migrations**, version-controlled the same as schema migrations:

- Keep seed data in the migration file itself for small, stable sets
  (`permissions`, system `roles`) via `op.bulk_insert()`.
- For large reference sets (`condition_codes` — thousands of ICD-10 rows,
  `lab_test_catalog` — thousands of LOINC rows), load from a versioned CSV
  fixture shipped alongside the migration
  (`backend/alembic/seed_data/icd10_codes.csv`) rather than inlining
  thousands of `INSERT` statements in the migration file — same idempotency
  guarantees, far more reviewable diffs.
- Every seed migration must be **idempotent** (`ON CONFLICT DO NOTHING` /
  `INSERT ... WHERE NOT EXISTS`) so re-running against a partially-seeded
  database is safe.

## 5. Branching & review rules

- **Linear history only.** Alembic supports branching revision graphs;
  this project forbids them by convention — two developers adding
  migrations concurrently must rebase so one revision's `down_revision`
  chains cleanly to the other, not merge two heads. CI (`alembic heads`
  must return exactly one) enforces this.
- One migration = one logical schema change (a table, a related group of
  columns, one index). Do not bundle unrelated table changes into one
  migration — it breaks the "roll back just this" guarantee.
- Every migration PR must include: the generated migration file, and a
  manual review of the ordering table above (does this change belong
  before/after existing steps?).

## 6. Zero-downtime change patterns

For a live production system, several categories of change need
multi-step, backward-compatible sequencing rather than a single blocking
migration:

| Change | Pattern |
|---|---|
| Add a `NOT NULL` column to a large table | 1) add column nullable with a `DEFAULT`, 2) backfill in batches, 3) separate migration adds `NOT NULL` (via `NOT VALID` + `VALIDATE CONSTRAINT` to avoid a full table lock) |
| Add an index on a large table | `CREATE INDEX CONCURRENTLY` (must run outside a transaction — Alembic: `op.execute()` with `autocommit_block()`); never a plain `CREATE INDEX` on a hot table |
| Rename a column | 1) add new column, 2) dual-write from the app, 3) backfill, 4) cut reads over, 5) drop old column — never a bare `RENAME COLUMN` on a table the running application still queries by the old name |
| Change a column type | Same expand/contract pattern as rename; add new column, backfill, cut over, drop old |
| Drop a column/table | Confirm no application code references it (a full deploy cycle after the code stops using it), then drop in its own migration |

## 7. Rollback strategy

- Every migration implements a real `downgrade()` — not `pass`. Reviewed
  with the same rigor as `upgrade()`.
- Destructive `downgrade()`s (dropping a column that had data) are
  acceptable **only** for migrations not yet deployed to production;
  once a migration has shipped to production, prefer a new
  forward-fixing migration over downgrading a live database.
- Migrations that seed reference data implement `downgrade()` as the
  matching `DELETE`, scoped precisely to the rows the `upgrade()` inserted.

## 8. Environment promotion

```
local dev  →  CI (ephemeral Postgres, runs full `alembic upgrade head`)  →  staging  →  production
```

- CI runs `alembic upgrade head` against a fresh Postgres 16 container on
  every PR (already wired in `.github/workflows/ci.yml` at the backend job
  level — add a dedicated `alembic upgrade head` step there once
  migrations exist).
- Staging and production are never migrated by a developer's local Alembic
  invocation — migrations run as a release-pipeline step
  (`docker compose exec backend alembic upgrade head`, or the CI/CD
  deploy job), with the migration step gated to run **before** the new
  application version receives traffic, and the previous application
  version remaining compatible with the *new* schema for the duration of
  a rolling deploy (this is what makes the expand/contract pattern in §6
  necessary, not optional).
