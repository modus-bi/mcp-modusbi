"""Typed native-axis adapter over the existing Modus component builders."""
from __future__ import annotations
import copy
import hashlib
import json

from .builders import COMPONENT_TYPE_MAP, NO_DATASET_TYPES, build_component_config
from .gigachat_models import VisualizationMetric
from .gigachat_geo import READABLE_HEIGHTS

REQUIRED_AXES = {
    **{name: {"categories": 1, "values": 1} for name in (
        "HsBarAMchartsChart", "HsLineAMchartsChart", "HsAreaAMchartsChart", "HsPieAMchartsChart",
        "HsRadarAMchartsChart", "HsStockAMchartsChart", "HsSunburstChart", "HsTreeMap", "HsTilemapChart", "HsMapLeafletChart")},
    "HsSpeedometerV2AMcharts": {"values": 1}, "HsTotalsPanelV2": {"values": 1},
    "HsTableReactabularChart": {"values": 1}, "HsBubbleAMchartsChart": {"categories": 1, "yvalues": 1, "xvalues": 1, "values": 1},
    "HsParallelCoordsChart": {"values": 3}, "HsPivotChart": {"rows": 1, "values": 1},
    "HsComparisonChart": {"objects": 1, "indicators": 1, "values": 1},
    "HsTreeGraph": {"identity": 1, "linkage": 1, "values": 1},
    "HsFilterControlPanel": {"filters": 1}, "HsHierarchicalFilterPanel": {"filters": 1},
    "HsSwitchControlPanel": {"categories": 1},
}
SINGLE_VALUE = {"HsPieAMchartsChart", "HsSunburstChart", "HsTreeMap", "HsSpeedometerV2AMcharts", "HsTotalsPanelV2"}
NUMERIC_TYPES = {"number", "numeric", "integer", "int", "float", "double", "decimal"}
MEASURE_AXES = {"values", "xvalues", "yvalues"}
RAW_FIELD_AXIS_TYPES = {"HsTreeGraph", "HsParallelCoordsChart"}
MEASURE_ONLY_TYPES = {name for name, axes in REQUIRED_AXES.items()
                      if name not in RAW_FIELD_AXIS_TYPES and set(axes) & MEASURE_AXES}


def skeleton(component_type, title=""):
    if component_type not in COMPONENT_TYPE_MAP:
        raise ValueError(f"Unknown native visualization {component_type!r}; read giga_list_visualizations")
    return build_component_config(component_type, title, 0, None, [], "number", None)


def catalog():
    return [{"component_type": name, "chart_type": shape[0], "content_utility": name in NO_DATASET_TYPES,
        "preferred_tool": {"HsTreeGraph":"giga_set_tree", "HsMapLeafletChart":"giga_set_map", "HsTilemapChart":"giga_set_tilemap", "HsTableReactabularChart": "giga_set_table", "HsTotalsPanelV2": "giga_set_kpi", "HsTextBlock": "giga_set_header or giga_upsert_components", "HsFilterControlPanel": "giga_bind_report_filter"}.get(name, "giga_set_visualization"),
        "active_control_supported": name not in {"HsHierarchicalFilterPanel", "HsSwitchControlPanel"},
        "minimum_height": READABLE_HEIGHTS.get(name, 14),
        "automatic_full_width": name in {'HsPivotChart','HsParallelCoordsChart','HsTilemapChart'},
        "axes": [{"axis": a["type"], "minimum_fields": REQUIRED_AXES.get(name, {}).get(a["type"], 0),
                  "input": "metrics with explicit kind" if a['type'] in MEASURE_AXES and name in MEASURE_ONLY_TYPES else "fields or raw metrics" if a['type'] in MEASURE_AXES else "fields"} for a in skeleton(name)["config"].get("axes", [])],
        "single_value": name in SINGLE_VALUE, "raw_data_required": name in {"HsTreeGraph", "HsParallelCoordsChart", "HsTableReactabularChart"},
        "notes": {"HsComparisonChart": "UNPIVOT: objects + indicators + numeric values; compare_values selects two objects. indicator_mode=all preserves all source measures; selected is only for an explicitly requested subset.",
                  "HsMapLeafletChart": "Latitude/longitude on values as numeric metrics (max/min/avg for fixed point coordinates), plus measure; provide latitude_field/longitude_field. Native frontend groups by category.",
                  "HsTreeGraph": "Unique numeric identity, nullable numeric parent linkage, raw values",
                  "HsParallelCoordsChart": "All dimensions and raw numeric measures on values axis",
                  "HsStockAMchartsChart": "Date categories, ascending order",
                  "HsBubbleAMchartsChart": "Explicit numeric X, Y and size on xvalues/yvalues/values",
                  "HsPivotChart": "Rows and columns are dimensions, values are aggregate measures"}.get(name, "")}
        for name, shape in COMPONENT_TYPE_MAP.items()]


def compile_visualization(spec, report_id, field_map, compile_metric, validate_metric):
    dedicated = {"HsTableReactabularChart": "giga_set_table (preserves columns)", "HsTotalsPanelV2": "giga_set_kpi", "HsTextBlock": "giga_set_header or giga_upsert_components", "HsFilterControlPanel": "giga_bind_report_filter"}
    if spec.component_type in dedicated:
        raise ValueError("Use dedicated tool: " + dedicated[spec.component_type])
    if spec.component_type in {"HsHierarchicalFilterPanel", "HsSwitchControlPanel"}:
        raise ValueError("Active hierarchical filters/category switchers are not yet supported by this compact profile; use the standard MCP for these controls")
    component = skeleton(spec.component_type, spec.title)
    cfg = component["config"]
    if spec.component_type == 'HsBubbleAMchartsChart':
        # Native frontend maps these documented settings to extraMin/extraMax
        # on both value axes. Keep the largest marker inside a narrow plot.
        cfg.update(strictMinMaxEnabled=True,strictMinMaxPadding=20)
    labels = {item.field: item.label for item in spec.field_labels}
    if any(name not in field_map for name in labels):
        raise ValueError('Display labels must reference existing source fields')
    if spec.dataset_id:
        cfg["datasetId"] = spec.dataset_id
    axes = {a["type"]: a for a in cfg.get("axes", [])}
    if spec.component_type not in NO_DATASET_TYPES and not spec.dataset_id:
        raise ValueError("A data visualization requires dataset_id")
    requested_axes = [a.model_copy(deep=True) for a in spec.axes]
    if spec.component_type == "HsMapLeafletChart":
        if spec.latitude_field == spec.longitude_field or not spec.latitude_field or not spec.longitude_field:
            raise ValueError("Choose two different latitude_field/longitude_field names")
        values = next((a for a in requested_axes if a.axis == "values"), None)
        if values is not None:
            bound = set(values.fields) | {m.field for m in values.metrics}
            for name in (spec.latitude_field, spec.longitude_field):
                if field_map.get(name, {}).get("type") not in NUMERIC_TYPES:
                    raise ValueError(f"Coordinate field {name!r} must exist and be numeric")
                if name not in bound:
                    values.metrics.append(VisualizationMetric(label=name, field=name, kind="max"))
    for requested in requested_axes:
        if requested.axis not in axes:
            raise ValueError(f"Unsupported axis {requested.axis}; available={list(axes)}")
        if len(requested.fields) != len(set(requested.fields)) or any(f not in field_map for f in requested.fields):
            raise ValueError("Use unique existing dataset field names on each axis")
        if requested.axis not in {"values", "xvalues", "yvalues"} and requested.metrics:
            raise ValueError("Use fields for dimensional axes; metrics belong to values/xvalues/yvalues")
        if requested.axis in MEASURE_AXES and requested.fields and spec.component_type in MEASURE_ONLY_TYPES:
            raise ValueError(f"AXIS_METRICS_REQUIRED: {spec.component_type}.{requested.axis}: move fields {requested.fields} into metrics with explicit kind and label. Choose sum/avg/min/max/count or a formula from the user's task; raw is only for intentional unaggregated coordinates. Preserve all required axes. Aggregation is never inferred from a field name.")
        fields = []
        for name in requested.fields:
            source = field_map[name]
            fields.append({"name": name, "datasetId": spec.dataset_id, "agg": None, "type": source.get("type", "string"),
                "alias": labels.get(name) or source.get("alias") or name, "title": labels.get(name) or source.get("alias") or name})
        for metric in requested.metrics:
            # Raw native fields retain the source type, without requiring the
            # model to repeat text formatting for tree labels/color codes.
            if metric.kind == "raw" and field_map.get(metric.field, {}).get("type") in {"string", "text", "date", "datetime", "timestamp"} and metric.format == "number":
                metric = metric.model_copy(update={"format": "text"})
            if metric.kind == 'raw' and spec.component_type in MEASURE_ONLY_TYPES and field_map.get(metric.field,{}).get('type') not in NUMERIC_TYPES:
                raise ValueError(f"NUMERIC_AXIS_REQUIRED: {requested.axis} raw metric {metric.field!r} must be numeric; labels belong on dimensional axes")
            validate_metric(metric, field_map)
            if metric.field and metric.kind in {"sum", "avg", "min", "max", "count", "raw"} and metric.format != "percent":
                source = field_map[metric.field]
                fields.append({"name": metric.field, "datasetId": spec.dataset_id,
                    "agg": None if metric.kind == "raw" else metric.kind, "type": "number" if metric.kind == "count" else source.get("type", "number"),
                    "alias": labels.get(metric.field) or source.get("alias") or metric.field, "title": labels.get(metric.field) or metric.label, "title__ru": labels.get(metric.field) or metric.label})
                continue
            expression = compile_metric(metric)
            if metric.format == "percent":
                expression = f"100.0 * ({expression})"
            fields.append({"name": "", "datasetId": spec.dataset_id, "agg": None, "type": "calculated", "calc": expression,
                "alias": metric.label, "title": metric.label, "title__ru": metric.label, "draft": True})
        for i, field in enumerate(fields):
            uid = "giga_" + hashlib.sha256(json.dumps([report_id, spec.key, requested.axis, i]).encode()).hexdigest()[:20]
            field["id"] = uid
            if not field["name"]:
                field["name"] = "{Вычисляемое поле}_" + uid + "_name"
            if requested.axis in {"categories", "rows", "columns", "objects", "indicators"}:
                field.update(order="asc", orderIndex=i)
        axes[requested.axis]["fields"] = fields
        if requested.axis in {"values", "xvalues", "yvalues"}:
            axes[requested.axis]["selectedFieldIndex"] = -2
    for name, minimum in REQUIRED_AXES.get(spec.component_type, {}).items():
        if len(axes.get(name, {}).get("fields", [])) < minimum:
            raise ValueError(f"{spec.component_type} requires axis {name} with at least {minimum} fields/metrics")
    if spec.component_type == "HsTreeMap":
        categories = axes["categories"]["fields"]
        series = axes["series"]["fields"]
        if len(categories)>2 or len(series)>1 or len(categories)==2 and series:
            raise ValueError("TreeMap supports two hierarchy levels: two categories, or one category plus one series. Use Sunburst for deeper hierarchies.")
        if len(categories)==2:
            axes["categories"]["fields"] = categories[:1]
            axes["series"]["fields"] = categories[1:]
        for name in ("categories","series"):
            axes[name]["selectedFieldIndex"] = 0 if axes[name]["fields"] else -1
    if spec.component_type == "HsSunburstChart":
        axes["categories"]["selectedFieldIndex"] = -2
        cfg.update(font={'size': 1.0, 'family': 'Arial'}, darkLabels=True, minPercent=0,
                   splittedMode=True, ellipsisLength=18)
    if spec.component_type in {'HsBarAMchartsChart','HsAreaAMchartsChart'}:
        axes['values']['rangeMode']='tozero'
    if spec.component_type == "HsPivotChart":
        for name in ("rows","columns"):
            for field in axes[name]["fields"]:
                field["pivotOrder"] = "asc"
        for field in axes["values"]["fields"]:
            if field.get("type")=="calculated" or field.get("agg") not in {"sum","min","max","avg","count"}:
                raise ValueError("Pivot requires direct aggregate metrics sum/min/max/avg/count; raw and calculated aggregate expressions are not supported by this native adapter")
            field["pivotAgg"] = field["agg"]
    if spec.component_type in {"HsBubbleAMchartsChart", "HsSpeedometerV2AMcharts"}:
        numeric_axes = ("xvalues", "yvalues", "values") if spec.component_type == "HsBubbleAMchartsChart" else ("values",)
        for name in numeric_axes:
            fields = axes[name]["fields"]
            if len(fields) != 1 or any(f.get("type") not in NUMERIC_TYPES | {"calculated"} for f in fields):
                raise ValueError(f"Axis {name} requires exactly one numeric field/metric")
            source_axis = next(a for a in spec.axes if a.axis == name)
            if any(m.format in {"text", "html"} for m in source_axis.metrics):
                raise ValueError(f"Axis {name} requires a numeric metric format")
    if spec.component_type == "HsStockAMchartsChart":
        categories = axes["categories"]["fields"]
        if len(categories) != 1 or categories[0].get("type") not in {"date", "datetime", "timestamp", "time"}:
            raise ValueError("Stock requires exactly one date-compatible category field")
        categories[0]["type"] = "date"
    if spec.component_type in SINGLE_VALUE and len(axes.get("values", {}).get("fields", [])) != 1:
        raise ValueError("This renderer displays exactly one value metric")
    if spec.component_type in {"HsTreeGraph", "HsParallelCoordsChart", "HsTableReactabularChart"}:
        if any(m.kind != "raw" for a in spec.axes for m in a.metrics):
            raise ValueError("Для Tree/Parallel задайте metrics[].kind='raw' явно для КАЖДОЙ метрики; либо перенесите готовые поля в axes[].fields. sum/avg/min/max здесь не допускаются.")
    if spec.component_type == "HsTreeGraph" and any(len(axes[name]["fields"]) != 1 or any(f.get("type") not in NUMERIC_TYPES for f in axes[name]["fields"]) for name in ("identity", "linkage")):
        raise ValueError("Tree identity and linkage must be numeric fields")
    if spec.component_type == "HsTreeGraph":
        cfg["initialZoom"] = 1
        roles=[n for n in (spec.label_field,spec.color_field,spec.size_field) if n]
        if len(roles)!=len(set(roles)):
            raise ValueError("Tree label/color/size roles require different fields")
        if spec.size_field and field_map.get(spec.size_field,{}).get("type") not in NUMERIC_TYPES:
            raise ValueError("Tree size_field must be numeric")
        if axes["identity"]["fields"][0]["name"] == axes["linkage"]["fields"][0]["name"]:
            raise ValueError("Tree identity and parent linkage must be different fields")
        values = {f["name"]:f for f in axes["values"]["fields"]}
        for name,role in ((spec.label_field,"value"),(spec.color_field,"color"),(spec.size_field,"size")):
            if name:
                if name not in values:raise ValueError(f"Tree role {role} requires bound field {name!r}")
                values[name]["valueType"] = role
    if spec.component_type == "HsSpeedometerV2AMcharts":
        cfg["grid"].update(minimum=spec.minimum, maximum=spec.maximum)
    if spec.component_type == "HsPieAMchartsChart":
        cfg.update(showDonut=spec.donut, innerRadius=60 if spec.donut else 0)
    if spec.component_type == "HsComparisonChart":
        if axes["series"]["fields"]:
            raise ValueError("Comparison series are not supported by this compact profile; omit series")
        if any(len(axes[name]["fields"]) != 1 for name in ("objects", "indicators", "values")):
            raise ValueError("Comparison requires exactly one field on objects, indicators and values")
        if axes["indicators"]["fields"][0].get("type") not in {"string", "text"}:
            raise ValueError("Comparison indicator must be a text field of the UNPIVOT source")
        if axes["objects"]["fields"][0].get("type") not in {"string", "text"}:
            raise ValueError("Comparison objects require a text field for string compare_values")
        if axes["values"]["fields"][0].get("type") not in NUMERIC_TYPES | {"calculated"}:
            raise ValueError("Comparison values require a numeric field/metric")
        if len(spec.compare_values) != 2 or spec.compare_values[0] == spec.compare_values[1]:
            raise ValueError("Comparison requires two distinct compare_values")
        # Current frontend hasNeededFields requires a selected single field
        # on these axes and explicitly -1 on an unused optional series axis.
        for name in ("objects", "indicators", "values"):
            axes[name]["selectedFieldIndex"] = 0
        axes["series"]["selectedFieldIndex"] = -1
        if not axes["series"]["fields"]:
            # Compatibility with the deployed renderer's bare find() check:
            # repeat an existing dimension on an inactive series axis. This
            # introduces no additional source grain or numerical calculation.
            compat = copy.deepcopy(axes["objects"]["fields"][0])
            compat["id"] += "_compat"
            axes["series"]["fields"] = [compat]
            cfg["_mcp_render_compatibility"] = "Inactive repeated object dimension for Comparison empty-series guard"
        name = axes["objects"]["fields"][0]["name"]
        indicator = axes["indicators"]["fields"][0]["name"]
        cfg.update(object1=spec.compare_values[0], object2=spec.compare_values[1])
        cfg.setdefault("filters", {})[name] = {"type": "by compare", "selected": spec.compare_values}
        cfg["filters"][indicator] = {"type": "by value", "selected": spec.indicator_values}
        cfg["filtersDefault"] = copy.deepcopy(cfg["filters"])
    if spec.component_type == "HsMapLeafletChart":
        if len(axes["categories"]["fields"])!=1 or axes.get("series",{}).get("fields"):
            raise ValueError("Single-layer Leaflet requires exactly one point category and no series")
        names = {f["name"]: f for a in axes.values() for f in a.get("fields", [])}
        if not all(name in names and field_map.get(name, {}).get("type") in NUMERIC_TYPES for name in (spec.latitude_field, spec.longitude_field)):
            raise ValueError("Leaflet requires bound numeric latitude_field and longitude_field")
        if any(names[name].get("agg") not in {"max", "min", "avg"} for name in (spec.latitude_field, spec.longitude_field)):
            raise ValueError("Leaflet coordinate metrics require max/min/avg aggregation because native frontend groups by point category")
        cat_id = axes["categories"]["fields"][0]["id"]
        cfg["geokeys"] = {cat_id: {"geodataId": -1, "latfield": spec.latitude_field, "lonfield": spec.longitude_field}}
        names[spec.latitude_field]["valueType"] = "latitude"
        names[spec.longitude_field]["valueType"] = "longitude"
    if spec.component_type == "HsTilemapChart":
        cfg.update(tilesNameFontSize='13px', tilesFontSize={0:'14px'}, tilesMaxLength={0:8})
        if len(axes["categories"]["fields"]) != 1 or len(axes["values"]["fields"]) != 1 or axes.get("series",{}).get("fields"):
            raise ValueError("Tilemap requires one region field and one numeric metric")
        field = axes["categories"]["fields"][0]
        mapping = field_map[field["name"]].get("_tilemap_mapping", {})
        if mapping:
            quote = lambda value: "'" + value.replace("'", "''") + "'"
            cases = " ".join(f"WHEN {quote(raw)} THEN {quote(canonical)}" for raw, canonical in sorted(mapping.items()))
            source = '"' + field["name"].replace('"', '""') + '"'
            field.update(type="calculated", draft=True, calc=f"CASE {source} {cases} ELSE NULL END")
            cfg["_mcp_region_mapping"] = mapping
    cfg["axesDefault"] = copy.deepcopy(cfg.get("axes", []))
    cfg["_mcp_gigachat"] = {"version": 1, "key": spec.key, "kind": "native", "spec": spec.model_dump()}
    return component
