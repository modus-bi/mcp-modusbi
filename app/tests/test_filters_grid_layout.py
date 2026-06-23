"""_filters_grid_layout — равномерное распределение фильтров.

component_filters(action='filters_grid_layout',
config_overrides={component_indices:[...], cols:4}) распределяет фильтры
по сетке автоматически: для «4 фильтра в ряд» считает w=15 (60/4) для hd,
w=12 (48/4) для lg и т.д. по всем 6 breakpoints.

Run:
    python -m app.tests.test_filters_grid_layout
"""
import asyncio
import sys

from app.tools.component_filters import _filters_grid_layout


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


class FakeClient:
    def __init__(self):
        self.responses = {}
        self.last_saved = None

    def setup_report(self, report_id, data):
        self.responses[("reports", "get", report_id)] = {
            "status": 200, "data": [data]
        }

    async def api_call(self, entity, action, object_id=None, **kwargs):
        if action == "update":
            self.last_saved = kwargs.get("data")
            return {"status": 200, "data": [{}]}
        return self.responses.get(
            (entity, action, object_id), {"status": 200, "data": [{}]}
        )


def run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


def make_report(indices):
    """Отчёт с N FilterControlPanel + пустые layouts."""
    components = {
        str(i): {"type": "HsFilterControlPanel", "config": {"axes": []}}
        for i in indices
    }
    return {"ID": 1, "grid": {"components": components, "layouts": {}}}


def main() -> None:
    section("4 фильтра в 1 ряд — hd: 60 / 4 = 15 каждый")
    client = FakeClient()
    client.setup_report(1, make_report([14, 15, 16, 17]))
    result = run(_filters_grid_layout(
        client, report_id=1,
        component_indices=[14, 15, 16, 17],
        cols=4,
    ))
    check("success=True", result.get("success") is True,
          detail=str(result)[:120])

    saved = client.last_saved[0]
    hd_layout = saved["grid"]["layouts"]["hd"]
    hd_by_i = {str(e["i"]): e for e in hd_layout}
    check("hd: i=14 → x=0, w=15",
          hd_by_i["14"]["x"] == 0 and hd_by_i["14"]["w"] == 15,
          detail=str(hd_by_i["14"]))
    check("hd: i=15 → x=15, w=15",
          hd_by_i["15"]["x"] == 15 and hd_by_i["15"]["w"] == 15,
          detail=str(hd_by_i["15"]))
    check("hd: i=16 → x=30, w=15",
          hd_by_i["16"]["x"] == 30 and hd_by_i["16"]["w"] == 15)
    check("hd: i=17 → x=45, w=15",
          hd_by_i["17"]["x"] == 45 and hd_by_i["17"]["w"] == 15)
    check("hd: все y=0", all(hd_by_i[str(i)]["y"] == 0 for i in [14, 15, 16, 17]))
    check("hd: все h=3 (default filter height)",
          all(hd_by_i[str(i)]["h"] == 3 for i in [14, 15, 16, 17]))
    check("hd: все modified=True",
          all(hd_by_i[str(i)]["modified"] is True for i in [14, 15, 16, 17]))

    # BREAKPOINT_COLS = {hd:60, lg:48, md:40, sm:30, xs:28, xxs:20}
    section("lg: 48/4=12, md: 40/4=10, sm: 30/4=7, xs: 28/4=7, xxs: 20/4=5")
    lg_layout = saved["grid"]["layouts"]["lg"]
    lg_by_i = {str(e["i"]): e for e in lg_layout}
    check("lg: w=12 для каждого",
          all(lg_by_i[str(i)]["w"] == 12 for i in [14, 15, 16, 17]))

    md_layout = saved["grid"]["layouts"]["md"]
    md_by_i = {str(e["i"]): e for e in md_layout}
    check("md: w=10 для каждого",
          all(md_by_i[str(i)]["w"] == 10 for i in [14, 15, 16, 17]))

    sm_layout = saved["grid"]["layouts"]["sm"]
    sm_by_i = {str(e["i"]): e for e in sm_layout}
    check("sm: w=7 для каждого (30 // 4 = 7, остаток 2)",
          all(sm_by_i[str(i)]["w"] == 7 for i in [14, 15, 16, 17]))

    section("8 фильтров в 2×4 grid — hd")
    client = FakeClient()
    client.setup_report(1, make_report(list(range(10, 18))))
    result = run(_filters_grid_layout(
        client, report_id=1,
        component_indices=list(range(10, 18)),
        cols=4, rows=2,
    ))
    check("8 в 2×4 success", result.get("success") is True)
    saved = client.last_saved[0]
    hd_by_i = {str(e["i"]): e for e in saved["grid"]["layouts"]["hd"]}
    # Первый ряд (i=10..13): y=0
    check("первый ряд: i=10..13 → y=0",
          all(hd_by_i[str(i)]["y"] == 0 for i in [10, 11, 12, 13]),
          detail=str([hd_by_i[str(i)]["y"] for i in [10, 11, 12, 13]]))
    # Второй ряд (i=14..17): y=3 (h=3)
    check("второй ряд: i=14..17 → y=3",
          all(hd_by_i[str(i)]["y"] == 3 for i in [14, 15, 16, 17]),
          detail=str([hd_by_i[str(i)]["y"] for i in [14, 15, 16, 17]]))
    # x в каждом ряду: 0, 15, 30, 45
    check("второй ряд: x={0,15,30,45}",
          [hd_by_i[str(i)]["x"] for i in [14, 15, 16, 17]] == [0, 15, 30, 45])

    section("y_start смещает начало сетки")
    client = FakeClient()
    client.setup_report(1, make_report([14, 15]))
    result = run(_filters_grid_layout(
        client, report_id=1,
        component_indices=[14, 15],
        cols=2, y_start=10,
    ))
    saved = client.last_saved[0]
    hd_by_i = {str(e["i"]): e for e in saved["grid"]["layouts"]["hd"]}
    check("y_start=10 → y=10 для всех",
          all(hd_by_i[str(i)]["y"] == 10 for i in [14, 15]))

    section("Existing layout entries обновляются in-place")
    report = make_report([14, 15])
    # Pre-existing entry с другими координатами
    report["grid"]["layouts"]["hd"] = [
        {"i": "14", "x": 99, "y": 99, "w": 99, "h": 99, "modified": False},
        {"i": "15", "x": 88, "y": 88, "w": 88, "h": 88, "modified": False},
    ]
    client = FakeClient()
    client.setup_report(1, report)
    result = run(_filters_grid_layout(
        client, report_id=1, component_indices=[14, 15], cols=2,
    ))
    saved = client.last_saved[0]
    hd_by_i = {str(e["i"]): e for e in saved["grid"]["layouts"]["hd"]}
    check("existing entry i=14 обновлён x=0, w=30",
          hd_by_i["14"]["x"] == 0 and hd_by_i["14"]["w"] == 30,
          detail=str(hd_by_i["14"]))
    check("existing entry i=15 обновлён x=30",
          hd_by_i["15"]["x"] == 30)
    check("modified=True проставлен",
          hd_by_i["14"]["modified"] is True)

    section("Валидация: пустой component_indices → error")
    client = FakeClient()
    result = run(_filters_grid_layout(
        client, report_id=1, component_indices=[], cols=4,
    ))
    check("empty indices → success=False",
          result.get("success") is False, detail=str(result))

    section("Валидация: cols/rows < 1 → error")
    result = run(_filters_grid_layout(
        client, report_id=1, component_indices=[14], cols=0,
    ))
    check("cols=0 → error", result.get("success") is False)

    result = run(_filters_grid_layout(
        client, report_id=1, component_indices=[14], cols=1, rows=0,
    ))
    check("rows=0 → error", result.get("success") is False)

    section("Валидация: слишком много indices для cols×rows")
    client = FakeClient()
    client.setup_report(1, make_report([10, 11, 12, 13, 14]))
    result = run(_filters_grid_layout(
        client, report_id=1,
        component_indices=[10, 11, 12, 13, 14],  # 5 indices
        cols=2, rows=2,  # only 4 slots
    ))
    check("5 indices в 2×2 → error",
          result.get("success") is False,
          detail=str(result))
    check("error упоминает 4 slots",
          "4" in result.get("error", ""))

    section("Валидация: indices, которых нет в отчёте")
    client = FakeClient()
    client.setup_report(1, make_report([14, 15]))
    result = run(_filters_grid_layout(
        client, report_id=1, component_indices=[14, 99], cols=2,
    ))
    check("99 не существует → error",
          result.get("success") is False)
    check("error упоминает missing 99",
          "99" in result.get("error", ""))

    section("wrapper component_filters пробрасывает config_overrides")
    # Проверяет, что config_overrides реально доходит до
    # _filters_grid_layout через MCP dispatcher.
    from app.server import mcp
    import inspect
    sig = inspect.signature(mcp._tool_manager._tools["component_filters"].fn)
    check("component_filters wrapper принимает config_overrides",
          "config_overrides" in sig.parameters,
          detail=f"params: {list(sig.parameters.keys())[:8]}")

    # END-TO-END через dispatcher
    from app.tools.component_operations import component_operations
    client = FakeClient()
    client.setup_report(1, make_report([14, 15]))
    result = run(component_operations(
        client=client, action="filters_grid_layout",
        report_id=1,
        config_overrides={"component_indices": [14, 15], "cols": 2},
    ))
    check("end-to-end через dispatcher: success=True",
          result.get("success") is True,
          detail=str(result)[:200])
    saved = client.last_saved[0]
    hd_by_i = {str(e["i"]): e for e in saved["grid"]["layouts"]["hd"]}
    check("end-to-end: i=14 → x=0, w=30",
          hd_by_i["14"]["x"] == 0 and hd_by_i["14"]["w"] == 30)
    check("end-to-end: i=15 → x=30, w=30",
          hd_by_i["15"]["x"] == 30 and hd_by_i["15"]["w"] == 30)

    section("единый BREAKPOINT_COLS")
    # BREAKPOINT_COLS — единый источник для component_crud и component_filters.
    from app.tools.component_crud import BREAKPOINT_COLS
    from app.tools.component_filters import BREAKPOINT_COLS as cf_bp
    check("BREAKPOINT_COLS импортируется из component_crud",
          BREAKPOINT_COLS is cf_bp,
          detail=f"crud={BREAKPOINT_COLS}, filters={cf_bp}")
    check("md=40", BREAKPOINT_COLS["md"] == 40)
    check("sm=30", BREAKPOINT_COLS["sm"] == 30)

    print(f"\n===\nResult: {ok} OK, {fail} FAIL")
    sys.exit(0 if fail == 0 else 1)


if __name__ == "__main__":
    main()
