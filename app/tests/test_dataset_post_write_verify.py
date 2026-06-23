"""post-write verification после dataset_operations.update.

Сценарий:
  dataset_operations(update, dataset_id=N,
                     field_aliases={"nonexistent_field": {"alias": "TEST"}})
  → backend HTTP 200 + success=true, но изменение НЕ применилось.

MCP делает post-write get и сравнивает; при расхождении возвращает
error_response со списком not_applied полей и подсказкой.

Run:
    python -m app.tests.test_dataset_post_write_verify
"""
import asyncio
import sys

from app.tools.dataset_operations import _update_dataset


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
    """Мок client.api_call. Программируется через .responses.

    Учитывает что _update_dataset сначала делает get (для resolve current
    state), затем update, затем post-write get для verify."""

    def __init__(self):
        self.calls = []
        self.responses = {}

    def setup_get(self, dataset_id, fields, name="ds", query="SELECT 1"):
        self.responses[("datasets", "get", dataset_id)] = {
            "status": 200,
            "data": [{
                "ID": dataset_id, "name": name, "caption": "",
                "parentID": 1, "driverID": 1, "query": query,
                "fields": fields,
            }],
        }

    def setup_get_after_update(self, dataset_id, fields):
        """Меняет get response — для имитации post-write state."""
        self.responses[("datasets", "get", dataset_id)] = {
            "status": 200,
            "data": [{
                "ID": dataset_id, "name": "ds", "caption": "",
                "parentID": 1, "driverID": 1, "query": "SELECT 1",
                "fields": fields,
            }],
        }

    async def api_call(self, entity, action, object_id=None, **kwargs):
        self.calls.append((entity, action, object_id))
        return self.responses.get(
            (entity, action, object_id),
            {"status": 200, "data": [{}]},
        )


def run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


def main() -> None:
    section("Happy path: alias реально применился")
    client = FakeClient()
    client.setup_get(5, fields=[
        {"name": "region", "alias": "region", "type": "string", "ID": 1},
    ])
    # Update mock: после update следующий get вернёт обновлённый alias
    result_holder = []

    class HappyClient(FakeClient):
        async def api_call(self, entity, action, object_id=None, **kwargs):
            self.calls.append((entity, action, object_id))
            if action == "get" and len(result_holder) > 0:
                # post-write call: возвращаем applied state
                return {
                    "status": 200,
                    "data": [{
                        "ID": 5, "name": "ds", "caption": "",
                        "parentID": 1, "driverID": 1, "query": "SELECT 1",
                        "fields": [{"name": "region", "alias": "Регион"}],
                    }],
                }
            if action == "update":
                result_holder.append(True)
                return {"status": 200, "data": [{}]}
            return self.responses.get(
                (entity, action, object_id),
                {"status": 200, "data": [{}]},
            )

    client = HappyClient()
    client.setup_get(5, fields=[
        {"name": "region", "alias": "region", "type": "string", "ID": 1},
    ])
    result = run(_update_dataset(
        client, dataset_id=5, name=None, caption=None,
        datasource_id=None, query=None,
        rls=None, query_rls=None,
        field_aliases={"region": {"alias": "Регион"}},
    ))
    check("success=True когда alias реально применился",
          result.get("success") is True, detail=str(result)[:150])

    section("Silent no-op: backend OK, но field не существует")
    # Запрашиваем alias для несуществующего поля
    result_holder.clear()

    class SilentNoOpClient(FakeClient):
        async def api_call(self, entity, action, object_id=None, **kwargs):
            self.calls.append((entity, action, object_id))
            if action == "get":
                # Всегда возвращаем dataset с 0 полями
                return {
                    "status": 200,
                    "data": [{
                        "ID": 5, "name": "ds", "caption": "",
                        "parentID": 1, "driverID": 1, "query": "",
                        "fields": [],
                    }],
                }
            if action == "update":
                # Backend silently returns OK даже когда field не существует
                return {"status": 200, "data": [{}]}
            return {"status": 200, "data": [{}]}

    client = SilentNoOpClient()
    result = run(_update_dataset(
        client, dataset_id=5, name=None, caption=None,
        datasource_id=None, query=None, rls=None, query_rls=None,
        field_aliases={"nonexistent": {"alias": "TEST"}},
    ))
    check("success=False (verify поймал silent no-op)",
          result.get("success") is False, detail=str(result)[:200])
    check("error упоминает field_aliases",
          "field_aliases" in result.get("error", "").lower(),
          detail=str(result.get("error")))
    check("field_aliases_not_applied содержит nonexistent",
          any(n.get("name") == "nonexistent"
              for n in result.get("field_aliases_not_applied", [])))
    check("reason=field_not_in_dataset",
          any(n.get("reason") == "field_not_in_dataset"
              for n in result.get("field_aliases_not_applied", [])),
          detail=str(result.get("field_aliases_not_applied")))

    section("Silent no-op: field есть, но alias не применился")
    class StuckAliasClient(FakeClient):
        async def api_call(self, entity, action, object_id=None, **kwargs):
            self.calls.append((entity, action, object_id))
            if action == "get":
                return {
                    "status": 200,
                    "data": [{
                        "ID": 5, "name": "ds", "caption": "",
                        "parentID": 1, "driverID": 1, "query": "SELECT region",
                        "fields": [{"name": "region", "alias": "OLD_ALIAS"}],
                    }],
                }
            if action == "update":
                return {"status": 200, "data": [{}]}
            return {"status": 200, "data": [{}]}

    client = StuckAliasClient()
    result = run(_update_dataset(
        client, dataset_id=5, name=None, caption=None,
        datasource_id=None, query=None, rls=None, query_rls=None,
        field_aliases={"region": {"alias": "Регион"}},
    ))
    check("success=False (alias застрял на OLD_ALIAS)",
          result.get("success") is False, detail=str(result)[:200])
    check("reason=alias_unchanged_after_save",
          any(n.get("reason") == "alias_unchanged_after_save"
              for n in result.get("field_aliases_not_applied", [])),
          detail=str(result.get("field_aliases_not_applied")))
    check("actual=OLD_ALIAS в response",
          any(n.get("actual") == "OLD_ALIAS"
              for n in result.get("field_aliases_not_applied", [])))

    section("Verify падает gracefully — не ломает happy path")
    class BrokenVerifyClient(FakeClient):
        def __init__(self):
            super().__init__()
            self.call_count = 0

        async def api_call(self, entity, action, object_id=None, **kwargs):
            self.calls.append((entity, action, object_id))
            self.call_count += 1
            if self.call_count == 1 and action == "get":
                # Первый get (initial fetch) — работает
                return {
                    "status": 200,
                    "data": [{
                        "ID": 5, "name": "ds", "caption": "",
                        "parentID": 1, "driverID": 1, "query": "",
                        "fields": [{"name": "region", "alias": "old", "ID": 1}],
                    }],
                }
            if action == "update":
                return {"status": 200, "data": [{}]}
            if action == "get":
                # Post-write get — сломан
                raise RuntimeError("network glitch")
            return {"status": 200, "data": [{}]}

    client = BrokenVerifyClient()
    result = run(_update_dataset(
        client, dataset_id=5, name=None, caption=None,
        datasource_id=None, query=None, rls=None, query_rls=None,
        field_aliases={"region": {"alias": "Регион"}},
    ))
    check("verify exception → success=True (graceful, не ломает)",
          result.get("success") is True, detail=str(result)[:200])

    section("Без field_aliases verify не запускается")
    client = FakeClient()
    client.setup_get(5, fields=[])
    result = run(_update_dataset(
        client, dataset_id=5, name="new_name", caption=None,
        datasource_id=None, query=None, rls=None, query_rls=None,
        field_aliases=None,
    ))
    # call_count: 1 initial get + 1 update = 2 (без verify)
    get_calls = sum(1 for c in client.calls if c[1] == "get")
    check("без field_aliases — нет post-write get",
          get_calls == 1, detail=f"got {get_calls} get calls")

    print(f"\n===\nResult: {ok} OK, {fail} FAIL")
    sys.exit(0 if fail == 0 else 1)


if __name__ == "__main__":
    main()
