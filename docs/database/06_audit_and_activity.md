# Modules 21–22: Audit Logs, Activity Logs

These two tables answer different compliance questions and are both
append-only. This document also defines the two shared trigger functions
referenced throughout the schema: `set_updated_at()` and `reject_mutation()`.

---

## Shared trigger functions

### `set_updated_at()`

Maintains `updated_at` on every table without repeating logic per table.
Applied `BEFORE UPDATE` on every table in the schema.

```sql
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Applied per table, e.g.:
-- CREATE TRIGGER trg_patients_set_updated_at
--     BEFORE UPDATE ON patients
--     FOR EACH ROW EXECUTE FUNCTION set_updated_at();
```

### `reject_mutation()`

Enforces true immutability on append-only, compliance-critical tables
(`audit_logs`, `activity_logs`, `auth_login_attempts`,
`conversation_transcripts`, `patient_timeline_events`). These tables keep
`updated_at`/`updated_by`/`deleted_at` columns for schema consistency with
every other table in the database, but this trigger guarantees they can
never actually be exercised — even by a compromised or misconfigured
application role (short of a superuser dropping the trigger, which is
itself a privileged, audited DDL action).

```sql
CREATE OR REPLACE FUNCTION reject_mutation()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION '% is append-only: % is not permitted on this table',
        TG_TABLE_NAME, TG_OP;
END;
$$ LANGUAGE plpgsql;
```

---

## Module 21: Audit Logs

### `audit_logs`

**Purpose:** Field-level record of every data mutation — what changed, from
what value to what value, who changed it, and when. The core HIPAA/SOC 2
"who changed this record" audit trail. Populated by **database triggers**
(gold standard — cannot be bypassed by application bugs), not application
middleware.

**Tenant scope:** `organization_id`, **nullable** to also capture
platform-level events not tied to a single tenant (e.g. organization
creation itself).

| Column | Type | Nullable | Default | Description |
|---|---|---|---|---|
| `id` | `UUID` | No | `gen_random_uuid()` | PK |
| `organization_id` | `UUID` | Yes | — | FK → `organizations.id` |
| `table_name` | `TEXT` | No | — | Source table of the change |
| `record_id` | `UUID` | No | — | PK of the changed row (every table has a UUID `id`, so this is uniform — see `00_overview.md` naming rationale) |
| `action` | `audit_action_enum` | No | — | |
| `changed_by` | `UUID` | Yes | — | FK → `users.id`; null for system/migration actions |
| `old_values` | `JSONB` | Yes | — | Full row snapshot before change (null for `insert`) |
| `new_values` | `JSONB` | Yes | — | Full row snapshot after change (null for `hard_delete`) |
| `changed_fields` | `TEXT[]` | Yes | — | Names of columns that actually differ, for fast filtering |
| `ip_address` | `INET` | Yes | — | Captured from the app-set session GUC, see note |
| `occurred_at` | `TIMESTAMPTZ` | No | `now()` | |
| `created_at` / `updated_at` / `deleted_at` / `created_by` / `updated_by` | standard, **immutability-enforced** | | | |

- **Primary key:** `id`
- **Foreign keys:** `organization_id → organizations.id ON DELETE SET NULL`; `changed_by → users.id ON DELETE SET NULL`. **No FK on `(table_name, record_id)`** — same polymorphic reasoning as `patient_timeline_events.source_id`; by design this table must be able to reference *any* table, including ones added after `audit_logs` itself was created.
- **Indexes:** `ix_audit_logs_table_record` on `(table_name, record_id, occurred_at DESC)` — "show me the history of this row"; `ix_audit_logs_organization_id_occurred_at`; `ix_audit_logs_changed_by`; BRIN on `occurred_at` for cheap retention-window scans at very high volume
- **Enums:** `audit_action_enum`
- **Soft delete:** none — append-only, trigger-enforced immutable

```sql
CREATE TYPE audit_action_enum AS ENUM ('insert', 'update', 'soft_delete', 'restore', 'hard_delete');

CREATE TABLE audit_logs (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id   UUID REFERENCES organizations(id) ON DELETE SET NULL,
    table_name        TEXT NOT NULL,
    record_id         UUID NOT NULL,
    action            audit_action_enum NOT NULL,
    changed_by        UUID REFERENCES users(id) ON DELETE SET NULL,
    old_values        JSONB,
    new_values        JSONB,
    changed_fields    TEXT[],
    ip_address        INET,
    occurred_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at        TIMESTAMPTZ,
    created_by        UUID,
    updated_by        UUID
);

CREATE INDEX ix_audit_logs_table_record ON audit_logs (table_name, record_id, occurred_at DESC);
CREATE INDEX ix_audit_logs_organization_id_occurred_at ON audit_logs (organization_id, occurred_at DESC);
CREATE INDEX ix_audit_logs_changed_by ON audit_logs (changed_by);
CREATE INDEX ix_audit_logs_occurred_at_brin ON audit_logs USING BRIN (occurred_at);

CREATE TRIGGER trg_audit_logs_immutable
    BEFORE UPDATE OR DELETE ON audit_logs
    FOR EACH ROW EXECUTE FUNCTION reject_mutation();
```

**Population pattern** (generic trigger installed on every audited table —
shown for `patients` as an example; the same function is reused with
`TG_TABLE_NAME` doing the work):

```sql
CREATE OR REPLACE FUNCTION write_audit_log()
RETURNS TRIGGER AS $$
DECLARE
    v_action audit_action_enum;
    v_org_id UUID;
BEGIN
    IF TG_OP = 'INSERT' THEN
        v_action := 'insert';
        v_org_id := NEW.organization_id;
    ELSIF TG_OP = 'UPDATE' THEN
        v_action := CASE WHEN NEW.deleted_at IS NOT NULL AND OLD.deleted_at IS NULL
                          THEN 'soft_delete'
                          WHEN NEW.deleted_at IS NULL AND OLD.deleted_at IS NOT NULL
                          THEN 'restore'
                          ELSE 'update' END;
        v_org_id := NEW.organization_id;
    ELSE
        v_action := 'hard_delete';
        v_org_id := OLD.organization_id;
    END IF;

    INSERT INTO audit_logs (organization_id, table_name, record_id, action,
                             changed_by, old_values, new_values)
    VALUES (
        v_org_id, TG_TABLE_NAME,
        COALESCE(NEW.id, OLD.id),
        v_action,
        COALESCE(NEW.updated_by, NEW.created_by, OLD.updated_by),
        CASE WHEN TG_OP <> 'INSERT' THEN to_jsonb(OLD) END,
        CASE WHEN TG_OP <> 'DELETE' THEN to_jsonb(NEW) END
    );
    RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql;

-- Applied to every audited, tenant-scoped clinical table, e.g.:
-- CREATE TRIGGER trg_patients_audit
--     AFTER INSERT OR UPDATE OR DELETE ON patients
--     FOR EACH ROW EXECUTE FUNCTION write_audit_log();
```

> Tables without an `organization_id` column (e.g. global reference tables)
> need a small variant of this function, or can be excluded from
> trigger-based auditing entirely since they're not tenant PHI. See
> `08_migration_strategy.md` for which tables get the audit trigger.

---

## Module 22: Activity Logs

### `activity_logs`

**Purpose:** Records **access and actions**, not data mutation — logins,
record views, exports, prints. This is the HIPAA "access log" requirement:
a nurse merely *viewing* a patient's chart must be logged even though no
data changed, which `audit_logs` alone would never capture.

**Tenant scope:** `organization_id`

| Column | Type | Nullable | Default | Description |
|---|---|---|---|---|
| `id` | `UUID` | No | `gen_random_uuid()` | PK |
| `organization_id` | `UUID` | No | — | FK → `organizations.id` |
| `user_id` | `UUID` | Yes | — | FK → `users.id`; null for unauthenticated/system events |
| `activity_type` | `activity_type_enum` | No | — | |
| `resource_type` | `TEXT` | Yes | — | e.g. `patient`, `lab_result` |
| `resource_id` | `UUID` | Yes | — | Loose polymorphic reference, no DB-level FK |
| `session_id` | `UUID` | Yes | — | FK → `auth_sessions.id` |
| `ip_address` | `INET` | Yes | — | |
| `user_agent` | `TEXT` | Yes | — | |
| `metadata` | `JSONB` | No | `'{}'` | e.g. export format, number of records exported |
| `occurred_at` | `TIMESTAMPTZ` | No | `now()` | |
| `created_at` / `updated_at` / `deleted_at` / `created_by` / `updated_by` | standard, **immutability-enforced** | | | |

- **Primary key:** `id`
- **Foreign keys:** `organization_id → organizations.id ON DELETE RESTRICT`; `user_id → users.id ON DELETE SET NULL`; `session_id → auth_sessions.id ON DELETE SET NULL`
- **Indexes:** `ix_activity_logs_user_id_occurred_at` on `(user_id, occurred_at DESC)`; `ix_activity_logs_resource` on `(resource_type, resource_id)` — "who has viewed this patient's chart"; `ix_activity_logs_organization_id_activity_type`; BRIN on `occurred_at`
- **Enums:** `activity_type_enum`
- **Soft delete:** none — append-only, trigger-enforced immutable

```sql
CREATE TYPE activity_type_enum AS ENUM (
    'login', 'logout', 'login_failed', 'view_patient', 'view_lab_result',
    'export_data', 'print_record', 'password_change', 'permission_change',
    'ai_session_started'
);

CREATE TABLE activity_logs (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id   UUID NOT NULL REFERENCES organizations(id) ON DELETE RESTRICT,
    user_id           UUID REFERENCES users(id) ON DELETE SET NULL,
    activity_type     activity_type_enum NOT NULL,
    resource_type     TEXT,
    resource_id       UUID,
    session_id        UUID REFERENCES auth_sessions(id) ON DELETE SET NULL,
    ip_address        INET,
    user_agent        TEXT,
    metadata          JSONB NOT NULL DEFAULT '{}'::jsonb,
    occurred_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at        TIMESTAMPTZ,
    created_by        UUID,
    updated_by        UUID
);

CREATE INDEX ix_activity_logs_user_id_occurred_at ON activity_logs (user_id, occurred_at DESC);
CREATE INDEX ix_activity_logs_resource ON activity_logs (resource_type, resource_id);
CREATE INDEX ix_activity_logs_org_activity_type ON activity_logs (organization_id, activity_type);
CREATE INDEX ix_activity_logs_occurred_at_brin ON activity_logs USING BRIN (occurred_at);

CREATE TRIGGER trg_activity_logs_immutable
    BEFORE UPDATE OR DELETE ON activity_logs
    FOR EACH ROW EXECUTE FUNCTION reject_mutation();
```

> `activity_logs` is written directly by the application (there's no source
> row to trigger off — a "view" isn't a data mutation), typically via a
> lightweight async write (fire-and-forget queue) so logging latency never
> blocks the user-facing request. `audit_logs`, by contrast, is
> trigger-populated and therefore synchronous with the mutating transaction
> by construction.
