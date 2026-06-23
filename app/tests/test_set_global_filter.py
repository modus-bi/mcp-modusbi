"""_set_global_filter принимает alias и пишет в globalFilters.

Фронт читает фильтр-state из `report.globalFilters[alias]`, поэтому alias
обязателен, чтобы фильтр применялся к другим компонентам.

При переданном alias пишем в `data.globalFilters[alias].selected`,
плюс для совместимости обновляем `cfg.selectedValue`.

Run:
    python -m app.tests.test_set_global_filter
"""
import asyncio
import sys

from app.tools.component_filters import _set_global_filter


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


def make_report(component_idx=0, alias="Регион"):
    return {
        "ID": 1,
        "grid": {
            "components": {
                str(component_idx): {
                    "type": "HsFilterControlPanel",
                    "config": {
                        "axes": [{
                            "type": "filters",
                            "fields": [
                                {"name": "region", "alias": alias, "global": True},
                            ],
                        }],
                        "selectedValue": [],
                    },
                },
            },
        },
        "globalFilters": {
            alias: {
                "enabled": True, "filterMode": "by value",
                "selected": [], "sourceValues": {},
            },
        },
    }


def main() -> None:
    section("alias передан → globalFilters[alias].selected обновляется")
    client = FakeClient()
    client.setup_report(1, make_report(0, "Регион"))
    result = run(_set_global_filter(
        client, report_id=1, component_idx=0,
        value_field="Москва,СПб", alias="Регион",
    ))
    check("success=True", result.get("success") is True, detail=str(result)[:120])
    check("global_filter_updated=True",
          result.get("global_filter_updated") is True)
    check("alias попал в response", result.get("alias") == "Регион")

    saved = client.last_saved[0]
    check("globalFilters['Регион'].selected == ['Москва','СПб']",
          saved["globalFilters"]["Регион"]["selected"] == ["Москва", "СПб"],
          detail=str(saved["globalFilters"]["Регион"]))
    check("filterMode='by value'",
          saved["globalFilters"]["Регион"]["filterMode"] == "by value")
    check("backward-compat: cfg.selectedValue тоже обновлён",
          saved["grid"]["components"]["0"]["config"]["selectedValue"]
          == ["Москва", "СПб"])

    section("alias НЕ передан → warning + только cfg.selectedValue")
    client = FakeClient()
    client.setup_report(1, make_report(0, "Регион"))
    result = run(_set_global_filter(
        client, report_id=1, component_idx=0,
        value_field="Москва", alias=None,
    ))
    check("success=True (backward-compat)", result.get("success") is True)
    check("global_filter_updated=False",
          result.get("global_filter_updated") is False)
    check("warning есть",
          "warnings" in result and len(result["warnings"]) == 1,
          detail=str(result.get("warnings")))
    check("warning упоминает alias",
          "alias" in result["warnings"][0].lower())

    saved = client.last_saved[0]
    check("globalFilters не тронут (selected пустой)",
          saved["globalFilters"]["Регион"]["selected"] == [],
          detail=str(saved["globalFilters"]["Регион"]))
    check("cfg.selectedValue обновлён",
          saved["grid"]["components"]["0"]["config"]["selectedValue"]
          == ["Москва"])

    section("alias не существует в globalFilters → error")
    client = FakeClient()
    client.setup_report(1, make_report(0, "Регион"))
    result = run(_set_global_filter(
        client, report_id=1, component_idx=0,
        value_field="X", alias="НесуществующийAlias",
    ))
    check("success=False", result.get("success") is False)
    check("error упоминает alias",
          "НесуществующийAlias" in result.get("error", ""),
          detail=str(result.get("error")))
    check("error показывает available aliases",
          "Регион" in result.get("error", ""))

    section("Пустое value_field → очистка selected")
    client = FakeClient()
    report = make_report(0, "Регион")
    report["globalFilters"]["Регион"]["selected"] = ["OldValue"]
    client.setup_report(1, report)
    result = run(_set_global_filter(
        client, report_id=1, component_idx=0,
        value_field="", alias="Регион",
    ))
    check("success=True", result.get("success") is True)
    saved = client.last_saved[0]
    check("globalFilters['Регион'].selected очищено",
          saved["globalFilters"]["Регион"]["selected"] == [],
          detail=str(saved["globalFilters"]["Регион"]["selected"]))

    section("Компонент не FilterControlPanel → error")
    client = FakeClient()
    report = make_report(0, "Регион")
    report["grid"]["components"]["0"]["type"] = "HsBarAMchartsChart"
    client.setup_report(1, report)
    result = run(_set_global_filter(
        client, report_id=1, component_idx=0, value_field="X", alias="Регион",
    ))
    check("success=False для non-filter компонента",
          result.get("success") is False)
    check("error упоминает component type",
          "HsBarAMchartsChart" in result.get("error", ""))

    print(f"\n===\nResult: {ok} OK, {fail} FAIL")
    sys.exit(0 if fail == 0 else 1)


if __name__ == "__main__":
    main()
