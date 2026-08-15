"""The Community Questions module's public port — the only contract
another module may depend on. See
`docs/backend-architecture/03_module_architecture.md` and
`10_module_communication.md`.

Never import from `app.modules.community_questions.domain`, `.application`
(beyond this package's own re-exports in `public/dto.py`), or
`.infrastructure` from outside this module — this file and `dto.py` are
the entire allowed surface today.

This is the read-only lookup port future modules this task's own GOAL
section anticipates (Answers, Comments, Votes, AI Summary) will need:
resolve a question id into a summary (or confirm one exists) without
depending on this module's own repositories/entities — the same "query
port for future consumer modules" shape
`app.modules.community_posts.public.interfaces.PostQueryPort` already
establishes for itself.
"""

from abc import ABC, abstractmethod
from uuid import UUID

from app.modules.community_questions.public.dto import CommunityQuestionSummaryDTO


class QuestionQueryPort(ABC):
    @abstractmethod
    async def question_exists(self, question_id: UUID) -> bool: ...

    @abstractmethod
    async def get_question_summary(
        self, question_id: UUID
    ) -> CommunityQuestionSummaryDTO | None: ...
