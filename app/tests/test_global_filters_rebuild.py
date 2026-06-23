"""_rebuild_global_filters — единый rebuild по живым aliases.

_rebuild_global_filters(report) — pure function:
  1. собирает живые aliases с global=True со всех компонентов
  2. сохраняет существующие записи для живых
  3. удаляет dead-keys

Покрывает изменение alias, bulk-обновление через dataset.field_aliases
и mismatch между component-fields и globalFilters.

Run:
    python -m app.tests.test_global_filters_rebuild
"""
import asyncio
import sys

from app.tools.component_filters import (
    _rebuild_global_filters,
    _filter_field_remove,
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


def make_report(components_filters: dict):
    """Make report with given {idx: [(name, alias, global)]} filter fields."""
    components = {}
    for idx, fields in components_filters.items():
        components[str(idx)] = {
            "type": "HsFilterControlPanel",
            "config": {
                "axes": [{
                    "type": "filters",
                    "fields": [
                        {"name": n, "alias": a, "global": g}
                        for n, a, g in fields
                    ],
                }],
            },
        }
    return {
        "ID": 1, "grid": {"components": components},
        "globalFilters": {},
    }


def main() -> None:
    section("_rebuild_global_filters: пустой отчёт")
    report = {"grid": {"components": {}}, "globalFilters": {}}
    result = _rebuild_global_filters(report)
    check("пустой → пустой globalFilters", result == {}, detail=str(result))

    section("_rebuild_global_filters: один компонент, один alias")
    report = make_report({0: [("product", "Категория", True)]})
    _rebuild_global_filters(report)
    check("создан ключ 'Категория'", "Категория" in report["globalFilters"])
    check("дефолтные настройки",
          report["globalFilters"]["Категория"]["enabled"] is True)
    check("selected=[]", report["globalFilters"]["Категория"]["selected"] == [])

    section("_rebuild_global_filters: dead-keys удаляются")
    report = make_report({0: [("product", "Категория", True)]})
    # Висит мёртвый ключ — поле было удалено руками или alias изменён
    report["globalFilters"] = {
        "Категория": {"enabled": True, "filterMode": "by value", "selected": ["A"], "sourceValues": {}},
        "Регион_DEAD": {"enabled": True, "filterMode": "by value", "selected": [], "sourceValues": {}},
        "year_DEAD": {"enabled": True, "filterMode": "by value", "selected": [], "sourceValues": {}},
    }
    _rebuild_global_filters(report)
    check("живой 'Категория' сохранён",
          "Категория" in report["globalFilters"])
    check("dead 'Регион_DEAD' удалён",
          "Регион_DEAD" not in report["globalFilters"])
    check("dead 'year_DEAD' удалён",
          "year_DEAD" not in report["globalFilters"])

    section("_rebuild_global_filters: существующие настройки сохраняются")
    report = make_report({0: [("product", "Категория", True)]})
    report["globalFilters"] = {
        "Категория": {
            "enabled": True, "filterMode": "by value",
            "selected": ["A", "B"],  # юзер уже выбрал
            "sourceValues": {"foo": "bar"},
        },
    }
    _rebuild_global_filters(report)
    check("selected=['A','B'] сохранены",
          report["globalFilters"]["Категория"]["selected"] == ["A", "B"])
    check("sourceValues сохранены",
          report["globalFilters"]["Категория"]["sourceValues"] == {"foo": "bar"})

    section("_rebuild_global_filters: global=False игнорируются")
    report = make_report({
        0: [
            ("product", "Категория", True),     # global → попадёт
            ("region",  "Регион",    False),    # local → НЕ попадёт
        ],
    })
    _rebuild_global_filters(report)
    check("global=True попал в globalFilters",
          "Категория" in report["globalFilters"])
    check("global=False НЕ попал",
          "Регион" not in report["globalFilters"])

    section("_rebuild_global_filters: малформированные структуры — графейсли")
    report = {
        "grid": {
            "components": {
                "0": "string_not_dict",         # malformed
                "1": {"config": "not a dict"},  # malformed config
                "2": {"config": {"axes": "not a list"}},
                "3": {  # валидный
                    "config": {"axes": [
                        {"type": "filters", "fields": [
                            {"name": "ok", "alias": "ОК", "global": True}
                        ]},
                    ]},
                },
            },
        },
        "globalFilters": {},
    }
    _rebuild_global_filters(report)
    check("malformed компоненты пропущены, валидный учтён",
          "ОК" in report["globalFilters"], detail=str(report["globalFilters"]))

    section("_filter_field_remove: использует rebuild END-TO-END")
    client = FakeClient()
    report = make_report({
        0: [("product", "Категория", True)],
        1: [("product", "Категория", True)],  # тот же alias на другом компоненте
    })
    report["globalFilters"] = {
        "Категория": {"enabled": True, "filterMode": "by value", "selected": [], "sourceValues": {}},
    }
    client.setup_report(1, report)
    result = run(_filter_field_remove(
        client, report_id=1, component_idx=0, field_name="product",
    ))
    check("remove успешен", result.get("success") is True,
          detail=str(result)[:120])
    saved_report = client.last_saved[0]
    check("'Категория' СОХРАНЁН (другой компонент использует)",
          "Категория" in saved_report["globalFilters"],
          detail=str(saved_report["globalFilters"]))
    check("global_filter_removed=False",
          result.get("global_filter_removed") is False)

    section("_filter_field_remove: alias удалён когда нигде не используется")
    client = FakeClient()
    report = make_report({
        0: [("product", "Категория", True)],
        1: [("year", "Год", True)],  # другой alias
    })
    report["globalFilters"] = {
        "Категория": {"enabled": True, "filterMode": "by value", "selected": [], "sourceValues": {}},
        "Год": {"enabled": True, "filterMode": "by value", "selected": [], "sourceValues": {}},
    }
    client.setup_report(1, report)
    result = run(_filter_field_remove(
        client, report_id=1, component_idx=0, field_name="product",
    ))
    saved_report = client.last_saved[0]
    check("'Категория' удалена (никто больше не использует)",
          "Категория" not in saved_report["globalFilters"])
    check("'Год' сохранена (живая)",
          "Год" in saved_report["globalFilters"])
    check("global_filter_removed=True",
          result.get("global_filter_removed") is True)

    print(f"\n===\nResult: {ok} OK, {fail} FAIL")
    sys.exit(0 if fail == 0 else 1)


if __name__ == "__main__":
    main()
