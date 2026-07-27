# Complete Backend Folder Structure

This extends the Clean Architecture scaffold already in the repository
(`backend/app/core/`, `backend/app/infrastructure/`, `backend/app/schemas/`,
`backend/app/middlewares/` — see `../ARCHITECTURE.md`) with the modular
monolith layer: a new `app/modules/` tree holding the 13 bounded contexts,
and a new `app/shared/` tree holding the DDD shared kernel. Nothing already
scaffolded is removed; `app/domain/`, `app/application/`, and
`app/infrastructure/database/models/` become the **shared kernel /
cross-cutting infrastructure** locations rather than the whole
application's layers — see the "Evolution note" at the end of this
document.

```
backend/
├── alembic/
│   ├── env.py
│   ├── script.py.mako
│   ├── seed_data/                       # versioned CSV fixtures for reference tables
│   └── versions/
│
├── app/
│   ├── main.py                          # ASGI app factory; composition root entrypoint
│   │
│   ├── core/                            # process-wide technical concerns — no domain knowledge
│   │   ├── config.py                    # Settings (existing)
│   │   ├── logging.py                   # structlog configuration (existing)
│   │   ├── exceptions.py                # base AppError hierarchy (existing)
│   │   ├── constants.py                 # (existing)
│   │   ├── container.py                 # NEW — app-wide composition root
│   │   └── security/
│   │       ├── jwt.py                   # token encode/decode contracts
│   │       ├── password_hashing.py      # hashing contracts
│   │       ├── encryption.py            # field-level PHI encryption contracts
│   │       └── permissions.py           # permission-string constants, RBAC evaluation contract
│   │
│   ├── shared/                          # NEW — DDD "shared kernel": reusable building blocks
│   │   ├── domain/
│   │   │   ├── entity.py                # Entity, AggregateRoot base classes
│   │   │   ├── value_object.py          # ValueObject base class
│   │   │   ├── domain_event.py          # DomainEvent base class
│   │   │   ├── specification.py         # Specification pattern base (composable query rules)
│   │   │   └── common_value_objects/    # PersonName, Address, PhoneNumber, EmailAddress, DateRange, Money
│   │   ├── application/
│   │   │   ├── use_case.py              # UseCase[TInput, TOutput] base (existing, relocated)
│   │   │   ├── unit_of_work.py          # AbstractUnitOfWork interface
│   │   │   ├── event_bus.py             # EventBus interface (publish/subscribe)
│   │   │   ├── dto.py                   # PageRequest/PageResponse and other cross-module DTOs
│   │   │   └── exceptions.py            # ApplicationError hierarchy
│   │   └── infrastructure/
│   │       ├── sqlalchemy_unit_of_work.py   # concrete UoW over an AsyncSession
│   │       ├── in_process_event_bus.py      # concrete synchronous/async in-process pub-sub
│   │       └── tenant_context.py            # contextvars-based per-request tenant/user context
│   │
│   ├── modules/                          # NEW — the 13 bounded contexts (see 03_module_architecture.md)
│   │   ├── authentication/
│   │   │   ├── domain/                   # User, Role, Permission entities; AuthSession; value objects
│   │   │   ├── application/              # use_cases/ (Login, RefreshToken, RegisterUser, AssignRole, …), dto.py
│   │   │   ├── infrastructure/           # models.py, repositories.py, password/jwt adapters
│   │   │   ├── api/                      # router.py, schemas.py, dependencies.py (structure only)
│   │   │   ├── public/                   # interfaces.py, dto.py, events.py — the ONLY importable surface
│   │   │   └── container.py              # module-level composition root
│   │   ├── organization/                 # same 6-part shape
│   │   ├── doctor/
│   │   ├── patient/
│   │   ├── visit/
│   │   ├── clinical_note/
│   │   ├── soap_note/
│   │   ├── patient_history/
│   │   ├── lab_report/
│   │   ├── ai/
│   │   ├── audit/
│   │   ├── file_storage/
│   │   └── notification/
│   │
│   ├── infrastructure/                   # TRUE cross-cutting infra clients (existing, extended)
│   │   ├── database/
│   │   │   ├── base.py                   # Declarative Base, naming convention, mixins (existing)
│   │   │   ├── session.py                # engine + session factory (existing)
│   │   │   └── models/
│   │   │       └── __init__.py           # thin aggregator: imports every module's infrastructure/models.py
│   │   │                                  #   so Alembic autogenerate sees the whole schema (see note)
│   │   ├── cache/                        # Redis client (existing)
│   │   ├── vector_store/                 # Qdrant client (existing)
│   │   ├── storage/                      # MinIO client (existing) — wrapped by file_storage module
│   │   └── ai/                           # Gemini/faster-whisper/PaddleOCR clients (existing) — wrapped by ai module
│   │
│   ├── api/
│   │   ├── v1/
│   │   │   └── router.py                 # aggregates each module's api/router.py under one prefix
│   │   └── deps.py                       # get_db_session, get_current_user, get_tenant_context (existing, extended)
│   │
│   ├── middlewares/                      # existing: request_id, logging, error_handler
│   │   └── tenant_context_middleware.py  # NEW — resolves org/user from JWT, binds contextvars
│   │
│   ├── workers/                          # NEW — Celery
│   │   ├── celery_app.py                 # app + queue/routing config (relocated from infrastructure/queue/)
│   │   └── tasks/                        # one file per module: ai_tasks.py, notification_tasks.py, audit_tasks.py, …
│   │
│   └── schemas/                          # shared, cross-module Pydantic base schemas (existing)
│
├── tests/
│   ├── unit/
│   │   ├── shared/
│   │   └── modules/<module_name>/        # domain + application unit tests, per module
│   ├── integration/
│   │   └── modules/<module_name>/        # real-DB repository + infrastructure tests, per module
│   ├── contract/
│   │   └── modules/<module_name>/        # tests against each module's public/ facade
│   ├── e2e/                              # full request-lifecycle tests via HTTP client
│   └── conftest.py
│
├── requirements/
├── Dockerfile / Dockerfile.dev
├── alembic.ini
└── pyproject.toml
```

## Top-level responsibility summary

| Folder | Responsibility | Depends on |
|---|---|---|
| `app/core/` | Configuration, logging, base exceptions, security primitives — technical, zero domain knowledge | Nothing in `modules/` or `shared/` |
| `app/shared/` | DDD shared kernel: base classes and interfaces every module builds on | `app/core/` only |
| `app/modules/<name>/` | One bounded context end-to-end (domain → API) | `app/core/`, `app/shared/`, other modules' `public/` only |
| `app/infrastructure/` | Shared technical clients (DB engine, Redis, Qdrant, MinIO, AI SDKs) instantiated once, injected into modules | `app/core/` |
| `app/api/` | Top-level route aggregation and app-wide FastAPI dependencies | `app/modules/*/api/router.py` |
| `app/middlewares/` | Cross-cutting HTTP concerns applied to every request | `app/core/`, `app/shared/infrastructure/tenant_context.py` |
| `app/workers/` | Celery process entrypoint and task registration | `app/modules/*/application/use_cases/` (delegates, never reimplements) |
| `app/schemas/` | Base Pydantic conventions shared by every module's `api/schemas.py` | Nothing |
| `tests/` | Mirrors `app/` structure exactly, one test tree per test *kind*, not per source folder | — |

## Evolution note: relationship to the Turn 1 scaffold

The original scaffold's flat `app/domain/`, `app/application/`, and
`app/infrastructure/database/models/` folders were the right starting point
before any business modules existed. Now that 13 named modules are being
designed, those flat folders are **repurposed, not discarded**:

- `app/domain/` → becomes `app/shared/domain/` (base classes only; no
  module-specific entities live at the top level anymore).
- `app/application/` → becomes `app/shared/application/` (base `UseCase`,
  `UnitOfWork`, `EventBus` interfaces only).
- `app/infrastructure/database/models/__init__.py` → stays exactly where it
  is, but its role narrows to being an **import aggregator**: it imports
  `app.modules.<name>.infrastructure.models` for every module so that
  `Base.metadata` (and therefore Alembic `--autogenerate`) sees every
  table, without any module needing to know this file exists. A module's
  ORM models are owned and physically located inside that module's
  `infrastructure/`, not in this central file — this file only re-exports.
- `app/application/interfaces/ai_provider_port.py`,
  `storage_port.py`, `vector_store_port.py` (Turn 1) → remain in
  `app/shared/application/` as cross-module technical ports, since AI
  generation, storage, and vector search are capabilities multiple modules
  consume, not something any single module owns end-to-end (the `ai` and
  `file_storage` modules own the *orchestration* around these ports — see
  `09_ai_gateway_and_storage.md` — while the port definitions themselves
  are shared).
