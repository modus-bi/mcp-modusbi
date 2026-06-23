"""Pydantic models for strongly-typed tool parameters.

Purpose
-------
Replaces weakly-typed ``list[dict]`` / ``dict`` annotations in MCP tool
signatures. Each model emits a full JSON Schema (``$defs``) so that LLMs
get accurate hints on the accepted fields, closing the
``weak_input_schema`` and ``arbitrary_top_level_properties`` Scorecard
rules.

Strict vs soft
--------------
* **strict** (``extra="forbid"``) — fully known schema, no extra keys.
  Used for ``dataset_query`` clauses, ``query_batch.queries``,
  ``batch_operations.layouts``.
* **soft** (``extra="allow"``) — schema documents the canonical fields
  but forward-compat keys are accepted (e.g. 339+ slug overrides on
  components, future ``options`` settings on report groups).
  ``additionalProperties: true`` will remain in the JSON Schema for
  these two models only — an accepted trade-off.

Internal dispatchers in ``app/tools/*.py`` continue to operate on
``list[dict]`` / ``dict``; the tool functions in ``server.py`` convert
Pydantic instances back via ``model_dump(exclude_none=True)`` before
forwarding.
"""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# dataset_query
# ---------------------------------------------------------------------------


class SelectField(BaseModel):
    """One field in the SELECT clause of ``dataset_query``."""

    model_config = {"extra": "forbid"}

    name: str = Field(description="Field name from dataset, e.g. 'amount'.")
    aggr: Literal["sum", "avg", "max", "min", "count", "none", ""] | None = Field(
        default=None,
        description="Aggregation function. Empty string or 'none' = no aggregation.",
    )
    alias: str | None = Field(
        default=None,
        description="Optional alias for the result column.",
    )
    calc: str | None = Field(
        default=None,
        description="Optional calculation expression (for calc fields).",
    )


class WhereClause(BaseModel):
    """One condition in the WHERE clause of ``dataset_query``."""

    model_config = {"extra": "forbid"}

    name: str = Field(description="Field name to filter on.")
    op: Literal[
        "=", "!=", "<", ">", "<=", ">=", "in", "not in", "like", "is", "is not"
    ] = Field(description=(
        "Comparison operator. 'is'/'is not' (value omitted) = IS [NOT] NULL. "
        "'in'/'not in' are NOT supported by the portal (HTTP 400) — "
        "use repeated '=' conditions with logicOr:1."
    ))
    value: str | int | float | bool | list[Any] | None = Field(
        default=None,
        description="Value to compare. Omit for 'is'/'is not' (NULL check).",
    )
    # Aliases / passthrough for API format
    oper: str | None = Field(
        default=None,
        description="Alternate spelling of 'op' (passthrough for API compatibility).",
    )
    lvl: int | None = Field(default=None, description="Logical nesting level.")
    logicOr: int | None = Field(
        default=None,
        description="1 = OR with previous condition, 0/absent = AND.",
    )


class GroupClause(BaseModel):
    """One field in the GROUP BY clause of ``dataset_query``."""

    model_config = {"extra": "forbid"}

    name: str = Field(description="Field name to group by.")
    calc: str | None = Field(
        default=None,
        description="Optional calculation expression.",
    )


class OrderClause(BaseModel):
    """One field in the ORDER BY clause of ``dataset_query``."""

    model_config = {"extra": "forbid"}

    name: str = Field(description="Field name to order by.")
    dir: Literal["asc", "desc"] = Field(
        default="asc",
        description="Sort direction (default: asc).",
    )
    alias: str | None = Field(
        default=None,
        description="Optional alias (when ordering by an aliased expression).",
    )


# ---------------------------------------------------------------------------
# query_batch
# ---------------------------------------------------------------------------


class BatchQueryParams(BaseModel):
    """Inner params for a single ``query_batch`` entry.

    Mirrors ``dataset_query`` arguments.

    NOTE: the batch path forwards params to the portal as-is (no order
    transformation) — for sorting in batch, pass the full format
    {name, alias, direction}; otherwise the portal drops the condition
    (alias='').
    """

    model_config = {"extra": "forbid"}

    select: list[SelectField] | None = Field(
        default=None, description="Fields to select (see SelectField)."
    )
    where: list[WhereClause] | None = Field(
        default=None, description="Filter conditions (see WhereClause)."
    )
    group: list[GroupClause] | None = Field(
        default=None, description="Group-by fields (see GroupClause)."
    )
    order: list[OrderClause] | None = Field(
        default=None, description="Order-by fields (see OrderClause)."
    )
    limit: int | None = Field(
        default=None, description="Row limit (default 1000 server-side)."
    )


class BatchQuerySpec(BaseModel):
    """One query in ``query_batch.queries``.

    Each query has a unique ``id`` so results can be looked up by caller.
    """

    model_config = {"extra": "forbid"}

    id: str = Field(description="Unique identifier for the query (result key).")
    params: BatchQueryParams = Field(
        description="Query parameters (select, where, group, order, limit).",
    )


# ---------------------------------------------------------------------------
# batch_operations
# ---------------------------------------------------------------------------


class LayoutSpec(BaseModel):
    """One layout update in ``batch_operations.layouts``.

    Strict: exactly the fields understood by ``_update_multiple_layouts``.
    """

    model_config = {"extra": "forbid"}

    component_idx: int = Field(
        description="Zero-based index of the component to re-layout.",
    )
    x: int | None = Field(default=None, description="Grid column (left).")
    y: int | None = Field(default=None, description="Grid row (top).")
    w: int | None = Field(default=None, description="Width in grid columns.")
    h: int | None = Field(default=None, description="Height in grid rows.")
    z_index: int | None = Field(
        default=None, description="CSS z-index (stacking order)."
    )


class ComponentSpec(BaseModel):
    """One component in ``batch_operations.components_add``.

    Soft model (``extra='allow'``): 339+ slug config_overrides and
    future builder flags can be passed through without schema bumps.
    Canonical fields listed explicitly for LLM guidance.
    """

    model_config = {"extra": "allow"}

    # --- required ---
    component_type: str = Field(
        description="Component type, e.g. 'HsBarAMchartsChart' (chart), 'HsTotalsPanelV2' (KPI), 'HsTableReactabularChart' (table), 'HsTextBlock' (text).",
    )
    title: str = Field(description="Component title (shown in header).")

    # --- required for data components (charts/tables/KPI/maps) ---
    dataset_id: int | None = Field(
        default=None, description="Dataset ID (required for data components)."
    )
    value_field: str | None = Field(
        default=None,
        description="Comma-separated field names for values axis (required for data components).",
    )
    category_field: str | None = Field(
        default=None, description="Field name for categories axis."
    )

    # --- optional data config ---
    aggregation: Literal["sum", "avg", "max", "min", "count", "none", ""] | None = Field(
        default=None,
        description="Aggregation for value fields. Tables auto-forced to 'none'.",
    )
    value_fields_type: str | None = Field(
        default=None, description="Type hint for value fields (default 'number')."
    )
    row_fields: str | None = Field(
        default=None, description="Comma-separated row fields (pivot table)."
    )
    column_fields: str | None = Field(
        default=None, description="Comma-separated column fields (pivot/comparison)."
    )
    size_field: str | None = Field(
        default=None, description="Bubble size field (bubble chart)."
    )
    field_titles: dict[str, str] | None = Field(
        default=None, description="Map of field name to display alias."
    )
    where_filter: list[WhereClause] | None = Field(
        default=None, description="Component-level WHERE filter."
    )
    text_content: str | None = Field(
        default=None, description="HTML content for text blocks (sanitized)."
    )

    # --- layout ---
    x: int | None = Field(default=None, description="Grid column (left).")
    y: int | None = Field(default=None, description="Grid row (top).")
    w: int | None = Field(default=None, description="Width in grid columns.")
    h: int | None = Field(default=None, description="Height in grid rows.")
    position: dict[str, int] | None = Field(
        default=None,
        description="Alternative to x/y/w/h: {'x':..,'y':..,'w':..,'h':..}.",
    )

    # --- visual params ---
    stacking: str | None = Field(
        default=None, description="Bar stacking: 'normal', '100', ''."
    )
    orientation: str | None = Field(
        default=None, description="Chart orientation: 'horizontal'|'vertical'."
    )
    preset: str | None = Field(
        default=None,
        description="Visual preset: minimal, presentation, dashboard, dark, print, kpi.",
    )
    legend_visible: bool | None = Field(default=None, description="Show legend.")
    legend_position: str | None = Field(
        default=None, description="Legend position (top/right/bottom/left)."
    )
    labels_visible: bool | None = Field(
        default=None, description="Show data labels on chart."
    )
    bg_color: str | None = Field(default=None, description="Background color (rgba).")
    config_overrides: dict[str, Any] | None = Field(
        default=None,
        description="Flat dict of slug overrides (see config_schema.SLUG_SCHEMA).",
    )


# ---------------------------------------------------------------------------
# reportgroup_operations
# ---------------------------------------------------------------------------


class ReportGroupOptions(BaseModel):
    """Options for ``reportgroup_operations``.

    Soft model (``extra='allow'``): the API accepts arbitrary keys and
    new localisation/display options may land here. Canonical fields
    listed per docs/infrastructure/reportgroup.md.
    """

    model_config = {"extra": "allow"}

    caption__ru: str | None = Field(
        default=None, description="Caption in Russian."
    )
    caption__en: str | None = Field(
        default=None, description="Caption in English."
    )
    name__ru: str | None = Field(
        default=None, description="Name in Russian."
    )
    name__en: str | None = Field(
        default=None, description="Name in English."
    )
    color: str | None = Field(
        default=None,
        description="Group colour in navigation, as rgba(R,G,B,A).",
    )
    cellMode: Literal["compact", "standard", "large"] | None = Field(
        default=None,
        description="Grid cell size for reports inside the group.",
    )
    allowOverlapMode: bool | None = Field(
        default=None,
        description="Allow component overlap in reports of this group.",
    )
    recalculatedCellMode: bool | None = Field(
        default=None, description="Recalculate cell size when layout changes."
    )
    icon: str | None = Field(default=None, description="Icon name.")


__all__ = [
    "SelectField",
    "WhereClause",
    "GroupClause",
    "OrderClause",
    "BatchQueryParams",
    "BatchQuerySpec",
    "LayoutSpec",
    "ComponentSpec",
    "ReportGroupOptions",
]
