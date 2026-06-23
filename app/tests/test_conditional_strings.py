"""conditional formatting для строк.

Сценарий:
  component_styling(action='conditional_rule_add', report_id=N,
    component_idx=I, config_overrides={
      'field':'status', 'operator':'=', 'value':'FAIL',
      'background':'#f44336'})

Операторы `=` и `~` принимают string без coerce (фронт сравнивает
строки напрямую без числового приведения для `=`). Числовые операторы
(>, <, ...) по-прежнему требуют числовое значение.

Run:
    python -m app.tests.test_conditional_strings
"""
import asyncio
import sys

from app.tools.component_operations import _conditional_rule_add


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

    def setup_report_with_field(self, report_id, comp_idx, field_name):
        self.responses[("reports", "get", report_id)] = {
            "status": 200,
            "data": [{
                "ID": report_id,
                "grid": {
                    "components": {
                        str(comp_idx): {
                            "type": "HsTableReactabularChart",
                            "config": {
                                "rules": [],
                                "axes": [{
                                    "type": "values",
                                    "fields": [{"name": field_name, "id": f"{field_name}_xyz"}]
                                }],
                            },
                        }
                    }
                },
            }],
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


def main() -> None:
    section("оператор '=' принимает строку (статус FAIL)")
    client = FakeClient()
    client.setup_report_with_field(1, 0, "status")
    result = run(_conditional_rule_add(client, 1, 0, {
        "field": "status", "operator": "=", "value": "FAIL",
        "background": "#f44336",
    }))
    check("success=True (строка принята без coerce)",
          result.get("success") is True, detail=str(result)[:200])

    section("оператор '~' (contains) для подстроки")
    client = FakeClient()
    client.setup_report_with_field(1, 0, "name")
    result = run(_conditional_rule_add(client, 1, 0, {
        "field": "name", "operator": "~", "value": "критич",
        "background": "#ff0000",
    }))
    check("'~' принят как contains",
          result.get("success") is True, detail=str(result)[:200])

    section("alias 'contains' = '~'")
    client = FakeClient()
    client.setup_report_with_field(1, 0, "name")
    result = run(_conditional_rule_add(client, 1, 0, {
        "field": "name", "operator": "contains", "value": "test",
    }))
    check("'contains' принят (мапится на '~')",
          result.get("success") is True, detail=str(result)[:200])

    section("numeric операторы работают на float")
    client = FakeClient()
    client.setup_report_with_field(1, 0, "amount")
    result = run(_conditional_rule_add(client, 1, 0, {
        "field": "amount", "operator": ">", "value": 1000,
    }))
    check("'>' c numeric value работает",
          result.get("success") is True)

    section("numeric оператор + string value → ошибка с подсказкой")
    client = FakeClient()
    client.setup_report_with_field(1, 0, "amount")
    result = run(_conditional_rule_add(client, 1, 0, {
        "field": "amount", "operator": ">", "value": "not_a_number",
    }))
    check("'>' + строка → error",
          result.get("success") is False and "cannot be converted" in result.get("error", ""),
          detail=str(result))
    check("error предлагает использовать =/~",
          "'='" in result.get("error", "") or "~" in result.get("error", ""),
          detail=str(result.get("error")))

    section("'!=' → explicit error (фронт не поддерживает)")
    client = FakeClient()
    client.setup_report_with_field(1, 0, "status")
    result = run(_conditional_rule_add(client, 1, 0, {
        "field": "status", "operator": "!=", "value": "PASS",
    }))
    # error-конверт с явным success:False (консистентность конвертов)
    check("'!=' → error",
          result.get("success") is False and "not supported" in result.get("error", ""),
          detail=str(result))
    check("error упоминает workaround (дублировать правило)",
          "дублировать" in result.get("error", "").lower()
          or "правило" in result.get("error", ""),
          detail=str(result.get("error")))

    section("'regex' / 'starts_with' → explicit error")
    for bad_op in ["regex", "starts_with", "ends_with", "in"]:
        client = FakeClient()
        client.setup_report_with_field(1, 0, "status")
        result = run(_conditional_rule_add(client, 1, 0, {
            "field": "status", "operator": bad_op, "value": "X",
        }))
        check(f"'{bad_op}' → error",
              result.get("success") is False and "not supported" in result.get("error", ""),
              detail=str(result)[:150])

    section("alias 'eq' тоже работает для строки")
    client = FakeClient()
    client.setup_report_with_field(1, 0, "status")
    result = run(_conditional_rule_add(client, 1, 0, {
        "field": "status", "operator": "eq", "value": "WARN",
    }))
    check("'eq' alias принят с string",
          result.get("success") is True)

    section("unknown оператор → error с подсказкой")
    client = FakeClient()
    client.setup_report_with_field(1, 0, "status")
    result = run(_conditional_rule_add(client, 1, 0, {
        "field": "status", "operator": "weirdop", "value": "X",
    }))
    check("'weirdop' → error",
          result.get("success") is False
          and "Unknown operator" in result.get("error", ""),
          detail=str(result))

    print(f"\n===\nResult: {ok} OK, {fail} FAIL")
    sys.exit(0 if fail == 0 else 1)


if __name__ == "__main__":
    main()
