"""The Personal Health Timeline module's public port — the only contract
another module may depend on. See
`docs/backend-architecture/03_module_architecture.md` and
`10_module_communication.md`.

Never import from `app.modules.timeline.domain`, `.application` (beyond
this package), or `.infrastructure` from outside this module — this file
and `dto.py` are the entire allowed surface today. Future consumers
(Patient Portal, Personal Health Dashboard, Family/Caregiver Access,
Medical Community, AI Health Summary, Timeline PDF Export, Mobile App
Timeline, FHIR APIs — see `container.py`'s own scope note) are expected
to depend on this port rather than re-implementing cross-module
aggregation themselves.
"""

from abc import ABC, abstractmethod
from typing import Literal
from uuid import UUID

from app.modules.timeline.public.dto import TimelineFilterInput, TimelinePageDTO


class TimelineQueryPort(ABC):
    @abstractmethod
    async def get_patient_timeline(
        self,
        patient_id: UUID,
        *,
        filters: TimelineFilterInput,
        offset: int = 0,
        limit: int = 20,
        sort_order: Literal["asc", "desc"] = "desc",
    ) -> TimelinePageDTO: ...
