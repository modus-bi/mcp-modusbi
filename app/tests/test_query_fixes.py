"""Tests for query_execute: is/is-not-null, limit 0/-1, and empty name.

NULL checks: the is/is not operator is sent as a literal JSON null inside
values plus a "not": true/false flag. Additionally, '='/'!='/'<>' with
value=None map to the same NULL form (a natural alternative spelling),
while op='is'/'is not' with a non-empty value is rejected with an
error envelope (a value with these operators is not a NULL check).

limit=0 returns exactly 0 rows (like SQL LIMIT 0); limit<0 returns an
error envelope.

dataset_create_from_sql with an empty/whitespace name returns a require
envelope before calling the portal; on an HTTP!=200 create the portal
message is included in details.

Run:
    python -m app.tests.test_query_fixes
"""
import asyncio
import sys
import types

import app.tools.query_execute as qe
from app.tools.query_execute import dataset_query, dataset_create_from_sql
from app.core.security import set_security_mode, SecurityMode

ok = 0
fail = 0


def check(label: str, cond: bool, detail: str = "") -> None:
    global ok, fail
    if cond:
        ok += 1
        print(f"  [OK ] {label}")
    else:
        fail += 1
        print(f"  [FAIL] {label}" + (f" — {detail}" if detail else ""))


class FakeClient:
    """Записывает payload recordsets.create; отдаёт заданные строки."""

    def __init__(self, rows=None):
        self.calls = []
        self.rows = rows if rows is not None else []

    async def api_call(self, entity, action, object_id=None, data=None, **kw):
        self.calls.append({"entity": entity, "action": action, "data": data})
        return {"status": 200, "data": list(self.rows)}


class FakeResponse:
    def __init__(self, status_code=200, json_data=None, text=""):
        self.status_code = status_code
        self._json = json_data
        self.text = text

    def json(self):
        if self._json is None:
            raise ValueError("no json body")
        return self._json


class CreateFakeClient:
    """Клиент для dataset_create_from_sql: datasources.list + raw_post."""

    def __init__(self, create_response):
        self.calls = []
        self.raw_posts = []
        self._create_response = create_response
        self.instance = types.SimpleNamespace(
            base_url="https://fake.local", token="t")

    async def api_call(self, entity, action, object_id=None, data=None, **kw):
        self.calls.append({"entity": entity, "action": action})
        if entity == "datasources" and action == "list":
            return {"status": 200,
                    "data": [{"ID": 5, "parentID": 20, "name": "pg_test"}]}
        return {"status": 200, "data": []}

    async def raw_post(self, url, json=None, headers=None, timeout=None):
        self.raw_posts.append({"url": url, "json": json})
        return self._create_response


def run(coro):
    return asyncio.run(coro)


def where_payload(client):
    return client.calls[0]["data"][0]["where"]


def main() -> None:
    set_security_mode(SecurityMode.READWRITE)  # без DEMO-капов

    print("=== is / is not → values:[null] + not flag ===")
    client = FakeClient()
    run(dataset_query(client, dataset_id=1,
                      where=[{"name": "region", "op": "is", "value": None}]))
    w = where_payload(client)[0]
    check("is: values == [None] (литеральный null)", w.get("values") == [None], str(w))
    check("is: operators пустые", w.get("operators") == [], str(w))
    check("is: not == False", w.get("not") is False, str(w))
    check("is: name сохранён", w.get("name") == "region", str(w))

    client = FakeClient()
    run(dataset_query(client, dataset_id=1,
                      where=[{"name": "region", "op": "is not", "value": None}]))
    w = where_payload(client)[0]
    check("is not: values == [None]", w.get("values") == [None], str(w))
    check("is not: not == True", w.get("not") is True, str(w))

    # server.py делает model_dump(exclude_none=True) — ключ value отсутствует
    client = FakeClient()
    run(dataset_query(client, dataset_id=1,
                      where=[{"name": "region", "op": "is"}]))
    w = where_payload(client)[0]
    check("is без ключа value (exclude_none): values == [None]",
          w.get("values") == [None] and w.get("not") is False, str(w))

    # нормализация написания оператора
    client = FakeClient()
    run(dataset_query(client, dataset_id=1, where=[
        {"name": "a", "op": "IS  NOT"},
        {"name": "b", "op": "is null"},
        {"name": "c", "op": "Is Not Null"},
    ]))
    ws = where_payload(client)
    check("'IS  NOT' (регистр/пробелы) → not=True", ws[0].get("not") is True, str(ws[0]))
    check("'is null' → values:[None], not=False",
          ws[1].get("values") == [None] and ws[1].get("not") is False, str(ws[1]))
    check("'Is Not Null' → values:[None], not=True",
          ws[2].get("values") == [None] and ws[2].get("not") is True, str(ws[2]))

    print("=== regression: regular operators unchanged ===")
    client = FakeClient()
    run(dataset_query(client, dataset_id=1, where=[
        {"name": "region", "op": "=", "value": "Moscow"},
        {"name": "year", "op": ">=", "value": 2024},
    ]))
    ws = where_payload(client)
    check("'=' value строка → values:['Moscow'], operators:['=']",
          ws[0].get("values") == ["Moscow"] and ws[0].get("operators") == ["="],
          str(ws[0]))
    check("'>=' value число → values:[2024]",
          ws[1].get("values") == [2024] and ws[1].get("operators") == [">="],
          str(ws[1]))

    # 0/False are valid values
    client = FakeClient()
    run(dataset_query(client, dataset_id=1, where=[
        {"name": "dead", "op": "=", "value": 0},
        {"name": "flag", "op": "=", "value": False},
    ]))
    ws = where_payload(client)
    check("value=0 не теряется → values:[0]", ws[0].get("values") == [0], str(ws[0]))
    check("value=False не теряется → values:[False]",
          ws[1].get("values") == [False], str(ws[1]))

    # full-format passthrough нетронут
    client = FakeClient()
    full = {"lvl": 0, "name": "x", "not": False,
            "values": ["a"], "operators": ["="], "logicOr": 0}
    run(dataset_query(client, dataset_id=1, where=[dict(full)]))
    check("full-format проходит как есть", where_payload(client)[0] == full,
          str(where_payload(client)[0]))

    # '='/'!=' without value — alternative spelling of a NULL check
    client = FakeClient()
    run(dataset_query(client, dataset_id=1, where=[
        {"name": "x", "op": "="},
        {"name": "y", "op": "!=", "value": None},
        {"name": "z", "op": "<>"},
    ]))
    ws = where_payload(client)
    check("'=' без value → values:[None], not=False (IS NULL)",
          ws[0].get("values") == [None] and ws[0].get("not") is False
          and ws[0].get("operators") == [], str(ws[0]))
    check("'!=' value=None → values:[None], not=True (IS NOT NULL)",
          ws[1].get("values") == [None] and ws[1].get("not") is True, str(ws[1]))
    check("'<>' без value → values:[None], not=True",
          ws[2].get("values") == [None] and ws[2].get("not") is True, str(ws[2]))

    # other operators without value → values:[] (portal drops the condition)
    client = FakeClient()
    run(dataset_query(client, dataset_id=1, where=[{"name": "x", "op": ">"}]))
    check("'>' без value → values:[]",
          where_payload(client)[0].get("values") == [], str(where_payload(client)[0]))

    # op='is' with a non-empty value → explicit error (not coerced to IS NULL)
    client = FakeClient()
    res = run(dataset_query(client, dataset_id=1,
                            where=[{"name": "status", "op": "is", "value": "active"}]))
    check("'is' + value → success:false", res.get("success") is False, str(res))
    check("'is' + value → error про NULL-проверку",
          "NULL" in str(res.get("error", "")), str(res))
    check("'is' + value → hint предлагает '='/'!='",
          "'='" in str(res.get("hint", "")), str(res))
    check("'is' + value → портал не вызывается", client.calls == [], str(client.calls))

    client = FakeClient()
    res = run(dataset_query(client, dataset_id=1,
                            where=[{"name": "status", "op": "is not", "value": 0}]))
    check("'is not' + value=0 → success:false (0 — значение, не NULL)",
          res.get("success") is False, str(res))

    print("=== limit=0 → 0 rows, limit<0 → error ===")
    client = FakeClient()
    res = run(dataset_query(client, dataset_id=1, limit=-1))
    check("limit=-1 → success:false", res.get("success") is False, str(res))
    check("limit=-1 → error 'limit must be >= 0'",
          res.get("error") == "limit must be >= 0", str(res))
    check("limit=-1 → портал не вызывается", client.calls == [], str(client.calls))
    check("limit=-1 → hint присутствует", bool(res.get("hint")), str(res))

    client = FakeClient(rows=[{"region": "A"}, {"region": "B"}])
    res = run(dataset_query(client, dataset_id=1, limit=0))
    payload = client.calls[0]["data"][0]
    check("limit=0 → portal receives limit=1 (0 means 'no limit' to the portal)",
          payload.get("limit") == 1, str(payload.get("limit")))
    check("limit=0 → rows == []", res.get("rows") == [], str(res.get("rows")))
    check("limit=0 → rows_count == 0", res.get("rows_count") == 0, str(res))
    check("limit=0 → truncated:false (explicit request for 0 rows — nothing truncated)",
          res.get("truncated") is False, str(res))
    check("limit=0 → success:true", res.get("success") is True, str(res))
    check("limit=0 → fields сохранены (метаданные как у SQL LIMIT 0)",
          res.get("fields"), str(res.get("fields")))

    client = FakeClient(rows=[])
    res = run(dataset_query(client, dataset_id=1, limit=0))
    check("limit=0 на пустом датасете → rows:[], truncated:false",
          res.get("rows") == [] and res.get("truncated") is False, str(res))

    # positive limit: slice and truncated are correct
    client = FakeClient(rows=[{"r": 1}, {"r": 2}])
    res = run(dataset_query(client, dataset_id=1, limit=1))
    check("limit=1 при 2 строках → 1 строка, rows_count=1",
          len(res.get("rows", [])) == 1 and res.get("rows_count") == 1, str(res))
    check("limit=1 при 2 строках → truncated:true",
          res.get("truncated") is True, str(res))

    client = FakeClient(rows=[{"r": 1}, {"r": 2}])
    res = run(dataset_query(client, dataset_id=1, limit=10))
    payload = client.calls[0]["data"][0]
    check("limit=10 → в портал уходит limit=10", payload.get("limit") == 10,
          str(payload.get("limit")))
    check("limit=10 при 2 строках → все строки, truncated:false",
          res.get("rows_count") == 2 and res.get("truncated") is False, str(res))

    client = FakeClient(rows=[{"r": 1}])
    run(dataset_query(client, dataset_id=1))
    payload = client.calls[0]["data"][0]
    check("default limit=1000 уходит в портал", payload.get("limit") == 1000,
          str(payload.get("limit")))

    print("=== name='' → require envelope before calling the portal ===")
    for label, bad_name in [("name=''", ""), ("name='   '", "   "), ("name=None", None)]:
        client = CreateFakeClient(FakeResponse(200))
        res = run(dataset_create_from_sql(
            client, sql_query="SELECT 1 AS x", datasource_id=5, name=bad_name))
        check(f"{label} → success:false + missing:['name']",
              res.get("success") is False and res.get("missing") == ["name"],
              str(res))
        check(f"{label} → hint и example присутствуют",
              bool(res.get("hint")) and bool(res.get("example")), str(res))
        check(f"{label} → портал не вызывался",
              client.calls == [] and client.raw_posts == [], str(client.calls))

    # a valid name passes the guard (reaches the datasource lookup)
    client = CreateFakeClient(FakeResponse(200))
    client.api_call = _failing_ds_list(client)
    res = run(dataset_create_from_sql(
        client, sql_query="SELECT 1 AS x", datasource_id=5, name="valid_name"))
    check("valid name passes guard (error later in the pipeline)",
          res.get("success") is False and "missing" not in res
          and res.get("step") == "get_driver", str(res))

    print("=== HTTP!=200 on create — portal message in details ===")
    portal_msg = "Имя набора данных не может быть пустым"
    client = CreateFakeClient(FakeResponse(400, json_data={"message": portal_msg}))
    orig_validate = qe.sql_query_validate
    qe.sql_query_validate = _fake_validate_ok()
    try:
        res = run(dataset_create_from_sql(
            client, sql_query="SELECT 1 AS x", datasource_id=5, name="ds_x"))
        check("HTTP 400 → success:false, step=create_dataset",
              res.get("success") is False and res.get("step") == "create_dataset",
              str(res))
        check("HTTP 400 → message портала в details",
              portal_msg in str(res.get("details", "")), str(res))
        check("HTTP 400 с message → hint не врёт про datasource",
              "Datasource may not support" not in str(res.get("hint", ""))
              and "details" in str(res.get("hint", "")), str(res))

        # without a readable body — datasource hint as fallback
        client = CreateFakeClient(FakeResponse(400, json_data=None, text=""))
        res = run(dataset_create_from_sql(
            client, sql_query="SELECT 1 AS x", datasource_id=5, name="ds_x"))
        check("HTTP 400 без тела → fallback-hint про datasource",
              "Datasource may not support" in str(res.get("hint", "")), str(res))
        check("HTTP 400 без тела → details отсутствует",
              "details" not in res, str(res))
    finally:
        qe.sql_query_validate = orig_validate

    print(f"\n===\nResult: {ok} OK, {fail} FAIL")
    sys.exit(0 if fail == 0 else 1)


def _failing_ds_list(client):
    async def api_call(entity, action, object_id=None, data=None, **kw):
        client.calls.append({"entity": entity, "action": action})
        return {"status": 500}
    return api_call


def _fake_validate_ok():
    async def fake(client, sql_query, datasource_id, dataset_name=None):
        return {"success": True,
                "fields": [{"id": 1, "name": "x", "type": "number"}]}
    return fake


if __name__ == "__main__":
    main()
