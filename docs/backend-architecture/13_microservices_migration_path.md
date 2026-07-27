# Future Migration to Microservices

## Framing

This is **not** a "microservices-in-disguise" architecture that pretends
to be a monolith while paying distributed-systems tax up front. It is a
well-bounded monolith that defers the *operational* cost of distributed
systems (network partitions, distributed tracing, N deployment pipelines,
eventual consistency at every seam) until team size or scaling needs
actually justify it — while never making a decision today that would
require a rewrite, rather than an extraction, to get there. This document
specifies exactly what "extraction, not rewrite" means in practice.

## What makes extraction cheap, by design decision

| Design decision (made throughout this document set) | What it buys at extraction time |
|---|---|
| Every module's `public/` package is the only thing other modules import (`10_module_communication.md`) | The `public/interfaces.py` contracts **are already the future service's API contract** — extraction defines a network transport for an interface that already exists and is already covered by contract tests (`12_testing_architecture.md`), rather than requiring the contract itself to be designed for the first time under migration pressure |
| Cross-module communication goes through an abstract `EventBus` interface (`10_module_communication.md`), never a direct function call assumed to be in-process | Swapping the in-process implementation for a real broker (e.g. RabbitMQ/Kafka/SNS-SQS) is a single infrastructure-layer change (`app/shared/infrastructure/`); no module's domain, application, or `public/` code changes at all |
| Aggregates reference other modules' aggregates **by ID only**, never by object reference (`03_module_architecture.md`) | No module's domain logic assumes it can join across module boundaries in one query — the assumption that would otherwise break the instant two modules' tables live in different databases |
| The Unit of Work is scoped narrowly, per-module-repository-set, never a cross-module god-transaction (`04_repository_and_service_patterns.md`) | No code path today *requires* two modules' writes to commit atomically together — which is exactly the property that's impossible to guarantee for free once they're separate services (distributed transactions are the hardest thing to retrofit; this design never introduces the assumption in the first place) |
| Each module owns its own ORM models and, physically, could migrate to its own schema/database with no cross-module foreign keys (`../database/00_overview.md`, `01_folder_structure.md`) | A module's data extraction is a data-migration exercise (copy this module's tables to a new database) rather than an untangling exercise |
| Global reference data (`specialties`, `condition_codes`, `lab_test_catalog`, `permissions`) is owned by one module and exposed to others only via its `public/` lookup port (`03_module_architecture.md`) | No module directly queries another module's reference table — so extracting the owning module doesn't strand any other module's queries |
| `import-linter` enforces the module boundary in CI today, not just in a design document (`11_standards_and_conventions.md`) | The boundary is real on day one, not something that has silently eroded by the time extraction is attempted years later — the most common reason "modular monoliths" fail to actually extract cleanly in practice |

## Realistic extraction candidates, ranked

1. **AI module** — the strongest candidate. Distinct scaling profile
   (inference is CPU/GPU-bound and benefits from independent autoscaling,
   possibly a different runtime/hardware class entirely), already fully
   decoupled (generic, doesn't import any other module — `03_module_architecture.md`),
   and already communicates results exclusively via events plus a narrow
   command/query port.
2. **Notification module** — naturally asynchronous, high fan-out, low
   coupling (a pure event-reactor with almost no inbound commands), and a
   natural candidate for a team that owns "all outbound communication"
   platform-wide across products, not just DrAssist.
3. **File Storage module** — already network-isolated in practice (client
   ⇄ MinIO directly via presigned URLs, `09_ai_gateway_and_storage.md`);
   extracting the metadata/URL-issuing service itself is low-risk since
   the heavy data path never went through the monolith to begin with.
4. **Audit module** — a natural extraction once compliance/audit
   requirements grow enough to warrant a dedicated, separately-secured
   audit service (common in regulated industries specifically so audit
   infrastructure is administratively separate from the system it audits)
   — enabled by Audit already being a pure event sink nothing else depends
   on (`03_module_architecture.md`).

Modules in the clinical spine (Patient, Visit, Clinical Note, SOAP Note,
Lab Report, Doctor, Organization, Authentication) are **not** near-term
candidates — they're highly interrelated by business meaning (even though
decoupled by *code* dependency direction) and share the same consistency/
compliance requirements; splitting them provides little operational
benefit until the organization itself is large enough to want separate
teams owning each with separate deployment cadences.

## Extraction playbook (Strangler Fig pattern)

Applied per module, when and if warranted by actual scaling or team-
structure evidence (not preemptively):

1. **Confirm the trigger.** A genuine need — independent scaling
   (AI inference load doesn't correlate with API request volume), an
   independent team taking ownership, or a deployment-cadence mismatch
   (Notification changes daily; Patient changes rarely and needs a slower,
   more controlled release process) — not "microservices are the
   industry trend."
2. **Stand up the module as its own service**, with its own database,
   seeded from the monolith's tables for that module only (a data
   migration, per the table above — no schema redesign, since the module
   already owned exactly these tables and no others).
3. **Implement the module's `public/interfaces.py` contract as a real
   network API** (REST or gRPC) — the interface signatures don't change;
   only how a caller reaches them does.
4. **Swap the in-process facade for a network-client implementation of the
   identical interface**, registered in the monolith's composition root
   (`app/core/container.py`) in place of the old binding. Every calling
   module is unaffected — it depended on the interface, never the
   implementation (Liskov Substitution, `00_architectural_principles.md §3`).
5. **Point the `EventBus`'s routing for that module's published events at
   the real broker** — subscribers elsewhere in the monolith are
   unaffected; they only ever depended on receiving a `DomainEvent`
   instance, never on the delivery mechanism.
6. **Run both paths in parallel behind a flag** (the Strangler Fig
   technique proper) — route a subset of traffic to the new service,
   verify contract tests and production behavior match, then cut over
   fully.
7. **Delete the module's code from the monolith** only after full cutover
   and a confidence window — at which point `app/modules/<name>/` is
   removed entirely, its `import-linter` contract entry removed, and the
   monolith is smaller and simpler than before, not more complex — the
   opposite of what typically happens when microservices are bolted onto
   a non-modular monolith under pressure.

## What this design does *not* solve automatically (honest limitations)

- **Distributed tracing** across a real network boundary needs to be
  introduced at extraction time (correlating `request_id`,
  `06_configuration_logging_exceptions.md`, across service calls via
  W3C Trace Context propagation) — the current design's request ID
  threading is sufficient for a monolith's structured logs, not yet a
  full distributed trace.
- **Schema evolution across a service boundary** requires the extracted
  service to version its API contract independently going forward
  (its `public/interfaces.py` becomes subject to real backward-
  compatibility rules a network client outside the same deploy can't
  ignore) — inside the monolith today, an interface change and every
  caller's update land in the same commit; that convenience ends at
  extraction, by definition.
- **Operational maturity** (per-service monitoring, independent CI/CD
  pipelines, service-mesh or API-gateway routing, on-call ownership) is
  infrastructure and organizational work this document does not attempt
  to solve in advance — the architecture makes the *code-level* extraction
  cheap; it does not remove the genuine operational cost that is the
  actual reason to defer this until it's warranted.
