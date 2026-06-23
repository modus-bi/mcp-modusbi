"""report_template scaffold вызывает filters_grid_layout
для filter-row.

После _add_multiple_components scaffold вызывает _filters_grid_layout
для filter-индексов с y=0, и фильтры распределяются равномерно по
ВСЕМ 6 breakpoints используя BREAKPOINT_COLS.

Run:
    python -m app.tests.test_scaffold_filters_grid
"""
import asyncio
import sys

from app.tools.report_template import _scaffold_template, TEMPLATES


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


class _FakeInstance:
    name = "test_instance"


class FakeClient:
    def __init__(self):
        self.created_id = 9999
        self.saved_grids: list[dict] = []
        # state: components stored as dict {idx: comp}
        self._state = {
            "ID": self.created_id,
            "name": "test",
            "grid": {"components": {}, "layouts": {}},
        }
        self.instance = _FakeInstance()

    async def api_call(self, entity, action, object_id=None, **kwargs):
        # report.create — generate id
        if entity == "reports" and action == "create":
            return {"status": 200, "data": [{"ID": self.created_id, "name": "test"}]}
        # report.get — return current state
        if entity == "reports" and action == "get":
            return {"status": 200, "data": [self._state]}
        # report.update — capture and merge
        if entity == "reports" and action == "update":
            data = kwargs.get("data")
            if isinstance(data, list) and data:
                # Merge incoming grid into state
                incoming = data[0]
                self._state.update(incoming)
                self.saved_grids.append(incoming.get("grid", {}))
            return {"status": 200, "data": [{}]}
        # datasets.get — for fetch_dataset_alias_map
        if entity == "datasets" and action == "get":
            return {"status": 200, "data": [{
                "ID": object_id, "fields": [
                    {"name": "value", "alias": "Значение"},
                ],
            }]}
        return {"status": 200, "data": [{}]}


def run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


def main() -> None:
    section("scaffold kpi_dashboard (3 фильтра в первой строке)")
    client = FakeClient()
    result = run(_scaffold_template(
        client, template="kpi_dashboard",
        dataset_id=5, name="Test KPI", group_id=3,
    ))
    check("success=True", result.get("success") is True,
          detail=str(result)[:200])
    check("есть components в response",
          "components" in result and len(result["components"]) > 0)

    # Проверим что в финальном saved grid фильтры распределены по 6 breakpoints
    if client.saved_grids:
        last = client.saved_grids[-1]
        layouts = last.get("layouts", {})
        breakpoints_with_layouts = list(layouts.keys())
        check("есть все 6 breakpoints (hd/lg/md/sm/xs/xxs)",
              all(b in breakpoints_with_layouts for b in
                  ["hd", "lg", "md", "sm", "xs", "xxs"]),
              detail=f"got {breakpoints_with_layouts}")

        # Проверим в hd breakpoint что 3 filter-индексов имеют разные x
        hd = layouts.get("hd", [])
        filter_indices = [
            i for i, c in enumerate(TEMPLATES["kpi_dashboard"]["components"])
            if c["type"] == "HsFilterControlPanel"
        ]
        # Найти entries для filter-indices
        filter_entries_hd = [e for e in hd if str(e.get("i")) in {str(i) for i in filter_indices}]
        check(f"в hd есть {len(filter_indices)} filter entries",
              len(filter_entries_hd) == len(filter_indices),
              detail=f"got {len(filter_entries_hd)} for indices {filter_indices}")

        # hd: 60 cols / 3 = 20 каждый
        if filter_entries_hd:
            widths = sorted([e.get("w") for e in filter_entries_hd])
            check("hd: фильтры одинаковой ширины (60/3=20)",
                  all(w == 20 for w in widths),
                  detail=f"widths={widths}")
            xs = sorted([e.get("x") for e in filter_entries_hd])
            check("hd: x={0, 20, 40}",
                  xs == [0, 20, 40], detail=f"xs={xs}")

        # md: 40 cols / 3 = 13 (с остатком 1, warning)
        md = layouts.get("md", [])
        filter_entries_md = [e for e in md if str(e.get("i")) in {str(i) for i in filter_indices}]
        if filter_entries_md:
            widths = sorted([e.get("w") for e in filter_entries_md])
            check("md: 3 фильтра w=13 (40/3 floor)",
                  all(w == 13 for w in widths),
                  detail=f"md widths={widths}")

    section("scaffold ranking (2 фильтра)")
    client = FakeClient()
    result = run(_scaffold_template(
        client, template="ranking",
        dataset_id=5, name="Test Ranking", group_id=3,
    ))
    check("success=True", result.get("success") is True)
    if client.saved_grids:
        last = client.saved_grids[-1]
        layouts = last.get("layouts", {})
        hd = layouts.get("hd", [])
        # ranking: indices 0 и 1 — фильтры
        filter_entries_hd = [e for e in hd if str(e.get("i")) in {"0", "1"}]
        check("ranking: 2 фильтра в hd",
              len(filter_entries_hd) == 2)
        if filter_entries_hd:
            widths = sorted([e.get("w") for e in filter_entries_hd])
            check("ranking hd: w=30 (60/2)",
                  all(w == 30 for w in widths), detail=f"widths={widths}")
            xs = sorted([e.get("x") for e in filter_entries_hd])
            check("ranking hd: x={0, 30}",
                  xs == [0, 30], detail=f"xs={xs}")

    section("scaffold simple (1 фильтр) — НЕ вызывает grid_layout")
    client = FakeClient()
    result = run(_scaffold_template(
        client, template="simple",
        dataset_id=5, name="Test Simple", group_id=3,
    ))
    check("success=True (1 фильтр ОК)", result.get("success") is True)
    # При 1 фильтре grid_layout не вызывается (len > 1 check)
    # → проверим что layout_warnings отсутствует
    check("нет layout_warnings при 1 фильтре",
          "layout_warnings" not in result, detail=str(result.get("layout_warnings")))

    section("Backward-compat: NO data templates (если бы были без filters)")
    # Все templates имеют filters — пропускаем

    print(f"\n===\nResult: {ok} OK, {fail} FAIL")
    sys.exit(0 if fail == 0 else 1)


if __name__ == "__main__":
    main()
