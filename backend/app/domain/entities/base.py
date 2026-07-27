"""Shared contract for domain entities.

Domain entities are plain Python dataclasses with identity — they must
not import SQLAlchemy, Pydantic, or any framework/infrastructure type.
Persistence mapping happens in `app/infrastructure/database/models/`;
API shape happens in `app/schemas/`. Keeping this layer pure is what
allows the domain to be tested and reasoned about independently of
FastAPI, SQLAlchemy, or any external service.
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4


@dataclass(kw_only=True)
class BaseEntity:
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
