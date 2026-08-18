"""The Community Answers module's public port — the only contract
another module may depend on. See
`docs/backend-architecture/03_module_architecture.md` and
`10_module_communication.md`.

Never import from `app.modules.community_answers.domain`, `.application`
(beyond this package's own re-exports in `public/dto.py`), or
`.infrastructure` from outside this module — this file and `dto.py` are
the entire allowed surface today.

This is the read-only lookup port this task's own GOAL section
anticipates future modules (Votes, Comments, Best-Answer-driven
reputation, AI Analysis) will need: resolve an answer id into a summary
(or confirm one exists) without depending on this module's own
repositories/entities — the same "query port for future consumer
modules" shape `app.modules.community_questions.public.interfaces
.QuestionQueryPort` already establishes for itself.
"""

from abc import ABC, abstractmethod
from uuid import UUID

from app.modules.community_answers.public.dto import CommunityAnswerSummaryDTO


class AnswerQueryPort(ABC):
    @abstractmethod
    async def answer_exists(self, answer_id: UUID) -> bool: ...

    @abstractmethod
    async def get_answer_summary(self, answer_id: UUID) -> CommunityAnswerSummaryDTO | None: ...
