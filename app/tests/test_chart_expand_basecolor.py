"""expand slugs и baseColor default.

slugs expandH/expandV для bar/line/area/pie/stock — растянуть chart
по высоте/ширине контейнера через config_overrides={"expandV": True}.

builder ставит default baseColor='#1F77B4' чтобы bars не рендерились
#FFFFFF (пустые на белом фоне). Override через
config_overrides={"data.baseColor": "#XXX"}.

Run:
    python -m app.tests.test_chart_expand_basecolor
"""
import sys

from app.tools.builders import build_component_config
from app.tools.config_schema import (
    SLUG_SCHEMA,
    validate_config_overrides,
    apply_slug_overrides,
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


def main() -> None:
    section("expandH/expandV в SLUG_SCHEMA")
    check("expandH в SLUG_SCHEMA", "expandH" in SLUG_SCHEMA)
    check("expandV в SLUG_SCHEMA", "expandV" in SLUG_SCHEMA)
    check("expandH type=bool", SLUG_SCHEMA["expandH"]["type"] == "bool")
    check("expandV type=bool", SLUG_SCHEMA["expandV"]["type"] == "bool")

    section("expandH/expandV принимается на supported chart types")
    for ct, chart_type_in_schema in [
        ("HsBarAMchartsChart", "barChart"),
        ("HsLineAMchartsChart", "lineChart"),
        ("HsAreaAMchartsChart", "areaChart"),
        ("HsPieAMchartsChart", "pieChart"),
        ("HsStockAMchartsChart", "stockChart"),
    ]:
        cleaned, warns = validate_config_overrides(
            {"expandH": True, "expandV": True}, ct
        )
        check(f"{ct}: expandH принят",
              cleaned.get("expandH") is True, detail=str(cleaned))
        check(f"{ct}: expandV принят",
              cleaned.get("expandV") is True, detail=str(cleaned))

    section("expandH/expandV отбрасывается на не-supported")
    for ct in ["HsTableReactabularChart", "HsTotalsPanelV2",
               "HsTextBlock", "HsFilterControlPanel"]:
        cleaned, warns = validate_config_overrides({"expandH": True}, ct)
        check(f"{ct}: expandH dropped",
              "expandH" not in cleaned, detail=str(cleaned))

    section("apply_slug_overrides → top-level config.expandH/V")
    cfg = {"chartType": "barChart"}
    result = apply_slug_overrides(cfg, {"expandH": True, "expandV": True},
                                   "HsBarAMchartsChart")
    check("config.expandH=True", result.get("expandH") is True,
          detail=str(result))
    check("config.expandV=True", result.get("expandV") is True)

    section("builder ставит default baseColor")
    cfg = build_component_config(
        component_type="HsBarAMchartsChart",
        title="Test", dataset_id=5,
        category_field="region", value_fields=["amount"],
        value_fields_type="number", aggregation="sum",
    )
    check("config.baseColor='#1F77B4'",
          cfg["config"].get("baseColor") == "#1F77B4",
          detail=str(cfg["config"].get("baseColor")))
    check("config.colorStep=0",
          cfg["config"].get("colorStep") == 0)

    section("baseColor для line/area тоже")
    for ct in ["HsLineAMchartsChart", "HsAreaAMchartsChart"]:
        cfg = build_component_config(
            component_type=ct, title="Test", dataset_id=5,
            category_field="month", value_fields=["amount"],
            value_fields_type="number", aggregation="sum",
        )
        check(f"{ct}: baseColor=#1F77B4",
              cfg["config"].get("baseColor") == "#1F77B4")

    section("можно переопределить через data.baseColor slug")
    cfg = {"baseColor": "#1F77B4", "colorStep": 0}
    result = apply_slug_overrides(
        cfg, {"data.baseColor": "#FF6B35"}, "HsBarAMchartsChart"
    )
    # data.baseColor пишет в config.baseColor (top-level)
    check("override через data.baseColor",
          result.get("baseColor") == "#FF6B35", detail=str(result))

    print(f"\n===\nResult: {ok} OK, {fail} FAIL")
    sys.exit(0 if fail == 0 else 1)


if __name__ == "__main__":
    main()
