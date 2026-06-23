"""slugs_list search mode.

search mode в _list_slugs(search='color') возвращает только
матчинг slugs. Можно комбинировать с component_type:
search='color' + component_type='HsBarAMchartsChart' → пересечение
(color-related slugs применимые к barChart).

Через MCP API доступно как slug_category='search:color' — переиспользуем
существующий параметр slug_category с префиксом search:
(без расширения wrapper surface).

Run:
    python -m app.tests.test_slugs_search
"""
import sys

from app.tools.component_crud import _list_slugs


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
    section("Search 'color' — все slugs со словом color/Color")
    result = _list_slugs(search="color")
    check("success=True", result.get("success") is True)
    check("count > 5 (есть много color slugs)",
          result.get("count", 0) > 5,
          detail=f"count={result.get('count')}")
    slugs = result.get("slugs", {})
    check("outline.color найден", "outline.color" in slugs)
    check("bgColor найден", "bgColor" in slugs)
    check("summColor найден", "summColor" in slugs)

    section("Search case-insensitive")
    result_upper = _list_slugs(search="COLOR")
    result_lower = _list_slugs(search="color")
    check("UPPER и lower возвращают одно и то же",
          result_upper["count"] == result_lower["count"],
          detail=f"UPPER={result_upper['count']} lower={result_lower['count']}")

    section("Search 'donut' — должен найти только один slug")
    result = _list_slugs(search="donut")
    check("count=1 (showDonut)",
          result.get("count") == 1, detail=str(result.get("slugs", {}).keys()))
    check("showDonut в результате",
          "showDonut" in result.get("slugs", {}))

    section("Search 'nonexistent' → 0 matches + hint")
    result = _list_slugs(search="zzz_nonexistent_xyz")
    check("count=0", result.get("count") == 0)
    check("hint о No matches",
          "No matches" in result.get("hint", ""),
          detail=str(result.get("hint")))

    section("Search + component_type — пересечение")
    # 'expand' slugs (expandH/V) применимы к bar/line/area/pie/stock
    result = _list_slugs(component_type="HsBarAMchartsChart", search="expand")
    check("expand найден на BarChart",
          result.get("count", 0) >= 2,
          detail=f"count={result.get('count')}")
    check("expandH в результате",
          "expandH" in result.get("slugs", {}))

    # На table — expand НЕ применим (не в applies_to)
    result = _list_slugs(component_type="HsTableReactabularChart", search="expand")
    check("expand НЕ применим к Table → count=0",
          result.get("count") == 0,
          detail=str(result.get("slugs", {}).keys()))

    section("Search 'subtitle' — top-level slug на 11 типах")
    result = _list_slugs(search="subtitle")
    check("subtitle найден", "subtitle" in result.get("slugs", {}))

    section("list_slugs без search возвращает прежние режимы")
    # Mode 1: category
    result = _list_slugs(category="legend")
    check("category='legend' возвращает legend.* slugs",
          result.get("count", 0) > 0
          and all(s.startswith("legend.") for s in result.get("slugs", {})),
          detail=str(list(result.get("slugs", {}).keys())[:3]))

    # Mode 2: component_type
    result = _list_slugs(component_type="HsBarAMchartsChart")
    check("component_type без search возвращает всю schema (без drill-down)",
          result.get("total_slugs", 0) > 50)

    # Mode 3: summary
    result = _list_slugs()
    check("default mode → category summary",
          "categories" in result and result.get("total", 0) > 100,
          detail=f"total={result.get('total')}")

    section("Sanity: search не ломает other modes если не задан")
    result = _list_slugs(search=None)
    check("search=None → default summary",
          "categories" in result and "search" not in result)

    print(f"\n===\nResult: {ok} OK, {fail} FAIL")
    sys.exit(0 if fail == 0 else 1)


if __name__ == "__main__":
    main()
