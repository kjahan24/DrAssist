"""Repository interface for the `DoctorReview` aggregate, expressed in
domain vocabulary only (no session, no SQL). Concrete implementation
lives in `app.modules.doctor_review.infrastructure.repositories`. See
`docs/backend-architecture/04_repository_and_service_patterns.md`.

No `update()` method: a repository returns the actual aggregate object,
the caller mutates it via its own methods, and the Unit of Work's
`commit()` persists the change through SQLAlchemy's session-level change
tracking.
"""

from abc import ABC, abstractmethod
from uuid import UUID

from app.modules.doctor_review.domain.entities import DoctorReview


class DoctorReviewRepository(ABC):
    @abstractmethod
    async def get_by_id(self, doctor_review_id: UUID) -> DoctorReview | None: ...

    @abstractmethod
    async def get_by_clinical_note_id(self, clinical_note_id: UUID) -> DoctorReview | None: ...

    @abstractmethod
    async def list_by_patient(self, patient_id: UUID) -> list[DoctorReview]: ...

    @abstractmethod
    async def add(self, review: DoctorReview) -> None: ...
