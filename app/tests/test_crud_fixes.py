#!/usr/bin/env python3
"""
Regression tests for component CRUD fixes.

types_list.mcp_creatable: классифицируется по техническому c.get('type'),
    а не по человекочитаемому c.get('name').
legend_position: короткие слова top/bottom/left/right нормализуются в
    композитные enum-значения (bottom-center и т.п.) для slug legend.position.
field_sort_set: невалидный order (например 'sideways') отклоняется
    error-конвертом; явный пустой/None — валидный clear.
conditional_rule_add: поле резолвится по имени/alias/field-id из осей;
    промах по полю даёт error-конверт со списком available.
"""

import asyncio
import copy
import sys
from pathlib import Path
from unittest.mock import AsyncMock

_project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_project_root))

from app.tools.component_crud import _apply_visual_overrides, _list_types
from app.tools.component_operations import component_operations


class TestResult:
    def __init__(self, name: str, passed: bool, message: str):
        self.name = name
        self.passed = passed
        self.message = message


def run_test(func):
    async def wrapper(results: list[TestResult]):
        name = func.__name__
        try:
            await func()
            results.append(TestResult(name, True, "OK"))
            print(f"  ✅ {name}")
        except AssertionError as e:
            results.append(TestResult(name, False, str(e)))
            print(f"  ❌ {name}: {e}")
        except Exception as e:
            results.append(TestResult(name, False, f"Exception: {e}"))
            print(f"  ❌ {name}: {type(e).__name__}: {e}")
    return wrapper


# =============================================================================
# Mock clients
# =============================================================================

_TABLE_COMPONENT = {
    "type": "HsTableReactabularChart",
    "config": {
        "title": "Test Table",
        "chartType": "tableChart",
        "rules": [],
        "axes": [
            {"type": "categories", "fields": [
                {"name": "region", "id": "region_e701d6d3", "alias": "Регион"},
            ]},
            {"type": "values", "fields": [
                {"name": "dtp_count", "id": "dtp_count_7e5d6208", "alias": "Кол-во ДТП"},
            ]},
        ],
    },
}


def _make_report_client(component: dict | None = None, captured: dict | None = None) -> AsyncMock:
    """Mock client: reports get/update вокруг одного компонента."""
    client = AsyncMock()
    client.base_url = "http://localhost:3000"
    comp = copy.deepcopy(component or _TABLE_COMPONENT)

    async def mock_api_call(resource: str, action: str, **kwargs):
        if resource == "reports" and action == "get":
            return {
                "status": 200,
                "data": [{
                    "ID": 999,
                    "grid": {
                        "layouts": {"lg": [{"i": "0", "x": 0, "y": 0, "w": 12, "h": 8}]},
                        "components": {"0": comp},
                    },
                }],
            }
        if resource == "reports" and action == "update":
            if captured is not None:
                captured["data"] = kwargs.get("data", [])
            return {"status": 200}
        return {"status": 200, "data": []}

    client.api_call = AsyncMock(side_effect=mock_api_call)
    return client


def _make_types_client() -> AsyncMock:
    """Mock client: components/list с человекочитаемыми name и тех. type."""
    client = AsyncMock()

    async def mock_api_call(resource: str, action: str, **kwargs):
        if resource == "components" and action == "list":
            return {"status": 200, "data": [
                {"ID": 1, "name": "Диаграмма столбчатая (AMcharts)",
                 "caption": "Bar", "type": "HsBarAMchartsChart", "base": "internal"},
                {"ID": 2, "name": "Пользовательский график 0",
                 "caption": "Custom", "type": "CustomChart0", "base": "plugin"},
                {"ID": 3, "name": "Таблица (Reactabular)",
                 "caption": "Table", "type": "HsTableReactabularChart", "base": "internal"},
            ]}
        return {"status": 200, "data": []}

    client.api_call = AsyncMock(side_effect=mock_api_call)
    return client


def _flatten_types(result: dict) -> dict[str, dict]:
    """Собрать все компоненты из групп в map type → comp."""
    out: dict[str, dict] = {}
    for group in ("charts", "tables", "maps", "filters", "other"):
        for comp in result.get(group, []):
            out[comp["type"]] = comp
    return out


def _saved_rules(captured: dict) -> list[dict]:
    report = (captured.get("data") or [{}])[0]
    return report.get("grid", {}).get("components", {}).get("0", {}) \
        .get("config", {}).get("rules", [])


# =============================================================================
# types_list.mcp_creatable по type, не по name
# =============================================================================

@run_test
async def test_creatable_true_for_technical_type():
    """mcp_creatable=True для HsBarAMchartsChart (несмотря на русское name)."""
    result = await _list_types(_make_types_client())
    assert result.get("success"), result
    comps = _flatten_types(result)
    assert comps["HsBarAMchartsChart"]["mcp_creatable"] is True, comps["HsBarAMchartsChart"]
    assert comps["HsTableReactabularChart"]["mcp_creatable"] is True, comps["HsTableReactabularChart"]


@run_test
async def test_creatable_false_for_ui_only_type():
    """mcp_creatable=False для plugin/legacy типа (CustomChart0)."""
    result = await _list_types(_make_types_client())
    assert result.get("success"), result
    comps = _flatten_types(result)
    assert comps["CustomChart0"]["mcp_creatable"] is False, comps["CustomChart0"]


# =============================================================================
# legend_position короткие слова → композитные enum-значения
# =============================================================================

@run_test
async def test_legend_position_short_words_normalized():
    """top/bottom/left/right транслируются и применяются без warning."""
    expected = {
        "top": "top-center",
        "bottom": "bottom-center",
        "left": "middle-left",
        "right": "middle-right",
    }
    for short, full in expected.items():
        cfg, warnings = _apply_visual_overrides(
            {}, "HsBarAMchartsChart", legend_position=short,
        )
        assert cfg.get("legend", {}).get("position") == full, \
            f"'{short}' → expected '{full}', got cfg={cfg}, warnings={warnings}"
        assert not any("legend.position" in w for w in warnings), \
            f"'{short}' must not warn: {warnings}"


@run_test
async def test_legend_position_enum_passthrough():
    """Точные enum-значения (top-left и т.п.) проходят без трансляции."""
    cfg, warnings = _apply_visual_overrides(
        {}, "HsBarAMchartsChart", legend_position="top-left",
    )
    assert cfg.get("legend", {}).get("position") == "top-left", (cfg, warnings)
    assert not any("legend.position" in w for w in warnings), warnings


@run_test
async def test_legend_position_invalid_still_warns():
    """Невалидное значение по-прежнему отбрасывается с warning (не молча)."""
    cfg, warnings = _apply_visual_overrides(
        {}, "HsBarAMchartsChart", legend_position="diagonal",
    )
    assert cfg.get("legend", {}).get("position") != "diagonal", cfg
    assert any("legend.position" in w for w in warnings), warnings


# =============================================================================
# field_sort_set: невалидный order → reject, пусто/None → clear
# =============================================================================

@run_test
async def test_invalid_order_rejected():
    """order='sideways' → error-конверт, отчёт НЕ сохраняется."""
    captured = {}
    client = _make_report_client(captured=captured)
    result = await component_operations(
        client, action="field_sort_set",
        report_id=999, component_idx=0, value_field="dtp_count",
        config_overrides={"order": "sideways"},
    )
    assert result.get("success") is False, f"Expected reject: {result}"
    assert "Invalid order" in result.get("error", ""), result
    assert "asc" in result.get("hint", ""), result
    assert "data" not in captured, "report must NOT be saved on invalid order"


@run_test
async def test_none_order_still_clears():
    """Без config_overrides (order=None) — валидный clear."""
    captured = {}
    client = _make_report_client(captured=captured)
    result = await component_operations(
        client, action="field_sort_set",
        report_id=999, component_idx=0, value_field="dtp_count",
    )
    assert result.get("success") is True, result
    assert "None" in result.get("message", ""), result
    assert "data" in captured, "clear must be persisted"


@run_test
async def test_empty_order_still_clears():
    """order='' (явный пустой) — тоже валидный clear, не reject."""
    client = _make_report_client()
    result = await component_operations(
        client, action="field_sort_set",
        report_id=999, component_idx=0, value_field="dtp_count",
        config_overrides={"order": ""},
    )
    assert result.get("success") is True, result


@run_test
async def test_valid_order_applies():
    """order='desc' по-прежнему применяется и персистится."""
    captured = {}
    client = _make_report_client(captured=captured)
    result = await component_operations(
        client, action="field_sort_set",
        report_id=999, component_idx=0, value_field="dtp_count",
        config_overrides={"order": "desc"},
    )
    assert result.get("success") is True, result
    report = captured["data"][0]
    fields = report["grid"]["components"]["0"]["config"]["axes"][1]["fields"]
    assert fields[0]["order"] == "desc", fields


# =============================================================================
# conditional_rule_add: поле должно резолвиться из осей
# =============================================================================

@run_test
async def test_unknown_field_rejected():
    """Несуществующее поле → error-конверт + available, правило НЕ пишется."""
    captured = {}
    client = _make_report_client(captured=captured)
    result = await component_operations(
        client, action="conditional_rule_add",
        report_id=999, component_idx=0,
        config_overrides={"field": "nonexistent_field_xyz", "operator": ">", "value": 5},
    )
    assert result.get("success") is False, f"Expected reject: {result}"
    assert "not found in axes" in result.get("error", ""), result
    available = result.get("available", [])
    assert "dtp_count" in available and "region" in available, available
    assert "Регион" in available, f"aliases must be listed: {available}"
    assert "data" not in captured, "rule must NOT be saved for unknown field"


@run_test
async def test_resolve_by_name():
    """Резолв по name → fieldId = internal id из оси."""
    captured = {}
    client = _make_report_client(captured=captured)
    result = await component_operations(
        client, action="conditional_rule_add",
        report_id=999, component_idx=0,
        config_overrides={"field": "dtp_count", "operator": ">", "value": 1000},
    )
    assert result.get("success") is True, result
    rules = _saved_rules(captured)
    assert rules and rules[0]["fieldId"] == "dtp_count_7e5d6208", rules


@run_test
async def test_resolve_by_alias():
    """Резолв по alias (русская подпись) → тот же internal id."""
    captured = {}
    client = _make_report_client(captured=captured)
    result = await component_operations(
        client, action="conditional_rule_add",
        report_id=999, component_idx=0,
        config_overrides={"field": "Кол-во ДТП", "operator": ">=", "value": 10},
    )
    assert result.get("success") is True, result
    rules = _saved_rules(captured)
    assert rules and rules[0]["fieldId"] == "dtp_count_7e5d6208", rules


@run_test
async def test_raw_field_id_passthrough():
    """Уже готовый field-id из осей принимается как есть."""
    captured = {}
    client = _make_report_client(captured=captured)
    result = await component_operations(
        client, action="conditional_rule_add",
        report_id=999, component_idx=0,
        config_overrides={"field": "region_e701d6d3", "operator": "=", "value": "Region A"},
    )
    assert result.get("success") is True, result
    rules = _saved_rules(captured)
    assert rules and rules[0]["fieldId"] == "region_e701d6d3", rules


# =============================================================================
# Runner
# =============================================================================

async def main():
    print("=" * 60)
    print("Tests: component CRUD fixes")
    print("=" * 60)

    results: list[TestResult] = []
    tests = [
        # types_list.mcp_creatable
        test_creatable_true_for_technical_type,
        test_creatable_false_for_ui_only_type,
        # legend_position normalization
        test_legend_position_short_words_normalized,
        test_legend_position_enum_passthrough,
        test_legend_position_invalid_still_warns,
        # field_sort_set
        test_invalid_order_rejected,
        test_none_order_still_clears,
        test_empty_order_still_clears,
        test_valid_order_applies,
        # conditional_rule_add field resolution
        test_unknown_field_rejected,
        test_resolve_by_name,
        test_resolve_by_alias,
        test_raw_field_id_passthrough,
    ]

    print(f"\nRunning {len(tests)} tests...\n")
    for test_func in tests:
        await test_func(results)

    passed = sum(1 for r in results if r.passed)
    failed = sum(1 for r in results if not r.passed)
    total = len(results)

    print(f"\n{'=' * 60}")
    print(f"Results: {passed}/{total} passed, {failed} failed")

    if failed:
        print("\nFailed tests:")
        for r in results:
            if not r.passed:
                print(f"  ❌ {r.name}: {r.message}")
        sys.exit(1)
    else:
        print("All tests passed!")
        sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())
