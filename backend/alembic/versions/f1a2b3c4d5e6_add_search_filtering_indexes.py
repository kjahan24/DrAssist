"""add search and filtering indexes

Search & Filtering module: adds composite B-tree indexes supporting the
new `search()` repository methods' most common `WHERE`/`ORDER BY` shape —
`organization_id` (always filtered) paired with the column each module's
search endpoint filters/sorts by most (a status-like enum, or the
module's own primary business-date column). None of these existed before
this migration (confirmed by inspecting every prior module's own
`create_*_table` migration) — every prior index in this schema is either
a single-column foreign-key index or a partial-unique natural-key index,
neither of which serves a `WHERE organization_id = ... AND status = ...`
or `WHERE organization_id = ... ORDER BY <date>` query efficiently at
production scale.

Deliberately does NOT add:
- GIN/full-text expression indexes for the new `to_tsvector(...) @@
  plainto_tsquery(...)` full-text search calls (see
  `app.infrastructure.database.query_utils.apply_full_text_search`'s own
  docstring) — those queries are correct without one (Postgres falls back
  to a sequential scan + expression evaluation), and the exact expression
  shape (which columns, `concat_ws` order) is more likely to evolve as
  real usage patterns emerge than the `organization_id` scoping this
  migration indexes; adding one now, before any query pattern is proven
  at scale, would be speculative index maintenance overhead the
  Performance section's "avoid over-engineering" spirit argues against.
  A follow-up migration adding one, once a specific slow query is
  identified, is a non-breaking, purely additive change.
- an index for every module in scope — `departments`, `soap_notes`, and
  `audit_logs` are excluded: `departments` already has a single-column
  `organization_id` index and is not expected to hold enough rows per
  organization for a composite index to matter; `soap_notes` has no
  status/date filter column beyond the timestamps already covered by its
  existing FK indexes; `audit_logs` already carries the composite
  `(organization_id, created_at DESC)` index its own migration added.

Revision ID: f1a2b3c4d5e6
Revises: e9d2cf4e86f5
Create Date: 2026-07-31

"""

from collections.abc import Sequence

from alembic import op

revision: str = "f1a2b3c4d5e6"
down_revision: str | None = "e9d2cf4e86f5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_INDEXES: list[tuple[str, str, tuple[str, ...]]] = [
    ("ix_patients_organization_id_status", "patients", ("organization_id", "status")),
    ("ix_patients_organization_id_created_at", "patients", ("organization_id", "created_at")),
    ("ix_doctors_organization_id_status", "doctors", ("organization_id", "status")),
    ("ix_doctors_organization_id_created_at", "doctors", ("organization_id", "created_at")),
    ("ix_appointments_organization_id_status", "appointments", ("organization_id", "status")),
    (
        "ix_appointments_organization_id_appointment_date",
        "appointments",
        ("organization_id", "appointment_date"),
    ),
    (
        "ix_patient_visits_organization_id_visit_status",
        "patient_visits",
        ("organization_id", "visit_status"),
    ),
    (
        "ix_patient_visits_organization_id_visit_date",
        "patient_visits",
        ("organization_id", "visit_date"),
    ),
    (
        "ix_clinical_notes_organization_id_status",
        "clinical_notes",
        ("organization_id", "status"),
    ),
    (
        "ix_clinical_notes_organization_id_encounter_datetime",
        "clinical_notes",
        ("organization_id", "encounter_datetime"),
    ),
    (
        "ix_prescriptions_organization_id_status",
        "prescriptions",
        ("organization_id", "status"),
    ),
    (
        "ix_prescriptions_organization_id_prescription_date",
        "prescriptions",
        ("organization_id", "prescription_date"),
    ),
    ("ix_lab_orders_organization_id_status", "lab_orders", ("organization_id", "status")),
    (
        "ix_lab_orders_organization_id_ordered_at",
        "lab_orders",
        ("organization_id", "ordered_at"),
    ),
    ("ix_lab_results_organization_id_status", "lab_results", ("organization_id", "status")),
    (
        "ix_lab_results_organization_id_reported_at",
        "lab_results",
        ("organization_id", "reported_at"),
    ),
    (
        "ix_notifications_organization_id_status",
        "notifications",
        ("organization_id", "status"),
    ),
    (
        "ix_patient_histories_organization_id_encounter_date",
        "patient_histories",
        ("organization_id", "encounter_date"),
    ),
]


def upgrade() -> None:
    for index_name, table_name, columns in _INDEXES:
        op.create_index(index_name, table_name, list(columns))


def downgrade() -> None:
    for index_name, table_name, _columns in reversed(_INDEXES):
        op.drop_index(index_name, table_name=table_name)
