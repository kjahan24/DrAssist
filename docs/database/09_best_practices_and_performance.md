# Database Best Practices & Performance Optimization

## Part 1: Best practices

### 1.1 Security & access control

- **Least-privilege database roles.** The application connects as a role
  with `SELECT/INSERT/UPDATE/DELETE` on tenant tables but **no**
  `BYPASSRLS`, no `SUPERUSER`, and no DDL rights. A separate `migrator` role
  (used only by CI/CD, never by the running app) owns DDL and RLS policy
  changes. This is what makes RLS an actual security boundary rather than a
  convention the app could accidentally step around.
- **RLS is mandatory, not optional, per tenant table** (`ENABLE ROW LEVEL
  SECURITY` + `FORCE ROW LEVEL SECURITY`), enforced by a CI check that
  diffs the migration history against the table list and fails if a new
  tenant-scoped table lacks a policy.
- **PHI/PII encryption at rest.** Beyond disk/volume encryption (Postgres
  data directory on an encrypted EBS/managed-disk volume — infrastructure
  concern, not schema), specific high-sensitivity columns
  (`patients.national_id_number_encrypted`, `users.mfa_secret_encrypted`)
  are encrypted **at the application layer** before the value reaches SQL,
  using envelope encryption via a KMS. This is deliberately not done with
  in-SQL `pgcrypto` calls (`pgp_sym_encrypt(...)` in a query) because the
  plaintext would then transit the query log, `pg_stat_statements`, and
  replication stream in cleartext at some point in the pipeline.
- **Secrets never in the schema.** Connection strings, KMS keys, and the
  RLS session GUC value are runtime configuration (see
  `../ARCHITECTURE.md`'s `core/config.py`), never hard-coded or stored in a
  table.
- **`SET LOCAL`, never `SET`, for the tenant GUC**, and always at the start
  of every transaction — see `00_overview.md`. Under a transaction-mode
  connection pooler (PgBouncer), a connection is handed to a different
  request between transactions; a session-level `SET` would leak the
  previous tenant's context.
- **Audit the auditors.** `audit_logs`/`activity_logs` themselves are
  covered by the same RLS and role restrictions as any tenant table; only
  the `migrator`/superuser role can alter or truncate them, and that
  capability itself should be gated by infrastructure-level access control
  (not something this schema can enforce alone).

### 1.2 Data integrity

- **Push invariants into the database, not just application code.**
  Every constraint documented per-table (`CHECK`, `UNIQUE`, `NOT NULL`, FK
  `ON DELETE` behavior) is enforced at the Postgres level. Application-level
  validation (Pydantic schemas) is a UX improvement (fast, friendly errors)
  — it is not a substitute for DB constraints, which are the actual
  correctness guarantee against bugs, migrations, and direct data fixes.
- **Prefer `RESTRICT` over `CASCADE` for clinical data.** FKs from
  `visits`, `vital_signs`, `clinical_notes`, `lab_reports`, etc. back to
  `patients`/`doctors`/`organizations` use `ON DELETE RESTRICT` — clinical
  history must never silently cascade-delete. Soft delete (`deleted_at`) is
  the only sanctioned deletion path for these entities; hard deletes are a
  deliberate, audited, exceptional operation (e.g., GDPR erasure), not a
  routine one.
- **Soft-delete uniqueness via partial indexes**, consistently, everywhere
  a natural key exists (`users.email` per org, `patients.medical_record_number`
  per org, `organizations.subdomain`) — see the pattern established in
  `00_overview.md`. Forgetting the `WHERE deleted_at IS NULL` filter on a
  unique index is the single most common soft-delete bug; it is called out
  explicitly on every table that needs it in this design.
- **Snapshot denormalization is explicit and named**, never accidental.
  Every place this schema denormalizes a value (e.g.
  `patient_conditions.condition_name` alongside `condition_code_id`,
  `lab_results.test_name` alongside `test_catalog_id`,
  `vital_signs.patient_id` alongside `visit_id`) is called out in that
  table's spec with the reason (survive catalog edits / avoid a join on a
  hot path / enable direct RLS filtering). If a denormalized value isn't
  documented as such, treat its presence as a bug, not a shortcut.

### 1.3 Retention & data lifecycle

- **Right-to-erasure vs. medical-record retention.** Most jurisdictions
  legally require retaining medical records for a minimum period (often
  6–10+ years) even when a patient requests deletion — this directly
  conflicts with a naive "GDPR delete = hard delete" implementation.
  Resolution: `patients.deleted_at` triggers **anonymization** (null out
  direct identifiers: name, contact info, national ID) rather than row
  deletion, preserving clinical history in de-identified form for the
  legally required retention window; true hard deletion happens only after
  that window, via a scheduled job, not user action.
- **Log retention is time-boxed, not indefinite.** `audit_logs` and
  `activity_logs` grow unboundedly by design (append-only). A retention
  policy (e.g., 7 years for `audit_logs` to match typical healthcare
  audit-trail regulation, 1–2 years for `activity_logs`) is enforced by
  dropping old **partitions** (see §2.3), not by `DELETE` statements
  against a monolithic table.
- **Attachment lifecycle is two-phase.** Soft-deleting an `attachments` row
  does not delete the MinIO object immediately (in case of accidental
  deletion / for the same retention reasons as above). A scheduled
  reconciliation job hard-deletes MinIO objects for `attachments` rows
  soft-deleted more than N days ago, keeping storage cost bounded without
  making deletion irreversible in the moment.

### 1.4 Enum vs. lookup table (recap and decision rule)

| Use a native `ENUM` when... | Use a lookup table when... |
|---|---|
| The value set is small (< ~20 values) | The value set is large (hundreds/thousands — ICD-10, LOINC) |
| Only engineers change it (ships with a migration) | Tenant admins or content curators need to manage it |
| It's a workflow/status flag | It's a coded external standard (needs code + description + metadata) |
| Renames/removals are effectively never needed | The set is expected to evolve independent of deploys |

### 1.5 Testing

- **Migration tests in CI**: every PR spins up a fresh Postgres 16
  container, runs `alembic upgrade head` from empty, then `alembic
  downgrade base` and back `upgrade head` again, to catch irreversible or
  broken `downgrade()` implementations before merge.
- **Constraint tests**: a lightweight test suite that asserts each
  documented `CHECK`/`UNIQUE` constraint actually rejects the invalid case
  it's meant to prevent (e.g. inserting a `vital_signs` row with
  `pain_score = 11` must raise) — schema constraints are part of the
  contract and deserve the same regression coverage as application logic.
- **RLS tests**: a dedicated test that, as a non-superuser app role with
  two different `app.current_organization_id` values set across two
  sessions, asserts tenant A can never read tenant B's rows — the most
  important test in the whole suite for a multi-tenant healthcare system.

---

## Part 2: Performance optimization

### 2.1 Indexing strategy

- **Every tenant-scoped table's most common query starts with
  `organization_id`** — composite indexes throughout this design put
  `organization_id` first (e.g. `ix_visits_status` on `(organization_id,
  status)`), so the tenant filter is satisfied by the index itself, not a
  post-filter scan.
- **Every FK column is indexed.** Unlike the referenced side (PK, always
  indexed), Postgres does **not** automatically index the referencing FK
  column — every FK in this design has a corresponding `ix_` index (or is
  covered by a composite index with the FK column leading), both for join
  performance and because an unindexed FK makes `ON DELETE`/`ON UPDATE`
  cascade checks scan the entire child table.
- **Partial indexes** are used wherever a query pattern only ever cares
  about a subset of rows: `WHERE deleted_at IS NULL` for all soft-delete
  uniqueness, `WHERE abnormal_flag <> 'normal'` on `lab_results` (critical
  results dashboards never scan normal results), `WHERE is_primary` on
  `doctor_specialties`. A partial index is smaller, faster to scan, and
  cheaper to maintain than a full index that's mostly dead weight for the
  query patterns that matter.
- **BRIN indexes** on `created_at`/`occurred_at`/`recorded_at` for the
  high-volume, naturally-time-ordered append-only tables (`audit_logs`,
  `activity_logs`, `auth_login_attempts`, `vital_signs`). BRIN indexes are
  a fraction of the size of a B-tree for this access pattern (range scans
  over a column that correlates with physical insert order) and are the
  right tool once these tables reach tens of millions of rows.
- **GIN indexes** for `JSONB` columns queried by key (`organizations.settings`,
  `ai_sessions.metadata`) and for full-text search (`clinical_notes.search_vector`,
  `soap_notes.search_vector`) and trigram fuzzy search
  (`condition_codes.description`, via `pg_trgm`).
- **Review, don't guess.** `pg_stat_user_indexes` (unused-index detection)
  and `pg_stat_statements` (actual query cost) should drive any index
  addition/removal beyond this initial design — an index not backed by an
  observed query pattern is pure write-amplification cost.

### 2.2 Query patterns

- **Avoid N+1 across the clinical spine.** The patient chart view (patient
  + allergies + medications + conditions + recent visits + recent vitals)
  is the hottest read path in the product. Use `selectinload`/explicit
  batched queries at the repository layer, not per-row lazy loading — this
  is an application-layer concern, but the schema supports it by keeping
  every one of those tables indexed on `patient_id`.
- **`patient_timeline_events` exists precisely to avoid a fan-out query.**
  Rendering "patient history" by joining across nine tables on every page
  load does not scale; the timeline table is pre-computed at write time so
  the read path is a single indexed range scan (see `04_ai_features.md`).
- **Use `EXPLAIN (ANALYZE, BUFFERS)`** during development for any query
  touching `visits`, `patients`, `lab_results`, or the log tables before it
  ships — these are the tables large enough for a missing index or a bad
  join order to matter in production but small enough in dev/staging to
  hide the problem until real data volume arrives.
- **Prefer covering indexes for hot list queries** where the row is
  narrow — e.g. an index on `visits (doctor_id, scheduled_start_at) INCLUDE
  (status, patient_id)` for a doctor's daily schedule view avoids a
  heap fetch entirely.

### 2.3 Partitioning (for scale, not day one)

Postgres native declarative partitioning is recommended once these tables
approach tens of millions of rows — the schema is designed to make adopting
it later a schema-only change, not a rewrite:

| Table | Partition strategy | Trigger for adoption |
|---|---|---|
| `audit_logs` | `RANGE` on `occurred_at`, monthly | > ~50M rows or retention-policy pruning needed |
| `activity_logs` | `RANGE` on `occurred_at`, monthly | Same |
| `conversation_transcripts` | `RANGE` on `created_at`, monthly | High-volume ambient-scribe adoption |
| `vital_signs` | `RANGE` on `recorded_at`, quarterly | Very high visit volume tenants |

Constraint to design around now: a partitioned table's primary key **must
include the partition key column**. For these tables that means the
eventual partitioned PK becomes `(id, occurred_at)` (or equivalent)
instead of `id` alone — a backward-compatible change (the surrogate `id`
remains globally unique and is what every FK/application reference uses;
only the physical PK constraint widens), but worth knowing before, not
during, a size-driven migration under pressure. Retention (§1.3) then
becomes `DROP PARTITION` instead of a slow `DELETE`.

### 2.4 Connection & pool management

- **PgBouncer in transaction pooling mode** in front of Postgres for the
  API tier (many short-lived transactions from an async FastAPI app);
  Celery workers can use session pooling if a worker task needs
  session-level features. Transaction pooling is what makes the `SET LOCAL`
  tenant-GUC pattern (§1.1) both necessary and correct.
- **SQLAlchemy pool sizing** (`backend/app/core/config.py`'s
  `DATABASE_POOL_SIZE`/`DATABASE_MAX_OVERFLOW`, already scaffolded) should
  be sized *per backend replica* against PgBouncer's own pool, not against
  Postgres's `max_connections` directly — Postgres connections are the
  scarce resource; PgBouncer is what lets many app replicas share a small
  number of them.
- **Statement timeouts** set at the role level
  (`ALTER ROLE app_user SET statement_timeout = '30s'`) so a runaway query
  from a bug can't hold a connection (and, transitively, an RLS-scoped
  transaction) indefinitely.

### 2.5 Vacuum & bloat

- **High-churn tables get tuned autovacuum settings**, not defaults —
  `visits` and `vital_signs` (frequent `UPDATE` as a visit progresses
  through `status` values) benefit from a lower
  `autovacuum_vacuum_scale_factor` than Postgres's default (which is tuned
  for mostly-static tables) so dead tuples don't accumulate between
  autovacuum runs.
- **Append-only tables (`audit_logs`, `activity_logs`,
  `conversation_transcripts`) never `UPDATE`**, so they don't bloat the
  same way — their vacuum concern is purely about visibility-map
  maintenance for index-only scans, which default autovacuum settings
  handle adequately.
- **`GENERATED ALWAYS AS ... STORED` columns** (`vital_signs.bmi`,
  `clinical_notes.search_vector`, `soap_notes.search_vector`) recompute and
  rewrite on every relevant `UPDATE` — expected and acceptable given these
  tables' write patterns (vitals are rarely updated after entry; notes are
  edited pre-finalization only), but worth remembering if a future
  high-frequency-update table considers a generated column.

### 2.6 Read scaling

- **A read replica for reporting/analytics** is the recommended path once
  dashboard/export queries start competing with transactional traffic —
  route BI/reporting connections there rather than adding ad hoc caching in
  the primary write path.
- **`clinical_notes.embedding_id`/`soap_notes.embedding_id`/etc. keep
  Postgres out of the vector-similarity-search business entirely** — that
  workload lives in Qdrant (see `../ARCHITECTURE.md`), which is a
  deliberate scaling decision: Postgres stores structured clinical data and
  relationships; Qdrant handles high-dimensional nearest-neighbor search.
  Don't let future AI features pull vector storage back into Postgres as a
  shortcut — it doesn't scale the same way and this schema is built
  assuming it won't need to.

### 2.7 Monitoring

- Enable `pg_stat_statements` from day one — the single highest-leverage
  extension for catching a slow query before it's a production incident,
  and it costs nothing when idle.
- Track index bloat and unused indexes quarterly (`pg_stat_user_indexes`,
  `pgstattuple`) — an index carried "just in case" that nothing ever uses is
  pure write-path tax.
- Alert on `autovacuum` falling behind (`n_dead_tup` trending up without a
  corresponding vacuum) on the high-churn tables named in §2.5 before it
  becomes a query-latency incident.
