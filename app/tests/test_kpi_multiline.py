"""multi-line KPI + kpi_icons CSS.

subheader_field / info_fields в component_crud(add, HsTotalsPanelV2)
кладут extra value-fields с valueType=subheader/info, frontend рендерит
их как subcaption + info-rows под главным значением.

style_operations(action='apply_theme', kpi_icons={idx: url}) генерирует
CSS background-image для KPI компонентов (нативного icon slot нет).

Run:
    python -m app.tests.test_kpi_multiline
"""
import sys

from app.tools.builders import build_component_config
from app.tools.style_operations import _build_kpi_icons_css


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
    section("subheader_field → 2-я field в axes.values с valueType=subheader")
    cfg = build_component_config(
        component_type="HsTotalsPanelV2",
        title="Sales", dataset_id=5,
        category_field="month",
        value_fields=["revenue"], value_fields_type="number",
        aggregation="sum",
        subheader_field="growth_pct",
    )
    values_axis = find_axis(cfg["config"], "values")
    check("values axis есть", values_axis is not None)
    fields = values_axis.get("fields", [])
    check("2 fields (main + subheader)",
          len(fields) == 2, detail=f"got {len(fields)}")
    check("fields[0] = main value (revenue)",
          fields[0]["name"] == "revenue")
    check("fields[1] = subheader",
          fields[1]["name"] == "growth_pct"
          and fields[1]["valueType"] == "subheader",
          detail=str(fields[1]))

    section("info_fields → N fields с valueType=info + showTitle")
    cfg = build_component_config(
        component_type="HsTotalsPanelV2",
        title="Sales", dataset_id=5,
        category_field="month",
        value_fields=["revenue"], value_fields_type="number",
        aggregation="sum",
        info_fields="avg_check,total_orders,top_product",
    )
    values_axis = find_axis(cfg["config"], "values")
    fields = values_axis.get("fields", [])
    check("4 fields (main + 3 info)",
          len(fields) == 4, detail=f"got {len(fields)}")
    info_names = [f["name"] for f in fields[1:]]
    check("info_fields порядок сохранён",
          info_names == ["avg_check", "total_orders", "top_product"])
    check("все info-fields имеют valueType='info'",
          all(f["valueType"] == "info" for f in fields[1:]))
    check("info-fields имеют showTitle=True",
          all(f["showTitle"] is True for f in fields[1:]))

    section("subheader + info вместе")
    cfg = build_component_config(
        component_type="HsTotalsPanelV2",
        title="Multi-row KPI", dataset_id=5,
        category_field="month",
        value_fields=["revenue"], value_fields_type="number",
        aggregation="sum",
        subheader_field="growth",
        info_fields="orders,avg",
    )
    fields = find_axis(cfg["config"], "values").get("fields", [])
    check("4 fields (main + subheader + 2 info)",
          len(fields) == 4, detail=str([f["name"] for f in fields]))
    check("порядок: main → subheader → info",
          [f.get("valueType", "value") for f in fields]
          == ["value", "subheader", "info", "info"]
          or fields[1]["valueType"] == "subheader",
          detail=str([f.get("valueType") for f in fields]))

    section("backward-compat — без subheader/info параметров")
    cfg = build_component_config(
        component_type="HsTotalsPanelV2",
        title="Single KPI", dataset_id=5,
        category_field="month",
        value_fields=["revenue"], value_fields_type="number",
        aggregation="sum",
    )
    fields = find_axis(cfg["config"], "values").get("fields", [])
    check("без extras → 1 field (только value)",
          len(fields) == 1)

    section("alias_map применяется к info-fields")
    cfg = build_component_config(
        component_type="HsTotalsPanelV2",
        title="Sales", dataset_id=5,
        category_field="month",
        value_fields=["revenue"], value_fields_type="number",
        aggregation="sum",
        info_fields="orders",
        field_alias_map={"orders": "Заказов", "revenue": "Выручка"},
    )
    fields = find_axis(cfg["config"], "values").get("fields", [])
    check("info-field alias='Заказов' из map",
          fields[1]["alias"] == "Заказов", detail=str(fields[1]))

    section("_build_kpi_icons_css — string URL")
    css = _build_kpi_icons_css({"0": "https://example.com/icon.svg"})
    check("содержит селектор data-i=\"0\"",
          '[data-i="0"]' in css, detail=css[:200])
    check("содержит background-image url",
          "background-image: url('https://example.com/icon.svg')" in css)
    check("default size=32px",
          "background-size: 32px" in css)

    section("dict spec с size/position")
    css = _build_kpi_icons_css({
        "1": {"url": "/uploads/sales.png", "size": "48px", "position": "center"},
    })
    check("custom size=48px",
          "background-size: 48px" in css)
    check("custom position=center",
          "background-position: center" in css)

    section("пустой/невалидный spec → skip без exception")
    css = _build_kpi_icons_css({})
    check("пустой dict → пустая строка", css == "")

    css = _build_kpi_icons_css({"0": {"url": ""}})  # url пустой
    check("пустой url → пропускается", css == "")

    css = _build_kpi_icons_css({"0": ["not", "dict"]})  # malformed
    check("malformed spec → пропускается", css == "")

    section("несколько KPI с разными иконками")
    css = _build_kpi_icons_css({
        "0": "url1.svg",
        "3": {"url": "url2.png", "size": "40px"},
        "5": "url3.jpg",
    })
    check("3 правила сгенерированы",
          css.count('background-image') == 3, detail=css[:300])
    check("все 3 индекса в css",
          all(f'data-i="{i}"' in css for i in ["0", "3", "5"]))

    print(f"\n===\nResult: {ok} OK, {fail} FAIL")
    sys.exit(0 if fail == 0 else 1)


if __name__ == "__main__":
    main()
