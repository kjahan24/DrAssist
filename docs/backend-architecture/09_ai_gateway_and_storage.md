# AI Gateway & Storage Layer

Both are **infrastructure-layer gateways to external systems**, owned by
the `ai` and `file_storage` modules respectively (`03_module_architecture.md`),
but documented together because they share a shape: a narrow port
interface, one or more provider adapters behind it, and a resilience
wrapper — plus every other module reaches them only through the owning
module's `public/` facade, never directly.

---

## AI Gateway

### Provider abstraction

The Turn 1 scaffold already defines the port interfaces this design
builds on (`app/shared/application/` after the relocation in
`01_folder_structure.md`): `TextGenerationPort`, `SpeechToTextPort`,
`OCRPort`. The `ai` module's infrastructure layer composes these into one
facade the Application layer depends on:

| Port | Concrete adapter (Turn 1 scaffold) | Provider |
|---|---|---|
| `TextGenerationPort` | `GeminiClient` | Gemini API |
| `SpeechToTextPort` | `WhisperClient` | faster-whisper (local inference) |
| `OCRPort` | `PaddleOCRClient` | PaddleOCR (local inference) |

**Strategy + Factory pattern for provider swapping:** a use case depends
on the *port*, never on `GeminiClient` directly. Adding a second text-
generation provider (e.g. a future non-Gemini LLM, or a fallback provider)
means writing one new adapter class implementing `TextGenerationPort` and
registering it in the `ai` module's `container.py` — zero changes to any
use case, satisfying the Open/Closed Principle. A `ProviderRegistry`
(infrastructure-layer) can select an adapter per request (e.g. "use
provider B for organization X because of a contractual requirement")
without that decision leaking into the Application layer.

### Resilience wrapper

AI providers are the least reliable external dependency in this system
(network calls, rate limits, occasional multi-second latency spikes). Every
provider call is wrapped, at the infrastructure layer, with:

- **Timeout** — bounded wait per call, so a hung provider request can't
  hold a Celery worker slot indefinitely.
- **Retry with backoff** (`tenacity`, already in the Turn 1
  `requirements/base.txt`) — for transient errors only (5xx, timeout, rate
  limit) — not for 4xx errors caused by bad input, which should fail fast.
- **Circuit breaker** — after repeated failures to one provider, stop
  sending it traffic for a cooldown window (fail fast, rather than let
  every queued job individually time out against a provider that's
  clearly down) — surfaces as an `AISessionFailed` event with a clear
  `error_message`, not a silent queue backup.

This wrapping lives entirely in `modules/ai/infrastructure/` — the
Application layer's use cases call the port and simply handle "it
succeeded" or "it raised," unaware of retry/circuit-breaker mechanics.

### Cost & usage tracking

Every Gateway call is wrapped by a thin interceptor that records
`input_tokens`/`output_tokens`/`cost_usd` (or the OCR/ASR-appropriate
equivalent) onto the owning `AiSession` aggregate — matching
`ai_sessions` columns in `../database/04_ai_features.md`. This is
infrastructure-layer instrumentation, not a decision any individual use
case makes per call, so cost tracking can't be accidentally omitted by a
future use case that forgets to add it.

### Async orchestration (why AI calls never block an API response)

AI operations (transcription, summarization) run for seconds, sometimes
tens of seconds — far longer than an HTTP request should hold open:

1. API layer: `RequestAIAssistedDraft`/`StartAISession` creates the
   `AiSession` in `pending` status and **returns immediately** — the HTTP
   response carries the session ID, not the result.
2. The use case enqueues a Celery task on the `ai_processing` queue
   (`08_background_workers.md`).
3. The worker task calls the Gateway (potentially minutes of real
   inference time for a long recording), then calls
   `CompleteAISession`, which updates the aggregate to `completed` (or
   `failed`) and publishes `AISessionCompleted`/`AISessionFailed`.
4. The client either polls `AISessionQueryPort.get_session_status` or
   receives a Notification-module push once the event fires — either way,
   the initial request/response cycle was never blocked on model
   inference.

### Embeddings & Qdrant

Embedding generation follows the same async path. On completion, the `ai`
module publishes `EmbeddingGenerated(source_table, source_id, point_id)` —
it does **not** write `point_id` into `clinical_notes.embedding_id` (or
whichever table) itself, because `ai` does not have write access to
another module's aggregate (`00_architectural_principles.md §8`). The
owning module (Clinical Note, SOAP Note, Lab Report) subscribes to this
event and updates its own row. This keeps `ai` genuinely generic — it
never needs to know the full list of tables that might one day want
embeddings.

Vector *search* (semantic retrieval for a future RAG feature) is exposed
the same way: a module wanting similarity search calls the `ai` module's
public query port with a query string/vector and gets back candidate
`(source_table, source_id, score)` tuples — Qdrant itself is never touched
outside `modules/ai/infrastructure/`.

---

## Storage layer

### Provider abstraction

`StoragePort` (Turn 1 scaffold, relocated to `app/shared/application/`)
is implemented by the `file_storage` module's MinIO adapter
(`modules/file_storage/infrastructure/`). As with the AI Gateway, every
other module reaches storage only through `file_storage`'s public facade
— no module constructs a MinIO client of its own.

### Presigned URL pattern

Uploads and downloads flow **client ⇄ MinIO directly**, never proxied
through the API server:

1. Caller (e.g. Patient module, wanting to attach a photo) calls
   `FileStorageCommandPort.request_upload_url(owner_type, owner_id,
   filename, content_type)`.
2. `file_storage`'s `RequestUploadUrl` use case validates the caller-
   supplied `owner_type` against the known enum
   (`../database/05_labs_and_attachments.md`), generates a `storage_key`
   (naming convention below), and returns a short-lived MinIO presigned
   PUT URL — no `attachments` row is created yet.
3. The client uploads bytes directly to MinIO using that URL.
4. The client calls back `ConfirmUpload` with the same key; **only now**
   does the `Attachment` aggregate get created, `virus_scan_status =
   'pending'`, and a virus-scan task enqueued (`08_background_workers.md`).
5. Until the scan completes as `clean`, `FileStorageQueryPort` does not
   return a download URL for that attachment to any caller.

This keeps the API server out of the (potentially large) file-transfer
path entirely — it only ever issues and validates short-lived URLs and
tracks metadata, which is what lets storage throughput scale independently
of API server capacity.

### Storage key naming convention

`{organization_id}/{owner_type}/{owner_id}/{attachment_id}/{filename}` —
partitioning by `organization_id` first means a future per-tenant bucket
migration or lifecycle policy can be scoped with a simple prefix, without
touching application code (an infrastructure-only change, consistent with
this document set's general preference for decisions that stay
reversible).

### Bucket strategy

One logical bucket (`drassist`, per `.env.example` in the Turn 1 scaffold)
today; the storage key convention above already makes a future move to
per-tenant buckets (for larger enterprise customers requiring storage
isolation) a `file_storage`-module-only change — no other module
references a bucket name directly, only the `FileStorageCommandPort`
interface.
