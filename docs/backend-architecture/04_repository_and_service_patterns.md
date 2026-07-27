# Repository & Service Patterns

Covers: repository interfaces, repository implementations, service
interfaces, service implementations, the Unit of Work pattern, and the
validation layer. All signatures shown below are **contracts** (name,
parameters, return type) — no method bodies, per the "no implementation
code" instruction.

---

## Repository interfaces (`modules/<name>/domain/repositories.py`)

**Rule: one repository per aggregate root, not per table.** `Patient` has
one `PatientRepository`, even though saving a patient may touch five
tables (`patients` + its four child-entity tables) — the repository's job
is to make the aggregate's persistence atomic and invisible to the
application layer, not to expose table-shaped CRUD. There is no
`PatientAllergyRepository` — allergies are only ever reached through
`Patient`.

A repository interface is expressed **entirely in domain vocabulary**: no
`Session`, no SQL, no ORM type ever appears in its signature.

Canonical shape (illustrative — every module's aggregate repository
follows this contract shape, with domain-specific lookup methods added):

| Method | Parameters | Returns | Purpose |
|---|---|---|---|
| `get_by_id` | `entity_id: UUID` | `Patient \| None` | Load the full aggregate |
| `add` | `patient: Patient` | `None` | Stage a new aggregate for persistence |
| `list` | `organization_id: UUID, offset: int, limit: int` | `list[Patient]` | Paginated listing |
| *(module-specific)* e.g. `get_by_medical_record_number` | `organization_id: UUID, mrn: str` | `Patient \| None` | Natural-key lookup |

Note there is **no `update` method** — because the repository returns the
actual aggregate object (not a copy or a DTO), the caller mutates it via
its domain methods, and the Unit of Work's `commit()` is what persists the
change (SQLAlchemy's identity map + change tracking does the diffing).
This mirrors how `AbstractRepository` was already scaffolded generically
in `app/domain/repositories/base.py` in the initial project foundation —
each module's repository interface now specializes that shape per
aggregate rather than being used generically.

**Why interfaces live in `domain/`, not `application/`:** the repository
contract is part of the aggregate's definition (Eric Evans' original
formulation) — the aggregate and the rules for retrieving/storing it as a
whole are one concept. The Application layer *depends on* this interface
but does not own it.

---

## Repository implementations (`modules/<name>/infrastructure/repositories.py`)

A concrete repository:

1. Accepts an `AsyncSession` (or, more precisely, receives the active Unit
   of Work's session — see below) via constructor injection.
2. Implements every method the domain interface declares.
3. Internally: builds a SQLAlchemy `select()`, executes it, and — this is
   the important part — **maps the ORM model to the domain entity** before
   returning it (via that module's `infrastructure/mappers.py`), and maps
   the domain entity back to ORM model attributes on `add()`. The
   Application and Domain layers never see a SQLAlchemy model instance.
4. Never calls `commit()` or `rollback()` itself — that is the Unit of
   Work's exclusive responsibility (a repository that commits its own
   transaction can't participate in a larger atomic operation coordinated
   by a use case).

**Composition over table joins for aggregate loading:** loading a
`Patient` aggregate loads `patients` plus its four child tables via
`selectinload` (or equivalent eager-loading strategy) in one repository
method — the *use case* calling `patient_repository.get_by_id(...)` never
issues a second query to "also get the allergies."

**Testing implication:** because the interface is domain-shaped, a second
implementation — an in-memory `FakePatientRepository` backed by a plain
dict — satisfies the exact same interface and is used in application-layer
unit tests instead of a real database. This is the concrete payoff of the
Repository Pattern + DIP combination; see `12_testing_architecture.md`.

---

## Service interfaces & implementations

"Service interface" takes two distinct, deliberate forms in this
architecture — conflating them is a common source of over-engineering, so
they're kept explicitly separate:

### A. The internal use-case contract

Every application service (use case) implements the same generic shape,
already scaffolded in the project foundation
(`app/application/use_cases/base.py`, now relocated to
`app/shared/application/use_case.py`):

| Contract | Shape |
|---|---|
| `UseCase[InputDTO, OutputDTO]` | one method, `execute(input_dto: InputDTO) -> OutputDTO` |

A concrete use case (e.g. `RegisterPatient`) is **not** further hidden
behind a bespoke `RegisterPatientInterface` ABC — with exactly one
production implementation and tests that fake its *dependencies* rather
than the use case itself, an extra interface layer here would be
indirection without payoff (a violation of YAGNI, not an application of
DIP). The generic `UseCase` contract is what the API layer's dependency
providers and Celery task wrappers type against, which is sufficient
substitutability for this layer.

### B. Module public service interfaces (the "real" service interfaces)

The `Port` interfaces defined in each module's `public/interfaces.py` —
`PatientQueryPort`, `AISessionCommandPort`, `PermissionCheckPort`, and so
on, catalogued per-module in `03_module_architecture.md` — **are** the
service interfaces the brief's items #17/#18 are asking for in the sense
that matters architecturally: they are the contracts *other* modules and
the API layer depend on, with a concrete implementation
(`modules/<name>/public/facade.py`, wiring to the module's internal use
cases) bound at the composition root. Unlike (A), these genuinely benefit
from being interfaces, because a second implementation is a real, planned
possibility — a future network client standing in for the in-process
facade during microservices extraction (`13_microservices_migration_path.md`).

**Rule of thumb applied throughout this design:** introduce a formal
interface where more than one implementation is plausible (repositories,
module public facades, AI provider adapters, notification channels).
Don't introduce one where exactly one implementation will ever exist
(a specific use case's own internal shape) — the generic `UseCase` base is
sufficient there.

---

## Unit of Work pattern

**Interface** (`app/shared/application/unit_of_work.py`):

| Member | Shape | Purpose |
|---|---|---|
| `__aenter__` / `__aexit__` | async context manager | Transaction boundary — begin on enter, rollback-on-exception on exit |
| `commit()` | `async () -> None` | Persist all staged changes and publish collected domain events (see below) |
| `rollback()` | `async () -> None` | Discard staged changes |
| `flush()` | `async () -> None` | Push pending changes to the DB without committing (needed when a use case needs a generated ID mid-operation) |

**Deliberate design choice — no repository attributes on the UoW.** The
common textbook Unit of Work (e.g. from *Architecture Patterns with
Python*) exposes repositories as attributes: `uow.patients`, `uow.visits`.
That works cleanly for a single-module application; in a 13-module
modular monolith it would either (a) force one god-UoW class that knows
about every module's repository — a direct violation of the module
boundary rule in `00_architectural_principles.md §8` — or (b) force each
module to define its own UoW subclass, which then still needs a
transaction shared with other modules' UoW instances for cross-module
transactional use cases.

This design instead keeps `UnitOfWork` narrowly responsible for **only the
transaction boundary**, and a use case's constructor receives both the
`UnitOfWork` and the specific repositories it needs as separate,
sibling dependencies — all constructed against the *same* underlying
`AsyncSession` for a given request by the composition root (see
`05_dependency_injection_and_lifecycle.md`). A use case that only touches
its own module's aggregate takes one repository; the rare use case that
must stay atomic across two modules' tables in the *same* physical
database (there are none identified in this design — see the "aggregates
reference each other by ID only" rule in `03_module_architecture.md`,
which is precisely what avoids needing this) would take both repositories
and the one shared `UnitOfWork`, and still commit exactly once.

**Domain event publication is tied to `commit()`, not to the use case
directly:** the UoW implementation collects domain events recorded on any
aggregate touched during the transaction (`aggregate.pull_events()`) and
hands them to the `EventBus` **only after a successful commit** — this
guarantees a subscriber (e.g. Notification) never reacts to an event whose
originating transaction subsequently rolled back. See
`10_module_communication.md`.

---

## Validation layer

Three tiers, each with a distinct responsibility — a value should never be
validated only at the tier closest to the bug, because the same use case
can be entered from more than one direction (HTTP today; a Celery task or
an admin script tomorrow):

| Tier | Where | Validates | Example |
|---|---|---|---|
| 1. Syntactic | `modules/<name>/api/schemas.py` (Pydantic v2) | Shape: types, required fields, string/number formats, enum membership | "`date_of_birth` must be an ISO date"; "`severity` must be one of the four allergy severity values" |
| 2. Application/business | `modules/<name>/application/` (inside the use case, or a dedicated `validators.py` when logic is reused by >1 use case) | Rules that need to consult other data — usually via a repository or another module's query port | "This medical record number is already in use for this organization"; "The referenced doctor exists and is accepting patients" |
| 3. Domain invariant | `modules/<name>/domain/` (entity/value-object constructors and mutating methods) | Rules that must hold **no matter the entry point** — the ones that make an invalid object impossible to construct at all | "A `Visit` cannot transition to `completed` without first being `checked_in`"; "A `BloodType` value object rejects any string outside the known set" |

Tier 3 is the load-bearing one: even if Tier 1 or Tier 2 were bypassed
(a bug, a direct script, a future gRPC entrypoint that forgets to
revalidate), Tier 3 still holds, because it's not possible to *construct*
the invalid domain object in the first place. Tiers 1 and 2 exist to fail
fast with a good error message before reaching the domain, not because
the domain trusts them.
