# DrAssist

Foundation scaffold for DrAssist, a healthcare SaaS platform. This
repository currently contains **architecture only**: no business logic,
API endpoints, or AI prompts have been implemented. See
[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the design rationale.

## Tech stack

| Layer | Technology |
|---|---|
| Frontend | Next.js, TypeScript, Tailwind CSS, shadcn/ui |
| Backend | FastAPI, Python 3.12+, SQLAlchemy, Alembic, Pydantic v2 |
| Database | PostgreSQL |
| Cache | Redis |
| Vector database | Qdrant |
| Queue | Celery |
| Object storage | MinIO |
| AI | Gemini API, faster-whisper, PaddleOCR |
| Infrastructure | Docker, Docker Compose |

## Project layout

```
DrAssist/
├── backend/                 FastAPI service (Clean Architecture)
│   ├── app/
│   │   ├── api/              Route aggregation (v1 router — no endpoints yet)
│   │   ├── application/      Use cases, DTOs, port interfaces
│   │   ├── domain/            Entities, repository interfaces, domain services
│   │   ├── infrastructure/    DB, cache, vector store, queue, storage, AI adapters
│   │   ├── core/              Settings, logging, exceptions, security primitives
│   │   ├── middlewares/        Request ID, access logging, error handling
│   │   └── schemas/            Shared Pydantic base schemas
│   ├── alembic/               Migration environment
│   ├── tests/                 unit/ + integration/
│   └── requirements/           base / dev / prod
├── frontend/                 Next.js app (App Router)
│   └── src/
│       ├── app/                Routes, layouts, global styles
│       ├── components/          ui/ (shadcn), layout/, shared/
│       ├── features/            Vertical feature slices (empty)
│       ├── lib/                 cn(), generic API transport
│       ├── config/              Typed env access, site metadata
│       └── store/, hooks/, types/
├── infra/docker/             Postgres init, Redis, Qdrant, Nginx configs
├── scripts/                  Dev scripts (bash + PowerShell)
├── docs/                     Architecture documentation
├── docker-compose.yml         Base service definitions
├── docker-compose.override.yml  Dev overlay (hot reload) — auto-applied
└── docker-compose.prod.yml     Prod overlay (gunicorn, nginx, resource limits)
```

## Prerequisites

- Docker Engine 24+ and Docker Compose v2
- Node.js 20+ and Python 3.12+ (only needed for running tooling outside containers)

## Getting started

```bash
# 1. Bootstrap environment files and build images
./scripts/setup.sh        # or: scripts/setup.ps1 on Windows

# 2. Edit secrets
#    .env, backend/.env, frontend/.env

# 3. Start the stack (hot reload)
make dev                  # or: ./scripts/dev.sh / scripts/dev.ps1
```

Services once running:

| Service | URL |
|---|---|
| Frontend | http://localhost:3000 |
| Backend (docs) | http://localhost:8000/docs |
| MinIO console | http://localhost:9001 |
| Qdrant | http://localhost:6333 |
| Flower (Celery monitoring) | http://localhost:5555 |

## Common tasks

```bash
make migrate        # apply Alembic migrations
make migrate-new m="add patients table"   # create a new migration
make lint           # ruff + mypy + eslint + tsc
make test           # pytest + vitest
make logs           # tail all service logs
make down           # stop the stack
```

Equivalent PowerShell scripts are provided under `scripts/*.ps1` for each
`make` target that isn't a one-line `docker compose` passthrough.

## Environment configuration

Each service ships a scoped `.env.example`:

- [.env.example](.env.example) — full reference, consumed by docker-compose
- [backend/.env.example](backend/.env.example) — backend-only subset
- [frontend/.env.example](frontend/.env.example) — `NEXT_PUBLIC_*` subset

Copy each to `.env` and fill in real values. Never commit a populated
`.env` file — see [.gitignore](.gitignore).

## Production deployment

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

This overlay swaps the backend to `gunicorn` + Uvicorn workers, builds the
frontend's optimized standalone output, disables interactive API docs,
adds resource limits, and fronts both services with the Nginx reverse
proxy defined in `infra/docker/nginx/nginx.conf`. TLS termination is not
configured — terminate TLS at a load balancer/ingress in front of this
stack, or extend the Nginx config once a certificate is provisioned.

## Contributing

Run `make lint` and `make test` before opening a PR. CI
(`.github/workflows/ci.yml`) runs the same checks on every push and pull
request against `main`/`develop`.
