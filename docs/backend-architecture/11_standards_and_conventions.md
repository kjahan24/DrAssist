# Folder Responsibilities, Coding Standards, Naming Conventions, Import Rules

## Folder responsibilities (consolidated index)

Every folder's responsibility is documented in depth where it's most
relevant; this table is the single lookup point.

| Folder | Full detail in |
|---|---|
| `app/core/` | `02_layer_responsibilities.md`, `06_configuration_logging_exceptions.md`, `07_security_layer.md` |
| `app/shared/` | `02_layer_responsibilities.md`, `04_repository_and_service_patterns.md`, `10_module_communication.md` |
| `app/modules/<name>/domain/` | `02_layer_responsibilities.md`, `04_repository_and_service_patterns.md` |
| `app/modules/<name>/application/` | `02_layer_responsibilities.md`, `04_repository_and_service_patterns.md` |
| `app/modules/<name>/infrastructure/` | `02_layer_responsibilities.md`, `04_repository_and_service_patterns.md`, `09_ai_gateway_and_storage.md` |
| `app/modules/<name>/api/` | `02_layer_responsibilities.md`, `05_dependency_injection_and_lifecycle.md` |
| `app/modules/<name>/public/` | `10_module_communication.md` |
| `app/modules/<name>/container.py` | `05_dependency_injection_and_lifecycle.md` |
| `app/infrastructure/` (top-level) | `01_folder_structure.md`, `02_layer_responsibilities.md` |
| `app/api/` | `01_folder_structure.md`, `05_dependency_injection_and_lifecycle.md` |
| `app/middlewares/` | `05_dependency_injection_and_lifecycle.md` |
| `app/workers/` | `08_background_workers.md` |
| Per-module content (all 13) | `03_module_architecture.md` |
| `tests/` | `12_testing_architecture.md` |

## Coding standards

- **Domain purity is non-negotiable and lint-enforced, not just reviewed.**
  `domain/` packages may import only the standard library, `app/shared/domain/`,
  and other classes within the same module's `domain/` package — no
  FastAPI, SQLAlchemy, Celery, redis, or any third-party SDK. Enforced by
  `import-linter` (see below), not left to code review discipline alone.
- **One concept per file** for domain entities, use cases, and repository
  implementations — a use case named `RegisterPatient` lives in
  `register_patient.py`; it is not appended to a growing
  `patient_use_cases.py`. This is what keeps a 13-module system navigable
  as each module's use-case count grows into the dozens.
- **Functions and methods are typed everywhere** (parameters and return
  values) — this project targets Python 3.12+ specifically so modern
  generic syntax and precise typing are available throughout, matching the
  strict `mypy` configuration already established in the Turn 1 scaffold
  (`backend/pyproject.toml`).
- **No bare `except:`** and no catching `Exception` except at the two
  designated boundary points (the outermost API exception handler, and a
  Celery task's top-level retry logic) — everywhere else, catch the
  specific exception type you can actually handle.
- **Entities are never mutated from outside their own methods.** A use
  case calls `patient.record_allergy(...)`; it does not do
  `patient.allergies.append(PatientAllergy(...))` — the latter bypasses
  whatever invariant the entity's method exists to enforce.
- **No business logic in `__init__.py`.** Package `__init__.py` files
  exist for import aggregation only (as already established for
  `app/infrastructure/database/models/__init__.py` in the Turn 1 scaffold)
  — never a place where side effects or logic hide.
- **Docstrings explain *why*, not *what*** — a method named
  `record_allergy` doesn't need a docstring saying "records an allergy";
  it needs one (only) if there's a non-obvious invariant or reason behind
  its behavior, consistent with the project's general documentation
  philosophy.

## Naming conventions

| Element | Convention | Example |
|---|---|---|
| Module package name | `snake_case`, singular concept | `patient`, `clinical_note` |
| Domain entity / aggregate root | `PascalCase` noun | `Patient`, `Visit`, `AiSession` |
| Value object | `PascalCase` noun, immutable | `MedicalRecordNumber`, `BloodType` |
| Domain event | `PascalCase`, past tense | `PatientRegistered`, `VisitCompleted` |
| Domain exception | `PascalCase`, ends in `Error` | `DuplicateMedicalRecordNumberError` |
| Use case / application service | `PascalCase`, imperative verb phrase | `RegisterPatient`, `ScheduleVisit`, `FinalizeSoapNote` |
| Repository interface | `PascalCase`, `<AggregateName>Repository` | `PatientRepository` |
| Repository implementation | `SqlAlchemy<AggregateName>Repository` | `SqlAlchemyPatientRepository` |
| Module public port | `PascalCase`, `<Capability>Port` | `PatientQueryPort`, `AISessionCommandPort` |
| Module public facade (implementation) | `<ModuleName>Facade` | `PatientFacade` |
| Infrastructure adapter (external system) | `PascalCase`, `<Provider><Capability>` | `GeminiClient`, `MinioStorageAdapter` |
| Pydantic API schema | `PascalCase`, `<Noun><Request\|Response>` | `RegisterPatientRequest`, `PatientResponse` |
| DTO (application-layer, not API) | `PascalCase`, `<Noun>DTO` | `PatientSummaryDTO` |
| Celery task function | `snake_case`, verb phrase matching its use case | `run_transcription`, `send_notification` |
| Module folders | fixed 5-part shape | `domain/`, `application/`, `infrastructure/`, `api/`, `public/` |

**No `I` prefix on interfaces** (`IPatientRepository` is avoided) —
Python's convention favors the interface and its implementation being
distinguishable by role and location (an `ABC`/`Protocol` in `domain/`,
concrete classes in `infrastructure/`), not Hungarian notation.

## Import rules

Enforced mechanically via `import-linter` (`.importlinter` config at the
repo root, run in CI alongside `ruff`/`mypy`/`pytest`), not left to
convention alone. Two contract types cover every rule in this document
set:

**1. Layered architecture contract, applied inside every module** — the
Dependency Rule from `00_architectural_principles.md §1`:

```ini
[importlinter:contract:module-layers]
name = Clean Architecture layers within every module
type = layers
layers =
    app.modules.*.api
    app.modules.*.infrastructure
    app.modules.*.application
    app.modules.*.domain
```

(`import-linter`'s `layers` contract type enforces that each layer may
only import from layers below it in the list — exactly the inward-only
Dependency Rule.)

**2. Independence contract, applied across modules** — the module
boundary rule from `00_architectural_principles.md §8`:

```ini
[importlinter:contract:module-independence]
name = Modules may only import each other's public package
type = independence
modules =
    app.modules.authentication
    app.modules.organization
    app.modules.doctor
    app.modules.patient
    app.modules.visit
    app.modules.clinical_note
    app.modules.soap_note
    app.modules.patient_history
    app.modules.lab_report
    app.modules.ai
    app.modules.audit
    app.modules.file_storage
    app.modules.notification
```

The `independence` contract type would, by default, forbid *any*
cross-module import — which is one notch stricter than this design
actually wants (facade calls through `public/` are allowed). The
practical CI setup adds a scoped `forbidden` contract per module pair
instead, allowlisting only `<module>.public` as an importable subpath from
other modules (`import-linter` supports this via its `forbidden` contract
type targeting `app.modules.<x>.domain`, `.application`, and
`.infrastructure` specifically, while leaving `.public` unrestricted) —
the effect is: **a broken build the moment any module reaches past
another module's `public/` package**, which is the enforcement this
architecture depends on to remain true over time rather than degrading
into a conventional monolith as the codebase and team grow.

A third, simpler rule needs no tool: **`app/shared/` and `app/core/` are
never allowed to import from `app/modules/`** — dependencies point one
way, from modules inward to the shared kernel, never the reverse. This is
covered by the same `layers` contract mechanism, with `app.shared`/
`app.core` positioned as the lowest layer.
