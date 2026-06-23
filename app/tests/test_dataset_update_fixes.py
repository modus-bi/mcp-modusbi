"""dataset_operations.update: query_rls, datasource_id unpack, query verify.

1. RLS filter: payload sends snake_case ``query_rls`` (the key backend
   reads), not camelCase ``queryRls``.

2. update(datasource_id=...) uses the canonical 3-tuple
   ``_get_driver_id_from_datasource`` from query_execute, returning an
   error envelope rather than raising ValueError.

3. update(query) on a bound dataset verifies via a post-write get +
   query comparison; a mismatch yields success=False + query_not_applied
   + hint (delete + dataset_create_from_sql).

Run:
    python -m app.tests.test_dataset_update_fixes
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
    """Мок client.api_call для _update_dataset.

    Учитывает последовательность вызовов: initial get → (datasources list
    при смене datasource_id) → update → post-write get для verify.
    Update-payload'ы складывает в .update_payloads для инспекции."""

    def __init__(self, dataset=None, datasources=None):
        self.calls = []
        self.update_payloads = []
        self.dataset = dataset or {
            "ID": 5, "name": "ds", "caption": "",
            "parentID": 1, "driverID": 20, "query": "SELECT 1",
            "fields": [],
        }
        self.datasources = datasources or []

    async def api_call(self, entity, action, object_id=None, **kwargs):
        self.calls.append((entity, action, object_id))
        if entity == "datasets" and action == "get":
            return {"status": 200, "data": [dict(self.dataset)]}
        if entity == "datasets" and action == "update":
            self.update_payloads.append(kwargs.get("data"))
            return {"status": 200, "data": [{}]}
        if entity == "datasources" and action == "list":
            return {"status": 200, "data": self.datasources}
        return {"status": 200, "data": [{}]}


def run(coro):
    return asyncio.run(coro)


def main() -> None:
    section("Fix 8: payload-ключ query_rls (не queryRls)")
    client = FakeClient()
    result = run(_update_dataset(
        client, dataset_id=5, name=None, caption=None,
        datasource_id=None, query=None,
        rls=True, query_rls="user_id = :current_user_id",
        field_aliases=None,
    ))
    check("update прошёл success=True",
          result.get("success") is True, detail=str(result)[:150])
    check("update-вызов отправлен",
          len(client.update_payloads) == 1)
    payload = client.update_payloads[0][0] if client.update_payloads else {}
    check("в payload есть query_rls (snake_case, как ждёт backend)",
          payload.get("query_rls") == "user_id = :current_user_id",
          detail=str(payload)[:200])
    check("в payload НЕТ queryRls (camelCase backend не читает)",
          "queryRls" not in payload, detail=str(payload)[:200])
    check("changes содержит query_rls",
          "query_rls" in (result.get("changes") or {}))

    section("Fix 8: query_rls=None — ключ не добавляется")
    client = FakeClient()
    result = run(_update_dataset(
        client, dataset_id=5, name=None, caption="Новый caption",
        datasource_id=None, query=None, rls=None, query_rls=None,
        field_aliases=None,
    ))
    payload = client.update_payloads[0][0] if client.update_payloads else {}
    check("без query_rls в payload нет ни одного rls-ключа",
          "query_rls" not in payload and "queryRls" not in payload,
          detail=str(payload)[:200])

    section("Fix 7: смена datasource_id — 3-tuple unpack без ValueError")
    client = FakeClient(datasources=[
        {"ID": 1, "parentID": 20, "name": "pg_old"},
        {"ID": 2, "parentID": 50, "name": "ch_new"},
    ])
    try:
        result = run(_update_dataset(
            client, dataset_id=5, name=None, caption=None,
            datasource_id=2, query=None, rls=None, query_rls=None,
            field_aliases=None,
        ))
        check("ValueError не выброшен, success=True",
              result.get("success") is True, detail=str(result)[:200])
    except ValueError as e:
        result = {}
        check("ValueError не выброшен, success=True", False, detail=str(e))
    changes = result.get("changes") or {}
    check("changes.datasource_id old=1 new=2",
          changes.get("datasource_id") == {"old": 1, "new": 2},
          detail=str(changes))
    check("changes.driver_id new=50 (parentID нового datasource)",
          (changes.get("driver_id") or {}).get("new") == 50,
          detail=str(changes))
    payload = client.update_payloads[0][0] if client.update_payloads else {}
    check("payload: parentID=2 (connection), driverID=50 (driver type)",
          payload.get("parentID") == 2 and payload.get("driverID") == 50,
          detail=str(payload)[:200])

    section("Fix 7: datasource_id не найден — error-конверт, не исключение")
    client = FakeClient(datasources=[{"ID": 1, "parentID": 20}])
    result = run(_update_dataset(
        client, dataset_id=5, name=None, caption=None,
        datasource_id=999, query=None, rls=None, query_rls=None,
        field_aliases=None,
    ))
    check("success=False при несуществующем datasource",
          result.get("success") is False, detail=str(result)[:200])
    check("error упоминает datasource 999",
          "999" in result.get("error", ""), detail=str(result.get("error")))
    check("update НЕ отправлен (упали до записи)",
          len(client.update_payloads) == 0)

    section("Fix 6: query silent no-op → success=False")

    class StuckQueryClient(FakeClient):
        """Backend отвечает 200 на update, но query не меняется
        (типичный bound dataset)."""

        async def api_call(self, entity, action, object_id=None, **kwargs):
            self.calls.append((entity, action, object_id))
            if entity == "datasets" and action == "get":
                # И initial, и post-write get возвращают СТАРЫЙ query
                return {"status": 200, "data": [{
                    "ID": 5, "name": "ds", "caption": "",
                    "parentID": 1, "driverID": 20,
                    "query": "SELECT old_field FROM t",
                    "fields": [{"name": "old_field", "alias": ""}],
                }]}
            if entity == "datasets" and action == "update":
                self.update_payloads.append(kwargs.get("data"))
                return {"status": 200, "data": [{}]}
            return {"status": 200, "data": [{}]}

    client = StuckQueryClient()
    result = run(_update_dataset(
        client, dataset_id=5, name=None, caption=None,
        datasource_id=None, query="SELECT new_field FROM t",
        rls=None, query_rls=None,
        validate_query=False,  # изоляция от sql_query_validate
        field_aliases=None,
    ))
    check("success=False (verify поймал silent no-op)",
          result.get("success") is False, detail=str(result)[:200])
    na = result.get("query_not_applied") or {}
    check("reason=query_unchanged_after_save",
          na.get("reason") == "query_unchanged_after_save", detail=str(na))
    check("expected/actual в query_not_applied",
          "new_field" in na.get("expected", "")
          and "old_field" in na.get("actual", ""), detail=str(na))
    check("hint рекомендует dataset_create_from_sql",
          "dataset_create_from_sql" in result.get("hint", ""),
          detail=str(result.get("hint")))
    check("changes_attempted сохранён для диагностики",
          "query" in (result.get("changes_attempted") or {}),
          detail=str(result.get("changes_attempted")))

    section("Fix 6: query реально применился → success=True")

    class AppliedQueryClient(FakeClient):
        def __init__(self):
            super().__init__()
            self.updated = False

        async def api_call(self, entity, action, object_id=None, **kwargs):
            self.calls.append((entity, action, object_id))
            if entity == "datasets" and action == "get":
                q = ("SELECT new_field FROM t" if self.updated
                     else "SELECT old_field FROM t")
                return {"status": 200, "data": [{
                    "ID": 5, "name": "ds", "caption": "",
                    "parentID": 1, "driverID": 20, "query": q,
                    "fields": [],
                }]}
            if entity == "datasets" and action == "update":
                self.updated = True
                self.update_payloads.append(kwargs.get("data"))
                return {"status": 200, "data": [{}]}
            return {"status": 200, "data": [{}]}

    client = AppliedQueryClient()
    result = run(_update_dataset(
        client, dataset_id=5, name=None, caption=None,
        datasource_id=None, query="SELECT new_field FROM t",
        rls=None, query_rls=None,
        validate_query=False,
        field_aliases=None,
    ))
    check("success=True когда query реально применился",
          result.get("success") is True, detail=str(result)[:200])
    get_calls = sum(1 for c in client.calls if c[1] == "get")
    check("post-write get выполнен (2 get: initial + verify)",
          get_calls == 2, detail=f"got {get_calls} get calls")

    section("Fix 6: без смены query verify не запускается")
    client = FakeClient()
    result = run(_update_dataset(
        client, dataset_id=5, name=None, caption="Только caption",
        datasource_id=None, query=None, rls=None, query_rls=None,
        field_aliases=None,
    ))
    check("success=True", result.get("success") is True)
    get_calls = sum(1 for c in client.calls if c[1] == "get")
    check("caption-only update — нет post-write get",
          get_calls == 1, detail=f"got {get_calls} get calls")

    section("Fix 6: тот же query (no change) — verify не запускается")
    client = FakeClient()  # dataset.query == "SELECT 1"
    result = run(_update_dataset(
        client, dataset_id=5, name=None, caption=None,
        datasource_id=None, query="SELECT 1", rls=None, query_rls=None,
        validate_query=False,
        field_aliases=None,
    ))
    check("success=True", result.get("success") is True)
    get_calls = sum(1 for c in client.calls if c[1] == "get")
    check("query без изменений — нет post-write get",
          get_calls == 1, detail=f"got {get_calls} get calls")

    section("Fix 6: verify падает gracefully — не ломает happy path")

    class BrokenVerifyClient(FakeClient):
        def __init__(self):
            super().__init__()
            self.updated = False

        async def api_call(self, entity, action, object_id=None, **kwargs):
            self.calls.append((entity, action, object_id))
            if entity == "datasets" and action == "get":
                if self.updated:
                    raise RuntimeError("network glitch")
                return {"status": 200, "data": [{
                    "ID": 5, "name": "ds", "caption": "",
                    "parentID": 1, "driverID": 20, "query": "SELECT 1",
                    "fields": [],
                }]}
            if entity == "datasets" and action == "update":
                self.updated = True
                return {"status": 200, "data": [{}]}
            return {"status": 200, "data": [{}]}

    client = BrokenVerifyClient()
    result = run(_update_dataset(
        client, dataset_id=5, name=None, caption=None,
        datasource_id=None, query="SELECT 2", rls=None, query_rls=None,
        validate_query=False,
        field_aliases=None,
    ))
    check("verify exception → success=True (graceful)",
          result.get("success") is True, detail=str(result)[:200])

    print("\n=== create(query) → роутинг в dataset_create_from_sql ===")
    from app.tools.dataset_operations import _create_dataset

    class CreateClient:
        class _Inst:
            name = "test"
        instance = _Inst()

        def __init__(self):
            self.calls = []

        async def api_call(self, entity, action, object_id=None, data=None, **kw):
            self.calls.append((entity, action))
            if entity == "datasets" and action == "create":
                return {"status": 200, "data": [{
                    "ID": 7, "name": data[0]["name"],
                    "caption": data[0].get("caption", ""),
                }]}
            # datasources list для роутингового пути (_get_driver_id...)
            return {"status": 200, "data": []}

        async def raw_post(self, *a, **kw):
            class R:
                status_code = 500
                text = "stub"
                def json(self):
                    return {}
            return R()

    client = CreateClient()
    result = run(_create_dataset(client, name="t1", datasource_id=1, query=None))
    check("create без query — старый envelope (id сохранён)",
          result.get("success") is True and result.get("dataset", {}).get("id") == 7
          and result.get("message") == "Dataset created successfully",
          detail=str(result)[:200])
    check("create без query НЕ роутится (только datasets-вызовы)",
          all(e == "datasets" for e, _ in client.calls), detail=str(client.calls))

    client = CreateClient()
    result = run(_create_dataset(client, name="t2", datasource_id=1, query="SELECT 1 AS x"))
    check("create с query → НЕ пустой create (роутинг)",
          ("datasets", "create") not in client.calls, detail=str(client.calls))
    check("create с query: envelope from_sql-формата (step при стабе)",
          result.get("success") is False and "step" in result,
          detail=str(result)[:200])

    client = CreateClient()
    result = run(_create_dataset(client, name="t3", datasource_id=1, query=""))
    check("query=\'\' → НЕ роутится (пустой create)",
          result.get("message") == "Dataset created successfully",
          detail=str(result)[:200])

    print(f"\n===\nResult: {ok} OK, {fail} FAIL")
    sys.exit(0 if fail == 0 else 1)


if __name__ == "__main__":
    main()
