"""series_field for multi-series charts.

component_crud(action='add', series_field='product') puts the field into
axes.series.fields[0]; the frontend builds N series from the distinct
values of the field.

Supported on bar/line/area/stock. On other types — a warning.

Run:
    python -m app.tests.test_series_field
"""
import sys

from app.tools.builders import (
    build_component_config,
    check_unsupported_params,
    SERIES_FIELD_SUPPORTED_TYPES,
)


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


def find_axis(cfg, axis_type):
    for ax in cfg.get("axes", []):
        if ax.get("type") == axis_type:
            return ax
    return None


def main() -> None:
    section("series_field на BarChart → axes.series.fields[0]")
    cfg = build_component_config(
        component_type="HsBarAMchartsChart",
        title="Multi-series Bar",
        dataset_id=1,
        category_field="year",
        value_fields=["amount"],
        value_fields_type="number",
        aggregation="sum",
        series_field="product",
    )
    series_axis = find_axis(cfg["config"], "series")
    check("series axis найден", series_axis is not None)
    check("series.fields содержит 1 элемент",
          len(series_axis["fields"]) == 1, detail=str(series_axis))
    f = series_axis["fields"][0]
    check("series.fields[0].name='product'", f["name"] == "product")
    check("series.fields[0].type='string'", f["type"] == "string")
    check("series.fields[0].agg=null", f["agg"] is None)
    check("series.fields[0].datasetId=1",
          f["datasetId"] == 1)

    section("series_field на LineChart, AreaChart, StockChart тоже работает")
    for ct in ["HsLineAMchartsChart", "HsAreaAMchartsChart", "HsStockAMchartsChart"]:
        cfg = build_component_config(
            component_type=ct, title="Test", dataset_id=1,
            category_field="year", value_fields=["amount"],
            value_fields_type="number", aggregation="sum",
            series_field="product",
        )
        series_axis = find_axis(cfg["config"], "series")
        check(f"{ct}: series axis заполнен",
              series_axis and len(series_axis["fields"]) == 1)

    section("Без series_field — axes.series.fields пустой (backward-compat)")
    cfg = build_component_config(
        component_type="HsBarAMchartsChart",
        title="Single-series", dataset_id=1,
        category_field="year", value_fields=["amount"],
        value_fields_type="number", aggregation="sum",
    )
    series_axis = find_axis(cfg["config"], "series")
    check("без series_field → fields=[]",
          series_axis["fields"] == [], detail=str(series_axis))

    section("series_field='' (пустая строка) → не применяется")
    cfg = build_component_config(
        component_type="HsBarAMchartsChart",
        title="Empty series", dataset_id=1,
        category_field="year", value_fields=["amount"],
        value_fields_type="number", aggregation="sum",
        series_field="",
    )
    series_axis = find_axis(cfg["config"], "series")
    check("'' → fields=[]", series_axis["fields"] == [])

    section("series_field + field_alias_map → русский alias")
    cfg = build_component_config(
        component_type="HsBarAMchartsChart",
        title="Test", dataset_id=1,
        category_field="year", value_fields=["amount"],
        value_fields_type="number", aggregation="sum",
        series_field="product",
        field_alias_map={"product": "Категория животных"},
    )
    series_axis = find_axis(cfg["config"], "series")
    f = series_axis["fields"][0]
    check("series.alias='Категория животных' (из map)",
          f["alias"] == "Категория животных", detail=str(f))

    section("SERIES_FIELD_SUPPORTED_TYPES — sanity")
    check("BarChart в supported",
          "HsBarAMchartsChart" in SERIES_FIELD_SUPPORTED_TYPES)
    check("LineChart в supported",
          "HsLineAMchartsChart" in SERIES_FIELD_SUPPORTED_TYPES)
    check("AreaChart в supported",
          "HsAreaAMchartsChart" in SERIES_FIELD_SUPPORTED_TYPES)
    check("StockChart в supported",
          "HsStockAMchartsChart" in SERIES_FIELD_SUPPORTED_TYPES)
    check("TableReactabular НЕ в supported",
          "HsTableReactabularChart" not in SERIES_FIELD_SUPPORTED_TYPES)

    section("check_unsupported_params — series_field на supported → 0 warning")
    w = check_unsupported_params("HsBarAMchartsChart", series_field="product")
    check("BarChart + series_field → 0 warnings", w == [], detail=str(w))

    w = check_unsupported_params("HsLineAMchartsChart", series_field="product")
    check("LineChart + series_field → 0 warnings", w == [])

    section("check_unsupported_params — series_field на не-chart типе → warning")
    for ct in ["HsPivotChart", "HsTableReactabularChart", "HsPieAMchartsChart",
               "HsTextBlock"]:
        w = check_unsupported_params(ct, series_field="product")
        check(f"{ct} + series_field → 1 warning",
              len(w) == 1, detail=str(w))

    section("Sanity: series_field=None → 0 warnings")
    w = check_unsupported_params("HsBarAMchartsChart", series_field=None)
    check("None → 0 warnings", w == [])

    print(f"\n===\nResult: {ok} OK, {fail} FAIL")
    sys.exit(0 if fail == 0 else 1)


if __name__ == "__main__":
    main()
