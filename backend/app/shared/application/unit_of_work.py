"""Unit of Work interface.

Deliberately narrow: it manages only the transaction boundary
(begin/commit/rollback/flush) and the domain events collected during that
transaction — it does **not** hold repository references itself. See
`docs/backend-architecture/04_repository_and_service_patterns.md` for why
a "god UoW" holding every module's repositories is avoided in this
modular monolith. A use case receives the `UnitOfWork` and the specific
repositories it needs as sibling constructor dependencies, both bound to
the same underlying session for a given request/task.
"""

from abc import ABC, abstractmethod
from types import TracebackType

from app.shared.domain.domain_event import DomainEvent


class UnitOfWork(ABC):
    async def __aenter__(self) -> "UnitOfWork":
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        if exc_type is not None:
            await self.rollback()

    @abstractmethod
    async def commit(self) -> None:
        """Persist all staged changes, then publish collected domain events.

        Event publication must only happen after a successful commit — a
        subscriber must never react to an event whose transaction rolled
        back. See `docs/backend-architecture/10_module_communication.md`.
        """
        ...

    @abstractmethod
    async def rollback(self) -> None:
        """Discard all staged changes and any events collected so far."""
        ...

    @abstractmethod
    async def flush(self) -> None:
        """Push pending changes to the database without committing."""
        ...

    @abstractmethod
    def collect_events(self, events: list[DomainEvent]) -> None:
        """Stage domain events (typically `aggregate.pull_events()`) for
        publication on the next successful `commit()`."""
        ...
