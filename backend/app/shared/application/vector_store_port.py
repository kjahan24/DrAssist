"""Port for vector search (implemented by Qdrant in `app/infrastructure/vector_store/`)."""

from abc import ABC, abstractmethod
from typing import Any


class VectorStorePort(ABC):
    @abstractmethod
    async def upsert(
        self,
        *,
        collection: str,
        vector_id: str,
        vector: list[float],
        payload: dict[str, Any],
    ) -> None: ...

    @abstractmethod
    async def search(
        self, *, collection: str, query_vector: list[float], top_k: int = 5
    ) -> list[dict[str, Any]]: ...

    @abstractmethod
    async def delete(self, *, collection: str, vector_id: str) -> None: ...

    @abstractmethod
    async def retrieve(self, *, collection: str, vector_id: str) -> list[float] | None:
        """The stored vector for `vector_id`, or `None` if it has never
        been upserted (or the collection does not exist yet). Lets a
        caller re-use a previously-embedded vector as a search query
        without re-embedding or re-supplying the original text."""
        ...
