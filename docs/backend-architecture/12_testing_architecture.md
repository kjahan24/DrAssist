# Testing Architecture

Four test kinds, each targeting a different layer boundary, mirrored in
`tests/` by kind first, then by module (`tests/<kind>/modules/<name>/`) —
not mirrored by source folder 1:1, because a single use case's behavior is
usually verified from more than one kind of test with different scope.

## 1. Unit tests — Domain and Application layers

**Target:** `domain/` and `application/` in isolation, no I/O whatsoever.

- **Domain tests** construct entities/value objects directly and assert
  on their behavior and invariants — "does `Visit.check_in()` raise
  `InvalidVisitStatusTransitionError` when called on a `completed` visit."
  These are the fastest, most numerous tests in the suite (pure Python,
  microseconds each) and are the primary regression protection for
  business rules, matching the "domain purity" principle in
  `00_architectural_principles.md`.
- **Application tests** exercise a use case's orchestration logic with
  **fake** repositories and a **fake** Unit of Work — an in-memory class
  implementing the exact same domain-defined interface a real
  `SqlAlchemyPatientRepository` implements (`04_repository_and_service_patterns.md`).
  This is the concrete return on investment from the Repository Pattern +
  Dependency Inversion: a use case's orchestration (did it call the right
  methods, in the right order, and publish the right events) is fully
  testable without a database, a running Postgres container, or network
  access.
- **Fakes over mocks, as the default.** A hand-written in-memory
  `FakePatientRepository` (backed by a dict) is preferred over a
  `unittest.mock.Mock()` wherever feasible — a fake actually behaves like
  the real thing (round-trips data, enforces the same interface shape at
  call time), so a test using it breaks when the *behavior* contract
  changes, not merely when a specific method-call assertion goes stale.
  Mocks remain appropriate for verifying a specific interaction happened
  (e.g. "the `EventBus.publish` was called with exactly this event"),
  where the point genuinely is the call itself, not stateful behavior.

## 2. Integration tests — Infrastructure layer

**Target:** the concrete repository implementations, the real database,
and RLS policy enforcement — run against a real Postgres 16 instance
(via the project's Docker Compose test profile or `testcontainers`), never
against SQLite or a mocked engine (a different database engine would
validate different SQL semantics than production runs on).

- **Repository round-trip tests:** save an aggregate, load it back by a
  fresh repository instance, assert equality — catches ORM-mapping bugs
  (`infrastructure/mappers.py`) that unit tests, which never touch the
  ORM, structurally cannot catch.
- **Migration tests:** `alembic upgrade head` from empty, then `downgrade
  base` and back — already specified in
  `../database/08_migration_strategy.md §8`; this project's CI treats it
  as one integration-test-suite entry, not a separate pipeline.
- **RLS tests — the highest-priority integration test in this system:**
  as the actual non-superuser application database role, with two
  different `app.current_organization_id` values set across two sessions,
  assert tenant A can never read or write tenant B's rows for **every**
  tenant-scoped table — directly verifying the multi-tenant isolation
  guarantee from `../database/00_overview.md` and
  `07_security_layer.md §3` at the only layer that actually matters for
  it (the database itself, not application code that could regress
  silently).
- **Constraint tests:** each documented `CHECK`/`UNIQUE` constraint
  (`../database/09_best_practices_and_performance.md §1.5`) has a
  corresponding test asserting the invalid case is actually rejected.

## 3. Contract tests — Module public interfaces

**Target:** each module's `public/facade.py`, tested through its
interface exactly as another module would call it (not through its
internal use cases or repositories directly).

- **Purpose:** guarantee a module's advertised behavior actually matches
  what other modules depend on — e.g. Notification's test suite includes
  a contract test asserting `PatientQueryPort.get_patient_summary`
  returns a value shaped exactly as `PatientSummaryDTO` promises, run
  against the *real* Patient module (not a fake) so a Patient-module
  change that silently breaks the contract is caught in Patient's own CI
  run, not discovered later inside Notification's tests.
- **Direct payoff for `13_microservices_migration_path.md`:** these are
  precisely the tests that get pointed at a real network client instead
  of the in-process facade on the day a module is extracted — if they
  pass unchanged against both, the extraction preserved the contract.

## 4. End-to-end tests — full request lifecycle

**Target:** real HTTP requests (via `httpx.AsyncClient` against the actual
FastAPI app, per the existing `tests/conftest.py` pattern from the Turn 1
scaffold) through the entire stack — middleware, DI resolution, permission
checks, a real (test) database, and the real event bus — verifying the
request lifecycle documented in `05_dependency_injection_and_lifecycle.md`
end to end. Kept deliberately few in number (the "testing pyramid" — many
unit tests, fewer integration tests, fewer still contract tests, fewest
e2e tests) covering only the highest-value user-facing flows, since these
are the slowest tests and the most expensive to maintain when UI/API shape
changes.

## Test doubles summary

| Test kind | Repository | Unit of Work | External systems (AI/Storage/Notification) |
|---|---|---|---|
| Unit (Application) | In-memory fake | In-memory fake (no-op commit) | Fake implementing the relevant `Port` |
| Integration | Real (`SqlAlchemy*Repository`) | Real, against a test Postgres | Fake or a sandboxed provider account, never a real charge/send |
| Contract | Real module, real repository | Real | Fake at the module's own external boundary only |
| E2E | Real | Real | Fake — e2e tests validate the platform's own behavior, not third-party providers' |

## CI integration

Extends the existing pipeline (`.github/workflows/ci.yml` from the Turn 1
scaffold: `ruff check`, `ruff format --check`, `mypy`, `pytest`) with:

- `import-linter` run as its own step (`11_standards_and_conventions.md`)
  — a module-boundary violation fails the build before tests even run,
  since it's a cheaper and more fundamental check.
- Unit tests run against every push (fast, no external services needed).
- Integration/contract/RLS tests run against a Postgres 16 service
  container in CI (already the pattern for the migration round-trip test
  in `../database/08_migration_strategy.md §8`).
- E2E tests run on the same CI job, after integration tests pass, using
  the same ephemeral database.
- Coverage is tracked per layer, not just overall — a drop in Domain-layer
  coverage specifically is treated more seriously than a drop in
  Infrastructure-layer coverage, since the domain is where business-rule
  regressions are cheapest to catch and most expensive to ship.
