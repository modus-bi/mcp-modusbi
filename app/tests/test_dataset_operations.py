"""Unit tests для dataset_operations — total_rows=null, delete pre-check,
create echo datasource_id.

total_rows: backend ленивый — для свежесозданных датасетов возвращает
count=0 (даже когда строки есть). MCP отдаёт None вместо обманчивого 0,
чтобы клиент не делал ложных предположений.

delete: портальный soft-delete идемпотентен — delete фантомного id даёт
success:true. MCP делает pre-check через get.
create echo: portal отдаёт parentID вместо datasourceID → fallback.

Run:
    python -m app.tests.test_dataset_operations
"""
import asyncio
import sys
from types import SimpleNamespace

from app.core.exceptions import APIError
from app.tools.dataset_operations import _create_dataset, _delete_dataset, _get_dataset


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
    """Минимальный мок client.api_call — возвращает заданный response."""

    def __init__(self, response: dict):
        self._response = response

    async def api_call(self, entity, action, **kwargs):
        return self._response


class RoutingFakeClient:
    """Мок client.api_call с маршрутизацией по action (get/delete/create).

    Значение в responses может быть Exception — тогда оно выбрасывается.
    """

    def __init__(self, responses: dict):
        self._responses = responses
        self.instance = SimpleNamespace(name="test")
        self.calls: list[tuple] = []

    async def api_call(self, entity, action, **kwargs):
        self.calls.append((entity, action))
        resp = self._responses.get(action)
        if isinstance(resp, Exception):
            raise resp
        return resp


def run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


def main() -> None:
    section("backend count=0 → total_rows=None")
    client = FakeClient({
        "status": 200,
        "data": [{
            "ID": 5, "name": "ds", "caption": "Test",
            "parentID": 1, "driverID": 1,
            "query": "SELECT 1", "fields": [],
            "count": 0,  # backend lazily не посчитал
        }],
    })
    result = run(_get_dataset(client, 5))
    check("success=True", result.get("success") is True)
    check("total_rows is None (а не 0)",
          result["dataset"]["total_rows"] is None,
          detail=f"got {result['dataset']['total_rows']!r}")

    section("backend count отсутствует (null) → total_rows=None")
    client = FakeClient({
        "status": 200,
        "data": [{
            "ID": 5, "name": "ds", "caption": "Test",
            "parentID": 1, "driverID": 1,
            "query": "SELECT 1", "fields": [],
            # count полностью отсутствует
        }],
    })
    result = run(_get_dataset(client, 5))
    check("отсутствие count → total_rows=None",
          result["dataset"]["total_rows"] is None,
          detail=f"got {result['dataset']['total_rows']!r}")

    section("backend честный count > 0 → pass-through")
    client = FakeClient({
        "status": 200,
        "data": [{
            "ID": 5, "name": "ds", "caption": "Test",
            "parentID": 1, "driverID": 1,
            "query": "SELECT 1", "fields": [],
            "count": 1234,  # реальный счёт
        }],
    })
    result = run(_get_dataset(client, 5))
    check("реальный count=1234 → total_rows=1234",
          result["dataset"]["total_rows"] == 1234,
          detail=f"got {result['dataset']['total_rows']!r}")

    section("Sanity: остальные поля не сломаны")
    fields_sample = [
        {"name": "id", "alias": "ID", "type": "integer"},
        {"name": "name", "alias": "Имя", "type": "string"},
    ]
    client = FakeClient({
        "status": 200,
        "data": [{
            "ID": 42, "name": "test_ds", "caption": "Тестовый",
            "parentID": 7, "datasourceName": "PG", "driverID": 1,
            "query": "SELECT * FROM t", "fields": fields_sample,
            "count": 100,
        }],
    })
    result = run(_get_dataset(client, 42))
    d = result["dataset"]
    check("id корректный", d["id"] == 42)
    check("name корректный", d["name"] == "test_ds")
    check("caption корректный", d["caption"] == "Тестовый")
    check("datasource_id корректный", d["datasource_id"] == 7)
    check("driver_id корректный", d["driver_id"] == 1)
    check("query сохранён", d["query"] == "SELECT * FROM t")
    check("fields_count корректный", d["fields_count"] == 2)
    check("fields переданы", len(d["fields"]) == 2)
    check("total_rows=100", d["total_rows"] == 100)

    section("delete фантома (get → HTTP 404) → success:false без delete")
    client = RoutingFakeClient({
        "get": APIError("HTTP 404: датасет не найден", status_code=404),
        "delete": {"status": 200},  # идемпотентный soft-delete портала
    })
    result = run(_delete_dataset(client, 99999))
    check("success=False", result.get("success") is False,
          detail=f"got {result!r}")
    check("error содержит 'not found'", "not found" in result.get("error", ""),
          detail=f"got {result.get('error')!r}")
    check("delete на портал НЕ ушёл",
          ("datasets", "delete") not in client.calls,
          detail=f"calls={client.calls!r}")

    section("delete фантома (get 200, data пустая) → success:false")
    client = RoutingFakeClient({
        "get": {"status": 200, "data": []},
        "delete": {"status": 200},
    })
    result = run(_delete_dataset(client, 99999))
    check("success=False при пустой data", result.get("success") is False,
          detail=f"got {result!r}")

    section("delete существующего → success:true (happy path)")
    client = RoutingFakeClient({
        "get": {"status": 200, "data": [{"ID": 5, "name": "ds"}]},
        "delete": {"status": 200},
    })
    result = run(_delete_dataset(client, 5))
    check("success=True", result.get("success") is True,
          detail=f"got {result!r}")
    check("delete на портал ушёл", ("datasets", "delete") in client.calls,
          detail=f"calls={client.calls!r}")

    section("не-404 ошибка get пробрасывается дальше")
    client = RoutingFakeClient({
        "get": APIError("HTTP 500: internal", status_code=500),
    })
    try:
        run(_delete_dataset(client, 5))
        check("APIError 500 проброшен", False, detail="исключение не выброшено")
    except APIError:
        check("APIError 500 проброшен", True)

    section("create echo — портал отдаёт parentID → datasource_id заполнен")
    client = RoutingFakeClient({
        "create": {"status": 200, "data": [{
            "ID": 99, "name": "new_ds", "caption": "Новый",
            "parentID": 7,  # портал отдаёт parentID, не datasourceID
        }]},
    })
    result = run(_create_dataset(client, name="new_ds", datasource_id=7))
    check("success=True", result.get("success") is True,
          detail=f"got {result!r}")
    check("datasource_id=7 (fallback на parentID)",
          result.get("dataset", {}).get("datasource_id") == 7,
          detail=f"got {result.get('dataset')!r}")

    section("create echo — datasourceID (если есть) в приоритете")
    client = RoutingFakeClient({
        "create": {"status": 200, "data": [{
            "ID": 100, "name": "ds2", "caption": "c",
            "datasourceID": 8,
        }]},
    })
    result = run(_create_dataset(client, name="ds2", datasource_id=8))
    check("datasource_id=8 из datasourceID",
          result.get("dataset", {}).get("datasource_id") == 8,
          detail=f"got {result.get('dataset')!r}")

    print(f"\n===\nResult: {ok} OK, {fail} FAIL")
    sys.exit(0 if fail == 0 else 1)


if __name__ == "__main__":
    main()
