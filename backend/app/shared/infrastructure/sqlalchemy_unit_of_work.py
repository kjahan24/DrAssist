"""SQLAlchemy-backed Unit of Work — the one concrete `UnitOfWork` implementation."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.application.event_bus import EventBus
from app.shared.application.unit_of_work import UnitOfWork
from app.shared.domain.domain_event import DomainEvent


class SqlAlchemyUnitOfWork(UnitOfWork):
    def __init__(self, session: AsyncSession, event_bus: EventBus | None = None) -> None:
        self._session = session
        self._event_bus = event_bus
        self._collected_events: list[DomainEvent] = []

    @property
    def session(self) -> AsyncSession:
        return self._session

    def collect_events(self, events: list[DomainEvent]) -> None:
        self._collected_events.extend(events)

    async def commit(self) -> None:
        await self._session.commit()
        events, self._collected_events = self._collected_events, []
        if self._event_bus is not None and events:
            await self._event_bus.publish(events)

    async def rollback(self) -> None:
        await self._session.rollback()
        self._collected_events.clear()

    async def flush(self) -> None:
        await self._session.flush()
