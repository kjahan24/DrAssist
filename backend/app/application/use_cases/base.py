"""Shared contract for application use cases.

A use case takes a single input DTO and returns a single output DTO,
depending only on domain entities and ports (`app/domain/repositories`,
`app/application/interfaces`) — never on FastAPI or a concrete driver.
This keeps orchestration logic transportable across HTTP, Celery tasks,
and CLI scripts alike.
"""

from abc import ABC, abstractmethod
from typing import Generic, TypeVar

InputDTO = TypeVar("InputDTO")
OutputDTO = TypeVar("OutputDTO")


class UseCase(ABC, Generic[InputDTO, OutputDTO]):
    @abstractmethod
    async def execute(self, input_dto: InputDTO) -> OutputDTO: ...
