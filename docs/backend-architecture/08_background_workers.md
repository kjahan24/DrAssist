# Background Workers (Celery Architecture)

## Where Celery fits: the second entrypoint, not a second application

A Celery task and an API route are two different **entrypoints into the
same Application layer** — both ultimately construct and run a use case
from `modules/<name>/application/use_cases/`. A task's body is
intentionally thin:

1. Deserialize the task's arguments (plain JSON-serializable IDs/values —
   never a domain entity or ORM object, which are not safely
   serializable across the process boundary).
2. Build the same request-scoped dependencies the API layer would (a fresh
   `AsyncSession`/`UnitOfWork`, the module's repositories, via that
   module's `container.py`).
3. Call `use_case.execute(input_dto)` — the exact same class the API route
   calls.
4. Let exceptions propagate to Celery's retry mechanism (below) rather than
   swallowing them.

**This is the load-bearing design decision for this whole document:**
business logic is never written twice for "the sync path" and "the async
path." A task that duplicated a use case's logic inline would silently
drift from the API path's behavior the first time either one changed.

## Folder structure

```
app/workers/
├── celery_app.py            # Celery() instance, broker/backend config, queue/routing table
└── tasks/
    ├── ai_tasks.py            # e.g. run_transcription, run_summarization, generate_embedding
    ├── notification_tasks.py  # e.g. send_notification, render_and_dispatch
    ├── file_storage_tasks.py  # e.g. scan_attachment_for_virus, reconcile_orphaned_objects
    ├── audit_tasks.py         # e.g. record_activity (async, off the request's critical path)
    └── event_dispatch_tasks.py# the generic bridge described below
```

Each `<module>_tasks.py` file contains only task *wrappers* per the
3-step pattern above — no business logic, consistent with this module's
own domain/application layers owning that.

## Queue topology

| Queue | Carries | Rationale for separation |
|---|---|---|
| `default` | Low-volume, fast tasks (audit activity recording, misc housekeeping) | Isolated from slower queues so a burst elsewhere doesn't delay these |
| `ai_processing` | Transcription, summarization, coding-assist, embedding generation | These are the slowest, most resource-intensive tasks (model inference) and benefit from dedicated worker concurrency limits, separate autoscaling, and — later — dedicated GPU-backed workers, independent of everything else |
| `notifications` | Email/SMS/push dispatch | Third-party API calls with their own latency/rate-limit characteristics; isolating this queue means a slow email provider never delays AI processing or vice versa |
| `file_processing` | Virus scanning, orphaned-object reconciliation | I/O-bound against MinIO, independent scaling profile from AI/notifications |

Routing is declared centrally in `celery_app.py`'s `task_routes` — a task
function's queue assignment is configuration, not something the task body
decides.

## Idempotency & retries

- **Every task must be safe to run more than once.** Celery's at-least-
  once delivery model means a task can execute twice (worker crash after
  execution but before ack, a retry after a transient failure that
  actually succeeded). Tasks achieve this the same way the Application
  layer already does for any operation — by operating on stable IDs and
  using state checks / upserts rather than blind appends (e.g. "start
  transcription for AI session X" checks the session isn't already
  `completed` before proceeding, rather than assuming this is the first
  attempt).
- **Retry policy:** exponential backoff (e.g. base 2s, capped, jittered),
  a bounded `max_retries` per task class, distinguishing *transient*
  failures (network timeout to an AI provider — retry) from
  *permanent* ones (malformed input that will never succeed — do not
  retry, fail immediately and surface it).
- **Dead-letter handling:** a task that exhausts its retries is not
  silently dropped — it publishes a failure event
  (`AISessionFailed`, etc., per `03_module_architecture.md`) so the
  owning module's aggregate reflects the failure state visibly (e.g.
  `ai_sessions.status = 'failed'`, `error_message` populated) and is
  logged at `error` level for alerting. "Silently lost background work"
  is treated as a production incident category, not an accepted risk.

## Scheduled tasks (Celery Beat)

| Task | Schedule | Purpose |
|---|---|---|
| `reconcile_orphaned_objects` (File Storage) | Daily | Hard-delete MinIO objects for attachments soft-deleted past the retention window (`../database/09_best_practices_and_performance.md §1.3`) |
| `sweep_expired_sessions` (Authentication) | Hourly | Clean up expired `auth_sessions`/reset/verification tokens |
| `drop_expired_log_partitions` (Audit) | Monthly | Retention enforcement on `audit_logs`/`activity_logs` partitions (`../database/09_best_practices_and_performance.md §2.3`) |
| `anonymize_eligible_patients` (Patient) | Daily | Executes the deferred hard-anonymization step for patients past their legal retention window (`../database/09_best_practices_and_performance.md §1.3`) |

Each scheduled task follows the exact same thin-wrapper-over-a-use-case
shape as event-triggered tasks — a schedule is just a third kind of
entrypoint (alongside HTTP and domain-event-triggered), not a special
case.

## Relationship to domain events

Some Celery tasks are triggered directly (a use case enqueues one, e.g.
`ConfirmUpload` enqueues `scan_attachment_for_virus`); others are triggered
*indirectly*, as the async-dispatch mechanism for a domain event subscriber
that shouldn't run inline in the request/transaction path. The
`EventBus` (`10_module_communication.md`) supports both subscriber styles:

- **Inline (synchronous) subscribers** — run inside the same request,
  immediately after commit, for fast, DB-local work (Patient History's
  projection handler: one `INSERT`).
- **Async (task-dispatching) subscribers** — the subscriber's entire body
  is `celery_app.send_task(...)`; the actual handling logic runs later, in
  a worker, as a normal use-case-backed task. Used wherever the reaction
  involves slow I/O (Notification's email/SMS dispatch) or non-critical-
  path work (Audit's supplementary event logging) that must never add
  latency to the triggering user's request.

`event_dispatch_tasks.py` (in the tree above) holds the small number of
generic task functions this async-subscriber bridge needs — it is
infrastructure plumbing, not a 14th module.
