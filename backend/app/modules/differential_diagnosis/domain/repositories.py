"""Repository interface for the `DifferentialDiagnosis` aggregate,
expressed in domain vocabulary only (no session, no SQL). Concrete
implementation lives in
`app.modules.differential_diagnosis.infrastructure.repositories`. See
`docs/backend-architecture/04_repository_and_service_patterns.md`.

No `update()` method: a repository returns the actual aggregate object,
the caller mutates it via its own methods, and the Unit of Work's
`commit()` persists the change through SQLAlchemy's session-level change
tracking.
"""

from abc import ABC, abstractmethod
from uuid import UUID

from app.modules.differential_diagnosis.domain.entities import DifferentialDiagnosis


class DifferentialDiagnosisRepository(ABC):
    @abstractmethod
    async def get_by_id(self, differential_diagnosis_id: UUID) -> DifferentialDiagnosis | None: ...

    @abstractmethod
    async def get_by_clinical_note_and_ranking(
        self, *, clinical_note_id: UUID, ranking: int
    ) -> DifferentialDiagnosis | None: ...

    @abstractmethod
    async def list_by_clinical_note(
        self, clinical_note_id: UUID
    ) -> list[DifferentialDiagnosis]: ...

    @abstractmethod
    async def list_by_patient(self, patient_id: UUID) -> list[DifferentialDiagnosis]: ...

    @abstractmethod
    async def add(self, diagnosis: DifferentialDiagnosis) -> None: ...
