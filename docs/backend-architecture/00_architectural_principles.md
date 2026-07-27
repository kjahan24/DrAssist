# Architectural Principles

This document explains **why** the backend is shaped the way it is, before
any folder or file is introduced. Every later document in this set is a
consequence of the decisions made here. No implementation code appears
anywhere in this documentation set — folder trees, interface *signatures*
(names, parameters, return types — no bodies), and configuration snippets
are used to communicate structure, never behavior.

## The governing idea: Modular Monolith of Clean Architecture slices

DrAssist is built as **one deployable service** (a monolith — one codebase,
one process family, one database today) that is internally partitioned into
**13 independent modules**, each of which is internally structured as its
own miniature **Clean Architecture** (Domain → Application → Infrastructure
→ API). This is deliberate, not a compromise:

- A true microservices architecture on day one would impose distributed-
  systems cost (network calls, eventual consistency, service discovery,
  distributed tracing, N deployment pipelines) on a team and product that
  doesn't yet have the scale or org structure to justify it.
- A conventional (non-modular) monolith — one big `models.py`, one big
  `services.py` — accumulates hidden coupling between unrelated concerns
  (e.g. billing code silently depending on clinical-note internals) until
  it can neither be safely changed nor safely split apart.
- The modular monolith gets the operational simplicity of the first option
  and, if the module boundaries are enforced with the same discipline as a
  real service boundary, the optionality of the second — see
  `13_microservices_migration_path.md` for exactly how that optionality is
  cashed in later.

Every principle below exists in service of one property: **a module's
internals can change freely; a module's boundary can only change
deliberately.**

---

## 1. Clean Architecture (the layer rule)

Four concentric layers, present inside *every* module (see
`02_layer_responsibilities.md` for the full per-layer breakdown):

```
┌─────────────────────────────────────────────┐
│  API (interface adapters)                    │  FastAPI routers, Pydantic
│  ┌─────────────────────────────────────────┐ │  schemas, DI wiring
│  │  Infrastructure                          │ │  SQLAlchemy repos, Celery
│  │  ┌───────────────────────────────────┐  │ │  adapters, AI/Storage
│  │  │  Application                       │  │ │  clients
│  │  │  ┌───────────────────────────┐    │  │ │
│  │  │  │  Domain                    │    │  │ │
│  │  │  │  entities, value objects,  │    │  │ │
│  │  │  │  domain events, domain     │    │  │ │
│  │  │  │  services, repository      │    │  │ │
│  │  │  │  interfaces                │    │  │ │
│  │  │  └───────────────────────────┘    │  │ │
│  │  │  use cases, DTOs, ports            │  │ │
│  │  └───────────────────────────────────┘  │ │
│  └─────────────────────────────────────────┘ │
└─────────────────────────────────────────────┘
```

**The Dependency Rule:** source code dependencies point only inward.
Domain knows nothing about Application. Application knows nothing about
Infrastructure or API. Infrastructure and API know about Application and
Domain (through interfaces the inner layers define), never the reverse.
Concretely: `domain/` never imports FastAPI, SQLAlchemy, Celery, redis,
qdrant-client, or minio — it is pure Python + the standard library. This is
what makes the domain testable in microseconds and portable to a different
web framework, ORM, or even language boundary without a rewrite.

Outer layers depend on **abstractions** the inner layers declare (Python
`Protocol`/`ABC` interfaces for repositories, gateways, and the Unit of
Work), and the concrete implementation is supplied at the composition root
— this is the Dependency Inversion Principle (the "D" in SOLID) applied at
the architecture level, not just the class level.

## 2. Domain-Driven Design (DDD)

- **Bounded contexts ≈ modules.** Each of the 13 modules is a bounded
  context: it owns a specific, consistent vocabulary (a "Visit" in the
  Visit module and any conceptual overlap in, say, Patient History, are
  related but not the same object — Patient History holds a denormalized,
  eventually-consistent *projection*, not the Visit aggregate itself).
- **Aggregates enforce invariants.** Each module's domain layer defines one
  or more aggregate roots (e.g. `Patient` is the aggregate root for
  `PatientContact`/`PatientAllergy`/`PatientMedication`/`PatientCondition`
  — see `03_module_architecture.md`). All writes to the aggregate's child
  entities go through the aggregate root, which is the only object a
  repository loads and saves as a unit — this is what keeps "a patient
  can't have two primary contacts" enforceable in one place instead of
  scattered across call sites.
- **Value objects are immutable and self-validating.** `EmailAddress`,
  `MedicalRecordNumber`, `DateRange`, `Money` — constructing one with an
  invalid value raises immediately, so "an invalid state" is unrepresentable
  once past the constructor, not merely "usually checked."
- **Domain events** are the connective tissue *between* bounded contexts
  (see `10_module_communication.md`). A module publishes what happened in
  its own vocabulary (`PatientAllergyRecorded`); it does not know or care
  who, if anyone, is listening.
- **Ubiquitous language.** Class and method names mirror how clinicians and
  admins actually talk about the domain (`CheckInPatient`, not
  `UpdateVisitStatus`) — see `11_standards_and_conventions.md`.

## 3. SOLID, applied at both class and module scale

| Principle | Class-level application | Module/architecture-level application |
|---|---|---|
| **S**ingle Responsibility | One use case class does one thing (`RegisterPatient`, not `PatientService.do_everything`) | One module owns one bounded context; it does not also own a neighboring concern "for convenience" |
| **O**pen/Closed | New AI provider = new adapter class implementing an existing port, zero changes to callers | New notification channel = new adapter behind `NotificationChannelPort`, zero changes to the modules that trigger notifications |
| **L**iskov Substitution | Any `PatientRepository` implementation (real SQLAlchemy, in-memory fake for tests) is interchangeable | Any module's in-process facade implementation is interchangeable with a future network-client implementation of the same interface — the literal mechanism microservices extraction relies on |
| **I**nterface Segregation | `PatientRepository` doesn't force a `Doctor`-shaped method onto callers that only need patient data | A module's public interface (see `10_module_communication.md`) exposes only what other modules actually need — not "the whole domain model," which would recreate tight coupling through the back door |
| **D**ependency Inversion | Use cases depend on `AbstractPatientRepository`, not `SqlAlchemyPatientRepository` | Modules depend on each other's *interfaces* (published in a `public/` package), never on each other's `infrastructure/` or `domain/` internals |

## 4. Repository Pattern

Every aggregate root has exactly one repository interface, declared in that
aggregate's `domain/` package, implemented in that module's
`infrastructure/` package. A repository's contract is expressed in domain
terms (`get_by_id`, `get_by_medical_record_number`, `add`), never in SQL or
ORM terms — no `session`, `query`, or SQL fragment ever appears in a
repository *interface* signature, only in its concrete implementation. Full
treatment, including why repositories are aggregate-scoped rather than
table-scoped, is in `04_repository_and_service_patterns.md`.

## 5. Service Layer (Application Services / Use Cases)

"Service Layer" (a term from Fowler's *Patterns of Enterprise Application
Architecture*) and "Use Case" (a term from Clean Architecture) name the same
concept in this system: **one class per business operation**, orchestrating
domain objects, repositories, and the Unit of Work to fulfil exactly one
request from the outside world (an API call, a Celery task, an admin
script). This is distinct from two things it is often confused with:

- **Domain Services** (inside `domain/`) — pure business *policy* with no
  I/O (e.g. "is this drug interaction combination dangerous, given these
  two medications" — a pure function of domain data already in memory).
- **Infrastructure Gateways/Adapters** (inside `infrastructure/`) — clients
  for external systems (AI providers, storage, email) with no business
  rules of their own, only a technical contract to fulfil.

An Application Service **may** call a Domain Service and **may** call a
Gateway through its port, but business orchestration logic lives only in
the Application Service. See `04_repository_and_service_patterns.md`.

## 6. Dependency Injection

FastAPI's `Depends()` is the request-scoped wiring mechanism; a small,
explicit **composition root** (`app/core/container.py` plus one
`container.py` per module) is where abstract interfaces are bound to
concrete implementations at process startup. No module reaches for a
concrete class directly — everything arrives through a constructor
parameter typed as an interface. Full design in
`05_dependency_injection_and_lifecycle.md`.

## 7. Unit of Work

One transaction boundary per request (or per Celery task), shared by every
repository that participates in that request, exposing only `commit()`,
`rollback()`, and (implicitly, via `async with`) `begin`. The UoW is
intentionally **not** a god-object holding a reference to every repository
in the system (a common but module-boundary-eroding textbook
simplification) — see `04_repository_and_service_patterns.md` for the
specific shape used here and why.

## 8. Modular Monolith — the module boundary rule

The single rule that makes everything above hold together at scale:

> A module may freely import anything inside itself, and may freely import
> `app/shared/` and `app/core/`. A module may **only** import another
> module's `public/` package — never that module's `domain/`,
> `application/` (beyond `public/`), or `infrastructure/`.

This rule is enforced by CI tooling (`import-linter`), not just convention
— see `11_standards_and_conventions.md`. It is the single decision that
determines whether "modular monolith" is a real architecture or just an
aspiration written in a README.
