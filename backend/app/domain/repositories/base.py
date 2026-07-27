"""Generic repository port.

Defines the shape every concrete repository must satisfy, without
committing to a storage technology. Application-layer use cases depend on
this abstraction, never on `app/infrastructure` directly (Dependency
Inversion Principle) — a concrete adapter is provided at runtime via DI.
"""

from abc import ABC, abstractmethod
from typing import Generic, TypeVar
from uuid import UUID

from app.domain.entities.base import BaseEntity

EntityT = TypeVar("EntityT", bound=BaseEntity)


class AbstractRepository(ABC, Generic[EntityT]):
    @abstractmethod
    async def get_by_id(self, entity_id: UUID) -> EntityT | None: ...

    @abstractmethod
    async def list(self, *, offset: int = 0, limit: int = 20) -> list[EntityT]: ...

    @abstractmethod
    async def add(self, entity: EntityT) -> EntityT: ...

    @abstractmethod
    async def update(self, entity: EntityT) -> EntityT: ...

    @abstractmethod
    async def delete(self, entity_id: UUID) -> None: ...
