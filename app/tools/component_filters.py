"""
Component filter operations: global filters + filter axis management.

Split from component_operations.py for maintainability.
Functions:
- _set_global_filter, _reset_global_filters
- _filter_fields_list, _filter_field_add, _filter_field_remove
- _filter_set_cascade
"""

import logging

from typing import Any

from ..core.exceptions import NotFoundError
from .builders import generate_uid
from .component_axes import _save_report as _save_report_filters
from .component_crud import BREAKPOINT_COLS

logger = logging.getLogger(__name__)


# -------------------------------------------------------------------------
# Shared helpers
# -------------------------------------------------------------------------

async def _fetch_report(client, report_id: int) -> dict:
    """Fetch report by id. Raises NotFoundError if missing."""
    resp = await client.api_call("reports", "get", object_id=report_id)
    if resp.get("status") != 200:
        raise NotFoundError(f"Report {report_id} not found", object_id=report_id)
    data = resp.get("data", [])
    if not data:
        raise NotFoundError(f"Report {report_id} not found", object_id=report_id)
    return data[0]


def _rebuild_global_filters(report: dict) -> dict:
    """Пересобрать report["globalFilters"] по живым (alias, global=True) парам.

    Единый источник правды: пересборка по всем компонентам покрывает
    кейсы, которые точечная очистка одного поля не закрывает:
      - изменение alias (старый ключ висит, новый не появляется)
      - bulk обновление aliases через dataset.update(field_aliases)
      - mismatch между component-fields и globalFilters после ручных правок

    Алгоритм:
      1. Собрать все живые aliases где global=True со всех компонентов.
      2. Для каждого живого alias — сохранить существующую запись из
         globalFilters (если есть) либо создать дефолт.
      3. Заменить report["globalFilters"] на чистый dict.

    Сохраняет настройки `enabled/filterMode/selected/sourceValues/filterBy`
    для живых ключей. Удаляет dead-keys которые висят в globalFilters но
    ни на одном компоненте больше не отмечены global=True.

    Возвращает мутированный report["globalFilters"] (in-place + returned
    for chaining).
    """
    grid = report.get("grid") or {}
    components = grid.get("components") or {}
    old_filters = report.get("globalFilters") or {}

    live_aliases: set[str] = set()
    for comp in components.values():
        if not isinstance(comp, dict):
            continue
        cfg = comp.get("config")
        if not isinstance(cfg, dict):
            continue
        axes = cfg.get("axes")
        if not isinstance(axes, list):
            continue
        for axis in axes:
            if not isinstance(axis, dict) or axis.get("type") != "filters":
                continue
            fields = axis.get("fields")
            if not isinstance(fields, list):
                continue
            for f in fields:
                if not isinstance(f, dict):
                    continue
                if not f.get("global"):
                    continue
                alias = f.get("alias")
                if alias:
                    live_aliases.add(alias)

    new_filters = {}
    for alias in live_aliases:
        # Сохраняем существующую запись если есть (включая пустой dict),
        # иначе создаём дефолт. `or` нельзя — empty-dict вернёт default
        # и затрёт legitimately empty entry.
        if alias in old_filters:
            new_filters[alias] = old_filters[alias]
        else:
            new_filters[alias] = {
                "enabled": True,
                "filterMode": "by value",
                "selected": [],
                "sourceValues": {},
            }

    report["globalFilters"] = new_filters
    return new_filters


async def fetch_dataset_alias_map(client, dataset_id: int | None) -> dict[str, str]:
    """Получить {name: alias} map для всех полей dataset.

    нужен builders.py при создании value/category field
    configs, чтобы writе alias из dataset, а не name fallback. Возвращает
    пустой dict при любой ошибке (graceful).
    """
    if not dataset_id:
        return {}
    try:
        resp = await client.api_call("datasets", "get", object_id=dataset_id)
        if not isinstance(resp, dict) or resp.get("status") != 200:
            return {}
        data = resp.get("data", [])
        if not data:
            return {}
        ds = data[0] if isinstance(data, list) else data
        if not isinstance(ds, dict):
            return {}
        fields = ds.get("fields") or []
        if not isinstance(fields, list):
            return {}
        result = {}
        for f in fields:
            if not isinstance(f, dict):
                continue
            name = f.get("name")
            alias = f.get("alias")
            if name and alias:
                result[name] = alias
        return result
    except Exception:
        return {}


async def _lookup_dataset_field_alias(
    client, dataset_id: int | None, field_name: str
) -> str | None:
    """Возвращает alias поля из dataset, или None.

    backbone для filter_field_add: если alias не передан явно, берём
    alias из dataset, а не fallback на `name`. Иначе в filter-компоненте
    отображается техническое имя поля вместо человекочитаемого alias.

    Никаких exceptions — при любой проблеме (нет dataset_id, network error,
    backend 4xx, malformed payload) возвращаем None и caller использует
    fallback `field_name`. ВЕСЬ парсинг под try/except, не только api_call.
    """
    if not dataset_id or not field_name:
        return None
    try:
        resp = await client.api_call("datasets", "get", object_id=dataset_id)
        if not isinstance(resp, dict) or resp.get("status") != 200:
            return None
        data = resp.get("data", [])
        if not data:
            return None
        ds = data[0] if isinstance(data, list) else data
        if not isinstance(ds, dict):
            return None
        fields = ds.get("fields") or []
        if not isinstance(fields, list):
            return None
        for f in fields:
            if not isinstance(f, dict):
                continue
            if f.get("name") == field_name:
                a = f.get("alias")
                return a if a else None
    except Exception:
        return None
    return None


async def _set_global_filter(
    client,
    report_id: int,
    component_idx: int,
    value_field: str | None = None,
    alias: str | None = None,
) -> dict[str, Any]:
    """Set filter value on a FilterControlPanel component AND globalFilters[alias].

    Фронт читает фильтр-state через `report.globalFilters[alias].selected`,
    поэтому без `alias` действие не применяет глобальный фильтр (запись
    идёт только в локальный `cfg.selectedValue` одного компонента).

    Поведение:
      - alias передан → пишем в `data.globalFilters[alias].selected` + ставим
        enabled=True, filterMode="by value". Это реально активирует
        global-фильтр для всех компонентов с тем же alias.
      - alias не передан → старое поведение (только cfg.selectedValue), плюс
        warning в response.

    Также всегда обновляется `cfg.selectedValue` на компоненте для
    обратной совместимости (некоторые версии фронта читают локально).

    Args:
        report_id: Report ID
        component_idx: Index of the FilterControlPanel component
        value_field: Comma-separated filter values to set (e.g., "Moscow,SPb").
                    If None or empty, clears the filter selection.
        alias: Alias из globalFilters (например, "Регион"). ОБЯЗАТЕЛЬНО для
               настоящего глобального фильтра. Получить можно из
               component_filters(action="filter_fields_list", ...).
    """
    report = await _fetch_report(client, report_id)
    grid = report.get("grid", {})
    components = grid.get("components", {})

    component_key = str(component_idx)
    if component_key not in components:
        return {"success": False, "error": f"Component {component_idx} not found"}

    comp = components[component_key]
    comp_type = comp.get("type", "")

    if "Filter" not in comp_type:
        return {
            "success": False,
            "error": f"Component {component_idx} is {comp_type}, not a filter panel"
        }

    cfg = comp.get("config", {})
    warnings: list[str] = []

    # Parse filter values once
    if value_field:
        filter_values = [v.strip() for v in value_field.split(",") if v.strip()]
        cfg["selectedValue"] = filter_values
        cfg["filterApplied"] = True
    else:
        filter_values = []
        cfg["selectedValue"] = []
        cfg["filterApplied"] = False

    # write to data.globalFilters[alias].selected — это то что
    # фронт реально читает для глобального фильтра.
    global_filters = report.get("globalFilters") or {}
    global_updated = False
    if alias:
        if alias not in global_filters:
            return {
                "success": False,
                "error": (
                    f"Alias {alias!r} not in report.globalFilters. "
                    f"Available: {list(global_filters.keys())}. "
                    f"Use component_filters(action='filter_fields_list', "
                    f"report_id={report_id}, component_idx={component_idx}) "
                    f"to inspect actual aliases on the component."
                ),
            }
        entry = global_filters[alias]
        if not isinstance(entry, dict):
            entry = {}
        entry["selected"] = filter_values
        entry["enabled"] = True if filter_values else entry.get("enabled", True)
        entry.setdefault("filterMode", "by value")
        entry.setdefault("sourceValues", {})
        global_filters[alias] = entry
        report["globalFilters"] = global_filters
        global_updated = True
    else:
        warnings.append(
            "alias not provided — only cfg.selectedValue updated on the "
            "component, NOT data.globalFilters[alias]. Frontend reads from "
            "globalFilters, so без alias фильтр на других компонентах не "
            "применится. Передайте alias из filter_fields_list."
        )

    comp["config"] = cfg
    components[component_key] = comp
    grid["components"] = components
    report["grid"] = grid

    err = await _save_report_filters(client, report_id, report)
    if err:
        return {"success": False, **err}

    result = {
        "success": True,
        "message": f"Filter set on component {component_idx}",
        "report_id": report_id,
        "component_idx": component_idx,
        "filter_values": cfg.get("selectedValue", []),
        "global_filter_updated": global_updated,
    }
    if global_updated:
        result["alias"] = alias
    if warnings:
        result["warnings"] = warnings
    return result


async def _reset_global_filters(
    client,
    report_id: int,
) -> dict[str, Any]:
    """Reset all global filters on a report.

    Finds all FilterControlPanel / HierarchicalFilterPanel components
    and clears their selectedValue.
    """
    report = await _fetch_report(client, report_id)
    grid = report.get("grid", {})
    components = grid.get("components", {})

    reset_count = 0
    reset_indices = []

    for key, comp in components.items():
        comp_type = comp.get("type", "")
        if "Filter" in comp_type:
            cfg = comp.get("config", {})
            if cfg.get("selectedValue") or cfg.get("filterApplied"):
                cfg["selectedValue"] = []
                cfg["filterApplied"] = False
                comp["config"] = cfg
                components[key] = comp
                reset_count += 1
                reset_indices.append(int(key))

    # Frontend consumers read report.globalFilters, not the panel's local
    # selectedValue. Clear both stores, including already-empty local panels.
    global_reset_count = 0
    for state in (report.get("globalFilters") or {}).values():
        if isinstance(state, dict) and state.get("selected"):
            state["selected"] = []
            global_reset_count += 1

    if reset_count == 0 and global_reset_count == 0:
        return {
            "success": True,
            "message": "No active filters found",
            "report_id": report_id,
            "reset_count": 0,
        }

    grid["components"] = components
    report["grid"] = grid

    err = await _save_report_filters(client, report_id, report)
    if err:
        return {"success": False, **err}

    return {
        "success": True,
        "message": f"Reset {reset_count} filter(s)",
        "report_id": report_id,
        "reset_count": reset_count,
        "global_reset_count": global_reset_count,
        "reset_indices": reset_indices,
    }


# -------------------------------------------------------------------------
# Filter axis management
# -------------------------------------------------------------------------

async def _filter_fields_list(
    client,
    report_id: int,
    component_idx: int,
) -> dict[str, Any]:
    """List fields on the filters axis of a component."""
    report = await _fetch_report(client, report_id)
    grid = report.get("grid", {})
    components = grid.get("components", {})

    component_key = str(component_idx)
    if component_key not in components:
        return {"success": False, "error": f"Component {component_idx} not found"}

    comp = components[component_key]
    cfg = comp.get("config", {})

    # Find filters axis
    filter_fields: list[dict[str, Any]] = []
    for axis in cfg.get("axes", []):
        if axis.get("type") == "filters":
            for field in axis.get("fields", []):
                filter_fields.append({
                    "name": field.get("name"),
                    "alias": field.get("alias", field.get("name")),
                    "type": field.get("type", "string"),
                    "id": field.get("id"),
                    "datasetId": field.get("datasetId"),
                    "global": field.get("global", False),
                })
            break

    return {
        "success": True,
        "report_id": report_id,
        "component_idx": component_idx,
        "component_type": comp.get("type", ""),
        "filter_fields": filter_fields,
        "count": len(filter_fields),
    }


async def _filter_field_add(
    client,
    report_id: int,
    component_idx: int,
    field_name: str,
    alias: str | None,
    field_type: str | None,
    dataset_id: int | None,
    depends_on: str | None = None,
) -> dict[str, Any]:
    """Add a field to component's filter axis. Also creates globalFilters entry.

    Args:
        depends_on: Alias of parent filter in globalFilters. If set,
            creates cascade dependency (filterBy + precursorsPhase=True).
    """
    report = await _fetch_report(client, report_id)
    grid = report.get("grid", {})
    components = grid.get("components", {})

    component_key = str(component_idx)
    if component_key not in components:
        return {"success": False, "error": f"Component {component_idx} not found"}

    comp = components[component_key]
    cfg = comp.get("config", {})
    axes = cfg.get("axes", [])

    # Find or create filters axis
    filter_axis = None
    for axis in axes:
        if axis.get("type") == "filters":
            filter_axis = axis
            break

    if filter_axis is None:
        filter_axis = {"type": "filters", "fields": []}
        axes.append(filter_axis)

    # Check duplicate
    for existing in filter_axis.get("fields", []):
        if existing.get("name") == field_name:
            return {"success": False, "error": f"Field '{field_name}' already exists on filter axis"}

    # Resolve dataset_id: check component level first, then nested config
    resolved_dataset_id = (
        dataset_id
        or comp.get("dataSetId")
        or comp.get("datasetId")
        or cfg.get("datasetId")
        or cfg.get("dataSetId")
    )

    # Resolve alias: explicit param > dataset field alias > field_name.
    # alias из dataset используется, иначе фильтр-компонент показывает
    # техническое имя поля вместо человекочитаемого alias.
    field_alias = alias
    if not field_alias:
        ds_alias = await _lookup_dataset_field_alias(
            client, resolved_dataset_id, field_name
        )
        field_alias = ds_alias or field_name

    field = {
        "datasetId": resolved_dataset_id,
        "name": field_name,
        "alias": field_alias,
        "type": field_type or "string",
        "agg": None,
        "id": f"{field_name}_{generate_uid()}",
        "global": True,
        "correctable": 0,
        "draft": None,
        "expression": [],
        "filterSqlType": None,
        "inactive": None,
        "order": None,
        "orderIndex": None,
        "prop": {},
        "title": "",
        "title__ru": field_alias,
        "units": None,
        "valueType": "value",
        "bk": 0,
        "calc": "",
    }

    filter_axis["fields"].append(field)

    # Update axes and axesDefault
    cfg["axes"] = axes
    cfg["axesDefault"] = [
        {**ax, "fields": list(ax.get("fields", []))} for ax in axes
    ]

    comp["config"] = cfg
    components[component_key] = comp
    grid["components"] = components
    report["grid"] = grid

    # Create globalFilters entry at report level
    global_filters = report.get("globalFilters", {})
    gf_was_new = field_alias not in global_filters  # capture before mutation
    if gf_was_new:
        global_filters[field_alias] = {
            "enabled": True,
            "filterMode": "by value",
            "selected": [],
            "sourceValues": {},
        }
        report["globalFilters"] = global_filters

    # Cascade dependency: depends_on sets filterBy on the child filter
    cascade_set = False
    if depends_on:
        if depends_on == field_alias:
            return {"success": False, "error": "Filter cannot depend on itself"}
        if depends_on not in global_filters:
            return {
                "success": False,
                "error": (
                    f"Parent filter alias '{depends_on}' not found in "
                    f"globalFilters. Available: {list(global_filters.keys())}"
                ),
            }
        cascade_set = _apply_cascade(global_filters, field_alias, depends_on)

    err = await _save_report_filters(client, report_id, report)
    if err:
        return err

    return {
        "success": True,
        "message": f"Filter field '{field_name}' added to component {component_idx}",
        "report_id": report_id,
        "component_idx": component_idx,
        "field": {"name": field_name, "alias": field_alias, "id": field["id"]},
        "global_filter_created": gf_was_new,
        "cascade_set": cascade_set,
    }


async def _filter_field_remove(
    client,
    report_id: int,
    component_idx: int,
    field_name: str,
) -> dict[str, Any]:
    """Remove a field from component's filter axis by name."""
    report = await _fetch_report(client, report_id)
    grid = report.get("grid", {})
    components = grid.get("components", {})

    component_key = str(component_idx)
    if component_key not in components:
        return {"success": False, "error": f"Component {component_idx} not found"}

    comp = components[component_key]
    cfg = comp.get("config", {})
    axes = cfg.get("axes", [])

    # Find filters axis and remove field
    removed_field = None
    for axis in axes:
        if axis.get("type") == "filters":
            original_fields = axis.get("fields", [])
            new_fields = [f for f in original_fields if f.get("name") != field_name]
            if len(new_fields) == len(original_fields):
                return {"success": False, "error": f"Field '{field_name}' not found on filter axis"}
            removed_field = next(
                f for f in original_fields if f.get("name") == field_name
            )
            axis["fields"] = new_fields
            break

    if removed_field is None:
        return {"success": False, "error": "No filters axis found on this component"}

    # Update axesDefault
    cfg["axes"] = axes
    cfg["axesDefault"] = [
        {**ax, "fields": list(ax.get("fields", []))} for ax in axes
    ]

    comp["config"] = cfg
    components[component_key] = comp
    grid["components"] = components
    report["grid"] = grid

    # единый rebuild globalFilters по живым (alias, global=True) парам.
    # Покрывает alias changes, dead-keys, mismatches между компонентами и
    # filters.
    removed_alias = removed_field.get("alias", field_name)
    before_aliases = set((report.get("globalFilters") or {}).keys())
    _rebuild_global_filters(report)
    after_aliases = set((report.get("globalFilters") or {}).keys())
    global_filter_removed = removed_alias in (before_aliases - after_aliases)

    err = await _save_report_filters(client, report_id, report)
    if err:
        return err

    return {
        "success": True,
        "message": f"Filter field '{field_name}' removed from component {component_idx}",
        "report_id": report_id,
        "component_idx": component_idx,
        "removed_field": field_name,
        "global_filter_removed": global_filter_removed,
    }


# -------------------------------------------------------------------------
# Grid layout helper for filter panels
# -------------------------------------------------------------------------

# используем единый BREAKPOINT_COLS из component_crud
# (hd=60, lg=48, md=40, sm=30, xs=28, xxs=20) чтобы layout filters
# и chart layout не конфликтовали по разным breakpoints.


async def _filters_grid_layout(
    client,
    report_id: int,
    component_indices: list[int],
    cols: int,
    rows: int = 1,
    y_start: int = 0,
    h: int = 3,
) -> dict:
    """Распределить N компонентов равномерно по сетке cols×rows.

    convenience для повторяющегося паттерна «4 фильтра в ряд»
    без ручного вычисления `w = total_cols / N` для каждого breakpoint.
    Production-паттерн: каждый фильтр — отдельный HsFilterControlPanel,
    выстроенный по горизонтали (или сетке).

    Args:
        report_id: ID отчёта
        component_indices: список component_idx в порядке слева-направо,
            сверху-вниз. Например [14, 15, 16, 17].
        cols: число колонок в сетке.
        rows: число рядов (default 1).
        y_start: верхний y для первой строки сетки (default 0).
        h: высота каждой ячейки в grid units (default 3 — typical filter).

    Возвращает {success, layouts_updated: {bp: [entry,...]}, ...}
    Все 6 breakpoints (hd/lg/md/sm/xs/xxs) пересчитываются автоматически
    исходя из своих total_cols.
    """
    if not component_indices:
        return {"success": False, "error": "component_indices required"}
    if cols < 1 or rows < 1:
        return {
            "success": False,
            "error": f"cols={cols}, rows={rows} — both must be >= 1",
        }
    expected = cols * rows
    if len(component_indices) > expected:
        return {
            "success": False,
            "error": (
                f"too many indices: {len(component_indices)} > {cols}x{rows}"
                f"={expected} slots"
            ),
        }

    report = await _fetch_report(client, report_id)
    grid = report.get("grid", {})
    components = grid.get("components", {})
    layouts = grid.get("layouts") or {}

    # Validate all indices exist before mutation
    missing = [i for i in component_indices if str(i) not in components]
    if missing:
        return {
            "success": False,
            "error": f"Components not found: {missing}",
        }

    layouts_updated: dict[str, list[dict]] = {}
    for bp, total_cols in BREAKPOINT_COLS.items():
        w_per_cell = total_cols // cols  # integer division — равные колонки
        bp_layout = layouts.get(bp) or []
        # mutate existing entries in-place by `i` matching, append if absent
        for i, idx in enumerate(component_indices):
            row = i // cols
            col = i % cols
            x = col * w_per_cell
            y = y_start + row * h
            target_i = str(idx)
            found = False
            for entry in bp_layout:
                if str(entry.get("i")) == target_i:
                    entry["x"] = x
                    entry["y"] = y
                    entry["w"] = w_per_cell
                    entry["h"] = h
                    entry["modified"] = True
                    found = True
                    break
            if not found:
                # No existing entry on this breakpoint — append fresh
                bp_layout.append({
                    "x": x, "y": y, "w": w_per_cell, "h": h,
                    "minH": 2, "minW": 2 if bp in ("sm", "xs", "xxs") else 3,
                    "i": target_i,
                    "modified": True,
                    "zIndex": 1,
                    "priority": -1,
                })
        layouts[bp] = bp_layout
        layouts_updated[bp] = [
            e for e in bp_layout if str(e.get("i")) in {str(i) for i in component_indices}
        ]

    grid["layouts"] = layouts
    report["grid"] = grid

    err = await _save_report_filters(client, report_id, report)
    if err:
        return {"success": False, **err}

    # Warn про неравномерное деление (60 // 7 = 8, остаток 4 col пустые)
    warnings = []
    for bp, total_cols in BREAKPOINT_COLS.items():
        if total_cols % cols != 0:
            unused = total_cols - (total_cols // cols) * cols
            warnings.append(
                f"breakpoint {bp}: {total_cols}/{cols}={total_cols//cols} с "
                f"остатком {unused} col — правый край ряда останется пустым"
            )

    result = {
        "success": True,
        "message": (
            f"Distributed {len(component_indices)} components in {cols}x{rows} "
            f"grid across {len(BREAKPOINT_COLS)} breakpoints"
        ),
        "report_id": report_id,
        "component_indices": component_indices,
        "cols": cols,
        "rows": rows,
        "layouts_updated": layouts_updated,
    }
    if warnings:
        result["warnings"] = warnings
    return result


# -------------------------------------------------------------------------
# Cascade filter dependency management
# -------------------------------------------------------------------------

# Контракт globalFilters:
# resetMode: "min" | "max" | null — к какому значению сбрасывать дочерний
# фильтр при смене родителя; resetType: "always" | null — когда сбрасывать.
# Schema-enum в server.py (ResetModeLiteral/ResetTypeLiteral) синхронизирован
# с этими whitelist'ами.
_VALID_RESET_MODES = {"min", "max"}
_VALID_RESET_TYPES = {"always"}


def _apply_cascade(
    global_filters: dict,
    child_alias: str,
    parent_alias: str,
    reset_mode: str | None = None,
    reset_type: str | None = None,
) -> bool:
    """Set filterBy on child filter pointing to parent. Returns True on success.

    Resolves parent's ``name`` (display name) and ``valueAlias`` from
    the globalFilters entry. The ``value`` field in filterBy corresponds
    to the parent alias (which equals the dataset field alias/name).
    """
    parent_entry = global_filters.get(parent_alias)
    if parent_entry is None:
        return False

    # parent_alias IS the key in globalFilters which is the field alias
    # "name" in filterBy = display name = parent_alias
    # "value" = technical field name = parent_alias (same in default case)
    # "valueAlias" = alias = parent_alias
    child_entry = global_filters.get(child_alias, {})
    child_entry["filterBy"] = [{
        "name": parent_alias,
        "value": parent_alias,
        "valueAlias": parent_alias,
        "expression": [],
    }]
    child_entry["precursorsPhase"] = True

    if reset_mode in _VALID_RESET_MODES:
        child_entry["resetMode"] = reset_mode
    if reset_type in _VALID_RESET_TYPES:
        child_entry["resetType"] = reset_type

    global_filters[child_alias] = child_entry
    return True


def _remove_cascade(global_filters: dict, filter_alias: str) -> bool:
    """Remove filterBy cascade from a filter. Returns True if changed."""
    entry = global_filters.get(filter_alias)
    if entry is None:
        return False

    changed = False
    for key in ("filterBy", "precursorsPhase", "resetMode", "resetType"):
        if key in entry:
            del entry[key]
            changed = True
    global_filters[filter_alias] = entry
    return changed


async def _filter_set_cascade(
    client,
    report_id: int,
    filter_alias: str,
    parent_alias: str | None = None,
    reset_mode: str | None = None,
    reset_type: str | None = None,
) -> dict[str, Any]:
    """Set or remove cascade dependency on an existing globalFilter entry.

    If parent_alias is provided, sets filterBy + precursorsPhase on filter_alias.
    If parent_alias is None, removes cascade (filterBy, precursorsPhase,
    resetMode, resetType).

    Args:
        report_id: Report ID.
        filter_alias: Alias of the child filter (key in globalFilters).
        parent_alias: Alias of the parent filter, or None to remove cascade.
        reset_mode: "min" or "max" -- value to reset to when parent changes.
        reset_type: "always" or None -- when to reset.
    """
    report = await _fetch_report(client, report_id)
    global_filters = report.get("globalFilters", {})

    if filter_alias not in global_filters:
        return {
            "success": False,
            "error": (
                f"Filter alias '{filter_alias}' not found in globalFilters. "
                f"Available: {list(global_filters.keys())}"
            ),
        }

    # Remove cascade
    if parent_alias is None:
        changed = _remove_cascade(global_filters, filter_alias)
        if not changed:
            return {
                "success": True,
                "message": f"Filter '{filter_alias}' had no cascade to remove",
                "report_id": report_id,
            }
        report["globalFilters"] = global_filters
        err = await _save_report_filters(client, report_id, report)
        if err:
            return err
        return {
            "success": True,
            "message": f"Cascade removed from filter '{filter_alias}'",
            "report_id": report_id,
            "filter_alias": filter_alias,
        }

    # Set cascade
    if parent_alias not in global_filters:
        return {
            "success": False,
            "error": (
                f"Parent filter alias '{parent_alias}' not found in "
                f"globalFilters. Available: {list(global_filters.keys())}"
            ),
        }

    if parent_alias == filter_alias:
        return {"success": False, "error": "Filter cannot depend on itself"}

    ok = _apply_cascade(
        global_filters, filter_alias, parent_alias, reset_mode, reset_type,
    )
    if not ok:
        return {"success": False, "error": f"Failed to apply cascade on '{filter_alias}'"}

    report["globalFilters"] = global_filters
    err = await _save_report_filters(client, report_id, report)
    if err:
        return err

    entry = global_filters[filter_alias]
    return {
        "success": True,
        "message": (
            f"Cascade set: '{filter_alias}' depends on '{parent_alias}'"
        ),
        "report_id": report_id,
        "filter_alias": filter_alias,
        "parent_alias": parent_alias,
        "filterBy": entry.get("filterBy"),
        "reset_mode": entry.get("resetMode"),
        "reset_type": entry.get("resetType"),
    }
