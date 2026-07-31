"""Model-agnostic SQLAlchemy query-building helpers for the Search &
Filtering module.

Every helper here takes an in-progress `Select` and returns a new one
(SQLAlchemy statements are immutable) — a module's
`infrastructure/repositories.py` composes them into its own `search()`
method, in the same style existing `list_*` methods already chain
`.where()`/`.order_by()`/`.offset()`/`.limit()` calls. Nothing here is
module-specific: no repository, entity, or enum is imported, so this file
has no knowledge of what it's filtering — that keeps it reusable across
all thirteen modules in scope for this task, and safe to reuse later for
any future module without becoming a god-object.

Columns are typed `InstrumentedAttribute[Any]` (an ORM-mapped attribute,
e.g. `PatientModel.first_name`) rather than the more general
`ColumnElement` — every caller in this codebase always passes a real
mapped attribute, never a raw SQLAlchemy Core expression, and
`InstrumentedAttribute` is where `.ilike()`/`.in_()`/`.desc()`/etc. are
actually defined; `Select` is likewise typed `[Any]` rather than
parameterized with a row-shape `TypeVar`, since SQLAlchemy 2.0's
`Select[_T]` requires `_T` to bind to a `tuple[...]` row shape that these
helpers never need to know (they never unpack rows).

Deliberately NOT here (over-engineering for what's actually needed today):
- a generic filter-expression parser/DSL — each repository's `search()`
  applies the specific, typed filters its own module needs, the same way
  existing endpoints already apply ad hoc filters before calling
  `app.api.pagination.paginate_and_sort` (see that module's own docstring).
- caching of any kind — explicitly out of scope for this task.
- a single "do everything" orchestrator function — composing 3-4 small
  calls in each repository's `search()` method is more readable than a
  mega-function with a dozen optional parameters, and lets each module
  skip the helpers it doesn't need (e.g. a module with no free-text
  column has no reason to call `apply_full_text_search`).

Sort-field validation (mapping a client-supplied string to an actual
column, and rejecting unknown fields) is deliberately NOT done here — it
stays split exactly like the existing `app.api.pagination.paginate_and_sort`
split: `app.api.search_params.resolve_sort_field` validates the *name* at
the API layer (where `BadRequestError` already lives), and each
repository's own small `_SORT_COLUMNS` mapping resolves the *column* at
the infrastructure layer (where SQLAlchemy models already live). This
file only applies an already-resolved column.
"""

from collections.abc import Sequence
from typing import Any, Literal

from sqlalchemy import ColumnElement, Select, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import InstrumentedAttribute

_Column = InstrumentedAttribute[Any]


def scope_to_organization(
    stmt: Select[Any], organization_id_column: _Column, organization_id: object
) -> Select[Any]:
    return stmt.where(organization_id_column == organization_id)


def exclude_soft_deleted(
    stmt: Select[Any], deleted_at_column: _Column, *, include_deleted: bool = False
) -> Select[Any]:
    """`include_deleted=True` is the escape hatch for admin/audit use cases
    that must see soft-deleted rows — every module's `search()` defaults it
    to `False` so ordinary search results exclude them, matching the
    `deleted_at.is_(None)` convention every existing `list_*` method uses.
    """
    if include_deleted:
        return stmt
    return stmt.where(deleted_at_column.is_(None))


def apply_equality(stmt: Select[Any], column: _Column, value: object) -> Select[Any]:
    """No-op when `value` is `None` — every filter helper in this module
    follows the same "omit the clause rather than filter on NULL" rule, so
    callers can pass every optional query parameter through unconditionally.
    """
    if value is None:
        return stmt
    return stmt.where(column == value)


def apply_in_filter(
    stmt: Select[Any], column: _Column, values: Sequence[object] | None
) -> Select[Any]:
    if not values:
        return stmt
    return stmt.where(column.in_(values))


def apply_date_range(
    stmt: Select[Any],
    column: _Column,
    *,
    start: object | None = None,
    end: object | None = None,
) -> Select[Any]:
    if start is not None:
        stmt = stmt.where(column >= start)
    if end is not None:
        stmt = stmt.where(column <= end)
    return stmt


def apply_partial_text_search(
    stmt: Select[Any], columns: Sequence[_Column], term: str | None
) -> Select[Any]:
    """Case-insensitive substring match (`ILIKE '%term%'`), OR'd across
    `columns` — the "partial text search" requirement, for callers that
    want simple prefix/substring matching rather than full-text ranking.
    """
    if term is None or not term.strip():
        return stmt
    pattern = f"%{term.strip()}%"
    return stmt.where(or_(*(column.ilike(pattern) for column in columns)))


def apply_full_text_search(
    stmt: Select[Any],
    columns: Sequence[_Column],
    term: str | None,
    *,
    language: str = "english",
) -> Select[Any]:
    """PostgreSQL native full-text search: builds
    `to_tsvector(language, concat_ws(' ', coalesce(col1, ''), ...)) @@
    plainto_tsquery(language, term)`, ranking-free (relevance ranking is
    future-compatibility scope, not required today — see this module's
    `__init__.py`). `plainto_tsquery` (rather than `to_tsquery`) normalizes
    plain user input for us, so callers don't need to pre-sanitize `term`.
    """
    if term is None or not term.strip():
        return stmt
    document = func.concat_ws(" ", *(func.coalesce(column, "") for column in columns))
    vector = func.to_tsvector(language, document)
    query = func.plainto_tsquery(language, term.strip())
    return stmt.where(vector.op("@@")(query))


def apply_combined_text_search(
    stmt: Select[Any],
    *,
    full_text_columns: Sequence[_Column] = (),
    partial_columns: Sequence[_Column] = (),
    term: str | None,
    language: str = "english",
) -> Select[Any]:
    """Most modules want *both* full-text search over prose/name columns
    (`full_text_columns`) *and* a substring match over an identifier-style
    column such as `patient_number`/`order_number` (`partial_columns`) for
    the *same* `term` — e.g. searching "warr" should find a patient named
    "Warren" via full-text stemming/prefix matching, while searching
    "PAT-042" should find it via a plain substring match, without the
    caller needing two separate query parameters.

    Calling `apply_full_text_search` and `apply_partial_text_search`
    separately would AND their two `.where()` clauses together instead of
    ORing them, which would require a row to match *both* conditions at
    once — effectively breaking search results for the common case where
    a term is prose-only or identifier-only. This function builds the
    single OR'd condition both callers actually want in one call.
    """
    if term is None or not term.strip():
        return stmt
    stripped = term.strip()
    conditions: list[ColumnElement[bool]] = []
    if full_text_columns:
        document = func.concat_ws(" ", *(func.coalesce(column, "") for column in full_text_columns))
        vector = func.to_tsvector(language, document)
        conditions.append(vector.op("@@")(func.plainto_tsquery(language, stripped)))
    if partial_columns:
        pattern = f"%{stripped}%"
        conditions.extend(column.ilike(pattern) for column in partial_columns)
    if not conditions:
        return stmt
    return stmt.where(or_(*conditions))


def apply_sort(
    stmt: Select[Any], column: _Column, sort_order: Literal["asc", "desc"]
) -> Select[Any]:
    return stmt.order_by(column.desc() if sort_order == "desc" else column.asc())


def apply_pagination(stmt: Select[Any], *, offset: int, limit: int) -> Select[Any]:
    return stmt.offset(offset).limit(limit)


async def count_total(session: AsyncSession, filtered_stmt: Select[Any]) -> int:
    """`SELECT count(*) FROM (filtered_stmt)` — always called on the
    statement *before* `apply_sort`/`apply_pagination` are applied, so the
    count reflects every filter but neither ordering nor slicing. Kept as
    a second round-trip (rather than a `COUNT(*) OVER()` window function
    folded into the page query) because it composes with plain
    `session.scalars(select(Model)...)` results — no per-row window value
    to strip back out — and stays legible; a window-function variant is a
    non-breaking, purely additive optimization to reach for later if
    profiling shows the extra round-trip actually matters at production
    scale.
    """
    count_stmt = select(func.count()).select_from(filtered_stmt.subquery())
    result = await session.execute(count_stmt)
    return result.scalar_one()
