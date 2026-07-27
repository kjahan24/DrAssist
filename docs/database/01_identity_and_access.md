# Modules 1–4: Authentication, Organizations, Users, Roles & Permissions

> Presented in the brief's module order. Actual `CREATE TABLE` dependency
> order is **organizations → users → auth_* → roles/permissions** (see
> `08_migration_strategy.md`), since Postgres requires a referenced table to
> exist before the foreign key is created.

All tables in this document are tenant-scoped (`organization_id NOT NULL`)
**except** `permissions`, which is a global system catalog.

---

## Module 2: Organizations

### `organizations`

**Purpose:** The tenant root. One row per clinic/hospital customer. Every
other tenant-scoped table ultimately hangs off this table's `id`.

**Tenant scope:** Self (this *is* the tenant).

| Column | Type | Nullable | Default | Description |
|---|---|---|---|---|
| `id` | `UUID` | No | `gen_random_uuid()` | Primary key |
| `name` | `TEXT` | No | — | Display name |
| `legal_name` | `TEXT` | Yes | — | Legal entity name, for billing/contracts |
| `organization_type` | `organization_type_enum` | No | `'clinic'` | Clinic, hospital, etc. |
| `subdomain` | `TEXT` | No | — | Tenant routing key (e.g. `acme` → `acme.drassist.app`) |
| `status` | `organization_status_enum` | No | `'trial'` | Lifecycle state |
| `subscription_plan` | `TEXT` | Yes | — | Billing plan identifier (owned by billing system, referenced here) |
| `timezone` | `TEXT` | No | `'UTC'` | IANA tz name, default display zone for the org |
| `phone` | `TEXT` | Yes | — | |
| `email` | `CITEXT` | Yes | — | Org contact email |
| `address_line1` | `TEXT` | Yes | — | |
| `address_line2` | `TEXT` | Yes | — | |
| `city` | `TEXT` | Yes | — | |
| `state` | `TEXT` | Yes | — | |
| `postal_code` | `TEXT` | Yes | — | |
| `country_code` | `CHAR(2)` | Yes | — | ISO 3166-1 alpha-2 |
| `tax_id` | `TEXT` | Yes | — | |
| `logo_attachment_id` | `UUID` | Yes | — | FK → `attachments.id`, added after `attachments` exists (see note below) |
| `settings` | `JSONB` | No | `'{}'` | Extensible org-level feature flags/preferences |
| `created_at` | `TIMESTAMPTZ` | No | `now()` | |
| `updated_at` | `TIMESTAMPTZ` | No | `now()` | |
| `deleted_at` | `TIMESTAMPTZ` | Yes | — | |
| `created_by` | `UUID` | Yes | — | FK → `users.id`; null for self-signup/system-provisioned |
| `updated_by` | `UUID` | Yes | — | FK → `users.id` |

- **Primary key:** `id`
- **Foreign keys:** `logo_attachment_id → attachments.id ON DELETE SET NULL` (deferred — see circular-reference note); `created_by`/`updated_by → users.id ON DELETE SET NULL`
- **Unique constraints:** `uq_organizations_subdomain` on `subdomain` (partial, `WHERE deleted_at IS NULL`)
- **Check constraints:** `ck_organizations_country_code_format CHECK (country_code ~ '^[A-Z]{2}$')`
- **Indexes:** `ix_organizations_status`; GIN index on `settings` if queried by feature flag
- **Enums:** `organization_type_enum`, `organization_status_enum`
- **Soft delete:** standard (`deleted_at`)

> **Circular reference note:** `organizations.logo_attachment_id` references
> `attachments`, and `attachments.organization_id` references
> `organizations`. Resolve with a two-phase migration: create both tables
> without the `logo_attachment_id` column, then `ALTER TABLE organizations
> ADD COLUMN logo_attachment_id UUID REFERENCES attachments(id)` in a later
> migration. Documented fully in `08_migration_strategy.md`.

```sql
CREATE TYPE organization_type_enum AS ENUM (
    'clinic', 'hospital', 'diagnostic_center', 'telehealth_provider', 'other'
);

CREATE TYPE organization_status_enum AS ENUM (
    'trial', 'active', 'suspended', 'cancelled'
);

CREATE TABLE organizations (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name                TEXT NOT NULL,
    legal_name          TEXT,
    organization_type   organization_type_enum NOT NULL DEFAULT 'clinic',
    subdomain           TEXT NOT NULL,
    status              organization_status_enum NOT NULL DEFAULT 'trial',
    subscription_plan   TEXT,
    timezone            TEXT NOT NULL DEFAULT 'UTC',
    phone               TEXT,
    email               CITEXT,
    address_line1       TEXT,
    address_line2       TEXT,
    city                TEXT,
    state               TEXT,
    postal_code         TEXT,
    country_code        CHAR(2),
    tax_id              TEXT,
    logo_attachment_id  UUID, -- FK added post-creation, see note
    settings            JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at          TIMESTAMPTZ,
    created_by          UUID,
    updated_by          UUID,
    CONSTRAINT ck_organizations_country_code_format
        CHECK (country_code IS NULL OR country_code ~ '^[A-Z]{2}$')
);

CREATE UNIQUE INDEX uq_organizations_subdomain
    ON organizations (subdomain) WHERE deleted_at IS NULL;
CREATE INDEX ix_organizations_status ON organizations (status);
```

---

### `organization_locations`

**Purpose:** Physical/virtual sites belonging to an organization (a hospital
may have several branches; a telehealth-only org has one virtual location).
`visits` reference this to record where an encounter happened.

**Tenant scope:** `organization_id`

| Column | Type | Nullable | Default | Description |
|---|---|---|---|---|
| `id` | `UUID` | No | `gen_random_uuid()` | PK |
| `organization_id` | `UUID` | No | — | FK → `organizations.id` |
| `name` | `TEXT` | No | — | e.g. "Downtown Branch" |
| `location_type` | `location_type_enum` | No | `'main'` | |
| `address_line1` | `TEXT` | Yes | — | |
| `address_line2` | `TEXT` | Yes | — | |
| `city` | `TEXT` | Yes | — | |
| `state` | `TEXT` | Yes | — | |
| `postal_code` | `TEXT` | Yes | — | |
| `country_code` | `CHAR(2)` | Yes | — | |
| `phone` | `TEXT` | Yes | — | |
| `email` | `CITEXT` | Yes | — | |
| `is_active` | `BOOLEAN` | No | `true` | |
| `created_at` / `updated_at` / `deleted_at` / `created_by` / `updated_by` | standard | | | |

- **Primary key:** `id`
- **Foreign keys:** `organization_id → organizations.id ON DELETE RESTRICT`; `created_by`/`updated_by → users.id ON DELETE SET NULL`
- **Unique constraints:** `uq_organization_locations_org_name` on `(organization_id, name)` (partial, `WHERE deleted_at IS NULL`)
- **Indexes:** `ix_organization_locations_organization_id`
- **Enums:** `location_type_enum`
- **Soft delete:** standard

```sql
CREATE TYPE location_type_enum AS ENUM ('main', 'branch', 'satellite', 'telehealth');

CREATE TABLE organization_locations (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE RESTRICT,
    name            TEXT NOT NULL,
    location_type   location_type_enum NOT NULL DEFAULT 'main',
    address_line1   TEXT,
    address_line2   TEXT,
    city            TEXT,
    state           TEXT,
    postal_code     TEXT,
    country_code    CHAR(2),
    phone           TEXT,
    email           CITEXT,
    is_active       BOOLEAN NOT NULL DEFAULT true,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at      TIMESTAMPTZ,
    created_by      UUID REFERENCES users(id) ON DELETE SET NULL,
    updated_by      UUID REFERENCES users(id) ON DELETE SET NULL
);

CREATE UNIQUE INDEX uq_organization_locations_org_name
    ON organization_locations (organization_id, name) WHERE deleted_at IS NULL;
CREATE INDEX ix_organization_locations_organization_id
    ON organization_locations (organization_id);
```

---

## Module 3: Users

### `users`

**Purpose:** The single authentication identity within an organization.
`doctors` and (optionally) `patients` are role-extensions of a `users` row.

**Tenant scope:** `organization_id`

| Column | Type | Nullable | Default | Description |
|---|---|---|---|---|
| `id` | `UUID` | No | `gen_random_uuid()` | PK |
| `organization_id` | `UUID` | No | — | FK → `organizations.id` |
| `email` | `CITEXT` | No | — | Case-insensitive login identifier |
| `password_hash` | `TEXT` | No | — | Argon2id/bcrypt hash — never plaintext |
| `first_name` | `TEXT` | No | — | |
| `last_name` | `TEXT` | No | — | |
| `phone` | `TEXT` | Yes | — | |
| `status` | `user_status_enum` | No | `'invited'` | |
| `mfa_enabled` | `BOOLEAN` | No | `false` | |
| `mfa_secret_encrypted` | `TEXT` | Yes | — | TOTP secret, encrypted at the application layer before storage |
| `email_verified_at` | `TIMESTAMPTZ` | Yes | — | |
| `last_login_at` | `TIMESTAMPTZ` | Yes | — | |
| `failed_login_attempts` | `SMALLINT` | No | `0` | Reset on success; drives lockout |
| `locked_until` | `TIMESTAMPTZ` | Yes | — | |
| `timezone` | `TEXT` | Yes | — | Overrides org default |
| `locale` | `TEXT` | No | `'en-US'` | |
| `avatar_attachment_id` | `UUID` | Yes | — | FK → `attachments.id` |
| `created_at` / `updated_at` / `deleted_at` / `created_by` / `updated_by` | standard | | | `created_by`/`updated_by` self-reference `users.id` |

- **Primary key:** `id`
- **Foreign keys:** `organization_id → organizations.id ON DELETE RESTRICT`; `avatar_attachment_id → attachments.id ON DELETE SET NULL`; `created_by`/`updated_by → users.id ON DELETE SET NULL` (self-referential)
- **Unique constraints:** `uq_users_organization_id_email` on `(organization_id, email)` (partial, `WHERE deleted_at IS NULL`) — email is unique **per tenant**, not globally, so the same person can hold accounts at two different organizations
- **Check constraints:** `ck_users_failed_login_attempts_nonneg CHECK (failed_login_attempts >= 0)`
- **Indexes:** `ix_users_organization_id`; `ix_users_status`
- **Enums:** `user_status_enum`
- **Soft delete:** standard. Deactivation should normally go through `status = 'deactivated'` rather than `deleted_at`; `deleted_at` is reserved for GDPR/right-to-erasure workflows. See `09_best_practices_and_performance.md`.

```sql
CREATE TYPE user_status_enum AS ENUM ('invited', 'active', 'suspended', 'deactivated');

CREATE TABLE users (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id         UUID NOT NULL REFERENCES organizations(id) ON DELETE RESTRICT,
    email                   CITEXT NOT NULL,
    password_hash           TEXT NOT NULL,
    first_name              TEXT NOT NULL,
    last_name               TEXT NOT NULL,
    phone                   TEXT,
    status                  user_status_enum NOT NULL DEFAULT 'invited',
    mfa_enabled             BOOLEAN NOT NULL DEFAULT false,
    mfa_secret_encrypted    TEXT,
    email_verified_at       TIMESTAMPTZ,
    last_login_at           TIMESTAMPTZ,
    failed_login_attempts   SMALLINT NOT NULL DEFAULT 0,
    locked_until            TIMESTAMPTZ,
    timezone                TEXT,
    locale                  TEXT NOT NULL DEFAULT 'en-US',
    avatar_attachment_id    UUID,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at              TIMESTAMPTZ,
    created_by              UUID REFERENCES users(id) ON DELETE SET NULL,
    updated_by              UUID REFERENCES users(id) ON DELETE SET NULL,
    CONSTRAINT ck_users_failed_login_attempts_nonneg CHECK (failed_login_attempts >= 0)
);

CREATE UNIQUE INDEX uq_users_organization_id_email
    ON users (organization_id, email) WHERE deleted_at IS NULL;
CREATE INDEX ix_users_organization_id ON users (organization_id);
CREATE INDEX ix_users_status ON users (organization_id, status);
```

> `avatar_attachment_id` FK to `attachments` is added post-creation for the
> same bootstrapping reason as `organizations.logo_attachment_id`.
> Requires the `citext` extension (`CREATE EXTENSION IF NOT EXISTS citext;`).

---

## Module 1: Authentication

Credentials (`password_hash`, MFA secret) live directly on `users` since
they're 1:1 with the identity. The tables below cover everything else:
session/token lifecycle and security auditing.

### `auth_sessions`

**Purpose:** Tracks issued refresh tokens / long-lived sessions per device,
enabling logout-everywhere, device management, and rotation.

**Tenant scope:** `organization_id` (denormalized from `user_id` for direct RLS filtering without a join)

| Column | Type | Nullable | Default | Description |
|---|---|---|---|---|
| `id` | `UUID` | No | `gen_random_uuid()` | PK |
| `organization_id` | `UUID` | No | — | FK → `organizations.id` |
| `user_id` | `UUID` | No | — | FK → `users.id` |
| `refresh_token_hash` | `TEXT` | No | — | SHA-256 hash of the refresh token; raw token is never stored |
| `device_label` | `TEXT` | Yes | — | e.g. "Chrome on macOS" |
| `ip_address` | `INET` | Yes | — | |
| `user_agent` | `TEXT` | Yes | — | |
| `issued_at` | `TIMESTAMPTZ` | No | `now()` | |
| `expires_at` | `TIMESTAMPTZ` | No | — | |
| `revoked_at` | `TIMESTAMPTZ` | Yes | — | |
| `revoked_reason` | `TEXT` | Yes | — | `logout`, `rotated`, `admin_revoked`, `password_changed` |
| `created_at` / `updated_at` / `deleted_at` / `created_by` / `updated_by` | standard | | | |

- **Primary key:** `id`
- **Foreign keys:** `organization_id → organizations.id ON DELETE RESTRICT`; `user_id → users.id ON DELETE CASCADE` (a session has no meaning without its user)
- **Unique constraints:** `uq_auth_sessions_refresh_token_hash` on `refresh_token_hash`
- **Indexes:** `ix_auth_sessions_user_id`; `ix_auth_sessions_expires_at` (for sweep jobs)
- **Soft delete:** not used for lifecycle — use `revoked_at` to end a session; `deleted_at` retained only for schema consistency / eventual archival purge

```sql
CREATE TABLE auth_sessions (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id     UUID NOT NULL REFERENCES organizations(id) ON DELETE RESTRICT,
    user_id             UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    refresh_token_hash  TEXT NOT NULL,
    device_label        TEXT,
    ip_address          INET,
    user_agent          TEXT,
    issued_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at          TIMESTAMPTZ NOT NULL,
    revoked_at          TIMESTAMPTZ,
    revoked_reason      TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at          TIMESTAMPTZ,
    created_by          UUID REFERENCES users(id) ON DELETE SET NULL,
    updated_by          UUID REFERENCES users(id) ON DELETE SET NULL
);

CREATE UNIQUE INDEX uq_auth_sessions_refresh_token_hash ON auth_sessions (refresh_token_hash);
CREATE INDEX ix_auth_sessions_user_id ON auth_sessions (user_id);
CREATE INDEX ix_auth_sessions_expires_at ON auth_sessions (expires_at);
```

---

### `auth_password_reset_tokens`

**Purpose:** One-time tokens for the "forgot password" flow.

**Tenant scope:** `organization_id`

| Column | Type | Nullable | Default | Description |
|---|---|---|---|---|
| `id` | `UUID` | No | `gen_random_uuid()` | PK |
| `organization_id` | `UUID` | No | — | FK → `organizations.id` |
| `user_id` | `UUID` | No | — | FK → `users.id` |
| `token_hash` | `TEXT` | No | — | Hashed token |
| `requested_ip` | `INET` | Yes | — | |
| `expires_at` | `TIMESTAMPTZ` | No | — | |
| `used_at` | `TIMESTAMPTZ` | Yes | — | Null until consumed |
| `created_at` / `updated_at` / `deleted_at` / `created_by` / `updated_by` | standard | | | |

- **Primary key:** `id`
- **Foreign keys:** `organization_id → organizations.id ON DELETE RESTRICT`; `user_id → users.id ON DELETE CASCADE`
- **Unique constraints:** `uq_auth_password_reset_tokens_token_hash` on `token_hash`
- **Indexes:** `ix_auth_password_reset_tokens_user_id`; `ix_auth_password_reset_tokens_expires_at`

```sql
CREATE TABLE auth_password_reset_tokens (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE RESTRICT,
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash      TEXT NOT NULL,
    requested_ip    INET,
    expires_at      TIMESTAMPTZ NOT NULL,
    used_at         TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at      TIMESTAMPTZ,
    created_by      UUID REFERENCES users(id) ON DELETE SET NULL,
    updated_by      UUID REFERENCES users(id) ON DELETE SET NULL
);

CREATE UNIQUE INDEX uq_auth_password_reset_tokens_token_hash
    ON auth_password_reset_tokens (token_hash);
CREATE INDEX ix_auth_password_reset_tokens_user_id ON auth_password_reset_tokens (user_id);
CREATE INDEX ix_auth_password_reset_tokens_expires_at ON auth_password_reset_tokens (expires_at);
```

---

### `auth_email_verification_tokens`

**Purpose:** One-time tokens for verifying a user's email address.

**Tenant scope:** `organization_id`

Same shape as `auth_password_reset_tokens` with `verified_at` instead of `used_at`.

| Column | Type | Nullable | Default | Description |
|---|---|---|---|---|
| `id` | `UUID` | No | `gen_random_uuid()` | PK |
| `organization_id` | `UUID` | No | — | FK → `organizations.id` |
| `user_id` | `UUID` | No | — | FK → `users.id` |
| `token_hash` | `TEXT` | No | — | |
| `expires_at` | `TIMESTAMPTZ` | No | — | |
| `verified_at` | `TIMESTAMPTZ` | Yes | — | |
| `created_at` / `updated_at` / `deleted_at` / `created_by` / `updated_by` | standard | | | |

- **Primary key:** `id`
- **Foreign keys:** `organization_id → organizations.id ON DELETE RESTRICT`; `user_id → users.id ON DELETE CASCADE`
- **Unique constraints:** `uq_auth_email_verification_tokens_token_hash` on `token_hash`
- **Indexes:** `ix_auth_email_verification_tokens_user_id`

```sql
CREATE TABLE auth_email_verification_tokens (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE RESTRICT,
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash      TEXT NOT NULL,
    expires_at      TIMESTAMPTZ NOT NULL,
    verified_at     TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at      TIMESTAMPTZ,
    created_by      UUID REFERENCES users(id) ON DELETE SET NULL,
    updated_by      UUID REFERENCES users(id) ON DELETE SET NULL
);

CREATE UNIQUE INDEX uq_auth_email_verification_tokens_token_hash
    ON auth_email_verification_tokens (token_hash);
CREATE INDEX ix_auth_email_verification_tokens_user_id
    ON auth_email_verification_tokens (user_id);
```

---

### `auth_login_attempts`

**Purpose:** Append-only security log of every login attempt (success and
failure), for brute-force detection, lockout policy, and security audits.

**Tenant scope:** `organization_id`, **nullable** — an attempt against an
unknown/mistyped tenant subdomain or an email that matches no user still
needs to be recorded for abuse analysis.

| Column | Type | Nullable | Default | Description |
|---|---|---|---|---|
| `id` | `UUID` | No | `gen_random_uuid()` | PK |
| `organization_id` | `UUID` | Yes | — | FK → `organizations.id`; null if tenant unresolved |
| `user_id` | `UUID` | Yes | — | FK → `users.id`; null if email matched no account |
| `attempted_email` | `CITEXT` | No | — | Raw attempted identifier, kept even on no-match |
| `success` | `BOOLEAN` | No | — | |
| `failure_reason` | `TEXT` | Yes | — | `bad_password`, `account_locked`, `unknown_email`, `mfa_failed` |
| `ip_address` | `INET` | Yes | — | |
| `user_agent` | `TEXT` | Yes | — | |
| `attempted_at` | `TIMESTAMPTZ` | No | `now()` | |
| `created_at` / `updated_at` / `deleted_at` / `created_by` / `updated_by` | standard, **immutability-enforced** | | | see below |

- **Primary key:** `id`
- **Foreign keys:** `organization_id → organizations.id ON DELETE SET NULL`; `user_id → users.id ON DELETE SET NULL`
- **Indexes:** `ix_auth_login_attempts_user_id_attempted_at`; `ix_auth_login_attempts_ip_address_attempted_at` (brute-force detection by IP); BRIN index on `attempted_at` for cheap time-range scans at high volume
- **Soft delete:** none — append-only, immutable (trigger-enforced, see `06_audit_and_activity.md` for the shared `reject_mutation()` trigger pattern applied here too)

```sql
CREATE TABLE auth_login_attempts (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id   UUID REFERENCES organizations(id) ON DELETE SET NULL,
    user_id           UUID REFERENCES users(id) ON DELETE SET NULL,
    attempted_email   CITEXT NOT NULL,
    success           BOOLEAN NOT NULL,
    failure_reason    TEXT,
    ip_address        INET,
    user_agent        TEXT,
    attempted_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at        TIMESTAMPTZ,
    created_by        UUID,
    updated_by        UUID
);

CREATE INDEX ix_auth_login_attempts_user_id_attempted_at
    ON auth_login_attempts (user_id, attempted_at DESC);
CREATE INDEX ix_auth_login_attempts_ip_attempted_at
    ON auth_login_attempts (ip_address, attempted_at DESC);
CREATE INDEX ix_auth_login_attempts_attempted_at_brin
    ON auth_login_attempts USING BRIN (attempted_at);

CREATE TRIGGER trg_auth_login_attempts_immutable
    BEFORE UPDATE OR DELETE ON auth_login_attempts
    FOR EACH ROW EXECUTE FUNCTION reject_mutation();
```

---

## Module 4: Roles & Permissions (RBAC)

### `permissions`

**Purpose:** Global, code-owned catalog of fine-grained capability strings
(e.g. `patients.read`, `visits.write`, `lab_results.delete`). Seeded by
migration; tenants do not create permissions, only assign them to roles.

**Tenant scope:** Global (no `organization_id`)

| Column | Type | Nullable | Default | Description |
|---|---|---|---|---|
| `id` | `UUID` | No | `gen_random_uuid()` | PK |
| `code` | `TEXT` | No | — | Stable machine key, e.g. `patients.read` |
| `module` | `TEXT` | No | — | Grouping for admin UI, e.g. `patients` |
| `description` | `TEXT` | No | — | |
| `created_at` / `updated_at` / `deleted_at` / `created_by` / `updated_by` | standard | | | `created_by`/`updated_by` typically null (migration-seeded) |

- **Primary key:** `id`
- **Unique constraints:** `uq_permissions_code` on `code`
- **Indexes:** `ix_permissions_module`
- **Soft delete:** standard, though in practice permissions are deprecated (unassigned from roles) rather than deleted

```sql
CREATE TABLE permissions (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code          TEXT NOT NULL,
    module        TEXT NOT NULL,
    description   TEXT NOT NULL,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at    TIMESTAMPTZ,
    created_by    UUID REFERENCES users(id) ON DELETE SET NULL,
    updated_by    UUID REFERENCES users(id) ON DELETE SET NULL
);

CREATE UNIQUE INDEX uq_permissions_code ON permissions (code) WHERE deleted_at IS NULL;
CREATE INDEX ix_permissions_module ON permissions (module);
```

---

### `roles`

**Purpose:** A named bundle of permissions. Supports both product-shipped
system roles (`organization_id IS NULL`) and tenant-authored custom roles.

**Tenant scope:** Nullable `organization_id` — `NULL` = system template
available to every tenant; non-null = custom role owned by that tenant.

| Column | Type | Nullable | Default | Description |
|---|---|---|---|---|
| `id` | `UUID` | No | `gen_random_uuid()` | PK |
| `organization_id` | `UUID` | Yes | — | FK → `organizations.id`; null = system role |
| `name` | `TEXT` | No | — | e.g. "Doctor", "Front Desk", "Billing Admin" |
| `description` | `TEXT` | Yes | — | |
| `is_system_role` | `BOOLEAN` | No | `false` | True for product-shipped templates |
| `created_at` / `updated_at` / `deleted_at` / `created_by` / `updated_by` | standard | | | |

- **Primary key:** `id`
- **Foreign keys:** `organization_id → organizations.id ON DELETE CASCADE` (deleting a tenant's custom roles is acceptable — RESTRICT applies to clinical data, not access config); `created_by`/`updated_by → users.id ON DELETE SET NULL`
- **Unique constraints:** `uq_roles_system_name` on `name` (partial, `WHERE organization_id IS NULL AND deleted_at IS NULL`); `uq_roles_org_name` on `(organization_id, name)` (partial, `WHERE organization_id IS NOT NULL AND deleted_at IS NULL`)
- **Indexes:** `ix_roles_organization_id`
- **Soft delete:** standard

```sql
CREATE TABLE roles (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    name            TEXT NOT NULL,
    description     TEXT,
    is_system_role  BOOLEAN NOT NULL DEFAULT false,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at      TIMESTAMPTZ,
    created_by      UUID REFERENCES users(id) ON DELETE SET NULL,
    updated_by      UUID REFERENCES users(id) ON DELETE SET NULL
);

CREATE UNIQUE INDEX uq_roles_system_name ON roles (name)
    WHERE organization_id IS NULL AND deleted_at IS NULL;
CREATE UNIQUE INDEX uq_roles_org_name ON roles (organization_id, name)
    WHERE organization_id IS NOT NULL AND deleted_at IS NULL;
CREATE INDEX ix_roles_organization_id ON roles (organization_id);
```

---

### `role_permissions`

**Purpose:** Join table — which permissions a role grants.

**Tenant scope:** Inherits from `roles.organization_id` (not duplicated here since this table is only ever queried by `role_id`, not filtered independently)

| Column | Type | Nullable | Default | Description |
|---|---|---|---|---|
| `id` | `UUID` | No | `gen_random_uuid()` | PK |
| `role_id` | `UUID` | No | — | FK → `roles.id` |
| `permission_id` | `UUID` | No | — | FK → `permissions.id` |
| `created_at` / `updated_at` / `deleted_at` / `created_by` / `updated_by` | standard | | | |

- **Primary key:** `id`
- **Foreign keys:** `role_id → roles.id ON DELETE CASCADE`; `permission_id → permissions.id ON DELETE CASCADE`
- **Unique constraints:** `uq_role_permissions_role_permission` on `(role_id, permission_id)`
- **Indexes:** `ix_role_permissions_permission_id` (reverse lookup: "which roles grant this permission")

```sql
CREATE TABLE role_permissions (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    role_id        UUID NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    permission_id  UUID NOT NULL REFERENCES permissions(id) ON DELETE CASCADE,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at     TIMESTAMPTZ,
    created_by     UUID REFERENCES users(id) ON DELETE SET NULL,
    updated_by     UUID REFERENCES users(id) ON DELETE SET NULL
);

CREATE UNIQUE INDEX uq_role_permissions_role_permission
    ON role_permissions (role_id, permission_id);
CREATE INDEX ix_role_permissions_permission_id ON role_permissions (permission_id);
```

---

### `user_roles`

**Purpose:** Join table — which roles a user holds. A user's effective
permissions are the union of all permissions across all assigned roles.

**Tenant scope:** `organization_id` (denormalized from `users.organization_id` for direct RLS filtering)

| Column | Type | Nullable | Default | Description |
|---|---|---|---|---|
| `id` | `UUID` | No | `gen_random_uuid()` | PK |
| `organization_id` | `UUID` | No | — | FK → `organizations.id` |
| `user_id` | `UUID` | No | — | FK → `users.id` |
| `role_id` | `UUID` | No | — | FK → `roles.id` |
| `granted_by` | `UUID` | Yes | — | FK → `users.id`, who assigned this role |
| `granted_at` | `TIMESTAMPTZ` | No | `now()` | |
| `created_at` / `updated_at` / `deleted_at` / `created_by` / `updated_by` | standard | | | |

- **Primary key:** `id`
- **Foreign keys:** `organization_id → organizations.id ON DELETE RESTRICT`; `user_id → users.id ON DELETE CASCADE`; `role_id → roles.id ON DELETE CASCADE`; `granted_by → users.id ON DELETE SET NULL`
- **Unique constraints:** `uq_user_roles_user_role` on `(user_id, role_id)`
- **Indexes:** `ix_user_roles_organization_id`; `ix_user_roles_role_id`

```sql
CREATE TABLE user_roles (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE RESTRICT,
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role_id         UUID NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    granted_by      UUID REFERENCES users(id) ON DELETE SET NULL,
    granted_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at      TIMESTAMPTZ,
    created_by      UUID REFERENCES users(id) ON DELETE SET NULL,
    updated_by      UUID REFERENCES users(id) ON DELETE SET NULL
);

CREATE UNIQUE INDEX uq_user_roles_user_role ON user_roles (user_id, role_id);
CREATE INDEX ix_user_roles_organization_id ON user_roles (organization_id);
CREATE INDEX ix_user_roles_role_id ON user_roles (role_id);
```
