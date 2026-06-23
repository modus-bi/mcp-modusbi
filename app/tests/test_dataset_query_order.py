"""dataset_query order — ключ direction + автоподстановка alias.

MCP шлёт direction (+legacy dir), alias берётся из select ([values][idx])
или group ([categories]), fallback — имя поля. Портал читает "direction",
а условие с пустым alias отбрасывается парсером.

Run:
    python -m app.tests.test_dataset_query_order
"""
import asyncio
import sys

from app.tools.query_execute import dataset_query

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
    def __init__(self):
        self.calls = []

    async def api_call(self, entity, action, object_id=None, data=None, **kw):
        self.calls.append({"entity": entity, "action": action, "data": data})
        return {"status": 200, "data": [{"fields": [], "rows": []}]}


def run(coro):
    return asyncio.run(coro)


def main() -> None:
    print("=== F11: order direction + alias ===")
    client = FakeClient()
    run(dataset_query(
        client, dataset_id=1,
        select=[{"name": "region"}, {"name": "accidents", "aggr": "sum"}],
        group=[{"name": "region"}],
        order=[{"name": "accidents", "dir": "desc"}],
    ))
    params = client.calls[0]["data"][0]
    o = params["order"][0]
    check("direction='desc' присутствует", o.get("direction") == "desc", str(o))
    check("legacy dir='desc' сохранён", o.get("dir") == "desc", str(o))
    check("alias автоподставлен из select ([values][1])",
          o.get("alias") == "[values][1]", str(o))

    client = FakeClient()
    run(dataset_query(
        client, dataset_id=1,
        select=[{"name": "accidents", "aggr": "sum"}],
        group=[{"name": "region"}],
        order=[{"name": "region"}],
    ))
    o = client.calls[0]["data"][0]["order"][0]
    check("group-поле получает [categories]", o.get("alias") == "[categories]", str(o))
    check("default direction=asc", o.get("direction") == "asc", str(o))

    client = FakeClient()
    run(dataset_query(
        client, dataset_id=1,
        order=[{"name": "unknown_f", "direction": "desc", "alias": "custom"}],
    ))
    o = client.calls[0]["data"][0]["order"][0]
    check("явный alias не перетирается", o.get("alias") == "custom", str(o))
    check("явный direction принимается", o.get("direction") == "desc", str(o))

    client = FakeClient()
    run(dataset_query(client, dataset_id=1, order=[{"name": "f1"}]))
    o = client.calls[0]["data"][0]["order"][0]
    check("fallback alias = имя поля (не пустой)", o.get("alias") == "f1", str(o))

    print("=== regression: окружающий payload не изменён фиксом ===")
    client = FakeClient()
    run(dataset_query(
        client, dataset_id=1,
        select=[{"name": "region"}, {"name": "amount", "aggr": "sum"}],
        where=[{"name": "year", "op": "=", "value": 2024}],
        group=[{"name": "region"}],
        order=[{"name": "amount", "dir": "desc"}],
        limit=10, variables={"v": ["x"]},
    ))
    p = client.calls[0]["data"][0]
    check("select alias [values][N]",
          [f["alias"] for f in p["select"]] == ["[values][0]", "[values][1]"], str(p["select"]))
    check("group alias [categories]", p["group"][0]["alias"] == "[categories]", str(p["group"]))
    check("where full-format", p["where"][0]["operators"] == ["="]
          and p["where"][0]["values"] == [2024], str(p["where"]))
    check("limit и variables на месте", p.get("limit") == 10
          and p["variables"][0]["name"] == "v", str(p.get("variables")))

    print("=== дубль имени в select: first-wins (как FindByName портала) ===")
    client = FakeClient()
    run(dataset_query(
        client, dataset_id=1,
        select=[{"name": "amount", "aggr": "sum"}, {"name": "amount", "aggr": "avg"}],
        order=[{"name": "amount", "dir": "desc"}],
    ))
    o = client.calls[0]["data"][0]["order"][0]
    check("dup-select: alias = [values][0] (первое вхождение)",
          o.get("alias") == "[values][0]", str(o))

    print("=== direction-санитайз (белый список) ===")
    client = FakeClient()
    run(dataset_query(client, dataset_id=1,
                      order=[{"name": "f1", "direction": "DESC; DROP TABLE x"}]))
    o = client.calls[0]["data"][0]["order"][0]
    check("невалидный direction → asc", o.get("direction") == "asc", str(o))

    print(f"\n===\nResult: {ok} OK, {fail} FAIL")
    sys.exit(0 if fail == 0 else 1)


if __name__ == "__main__":
    main()
