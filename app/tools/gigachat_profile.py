"""Idempotent, validated dashboard operations; shared Modus builders underneath.

This profile contains no model API client. Every mutation checks the same
security mode as the standard tools, validates before PUT and reads back after.
"""
from __future__ import annotations

import asyncio
from collections import defaultdict
import copy
import hashlib
import json
import math
import re
import weakref
import httpx

from ..core.exceptions import APIError, NotFoundError, ValidationError
from ..core.security import check_action
from ..core.validation import sanitize_html
from .builders import build_component_config
from .component_crud import BREAKPOINT_COLS, _get_component_data, _apply_visual_overrides
from .dataset_operations import _get_dataset
from .gigachat_models import DashboardComponent, DatasetFilter, Metric, Placement, ValueFilter, NativeVisualization
from .gigachat_visualizations import catalog as visualization_catalog, compile_visualization
from .gigachat_geo import canonical_region, validate_tree, validate_points, normalize_native, READABLE_HEIGHTS
from .gigachat_styles import STYLES, style_css
from .gigachat_verification import verification_plan
from .report_operations import report_operations

META = "_mcp_gigachat"
_LOCKS = weakref.WeakKeyDictionary()
TYPES = {"kpi": "HsTotalsPanelV2", "bar": "HsBarAMchartsChart", "line": "HsLineAMchartsChart",
         "donut": "HsPieAMchartsChart", "table": "HsTableReactabularChart", "rich_text": "HsTableReactabularChart", "text": "HsTextBlock"}


class WriteOutcomeError(Exception):
    def __init__(self, message, changed, commit_state):
        super().__init__(message)
        self.changed, self.commit_state = changed, commit_state


def _rows(response):
    if isinstance(response, list):
        return response
    if not isinstance(response, dict) or response.get("status", 200) != 200:
        raise APIError("Recordset query failed", status_code=response.get("status") if isinstance(response, dict) else None)
    data = response.get("data", [])
    if not isinstance(data, list):
        raise ValueError("Recordset data must be a list")
    return data


def _lock(report_id):
    locks = _LOCKS.setdefault(asyncio.get_running_loop(), {})
    return locks.setdefault(report_id, asyncio.Lock())


def _digest(value):
    def canonical(node):
        if isinstance(node, float) and node.is_integer():
            return int(node)
        if isinstance(node, dict):
            return {k: canonical(v) for k, v in node.items()}
        if isinstance(node, list):
            return [canonical(v) for v in node]
        return node

    return hashlib.sha256(json.dumps(canonical(value), sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()


def _state(report):
    return {k: report.get(k, {}) for k in ("grid", "globalFilters", "options")}


def _quote(name):
    return '"' + name.replace('"', '""') + '"'


def sample_profiles(fields, rows):
    profiles = []
    for field in fields:
        values = [r[field["name"]] for r in rows if field["name"] in r]
        distinct = {json.dumps(v, sort_keys=True, ensure_ascii=False, default=str): v for v in values if v is not None}
        profile = {"field": field["name"], "sample_rows": len(rows), "missing_in_sample": len(rows)-len(values),
            "nulls_in_sample": sum(v is None for v in values), "distinct_in_sample": len(distinct), "examples": list(distinct.values())[:5]}
        if field.get("type") in {"number", "numeric", "integer", "int", "float", "double", "decimal"}:
            numeric = []
            for value in values:
                try:
                    number = float(value) if value is not None and not isinstance(value, bool) else math.nan
                    if math.isfinite(number):
                        numeric.append(number)
                except (ValueError, TypeError):
                    pass
            profile.update(min_in_sample=min(numeric, default=None), max_in_sample=max(numeric, default=None))
        profiles.append(profile)
    return profiles


def metric_sql(metric: Metric):
    if metric.kind == "count" and not metric.field:
        return "COUNT(*)"
    if metric.kind in {"sum", "avg", "min", "max", "count"}:
        return f"{metric.kind.upper()}({_quote(metric.field)})"
    if metric.kind == "ratio_of_sums":
        return f"(1.0 * SUM({_quote(metric.numerator)}) / NULLIF(SUM({_quote(metric.denominator)}), 0))"
    if metric.kind == "difference_of_sums":
        return f"(SUM({_quote(metric.numerator)}) - SUM({_quote(metric.denominator)}))"
    if metric.kind == "constant":
        return str(metric.constant)
    return _quote(metric.field)


def display_sql(metric: Metric, component_kind):
    """PostgreSQL display expressions; raw numeric values remain in the spec.

    Text on KPI avoids the renderer rounding 0.75 to 1. Tables use text for
    numeric display so zero is not lost by a falsy-value rendering branch.
    Charts keep numeric values. Unsupported DB functions fail preflight.
    """
    expression = metric_sql(metric)
    if metric.format in {"text", "html"}:
        return expression
    if component_kind in {"bar", "line", "donut"}:
        return f"(100.0 * ({expression}))" if metric.format == "percent" else expression
    # Literal comma/period in TO_CHAR are locale independent; G/D are not.
    picture = "FM999,999,999,999,990" + ("." + "0" * metric.decimals if metric.decimals else "")
    if metric.format == "percent":
        expression = f"(100.0 * ({expression}))"
        picture = "FM999999999990" + ("." + "0" * metric.decimals if metric.decimals else "")
    formatted = f"REPLACE(REPLACE(TO_CHAR(({expression}), '{picture}'), ',', ' '), '.', ',')"
    if metric.format == "percent":
        formatted += " || '%'"
    result = f"CASE WHEN ({metric_sql(metric)}) IS NULL THEN 'н/д' ELSE {formatted} END"
    if metric.cell_rules:
        operators = {"gt": ">", "gte": ">=", "lt": "<", "lte": "<=", "eq": "="}
        colors = "CASE " + " ".join(f"WHEN ({metric_sql(metric)}) {operators[r.operator]} {r.value} THEN '{r.background}'" for r in metric.cell_rules) + " ELSE 'transparent' END"
        result = f"'<span class=\"giga-cell\" style=\"background:' || ({colors}) || '\">' || ({result}) || '</span>'"
    return result


def _fields(component, axis=None):
    return [f for a in component.get("config", {}).get("axes", []) if axis is None or a.get("type") == axis for f in a.get("fields", [])]


def _dataset_id(component):
    ids = {f.get("datasetId") for f in _fields(component) if f.get("datasetId")}
    if len(ids) > 1:
        raise ValueError("One component cannot silently combine different datasets")
    return next(iter(ids), 0)


def _components(report):
    return report.setdefault("grid", {}).setdefault("components", {})


def _find(report, key):
    matches = [(idx, c) for idx, c in _components(report).items() if c.get("config", {}).get(META, {}).get("key") == key]
    if len(matches) > 1:
        raise ValueError(f"Duplicate stable key {key!r}; repair the report before writing")
    return matches[0] if matches else (None, None)


FIELD_DATE_FORMATS = ("DD.MM.YYYY", "DD.MM.YYYY HH:mm", "MM.YYYY", "MMM YYYY", "MMMM YYYY", "MMM", "MMMM", "YYYY", "YYYY-MM-DD")
DATE_TYPES = {"date", "datetime", "timestamp"}


def _apply_field_display(component, field_id, options):
    cfg = component["config"]
    if label := options.get("label"):
        for axes in (cfg.get("axes", []), cfg.get("axesDefault", [])):
            for axis in axes:
                for field in axis.get("fields", []):
                    if field.get("id") == field_id:
                        field.update(alias=label, title=label, title__ru=label)
        if component["type"] == TYPES["table"]:
            cfg.setdefault("columns", {}).setdefault(field_id, {}).update(title=label, title__ru=label)
    if order := options.get("order"):
        for axes in (cfg.get("axes", []), cfg.get("axesDefault", [])):
            for axis in axes:
                for field in axis.get("fields", []):
                    if field.get("id") == field_id:
                        field.update(order=order, orderIndex=0)
                        for name in ("sortByFieldName", "sortByFieldValue", "sortByAgg"):
                            field.pop(name, None)
                    elif field.get("order") in {"asc", "desc"}:
                        field["orderIndex"] = max(1, field.get("orderIndex") or 0)
    if format_name := options.get("date_format"):
        if component["type"] == TYPES["table"]:
            cfg.setdefault("columns", {}).setdefault(field_id, {})["dateFormat"] = format_name
            if options.get("date_type"):
                for axes in (cfg.get("axes", []), cfg.get("axesDefault", [])):
                    for axis in axes:
                        for field in axis.get("fields", []):
                            if field.get("id") == field_id:
                                field["type"] = options["date_type"]
        else:
            cfg["dateFormat"] = format_name
    cfg[META].setdefault("field_display", {}).setdefault(field_id, {}).update(options)


def _apply_axis_title(cfg, role, title):
    for axes in (cfg.get("axes", []), cfg.get("axesDefault", [])):
        for axis in axes:
            if axis.get("type") == role:
                axis.update(title=title, title__ru=title, showtitle=True)
    cfg[META].setdefault("axis_titles", {})[role] = title


def _summaries(report, details=True):
    result = [{"key": c.get("config", {}).get(META, {}).get("key"), "component_idx": int(i),
             "kind": c.get("config", {}).get(META, {}).get("kind"), "title": c.get("config", {}).get("caption"),
             "dataset_id": _dataset_id(c) if c.get("config", {}).get(META) else None,
             "fields": [{"name": f.get("name"), "label": f.get("title") or f.get("alias"), "aggregation": f.get("agg")} for f in _fields(c) if f.get("name")],
             "spec": c.get("config", {}).get(META, {}).get("spec")} for i, c in _components(report).items()]
    if details:
        for item, component in zip(result, _components(report).values()):
            meta = component.get("config", {}).get(META, {})
            if meta.get("kind") == "filter":
                item["filter"] = meta["filter"]
            if display := meta.get("field_display"):
                item["field_display"] = list(display.values())
            if component.get("type") in {TYPES["bar"], TYPES["line"]}:
                cfg = component["config"]
                item["chart_type"] = "bar" if component["type"] == TYPES["bar"] else "line"
                item["chart_axes"] = {a["type"]: {"title":a.get("title__ru") or a.get("title"),
                    "fields":[{k:f.get(k) for k in ("name", "type", "alias", "order")} for f in a.get("fields", [])]}
                    for a in cfg.get("axes", []) if a.get("type") in {"categories", "values"}}
    if not details:
        for item in result:
            item.pop("fields")
            item.pop("spec")
    return result


def arrange(report):
    """Reflow managed components, using the portal's columns at each breakpoint."""
    managed = [(i, c) for i, c in _components(report).items() if c.get("config", {}).get(META)]
    for _, component in managed:
        minimum = READABLE_HEIGHTS.get(component.get("type"), 0)
        if component["config"][META].get("spec", {}).get("height", 0) < minimum:
            raise ValueError(f"READABLE_HEIGHT: {component['config'][META]['key']} requires height >= {minimum}; preserve its field bindings and use giga_arrange_report")
    groups = defaultdict(list)
    for idx, component in managed:
        spec = component["config"][META].get("spec", {})
        groups[spec.get("row", 2)].append((idx, component))
    layouts = report["grid"].setdefault("layouts", {})
    for breakpoint, columns in BREAKPOINT_COLS.items():
        ids = {i for i, _ in managed}
        fixed = [x for x in layouts.get(breakpoint, []) if str(x.get("i")) not in ids]
        y = max((x.get("y", 0) + x.get("h", 1) + 1 for x in fixed), default=0)
        items = []
        for row in sorted(groups):
            group = sorted(groups[row], key=lambda x: int(x[0]))
            all_kpi=all(c['config'][META]['kind']=='kpi' for _,c in group)
            chunk_size = min(len(group),columns//2) if all_kpi and breakpoint in {'hd','lg','md'} else 2 if breakpoint in {'hd','lg','md'} else 3 if all_kpi else 1
            controls=[item for item in group if item[1]['config'][META]['kind']=='filter']
            visual_group=[item for item in group if item not in controls]
            if controls and any(c['config'][META]['kind'] not in {'text','filter'} for _,c in visual_group):
                base_chunks=[controls]+[visual_group[n:n+chunk_size] for n in range(0,len(visual_group),chunk_size)]
            else:
                base_chunks=[group[n:n+chunk_size] for n in range(0,len(group),chunk_size)]
            for chunk in base_chunks:
                # Dense tabular axes and the national tile dictionary need
                # horizontal space. Reflow without changing any source roles.
                wide = {'HsPivotChart','HsParallelCoordsChart','HsTilemapChart'}
                if breakpoint=='md':wide.add('HsSunburstChart')
                if breakpoint in {'hd','lg','md'} and any(c.get('type') in wide for _,c in chunk) and len(chunk)>1:
                    chunks = [[item] for item in chunk]
                else:
                    chunks = [chunk]
                for part in chunks:
                    weights = [c['config'][META].get('spec',{}).get('width',1) for _,c in part]
                    total = sum(weights)
                    widths = [columns * weight // total for weight in weights]
                    for index in range(columns - sum(widths)):
                        widths[index % len(widths)] += 1
                    if min(widths) < 2:
                        raise ValueError('Layout component is narrower than two columns')
                    x, height = 0, max(c['config'][META].get('spec',{}).get('height',4) for _,c in part)
                    for (idx,component),width in zip(part,widths):
                        items.append({'i':idx,'x':x,'y':y,'w':width,'h':height,'minW':2,'minH':2,
                                      'modified':True,'group':-1,'zIndex':int(idx)+1,'priority':-1})
                        x += width
                    y += height + 1
        layouts[breakpoint] = fixed + items
    report.setdefault("options", {}).update(allowOverlapMode=False, freePaneMovement=False, recalculatedCellMode=True, noGapMode=False)


def layout_issues(report):
    issues = []
    ids = set(_components(report))
    keys = [c.get("config", {}).get(META, {}).get("key") for c in _components(report).values() if c.get("config", {}).get(META)]
    if len(keys) != len(set(keys)) or any(not k for k in keys):
        issues.append("Missing or duplicate stable component keys")
    for bp, columns in BREAKPOINT_COLS.items():
        seen, boxes = set(), report.get("grid", {}).get("layouts", {}).get(bp, [])
        for a in boxes:
            idx = str(a.get("i"))
            if idx in seen or idx not in ids:
                issues.append(f"{bp}: duplicate or dangling component {idx}")
            seen.add(idx)
            if min(a.get("x", -1), a.get("y", -1)) < 0 or min(a.get("w", 0), a.get("h", 0)) <= 0 or a.get("x", 0) + a.get("w", 0) > columns:
                issues.append(f"{bp}: component {idx} outside grid")
        for i, a in enumerate(boxes):
            for b in boxes[i + 1:]:
                if a["x"] < b["x"] + b["w"] and b["x"] < a["x"] + a["w"] and a["y"] < b["y"] + b["h"] and b["y"] < a["y"] + a["h"]:
                    issues.append(f"{bp}: overlap {a['i']}/{b['i']}")
        for missing in sorted(ids - seen):
            issues.append(f"{bp}: missing layout for component {missing}")
    return issues


def build(spec: DashboardComponent, report_id, field_map):
    """Compile complete component state; no partially applied field updates."""
    if isinstance(spec, NativeVisualization):
        def validate(metric, fields):
            build(DashboardComponent(key="validation", kind="table" if metric.kind == "raw" else "kpi", title=metric.label,
                dataset_id=spec.dataset_id, metrics=[metric]), report_id, fields)
        return compile_visualization(spec, report_id, field_map, metric_sql, validate)
    needed = [x for x in (spec.category, spec.series) if x]
    for metric in spec.metrics:
        needed += [metric.numerator, metric.denominator] if metric.kind in {"ratio_of_sums", "difference_of_sums"} else ([metric.field] if metric.kind != "constant" and not (metric.kind == "count" and not metric.field) else [])
    missing = sorted(set(needed) - set(field_map))
    if missing:
        raise ValueError(f"Unknown dataset fields: {missing}. Available fields: {sorted(field_map)}")
    for metric in spec.metrics:
        numeric_names = [metric.numerator, metric.denominator] if metric.kind in {"ratio_of_sums", "difference_of_sums"} else ([metric.field] if metric.kind in {"sum", "avg", "min", "max"} or metric.format in {"number", "rubles", "percent"} and metric.kind == "raw" else [])
        if any(field_map[name].get("type") not in {"number", "numeric", "integer", "int", "float", "double", "decimal"} for name in numeric_names):
            raise ValueError(f"Numeric metric requires numeric fields: {numeric_names}")
    data_fields = [m.field or m.numerator or "value" for m in spec.metrics]
    component = build_component_config(TYPES[spec.kind], spec.title, spec.dataset_id or None,
        spec.category or None, data_fields, "number", "sum" if spec.kind not in {"table", "rich_text", "text"} else None,
        text_content=sanitize_html(spec.text), series_field=spec.series or None)
    if "config" not in component:
        raise ValueError(component.get("error", "Unsupported component"))
    cfg = component["config"]
    cfg[META] = {"version": 1, "key": spec.key, "kind": spec.kind, "spec": spec.model_dump()}
    # Replace the complete values axis. Generated fields have deterministic IDs.
    values = []
    for index, metric in enumerate(spec.metrics):
        uid = "giga_" + _digest([report_id, spec.key, index])[:20]
        raw_text = metric.kind == "raw" and metric.format in {"text", "html"}
        source_type = field_map.get(metric.field, {}).get("type")
        raw_type = source_type if metric.format == "text" and source_type in DATE_TYPES else "string"
        expression = display_sql(metric, spec.kind)
        values.append({"id": uid, "name": metric.field if raw_text else "{Вычисляемое поле}_" + uid + "_name",
                       "datasetId": spec.dataset_id, "type": raw_type if raw_text else "calculated",
                       "alias": metric.label, "title": metric.label, "title__ru": metric.label,
                       "calc": "" if raw_text else expression, "draft": None if raw_text else True,
                       "agg": None, "units": None, "expression": []})
    for axis in cfg.get("axes", []):
        if axis.get("type") == "values":
            axis["fields"] = values
            if spec.kind=='bar':axis['rangeMode']='tozero'
            if spec.kind in {"bar", "line", "donut"}:
                axis["selectedFieldIndex"] = -2  # Native renderer: all values, including target/color.
        elif axis.get("type") in {"categories", "series"}:
            for f in axis.get("fields", []):
                f["id"] = "giga_" + _digest([report_id, spec.key, axis["type"], f["name"]])[:20]
                f["type"] = field_map[f["name"]].get("type", "string")
                f["alias"] = field_map[f["name"]].get("alias") or f["name"]
                if spec.kind == "line" and axis["type"] == "categories":
                    f["order"] = "asc"
                    f["orderIndex"] = 0
    if spec.kind in {"table", "rich_text"}:
        cfg["columns"] = {f["id"]: {"title": m.label, "title__ru": m.label, "lineWrap": True,
            "isHtml": m.format == "html" or bool(m.cell_rules), "emptyAsNil": False, "columnNullVisible": True,
            "valueSeparator": False, "visibleOrder": i + 1} for i, (f, m) in enumerate(zip(values, spec.metrics))}
        cfg["settings"].update(AllowVirtualization=False, AllowPagination=False, AllowResponsible=False, AllowMultilineHeader=True)
    if spec.kind == "kpi":
        cfg.update(precision=spec.metrics[0].decimals, showtitle=False)
        for visual in cfg["visuals"]:
            if visual["anchor"] in {"trend", "subcaption"}:
                visual["visible"] = False
    if spec.kind in {"bar", "line"}:
        cfg, warnings = _apply_visual_overrides(cfg, TYPES[spec.kind], orientation="horizontal" if spec.horizontal else "vertical",
            stacking="normal" if spec.stacked else "none", legend_position="bottom", labels_visible=spec.kind == "bar")
        if warnings:
            raise ValueError("Unsupported visual settings: " + "; ".join(warnings))
        for axis in cfg["axes"]:
            if axis["type"] == "values":
                percent = all(m.format == "percent" for m in spec.metrics)
                axis.update(decimalPlaces=max(m.decimals for m in spec.metrics),
                    showtitle=percent, title="Выполнение плана, %" if percent else "", title__ru="Выполнение плана, %" if percent else "")
        cfg["precision"] = max(m.decimals for m in spec.metrics)
        if spec.kind == "bar":
            cfg["labels"].update(inner={"color": "#FFFFFF", "fontsize": 13}, outer={"fontsize": 13})
            if spec.series:
                cfg["balloonTemplate"] = "[[title]]: [[value]] ([[percents]]%)"
        if spec.kind == "line":
            for i, metric in enumerate(spec.metrics):
                cfg["visuals"].append({"anchor": values[i]["id"], "type": "line", "lineColor": "#9AA5B5" if metric.kind == "constant" else "#4D7FA8", "lineMode": "dash" if metric.kind == "constant" else "solid", "lineWidth": 2})
    if spec.kind == "donut":
        cfg.update(showDonut=True, innerRadius="60%", labelsTemplate="[[percents]]%")
    if spec.colors:
        cfg["colors"] = [x.color for x in spec.colors]
        status_axis = "series" if spec.series else "categories"
        for axis in cfg.get("axes", []):
            if axis.get("type") == status_axis:
                for field in axis.get("fields", []):
                    cases = " ".join("WHEN '" + item.value.replace("'", "''") + f"' THEN {i}" for i, item in enumerate(spec.colors))
                    sort_name = "{Вычисляемое поле}_giga_sort_" + _digest([report_id, spec.key, field["name"]])[:12] + "_name"
                    field.update(order="asc", orderIndex=1, sortByFieldName="Порядок статуса", sortByAgg="max",
                        sortByFieldValue=sort_name + "$!$CASE " + _quote(field["name"]) + " " + cases + " ELSE 999 END")
        for item in spec.colors:
            cfg.setdefault("visuals", []).append({"anchor": item.value, "fillColor": item.color, "lineColor": item.color})
        if spec.kind == "donut":
            # The native pie adapter takes slice colors from a color value field;
            # category visual.fillColor is ignored by that adapter.
            uid = "giga_" + _digest([report_id, spec.key, "color"])[:20]
            cases = " ".join("WHEN '" + item.value.replace("'", "''") + "' THEN '" + item.color + "'" for item in spec.colors)
            values.append({"id": uid, "name": "{Вычисляемое поле}_" + uid + "_name", "datasetId": spec.dataset_id,
                "type": "calculated", "alias": "Цвет статуса", "valueType": "color", "agg": None,
                "calc": f"CASE {_quote(spec.category)} {cases} ELSE '#9AA5B5' END", "draft": True})
    cfg["axesDefault"] = copy.deepcopy(cfg.get("axes", []))
    component["config"] = cfg
    return component


def apply_theme(report):
    """Only generated panel IDs are targeted; preserve caller CSS outside block."""
    css = []
    for idx, comp in _components(report).items():
        meta = comp.get("config", {}).get(META)
        if not meta:
            continue
        selector = f"#panel_{idx}"
        css += [f".hsGridLayout:has(>{selector}){{background:#F5F7FA;}}"]
        css += [f"{selector}{{background:#fff;color:#333;border:1px solid #DCE2E9;border-radius:6px;font-family:GolosUIWebRegular,Arial,sans-serif;transition:border-color 150ms,box-shadow 150ms;}}",
                f"{selector}:hover{{border-color:#9AA5B5;box-shadow:0 1px 4px #00000012;}}",
                f"{selector} .componentHeader{{font-size:16px;font-weight:600;text-transform:none;}}",
                f"{selector} .amcharts-legend-label{{font-size:13px;font-weight:400;}}"]
        if meta["kind"] in {"table", "rich_text"}:
            css += [f"{selector} .componentContainerForTable,{selector} .hs-table__main{{overflow:visible!important;}}",
                    f"{selector} table{{width:100%;border-collapse:collapse;}}",
                    f"{selector} td,{selector} th{{font-size:14px;padding:9px 10px;}}"]
            css += [f"{selector} .giga-cell{{display:block;padding:6px 8px;border-radius:3px;text-align:right;}}"]
        if meta["kind"] == "table":
            # Native tbody has a separate fixed scroll area. Checking only the
            # outer component misses overflow from wrapped column headings.
            css += [f"{selector} tbody{{height:auto!important;max-height:none!important;overflow:visible!important;}}",
                    f"{selector} .componentBody{{overflow:auto!important;}}"]
        if comp.get('type') == 'HsParallelCoordsChart':
            css += [f'{selector} svg text{{font-size:14px!important;fill:#20313F!important;}}']
        if comp.get('type') == 'HsTilemapChart':
            css += [f'{selector} .tile-value0{{fill:#111827!important;paint-order:stroke;stroke:#fff!important;stroke-width:3px!important;font-weight:700;font-size:14px!important;}}',
                    f'{selector} .tile-label{{fill:#111827!important;font-size:13px!important;}}',
                    f'{selector} .componentBody::after{{content:"Серые регионы — нет данных";position:absolute;bottom:6px;left:12px;font-size:13px;color:#526474;background:#ffffffed;padding:3px 6px;border-radius:3px;pointer-events:none;}}']
        if meta["kind"] == "rich_text":
            css += [f"{selector} thead,{selector} tfoot{{display:none!important;}}",
                    f"{selector} tbody{{display:grid!important;height:auto!important;overflow:visible!important;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px;}}",
                    f"{selector} tbody:has(>tr:nth-child(1):last-child){{grid-template-columns:1fr;}}",
                    f"{selector} tbody>tr{{display:block;min-width:0;}}{selector} td{{display:block;width:auto!important;min-width:0!important;max-width:100%!important;white-space:normal!important;font-size:16px;}}",
                    f"{selector} .htmlWrapper article{{padding:12px;border:1px solid #DCE2E9;border-radius:6px;}}",
                    f"{selector} h3{{font-size:18px;margin:0 0 8px;}}{selector} p{{margin:6px 0;line-height:1.4;}}"]
            css += [f"{selector} .htmlWrapper,{selector} .htmlWrapper *{{white-space:normal!important;overflow-wrap:anywhere;max-width:100%;box-sizing:border-box;}}",
                    f"{selector}{{height:auto!important;}}",
                    f"{selector} .hsGridPanelContainer,{selector} .inner,{selector} .frontSide,{selector} .hsChartContainer,{selector} .hs-table__main,{selector} .componentBody,{selector} .componentContainerForTable{{position:relative!important;height:auto!important;min-height:0!important;overflow:visible!important;}}"]
        if meta["kind"] == "text":
            css += [f"{selector} h1,{selector} h2,{selector} h3{{font-family:Montserrat,GolosUIWebRegular,Arial,sans-serif;font-size:26px;line-height:1.1;font-weight:700;margin:0;}}",
                    f"{selector} p{{font-size:14px;line-height:1.2;margin:4px 0 0;font-style:normal!important;color:#667085;}}",
                    f"{selector} .hsTextBlock .componentBody>div{{padding:4px 10px!important;overflow:visible!important;}}"]
        if meta["kind"] == "kpi":
            css += [f"{selector} .hsTotalsPanelV2{{justify-content:center!important;}}",
                    f"{selector} .value{{flex:0 0 auto!important;font-size:32px!important;font-weight:700!important;line-height:1.2;white-space:normal!important;margin:8px 8px 4px!important;text-align:center;}}",
                    f"{selector} .hsTotalsPanelV2>div:nth-child(2){{flex:0 0 auto!important;}}",
                    f"{selector} .caption{{flex:0 0 auto!important;height:auto!important;max-height:none!important;overflow:visible!important;font-size:15px!important;line-height:1.2;margin:0 8px!important;text-align:center;white-space:normal!important;}}",
                    f"{selector} .caption .titleText{{white-space:normal!important;overflow:visible!important;}}"]
        if meta["kind"] == "filter":
            # Grid siblings otherwise paint over the dropdown: options remain
            # in the accessibility tree but clicks hit the following chart.
            css += [f"{selector}{{z-index:1000!important;}}",
                    f"{selector} .hsGridPanelContainer,{selector} .inner,{selector} .frontSide{{overflow:visible!important;}}",
                    f"{selector} .r-ss-dropdown{{z-index:100!important;}}"]
    options = report.setdefault("options", {})
    css.append(style_css(options.get("_mcp_gigachat_style", "corporate_clean"),[i for i,c in _components(report).items() if c.get("config",{}).get(META)]))
    old = options.get("CSStext", "")
    old = re.sub(r"/\* modus-gigachat:start \*/.*?/\* modus-gigachat:end \*/", "", old, flags=re.S).strip()
    report["options"]["CSStext"] = old + "\n/* modus-gigachat:start */\n" + "\n".join(css) + "\n/* modus-gigachat:end */"


class _Preview:
    def __init__(self, client, report):
        self.client, self.report = client, report

    async def api_call(self, entity, action, object_id=None, **kwargs):
        if entity == "reports" and action == "get":
            return {"status": 200, "data": [self.report]}
        if entity != "recordsets" or action != "create":
            raise RuntimeError("Preview cannot mutate portal configuration")
        return await self.client.api_call(entity, action, object_id=object_id, **kwargs)


class GigaChatProfile:
    def __init__(self, client):
        self.client = client

    async def validate_geography(self, spec, field_map, report=None, component=None):
        if not isinstance(spec, NativeVisualization) or spec.component_type not in {"HsTreeGraph", "HsMapLeafletChart", "HsTilemapChart"}:
            return
        axes = {a.axis:a for a in spec.axes}
        build(spec, 1, field_map)  # Field/type validation precedes any query.
        if spec.component_type == "HsTreeGraph":
            names=[axes[a].fields[0] for a in ("identity","linkage")]
            if spec.size_field:names.append(spec.size_field)
        elif spec.component_type == "HsMapLeafletChart":
            names=axes["categories"].fields+[spec.latitude_field,spec.longitude_field]
        else:
            names=axes["categories"].fields
        names=list(dict.fromkeys(names))
        select=[{"lvl":0,"name":n,"alias":f"geometry_{i}","fieldAlias":n,"calc":"","aggr":""} for i,n in enumerate(names)]
        where=[]
        if report and component:
            for field in _fields(component,"filters"):
                if field.get("global"):
                    selection=report.get("globalFilters",{}).get(field.get("alias"),{})
                    if selection.get("enabled",True) and selection.get("selected"):
                        values=selection["selected"]
                        where.append({"lvl":0,"name":field["name"],"values":values,"operators":["="]*len(values),"not":False,"logicOr":int(len(values)>1)})
        group=select if spec.component_type=="HsTilemapChart" else []
        if spec.component_type=="HsTilemapChart":where=[]  # Stable dictionary covers every slice.
        rows=_rows(await self.client.api_call("recordsets","create",object_id=spec.dataset_id,data=[{"select":select,"group":group,"where":where,"order":[],"having":{"condition":""},"series":{"enable":0},"limit":10001}]))
        if len(rows)>10000:
            raise ValueError("Geometry validation exceeds 10000 rows; narrow or preaggregate the source explicitly")
        rows=[{n:r[f"geometry_{i}"] for i,n in enumerate(names)} for r in rows]
        if spec.component_type=="HsTreeGraph":
            validate_tree(rows,axes["identity"].fields[0],axes["linkage"].fields[0])
            if spec.size_field and any(isinstance(r[spec.size_field],bool) or not isinstance(r[spec.size_field],(int,float)) or not math.isfinite(r[spec.size_field]) or r[spec.size_field]<0 for r in rows):
                raise ValueError("Tree size must be finite, non-null and nonnegative")
        elif spec.component_type=="HsMapLeafletChart":
            validate_points(rows,axes["categories"].fields,spec.latitude_field,spec.longitude_field)
        else:
            name=names[0]
            field_map[name]["_tilemap_mapping"]={r[name]:canonical_region(r[name]) for r in rows}

    async def validate_report_geography(self, report):
        for c in _components(report).values():
            meta=c.get("config",{}).get(META,{})
            if meta.get("kind")=="native":
                spec=NativeVisualization.model_validate(meta["spec"])
                if spec.component_type in {"HsTreeGraph","HsMapLeafletChart","HsTilemapChart"}:
                    await self.validate_geography(spec,(await self.schema(spec.dataset_id))[1],report,c)

    async def fetch(self, report_id):
        response = await self.client.api_call("reports", "get", object_id=report_id)
        if response.get("status") != 200 or not response.get("data"):
            raise NotFoundError(f"Report {report_id} not found", object_id=report_id)
        return copy.deepcopy(response["data"][0])

    async def schema(self, dataset_id):
        ds = (await _get_dataset(self.client, dataset_id))["dataset"]
        return ds, {f["name"]: f for f in ds["fields"]}

    async def save(self, before, candidate, report_id):
        expected = _digest(_state(candidate))
        changed = _digest(_state(before)) != expected
        if changed:
            try:
                response = await self.client.api_call("reports", "update", object_id=report_id, data=[candidate])
            except (APIError, httpx.TransportError, TimeoutError, ConnectionError) as error:
                raise WriteOutcomeError("Write outcome unknown; inspect before retry", None, "unknown") from error
            if response.get("status") != 200:
                raise WriteOutcomeError("Write was not confirmed; inspect before retry", None, "unknown")
        try:
            actual = await self.fetch(report_id) if changed else candidate
        except (APIError, NotFoundError, httpx.TransportError, TimeoutError, ConnectionError) as error:
            raise WriteOutcomeError("PUT acknowledged, readback failed; inspect before retry", None, "acknowledged_readback_failed") from error
        verified = _digest(_state(actual)) == expected
        actual_changed = _digest(_state(before)) != _digest(_state(actual))
        return {"success": verified, "changed": actual_changed, "write_attempted": changed, "configuration_verified": verified,
                "error": "" if verified else "READBACK_MISMATCH: saved configuration differs; inspect before retry",
                "report_id": report_id, "fingerprint": _digest(_state(actual)), "components": _summaries(actual, details=False), "browser_verified": False}

    async def read_dataset(self, dataset_id, limit=20):
        check_action("get")
        if not 1 <= limit <= 100:
            raise ValueError("limit must be 1..100")
        ds, _ = await self.schema(dataset_id)
        params = {"select": [], "where": [], "group": [], "order": [], "having": {"condition": ""}, "series": {"enable": 0}, "limit": limit + 1}
        response = await self.client.api_call("recordsets", "create", object_id=dataset_id, data=[params])
        rows = _rows(response)
        return {"success": True, "dataset_id": dataset_id, "name": ds["name"], "fields": ds["fields"], "fields_count": len(ds["fields"]), "rows": rows[:limit], "truncated": len(rows) > limit,
                "sample_scope": "First returned rows only; sample uniqueness/range does not establish dataset-wide grain or bounds",
                "sample_profiles": sample_profiles(ds["fields"], rows[:limit])}

    async def query_dataset(self, dataset_id, metrics, group_by=None, filters=None, limit=100):
        """Independent source probe. No report ID, SQL input, or write operation."""
        check_action("get")
        if not 1 <= limit <= 1000 or not metrics or len(metrics) > 24:
            raise ValueError("Supply 1..24 metrics and limit 1..1000")
        group_by = group_by or []
        filters = [f if isinstance(f, ValueFilter) else ValueFilter.model_validate(f) for f in (filters or [])]
        metrics = [m if isinstance(m, Metric) else Metric.model_validate(m) for m in metrics]
        ds, field_map = await self.schema(dataset_id)
        # Source probes return typed raw values, not formatted dashboard cells.
        metrics = [m.model_copy(update={"format": "text"}) if m.kind == "raw" and m.format == "number"
                   and field_map.get(m.field, {}).get("type") in {"string", "text", "date", "datetime", "timestamp", "time"} else m for m in metrics]
        if len(group_by) != len(set(group_by)) or any(n not in field_map for n in group_by + [f.field for f in filters]):
            raise ValueError("Unknown or duplicate grouping/filter field; use exact dataset names")
        if len({f.field for f in filters}) != len(filters):
            raise ValueError("Use one filter per field with all desired values")
        aggregated = any(m.kind != "raw" for m in metrics)
        for index, metric in enumerate(metrics):
            validation = DashboardComponent(key=f"probe_{index}", kind="table" if metric.kind == "raw" else "kpi",
                title=metric.label, dataset_id=dataset_id, metrics=[metric])
            build(validation, 0, field_map)  # Type/name validation, no query side effects.
        ungrouped_raw=[m for m in metrics if m.kind=='raw' and m.field not in group_by]
        if aggregated and ungrouped_raw:
            detail_metrics=list(ungrouped_raw)
            for name in group_by:
                if name not in {m.field for m in detail_metrics}:
                    detail_metrics.append(Metric(kind='raw',field=name,label=name))
            if len(detail_metrics)>24:
                raise ValueError('DETAIL_COLUMN_LIMIT: raw details plus grouping keys exceed 24 columns. Request the aggregate and smaller detail probes separately; no fields have been dropped.')
            aggregate=await self.query_dataset(dataset_id,[m for m in metrics if m not in ungrouped_raw],group_by,filters,limit)
            detail=await self.query_dataset(dataset_id,detail_metrics,[],filters,limit)
            truncated=aggregate['truncated'] or detail['truncated']
            return {**aggregate,'diagnostic_detail':detail,'grain_split':True,
                    'aggregate_query_complete':aggregate['query_complete'],
                    'query_complete':not truncated,'truncated':truncated,
                    'atomic_snapshot_guaranteed':False,
                    'scope':aggregate['scope']+' Aggregate and raw detail are two independent reads, not a guaranteed transactional snapshot. Grouping keys are included in detail; never join the blocks by row position.',
                    'next_action':('Результат УСЕЧЁН: одна из двух проверок неполна. Увеличь limit до 1000; если детали всё ещё усечены, не объявляй их полными. Для отдельной проверки агрегата запроси только его метрики.' if truncated else
                        'Запрос завершён: разные зерна явно разделены. rows/columns содержат агрегаты в исходной группировке; diagnostic_detail.rows/columns — исходные raw-строки с ключами групп. Все запрошенные поля возвращены, агрегации не подставлялись. Не объединяй блоки по позиции строки. Сопоставь агрегаты с отчётом и переходи дальше; повторять успешный запрос не нужно.')}
        if ungrouped_raw and group_by:
            raise ValueError('RAW_GROUPING_CONFLICT: pure raw fields must be in group_by, or use group_by=[] to retain original rows. Aggregation is never inferred.')
        def direct(name, alias):
            return {"lvl": 0, "name": name, "alias": alias, "calc": "", "aggr": "", "fieldAlias": name}
        select = [direct(name, f"group_{i}") for i, name in enumerate(group_by)]
        columns = [{"name": f"group_{i}", "field": name} for i, name in enumerate(group_by)]
        for i, metric in enumerate(metrics):
            select.append({"lvl": 0, "name": f"{{Вычисляемое поле}}_giga_probe_{i}", "alias": f"metric_{i}",
                "calc": metric_sql(metric), "aggr": "", "fieldAlias": metric.label})
            columns.append({"name": f"metric_{i}", "metric": metric.model_dump()})
        if aggregated:
            select.append({"lvl": 0, "name": "{Вычисляемое поле}_giga_probe_rows", "alias": "source_row_count", "calc": "COUNT(*)", "aggr": "", "fieldAlias": "Source rows"})
        params = {"select": select, "where": [{"lvl": 0, "name": f.field, "not": False, "values": f.values,
            "operators": ["="] * len(f.values), "logicOr": int(len(f.values) > 1)} for f in filters],
            "group": [direct(name, f"group_{i}") for i, name in enumerate(group_by)], "order": [],
            "having": {"condition": ""}, "series": {"enable": 0}, "limit": limit + 1}
        rows = _rows(await self.client.api_call("recordsets", "create", object_id=dataset_id, data=[params]))
        return {"success": True, "dataset_id": dataset_id, "dataset_name": ds["name"], "columns": columns,
            "rows": rows[:limit], "truncated": len(rows) > limit, "criteria": {"group_by": group_by, "filters": [f.model_dump() for f in filters]},
            "scope": "Source query independent of report configuration. Numeric percent values are fractions. Aggregates cover filtered source; result groups/rows are limited.",
            "business_meaning_verified": False,"query_complete":len(rows)<=limit,"execution_completed":True,
            "next_action":("Результат УСЕЧЁН: полной проверки ещё нет. Повтори те же поля и группировку с limit=1000 (максимум). Если при 1000 всё ещё truncated=true, явно обозначь неполноту; не объявляй успех." if len(rows)>limit else
                "Запрос успешно завершён без усечения. Не повторяйте его без изменения задачи. Сопоставьте числа с отчётом и переходите дальше. business_meaning_verified=false обозначает границу доказательства, а не ошибку запроса.")}

    async def find_datasets(self, name, limit=10):
        check_action("list")
        if not name.strip() or not 1 <= limit <= 100:
            raise ValueError("Supply a dataset name and limit 1..100")
        rows = _rows(await self.client.api_call("datasets", "list"))
        exact = [r for r in rows if r.get("name", "").casefold() == name.casefold() or r.get("caption", "").casefold() == name.casefold()]
        matches = exact or [r for r in rows if name.casefold() in (r.get("name", "") + " " + r.get("caption", "")).casefold()]
        return {"success": True, "exact_match": bool(exact), "total": len(matches), "truncated": len(matches) > limit,
                "items": [{"dataset_id": r["ID"], "name": r.get("name"), "caption": r.get("caption")} for r in matches[:limit]]}

    async def list_groups(self):
        check_action("groups_list")
        rows = _rows(await self.client.api_call("reportgroups", "list"))
        return {"success": True, "items": [{"group_id": r["ID"], "name": r.get("name"), "caption": r.get("caption")} for r in rows]}

    async def list_visualizations(self):
        check_action("get")
        available = {r.get("type"): r for r in _rows(await self.client.api_call("components", "list"))}
        return {"success": True, "items": [{**item, "available_on_portal": item["component_type"] in available,
            "caption": available.get(item["component_type"], {}).get("caption")} for item in visualization_catalog()],
            "scope": "Native builder capabilities and portal catalog; does not establish successful rendering"}

    async def find_many(self, names, limit=10):
        if not names or len(names) != len(set(names)):
            raise ValueError("Supply unique dataset names")
        results = [{"query": name, **await self.find_datasets(name, limit)} for name in names]
        items = {item["dataset_id"]: item for result in results for item in result["items"]}
        return {"success": True, "exact_match": all(r["exact_match"] for r in results),
                "items": list(items.values()), "results": results}

    async def create_report(self, name, caption, group_id):
        check_action("create")
        if not re.fullmatch(r"[a-z][a-z0-9_]{2,100}", name) or group_id <= 0 or not caption.strip():
            raise ValueError("Report requires technical name, caption and positive group_id")
        async with _lock(("create", name, group_id)):
            return await self._create_report(name, caption, group_id)

    async def _create_report(self, name, caption, group_id):
        # No hidden fallback to another group/report.
        response = await self.client.api_call("reports", "list")
        matches = [r for r in _rows(response) if r.get("name") == name]
        if matches:
            if len(matches) != 1 or matches[0].get("groupID", matches[0].get("report_group_id")) != group_id:
                raise ValueError("Report name is ambiguous or belongs to a different group")
            return {"success": True, "changed": False, "report_id": matches[0]["ID"]}
        try:
            result = await report_operations(self.client, "create", name=name, caption=caption, group_id=group_id)
        except (APIError, httpx.TransportError, TimeoutError, ConnectionError) as error:
            raise WriteOutcomeError(f"Creation outcome unknown for name={name!r}, group_id={group_id}; verify existence before retry", None, "unknown") from error
        report_id = result.get("report_id") or result.get("report", {}).get("id")
        if result.get("success") and report_id:
            return {**result, "report_id": report_id, "changed": True}
        raise WriteOutcomeError(f"Creation not confirmed for name={name!r}, group_id={group_id}; verify existence before retry", None, "unknown")

    async def upsert(self, report_id, components, table_mode="merge", native_mode="merge", replace_kind=False):
        check_action("update")
        if table_mode not in {"merge", "replace"}:
            raise ValueError("table_mode must be merge or replace")
        specs = [s if isinstance(s, (DashboardComponent, NativeVisualization)) else DashboardComponent.model_validate(s) for s in components]
        if not specs or len(specs) > 30 or len({s.key for s in specs}) != len(specs):
            raise ValueError("Supply 1..30 unique component keys")
        async with _lock(report_id):
            before = await self.fetch(report_id)
            candidate = copy.deepcopy(before)
            datasets = {}
            changed_ids = []
            native_available = None
            for spec in specs:
                if isinstance(spec, NativeVisualization):
                    if native_available is None:
                        native_available = {r.get("type") for r in _rows(await self.client.api_call("components", "list"))}
                    if spec.component_type not in native_available:
                        raise ValueError("Native visualization is not listed by this portal; read giga_list_visualizations")
                field_map = {}
                if spec.dataset_id:
                    if spec.dataset_id not in datasets:
                        datasets[spec.dataset_id] = (await self.schema(spec.dataset_id))[1]
                    field_map = datasets[spec.dataset_id]
                idx, previous = _find(candidate, spec.key)
                if previous:
                    old = previous["config"][META]
                    target = spec.component_type if isinstance(spec, NativeVisualization) else TYPES[spec.kind]
                    if old["kind"] == "filter":
                        raise ValueError(f"Key {spec.key!r} belongs to a shared filter; use its filter tools")
                    changed_definition = old["kind"] != spec.kind or previous.get("type") != target or _dataset_id(previous) != spec.dataset_id
                    if changed_definition and not (replace_kind or isinstance(spec, NativeVisualization) and native_mode == "replace" or spec.kind == "table" and table_mode == "replace"):
                        raise ValueError(f"COMPONENT_REPLACEMENT_REQUIRED: {spec.key!r} already uses {previous.get('type')} / dataset {_dataset_id(previous)}. For a title change use giga_rename_component; preserve data and type. To intentionally replace use explicit replace mode.")
                if isinstance(spec, NativeVisualization):
                    old_spec = previous.get("config",{}).get(META,{}).get("spec") if previous and previous.get("config",{}).get(META,{}).get("kind")=="native" else None
                    spec = normalize_native(spec, field_map, old_spec, native_mode)
                elif spec.kind=='table':
                    # Omitted display format follows the actual raw field type.
                    # An explicit numeric format on text still fails validation.
                    existing_fields={m['field'] for m in previous['config'][META]['spec'].get('metrics',[])} if previous and previous['config'][META]['kind']=='table' and table_mode=='merge' else set()
                    spec=spec.model_copy(update={'metrics':[
                        m.model_copy(update={'format':'text'}) if m.kind=='raw' and 'format' not in m.model_fields_set
                        and m.field not in existing_fields and not m.cell_rules
                        and str(field_map.get(m.field,{}).get('type','')).lower() in {'text','string','date','datetime','timestamp','time'} else m
                        for m in spec.metrics]})
                await self.validate_geography(spec, field_map)
                if isinstance(spec, NativeVisualization) and spec.component_type == "HsComparisonChart":
                    build(spec, report_id, field_map)  # Reject invalid axes/types before query.
                    indicator = next(a for a in spec.axes if a.axis == "indicators").fields[0]
                    if field_map[indicator].get("type") not in {"string", "text"}:
                        raise ValueError("Comparison indicator must be a text field of the UNPIVOT source")
                    params = {"select": [{"lvl":0,"name":indicator,"alias":"indicator_value","calc":"","aggr":"","fieldAlias":indicator}],
                        "group":[{"lvl":0,"name":indicator,"alias":"indicator_value","calc":"","aggr":"","fieldAlias":indicator}],
                        "where":[] if spec.indicator_mode=='all' else [{'lvl':0,'name':indicator,'not':False,'values':spec.indicator_values,'operators':['=']*len(spec.indicator_values),'logicOr':int(len(spec.indicator_values)>1)}],
                        "order":[],"having":{"condition":""},"series":{"enable":0},"limit":102}
                    options = _rows(await self.client.api_call("recordsets", "create", object_id=spec.dataset_id, data=[params]))
                    choices = list(dict.fromkeys(str(r["indicator_value"]) for r in options if r.get("indicator_value") is not None))
                    if not choices or len(choices) > 100:
                        raise ValueError("Comparison requires 1..100 selected indicator_values; query and select them explicitly")
                    if spec.indicator_values and not set(spec.indicator_values).issubset(choices):
                        raise ValueError('Unknown Comparison indicator_values; read actual distinct indicators')
                    if spec.indicator_mode=='all':spec = spec.model_copy(update={"indicator_values": sorted(choices)})
                idx, previous = _find(candidate, spec.key)
                if previous and previous["config"][META]["kind"] == "filter":
                    raise ValueError(f"Key {spec.key!r} belongs to a shared filter; use its filter tools")
                merge_table = previous and previous["config"][META]["kind"] == spec.kind == "table" and table_mode == "merge"
                if merge_table:
                    old = DashboardComponent.model_validate(previous["config"][META]["spec"])
                    if old.dataset_id != spec.dataset_id:
                        raise ValueError("TABLE_DATASET_CHANGE: merge cannot change dataset_id; use explicit replace")
                    incoming = {m.field: m for m in spec.metrics}
                    merged = []
                    for metric in old.metrics:
                        update = incoming.pop(metric.field, None)
                        merged.append(Metric.model_validate({**metric.model_dump(), **update.model_dump(include=update.model_fields_set)}) if update else metric)
                    merged.extend(incoming.values())
                    spec = DashboardComponent.model_validate({**spec.model_dump(), "metrics": [m.model_dump() for m in merged]})
                if idx is None:
                    idx = str(max((int(i) for i in _components(candidate)), default=-1) + 1)
                compiled = build(spec, report_id, field_map)
                display = previous["config"][META].get("field_display", {}) if previous and previous["type"] == compiled["type"] and _dataset_id(previous) == spec.dataset_id else {}
                if merge_table:
                    preserved = copy.deepcopy(previous)
                    old_cfg, new_cfg = preserved["config"], compiled["config"]
                    local_axis = next((a for a in old_cfg.get("axes", []) if a["type"] == "filters"), None)
                    if local_axis:
                        for axes in (new_cfg["axes"], new_cfg["axesDefault"]):
                            for axis in axes:
                                if axis["type"] == "filters":
                                    axis["fields"] = copy.deepcopy(local_axis.get("fields", []))
                    for name in (META, "caption", "caption__ru", "title", "axes", "axesDefault"):
                        old_cfg[name] = new_cfg[name]
                    old_cfg["columns"] = {field_id: {**old_cfg.get("columns", {}).get(field_id, {}), **column} for field_id, column in new_cfg["columns"].items()}
                    old_cfg.setdefault("settings", {}).update(new_cfg["settings"])
                    compiled = preserved
                current_fields = {f.get("id") for f in _fields(compiled)}
                for field_id, options in display.items():
                    if field_id in current_fields:
                        _apply_field_display(compiled, field_id, options)
                if previous and previous["type"] == compiled["type"]:
                    for role, title in previous["config"][META].get("axis_titles", {}).items():
                        _apply_axis_title(compiled["config"], role, title)
                _components(candidate)[idx] = compiled
                changed_ids.append(idx)
            await self._rebind(candidate)
            await self.validate_report_geography(candidate)
            arrange(candidate)
            apply_theme(candidate)
            issues = layout_issues(candidate)
            if issues:
                raise ValueError("; ".join(issues))
            previews = {}
            preview_bindings = {}
            for idx in changed_ids:
                c = _components(candidate)[idx]
                if c["config"][META]["kind"] != "text":
                    data = await _get_component_data(_Preview(self.client, candidate), report_id, int(idx), limit=20)
                    if not data.get("success"):
                        raise ValueError(f"QUERY_PREFLIGHT_FAILED {c['config'][META]['key']}: {data.get('error')}")
                    previews[c["config"][META]["key"]] = data.get("rows", [])
                    if data.get("column_bindings"):
                        preview_bindings[c["config"][META]["key"]] = data["column_bindings"]
            result = await self.save(before, candidate, report_id)
            result["preview_rows"] = previews
            if preview_bindings:result["preview_bindings"] = preview_bindings
            return result

    async def _rebind(self, report):
        panels = [c for c in _components(report).values() if c.get("config", {}).get(META, {}).get("kind") == "filter"]
        for panel in panels:
            definition = panel["config"][META]["filter"]
            mappings = {b["dataset_id"]: b["field"] for b in definition["bindings"]}
            for c in _components(report).values():
                did = _dataset_id(c)
                if not did:
                    continue
                if did not in mappings:
                    raise ValueError(f"Filter {definition['alias']!r} has no field mapping for dataset {did}")
                _, schema = await self.schema(did)
                name = mappings[did]
                if name not in schema:
                    raise ValueError(f"Filter field {name!r} not in dataset {did}")
                cfg = c["config"]
                axis = next((a for a in cfg["axes"] if a["type"] == "filters"), None)
                if axis is None:
                    axis = {"name": "filters", "type": "filters", "fields": []}
                    cfg["axes"].insert(0, axis)
                axis["fields"] = [f for f in axis["fields"] if f.get("alias") != definition["alias"]]
                axis["fields"].append({"id": "giga_" + _digest([did, definition["alias"], name])[:20], "name": name, "alias": definition["alias"],
                                       "title": definition["alias"], "type": schema[name]["type"], "datasetId": did, "agg": None, "global": True})
                cfg.setdefault("filters", {}).setdefault(name, {}).update({"global": True, "nonglobal": False, "filterMode": "by value"})
                cfg["filtersDefault"] = copy.deepcopy(cfg["filters"])
                cfg["axesDefault"] = copy.deepcopy(cfg["axes"])

    async def bind_filter(self, report_id, key, label, bindings, row=2):
        check_action("update")
        bindings = [b if isinstance(b, DatasetFilter) else DatasetFilter.model_validate(b) for b in bindings]
        if not re.fullmatch(r"[a-z][a-z0-9_]{0,63}", key) or not label.strip() or not bindings or len({b.dataset_id for b in bindings}) != len(bindings):
            raise ValueError("Filter requires stable key, label and unique dataset mappings")
        async with _lock(report_id):
            before = await self.fetch(report_id)
            candidate = copy.deepcopy(before)
            types = set()
            for binding in bindings:
                _, schema = await self.schema(binding.dataset_id)
                if binding.field not in schema:
                    raise ValueError(f"Missing filter field {binding.field!r} in dataset {binding.dataset_id}")
                types.add(schema[binding.field]["type"])
            if len(types) != 1:
                raise ValueError("Filter dataset field types do not match")
            idx, existing = _find(candidate, key)
            if existing and existing["config"][META]["kind"] != "filter":
                raise ValueError("Stable key belongs to another component kind")
            other_filters = [c for c in _components(candidate).values() if c.get("config", {}).get(META, {}).get("kind") == "filter" and c["config"][META]["key"] != key]
            if any(c["config"][META]["filter"]["alias"] == label for c in other_filters):
                raise ValueError("Filter label is already owned by another stable key")
            old_alias = existing["config"][META]["filter"]["alias"] if existing else label
            state = candidate.setdefault("globalFilters", {}).get(old_alias, {"enabled": True, "selected": [], "filterMode": "by value", "sourceValues": {}})
            if existing and state.get("selected") and existing["config"][META]["filter"]["bindings"] != [b.model_dump() for b in bindings]:
                raise ValueError("Reset selection before changing filter dataset mappings")
            if old_alias != label:
                if label in candidate["globalFilters"]:
                    raise ValueError("New filter label already exists")
                candidate["globalFilters"].pop(old_alias, None)
                for c in _components(candidate).values():
                    for axis in c.get("config", {}).get("axes", []):
                        if axis.get("type") == "filters":
                            axis["fields"] = [f for f in axis.get("fields", []) if not (f.get("global") and f.get("alias") == old_alias)]
            candidate["globalFilters"][label] = state
            idx = idx if idx is not None else str(max((int(i) for i in _components(candidate)), default=-1) + 1)
            first = bindings[0]
            panel = build_component_config("HsFilterControlPanel", label, first.dataset_id, None, [first.field], next(iter(types)), None)
            # Builder initially aliases the technical field. Give it the shared
            # alias before rebind, otherwise two global fields survive and a
            # regenerated random ID makes every repeated bind look changed.
            for field in _fields(panel, "filters"):
                field["alias"] = label
            panel["config"][META] = {"version": 1, "key": key, "kind": "filter", "spec": {"row": row, "width": 1, "height": 4}, "filter": {"alias": label, "bindings": [b.model_dump() for b in bindings]}}
            selected = state.get("selected", [])
            keeps_multi = bool(existing and existing["config"].get("multipleChoice"))
            panel["config"].update(multipleChoice=keeps_multi or len(selected) > 1, bothChoice=True, updateOnCloseDropdown=False,
                                   updateOnApply=False, applyButtonMode=False)
            panel["config"].update(selectedValue=selected, filterApplied=bool(selected))
            _components(candidate)[idx] = panel
            candidate.setdefault("globalFilters", {}).setdefault(label, {"enabled": True, "selected": [], "filterMode": "by value", "sourceValues": {}})
            await self._rebind(candidate)
            await self.validate_report_geography(candidate)
            arrange(candidate)
            apply_theme(candidate)
            return await self.save(before, candidate, report_id)

    async def _filter_domain(self, definition):
        first = definition["bindings"][0]
        name = first["field"]
        query_field = {"lvl": 0, "name": name, "alias": name, "calc": "", "aggr": "", "fieldAlias": name}
        params = {"select": [query_field], "group": [query_field], "where": [], "order": [], "having": {"condition": ""}, "series": {"enable": 0}, "limit": 1001}
        rs = await self.client.api_call("recordsets", "create", object_id=first["dataset_id"], data=[params])
        rows = _rows(rs)
        if len(rows) > 1000:
            raise ValueError("Filter has >1000 values; bounded validation requires a narrower dataset")
        values = [r.get(name, next(iter(r.values())) if len(r) == 1 else None) for r in rows]
        return {str(value): value for value in values}

    async def list_filter_values(self, report_id, key):
        check_action("get")
        report = await self.fetch(report_id)
        _, panel = _find(report, key)
        if not panel or panel["config"][META]["kind"] != "filter":
            raise ValueError("Filter key not found")
        definition = panel["config"][META]["filter"]
        return {"success": True, "key": key, "label": definition["alias"], "values": sorted(await self._filter_domain(definition))}

    async def select_filter(self, report_id, key, values):
        check_action("update")
        async with _lock(report_id):
            before = await self.fetch(report_id)
            candidate = copy.deepcopy(before)
            _, panel = _find(candidate, key)
            if not panel or panel["config"][META]["kind"] != "filter":
                raise ValueError("Filter key not found")
            definition = panel["config"][META]["filter"]
            if values:
                allowed = await self._filter_domain(definition)
                if any(v not in allowed for v in values):
                    raise ValueError(f"Unknown filter values. Allowed examples: {list(allowed)[:20]}")
                selected = [allowed[v] for v in dict.fromkeys(values)]
            else:
                selected = []
            panel["config"].update(selectedValue=selected, filterApplied=bool(selected))
            if len(selected) > 1:
                panel["config"]["multipleChoice"] = True
            candidate["globalFilters"][definition["alias"]].update(selected=selected, enabled=True)
            await self.validate_report_geography(candidate)
            return await self.save(before, candidate, report_id)

    async def remove(self, report_id, keys):
        check_action("delete")
        if not keys or len(keys) != len(set(keys)):
            raise ValueError("Supply unique component keys")
        async with _lock(report_id):
            before = await self.fetch(report_id)
            candidate = copy.deepcopy(before)
            ids = []
            for key in keys:
                idx, component = _find(candidate, key)
                if not component:
                    continue  # Idempotent deletion of an already absent key.
                if component["config"][META]["kind"] == "filter":
                    raise ValueError("Shared filters cannot be removed by this tool")
                ids.append(idx)
            for idx in ids:
                _components(candidate).pop(idx)
            for bp, layout in candidate.get("grid", {}).get("layouts", {}).items():
                candidate["grid"]["layouts"][bp] = [item for item in layout if str(item.get("i")) not in ids]
            arrange(candidate)
            apply_theme(candidate)
            issues = layout_issues(candidate)
            if issues:
                raise ValueError("; ".join(issues))
            return await self.save(before, candidate, report_id)

    async def patch_component(self, report_id, key, horizontal=None, stacked=None, rule_field=None, rules=None):
        """Patch a narrow option while preserving the full saved component."""
        check_action("update")
        async with _lock(report_id):
            before = await self.fetch(report_id)
            candidate = copy.deepcopy(before)
            idx, component = _find(candidate, key)
            if not component:
                raise ValueError(f"Unknown component key {key!r}")
            meta = component["config"][META]
            spec = copy.deepcopy(meta["spec"])
            if horizontal is not None or stacked is not None:
                if meta["kind"] != "bar":
                    raise ValueError("Bar options require an existing bar component")
                spec.update(horizontal=horizontal, stacked=stacked)
            if rule_field is not None:
                if meta["kind"] != "table":
                    raise ValueError("Cell rules require an existing table")
                metrics = [m for m in spec["metrics"] if m["field"] == rule_field]
                if len(metrics) != 1:
                    raise ValueError(f"Expected one existing column for {rule_field!r}")
                metrics[0]["cell_rules"] = [r.model_dump() if hasattr(r, "model_dump") else r for r in rules]
            validated = DashboardComponent.model_validate(spec)
            cfg = component["config"]
            if horizontal is not None or stacked is not None:
                cfg, warnings = _apply_visual_overrides(cfg, TYPES["bar"],
                    orientation="horizontal" if horizontal else "vertical",
                    stacking="normal" if stacked else "none")
                if warnings:
                    raise ValueError("; ".join(warnings))
                component["config"] = cfg
            if rule_field is not None:
                field_map = (await self.schema(validated.dataset_id))[1]
                original = build(DashboardComponent.model_validate(meta["spec"]), report_id, field_map)["config"]
                compiled = build(validated, report_id, field_map)["config"]
                index = next(i for i,m in enumerate(spec["metrics"]) if m["field"] == rule_field)
                before_field = next(a for a in original["axes"] if a["type"] == "values")["fields"][index]
                after_field = next(a for a in compiled["axes"] if a["type"] == "values")["fields"][index]
                target_id = after_field["id"]
                live = [f for a in cfg.get("axes", []) if a["type"] == "values" for f in a.get("fields", []) if f.get("id") == target_id]
                if len(live) != 1 or any(live[0].get(k) != before_field.get(k) for k in ("name", "type", "calc", "agg")):
                    raise ValueError("Native column definition differs from saved profile; refresh its full table specification before changing rules")
                for axes in (cfg["axes"], cfg.get("axesDefault", [])):
                    for axis in axes:
                        if axis["type"] == "values":
                            for field in axis.get("fields", []):
                                if field.get("id") == target_id:
                                    field["calc"] = after_field["calc"]
                cfg.setdefault("columns", {}).setdefault(target_id, {})["isHtml"] = compiled["columns"][target_id]["isHtml"]
            cfg[META]["spec"] = validated.model_dump()
            issues = layout_issues(candidate)
            if issues:
                raise ValueError("; ".join(issues))
            preview = await _get_component_data(_Preview(self.client, candidate), report_id, int(idx), limit=20)
            if not preview.get("success"):
                raise ValueError("QUERY_PREFLIGHT_FAILED: " + str(preview.get("error")))
            result = await self.save(before, candidate, report_id)
            result["preview_rows"] = {key: preview.get("rows", [])}
            return result

    async def set_field_display(self, report_id, key, field, label="", order="", date_format=""):
        check_action("update")
        options = {k: v for k, v in {"label": label.strip(), "order": order, "date_format": date_format}.items() if v}
        if not options or order not in {"", "asc", "desc"} or date_format and date_format not in FIELD_DATE_FORMATS:
            raise ValueError("Supply a label, asc/desc or a supported date format")
        async with _lock(report_id):
            before = await self.fetch(report_id)
            candidate = copy.deepcopy(before)
            idx, component = _find(candidate, key)
            if not component or component["type"] not in {TYPES[k] for k in ("bar", "line", "donut", "table")}:
                raise ValueError("Select an existing bar, line, donut or table component")
            is_table = component["type"] == TYPES["table"]
            cfg = component["config"]
            matches = [(axis["type"], f) for axis in cfg.get("axes", []) if axis["type"] not in {"filters", "tooltip"}
                       for f in axis.get("fields", []) if f.get("name") == field and f.get("id")]
            if not matches and is_table:
                values = next((axis.get("fields", []) for axis in cfg["axes"] if axis["type"] == "values"), [])
                matches = [("values", native) for native, metric in zip(values, cfg[META]["spec"]["metrics"])
                           if metric["field"] == field and native.get("id")]
            if len(matches) != 1:
                raise ValueError(f"Expected one bound field {field!r}; inspect the component and use its exact source field")
            axis, target = matches[0]
            if order and axis not in ({"values"} if is_table else {"categories", "series"}):
                raise ValueError("Use a table column or a chart category/series for sorting")
            if date_format:
                _, schema = await self.schema(_dataset_id(component))
                date_type = str(schema.get(field, {}).get("type", "")).lower()
                if date_type not in DATE_TYPES or not is_table and axis != "categories" or target.get("type") == "calculated":
                    raise ValueError("Date format requires a date column or the chart's date category; select a typed date field")
                if is_table:
                    options["date_type"] = date_type
            _apply_field_display(component, target["id"], {"field": field, **options})
            preview = await _get_component_data(_Preview(self.client, candidate), report_id, int(idx), limit=12)
            if not preview.get("success"):
                raise ValueError("QUERY_PREFLIGHT_FAILED: " + str(preview.get("error")))
            result = await self.save(before, candidate, report_id)
            result["field_display"] = component["config"][META]["field_display"][target["id"]]
            return result

    async def set_chart_axis(self, report_id, key, axis, title="", order="", date_format=""):
        """Change the native axis caption and date presentation without relabeling fields."""
        check_action("update")
        title = title.strip()
        if axis not in {"categories", "values"} or not (title or order or date_format):
            raise ValueError("Choose an axis and at least one setting")
        if order not in {"", "asc", "desc"} or date_format and date_format not in FIELD_DATE_FORMATS:
            raise ValueError("Use a supported date format or asc/desc")
        if (order or date_format) and axis != "categories":
            raise ValueError("Sort and format dates on the categories axis")
        async with _lock(report_id):
            before = await self.fetch(report_id)
            candidate = copy.deepcopy(before)
            idx, component = _find(candidate, key)
            if not component or component["type"] not in {TYPES["bar"], TYPES["line"]}:
                raise ValueError("Select a supported existing bar or line chart")
            cfg = component["config"]
            bound = next((a for a in cfg.get("axes", []) if a.get("type") == axis), None)
            if bound is None:
                raise ValueError("The selected axis is unavailable in this chart")
            if date_format or order:
                fields = bound.get("fields", [])
                if len(fields) != 1 or not fields[0].get("id") or fields[0].get("type") not in DATE_TYPES:
                    raise ValueError("Select a chart with one bound date field on its categories axis")
                field = fields[0]
                changes = {k:v for k,v in {"order":order,"date_format":date_format}.items() if v}
                _apply_field_display(component, field["id"], {"field":field["name"], **changes})
                preview = await _get_component_data(_Preview(self.client, candidate), report_id, int(idx), limit=12)
                if not preview.get("success"):
                    raise ValueError("QUERY_PREFLIGHT_FAILED: " + str(preview.get("error")))
            if title:
                _apply_axis_title(cfg, axis, title)
            result = await self.save(before, candidate, report_id)
            result["axis"] = {"role":axis, "title":bound.get("title"), "date_format":cfg.get("dateFormat"),
                              "order":next((f.get("order") for f in bound.get("fields", [])),None)}
            return result

    async def update_kpi(self, report_id, key, field="", aggregation=""):
        """Patch an existing card while retaining its layout, title and formatting."""
        check_action("update")
        if not (field or aggregation):
            raise ValueError("Choose a new source field or aggregation")
        if aggregation and aggregation not in {"sum", "avg", "min", "max", "count"}:
            raise ValueError("Unsupported aggregation; use the full KPI tool for formulas")
        async with _lock(report_id):
            before = await self.fetch(report_id)
            candidate = copy.deepcopy(before)
            idx, component = _find(candidate, key)
            if not component or component["config"][META]["kind"] != "kpi":
                raise ValueError("Select the key of an existing KPI card")
            cfg = component["config"]
            spec = DashboardComponent.model_validate(cfg[META]["spec"])
            metric = spec.metrics[0].model_dump()
            _, schema = await self.schema(spec.dataset_id)
            if field:
                if field not in schema:
                    raise ValueError("Use the exact field name from the card's dataset")
                if field != metric["field"]:
                    metric.update(field=field, label=schema[field].get("alias") or field)
            if aggregation:
                metric.update(kind=aggregation, numerator="", denominator="", constant=0.0)
            if metric["kind"] not in {"sum", "avg", "min", "max", "count"}:
                raise ValueError("Existing formula requires the full KPI tool; choose aggregation explicitly to replace it")
            spec = DashboardComponent.model_validate({**spec.model_dump(), "metrics": [metric]})
            updated = build(spec, report_id, schema)["config"]
            fields = next(a["fields"] for a in updated["axes"] if a["type"] == "values")
            for axes in (cfg["axes"], cfg.get("axesDefault", [])):
                for axis in axes:
                    if axis["type"] == "values":
                        axis["fields"] = copy.deepcopy(fields)
            cfg[META]["spec"] = spec.model_dump()
            # The Totals renderer uses the card title for its main caption.
            # Show the actual measure and aggregation on the separate subtitle line.
            operation = {"sum":"Сумма", "avg":"Среднее", "min":"Минимум", "max":"Максимум", "count":"Количество"}[metric["kind"]]
            subtitle = f"{operation} · {metric['label']}"
            cfg.update(subtitle=subtitle, subtitle__ru=subtitle)
            for visual in cfg.get("visuals", []):
                if visual.get("anchor") == "subcaption":
                    visual["visible"] = True
            preview = await _get_component_data(_Preview(self.client, candidate), report_id, int(idx), limit=1)
            if not preview.get("success"):
                raise ValueError("QUERY_PREFLIGHT_FAILED: " + str(preview.get("error")))
            result = await self.save(before, candidate, report_id)
            result["preview_rows"] = {key: preview.get("rows", [])}
            return result

    async def rename(self, report_id, key, title):
        check_action("update")
        if not title.strip() or len(title) > 240:
            raise ValueError("Supply a nonempty title up to 240 characters")
        async with _lock(report_id):
            before = await self.fetch(report_id)
            candidate = copy.deepcopy(before)
            _, component = _find(candidate, key)
            if not component or component["config"][META]["kind"] in {"filter", "text"}:
                raise ValueError("Use filter/header tools for filters/static text; rename requires a data component key")
            cfg = component["config"]
            cfg[META]["spec"]["title"] = title
            for name in ("caption", "caption__ru", "title"):
                if isinstance(cfg.get(name), dict):
                    cfg[name]["text"] = title
                else:
                    cfg[name] = title
            return await self.save(before, candidate, report_id)

    async def arrange(self, report_id, placements):
        check_action("update")
        placements = [p if isinstance(p, Placement) else Placement.model_validate(p) for p in placements]
        if not placements or len({p.key for p in placements}) != len(placements):
            raise ValueError("Supply unique placements")
        async with _lock(report_id):
            before = await self.fetch(report_id)
            candidate = copy.deepcopy(before)
            for placement in placements:
                _, c = _find(candidate, placement.key)
                if not c:
                    raise ValueError(f"Unknown component key {placement.key!r}")
                spec = c["config"][META]["spec"]
                spec["row"] = placement.row
                if placement.width:
                    spec["width"] = placement.width
                if placement.height:
                    spec["height"] = placement.height
            arrange(candidate)
            return await self.save(before, candidate, report_id)

    async def apply_preset(self, report_id, style="corporate_clean"):
        check_action("update")
        if style not in STYLES:raise ValueError("Unknown report style")
        async with _lock(report_id):
            before = await self.fetch(report_id)
            candidate = copy.deepcopy(before)
            candidate.setdefault("options",{})["_mcp_gigachat_style"] = style
            positions = {"text": (0, 1, 3), "kpi": (1, 1, 5), "filter": (2, 1, 3),
                         "bar": (3, 2, 16), "donut": (3, 1, 16), "line": (4, 1, 14),
                         "table": (5, 1, 13), "rich_text": (6, 1, 16)}
            for c in _components(candidate).values():
                meta = c.get("config", {}).get(META)
                if meta and meta["kind"] in positions:
                    row, width, height = positions[meta["kind"]]
                    meta["spec"].update(row=row, width=width, height=height)
            arrange(candidate)
            apply_theme(candidate)
            issues = layout_issues(candidate)
            if issues:
                raise ValueError("; ".join(issues))
            result = await self.save(before, candidate, report_id)
            result["applied_preset"] = "light_dashboard"
            result["applied_style"] = style
            return result

    async def inspect(self, report_id, include_data=True, include_style=False):
        check_action("get")
        report = await self.fetch(report_id)
        result = {"success": True, "report_id": report_id, "fingerprint": _digest(_state(report)), "components": _summaries(report),
                  "global_filters": report.get("globalFilters", {}), "issues": layout_issues(report), "browser_verified": False}
        result['layouts']={bp:[{k:item.get(k) for k in ('i','x','y','w','h')} for item in boxes]
                           for bp,boxes in report.get('grid',{}).get('layouts',{}).items()}
        expected_bindings=copy.deepcopy(report)
        try:
            await self._rebind(expected_bindings)
            for idx,c in _components(report).items():
                cfg=c.get("config",{});meta=cfg.get(META,{})
                if meta.get("kind")=="filter":
                    selection=report.get("globalFilters",{}).get(meta["filter"]["alias"])
                    if selection is None or cfg.get("selectedValue")!=selection.get("selected",[]) or cfg.get("filterApplied")!=bool(selection.get("selected")):
                        result["issues"].append(f"FILTER_SELECTION_DRIFT: {meta['key']}")
                expected_cfg=_components(expected_bindings)[idx].get("config",{})
                actual_axis=next((a for a in cfg.get("axes",[]) if a["type"]=="filters"),None)
                expected_axis=next((a for a in expected_cfg.get("axes",[]) if a["type"]=="filters"),None)
                default_axis=next((a for a in cfg.get("axesDefault",[]) if a["type"]=="filters"),None)
                if _digest(actual_axis)!=_digest(expected_axis) or expected_axis and _digest(default_axis)!=_digest(expected_axis) or any(any(any(cfg.get(container,{}).get(name,{}).get(k)!=v for k,v in state.items() if k in {"global","nonglobal","filterMode"}) for name,state in expected_cfg.get("filters",{}).items()) for container in ("filters","filtersDefault")):
                    result["issues"].append(f"FILTER_BINDING_DRIFT: {meta.get('key',idx)}")
        except (ValueError,KeyError) as error:
            result["issues"].append(f"INVALID_FILTER_BINDING: {error}")
        # META is provenance, not proof: compare rendered expressions and captions.
        schemas = {}
        for idx, component in _components(report).items():
            meta = component.get("config", {}).get(META, {})
            if meta.get("kind") not in {*TYPES, "native"}:
                continue
            try:
                spec = (NativeVisualization if meta.get("kind") == "native" else DashboardComponent).model_validate(meta["spec"])
                if spec.dataset_id not in schemas:
                    schemas[spec.dataset_id] = (await self.schema(spec.dataset_id))[1] if spec.dataset_id else {}
                await self.validate_geography(spec, schemas[spec.dataset_id], report, component)
                expected_component = build(spec, report_id, schemas[spec.dataset_id])
                for field_id, options in meta.get("field_display", {}).items():
                    _apply_field_display(expected_component, field_id, options)
                for role, title in meta.get("axis_titles", {}).items():
                    _apply_axis_title(expected_component["config"], role, title)
                expected = expected_component["config"]
                cfg = component["config"]
                def signature(config):
                    axes = []
                    for axis in config.get("axes", []):
                        if axis["type"] == "filters":
                            continue
                        fields = []
                        for field in axis.get("fields", []):
                            item = {k: field.get(k) for k in ("id", "name", "datasetId", "calc", "type", "valueType", "pivotAgg", "pivotOrder")}
                            item["agg"] = str(field.get("agg") or field.get("aggregation") or "").casefold()
                            if field.get("type") == "calculated":
                                item["draft"] = field.get("draft")
                            if axis["type"] == "values" or spec.kind=='native' and field.get('name') in {label.field for label in spec.field_labels}:
                                item.update({k: field.get(k) for k in ("alias", "title", "title__ru")})
                            fields.append(item)
                        axes.append((axis["type"], axis.get("selectedFieldIndex") if spec.kind == "native" or axis["type"] in {"values", "xvalues", "yvalues"} and spec.kind in {"bar", "line", "donut"} else None, fields, axis.get('rangeMode')))
                    return axes
                def title(config, name):
                    value = config.get(name)
                    return value.get("text") if isinstance(value, dict) else value
                if _digest(signature(cfg)) != _digest(signature(expected)) or any(title(cfg, name) != title(expected, name) for name in ("caption", "caption__ru", "title")):
                    result["issues"].append(f"NATIVE_DEFINITION_DRIFT: {meta.get('key', idx)}")
                if component.get("type") != expected_component.get("type") or any(cfg.get(name) != expected.get(name) for name in ("chartType", "visualType")):
                    result["issues"].append(f"NATIVE_RENDERER_TYPE_DRIFT: {meta.get('key', idx)}")
                if spec.kind == "native" and spec.component_type == "HsComparisonChart" and any(cfg.get(name) != expected.get(name) for name in ("filters", "filtersDefault")):
                    # Global filter metadata may coexist with local comparison state.
                    expected_filters = expected.get("filters", {})
                    if any(any(any(cfg.get(name, {}).get(field, {}).get(k) != v for k, v in selection.items()) for field, selection in expected_filters.items()) for name in ("filters", "filtersDefault")):
                        result["issues"].append(f"NATIVE_COMPARISON_SELECTION_DRIFT: {meta.get('key', idx)}")
                if spec.kind in {"bar", "line"} and any(cfg.get(name) != expected.get(name) for name in ("orientation", "groupMode")):
                    result["issues"].append(f"NATIVE_CHART_OPTIONS_DRIFT: {meta.get('key', idx)}")
                if spec.kind == "native" and any(_digest(cfg.get(name)) != _digest(expected[name]) for name in ("geokeys", "object1", "object2", "orientation", "groupMode", "showDonut", "innerRadius") if name in expected):
                    result["issues"].append(f"NATIVE_CHART_OPTIONS_DRIFT: {meta.get('key', idx)}")
                if spec.kind == "native" and spec.component_type == "HsSpeedometerV2AMcharts" and any(cfg.get("grid", {}).get(name) != expected["grid"][name] for name in ("minimum", "maximum")):
                    result["issues"].append(f"NATIVE_GAUGE_RANGE_DRIFT: {meta.get('key', idx)}")
                if spec.kind == "table" and any(any(cfg.get("columns", {}).get(fid, {}).get(name) != col.get(name) for name in ("title", "title__ru", "visibleOrder", "isHtml")) for fid, col in expected.get("columns", {}).items()):
                    result["issues"].append(f"NATIVE_COLUMN_TITLE_DRIFT: {meta.get('key', idx)}")
            except (ValueError, KeyError) as error:
                result["issues"].append(f"INVALID_SAVED_SPEC: {meta.get('key', idx)}: {error}")
        if include_style:
            result["style"] = {"preset":report.get("options",{}).get("_mcp_gigachat_style","corporate_clean"),"css": report.get("options", {}).get("CSStext", ""),
                "managed_panel_ids": ["panel_"+idx for idx,c in _components(report).items() if c.get("config", {}).get(META)],
                "supported_classes": ["hsGridLayout", "hsTotalsPanelV2", "value", "caption", "componentHeader", "hs-table__table", "htmlWrapper", "amcharts-legend-label"]}
        if include_data:
            result["data"] = {}
            for idx, c in _components(report).items():
                meta = c.get("config", {}).get(META, {})
                if meta.get("kind") in {"text", "filter"}:
                    continue
                data = await _get_component_data(_Preview(self.client, report), report_id, int(idx), limit=20)
                key = meta.get("key", idx)
                if data.get("column_bindings"):
                    summary = next(s for s in result["components"] if s["component_idx"]==int(idx))
                    summary["field_outputs"] = data["column_bindings"]
                result["data"][key if key not in result["data"] else f"{key}#{idx}"] = data
                if not data.get("success"):
                    result["issues"].append(f"Query failed: {meta.get('key', idx)}")
        result["checks_passed"] = not result["issues"]
        result["verification_scope"] = "Saved configuration, native expressions and query execution. Compare source queries and user requirements separately; structural success does not establish business meaning or browser acceptance."
        result["business_data_verified"] = False
        result['verification_plan'] = verification_plan(result['components'])
        result['verification_plan']['filters'] = [
            {'key': c['config'][META]['key'], **c['config'][META]['filter']}
            for c in _components(report).values()
            if c.get('config', {}).get(META, {}).get('kind') == 'filter']
        return result
