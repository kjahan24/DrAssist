# Modules 15–17: AI Sessions, Conversation Transcripts, Patient History Timeline

All tables tenant-scoped (`organization_id NOT NULL`). This module is the
platform's primary integration surface with the AI stack (Gemini,
faster-whisper, PaddleOCR, Qdrant) — see `../ARCHITECTURE.md` for the
application-layer ports these tables support (`ai_provider_port`,
`vector_store_port`).

---

## Module 15: AI Sessions

### `ai_sessions`

**Purpose:** One row per AI-assisted interaction — an ambient-scribe
recording, a transcription job, a summarization pass, a coding-assist run.
Tracks provider/model, lifecycle, and cost, independent of what the session
ultimately produces (transcripts, notes).

**Tenant scope:** `organization_id`

| Column | Type | Nullable | Default | Description |
|---|---|---|---|---|
| `id` | `UUID` | No | `gen_random_uuid()` | PK |
| `organization_id` | `UUID` | No | — | FK → `organizations.id` |
| `visit_id` | `UUID` | Yes | — | FK → `visits.id`; nullable — some sessions (e.g. async chat) aren't visit-bound |
| `patient_id` | `UUID` | Yes | — | FK → `patients.id` |
| `initiated_by` | `UUID` | No | — | FK → `users.id`, who started the session |
| `session_type` | `ai_session_type_enum` | No | — | |
| `status` | `ai_session_status_enum` | No | `'pending'` | |
| `ai_provider` | `TEXT` | No | — | e.g. `gemini`, `faster-whisper`, `paddleocr` |
| `model_name` | `TEXT` | Yes | — | e.g. `gemini-2.5-pro` |
| `model_version` | `TEXT` | Yes | — | |
| `started_at` | `TIMESTAMPTZ` | Yes | — | |
| `ended_at` | `TIMESTAMPTZ` | Yes | — | |
| `input_tokens` | `INTEGER` | Yes | — | |
| `output_tokens` | `INTEGER` | Yes | — | |
| `cost_usd` | `NUMERIC(10,4)` | Yes | — | |
| `error_message` | `TEXT` | Yes | — | |
| `qdrant_collection` | `TEXT` | Yes | — | Collection name if this session wrote embeddings |
| `metadata` | `JSONB` | No | `'{}'` | Provider-specific extras |
| `created_at` / `updated_at` / `deleted_at` / `created_by` / `updated_by` | standard | | | |

- **Primary key:** `id`
- **Foreign keys:** `organization_id → organizations.id ON DELETE RESTRICT`; `visit_id → visits.id ON DELETE SET NULL`; `patient_id → patients.id ON DELETE SET NULL`; `initiated_by → users.id ON DELETE RESTRICT`
- **Check constraints:** `ck_ai_sessions_ended_after_started CHECK (ended_at IS NULL OR started_at IS NULL OR ended_at >= started_at)`; `ck_ai_sessions_tokens_nonneg CHECK (input_tokens IS NULL OR input_tokens >= 0)`
- **Indexes:** `ix_ai_sessions_visit_id`; `ix_ai_sessions_patient_id`; `ix_ai_sessions_organization_id_status`
- **Enums:** `ai_session_type_enum`, `ai_session_status_enum`
- **Soft delete:** standard

```sql
CREATE TYPE ai_session_type_enum AS ENUM (
    'ambient_scribe', 'transcription', 'summarization', 'coding_assist',
    'differential_diagnosis', 'chat'
);
CREATE TYPE ai_session_status_enum AS ENUM (
    'pending', 'in_progress', 'completed', 'failed', 'cancelled'
);

CREATE TABLE ai_sessions (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id     UUID NOT NULL REFERENCES organizations(id) ON DELETE RESTRICT,
    visit_id            UUID REFERENCES visits(id) ON DELETE SET NULL,
    patient_id          UUID REFERENCES patients(id) ON DELETE SET NULL,
    initiated_by        UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    session_type        ai_session_type_enum NOT NULL,
    status              ai_session_status_enum NOT NULL DEFAULT 'pending',
    ai_provider         TEXT NOT NULL,
    model_name          TEXT,
    model_version       TEXT,
    started_at          TIMESTAMPTZ,
    ended_at            TIMESTAMPTZ,
    input_tokens        INTEGER,
    output_tokens       INTEGER,
    cost_usd            NUMERIC(10,4),
    error_message       TEXT,
    qdrant_collection   TEXT,
    metadata            JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at          TIMESTAMPTZ,
    created_by          UUID REFERENCES users(id) ON DELETE SET NULL,
    updated_by          UUID REFERENCES users(id) ON DELETE SET NULL,
    CONSTRAINT ck_ai_sessions_ended_after_started
        CHECK (ended_at IS NULL OR started_at IS NULL OR ended_at >= started_at),
    CONSTRAINT ck_ai_sessions_tokens_nonneg
        CHECK (input_tokens IS NULL OR input_tokens >= 0)
);

CREATE INDEX ix_ai_sessions_visit_id ON ai_sessions (visit_id);
CREATE INDEX ix_ai_sessions_patient_id ON ai_sessions (patient_id);
CREATE INDEX ix_ai_sessions_organization_id_status ON ai_sessions (organization_id, status);
```

> `clinical_notes.ai_session_id` and `soap_notes.ai_session_id` (defined in
> `03_encounters.md`) reference this table — those FKs are only satisfiable
> once `ai_sessions` exists, which is why `ai_sessions` must be created
> before `clinical_notes`/`soap_notes` in migration order (see
> `08_migration_strategy.md`).

---

## Module 16: Conversation Transcripts

### `conversation_transcripts`

**Purpose:** Turn-level, speaker-diarized transcript segments produced by an
AI session (typically faster-whisper output during an ambient-scribe
recording). Segment-level granularity (rather than one blob per session)
supports audio-sync playback, per-speaker analysis, and fine-grained
retrieval for RAG.

**Tenant scope:** `organization_id`

| Column | Type | Nullable | Default | Description |
|---|---|---|---|---|
| `id` | `UUID` | No | `gen_random_uuid()` | PK |
| `organization_id` | `UUID` | No | — | FK → `organizations.id` |
| `ai_session_id` | `UUID` | No | — | FK → `ai_sessions.id` |
| `visit_id` | `UUID` | Yes | — | FK → `visits.id`; denormalized for direct visit-scoped queries |
| `sequence_number` | `INTEGER` | No | — | Ordering within the session |
| `speaker_role` | `speaker_role_enum` | No | `'unknown'` | |
| `speaker_label` | `TEXT` | Yes | — | Raw diarization label, e.g. "Speaker 1" |
| `start_offset_ms` | `INTEGER` | Yes | — | Offset from recording start |
| `end_offset_ms` | `INTEGER` | Yes | — | |
| `text_content` | `TEXT` | No | — | |
| `confidence_score` | `NUMERIC(5,4)` | Yes | — | ASR confidence, 0–1 |
| `language_code` | `TEXT` | Yes | — | BCP-47, e.g. `en-US` |
| `is_final` | `BOOLEAN` | No | `true` | False for interim streaming segments if ever persisted |
| `embedding_id` | `UUID` | Yes | — | Qdrant point ID |
| `created_at` / `updated_at` / `deleted_at` / `created_by` / `updated_by` | standard, **immutability-enforced** | | | see below |

- **Primary key:** `id`
- **Foreign keys:** `organization_id → organizations.id ON DELETE RESTRICT`; `ai_session_id → ai_sessions.id ON DELETE CASCADE`; `visit_id → visits.id ON DELETE SET NULL`
- **Unique constraints:** `uq_conversation_transcripts_session_sequence` on `(ai_session_id, sequence_number)`
- **Check constraints:** `ck_conversation_transcripts_offset_order CHECK (end_offset_ms IS NULL OR start_offset_ms IS NULL OR end_offset_ms >= start_offset_ms)`; `ck_conversation_transcripts_confidence_range CHECK (confidence_score BETWEEN 0 AND 1)`
- **Indexes:** `ix_conversation_transcripts_ai_session_id`; `ix_conversation_transcripts_visit_id`
- **Enums:** `speaker_role_enum`
- **Soft delete:** none functionally used — append-only, immutable once written (raw transcript is source-of-truth evidence for the encounter); `deleted_at` retained for schema consistency only, trigger-blocked like `audit_logs`

```sql
CREATE TYPE speaker_role_enum AS ENUM ('doctor', 'patient', 'other_participant', 'unknown', 'system');

CREATE TABLE conversation_transcripts (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id     UUID NOT NULL REFERENCES organizations(id) ON DELETE RESTRICT,
    ai_session_id       UUID NOT NULL REFERENCES ai_sessions(id) ON DELETE CASCADE,
    visit_id            UUID REFERENCES visits(id) ON DELETE SET NULL,
    sequence_number     INTEGER NOT NULL,
    speaker_role        speaker_role_enum NOT NULL DEFAULT 'unknown',
    speaker_label       TEXT,
    start_offset_ms     INTEGER,
    end_offset_ms       INTEGER,
    text_content        TEXT NOT NULL,
    confidence_score    NUMERIC(5,4),
    language_code       TEXT,
    is_final            BOOLEAN NOT NULL DEFAULT true,
    embedding_id        UUID,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at          TIMESTAMPTZ,
    created_by          UUID REFERENCES users(id) ON DELETE SET NULL,
    updated_by          UUID REFERENCES users(id) ON DELETE SET NULL,
    CONSTRAINT ck_conversation_transcripts_offset_order
        CHECK (end_offset_ms IS NULL OR start_offset_ms IS NULL OR end_offset_ms >= start_offset_ms),
    CONSTRAINT ck_conversation_transcripts_confidence_range
        CHECK (confidence_score IS NULL OR confidence_score BETWEEN 0 AND 1)
);

CREATE UNIQUE INDEX uq_conversation_transcripts_session_sequence
    ON conversation_transcripts (ai_session_id, sequence_number);
CREATE INDEX ix_conversation_transcripts_ai_session_id ON conversation_transcripts (ai_session_id);
CREATE INDEX ix_conversation_transcripts_visit_id ON conversation_transcripts (visit_id);

CREATE TRIGGER trg_conversation_transcripts_immutable
    BEFORE UPDATE OR DELETE ON conversation_transcripts
    FOR EACH ROW EXECUTE FUNCTION reject_mutation();
```

---

## Module 17: Patient History Timeline

### `patient_timeline_events`

**Purpose:** A derived, append-only feed of clinically significant events
for fast "what happened to this patient, in order" rendering — without the
UI having to fan out joins across visits, conditions, medications, labs,
notes, and AI sessions.

**Tenant scope:** `organization_id`

| Column | Type | Nullable | Default | Description |
|---|---|---|---|---|
| `id` | `UUID` | No | `gen_random_uuid()` | PK |
| `organization_id` | `UUID` | No | — | FK → `organizations.id` |
| `patient_id` | `UUID` | No | — | FK → `patients.id` |
| `event_type` | `timeline_event_type_enum` | No | — | |
| `event_timestamp` | `TIMESTAMPTZ` | No | — | When the clinical event occurred (may differ from `created_at`, the row-insert time) |
| `title` | `TEXT` | No | — | Short display label |
| `description` | `TEXT` | Yes | — | |
| `source_table` | `TEXT` | No | — | Loose polymorphic reference — see note |
| `source_id` | `UUID` | No | — | Loose polymorphic reference, **not** a DB-level FK |
| `actor_user_id` | `UUID` | Yes | — | FK → `users.id`, who caused the event |
| `is_visible_to_patient` | `BOOLEAN` | No | `true` | Gates patient-portal visibility |
| `metadata` | `JSONB` | No | `'{}'` | Denormalized snapshot so the UI never needs to join back to `source_table` |
| `created_at` / `updated_at` / `deleted_at` / `created_by` / `updated_by` | standard, **immutability-enforced** | | | see below |

- **Primary key:** `id`
- **Foreign keys:** `organization_id → organizations.id ON DELETE RESTRICT`; `patient_id → patients.id ON DELETE CASCADE`; `actor_user_id → users.id ON DELETE SET NULL`. **No FK on `(source_table, source_id)`** — a single polymorphic pair cannot reference multiple target tables with a native Postgres FK; see the trade-off discussion in `00_overview.md` and enforcement options in `09_best_practices_and_performance.md`.
- **Check constraints:** `ck_patient_timeline_events_source_table_known CHECK (source_table IN ('visits','patient_conditions','patient_medications','patient_allergies','lab_results','clinical_notes','soap_notes','ai_sessions','attachments'))`
- **Indexes:** `ix_patient_timeline_events_patient_id_event_timestamp` on `(patient_id, event_timestamp DESC)` — the primary access pattern; `ix_patient_timeline_events_source` on `(source_table, source_id)` for reverse lookup/backfill
- **Enums:** `timeline_event_type_enum`
- **Soft delete:** none functionally used — append-only; trigger-blocked

```sql
CREATE TYPE timeline_event_type_enum AS ENUM (
    'visit_created', 'visit_completed', 'diagnosis_added', 'medication_prescribed',
    'allergy_recorded', 'lab_result_received', 'note_added', 'ai_session_completed',
    'attachment_uploaded'
);

CREATE TABLE patient_timeline_events (
    id                       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id          UUID NOT NULL REFERENCES organizations(id) ON DELETE RESTRICT,
    patient_id                UUID NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    event_type                 timeline_event_type_enum NOT NULL,
    event_timestamp            TIMESTAMPTZ NOT NULL,
    title                      TEXT NOT NULL,
    description                TEXT,
    source_table               TEXT NOT NULL,
    source_id                  UUID NOT NULL,
    actor_user_id               UUID REFERENCES users(id) ON DELETE SET NULL,
    is_visible_to_patient       BOOLEAN NOT NULL DEFAULT true,
    metadata                    JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at                  TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at                  TIMESTAMPTZ,
    created_by                  UUID REFERENCES users(id) ON DELETE SET NULL,
    updated_by                  UUID REFERENCES users(id) ON DELETE SET NULL,
    CONSTRAINT ck_patient_timeline_events_source_table_known CHECK (
        source_table IN (
            'visits', 'patient_conditions', 'patient_medications', 'patient_allergies',
            'lab_results', 'clinical_notes', 'soap_notes', 'ai_sessions', 'attachments'
        )
    )
);

CREATE INDEX ix_patient_timeline_events_patient_id_event_timestamp
    ON patient_timeline_events (patient_id, event_timestamp DESC);
CREATE INDEX ix_patient_timeline_events_source
    ON patient_timeline_events (source_table, source_id);

CREATE TRIGGER trg_patient_timeline_events_immutable
    BEFORE UPDATE OR DELETE ON patient_timeline_events
    FOR EACH ROW EXECUTE FUNCTION reject_mutation();
```

> **How rows get here:** application-level, inside the same transaction that
> writes the source event (an "outbox"-style insert, not a separate async
> job — this guarantees the timeline never misses or duplicates an event).
> `reject_mutation()` is defined once and reused across every append-only
> table; see `06_audit_and_activity.md`.
