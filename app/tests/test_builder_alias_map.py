"""builders.py принимает field_alias_map для resolve alias.

build_component_config принимает параметр field_alias_map={name:alias},
который передаётся caller'ом после fetch_dataset_alias_map. Без него alias
падает обратно на технический name поля. field_alias_map применяется к:
  - category_field_config
  - value_field_configs
  - _parse_extra_fields (row/column/size)
  - where_filter fields

Run:
    python -m app.tests.test_builder_alias_map
"""
import asyncio
import sys

from app.tools.builders import build_component_config, _parse_extra_fields
from app.tools.component_filters import fetch_dataset_alias_map


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
    section("build_component_config: alias_map применяется к value_field")
    cfg = build_component_config(
        component_type="HsFilterControlPanel",
        title="Test",
        dataset_id=5,
        category_field="",
        value_fields=["region"],
        value_fields_type="string",
        aggregation=None,
        field_alias_map={"region": "Район"},
    )
    filters_axis = find_axis(cfg["config"], "filters")
    check("filters axis есть", filters_axis is not None,
          detail=str(cfg["config"].get("axes", []))[:200])
    f = filters_axis["fields"][0] if filters_axis else None
    check("alias='Район' (из map), не 'region' (name)",
          f and f["alias"] == "Район",
          detail=f"got alias={f.get('alias') if f else None!r}")
    check("name='region' (technical)",
          f and f["name"] == "region")

    section("Без map alias=name (backward-compat)")
    cfg = build_component_config(
        component_type="HsFilterControlPanel",
        title="Test", dataset_id=5, category_field="",
        value_fields=["region"], value_fields_type="string", aggregation=None,
    )
    filters_axis = find_axis(cfg["config"], "filters")
    f = filters_axis["fields"][0] if filters_axis else None
    check("без map: alias='region' (fallback)",
          f and f["alias"] == "region", detail=str(f))

    section("category_field тоже из map (BarChart)")
    cfg = build_component_config(
        component_type="HsBarAMchartsChart",
        title="Bar", dataset_id=5,
        category_field="region",
        value_fields=["dtp_count"],
        value_fields_type="number", aggregation="sum",
        field_alias_map={"region": "Район", "dtp_count": "Количество ДТП"},
    )
    cat_axis = find_axis(cfg["config"], "categories")
    val_axis = find_axis(cfg["config"], "values")
    cat_field = cat_axis["fields"][0] if cat_axis else None
    val_field = val_axis["fields"][0] if val_axis else None
    check("category alias='Район'",
          cat_field and cat_field["alias"] == "Район",
          detail=str(cat_field))
    check("value alias='Количество ДТП'",
          val_field and val_field["alias"] == "Количество ДТП",
          detail=str(val_field))

    section("_parse_extra_fields поддерживает alias_map")
    parsed = _parse_extra_fields(
        "year,quarter", dataset_id=1,
        field_alias_map={"year": "Год", "quarter": "Квартал"},
    )
    check("row_fields[0].alias='Год'",
          parsed[0]["alias"] == "Год", detail=str(parsed[0]))
    check("row_fields[1].alias='Квартал'",
          parsed[1]["alias"] == "Квартал", detail=str(parsed[1]))

    # Без map: fallback на name
    parsed = _parse_extra_fields("year", dataset_id=1)
    check("без map: alias=name fallback",
          parsed[0]["alias"] == "year")

    section("where_filter alias тоже из map")
    cfg = build_component_config(
        component_type="HsTableReactabularChart",
        title="T", dataset_id=5, category_field="region",
        value_fields=["amount"], value_fields_type="number", aggregation="none",
        where_filter=[{"field": "region", "operator": "=", "value": "Region A"}],
        field_alias_map={"region": "Район"},
    )
    filters_axis = find_axis(cfg["config"], "filters")
    f = filters_axis["fields"][0] if filters_axis else None
    check("where_filter alias='Район'",
          f and f["alias"] == "Район",
          detail=str(f))

    section("Поле НЕ в alias_map → fallback на name")
    cfg = build_component_config(
        component_type="HsBarAMchartsChart",
        title="X", dataset_id=5, category_field="unknown_field",
        value_fields=["another_unknown"], value_fields_type="number",
        aggregation="sum",
        field_alias_map={"region": "Район"},  # не содержит наших полей
    )
    cat_axis = find_axis(cfg["config"], "categories")
    cat_field = cat_axis["fields"][0]
    check("unknown_field → alias='unknown_field' (fallback)",
          cat_field["alias"] == "unknown_field",
          detail=str(cat_field))

    section("fetch_dataset_alias_map graceful errors")
    class BadClient:
        async def api_call(self, *args, **kwargs):
            raise RuntimeError("network broken")

    result = asyncio.get_event_loop().run_until_complete(
        fetch_dataset_alias_map(BadClient(), 5)
    )
    check("network error → пустой dict", result == {},
          detail=str(result))

    class NoneClient:
        async def api_call(self, *args, **kwargs):
            return None
    result = asyncio.get_event_loop().run_until_complete(
        fetch_dataset_alias_map(NoneClient(), 5)
    )
    check("None response → пустой dict", result == {})

    class GoodClient:
        async def api_call(self, *args, **kwargs):
            return {
                "status": 200,
                "data": [{"fields": [
                    {"name": "region", "alias": "Район"},
                    {"name": "amount", "alias": "Сумма"},
                    {"name": "empty_alias", "alias": ""},  # пустой alias пропускаем
                    {"name": "null_alias", "alias": None},
                ]}],
            }
    result = asyncio.get_event_loop().run_until_complete(
        fetch_dataset_alias_map(GoodClient(), 5)
    )
    check("valid response → map собран",
          result == {"region": "Район", "amount": "Сумма"},
          detail=str(result))
    check("dataset_id=None → пустой dict",
          asyncio.get_event_loop().run_until_complete(
              fetch_dataset_alias_map(GoodClient(), None)
          ) == {})

    print(f"\n===\nResult: {ok} OK, {fail} FAIL")
    sys.exit(0 if fail == 0 else 1)


if __name__ == "__main__":
    main()
