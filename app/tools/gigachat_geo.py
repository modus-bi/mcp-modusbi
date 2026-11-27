"""Platform vocabulary and data integrity checks, independent of any report."""
import json
import math
from pathlib import Path
import re
from .gigachat_models import NativeVisualization, VisualizationAxis, VisualizationMetric

REGIONS = json.loads(Path(__file__).with_name("tilemap_regions.json").read_text(encoding="utf-8"))["regions"]
READABLE_HEIGHTS = {"HsTreeGraph": 26, "HsMapLeafletChart": 24, "HsTilemapChart": 30,
                    "HsSunburstChart":26, "HsParallelCoordsChart":20, "HsPivotChart":18}


def normalize_native(spec, schema, previous=None, mode="merge"):
    if mode not in {"merge","replace"}:raise ValueError("fields_mode must be merge or replace")
    protected = spec.component_type in {"HsTreeGraph","HsMapLeafletChart","HsTilemapChart"}
    axes = {a.axis:a.model_copy(deep=True) for a in spec.axes}
    updates={}
    if spec.component_type in READABLE_HEIGHTS and spec.height < READABLE_HEIGHTS[spec.component_type]:
        updates['height'] = READABLE_HEIGHTS[spec.component_type]
    if protected and "height" not in spec.model_fields_set:
        updates["height"] = READABLE_HEIGHTS[spec.component_type]
    if previous and protected and mode=="merge":
        old=NativeVisualization.model_validate(previous)
        if old.dataset_id!=spec.dataset_id or old.component_type!=spec.component_type:
            raise ValueError("GEOMETRY_SOURCE_CHANGE: use explicit fields_mode=replace")
        for a in old.axes:
            if a.axis not in axes:axes[a.axis]=a.model_copy(deep=True)
            elif a.axis=="values":
                current=axes[a.axis]
                current_names=set(current.fields)|{m.field or m.label for m in current.metrics}
                current.fields += [f for f in a.fields if f not in current_names]
                current.metrics += [m for m in a.metrics if (m.field or m.label) not in current_names]
        for name in ("latitude_field","longitude_field","label_field","color_field","size_field"):
            if not getattr(spec,name):updates[name]=getattr(old,name)
        for name in ("row", "width", "height"):
            if name not in spec.model_fields_set:updates[name]=getattr(old,name)
    spec=spec.model_copy(update=updates)
    if spec.component_type=="HsMapLeafletChart" and "values" in axes:
        values=axes["values"]
        bound=set(values.fields)|{m.field for m in values.metrics}
        for name in (spec.latitude_field,spec.longitude_field):
            if name and name not in bound:
                values.metrics.append(VisualizationMetric(label=name,field=name,kind="max"))
    for a in axes.values():
        a.metrics=[m.model_copy(update={"format":"text"}) if m.kind=="raw" and m.format=="number" and schema.get(m.field,{}).get("type") in {"text","string","date","datetime","timestamp"} else m for m in a.metrics]
    return spec.model_copy(update={"axes":list(axes.values())})


def region_key(value):
    text = str(value).casefold().replace("ё", "е").replace("–", "-").replace("—", "-")
    text = re.sub(r"^\s*(?:г\.|город)\s*", "", text)
    text = re.sub(r"\s*\([^)]*\)", "", text)
    return " ".join(text.split())


def canonical_region(value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("Tilemap region is empty; no rows may be silently dropped")
    matches = {r["name"] for r in REGIONS if region_key(value) in {region_key(r["name"]), region_key(r["code"])}}
    if len(matches) != 1:
        raise ValueError(f"Tilemap region {value!r} is unknown or ambiguous; use native region names")
    return next(iter(matches))


def validate_tree(rows, identity, parent):
    ids = [r[identity] for r in rows]
    if any(isinstance(n, bool) or not isinstance(n, (int, float)) or not math.isfinite(n) or abs(n)>2**53-1 for n in ids):
        raise ValueError("Tree identity must be finite and non-null")
    if len(ids) != len(set(ids)):
        raise ValueError("Tree identity is not unique; aggregation must not hide duplicate nodes")
    graph = {r[identity]: r[parent] for r in rows}
    if any(p is not None and (isinstance(p,bool) or not isinstance(p,(int,float)) or not math.isfinite(p) or abs(p)>2**53-1) for p in graph.values()):
        raise ValueError("Tree parent must be null or a safe finite numeric identity")
    if any(p is not None and p not in graph for p in graph.values()):
        raise ValueError("Tree filter/source leaves orphan nodes: retain their parents or use a complete branch")
    done = set()
    for node in graph:
        path = set()
        while node is not None and node not in done:
            if node in path:
                raise ValueError("Tree contains a cycle")
            path.add(node)
            node = graph[node]
        done.update(path)


def validate_points(rows, dimensions, latitude, longitude):
    coordinates = {}
    for row in rows:
        lat, lon = row[latitude], row[longitude]
        if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) for v in (lat, lon)) or not -90 <= lat <= 90 or not -180 <= lon <= 180:
            raise ValueError("Map coordinates must be finite latitude[-90,90], longitude[-180,180]")
        key = tuple(row[d] for d in dimensions)
        if any(v is None or isinstance(v,bool) or v=="" or isinstance(v,(int,float)) and (not math.isfinite(v) or abs(v)>2**53-1) for v in key):
            raise ValueError("Map point identity must be nonempty and safe for JavaScript; use a string field for large integers")
        if key in coordinates and coordinates[key] != (lat, lon):
            raise ValueError("Point category has multiple coordinates; choose a finer identity instead of summing or averaging coordinates")
        coordinates[key] = lat, lon
