# Module Communication

Two mechanisms, used deliberately for different purposes — the choice
between them is not stylistic, it reflects a real difference in
consistency and coupling requirements.

## Mechanism 1: Public facade calls (synchronous, in-process)

**Use when:** the caller needs an answer *now*, within the current
transaction/request, to decide what to do next (an existence check, a
query, or a command whose result the caller immediately depends on).

- Every module exposes exactly one importable package for this:
  `modules/<name>/public/`, containing `interfaces.py` (the Port
  contracts), `dto.py` (data shapes safe to cross the boundary), and
  `facade.py`'s concrete implementation (wired at the module's
  `container.py`).
- A calling module depends on the **interface**, injected via DI — never
  on the concrete `facade.py` class, and never, under any circumstance, on
  anything under the target module's `domain/`, `application/`
  (non-public), or `infrastructure/`.
- **What crosses the boundary:** primitive values and DTOs
  (`PatientSummaryDTO`, plain UUIDs/strings/enums) — never a domain entity,
  never an ORM model. A `PatientSummaryDTO` is a deliberately narrow,
  stable shape (name, DOB, MRN — not the full `Patient` aggregate with its
  four child-entity collections), because the whole point of the public
  interface is to expose *only* what other modules legitimately need,
  per the Interface Segregation Principle applied at module scale
  (`00_architectural_principles.md §3`).
- **Transactional behavior:** a facade call made *within* a use case that
  is itself running inside a `UnitOfWork` executes inside that same
  physical transaction (same `AsyncSession`) if the called module's
  repository was constructed against it — but per the "aggregates
  reference by ID only" rule (`03_module_architecture.md`), this pattern is
  used for *reads* almost exclusively in this design; no identified use
  case requires two modules' *writes* to commit atomically together. Where
  a command does cross a facade (e.g. Doctor's `OnboardDoctor` calling
  Authentication's `RegisterUser`), the calling module accepts that if the
  second step failed after the first succeeded, compensating logic (or
  simply retrying the whole onboarding operation, since `RegisterUser` is
  idempotent on email) resolves it — not a two-phase-commit.

## Mechanism 2: Domain events (asynchronous, decoupled)

**Use when:** the caller doesn't need — and shouldn't wait for — the
answer, and the "reaction" is conceptually owned by the *other* module,
not the one where the event originated. This is the default choice for
anything reactive: notifications, audit trails, read-model projections.

### The Event Bus

`EventBus` (`app/shared/application/event_bus.py`, interface;
`app/shared/infrastructure/in_process_event_bus.py`, the one concrete
implementation today) provides:

| Member | Shape | Purpose |
|---|---|---|
| `subscribe(event_type, handler)` | registers a handler for one `DomainEvent` subclass | Called once per handler, at startup, from each subscribing module's `container.py` |
| `publish(events: list[DomainEvent])` | dispatches to every registered handler for each event's type | Called exactly once per request, by the `UnitOfWork`, **after** a successful commit (`04_repository_and_service_patterns.md`) |

- **A module publishes events without knowing who, if anyone, subscribes.**
  `Visit`'s domain layer records a `VisitCompleted` event on the
  aggregate; the `visit` module has zero import-time knowledge that
  Patient History or Notification exist. Subscriptions are registered
  centrally, at the composition root (`app/core/container.py` calls each
  module's `container.py`'s `register_subscriptions(event_bus)` during
  startup) — **not** by the publishing module importing the subscriber.
  This is the precise mechanism that keeps the dashed arrows in the
  dependency graph (`05_dependency_injection_and_lifecycle.md`) from ever
  becoming solid (import) arrows.
- **Two subscriber styles** (`08_background_workers.md`): inline
  (synchronous, same request — for fast, DB-local reactions like Patient
  History's projection) and async (the handler's body is "enqueue a
  Celery task" — for anything slow or non-critical-path, like
  Notification's email dispatch).
- **At-least-once, not exactly-once, for async subscribers.** A Celery
  task triggered by an event can retry (`08_background_workers.md`), so
  every async event handler must be idempotent — the same discipline
  already required of all Celery tasks.
- **Ordering is not guaranteed across subscribers**, and subscribers must
  not depend on it — Patient History and Notification both reacting to
  `VisitCompleted` do so independently; neither may assume the other ran
  first.

### Choosing between the two mechanisms

| Question | Facade call | Domain event |
|---|---|---|
| Does the caller need the result to proceed? | Yes | No |
| Should the caller know which modules react? | Yes (it's calling them by name) | No — reaction is decoupled by design |
| Is the reaction on the critical path of the user's request? | Yes | Usually no |
| Would adding a new reactor require changing the originating module? | Yes (new call site) | No (new subscriber registers itself) |
| Example | Visit checks `PatientQueryPort.patient_exists` before scheduling | Notification reacts to `CriticalLabResultFlagged` |

A module that finds itself wanting to *call* another module just to tell
it "something happened, go do your thing" (rather than to get an answer
back) is the signal to use an event instead — this is the check applied
when designing every cross-module interaction in `03_module_architecture.md`.

## What this buys, concretely

- **Patient History and Notification exist without Visit, Clinical Note,
  SOAP Note, Lab Report, Patient, or AI ever importing them.** Both
  modules could be deleted entirely and every other module would still
  compile and run (they'd just stop having a timeline/getting notified) —
  the clearest possible demonstration that the dependency direction is
  correct.
- **Adding module #14 later never requires modifying an existing module's
  source** if its only need is to react to existing events — it registers
  subscriptions at startup and is done. If it needs to *ask* an existing
  module something, it depends on that module's already-published `public/`
  interface, which is designed to be stable Independent of internal
  refactors.
- **This is the exact mechanism `13_microservices_migration_path.md`
  relies on** — an in-process `EventBus` swapped for a real message broker
  is an infrastructure-layer change only, because every subscriber already
  only knows about a `DomainEvent` type, never about *how* it was
  delivered.
