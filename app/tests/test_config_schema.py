"""Unit tests for config_schema.py — slug validation, resolution, suggestions.

Validates the core "slug-overrides" system: ~270 slugs, type/range
clamping, fuzzy suggestions, and section-aware dispatch are the heart
of the visual customization story — silent regressions there break
config_overrides on every component type.

Run:
    python -m app.tests.test_config_schema
"""
import sys

from app.tools.config_schema import (
    SLUG_SCHEMA,
    CHART_TYPE_MAP,
    suggest_slug,
    validate_config_overrides,
    apply_slug_overrides,
    apply_title,
    apply_bg_color,
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
    section("SLUG_SCHEMA registry shape")
    check("non-empty registry", len(SLUG_SCHEMA) > 200,
          detail=f"size={len(SLUG_SCHEMA)}")
    # Lower bound only — schema grows over time as new slugs are added.
    # ~270 today; bump the floor when intentionally adding more.
    check("registry size at least matches documented count (≥250)",
          len(SLUG_SCHEMA) >= 250,
          detail=f"size={len(SLUG_SCHEMA)}")
    # Every entry must have type
    bad = [k for k, v in SLUG_SCHEMA.items() if "type" not in v]
    check("every slug has 'type'", not bad,
          detail=f"missing: {bad[:3]}")

    section("CHART_TYPE_MAP coverage")
    check("CHART_TYPE_MAP non-empty", len(CHART_TYPE_MAP) >= 25,
          detail=f"size={len(CHART_TYPE_MAP)}")
    # Common types must map
    for ctype in ["HsTableReactabularChart", "HsBarAMchartsChart",
                  "HsPieAMchartsChart", "HsTotalsPanelV2"]:
        check(f"CHART_TYPE_MAP has {ctype}", ctype in CHART_TYPE_MAP)

    section("suggest_slug — fuzzy matching")
    s = suggest_slug("legend.visibel")
    check("typo 'legend.visibel' → suggestion", s is not None, detail=f"got {s!r}")
    s = suggest_slug("margin.lft")
    check("typo 'margin.lft' → suggestion", s is not None, detail=f"got {s!r}")
    s = suggest_slug("totally_unrelated_xyz")
    check("garbage → None", s is None, detail=f"got {s!r}")

    section("validate_config_overrides — type coercion")
    cleaned, warns = validate_config_overrides(
        {"legend.visible": "true"}, "HsBarAMchartsChart"
    )
    check("'true' string → bool True",
          cleaned.get("legend.visible") is True, detail=str(cleaned))

    cleaned, warns = validate_config_overrides(
        {"fontSize": "14"}, "HsBarAMchartsChart"
    )
    check("string '14' → int 14",
          cleaned.get("fontSize") == 14, detail=str(cleaned))

    section("validate_config_overrides — range clamping")
    cleaned, warns = validate_config_overrides(
        {"fontSize": 999}, "HsBarAMchartsChart"
    )
    # fontSize max=72
    check("fontSize=999 clamped to ≤72",
          cleaned.get("fontSize") == 72, detail=str(cleaned))

    cleaned, warns = validate_config_overrides(
        {"margin.l": -50}, "HsBarAMchartsChart"
    )
    # margin.l min=0
    check("margin.l=-50 clamped to ≥0",
          cleaned.get("margin.l") == 0, detail=str(cleaned))

    section("validate_config_overrides — enum check")
    cleaned, warns = validate_config_overrides(
        {"legend.position": "outer-galaxy"}, "HsBarAMchartsChart"
    )
    check("invalid enum dropped",
          "legend.position" not in cleaned, detail=str(cleaned))
    check("invalid enum produces warning",
          any("legend.position" in w for w in warns), detail=str(warns))

    section("validate_config_overrides — unknown slug + suggestion")
    cleaned, warns = validate_config_overrides(
        {"legend.visibel": True}, "HsBarAMchartsChart"
    )
    check("unknown slug dropped",
          "legend.visibel" not in cleaned, detail=str(cleaned))

    section("apply_slug_overrides — universal slugs")
    cfg = {
        "margin": {"l": 5, "r": 10, "t": 10, "b": 5, "pad": 0},
        "outline": {"enabled": False, "width": 4, "color": "#DDDFE4"},
        "bgColor": "rgba(255,255,255,1)",
    }
    result = apply_slug_overrides(cfg, {"margin.l": 20, "outline.enabled": True})
    check("margin.l=20 applied",
          result["margin"]["l"] == 20, detail=str(result.get("margin")))
    check("outline.enabled=True applied",
          result["outline"]["enabled"] is True, detail=str(result.get("outline")))

    section("apply_slug_overrides — bgColor at top level")
    result = apply_slug_overrides(cfg, {"bgColor": "rgba(0,0,0,1)"})
    check("bgColor applied at top level",
          result.get("bgColor") == "rgba(0,0,0,1)", detail=str(result))

    section("apply_slug_overrides — does not mutate input")
    original = {"margin": {"l": 5}}
    _ = apply_slug_overrides(original, {"margin.l": 99})
    check("input config not mutated",
          original["margin"]["l"] == 5, detail=str(original))

    section("apply_title — per-type dispatch")
    cfg_table = {"columns": []}
    apply_title(cfg_table, "HsTableReactabularChart", "My Table")
    # Title must land *somewhere* in the dict — assert it appears in the
    # serialized form, not just that the call didn't raise.
    import json as _json
    check("apply_title on table writes 'My Table' into config",
          "My Table" in _json.dumps(cfg_table), detail=str(cfg_table))

    cfg_chart = {}
    apply_title(cfg_chart, "HsBarAMchartsChart", "My Chart")
    check("apply_title on chart writes 'My Chart' into config",
          "My Chart" in _json.dumps(cfg_chart), detail=str(cfg_chart))

    section("apply_bg_color — per-type dispatch")
    cfg_chart = {"bgColor": "rgba(255,255,255,1)"}
    apply_bg_color(cfg_chart, "HsBarAMchartsChart", "rgba(0,0,255,0.5)")
    check("apply_bg_color updates chart",
          cfg_chart.get("bgColor") == "rgba(0,0,255,0.5)" or
          cfg_chart.get("backgroundColor") == "rgba(0,0,255,0.5)",
          detail=str(cfg_chart))

    section("rules.{n}.{prop} — conditional formatting slugs")
    # Bad rule prop → must produce a warning, not silently accept.
    cleaned, warns = validate_config_overrides(
        {"rules.0.bogus_property_xyz": "anything"},
        "HsTableReactabularChart",
    )
    check("unknown rules.* prop dropped",
          "rules.0.bogus_property_xyz" not in cleaned, detail=str(cleaned))
    check("unknown rules.* prop produces warning",
          any("bogus_property_xyz" in w for w in warns), detail=str(warns))
    # rules.* on non-table chart → must warn (not applicable)
    cleaned, warns = validate_config_overrides(
        {"rules.0.field": "amount"},
        "HsBarAMchartsChart",
    )
    check("rules.* on non-table dropped",
          "rules.0.field" not in cleaned, detail=str(cleaned))

    section("subtitle — top-level slug, разрешён на 11 типах")
    # ALLOWED: типы, у которых frontend поддерживает поле config.subtitle.
    allowed = [
        ("HsBarAMchartsChart", "barChart"),
        ("HsLineAMchartsChart", "lineChart"),
        ("HsPieAMchartsChart", "pieChart"),
        ("HsStockAMchartsChart", "stockChart"),
        ("HsSunburstChart", "sunburstChart"),
        ("HsParallelCoordsChart", "parallelCoordsChart"),
        ("HsTreeGraph", "treeGraph"),
        ("HsTreeMap", "treeMap"),
        ("HsTotalsPanelV2", "totalsPanelV2"),
        ("HsTableReactabularChart", "table"),
        # subheader не в CHART_TYPE_MAP как отдельный component_type, не тестируем
    ]
    for ct, _expected_chart in allowed:
        cleaned, warns = validate_config_overrides({"subtitle": "Под."}, ct)
        check(f"subtitle принимается на {ct}",
              cleaned.get("subtitle") == "Под.", detail=str(cleaned))

    # NOT-ALLOWED: типы, у которых нет поля config.subtitle
    not_allowed = ["HsRadarAMchartsChart", "HsBubbleAMchartsChart",
                   "HsSpeedometerV2AMcharts", "HsTilemapChart",
                   "HsTextBlock", "HsImagePanel"]
    for ct in not_allowed:
        cleaned, warns = validate_config_overrides({"subtitle": "X"}, ct)
        check(f"subtitle отбрасывается на {ct} (нет config.subtitle)",
              "subtitle" not in cleaned, detail=f"cleaned={cleaned}")
        check(f"  + warning про {ct}",
              any("subtitle" in w for w in warns), detail=str(warns))

    # Edge cases
    cleaned, _ = validate_config_overrides({"subtitle": ""}, "HsBarAMchartsChart")
    check("пустая строка валидна (для очистки subtitle)",
          cleaned.get("subtitle") == "", detail=str(cleaned))

    # Coerce — целое число → строка (str schema всегда coerce'ит)
    cleaned, _ = validate_config_overrides({"subtitle": 42}, "HsBarAMchartsChart")
    check("число 42 coerce'ится в строку '42'",
          cleaned.get("subtitle") == "42", detail=str(cleaned))

    # apply_slug_overrides — запись в config.subtitle через top-level dispatch
    cfg = {"subtitle": ""}
    result = apply_slug_overrides(cfg, {"subtitle": "Доп. строка"}, "HsBarAMchartsChart")
    check("apply_slug_overrides пишет в config.subtitle",
          result.get("subtitle") == "Доп. строка", detail=str(result))

    # apply_slug_overrides — на конфиге БЕЗ subtitle поля (top-level dispatch
    # должен создать ключ)
    cfg_empty = {"chartType": "barChart"}
    result = apply_slug_overrides(cfg_empty, {"subtitle": "X"}, "HsBarAMchartsChart")
    check("apply_slug_overrides создаёт subtitle если ключа не было",
          result.get("subtitle") == "X", detail=str(result))

    section("columns.{fieldId}.{prop} — per-column overrides")
    # A real COLUMN_PROPS entry: width is type=int. Should be accepted.
    cleaned, warns = validate_config_overrides(
        {"columns.amount.width": 200},
        "HsTableReactabularChart",
    )
    check("columns.amount.width=200 accepted on table",
          cleaned.get("columns.amount.width") == 200,
          detail=f"cleaned={cleaned} warns={warns}")

    cleaned, warns = validate_config_overrides(
        {"columns.amount.width": 200},
        "HsBarAMchartsChart",  # not table — should warn
    )
    check("columns.* on non-table dropped",
          "columns.amount.width" not in cleaned, detail=str(cleaned))

    print(f"\n===\nResult: {ok} OK, {fail} FAIL")
    sys.exit(0 if fail == 0 else 1)


if __name__ == "__main__":
    main()
