# Modules 18–20: Lab Reports, Lab Results, Attachments

All tables tenant-scoped (`organization_id NOT NULL`) except the
`lab_test_catalog` reference table.

---

## Module 18: Lab Reports

### `lab_reports`

**Purpose:** Header-level record of an ordered/received lab report — one row
per report from a lab, containing one or more individual results.

**Tenant scope:** `organization_id`

| Column | Type | Nullable | Default | Description |
|---|---|---|---|---|
| `id` | `UUID` | No | `gen_random_uuid()` | PK |
| `organization_id` | `UUID` | No | — | FK → `organizations.id` |
| `patient_id` | `UUID` | No | — | FK → `patients.id` |
| `visit_id` | `UUID` | Yes | — | FK → `visits.id`; nullable — labs can be ordered outside a visit context |
| `ordering_doctor_id` | `UUID` | Yes | — | FK → `doctors.id` |
| `performing_lab_name` | `TEXT` | Yes | — | External lab name |
| `lab_external_id` | `TEXT` | Yes | — | Reference ID in the external lab's system |
| `report_number` | `TEXT` | Yes | — | Lab-assigned report number |
| `status` | `lab_report_status_enum` | No | `'ordered'` | |
| `ordered_at` | `TIMESTAMPTZ` | Yes | — | |
| `collected_at` | `TIMESTAMPTZ` | Yes | — | Specimen collection time |
| `resulted_at` | `TIMESTAMPTZ` | Yes | — | |
| `notes` | `TEXT` | Yes | — | |
| `created_at` / `updated_at` / `deleted_at` / `created_by` / `updated_by` | standard | | | |

- **Primary key:** `id`
- **Foreign keys:** `organization_id → organizations.id ON DELETE RESTRICT`; `patient_id → patients.id ON DELETE RESTRICT`; `visit_id → visits.id ON DELETE SET NULL`; `ordering_doctor_id → doctors.id ON DELETE SET NULL`
- **Check constraints:** `ck_lab_reports_date_order CHECK (resulted_at IS NULL OR collected_at IS NULL OR resulted_at >= collected_at)`
- **Indexes:** `ix_lab_reports_patient_id`; `ix_lab_reports_visit_id`; `ix_lab_reports_status`
- **Enums:** `lab_report_status_enum`
- **Soft delete:** standard

```sql
CREATE TYPE lab_report_status_enum AS ENUM ('ordered', 'collected', 'in_progress', 'resulted', 'cancelled');

CREATE TABLE lab_reports (
    id                     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id        UUID NOT NULL REFERENCES organizations(id) ON DELETE RESTRICT,
    patient_id             UUID NOT NULL REFERENCES patients(id) ON DELETE RESTRICT,
    visit_id               UUID REFERENCES visits(id) ON DELETE SET NULL,
    ordering_doctor_id     UUID REFERENCES doctors(id) ON DELETE SET NULL,
    performing_lab_name    TEXT,
    lab_external_id        TEXT,
    report_number          TEXT,
    status                 lab_report_status_enum NOT NULL DEFAULT 'ordered',
    ordered_at             TIMESTAMPTZ,
    collected_at           TIMESTAMPTZ,
    resulted_at            TIMESTAMPTZ,
    notes                  TEXT,
    created_at             TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at             TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at             TIMESTAMPTZ,
    created_by             UUID REFERENCES users(id) ON DELETE SET NULL,
    updated_by             UUID REFERENCES users(id) ON DELETE SET NULL,
    CONSTRAINT ck_lab_reports_date_order
        CHECK (resulted_at IS NULL OR collected_at IS NULL OR resulted_at >= collected_at)
);

CREATE INDEX ix_lab_reports_patient_id ON lab_reports (patient_id);
CREATE INDEX ix_lab_reports_visit_id ON lab_reports (visit_id);
CREATE INDEX ix_lab_reports_status ON lab_reports (organization_id, status);
```

---

## Module 19: Lab Results

### `lab_test_catalog` (reference table)

**Purpose:** Global LOINC-coded catalog of lab test types, supporting
structured (rather than free-text) result recording and future AI
interpretation features.

**Tenant scope:** Global

| Column | Type | Nullable | Default | Description |
|---|---|---|---|---|
| `id` | `UUID` | No | `gen_random_uuid()` | PK |
| `loinc_code` | `TEXT` | No | — | e.g. `2345-7` |
| `name` | `TEXT` | No | — | e.g. "Glucose [Mass/volume] in Serum or Plasma" |
| `default_unit` | `TEXT` | Yes | — | e.g. `mg/dL` |
| `category` | `TEXT` | Yes | — | e.g. "Chemistry", "Hematology" |
| `created_at` / `updated_at` / `deleted_at` / `created_by` / `updated_by` | standard | | | |

- **Primary key:** `id`
- **Unique constraints:** `uq_lab_test_catalog_loinc_code` on `loinc_code`

```sql
CREATE TABLE lab_test_catalog (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    loinc_code      TEXT NOT NULL,
    name            TEXT NOT NULL,
    default_unit    TEXT,
    category        TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at      TIMESTAMPTZ,
    created_by      UUID REFERENCES users(id) ON DELETE SET NULL,
    updated_by      UUID REFERENCES users(id) ON DELETE SET NULL
);

CREATE UNIQUE INDEX uq_lab_test_catalog_loinc_code
    ON lab_test_catalog (loinc_code) WHERE deleted_at IS NULL;
```

### `lab_results`

**Purpose:** Individual test result line items within a lab report.

**Tenant scope:** `organization_id`

| Column | Type | Nullable | Default | Description |
|---|---|---|---|---|
| `id` | `UUID` | No | `gen_random_uuid()` | PK |
| `organization_id` | `UUID` | No | — | FK → `organizations.id` |
| `lab_report_id` | `UUID` | No | — | FK → `lab_reports.id` |
| `test_catalog_id` | `UUID` | Yes | — | FK → `lab_test_catalog.id` |
| `test_name` | `TEXT` | No | — | Snapshot at result time (survives catalog edits) |
| `result_value` | `TEXT` | No | — | Kept as text — labs report both numeric and qualitative ("Positive") values |
| `result_value_numeric` | `NUMERIC(12,4)` | Yes | — | Populated when the value is numeric, for analytics/trend queries |
| `unit` | `TEXT` | Yes | — | |
| `reference_range_low` | `NUMERIC(12,4)` | Yes | — | |
| `reference_range_high` | `NUMERIC(12,4)` | Yes | — | |
| `reference_range_text` | `TEXT` | Yes | — | For non-numeric ranges |
| `abnormal_flag` | `lab_abnormal_flag_enum` | No | `'normal'` | |
| `status` | `lab_result_status_enum` | No | `'preliminary'` | |
| `resulted_at` | `TIMESTAMPTZ` | Yes | — | |
| `embedding_id` | `UUID` | Yes | — | Qdrant point ID for AI interpretation retrieval |
| `created_at` / `updated_at` / `deleted_at` / `created_by` / `updated_by` | standard | | | |

- **Primary key:** `id`
- **Foreign keys:** `organization_id → organizations.id ON DELETE RESTRICT`; `lab_report_id → lab_reports.id ON DELETE CASCADE`; `test_catalog_id → lab_test_catalog.id ON DELETE SET NULL`
- **Check constraints:** `ck_lab_results_reference_range_order CHECK (reference_range_high IS NULL OR reference_range_low IS NULL OR reference_range_high >= reference_range_low)`
- **Indexes:** `ix_lab_results_lab_report_id`; `ix_lab_results_test_catalog_id`; `ix_lab_results_abnormal_flag` on `(organization_id, abnormal_flag) WHERE abnormal_flag <> 'normal'` (partial index — critical-result dashboards only care about abnormal results)
- **Enums:** `lab_abnormal_flag_enum`, `lab_result_status_enum`
- **Soft delete:** standard; corrections should use `status = 'corrected'` with a new row rather than overwriting the original (preserve the amended-result audit trail)

```sql
CREATE TYPE lab_abnormal_flag_enum AS ENUM (
    'normal', 'low', 'high', 'critical_low', 'critical_high', 'abnormal'
);
CREATE TYPE lab_result_status_enum AS ENUM ('preliminary', 'final', 'corrected', 'cancelled');

CREATE TABLE lab_results (
    id                       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id          UUID NOT NULL REFERENCES organizations(id) ON DELETE RESTRICT,
    lab_report_id             UUID NOT NULL REFERENCES lab_reports(id) ON DELETE CASCADE,
    test_catalog_id            UUID REFERENCES lab_test_catalog(id) ON DELETE SET NULL,
    test_name                  TEXT NOT NULL,
    result_value                TEXT NOT NULL,
    result_value_numeric         NUMERIC(12,4),
    unit                         TEXT,
    reference_range_low          NUMERIC(12,4),
    reference_range_high         NUMERIC(12,4),
    reference_range_text         TEXT,
    abnormal_flag                 lab_abnormal_flag_enum NOT NULL DEFAULT 'normal',
    status                        lab_result_status_enum NOT NULL DEFAULT 'preliminary',
    resulted_at                   TIMESTAMPTZ,
    embedding_id                  UUID,
    created_at                    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at                    TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at                    TIMESTAMPTZ,
    created_by                    UUID REFERENCES users(id) ON DELETE SET NULL,
    updated_by                    UUID REFERENCES users(id) ON DELETE SET NULL,
    CONSTRAINT ck_lab_results_reference_range_order CHECK (
        reference_range_high IS NULL OR reference_range_low IS NULL
        OR reference_range_high >= reference_range_low
    )
);

CREATE INDEX ix_lab_results_lab_report_id ON lab_results (lab_report_id);
CREATE INDEX ix_lab_results_test_catalog_id ON lab_results (test_catalog_id);
CREATE INDEX ix_lab_results_abnormal_flag
    ON lab_results (organization_id, abnormal_flag) WHERE abnormal_flag <> 'normal';
```

---

## Module 20: Attachments

### `attachments`

**Purpose:** A single polymorphic file table shared by every owning entity
(patients, visits, lab reports, clinical notes, SOAP notes, transcripts,
organizations), backed by MinIO object storage.

**Tenant scope:** `organization_id`

| Column | Type | Nullable | Default | Description |
|---|---|---|---|---|
| `id` | `UUID` | No | `gen_random_uuid()` | PK |
| `organization_id` | `UUID` | No | — | FK → `organizations.id` |
| `owner_type` | `attachment_owner_type_enum` | No | — | |
| `owner_id` | `UUID` | No | — | Loose polymorphic reference, **not** a DB-level FK — see note |
| `storage_bucket` | `TEXT` | No | — | MinIO bucket name |
| `storage_key` | `TEXT` | No | — | MinIO object key |
| `file_name` | `TEXT` | No | — | Original filename |
| `mime_type` | `TEXT` | No | — | |
| `file_size_bytes` | `BIGINT` | No | — | |
| `checksum_sha256` | `TEXT` | Yes | — | Integrity verification |
| `is_phi` | `BOOLEAN` | No | `true` | Flags Protected Health Information for compliance handling (retention, encryption-at-rest policy) |
| `virus_scan_status` | `virus_scan_status_enum` | No | `'pending'` | |
| `uploaded_by` | `UUID` | Yes | — | FK → `users.id` |
| `metadata` | `JSONB` | No | `'{}'` | |
| `created_at` / `updated_at` / `deleted_at` / `created_by` / `updated_by` | standard | | | |

- **Primary key:** `id`
- **Foreign keys:** `organization_id → organizations.id ON DELETE RESTRICT`; `uploaded_by → users.id ON DELETE SET NULL`. **No FK on `owner_id`** — same polymorphic trade-off as `patient_timeline_events.source_id`.
- **Unique constraints:** `uq_attachments_bucket_key` on `(storage_bucket, storage_key)`
- **Check constraints:** `ck_attachments_file_size_positive CHECK (file_size_bytes > 0)`; `ck_attachments_owner_type_known` enforced via the enum type itself
- **Indexes:** `ix_attachments_owner` on `(owner_type, owner_id)` — primary access pattern ("all attachments for this patient/visit/note")
- **Enums:** `attachment_owner_type_enum`, `virus_scan_status_enum`
- **Soft delete:** standard — note that soft-deleting the row does **not** delete the underlying MinIO object automatically; object lifecycle is handled by a scheduled reconciliation job (see `09_best_practices_and_performance.md`)

```sql
CREATE TYPE attachment_owner_type_enum AS ENUM (
    'patient', 'visit', 'clinical_note', 'soap_note', 'lab_report',
    'conversation_transcript', 'organization'
);
CREATE TYPE virus_scan_status_enum AS ENUM ('pending', 'clean', 'infected', 'scan_failed');

CREATE TABLE attachments (
    id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id      UUID NOT NULL REFERENCES organizations(id) ON DELETE RESTRICT,
    owner_type           attachment_owner_type_enum NOT NULL,
    owner_id             UUID NOT NULL,
    storage_bucket       TEXT NOT NULL,
    storage_key          TEXT NOT NULL,
    file_name            TEXT NOT NULL,
    mime_type            TEXT NOT NULL,
    file_size_bytes      BIGINT NOT NULL,
    checksum_sha256      TEXT,
    is_phi               BOOLEAN NOT NULL DEFAULT true,
    virus_scan_status    virus_scan_status_enum NOT NULL DEFAULT 'pending',
    uploaded_by          UUID REFERENCES users(id) ON DELETE SET NULL,
    metadata             JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at           TIMESTAMPTZ,
    created_by           UUID REFERENCES users(id) ON DELETE SET NULL,
    updated_by           UUID REFERENCES users(id) ON DELETE SET NULL,
    CONSTRAINT ck_attachments_file_size_positive CHECK (file_size_bytes > 0)
);

CREATE UNIQUE INDEX uq_attachments_bucket_key ON attachments (storage_bucket, storage_key);
CREATE INDEX ix_attachments_owner ON attachments (owner_type, owner_id);
```

> **Why `organizations.logo_attachment_id`, `users.avatar_attachment_id`, and
> `doctors.signature_attachment_id` can safely reference `attachments`
> directly** (as real FKs, unlike `owner_id`): those are single, known,
> 1:1-ish relationships from a *fixed* table, not a polymorphic fan-out — a
> real FK is both possible and preferable there.
