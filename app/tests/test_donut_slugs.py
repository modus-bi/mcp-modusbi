"""donut/pie slugs (showDonut, summEnabled, etc.).

6 slugs (showDonut, radius, summEnabled, summFontSize, summColor,
labelsTemplate) are accepted via config_overrides on HsPieAMchartsChart.

Run:
    python -m app.tests.test_donut_slugs
"""
import sys

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
    section("6 slugs в SLUG_SCHEMA")
    new_slugs = ["showDonut", "radius", "summEnabled", "summFontSize",
                 "summColor", "labelsTemplate"]
    for s in new_slugs:
        check(f"{s} в SLUG_SCHEMA", s in SLUG_SCHEMA)

    section("типы slug'ов корректны")
    check("showDonut type=bool",
          SLUG_SCHEMA["showDonut"]["type"] == "bool")
    check("radius type=int min=0 max=100",
          SLUG_SCHEMA["radius"]["type"] == "int"
          and SLUG_SCHEMA["radius"]["min"] == 0
          and SLUG_SCHEMA["radius"]["max"] == 100)
    check("summFontSize type=int",
          SLUG_SCHEMA["summFontSize"]["type"] == "int")
    check("summColor type=color",
          SLUG_SCHEMA["summColor"]["type"] == "color")
    check("labelsTemplate type=str",
          SLUG_SCHEMA["labelsTemplate"]["type"] == "str")
    check("labelsTemplate default='[[percents]]%'",
          SLUG_SCHEMA["labelsTemplate"]["default"] == "[[percents]]%")

    section("applies_to включает pieChart")
    for s in new_slugs:
        # radius also applies to radarChart — check membership, not exact
        # list equality.
        check(f"{s}.applies_to содержит 'pieChart'",
              "pieChart" in SLUG_SCHEMA[s]["applies_to"])

    section("принимается на PieChart")
    cleaned, warns = validate_config_overrides(
        {
            "showDonut": True,
            "radius": 80,
            "summEnabled": True,
            "summFontSize": 36,
            "summColor": "#1F77B4",
            "labelsTemplate": "[[categories]] — [[percents]]%",
        },
        "HsPieAMchartsChart",
    )
    check("showDonut=True", cleaned.get("showDonut") is True)
    check("radius=80", cleaned.get("radius") == 80)
    check("summEnabled=True", cleaned.get("summEnabled") is True)
    check("summFontSize=36", cleaned.get("summFontSize") == 36)
    check("summColor=#1F77B4", cleaned.get("summColor") == "#1F77B4")
    check("labelsTemplate сохранён",
          cleaned.get("labelsTemplate") == "[[categories]] — [[percents]]%")

    section("отбрасывается на не-pie types")
    for ct in ["HsBarAMchartsChart", "HsLineAMchartsChart",
               "HsTableReactabularChart", "HsTotalsPanelV2"]:
        cleaned, warns = validate_config_overrides(
            {"showDonut": True, "radius": 80}, ct
        )
        check(f"{ct}: showDonut dropped",
              "showDonut" not in cleaned, detail=str(cleaned))
        check(f"{ct}: radius dropped",
              "radius" not in cleaned)

    section("clamp значений (radius)")
    cleaned, warns = validate_config_overrides(
        {"radius": 999}, "HsPieAMchartsChart"
    )
    check("radius=999 clamped to 100",
          cleaned.get("radius") == 100, detail=str(cleaned))

    cleaned, _ = validate_config_overrides(
        {"radius": -50}, "HsPieAMchartsChart"
    )
    check("radius=-50 clamped to 0",
          cleaned.get("radius") == 0)

    section("apply_slug_overrides → top-level config")
    cfg = {"chartType": "pieChart"}
    result = apply_slug_overrides(
        cfg,
        {
            "showDonut": True,
            "summEnabled": True,
            "labelsTemplate": "[[title]] [[value]]",
        },
        "HsPieAMchartsChart",
    )
    check("config.showDonut=True",
          result.get("showDonut") is True, detail=str(result))
    check("config.summEnabled=True", result.get("summEnabled") is True)
    check("config.labelsTemplate", result.get("labelsTemplate") == "[[title]] [[value]]")

    # NB: visuals.innerRadius пишется на ВЕРХНИЙ уровень config (фронт читает top-level)
    # и клампится в validate_config_overrides (90→45). Корректно покрыто в test_noeffect_fixes.

    print(f"\n===\nResult: {ok} OK, {fail} FAIL")
    sys.exit(0 if fail == 0 else 1)


if __name__ == "__main__":
    main()
