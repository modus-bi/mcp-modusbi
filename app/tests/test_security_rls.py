"""security_operations RLS: status/test → datasets/get; writes → read-modify-write.

  - status/test read via datasets/get (like dataset_operations);
  - enable/disable/update_filter do a read-modify-write: get the full object →
    apply rls/query_rls → update the FULL object (snake_case query_rls);
  - an APIError from api_call (non-200 HTTP) propagates status_code into
    _rls_write_error.

Run:
    python -m app.tests.test_security_rls
"""
import asyncio
import sys

from app.core.exceptions import APIError
from app.tools.security_operations import security_operations


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


# Полный объект датасета как его возвращает datasets/get
DS = {
    "ID": 42,
    "name": "t_sec_ds",
    "caption": "Тестовый DS",
    "parentID": 5,    # datasource connection ID
    "driverID": 20,    # driver type
    "query": "SELECT 1 AS id, 'a' AS region",
    "rls": 0,
    "query_rls": "region = :current_user_id",
    "fields": [{"ID": 1, "name": "id"}, {"ID": 2, "name": "region"}],
}


class FakeClient:
    """Мок client.api_call: get отдаёт self.dataset, update пишется в журнал."""

    def __init__(self, dataset=None, update_response=None, update_exc=None):
        self.calls = []           # (object_name, command_name, object_id)
        self.update_payloads = []  # data из datasets/update
        self.dataset = dataset
        self.update_response = update_response or {"status": 200, "data": [{}]}
        self.update_exc = update_exc

    async def api_call(self, object_name, command_name, object_id=None, data=None, **kwargs):
        self.calls.append((object_name, command_name, object_id))
        if command_name == "get":
            if self.dataset is None:
                return {"status": 200, "data": []}
            return {"status": 200, "data": [dict(self.dataset)]}
        if command_name == "update":
            self.update_payloads.append(data)
            if self.update_exc:
                raise self.update_exc
            return self.update_response
        return {"status": 200, "data": [{}]}


def run(coro):
    return asyncio.run(coro)


FULL_OBJECT_KEYS = ("ID", "name", "caption", "query", "parentID", "driverID")


def check_full_object_preserved(payload: dict) -> None:
    """Контракт datasets/update: полный объект, не меняющиеся поля из get."""
    check("update payload содержит все обязательные ключи",
          all(k in payload for k in FULL_OBJECT_KEYS),
          detail=f"keys={sorted(payload.keys())}")
    check("name/caption/query/parentID/driverID сохранены из get",
          payload.get("name") == DS["name"]
          and payload.get("caption") == DS["caption"]
          and payload.get("query") == DS["query"]
          and payload.get("parentID") == DS["parentID"]
          and payload.get("driverID") == DS["driverID"],
          detail=str(payload))
    check("ключ фильтра snake_case query_rls (не queryRls)",
          "query_rls" in payload and "queryRls" not in payload,
          detail=f"keys={sorted(payload.keys())}")


def main() -> None:
    section("status: команда datasets/get, не read")
    client = FakeClient(dataset=DS)
    result = run(security_operations(client, "status", dataset_id=42))
    check("success=True", result.get("success") is True, detail=str(result)[:200])
    check("вызвана команда get",
          ("datasets", "get", 42) in client.calls, detail=str(client.calls))
    check("команда read НЕ вызывается",
          all(c[1] != "read" for c in client.calls), detail=str(client.calls))
    check("rls_enabled/rls_query из объекта датасета",
          result.get("rls_enabled") is False
          and result.get("rls_query") == DS["query_rls"],
          detail=str(result)[:200])
    check("dataset_name из объекта",
          result.get("dataset_name") == DS["name"], detail=str(result)[:200])

    section("status: датасет не найден (пустой data)")
    client = FakeClient(dataset=None)
    result = run(security_operations(client, "status", dataset_id=99))
    check("success=False", result.get("success") is False, detail=str(result)[:200])
    check("error = Dataset not found",
          result.get("error") == "Dataset not found", detail=str(result)[:200])

    section("test: делегирует в status через get (rls выключен → skipped)")
    client = FakeClient(dataset=DS)  # rls=0
    result = run(security_operations(client, "test", dataset_id=42))
    check("success=True, test_result=skipped",
          result.get("success") is True and result.get("test_result") == "skipped",
          detail=str(result)[:200])
    check("команда read НЕ вызывается",
          all(c[1] != "read" for c in client.calls), detail=str(client.calls))

    section("enable: read-modify-write полного объекта")
    client = FakeClient(dataset=DS)
    result = run(security_operations(client, "enable", dataset_id=42))
    check("success=True", result.get("success") is True, detail=str(result)[:200])
    check("сначала get, затем update",
          [c[1] for c in client.calls] == ["get", "update"],
          detail=str(client.calls))
    check("update payload = data[список из одного объекта]",
          isinstance(client.update_payloads[0], list)
          and len(client.update_payloads[0]) == 1,
          detail=str(client.update_payloads))
    payload = client.update_payloads[0][0]
    check_full_object_preserved(payload)
    check("rls=1", payload.get("rls") == 1, detail=str(payload))
    check("существующий query_rls сохранён (не затёрт)",
          payload.get("query_rls") == DS["query_rls"], detail=str(payload))
    check("rls_enabled=True в ответе", result.get("rls_enabled") is True)

    section("disable: rls=0, фильтр очищен, прочие поля сохранены")
    client = FakeClient(dataset={**DS, "rls": 1})
    result = run(security_operations(client, "disable", dataset_id=42))
    check("success=True", result.get("success") is True, detail=str(result)[:200])
    payload = client.update_payloads[0][0]
    check_full_object_preserved(payload)
    check("rls=0", payload.get("rls") == 0, detail=str(payload))
    check("query_rls очищен", payload.get("query_rls") == "", detail=str(payload))

    section("update_filter: новый фильтр, прочие поля не потеряны")
    client = FakeClient(dataset=DS)
    new_filter = "user_id = :current_user_id"
    result = run(security_operations(
        client, "update_filter", dataset_id=42, rls_query=new_filter))
    check("success=True", result.get("success") is True, detail=str(result)[:200])
    payload = client.update_payloads[0][0]
    check_full_object_preserved(payload)
    check("rls=1 (включается вместе с фильтром)",
          payload.get("rls") == 1, detail=str(payload))
    check("query_rls = новый фильтр",
          payload.get("query_rls") == new_filter, detail=str(payload))
    check("rls_query в ответе", result.get("rls_query") == new_filter)

    section("update вернул body-status 400 → error-конверт с driver hint")
    client = FakeClient(
        dataset=DS,
        update_response={"status": 400, "message": "driver does not support RLS"},
    )
    result = run(security_operations(client, "enable", dataset_id=42))
    check("success=False", result.get("success") is False, detail=str(result)[:200])
    check("status=400 в ответе", result.get("status") == 400, detail=str(result)[:200])
    check("hint про драйвер присутствует",
          "driver" in result.get("hint", ""), detail=str(result)[:300])

    section("api_call бросил APIError (HTTP 400) → status_code прокинут в конверт")
    client = FakeClient(
        dataset=DS,
        update_exc=APIError("Ошибка API: HTTP 400", status_code=400),
    )
    result = run(security_operations(
        client, "update_filter", dataset_id=42, rls_query="region = 'a'"))
    check("success=False", result.get("success") is False, detail=str(result)[:200])
    check("status=400 (из APIError.details)",
          result.get("status") == 400, detail=str(result)[:200])
    check("hint про драйвер присутствует",
          "driver" in result.get("hint", ""), detail=str(result)[:300])

    print(f"\n===\nResult: {ok} OK, {fail} FAIL")
    sys.exit(0 if fail == 0 else 1)


if __name__ == "__main__":
    main()
