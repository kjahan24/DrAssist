# Modules 11–14: Visits, Vital Signs, Clinical Notes, SOAP Notes

All tables in this document are tenant-scoped (`organization_id NOT NULL`).
`visits` is the central encounter entity everything here hangs off.

---

## Module 11: Visits

### `visits`

**Purpose:** The clinical encounter — binds a patient, a doctor, a location,
and a time window. The anchor for vitals, notes, AI sessions, and
(optionally) lab orders.

**Tenant scope:** `organization_id`

| Column | Type | Nullable | Default | Description |
|---|---|---|---|---|
| `id` | `UUID` | No | `gen_random_uuid()` | PK |
| `organization_id` | `UUID` | No | — | FK → `organizations.id` |
| `location_id` | `UUID` | Yes | — | FK → `organization_locations.id`; null for pure telehealth |
| `patient_id` | `UUID` | No | — | FK → `patients.id` |
| `doctor_id` | `UUID` | No | — | FK → `doctors.id` |
| `visit_type` | `visit_type_enum` | No | `'in_person'` | |
| `status` | `visit_status_enum` | No | `'scheduled'` | |
| `scheduled_start_at` | `TIMESTAMPTZ` | No | — | |
| `scheduled_end_at` | `TIMESTAMPTZ` | Yes | — | |
| `actual_start_at` | `TIMESTAMPTZ` | Yes | — | Check-in / encounter start |
| `actual_end_at` | `TIMESTAMPTZ` | Yes | — | |
| `chief_complaint` | `TEXT` | Yes | — | |
| `visit_reason` | `TEXT` | Yes | — | |
| `cancellation_reason` | `TEXT` | Yes | — | |
| `checked_in_at` | `TIMESTAMPTZ` | Yes | — | |
| `checked_out_at` | `TIMESTAMPTZ` | Yes | — | |
| `created_at` / `updated_at` / `deleted_at` / `created_by` / `updated_by` | standard | | | |

- **Primary key:** `id`
- **Foreign keys:** `organization_id → organizations.id ON DELETE RESTRICT`; `location_id → organization_locations.id ON DELETE SET NULL`; `patient_id → patients.id ON DELETE RESTRICT`; `doctor_id → doctors.id ON DELETE RESTRICT`
- **Check constraints:** `ck_visits_scheduled_order CHECK (scheduled_end_at IS NULL OR scheduled_end_at > scheduled_start_at)`; `ck_visits_actual_order CHECK (actual_end_at IS NULL OR actual_start_at IS NULL OR actual_end_at >= actual_start_at)`
- **Indexes:** `ix_visits_organization_id`; `ix_visits_patient_id_scheduled_start_at` on `(patient_id, scheduled_start_at DESC)`; `ix_visits_doctor_id_scheduled_start_at` on `(doctor_id, scheduled_start_at)` (schedule/calendar queries); `ix_visits_status`
- **Enums:** `visit_type_enum`, `visit_status_enum`
- **Soft delete:** standard — cancellation should use `status = 'cancelled'`; `deleted_at` reserved for erroneous records

```sql
CREATE TYPE visit_type_enum AS ENUM ('in_person', 'telehealth', 'phone', 'home_visit');
CREATE TYPE visit_status_enum AS ENUM (
    'scheduled', 'checked_in', 'in_progress', 'completed', 'cancelled', 'no_show'
);

CREATE TABLE visits (
    id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id       UUID NOT NULL REFERENCES organizations(id) ON DELETE RESTRICT,
    location_id           UUID REFERENCES organization_locations(id) ON DELETE SET NULL,
    patient_id            UUID NOT NULL REFERENCES patients(id) ON DELETE RESTRICT,
    doctor_id             UUID NOT NULL REFERENCES doctors(id) ON DELETE RESTRICT,
    visit_type            visit_type_enum NOT NULL DEFAULT 'in_person',
    status                visit_status_enum NOT NULL DEFAULT 'scheduled',
    scheduled_start_at    TIMESTAMPTZ NOT NULL,
    scheduled_end_at      TIMESTAMPTZ,
    actual_start_at       TIMESTAMPTZ,
    actual_end_at         TIMESTAMPTZ,
    chief_complaint       TEXT,
    visit_reason          TEXT,
    cancellation_reason   TEXT,
    checked_in_at         TIMESTAMPTZ,
    checked_out_at        TIMESTAMPTZ,
    created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at            TIMESTAMPTZ,
    created_by            UUID REFERENCES users(id) ON DELETE SET NULL,
    updated_by            UUID REFERENCES users(id) ON DELETE SET NULL,
    CONSTRAINT ck_visits_scheduled_order
        CHECK (scheduled_end_at IS NULL OR scheduled_end_at > scheduled_start_at),
    CONSTRAINT ck_visits_actual_order
        CHECK (actual_end_at IS NULL OR actual_start_at IS NULL OR actual_end_at >= actual_start_at)
);

CREATE INDEX ix_visits_organization_id ON visits (organization_id);
CREATE INDEX ix_visits_patient_id_scheduled_start_at ON visits (patient_id, scheduled_start_at DESC);
CREATE INDEX ix_visits_doctor_id_scheduled_start_at ON visits (doctor_id, scheduled_start_at);
CREATE INDEX ix_visits_status ON visits (organization_id, status);
```

---

## Module 12: Vital Signs

### `vital_signs`

**Purpose:** One row per vitals-taking event during a visit. Modeled as a
fixed-column ("wide") table rather than key/value, because the vital sign
set is small, standardized, and every row needs the same fields — this
keeps queries and unit conversion simple and avoids EAV overhead.

**Tenant scope:** `organization_id`

| Column | Type | Nullable | Default | Description |
|---|---|---|---|---|
| `id` | `UUID` | No | `gen_random_uuid()` | PK |
| `organization_id` | `UUID` | No | — | FK → `organizations.id` |
| `visit_id` | `UUID` | No | — | FK → `visits.id` |
| `patient_id` | `UUID` | No | — | FK → `patients.id`; denormalized from `visits.patient_id` for direct patient-level trend queries without a join |
| `recorded_by` | `UUID` | Yes | — | FK → `users.id` |
| `recorded_at` | `TIMESTAMPTZ` | No | `now()` | |
| `height_cm` | `NUMERIC(5,1)` | Yes | — | |
| `weight_kg` | `NUMERIC(5,1)` | Yes | — | |
| `bmi` | `NUMERIC(4,1)` | Yes | *generated* | `GENERATED ALWAYS AS` from height/weight |
| `temperature_celsius` | `NUMERIC(3,1)` | Yes | — | |
| `heart_rate_bpm` | `SMALLINT` | Yes | — | |
| `respiratory_rate_bpm` | `SMALLINT` | Yes | — | |
| `blood_pressure_systolic` | `SMALLINT` | Yes | — | |
| `blood_pressure_diastolic` | `SMALLINT` | Yes | — | |
| `spo2_percent` | `SMALLINT` | Yes | — | |
| `pain_score` | `SMALLINT` | Yes | — | 0–10 scale |
| `notes` | `TEXT` | Yes | — | |
| `created_at` / `updated_at` / `deleted_at` / `created_by` / `updated_by` | standard | | | |

- **Primary key:** `id`
- **Foreign keys:** `organization_id → organizations.id ON DELETE RESTRICT`; `visit_id → visits.id ON DELETE CASCADE`; `patient_id → patients.id ON DELETE RESTRICT`; `recorded_by → users.id ON DELETE SET NULL`
- **Check constraints:** `ck_vital_signs_pain_score_range CHECK (pain_score BETWEEN 0 AND 10)`; `ck_vital_signs_spo2_range CHECK (spo2_percent BETWEEN 0 AND 100)`; `ck_vital_signs_heart_rate_positive CHECK (heart_rate_bpm IS NULL OR heart_rate_bpm > 0)`
- **Indexes:** `ix_vital_signs_visit_id`; `ix_vital_signs_patient_id_recorded_at` on `(patient_id, recorded_at DESC)` for trend charts; BRIN on `recorded_at` for large-scale time-range scans
- **Soft delete:** standard

```sql
CREATE TABLE vital_signs (
    id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id             UUID NOT NULL REFERENCES organizations(id) ON DELETE RESTRICT,
    visit_id                    UUID NOT NULL REFERENCES visits(id) ON DELETE CASCADE,
    patient_id                  UUID NOT NULL REFERENCES patients(id) ON DELETE RESTRICT,
    recorded_by                 UUID REFERENCES users(id) ON DELETE SET NULL,
    recorded_at                 TIMESTAMPTZ NOT NULL DEFAULT now(),
    height_cm                   NUMERIC(5,1),
    weight_kg                   NUMERIC(5,1),
    bmi                         NUMERIC(4,1) GENERATED ALWAYS AS (
                                     CASE WHEN height_cm > 0 AND weight_kg IS NOT NULL
                                          THEN round(weight_kg / ((height_cm / 100.0) ^ 2), 1)
                                     END
                                 ) STORED,
    temperature_celsius         NUMERIC(3,1),
    heart_rate_bpm               SMALLINT,
    respiratory_rate_bpm         SMALLINT,
    blood_pressure_systolic      SMALLINT,
    blood_pressure_diastolic     SMALLINT,
    spo2_percent                 SMALLINT,
    pain_score                   SMALLINT,
    notes                        TEXT,
    created_at                   TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at                   TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at                   TIMESTAMPTZ,
    created_by                   UUID REFERENCES users(id) ON DELETE SET NULL,
    updated_by                   UUID REFERENCES users(id) ON DELETE SET NULL,
    CONSTRAINT ck_vital_signs_pain_score_range CHECK (pain_score IS NULL OR pain_score BETWEEN 0 AND 10),
    CONSTRAINT ck_vital_signs_spo2_range CHECK (spo2_percent IS NULL OR spo2_percent BETWEEN 0 AND 100),
    CONSTRAINT ck_vital_signs_heart_rate_positive CHECK (heart_rate_bpm IS NULL OR heart_rate_bpm > 0)
);

CREATE INDEX ix_vital_signs_visit_id ON vital_signs (visit_id);
CREATE INDEX ix_vital_signs_patient_id_recorded_at ON vital_signs (patient_id, recorded_at DESC);
CREATE INDEX ix_vital_signs_recorded_at_brin ON vital_signs USING BRIN (recorded_at);
```

---

## Module 13: Clinical Notes

### `clinical_notes`

**Purpose:** Free-text clinical documentation tied to a visit — progress
notes, consultation notes, discharge summaries, nursing notes, addenda. A
visit may have several (unlike the single structured SOAP note).

**Tenant scope:** `organization_id`

| Column | Type | Nullable | Default | Description |
|---|---|---|---|---|
| `id` | `UUID` | No | `gen_random_uuid()` | PK |
| `organization_id` | `UUID` | No | — | FK → `organizations.id` |
| `visit_id` | `UUID` | No | — | FK → `visits.id` |
| `patient_id` | `UUID` | No | — | FK → `patients.id`; denormalized from `visits.patient_id` |
| `author_id` | `UUID` | No | — | FK → `users.id` |
| `note_type` | `clinical_note_type_enum` | No | `'progress'` | |
| `title` | `TEXT` | Yes | — | |
| `content` | `TEXT` | No | — | |
| `is_ai_generated` | `BOOLEAN` | No | `false` | |
| `ai_session_id` | `UUID` | Yes | — | FK → `ai_sessions.id`, set when `is_ai_generated` |
| `review_status` | `content_review_status_enum` | No | `'draft'` | |
| `reviewed_by` | `UUID` | Yes | — | FK → `users.id` |
| `reviewed_at` | `TIMESTAMPTZ` | Yes | — | |
| `finalized_at` | `TIMESTAMPTZ` | Yes | — | Once set, `content` should not change further — see note below |
| `embedding_id` | `UUID` | Yes | — | Qdrant point ID for semantic search/RAG (Postgres stores the reference only) |
| `search_vector` | `TSVECTOR` | Yes | *generated* | Full-text search over `title`/`content` |
| `created_at` / `updated_at` / `deleted_at` / `created_by` / `updated_by` | standard | | | |

- **Primary key:** `id`
- **Foreign keys:** `organization_id → organizations.id ON DELETE RESTRICT`; `visit_id → visits.id ON DELETE CASCADE`; `patient_id → patients.id ON DELETE RESTRICT`; `author_id → users.id ON DELETE RESTRICT` (a clinical note must always be attributable — restrict, don't null out authorship); `ai_session_id → ai_sessions.id ON DELETE SET NULL`; `reviewed_by → users.id ON DELETE SET NULL`
- **Check constraints:** `ck_clinical_notes_ai_session_requires_flag CHECK (ai_session_id IS NULL OR is_ai_generated)`
- **Indexes:** `ix_clinical_notes_visit_id`; `ix_clinical_notes_patient_id_created_at` on `(patient_id, created_at DESC)`; GIN on `search_vector`
- **Enums:** `clinical_note_type_enum`, `content_review_status_enum`
- **Soft delete:** standard, but see immutability note

```sql
CREATE TYPE clinical_note_type_enum AS ENUM (
    'progress', 'consultation', 'discharge_summary', 'nursing', 'referral', 'procedure', 'addendum'
);
CREATE TYPE content_review_status_enum AS ENUM (
    'draft', 'pending_review', 'reviewed', 'finalized', 'amended'
);

CREATE TABLE clinical_notes (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id   UUID NOT NULL REFERENCES organizations(id) ON DELETE RESTRICT,
    visit_id          UUID NOT NULL REFERENCES visits(id) ON DELETE CASCADE,
    patient_id        UUID NOT NULL REFERENCES patients(id) ON DELETE RESTRICT,
    author_id         UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    note_type         clinical_note_type_enum NOT NULL DEFAULT 'progress',
    title             TEXT,
    content           TEXT NOT NULL,
    is_ai_generated   BOOLEAN NOT NULL DEFAULT false,
    ai_session_id     UUID REFERENCES ai_sessions(id) ON DELETE SET NULL,
    review_status     content_review_status_enum NOT NULL DEFAULT 'draft',
    reviewed_by       UUID REFERENCES users(id) ON DELETE SET NULL,
    reviewed_at       TIMESTAMPTZ,
    finalized_at      TIMESTAMPTZ,
    embedding_id      UUID,
    search_vector     TSVECTOR GENERATED ALWAYS AS (
                          setweight(to_tsvector('english', coalesce(title, '')), 'A') ||
                          setweight(to_tsvector('english', coalesce(content, '')), 'B')
                      ) STORED,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at        TIMESTAMPTZ,
    created_by        UUID REFERENCES users(id) ON DELETE SET NULL,
    updated_by        UUID REFERENCES users(id) ON DELETE SET NULL,
    CONSTRAINT ck_clinical_notes_ai_session_requires_flag
        CHECK (ai_session_id IS NULL OR is_ai_generated)
);

CREATE INDEX ix_clinical_notes_visit_id ON clinical_notes (visit_id);
CREATE INDEX ix_clinical_notes_patient_id_created_at ON clinical_notes (patient_id, created_at DESC);
CREATE INDEX ix_clinical_notes_search_vector ON clinical_notes USING GIN (search_vector);
```

> **Finalization immutability:** once `review_status = 'finalized'`, a
> clinical note should not have its `content` edited — corrections are made
> via a new `note_type = 'addendum'` row referencing it (application-level
> convention; the FK for "addends" can be added as a future
> `amends_note_id UUID REFERENCES clinical_notes(id)` column if needed). An
> optional `BEFORE UPDATE` trigger can enforce
> `OLD.finalized_at IS NOT NULL AND NEW.content <> OLD.content → RAISE
> EXCEPTION` for teams that want this enforced in the database rather than
> only in application logic.

---

## Module 14: SOAP Notes

### `soap_notes`

**Purpose:** The structured Subjective/Objective/Assessment/Plan note — the
canonical, standardized encounter summary. One per visit.

**Tenant scope:** `organization_id`

| Column | Type | Nullable | Default | Description |
|---|---|---|---|---|
| `id` | `UUID` | No | `gen_random_uuid()` | PK |
| `organization_id` | `UUID` | No | — | FK → `organizations.id` |
| `visit_id` | `UUID` | No | — | FK → `visits.id`, **unique** (1:1) |
| `patient_id` | `UUID` | No | — | FK → `patients.id`; denormalized |
| `author_id` | `UUID` | No | — | FK → `users.id` |
| `subjective` | `TEXT` | Yes | — | Patient-reported symptoms/history |
| `objective` | `TEXT` | Yes | — | Exam findings, measurements |
| `assessment` | `TEXT` | Yes | — | Diagnosis/clinical impression |
| `plan` | `TEXT` | Yes | — | Treatment plan, follow-up |
| `is_ai_generated` | `BOOLEAN` | No | `false` | |
| `ai_session_id` | `UUID` | Yes | — | FK → `ai_sessions.id` |
| `ai_model_used` | `TEXT` | Yes | — | Snapshot, e.g. `gemini-2.5-pro` |
| `ai_confidence_score` | `NUMERIC(5,4)` | Yes | — | 0.0000–1.0000 |
| `suggested_icd10_codes` | `JSONB` | Yes | — | AI-suggested coding candidates, `[{code, description, confidence}]` |
| `review_status` | `content_review_status_enum` | No | `'draft'` | |
| `reviewed_by` | `UUID` | Yes | — | FK → `users.id` |
| `reviewed_at` | `TIMESTAMPTZ` | Yes | — | |
| `finalized_at` | `TIMESTAMPTZ` | Yes | — | |
| `embedding_id` | `UUID` | Yes | — | Qdrant point ID |
| `search_vector` | `TSVECTOR` | Yes | *generated* | Full-text search over all four SOAP fields |
| `created_at` / `updated_at` / `deleted_at` / `created_by` / `updated_by` | standard | | | |

- **Primary key:** `id`
- **Foreign keys:** `organization_id → organizations.id ON DELETE RESTRICT`; `visit_id → visits.id ON DELETE CASCADE`; `patient_id → patients.id ON DELETE RESTRICT`; `author_id → users.id ON DELETE RESTRICT`; `ai_session_id → ai_sessions.id ON DELETE SET NULL`; `reviewed_by → users.id ON DELETE SET NULL`
- **Unique constraints:** `uq_soap_notes_visit_id` on `visit_id` — enforces one SOAP note per visit
- **Check constraints:** `ck_soap_notes_confidence_range CHECK (ai_confidence_score BETWEEN 0 AND 1)`; `ck_soap_notes_ai_session_requires_flag CHECK (ai_session_id IS NULL OR is_ai_generated)`
- **Indexes:** `ix_soap_notes_patient_id_created_at`; GIN on `search_vector`
- **Enums:** `content_review_status_enum`
- **Soft delete:** standard; finalization immutability convention as per `clinical_notes`

```sql
CREATE TABLE soap_notes (
    id                       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id          UUID NOT NULL REFERENCES organizations(id) ON DELETE RESTRICT,
    visit_id                 UUID NOT NULL REFERENCES visits(id) ON DELETE CASCADE,
    patient_id                UUID NOT NULL REFERENCES patients(id) ON DELETE RESTRICT,
    author_id                 UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    subjective                 TEXT,
    objective                  TEXT,
    assessment                 TEXT,
    plan                       TEXT,
    is_ai_generated            BOOLEAN NOT NULL DEFAULT false,
    ai_session_id              UUID REFERENCES ai_sessions(id) ON DELETE SET NULL,
    ai_model_used              TEXT,
    ai_confidence_score        NUMERIC(5,4),
    suggested_icd10_codes      JSONB,
    review_status              content_review_status_enum NOT NULL DEFAULT 'draft',
    reviewed_by                UUID REFERENCES users(id) ON DELETE SET NULL,
    reviewed_at                TIMESTAMPTZ,
    finalized_at               TIMESTAMPTZ,
    embedding_id               UUID,
    search_vector              TSVECTOR GENERATED ALWAYS AS (
                                    setweight(to_tsvector('english', coalesce(subjective, '')), 'A') ||
                                    setweight(to_tsvector('english', coalesce(assessment, '')), 'A') ||
                                    setweight(to_tsvector('english', coalesce(objective, '')), 'B') ||
                                    setweight(to_tsvector('english', coalesce(plan, '')), 'B')
                                ) STORED,
    created_at                 TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at                 TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at                 TIMESTAMPTZ,
    created_by                 UUID REFERENCES users(id) ON DELETE SET NULL,
    updated_by                 UUID REFERENCES users(id) ON DELETE SET NULL,
    CONSTRAINT ck_soap_notes_confidence_range
        CHECK (ai_confidence_score IS NULL OR ai_confidence_score BETWEEN 0 AND 1),
    CONSTRAINT ck_soap_notes_ai_session_requires_flag
        CHECK (ai_session_id IS NULL OR is_ai_generated)
);

CREATE UNIQUE INDEX uq_soap_notes_visit_id ON soap_notes (visit_id);
CREATE INDEX ix_soap_notes_patient_id_created_at ON soap_notes (patient_id, created_at DESC);
CREATE INDEX ix_soap_notes_search_vector ON soap_notes USING GIN (search_vector);
```
