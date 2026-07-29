"""SQLAlchemy ORM model for the Procedures module.

One table: `visit_procedures`. See `app.modules.procedures.container` for
the module's scope note.

`visit_procedures.organization_id` carries a real foreign key to
`organizations.id`, and `visit_id` a real foreign key to
`patient_visits.id` — brand-new columns on a brand-new table, so there is
no backward-compatibility reason to defer them; neither `organizations`
nor `patient_visits` is modified by this migration.

`visit_id` uses `ON DELETE CASCADE`, the same choice
`visit_diagnoses.visit_id` already makes: a procedure has no independent
lifecycle meaning without its visit. `performed_by` (nullable,
best-effort attribution) follows `visit_diagnoses.diagnosed_by`'s
`SET NULL` choice — see that column's own comment for the full reasoning.

"sequence_number must be unique within a Visit" is enforced by a partial
unique index on `(visit_id, sequence_number) WHERE deleted_at IS NULL`,
the same shape `visit_diagnoses`' own sequence uniqueness already uses.

Two status/date consistency rules are enforced as DB `CHECK` constraints
(in addition to `VisitProcedure.__post_init__`, the same defense-in-depth
pattern applied to every prior module):
- "performed_at is required only when status = Completed" ->
  `procedure_status != 'completed' OR performed_at IS NOT NULL`.
- "Cancelled procedures cannot have performed_at" ->
  `procedure_status != 'cancelled' OR performed_at IS NULL`.
"""

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, Index, SmallInteger, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import (
    AuditActorMixin,
    Base,
    SoftDeleteMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
    pg_enum,
)
from app.modules.procedures.domain.enums import ProcedureStatus

_procedure_status_enum = pg_enum(ProcedureStatus, "procedure_status_enum")


class VisitProcedureModel(
    Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin, AuditActorMixin
):
    __tablename__ = "visit_procedures"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False
    )
    visit_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("patient_visits.id", ondelete="CASCADE"), nullable=False
    )
    sequence_number: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    procedure_name: Mapped[str] = mapped_column(Text, nullable=False)
    procedure_code: Mapped[str | None] = mapped_column(Text, default=None)
    procedure_category: Mapped[str | None] = mapped_column(Text, default=None)
    procedure_status: Mapped[ProcedureStatus] = mapped_column(
        _procedure_status_enum, nullable=False, default=ProcedureStatus.PLANNED
    )
    performed_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("doctors.id", ondelete="SET NULL"), default=None
    )
    performed_at: Mapped[datetime | None] = mapped_column(default=None)
    notes: Mapped[str | None] = mapped_column(Text, default=None)

    __table_args__ = (
        Index(
            "uq_visit_procedures_visit_id_sequence_number",
            "visit_id",
            "sequence_number",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index("ix_visit_procedures_organization_id", "organization_id"),
        CheckConstraint("sequence_number >= 1", name="sequence_number_starts_at_one"),
        CheckConstraint(
            "procedure_status != 'completed' OR performed_at IS NOT NULL",
            name="completed_requires_performed_at",
        ),
        CheckConstraint(
            "procedure_status != 'cancelled' OR performed_at IS NULL",
            name="cancelled_forbids_performed_at",
        ),
    )
