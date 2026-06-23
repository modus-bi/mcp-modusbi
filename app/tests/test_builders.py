"""Integration smoke tests for builders.py.

For each registered component type — invoke build_component_config()
with minimal valid args and assert the produced config is a dict that
round-trips through config_schema.apply_slug_overrides() without
exception. This is regression armor against shared-helper changes
(_NO_DATA_TYPES, _apply_visual_overrides, BUILDER_DEFAULTS) that
could silently break a subset of types.

Run:
    python -m app.tests.test_builders
"""
import sys

from app.tools.builders import build_component_config
from app.tools.config_schema import apply_slug_overrides


ok = 0
fail = 0


def check(label: str, cond: bool, detail: str = "") -> None:
    global ok, fail
    if cond:
        ok += 1
        print(f"  [OK ] {label}")
    else:
        fail += 1
        suffix = f" — {detail}" if detail else ""
        print(f"  [FAIL] {label}{suffix}")


def section(title: str) -> None:
    print(f"\n=== {title} ===")


# Минимальные args для каждого component type. Различаются — некоторым нужен
# value_field, некоторым только title (текстовые/utility).
TYPE_FIXTURES = {
    "HsTableReactabularChart": {
        "value_fields": ["amount"], "category_field": "region",
        "value_fields_type": "number", "aggregation": "none",
    },
    "HsTotalsPanelV2": {
        "value_fields": ["amount"], "category_field": "",
        "value_fields_type": "number", "aggregation": "sum",
    },
    "HsPieAMchartsChart": {
        "value_fields": ["amount"], "category_field": "region",
        "value_fields_type": "number", "aggregation": "sum",
    },
    "HsBarAMchartsChart": {
        "value_fields": ["amount"], "category_field": "region",
        "value_fields_type": "number", "aggregation": "sum",
    },
    "HsLineAMchartsChart": {
        "value_fields": ["amount"], "category_field": "month",
        "value_fields_type": "number", "aggregation": "sum",
    },
    "HsAreaAMchartsChart": {
        "value_fields": ["amount"], "category_field": "month",
        "value_fields_type": "number", "aggregation": "sum",
    },
    "HsRadarAMchartsChart": {
        "value_fields": ["score"], "category_field": "metric",
        "value_fields_type": "number", "aggregation": "max",
    },
    "HsStockAMchartsChart": {
        "value_fields": ["price"], "category_field": "date",
        "value_fields_type": "number", "aggregation": "max",
    },
    "HsSpeedometerV2AMcharts": {
        "value_fields": ["score"], "category_field": "",
        "value_fields_type": "number", "aggregation": "max",
    },
    "HsBubbleAMchartsChart": {
        "value_fields": ["x", "y", "size"], "category_field": "category",
        "value_fields_type": "number", "aggregation": "max",
    },
    "HsSunburstChart": {
        "value_fields": ["value"], "category_field": "level1",
        "value_fields_type": "number", "aggregation": "sum",
    },
    "HsTreeMap": {
        "value_fields": ["amount"], "category_field": "region",
        "value_fields_type": "number", "aggregation": "sum",
    },
    "HsParallelCoordsChart": {
        "value_fields": ["m1", "m2", "m3"], "category_field": "row",
        "value_fields_type": "number", "aggregation": "max",
    },
    "HsPivotChart": {
        "value_fields": ["amount"], "category_field": "region",
        "value_fields_type": "number", "aggregation": "sum",
        "row_fields": "region", "column_fields": "year",
    },
    "HsComparisonChart": {
        "value_fields": ["metric_value"], "category_field": "object",
        "value_fields_type": "number", "aggregation": "sum",
        "column_fields": "metric_name",
    },
    "HsTreeGraph": {
        "value_fields": ["value"], "category_field": "id",
        "value_fields_type": "number", "aggregation": "max",
    },
    "HsMapLeafletChart": {
        "value_fields": ["density"], "category_field": "region_code",
        "value_fields_type": "number", "aggregation": "sum",
    },
    "HsTilemapChart": {
        "value_fields": ["count"], "category_field": "x",
        "value_fields_type": "number", "aggregation": "sum",
    },
    # No-data utility types
    "HsTextBlock": {
        "value_fields": [], "category_field": "",
        "value_fields_type": "number", "aggregation": None,
        "text_content": "<h1>Hello</h1>",
    },
    "HsFilterControlPanel": {
        "value_fields": [], "category_field": "",
        "value_fields_type": "number", "aggregation": None,
    },
    "HsTabsPanel": {
        "value_fields": [], "category_field": "",
        "value_fields_type": "number", "aggregation": None,
    },
    "HsAudioplayer": {
        "value_fields": [], "category_field": "",
        "value_fields_type": "number", "aggregation": None,
    },
    "HsImagePanel": {
        "value_fields": [], "category_field": "",
        "value_fields_type": "number", "aggregation": None,
    },
    "HsIframe": {
        "value_fields": [], "category_field": "",
        "value_fields_type": "number", "aggregation": None,
    },
    "HsHierarchicalFilterPanel": {
        "value_fields": [], "category_field": "",
        "value_fields_type": "number", "aggregation": None,
    },
    "HsSwitchControlPanel": {
        "value_fields": [], "category_field": "",
        "value_fields_type": "number", "aggregation": None,
    },
    "HsSubheaderComponent": {
        "value_fields": [], "category_field": "",
        "value_fields_type": "number", "aggregation": None,
    },
    "HsPageContainer": {
        "value_fields": [], "category_field": "",
        "value_fields_type": "number", "aggregation": None,
    },
}


def main() -> None:
    section(f"build_component_config for {len(TYPE_FIXTURES)} component types")
    built_count = 0
    for ctype, fixture in TYPE_FIXTURES.items():
        try:
            cfg = build_component_config(
                component_type=ctype,
                title=f"Test {ctype}",
                dataset_id=1,
                **fixture,
            )
            check(f"{ctype}: returns dict", isinstance(cfg, dict))
            check(f"{ctype}: has 'config' key", "config" in cfg)
            built_count += 1
        except Exception as e:
            check(f"{ctype}: build_component_config", False, detail=str(e))

    section(f"apply_slug_overrides round-trip on {built_count} configs")
    overrides = {"legend.visible": True, "outline.color": "rgba(0,0,0,0.5)"}
    for ctype, fixture in TYPE_FIXTURES.items():
        try:
            cfg = build_component_config(
                component_type=ctype,
                title=f"Test {ctype}",
                dataset_id=1,
                **fixture,
            )
            result = apply_slug_overrides(cfg.get("config", {}), overrides)
            check(f"{ctype}: apply_slug_overrides → dict", isinstance(result, dict))
        except Exception as e:
            check(f"{ctype}: apply_slug_overrides", False, detail=str(e))

    print(f"\n===\nResult: {ok} OK, {fail} FAIL")
    sys.exit(0 if fail == 0 else 1)


if __name__ == "__main__":
    main()
