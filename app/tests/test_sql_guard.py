"""SELECT-only guard для sql_query_validate + детект пустого data в query_batch.

Портал валидирует SQL исполнением — /v1/api/query реально выполняет
присланный SQL на источнике. MCP пропускает РОВНО ОДИН statement и только
SELECT/WITH...SELECT; DML/DDL/multi-statement отбиваются ДО raw_post с error
«only single SELECT allowed». Строковые литералы/комментарии вырезаются перед
анализом, чтобы слово UPDATE внутри строки не давало ложного срабатывания, а
';' внутри литерала не считалась разделителем стейтментов.

query_batch: если портал отдаёт status:200 + data:[] на контракт-валидный
батч, MCP возвращает success:false + warning «portal returned empty data
(known issue); use dataset_query per query».

Run:
    python -m app.tests.test_sql_guard
"""
import asyncio
import sys

from app.tools.query_execute import (
    _sql_select_only_guard,
    query_batch,
    sql_query_validate,
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


def run(coro):
    return asyncio.run(coro)


def guard_ok(sql: str) -> bool:
    """True если guard пропускает SQL (возвращает None)."""
    return _sql_select_only_guard(sql) is None


def guard_blocked(sql: str) -> bool:
    """True если guard отбивает SQL с каноничным error-конвертом."""
    result = _sql_select_only_guard(sql)
    return (
        isinstance(result, dict)
        and result.get("success") is False
        and result.get("error") == "only single SELECT allowed"
        and bool(result.get("hint"))
    )


# --- fakes -------------------------------------------------------------------

class FakeResponse:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self._payload = payload if payload is not None else {}

    def json(self):
        return self._payload


class FakeInstance:
    base_url = "https://fake.local"
    token = "fake-token"


class FakeValidateClient:
    """Мок client для sql_query_validate: считает raw_post вызовы."""

    def __init__(self):
        self.instance = FakeInstance()
        self.raw_post_calls = []

    async def api_call(self, entity, action, object_id=None, **kwargs):
        # datasources list — для _get_driver_id_from_datasource
        return {
            "status": 200,
            "data": [{"ID": 5, "parentID": 20, "name": "ger"}],
        }

    async def raw_post(self, url, **kwargs):
        self.raw_post_calls.append((url, kwargs.get("json")))
        return FakeResponse(200, {
            "fields": [{"ID": 1, "name": "f1", "alias": "", "type": "number"}],
        })


class FakeBatchClient:
    """Мок client для query_batch: отдаёт заданный data[] на recordset.batch."""

    def __init__(self, data):
        self._data = data

    async def api_call(self, entity, action, object_id=None, **kwargs):
        return {"status": 200, "data": self._data}


def main() -> None:
    section("Guard: валидный SELECT/WITH проходит")
    check("простой SELECT — ok", guard_ok("SELECT 1 as f1, 'z' as f2"))
    check("SELECT с trailing ';' — ok", guard_ok("SELECT id, name FROM users;"))
    check("WITH ... SELECT — ok",
          guard_ok("WITH t AS (SELECT region, sum(x) s FROM dtp GROUP BY 1) "
                   "SELECT * FROM t ORDER BY s DESC"))
    check("SELECT в нижнем регистре с переносами — ok",
          guard_ok("select id,\n  name\nfrom users\nlimit 10"))

    section("Guard: DML/DDL отбиваются")
    check("UPDATE — fail", guard_blocked("UPDATE users SET name = 'x' WHERE id = 1"))
    check("DELETE — fail", guard_blocked("DELETE FROM users WHERE id = 1"))
    check("DROP — fail", guard_blocked("DROP TABLE users"))
    check("INSERT — fail", guard_blocked("INSERT INTO users (id) VALUES (1)"))
    check("TRUNCATE — fail", guard_blocked("TRUNCATE users"))
    check("CREATE — fail", guard_blocked("CREATE TABLE t (id int)"))
    check("ALTER — fail", guard_blocked("ALTER TABLE users ADD COLUMN x int"))
    check("DML внутри WITH (data-modifying CTE) — fail",
          guard_blocked("WITH x AS (DELETE FROM t RETURNING *) SELECT * FROM x"))
    check("SELECT ... INTO (создаёт таблицу) — fail",
          guard_blocked("SELECT id INTO new_table FROM users"))

    section("Guard: multi-statement отбивается")
    check("два SELECT через ';' — fail", guard_blocked("SELECT 1 as a; SELECT 2 as b"))
    check("SELECT; UPDATE — fail",
          guard_blocked("SELECT 1; UPDATE users SET name='x'"))
    result = _sql_select_only_guard("SELECT 1; SELECT 2; SELECT 3")
    check("details содержит число стейтментов (3)",
          "3 statements" in (result or {}).get("details", ""),
          detail=str(result))

    section("Guard: литералы и комментарии не дают ложных срабатываний")
    check("слово UPDATE внутри строкового литерала — ok",
          guard_ok("SELECT 'UPDATE users SET x=1' as cmd FROM logs"))
    check("';' внутри литерала — не разделитель — ok",
          guard_ok("SELECT ';' as semi, 'a;b' as parts"))
    check("UPDATE в line-комментарии — ok",
          guard_ok("-- UPDATE happens elsewhere\nSELECT 1"))
    check("DELETE в block-комментарии — ok",
          guard_ok("/* DELETE FROM t */ SELECT 1"))
    check("экранированная кавычка '' внутри литерала — ok",
          guard_ok("SELECT 'it''s; UPDATE x' as s"))
    check("колонка last_update (не whole-word) — ok",
          guard_ok("SELECT last_update, created_at FROM users"))
    check("quoted identifier \"update\" — ok",
          guard_ok('SELECT "update" FROM audit'))
    check("UPDATE вне литерала всё равно ловится — fail",
          guard_blocked("SELECT 'safe' as s; UPDATE users SET x=1"))
    check("untagged $$UPDATE users$$ — ok",
          guard_ok("SELECT $$UPDATE users$$ as cmd"))
    check("';' внутри untagged $$a;b$$ — не разделитель — ok",
          guard_ok("SELECT $$a;b$$ as parts"))
    check("tagged $x$DELETE FROM t$x$ — ok",
          guard_ok("SELECT $x$DELETE FROM t$x$ as cmd"))
    check("ведущая скобка (SELECT 1) UNION ALL (SELECT 2) — ok",
          guard_ok("(SELECT 1 as a) UNION ALL (SELECT 2 as a)"))

    section("Guard: мусорный ввод")
    check("пустая строка — fail", guard_blocked(""))
    check("только комментарий — fail", guard_blocked("-- nothing here"))
    check("не-SQL слово первым — fail", guard_blocked("EXPLAIN SELECT 1"))

    section("sql_query_validate: guard срабатывает ДО raw_post")
    client = FakeValidateClient()
    result = run(sql_query_validate(
        client, sql_query="UPDATE users SET x=1", datasource_id=5))
    check("UPDATE → success=False", result.get("success") is False,
          detail=str(result)[:150])
    check("error='only single SELECT allowed'",
          result.get("error") == "only single SELECT allowed",
          detail=str(result.get("error")))
    check("raw_post НЕ вызывался (SQL не ушёл на портал)",
          len(client.raw_post_calls) == 0,
          detail=f"calls={len(client.raw_post_calls)}")

    section("sql_query_validate: валидный SELECT проходит на портал")
    client = FakeValidateClient()
    result = run(sql_query_validate(
        client, sql_query="SELECT 1 as f1", datasource_id=5))
    check("SELECT → success=True", result.get("success") is True,
          detail=str(result)[:150])
    check("raw_post вызван ровно 1 раз", len(client.raw_post_calls) == 1)
    check("fields распарсены", result.get("fields_count") == 1,
          detail=str(result.get("fields")))

    section("query_batch: пустой data → success=False + warning")
    client = FakeBatchClient(data=[])
    result = run(query_batch(client, dataset_id=5, queries=[
        {"id": "total", "params": {"select": [{"name": "x", "aggr": "sum"}]}},
        {"id": "by_region", "params": {"select": [{"name": "region"}]}},
    ]))
    check("success=False на пустом data", result.get("success") is False,
          detail=str(result)[:200])
    check("warning про known issue + обход dataset_query",
          "portal returned empty data" in result.get("warning", "")
          and "dataset_query" in result.get("warning", ""),
          detail=str(result.get("warning")))

    section("query_batch: все запросы с 0 строк и без ошибок → success=True + warning")
    # Жёсткий fail только на сигнатуре пустого ответа (data:[]);
    # непустой results со сплошными 0 строк может быть легитимным пустым
    # результатом (WHERE без совпадений) — мягкий warning вместо ошибки.
    client = FakeBatchClient(data=[
        {"call_id": "q1", "call_error": 0, "call_message": "", "call_result": []},
        {"call_id": "q2", "call_error": 0, "call_message": "", "call_result": []},
    ])
    result = run(query_batch(client, dataset_id=5, queries=[
        {"id": "q1", "params": {}},
        {"id": "q2", "params": {}},
    ]))
    check("success=True (не жёсткий fail)", result.get("success") is True,
          detail=str(result)[:200])
    check("warning про 0 rows + cross-check",
          "0 rows" in result.get("warning", "")
          and "dataset_query" in result.get("warning", ""),
          detail=str(result.get("warning")))

    section("query_batch: данные есть → success=True (регрессия)")
    client = FakeBatchClient(data=[
        {"call_id": "q1", "call_error": 0, "call_message": "", "call_result": [
            {"fields": [{"name": "region", "type": "string"}],
             "rows": [["SPb"], ["Msk"]]},
        ]},
    ])
    result = run(query_batch(client, dataset_id=5, queries=[
        {"id": "q1", "params": {"select": [{"name": "region"}]}},
    ]))
    check("success=True при непустых rows", result.get("success") is True,
          detail=str(result)[:200])
    check("rows_count=2 в results",
          result.get("results", [{}])[0].get("rows_count") == 2,
          detail=str(result.get("results")))

    section("query_batch: per-query ошибки — частично/все упали")
    # ВСЕ под-запросы упали → честный success:false
    client = FakeBatchClient(data=[
        {"call_id": "q1", "call_error": 1, "call_message": "boom",
         "call_result": []},
    ])
    result = run(query_batch(client, dataset_id=5, queries=[
        {"id": "q1", "params": {}},
    ]))
    check("все под-запросы упали → success=False",
          result.get("success") is False
          and "all batch sub-queries failed" in result.get("error", ""),
          detail=str(result)[:200])
    check("results[0].success=False с текстом ошибки",
          result.get("results", [{}])[0].get("success") is False
          and result.get("results", [{}])[0].get("error") == "boom",
          detail=str(result.get("results")))
    # ЧАСТЬ упала → success:true + warning
    client = FakeBatchClient(data=[
        {"call_id": "ok", "call_error": 0, "call_message": "", "call_result": [
            {"fields": [{"name": "r", "type": "string"}], "rows": [["x"]]}]},
        {"call_id": "bad", "call_error": 1, "call_message": "boom",
         "call_result": []},
    ])
    result = run(query_batch(client, dataset_id=5, queries=[
        {"id": "ok", "params": {}}, {"id": "bad", "params": {}},
    ]))
    check("часть упала → success=True + warning",
          result.get("success") is True
          and "some batch sub-queries failed" in result.get("warning", ""),
          detail=str(result)[:200])

    print(f"\n===\nResult: {ok} OK, {fail} FAIL")
    sys.exit(0 if fail == 0 else 1)


if __name__ == "__main__":
    main()
