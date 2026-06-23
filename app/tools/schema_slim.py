"""Post-process Pydantic JSON Schema to minimize the LLM tool envelope.

Pydantic 2 emits `anyOf: [T, null]` for `Optional[T]` and auto-generated
`title` per field. Both are redundant for LLM clients:

- LLM either sends a typed value or omits the field — `null` branch in
  `anyOf` doesn't help.
- `title` duplicates the field name (Pydantic camelCases the key).

We keep runtime Pydantic validation untouched; this only rewrites the
JSON schema we ship via `tools/list`.
"""
from __future__ import annotations

from typing import Any


def _strip_null_branch(node: dict[str, Any]) -> dict[str, Any]:
    """If node has anyOf:[T, null], replace with T + default:null.

    Returns the input unchanged if the pattern doesn't match.
    """
    alts = node.get("anyOf")
    if not isinstance(alts, list):
        return node
    null_branches = [a for a in alts if isinstance(a, dict) and a.get("type") == "null"]
    other_branches = [a for a in alts if not (isinstance(a, dict) and a.get("type") == "null")]
    if not null_branches or len(other_branches) != 1:
        return node
    keep = {k: v for k, v in node.items() if k != "anyOf"}
    merged = {**other_branches[0], **keep}
    if "default" not in merged:
        merged["default"] = None
    return merged


def slim_schema(schema: Any) -> Any:
    """Recursively rewrite anyOf:[T, null] → T (with default:null).

    Idempotent — running twice is a no-op. Safe on $defs (Pydantic refs).
    Does not touch oneOf/allOf (we have none).
    """
    if isinstance(schema, dict):
        slimmed = _strip_null_branch(schema)
        return {k: slim_schema(v) for k, v in slimmed.items()}
    if isinstance(schema, list):
        return [slim_schema(v) for v in schema]
    return schema


def strip_titles(schema: Any, _depth: int = 0, _parent_key: str | None = None) -> Any:
    """Remove auto-generated `title` fields from Pydantic schema output.

    Keeps top-level (depth 0) `title` — it's the tool/schema name and may be
    referenced by clients. Strips nested ones; they duplicate the field key.

    Crucially, the key `title` directly under `properties` / `$defs` is the
    *name of a parameter* (e.g. `component_crud(title=...)`), not a Pydantic
    meta-label — those must NOT be dropped. Without this guard, any tool with
    a `title` parameter would silently lose it from the JSON schema and
    LLM clients would never see it.
    """
    if isinstance(schema, dict):
        is_param_container = _parent_key in ("properties", "$defs")
        keys_to_drop = set() if (_depth == 0 or is_param_container) else {"title"}
        kept = {k: v for k, v in schema.items() if k not in keys_to_drop}
        return {k: strip_titles(v, _depth + 1, _parent_key=k) for k, v in kept.items()}
    if isinstance(schema, list):
        return [strip_titles(v, _depth + 1, _parent_key=_parent_key) for v in schema]
    return schema


def apply_slim_to_mcp(mcp) -> int:
    """Apply slim_schema + strip_titles to every registered tool.

    Returns count of tools updated. Safe to call multiple times (idempotent).
    """
    updated = 0
    try:
        tools = mcp._tool_manager._tools  # noqa: SLF001
    except Exception:
        return 0
    for tool in tools.values():
        params = getattr(tool, "parameters", None)
        if not params:
            continue
        params = slim_schema(params)
        params = strip_titles(params)
        tool.parameters = params
        updated += 1
    return updated
