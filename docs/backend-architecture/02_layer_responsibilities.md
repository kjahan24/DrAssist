# Layer Responsibilities

Every module (`app/modules/<name>/`) is internally organized into the same
four layers, plus the two horizontal layers (`core/`, `shared/`) that sit
outside any single module. This document defines what belongs — and,
importantly, what does **not** belong — in each.

---

## Domain layer (`modules/<name>/domain/`)

**Responsibility:** the module's business rules and vocabulary, expressed
in plain Python with zero framework dependencies.

| Contains | Does not contain |
|---|---|
| Entities and aggregate roots (`Patient`, `Visit`) | SQLAlchemy models, `Column()`, table names |
| Value objects (`MedicalRecordNumber`, `BloodType`) | Pydantic `BaseModel` (that's an API/DTO concern) |
| Domain events (`PatientRegistered`) | Anything that publishes/dispatches an event (that's infrastructure) |
| Domain services — pure, stateless policy functions operating only on data already in memory (e.g. "does this new medication conflict with an existing allergy, given both are already loaded") | Anything that queries a database, calls an API, or reads a clock/random source directly (inject these as parameters instead, to keep the function pure and testable) |
| Repository **interfaces** (`PatientRepository` as an `abc.ABC`/`typing.Protocol`) | Repository **implementations** |
| Domain-specific exceptions (`DuplicateMedicalRecordNumberError`) | HTTP status codes (that translation happens in `api/` or the shared exception handler) |

**Key property:** a domain object's constructor and mutating methods make
invalid states unrepresentable. E.g. `Visit.check_in()` raises a domain
exception if called on a visit whose `status` isn't `scheduled` — this rule
lives once, in the entity, and is enforced identically whether the caller
is the API, a Celery task, or a data-fix script. This is why "don't
implement business logic" for this document's own output is unambiguous:
business *rules* belong here, in code, not in this documentation.

---

## Application layer (`modules/<name>/application/`)

**Responsibility:** orchestrate one use case at a time — load domain
objects via repository interfaces, invoke domain behavior, persist via the
Unit of Work, publish resulting domain events. This is the **Service
Layer** referenced in the brief; "use case" and "application service" are
the same concept here (see `00_architectural_principles.md §5`).

| Contains | Does not contain |
|---|---|
| One class per use case (`use_cases/register_patient.py`) | Business rules that belong on the entity (a use case *calls* `patient.record_allergy(...)`, it does not reimplement the allergy-conflict check inline) |
| Input/Output DTOs (`dto.py`) — plain dataclasses/Pydantic models distinct from both domain entities and API schemas | SQL, ORM session usage, HTTP request/response objects |
| Application-level exceptions that wrap/translate domain exceptions for the outside world | Direct instantiation of infrastructure classes (`SqlAlchemyPatientRepository()`) — always received via constructor injection |
| Entity ↔ DTO mappers | Entity ↔ ORM-model mapping (that's infrastructure's job) |
| Ports this module needs from *other* modules, expressed as interfaces (rare — prefer domain events; see `10_module_communication.md`) | Direct imports of another module's `domain/` or `infrastructure/` |

A use case's constructor signature is its complete list of dependencies —
repositories (by interface), the Unit of Work, the Event Bus, and any
cross-module ports it needs — nothing is reached for globally.

---

## Infrastructure layer (`modules/<name>/infrastructure/`)

**Responsibility:** fulfil the interfaces the Domain and Application layers
declared, using real technology.

| Contains | Does not contain |
|---|---|
| SQLAlchemy ORM models (`models.py`) — the *persistence* shape, which may differ from the *domain* shape | Business rules (a model is a mapping, not a policy) |
| Concrete repository classes implementing the module's domain repository interfaces | Anything the Application layer should be orchestrating instead |
| ORM ↔ domain-entity mappers | — |
| Adapters for external systems this module specifically owns (e.g. the `ai` module's Gemini/Whisper/PaddleOCR clients, the `file_storage` module's MinIO adapter) | Adapters for systems shared across modules — those live in the top-level `app/infrastructure/` and are injected in, not reimplemented per module |
| Celery task *registration* glue where a module needs it (the task body itself just calls into `application/use_cases/`) | Business logic inside the Celery task function itself |

Infrastructure is the only layer allowed to import third-party
SDKs/drivers (`sqlalchemy`, `redis`, `qdrant_client`, `minio`,
`google.generativeai`) directly.

---

## API layer (`modules/<name>/api/`)

**Responsibility:** translate HTTP ⇄ Application layer. Per this
project's current phase, **no endpoint bodies exist yet** — this layer's
architecture is documented so the *shape* is correct when endpoints are
implemented, not to implement them now.

| Contains | Does not contain |
|---|---|
| `router.py` — an `APIRouter()` instance, ready to `include_router` endpoint modules into, matching the pattern already established in `app/api/v1/router.py` | Endpoint function bodies with business logic |
| `schemas.py` — Pydantic request/response models, inheriting the shared `ORJSONModel` base (`app/schemas/base.py`, existing) | Domain entities used directly as response models (always map through a DTO/schema, so the wire format can evolve independently of the domain model) |
| `dependencies.py` — FastAPI `Depends()` provider functions that construct this module's use cases with their dependencies resolved | Direct construction of infrastructure classes inline in a route function |

A route handler's job, when implemented, is exactly three steps: validate
input (Pydantic, automatic), call one use case, map the result to a
response schema. Any handler doing more than that is a sign business logic
leaked into the wrong layer.

---

## Core (`app/core/`)

**Responsibility:** process-wide technical concerns with **no domain
knowledge whatsoever** — configuration, logging setup, the base exception
hierarchy, and security *primitives* (JWT encode/decode, password hashing,
encryption helpers, permission-string constants). `core/` does not know
what a "Patient" is; it knows what a "JWT" or a "log level" is. Every
module and `shared/` depends on `core/`; `core/` depends on nothing inside
the application. See `06_configuration_logging_exceptions.md` and
`07_security_layer.md`.

## Shared (`app/shared/`)

**Responsibility:** the DDD "shared kernel" — building blocks every module
needs but that don't belong to any one bounded context: base `Entity`/
`AggregateRoot`/`ValueObject` classes, the `DomainEvent` base, the
`UnitOfWork` and `EventBus` interfaces (and their one concrete
implementation each, since — unlike modules — there is intentionally only
one transaction mechanism and one event bus in this system), and truly
universal value objects (`EmailAddress`, `PhoneNumber`, `Address`,
`DateRange`, `Money`). A change to `shared/` is a change every module
feels — it is kept deliberately small and stable; module-specific value
objects (`MedicalRecordNumber`, `BloodType`) live inside their owning
module's `domain/`, not here, precisely to keep this shared surface from
becoming a dumping ground.

## Where cross-cutting *infrastructure* clients live

`app/infrastructure/` (top-level, outside `shared/`) holds the singleton
technical clients genuinely shared by multiple modules — the DB engine and
session factory, the Redis connection, the Qdrant client, the MinIO client,
and the raw AI provider SDK clients (existing from the Turn 1 scaffold).
These are instantiated once at startup (`app/core/container.py`, see
`05_dependency_injection_and_lifecycle.md`) and injected into whichever
module's infrastructure layer needs them — a module never constructs its
own second Redis connection pool.
