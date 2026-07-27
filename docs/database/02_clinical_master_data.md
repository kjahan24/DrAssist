# Modules 5–10: Doctors, Patients, Contacts, Allergies, Medications, Conditions

All tables here are tenant-scoped (`organization_id NOT NULL`) **except** the
two reference catalogs `specialties` and `condition_codes`, which are global.

---

## Module 5: Doctors

### `specialties` (reference table)

**Purpose:** Global catalog of medical specialties (Cardiology, Pediatrics,
…). A lookup table rather than an enum because the list is long, grows over
time, and may need admin curation independent of a schema migration.

**Tenant scope:** Global

| Column | Type | Nullable | Default | Description |
|---|---|---|---|---|
| `id` | `UUID` | No | `gen_random_uuid()` | PK |
| `name` | `TEXT` | No | — | e.g. "Cardiology" |
| `description` | `TEXT` | Yes | — | |
| `created_at` / `updated_at` / `deleted_at` / `created_by` / `updated_by` | standard | | | |

- **Primary key:** `id`
- **Unique constraints:** `uq_specialties_name` on `name` (partial, `WHERE deleted_at IS NULL`)

```sql
CREATE TABLE specialties (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name          TEXT NOT NULL,
    description   TEXT,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at    TIMESTAMPTZ,
    created_by    UUID REFERENCES users(id) ON DELETE SET NULL,
    updated_by    UUID REFERENCES users(id) ON DELETE SET NULL
);

CREATE UNIQUE INDEX uq_specialties_name ON specialties (name) WHERE deleted_at IS NULL;
```

---

### `doctors`

**Purpose:** Clinical-role extension of a `users` row — license, NPI, and
practice details for staff with prescribing/clinical documentation
privileges.

**Tenant scope:** `organization_id`

| Column | Type | Nullable | Default | Description |
|---|---|---|---|---|
| `id` | `UUID` | No | `gen_random_uuid()` | PK |
| `organization_id` | `UUID` | No | — | FK → `organizations.id` |
| `user_id` | `UUID` | No | — | FK → `users.id`, 1:1 |
| `license_number` | `TEXT` | No | — | |
| `license_state` | `TEXT` | Yes | — | |
| `license_expiry` | `DATE` | Yes | — | |
| `npi_number` | `TEXT` | Yes | — | US National Provider Identifier |
| `years_of_experience` | `SMALLINT` | Yes | — | |
| `bio` | `TEXT` | Yes | — | |
| `signature_attachment_id` | `UUID` | Yes | — | FK → `attachments.id` |
| `consultation_fee` | `NUMERIC(10,2)` | Yes | — | |
| `is_accepting_patients` | `BOOLEAN` | No | `true` | |
| `created_at` / `updated_at` / `deleted_at` / `created_by` / `updated_by` | standard | | | |

- **Primary key:** `id`
- **Foreign keys:** `organization_id → organizations.id ON DELETE RESTRICT`; `user_id → users.id ON DELETE CASCADE` (a doctor profile has no independent existence without its user identity); `signature_attachment_id → attachments.id ON DELETE SET NULL`
- **Unique constraints:** `uq_doctors_user_id` on `user_id`; `uq_doctors_npi_number` on `npi_number` (partial, `WHERE npi_number IS NOT NULL AND deleted_at IS NULL`) — NPI is nationally unique, not per-tenant
- **Check constraints:** `ck_doctors_years_of_experience_nonneg CHECK (years_of_experience >= 0)`
- **Indexes:** `ix_doctors_organization_id`
- **Soft delete:** standard

```sql
CREATE TABLE doctors (
    id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id             UUID NOT NULL REFERENCES organizations(id) ON DELETE RESTRICT,
    user_id                     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    license_number              TEXT NOT NULL,
    license_state               TEXT,
    license_expiry              DATE,
    npi_number                  TEXT,
    years_of_experience         SMALLINT,
    bio                         TEXT,
    signature_attachment_id     UUID REFERENCES attachments(id) ON DELETE SET NULL,
    consultation_fee            NUMERIC(10,2),
    is_accepting_patients       BOOLEAN NOT NULL DEFAULT true,
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at                  TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at                  TIMESTAMPTZ,
    created_by                  UUID REFERENCES users(id) ON DELETE SET NULL,
    updated_by                  UUID REFERENCES users(id) ON DELETE SET NULL,
    CONSTRAINT ck_doctors_years_of_experience_nonneg CHECK (years_of_experience IS NULL OR years_of_experience >= 0)
);

CREATE UNIQUE INDEX uq_doctors_user_id ON doctors (user_id);
CREATE UNIQUE INDEX uq_doctors_npi_number ON doctors (npi_number)
    WHERE npi_number IS NOT NULL AND deleted_at IS NULL;
CREATE INDEX ix_doctors_organization_id ON doctors (organization_id);
```

---

### `doctor_specialties`

**Purpose:** Join table — a doctor may practice multiple specialties, one marked primary.

**Tenant scope:** Inherits from `doctors.organization_id`

| Column | Type | Nullable | Default | Description |
|---|---|---|---|---|
| `id` | `UUID` | No | `gen_random_uuid()` | PK |
| `doctor_id` | `UUID` | No | — | FK → `doctors.id` |
| `specialty_id` | `UUID` | No | — | FK → `specialties.id` |
| `is_primary` | `BOOLEAN` | No | `false` | |
| `created_at` / `updated_at` / `deleted_at` / `created_by` / `updated_by` | standard | | | |

- **Primary key:** `id`
- **Foreign keys:** `doctor_id → doctors.id ON DELETE CASCADE`; `specialty_id → specialties.id ON DELETE RESTRICT`
- **Unique constraints:** `uq_doctor_specialties_doctor_specialty` on `(doctor_id, specialty_id)`
- **Indexes:** `ix_doctor_specialties_specialty_id`
- **Note:** "exactly one primary specialty per doctor" is enforced at the application layer (a partial unique index `WHERE is_primary` per `doctor_id` is also viable if strict DB enforcement is preferred: `CREATE UNIQUE INDEX ... ON doctor_specialties (doctor_id) WHERE is_primary`).

```sql
CREATE TABLE doctor_specialties (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    doctor_id      UUID NOT NULL REFERENCES doctors(id) ON DELETE CASCADE,
    specialty_id   UUID NOT NULL REFERENCES specialties(id) ON DELETE RESTRICT,
    is_primary     BOOLEAN NOT NULL DEFAULT false,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at     TIMESTAMPTZ,
    created_by     UUID REFERENCES users(id) ON DELETE SET NULL,
    updated_by     UUID REFERENCES users(id) ON DELETE SET NULL
);

CREATE UNIQUE INDEX uq_doctor_specialties_doctor_specialty
    ON doctor_specialties (doctor_id, specialty_id);
CREATE UNIQUE INDEX uq_doctor_specialties_one_primary
    ON doctor_specialties (doctor_id) WHERE is_primary;
CREATE INDEX ix_doctor_specialties_specialty_id ON doctor_specialties (specialty_id);
```

---

## Module 6: Patients

### `patients`

**Purpose:** Core demographic/identity record for a patient. The anchor for
all clinical data (allergies, medications, conditions, visits, labs).

**Tenant scope:** `organization_id`

| Column | Type | Nullable | Default | Description |
|---|---|---|---|---|
| `id` | `UUID` | No | `gen_random_uuid()` | PK |
| `organization_id` | `UUID` | No | — | FK → `organizations.id` |
| `user_id` | `UUID` | Yes | — | FK → `users.id`; null unless the patient has portal login |
| `medical_record_number` | `TEXT` | No | — | Tenant-assigned MRN |
| `first_name` | `TEXT` | No | — | |
| `last_name` | `TEXT` | No | — | |
| `middle_name` | `TEXT` | Yes | — | |
| `date_of_birth` | `DATE` | No | — | |
| `sex_at_birth` | `sex_enum` | No | `'unknown'` | |
| `gender_identity` | `TEXT` | Yes | — | Free text; deliberately not an enum |
| `blood_type` | `blood_type_enum` | Yes | — | |
| `marital_status` | `marital_status_enum` | Yes | — | |
| `email` | `CITEXT` | Yes | — | |
| `phone` | `TEXT` | Yes | — | |
| `address_line1` | `TEXT` | Yes | — | |
| `address_line2` | `TEXT` | Yes | — | |
| `city` | `TEXT` | Yes | — | |
| `state` | `TEXT` | Yes | — | |
| `postal_code` | `TEXT` | Yes | — | |
| `country_code` | `CHAR(2)` | Yes | — | |
| `preferred_language` | `TEXT` | Yes | — | |
| `national_id_number_encrypted` | `TEXT` | Yes | — | SSN/national ID — application-layer encrypted before storage, see best practices |
| `is_deceased` | `BOOLEAN` | No | `false` | |
| `deceased_date` | `DATE` | Yes | — | |
| `photo_attachment_id` | `UUID` | Yes | — | FK → `attachments.id` |
| `created_at` / `updated_at` / `deleted_at` / `created_by` / `updated_by` | standard | | | |

- **Primary key:** `id`
- **Foreign keys:** `organization_id → organizations.id ON DELETE RESTRICT`; `user_id → users.id ON DELETE SET NULL`; `photo_attachment_id → attachments.id ON DELETE SET NULL`; `created_by`/`updated_by → users.id ON DELETE SET NULL`
- **Unique constraints:** `uq_patients_org_mrn` on `(organization_id, medical_record_number)` (partial, `WHERE deleted_at IS NULL`); `uq_patients_user_id` on `user_id` (partial, `WHERE user_id IS NOT NULL`)
- **Check constraints:** `ck_patients_deceased_date_requires_flag CHECK (deceased_date IS NULL OR is_deceased)`; `ck_patients_country_code_format CHECK (country_code ~ '^[A-Z]{2}$')`
- **Indexes:** `ix_patients_organization_id`; `ix_patients_org_last_first_name` on `(organization_id, last_name, first_name)` for name search; `ix_patients_date_of_birth`
- **Enums:** `sex_enum`, `blood_type_enum`, `marital_status_enum`
- **Soft delete:** standard — this is the primary retention lever for right-to-erasure requests balanced against legal medical-record retention requirements (see best practices doc)

```sql
CREATE TYPE sex_enum AS ENUM ('male', 'female', 'intersex', 'unknown');

CREATE TYPE blood_type_enum AS ENUM (
    'a_positive', 'a_negative', 'b_positive', 'b_negative',
    'ab_positive', 'ab_negative', 'o_positive', 'o_negative', 'unknown'
);

CREATE TYPE marital_status_enum AS ENUM (
    'single', 'married', 'divorced', 'widowed', 'separated', 'unknown'
);

CREATE TABLE patients (
    id                              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id                 UUID NOT NULL REFERENCES organizations(id) ON DELETE RESTRICT,
    user_id                         UUID REFERENCES users(id) ON DELETE SET NULL,
    medical_record_number           TEXT NOT NULL,
    first_name                      TEXT NOT NULL,
    last_name                       TEXT NOT NULL,
    middle_name                     TEXT,
    date_of_birth                   DATE NOT NULL,
    sex_at_birth                    sex_enum NOT NULL DEFAULT 'unknown',
    gender_identity                 TEXT,
    blood_type                      blood_type_enum,
    marital_status                  marital_status_enum,
    email                           CITEXT,
    phone                           TEXT,
    address_line1                   TEXT,
    address_line2                   TEXT,
    city                            TEXT,
    state                           TEXT,
    postal_code                     TEXT,
    country_code                    CHAR(2),
    preferred_language              TEXT,
    national_id_number_encrypted    TEXT,
    is_deceased                     BOOLEAN NOT NULL DEFAULT false,
    deceased_date                   DATE,
    photo_attachment_id             UUID REFERENCES attachments(id) ON DELETE SET NULL,
    created_at                      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at                      TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at                      TIMESTAMPTZ,
    created_by                      UUID REFERENCES users(id) ON DELETE SET NULL,
    updated_by                      UUID REFERENCES users(id) ON DELETE SET NULL,
    CONSTRAINT ck_patients_deceased_date_requires_flag
        CHECK (deceased_date IS NULL OR is_deceased),
    CONSTRAINT ck_patients_country_code_format
        CHECK (country_code IS NULL OR country_code ~ '^[A-Z]{2}$')
);

CREATE UNIQUE INDEX uq_patients_org_mrn
    ON patients (organization_id, medical_record_number) WHERE deleted_at IS NULL;
CREATE UNIQUE INDEX uq_patients_user_id ON patients (user_id) WHERE user_id IS NOT NULL;
CREATE INDEX ix_patients_organization_id ON patients (organization_id);
CREATE INDEX ix_patients_org_last_first_name ON patients (organization_id, last_name, first_name);
CREATE INDEX ix_patients_date_of_birth ON patients (date_of_birth);
```

> **PII encryption note:** `national_id_number_encrypted` stores ciphertext
> produced by the application (e.g. `pgcrypto`'s `pgp_sym_encrypt` called
> from the app, or envelope encryption via a KMS) — the database never sees
> the plaintext value. This is distinct from column-level `pgcrypto` calls
> done in SQL, which would still expose plaintext in query logs.

---

## Module 7: Patient Contacts

### `patient_contacts`

**Purpose:** Emergency contacts, guardians, next-of-kin, and caregivers
associated with a patient.

**Tenant scope:** `organization_id` (denormalized from `patients.organization_id`)

| Column | Type | Nullable | Default | Description |
|---|---|---|---|---|
| `id` | `UUID` | No | `gen_random_uuid()` | PK |
| `organization_id` | `UUID` | No | — | FK → `organizations.id` |
| `patient_id` | `UUID` | No | — | FK → `patients.id` |
| `contact_type` | `contact_type_enum` | No | — | |
| `full_name` | `TEXT` | No | — | |
| `relationship` | `TEXT` | Yes | — | e.g. "Mother", "Spouse" |
| `phone` | `TEXT` | Yes | — | |
| `email` | `CITEXT` | Yes | — | |
| `address_line1` | `TEXT` | Yes | — | |
| `is_primary` | `BOOLEAN` | No | `false` | |
| `created_at` / `updated_at` / `deleted_at` / `created_by` / `updated_by` | standard | | | |

- **Primary key:** `id`
- **Foreign keys:** `organization_id → organizations.id ON DELETE RESTRICT`; `patient_id → patients.id ON DELETE CASCADE`
- **Indexes:** `ix_patient_contacts_patient_id`
- **Enums:** `contact_type_enum`
- **Soft delete:** standard

```sql
CREATE TYPE contact_type_enum AS ENUM (
    'emergency', 'guardian', 'next_of_kin', 'caregiver', 'insurance'
);

CREATE TABLE patient_contacts (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id   UUID NOT NULL REFERENCES organizations(id) ON DELETE RESTRICT,
    patient_id        UUID NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    contact_type      contact_type_enum NOT NULL,
    full_name         TEXT NOT NULL,
    relationship      TEXT,
    phone             TEXT,
    email             CITEXT,
    address_line1     TEXT,
    is_primary        BOOLEAN NOT NULL DEFAULT false,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at        TIMESTAMPTZ,
    created_by        UUID REFERENCES users(id) ON DELETE SET NULL,
    updated_by        UUID REFERENCES users(id) ON DELETE SET NULL
);

CREATE INDEX ix_patient_contacts_patient_id ON patient_contacts (patient_id);
CREATE INDEX ix_patient_contacts_organization_id ON patient_contacts (organization_id);
```

---

## Module 8: Patient Allergies

### `patient_allergies`

**Purpose:** Longitudinal allergy list — persists across visits, critical
for clinical safety checks (drug interaction warnings).

**Tenant scope:** `organization_id`

| Column | Type | Nullable | Default | Description |
|---|---|---|---|---|
| `id` | `UUID` | No | `gen_random_uuid()` | PK |
| `organization_id` | `UUID` | No | — | FK → `organizations.id` |
| `patient_id` | `UUID` | No | — | FK → `patients.id` |
| `allergen` | `TEXT` | No | — | e.g. "Penicillin" |
| `allergen_type` | `allergen_type_enum` | No | — | |
| `reaction` | `TEXT` | Yes | — | e.g. "Hives, difficulty breathing" |
| `severity` | `allergy_severity_enum` | No | `'mild'` | |
| `status` | `clinical_status_enum` | No | `'active'` | |
| `onset_date` | `DATE` | Yes | — | |
| `recorded_by` | `UUID` | Yes | — | FK → `users.id` |
| `notes` | `TEXT` | Yes | — | |
| `created_at` / `updated_at` / `deleted_at` / `created_by` / `updated_by` | standard | | | |

- **Primary key:** `id`
- **Foreign keys:** `organization_id → organizations.id ON DELETE RESTRICT`; `patient_id → patients.id ON DELETE CASCADE`; `recorded_by → users.id ON DELETE SET NULL`
- **Indexes:** `ix_patient_allergies_patient_id`; `ix_patient_allergies_patient_status` on `(patient_id, status)` — safety-check queries always filter to active allergies
- **Enums:** `allergen_type_enum`, `allergy_severity_enum`, `clinical_status_enum` (shared enum, see below)
- **Soft delete:** standard — but note allergies are typically *corrected* via `status = 'resolved'`, not deleted; `deleted_at` is reserved for true data-entry errors

```sql
CREATE TYPE allergen_type_enum AS ENUM ('medication', 'food', 'environmental', 'other');
CREATE TYPE allergy_severity_enum AS ENUM ('mild', 'moderate', 'severe', 'life_threatening');

-- Shared across allergies / medications / conditions where a lifecycle status applies
CREATE TYPE clinical_status_enum AS ENUM ('active', 'inactive', 'resolved', 'chronic', 'in_remission');

CREATE TABLE patient_allergies (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id   UUID NOT NULL REFERENCES organizations(id) ON DELETE RESTRICT,
    patient_id        UUID NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    allergen          TEXT NOT NULL,
    allergen_type     allergen_type_enum NOT NULL,
    reaction          TEXT,
    severity          allergy_severity_enum NOT NULL DEFAULT 'mild',
    status            clinical_status_enum NOT NULL DEFAULT 'active',
    onset_date        DATE,
    recorded_by       UUID REFERENCES users(id) ON DELETE SET NULL,
    notes             TEXT,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at        TIMESTAMPTZ,
    created_by        UUID REFERENCES users(id) ON DELETE SET NULL,
    updated_by        UUID REFERENCES users(id) ON DELETE SET NULL
);

CREATE INDEX ix_patient_allergies_patient_id ON patient_allergies (patient_id);
CREATE INDEX ix_patient_allergies_patient_status ON patient_allergies (patient_id, status);
```

---

## Module 9: Patient Medications

### `patient_medications`

**Purpose:** Medication history — active prescriptions and past courses.

**Tenant scope:** `organization_id`

| Column | Type | Nullable | Default | Description |
|---|---|---|---|---|
| `id` | `UUID` | No | `gen_random_uuid()` | PK |
| `organization_id` | `UUID` | No | — | FK → `organizations.id` |
| `patient_id` | `UUID` | No | — | FK → `patients.id` |
| `prescribed_by` | `UUID` | Yes | — | FK → `doctors.id` |
| `medication_name` | `TEXT` | No | — | |
| `dosage` | `TEXT` | Yes | — | e.g. "500mg" |
| `route` | `medication_route_enum` | Yes | — | |
| `frequency` | `TEXT` | Yes | — | e.g. "Twice daily" |
| `start_date` | `DATE` | No | — | |
| `end_date` | `DATE` | Yes | — | |
| `status` | `medication_status_enum` | No | `'active'` | |
| `reason` | `TEXT` | Yes | — | |
| `created_at` / `updated_at` / `deleted_at` / `created_by` / `updated_by` | standard | | | |

- **Primary key:** `id`
- **Foreign keys:** `organization_id → organizations.id ON DELETE RESTRICT`; `patient_id → patients.id ON DELETE CASCADE`; `prescribed_by → doctors.id ON DELETE SET NULL`
- **Check constraints:** `ck_patient_medications_date_order CHECK (end_date IS NULL OR end_date >= start_date)`
- **Indexes:** `ix_patient_medications_patient_id`; `ix_patient_medications_patient_status` on `(patient_id, status)`
- **Enums:** `medication_route_enum`, `medication_status_enum`
- **Soft delete:** standard

```sql
CREATE TYPE medication_route_enum AS ENUM (
    'oral', 'intravenous', 'intramuscular', 'subcutaneous', 'topical', 'inhalation', 'other'
);
CREATE TYPE medication_status_enum AS ENUM ('active', 'discontinued', 'completed', 'on_hold');

CREATE TABLE patient_medications (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id   UUID NOT NULL REFERENCES organizations(id) ON DELETE RESTRICT,
    patient_id        UUID NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    prescribed_by     UUID REFERENCES doctors(id) ON DELETE SET NULL,
    medication_name   TEXT NOT NULL,
    dosage            TEXT,
    route             medication_route_enum,
    frequency         TEXT,
    start_date        DATE NOT NULL,
    end_date          DATE,
    status            medication_status_enum NOT NULL DEFAULT 'active',
    reason            TEXT,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at        TIMESTAMPTZ,
    created_by        UUID REFERENCES users(id) ON DELETE SET NULL,
    updated_by        UUID REFERENCES users(id) ON DELETE SET NULL,
    CONSTRAINT ck_patient_medications_date_order CHECK (end_date IS NULL OR end_date >= start_date)
);

CREATE INDEX ix_patient_medications_patient_id ON patient_medications (patient_id);
CREATE INDEX ix_patient_medications_patient_status ON patient_medications (patient_id, status);
```

---

## Module 10: Patient Conditions

### `condition_codes` (reference table)

**Purpose:** Global ICD-10 diagnosis code catalog, supporting structured
coding rather than free text (also a natural anchor point for future AI
coding-assist features).

**Tenant scope:** Global

| Column | Type | Nullable | Default | Description |
|---|---|---|---|---|
| `id` | `UUID` | No | `gen_random_uuid()` | PK |
| `code` | `TEXT` | No | — | e.g. `E11.9` |
| `description` | `TEXT` | No | — | e.g. "Type 2 diabetes mellitus without complications" |
| `category` | `TEXT` | Yes | — | ICD-10 chapter/category |
| `created_at` / `updated_at` / `deleted_at` / `created_by` / `updated_by` | standard | | | |

- **Primary key:** `id`
- **Unique constraints:** `uq_condition_codes_code` on `code`
- **Indexes:** GIN trigram index on `description` for fuzzy diagnosis search (`pg_trgm`)

```sql
CREATE TABLE condition_codes (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code          TEXT NOT NULL,
    description   TEXT NOT NULL,
    category      TEXT,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at    TIMESTAMPTZ,
    created_by    UUID REFERENCES users(id) ON DELETE SET NULL,
    updated_by    UUID REFERENCES users(id) ON DELETE SET NULL
);

CREATE UNIQUE INDEX uq_condition_codes_code ON condition_codes (code) WHERE deleted_at IS NULL;
CREATE INDEX ix_condition_codes_description_trgm
    ON condition_codes USING GIN (description gin_trgm_ops);
```

---

### `patient_conditions`

**Purpose:** Diagnoses / chronic conditions attributed to a patient, each
optionally coded against `condition_codes`.

**Tenant scope:** `organization_id`

| Column | Type | Nullable | Default | Description |
|---|---|---|---|---|
| `id` | `UUID` | No | `gen_random_uuid()` | PK |
| `organization_id` | `UUID` | No | — | FK → `organizations.id` |
| `patient_id` | `UUID` | No | — | FK → `patients.id` |
| `condition_code_id` | `UUID` | Yes | — | FK → `condition_codes.id` |
| `condition_name` | `TEXT` | No | — | Snapshot of the name at diagnosis time (survives catalog edits) |
| `icd10_code` | `TEXT` | Yes | — | Denormalized snapshot of the code string |
| `status` | `clinical_status_enum` | No | `'active'` | |
| `severity` | `allergy_severity_enum` | Yes | — | Reused mild/moderate/severe/life_threatening scale |
| `diagnosed_date` | `DATE` | Yes | — | |
| `resolved_date` | `DATE` | Yes | — | |
| `diagnosed_by` | `UUID` | Yes | — | FK → `doctors.id` |
| `notes` | `TEXT` | Yes | — | |
| `created_at` / `updated_at` / `deleted_at` / `created_by` / `updated_by` | standard | | | |

- **Primary key:** `id`
- **Foreign keys:** `organization_id → organizations.id ON DELETE RESTRICT`; `patient_id → patients.id ON DELETE CASCADE`; `condition_code_id → condition_codes.id ON DELETE SET NULL`; `diagnosed_by → doctors.id ON DELETE SET NULL`
- **Check constraints:** `ck_patient_conditions_date_order CHECK (resolved_date IS NULL OR diagnosed_date IS NULL OR resolved_date >= diagnosed_date)`
- **Indexes:** `ix_patient_conditions_patient_id`; `ix_patient_conditions_patient_status`; `ix_patient_conditions_condition_code_id`
- **Enums:** `clinical_status_enum`, `allergy_severity_enum` (reused)
- **Soft delete:** standard

```sql
CREATE TABLE patient_conditions (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id     UUID NOT NULL REFERENCES organizations(id) ON DELETE RESTRICT,
    patient_id          UUID NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    condition_code_id   UUID REFERENCES condition_codes(id) ON DELETE SET NULL,
    condition_name      TEXT NOT NULL,
    icd10_code          TEXT,
    status              clinical_status_enum NOT NULL DEFAULT 'active',
    severity            allergy_severity_enum,
    diagnosed_date      DATE,
    resolved_date       DATE,
    diagnosed_by        UUID REFERENCES doctors(id) ON DELETE SET NULL,
    notes               TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at          TIMESTAMPTZ,
    created_by          UUID REFERENCES users(id) ON DELETE SET NULL,
    updated_by          UUID REFERENCES users(id) ON DELETE SET NULL,
    CONSTRAINT ck_patient_conditions_date_order
        CHECK (resolved_date IS NULL OR diagnosed_date IS NULL OR resolved_date >= diagnosed_date)
);

CREATE INDEX ix_patient_conditions_patient_id ON patient_conditions (patient_id);
CREATE INDEX ix_patient_conditions_patient_status ON patient_conditions (patient_id, status);
CREATE INDEX ix_patient_conditions_condition_code_id ON patient_conditions (condition_code_id);
```
