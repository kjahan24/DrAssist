# DrAssist — Backend Architecture Documentation

The complete backend architecture for DrAssist: a **modular monolith**
where each of 13 business modules is internally structured as its own
**Clean Architecture** slice (Domain-Driven Design, SOLID, Repository
Pattern, Service Layer, Dependency Injection, Unit of Work), built to
convert into microservices later without a rewrite.

**Documentation only** — no business logic, no API endpoints, no frontend
code. This set extends the Clean Architecture scaffold from
[`../ARCHITECTURE.md`](../ARCHITECTURE.md) and is grounded in the schema
from [`../database/`](../database/README.md); read those first if you
haven't already.

## Read order

1. **[00_architectural_principles.md](00_architectural_principles.md)** — start here. Why modular monolith; how Clean Architecture, DDD, SOLID, Repository Pattern, Service Layer, DI, and Unit of Work fit together
2. **[01_folder_structure.md](01_folder_structure.md)** — the complete backend tree
3. **[02_layer_responsibilities.md](02_layer_responsibilities.md)** — Domain / Application / Infrastructure / API / Core / Shared, in depth
4. **[03_module_architecture.md](03_module_architecture.md)** — all 13 modules: domain model, use cases, public interface, dependencies
5. **[04_repository_and_service_patterns.md](04_repository_and_service_patterns.md)** — repository & service interfaces/implementations, Unit of Work design, validation layer
6. **[05_dependency_injection_and_lifecycle.md](05_dependency_injection_and_lifecycle.md)** — DI structure, middleware, dependency graph, request lifecycle
7. **[06_configuration_logging_exceptions.md](06_configuration_logging_exceptions.md)** — configuration management, logging architecture, exception handling
8. **[07_security_layer.md](07_security_layer.md)** — authN, RBAC, tenant isolation, PHI protection, secrets, rate limiting
9. **[08_background_workers.md](08_background_workers.md)** — Celery architecture: queues, routing, idempotency, retries, scheduled tasks
10. **[09_ai_gateway_and_storage.md](09_ai_gateway_and_storage.md)** — AI Gateway (provider abstraction, resilience, async orchestration) and Storage layer (MinIO, presigned URLs)
11. **[10_module_communication.md](10_module_communication.md)** — public facades vs. domain events, the Event Bus, when to use which
12. **[11_standards_and_conventions.md](11_standards_and_conventions.md)** — folder responsibility index, coding standards, naming conventions, import rules
13. **[12_testing_architecture.md](12_testing_architecture.md)** — unit / integration / contract / e2e testing strategy
14. **[13_microservices_migration_path.md](13_microservices_migration_path.md)** — what makes extraction cheap, ranked candidates, the extraction playbook

## Requirement traceability (all 30 design areas)

| # | Design area | Document |
|---|---|---|
| 1 | Complete backend folder structure | `01_folder_structure.md` |
| 2 | Domain layer | `02_layer_responsibilities.md` |
| 3 | Application layer | `02_layer_responsibilities.md` |
| 4 | Infrastructure layer | `02_layer_responsibilities.md` |
| 5 | API layer | `02_layer_responsibilities.md` |
| 6 | Core utilities | `02_layer_responsibilities.md`, `06_configuration_logging_exceptions.md` |
| 7 | Shared modules | `02_layer_responsibilities.md` |
| 8 | Dependency Injection structure | `05_dependency_injection_and_lifecycle.md` |
| 9 | Configuration management | `06_configuration_logging_exceptions.md` |
| 10 | Logging architecture | `06_configuration_logging_exceptions.md` |
| 11 | Exception handling | `06_configuration_logging_exceptions.md` |
| 12 | Background workers | `08_background_workers.md` |
| 13 | AI Gateway | `09_ai_gateway_and_storage.md` |
| 14 | Storage layer | `09_ai_gateway_and_storage.md` |
| 15 | Repository interfaces | `04_repository_and_service_patterns.md` |
| 16 | Repository implementations | `04_repository_and_service_patterns.md` |
| 17 | Service interfaces | `04_repository_and_service_patterns.md` |
| 18 | Service implementations | `04_repository_and_service_patterns.md` |
| 19 | Validation layer | `04_repository_and_service_patterns.md` |
| 20 | Security layer | `07_security_layer.md` |
| 21 | Middleware | `05_dependency_injection_and_lifecycle.md` |
| 22 | Dependency graph | `05_dependency_injection_and_lifecycle.md` |
| 23 | Request lifecycle | `05_dependency_injection_and_lifecycle.md` |
| 24 | Module communication | `10_module_communication.md` |
| 25 | Folder responsibilities | `11_standards_and_conventions.md` (index of every other doc) |
| 26 | Coding standards | `11_standards_and_conventions.md` |
| 27 | Naming conventions | `11_standards_and_conventions.md` |
| 28 | Import rules | `11_standards_and_conventions.md` |
| 29 | Testing architecture | `12_testing_architecture.md` |
| 30 | Future migration to microservices | `13_microservices_migration_path.md` |

## The 13 modules (full detail in `03_module_architecture.md`)

| Module | Owns (see `../database/`) | Depends on | Leaf / sink? |
|---|---|---|---|
| Authentication | users, roles, permissions, auth_sessions, … | Organization | No — depended on by nearly everything |
| Organization | organizations, organization_locations | *(none)* | No — foundational |
| Doctor | doctors, doctor_specialties, specialties | Authentication, Organization | No |
| Patient | patients, patient_contacts, allergies, medications, conditions, condition_codes | Authentication, Organization, Doctor | No |
| Visit | visits, vital_signs | Patient, Doctor, Organization | No |
| Clinical Note | clinical_notes | Visit, Patient, Authentication, AI | No |
| SOAP Note | soap_notes | Visit, Patient, Authentication, AI | No |
| Patient History | patient_timeline_events | *(events only, from all clinical modules)* | Yes — pure read-side |
| Lab Report | lab_reports, lab_results, lab_test_catalog | Patient, Visit, Doctor | No |
| AI | ai_sessions, conversation_transcripts | Patient, Visit (existence checks only) | No |
| Audit | audit_logs, activity_logs | *(none)* | Yes — pure sink |
| File Storage | attachments | *(none — deliberately generic)* | No, but depends on nothing |
| Notification | (module-local; not in the 22-table clinical schema) | Authentication, Patient | Yes — pure reactor |

## Relationship to other documentation in this repository

| Document | Relationship |
|---|---|
| `../ARCHITECTURE.md` | The original Clean Architecture scaffold this design extends into a modular monolith |
| `../database/` | The full PostgreSQL schema each module's `infrastructure/` layer maps to |
| This document set | How the application code above that schema is organized, layered, and allowed to talk to itself |
