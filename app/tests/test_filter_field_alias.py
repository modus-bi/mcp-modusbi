"""filter_field_add alias inheritance from dataset.

When `_filter_field_add` is called without an explicit alias, the alias is
read from the dataset via `_lookup_dataset_field_alias`. It falls back to
field_name only when the dataset field has no alias.

Run:
    python -m app.tests.test_filter_field_alias
"""
import asyncio
import sys

from app.tools.component_filters import (
    _filter_field_add,
    _lookup_dataset_field_alias,
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
    """Мок client.api_call с программируемыми ответами по (entity, action)."""

    def __init__(self):
        self.responses: dict[tuple, dict] = {}
        self.calls: list[tuple] = []

    def setup_report(self, report_id, report_data):
        self.responses[("reports", "get", report_id)] = {
            "status": 200, "data": [report_data]
        }

    def setup_dataset(self, dataset_id, fields):
        self.responses[("datasets", "get", dataset_id)] = {
            "status": 200,
            "data": [{"ID": dataset_id, "fields": fields}],
        }

    def setup_missing_dataset(self, dataset_id):
        self.responses[("datasets", "get", dataset_id)] = {
            "status": 404, "data": [], "message": "Not found"
        }

    async def api_call(self, entity, action, object_id=None, **kwargs):
        self.calls.append((entity, action, object_id))
        # Capture saved data so test can assert what was sent.
        if action == "update":
            self.last_saved = kwargs.get("data")
        return self.responses.get(
            (entity, action, object_id),
            {"status": 200, "data": [{}]},  # default empty success
        )


def run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


def make_report(component_idx=0, dataset_id=100):
    """Минимальный валидный отчёт с одним FilterControlPanel."""
    return {
        "ID": 1, "name": "test_report",
        "grid": {
            "components": {
                str(component_idx): {
                    "type": "HsFilterControlPanel",
                    "dataSetId": dataset_id,
                    "config": {
                        "axes": [{"type": "filters", "fields": []}],
                    },
                },
            },
        },
        "globalFilters": {},
    }


def main() -> None:
    section("_lookup_dataset_field_alias: базовое поведение")
    client = FakeClient()
    client.setup_dataset(100, fields=[
        {"name": "product", "alias": "Категория животных"},
        {"name": "region",  "alias": "Регион"},
        {"name": "year",    "alias": ""},          # пустой alias
        {"name": "code",    "alias": None},        # null alias
    ])
    result = run(_lookup_dataset_field_alias(client, 100, "product"))
    check("русский alias найден", result == "Категория животных",
          detail=f"got {result!r}")

    result = run(_lookup_dataset_field_alias(client, 100, "region"))
    check("второй alias найден", result == "Регион", detail=f"got {result!r}")

    result = run(_lookup_dataset_field_alias(client, 100, "year"))
    check("пустой alias → None (fallback)", result is None,
          detail=f"got {result!r}")

    result = run(_lookup_dataset_field_alias(client, 100, "code"))
    check("null alias → None", result is None, detail=f"got {result!r}")

    result = run(_lookup_dataset_field_alias(client, 100, "absent"))
    check("отсутствующее поле → None", result is None,
          detail=f"got {result!r}")

    result = run(_lookup_dataset_field_alias(client, None, "product"))
    check("dataset_id=None → None (без api-call)", result is None)

    result = run(_lookup_dataset_field_alias(client, 100, ""))
    check("пустой field_name → None", result is None)

    section("_lookup_dataset_field_alias: робастность к ошибкам")
    client.setup_missing_dataset(999)
    result = run(_lookup_dataset_field_alias(client, 999, "product"))
    check("404 на dataset → None (без эксепшна)", result is None)

    # Malformed payloads return None instead of raising AttributeError.
    malformed_client = FakeClient()
    malformed_client.responses[("datasets", "get", 1)] = "not a dict"
    result = run(_lookup_dataset_field_alias(malformed_client, 1, "product"))
    check("resp не dict → None", result is None)

    malformed_client.responses[("datasets", "get", 2)] = {
        "status": 200, "data": ["string instead of dict"]
    }
    result = run(_lookup_dataset_field_alias(malformed_client, 2, "product"))
    check("data[0] не dict → None", result is None)

    malformed_client.responses[("datasets", "get", 3)] = {
        "status": 200, "data": [{"fields": {"product": {"alias": "X"}}}]
    }
    result = run(_lookup_dataset_field_alias(malformed_client, 3, "product"))
    check("fields не list (dict) → None", result is None)

    malformed_client.responses[("datasets", "get", 4)] = {
        "status": 200, "data": [{"fields": [
            "string in list",
            {"name": "product", "alias": "Категория"},
        ]}]
    }
    result = run(_lookup_dataset_field_alias(malformed_client, 4, "product"))
    check("string в fields пропускается, dict обрабатывается",
          result == "Категория", detail=f"got {result!r}")

    def _extract_filter_field(saved_data, idx=0, field_idx=0):
        """Достать filter axis field 0 из сохранённого отчёта."""
        report = saved_data[0]
        comp = report["grid"]["components"][str(idx)]
        for axis in comp["config"]["axes"]:
            if axis.get("type") == "filters":
                return axis["fields"][field_idx]
        return None

    section("_filter_field_add: alias наследуется из dataset (END-TO-END)")
    client = FakeClient()
    client.setup_dataset(100, fields=[
        {"name": "product", "alias": "Категория животных"},
    ])
    client.setup_report(1, make_report(component_idx=0, dataset_id=100))
    result = run(_filter_field_add(
        client, report_id=1, component_idx=0,
        field_name="product", alias=None, field_type="string",
        dataset_id=None,  # резолвится из comp.dataSetId
    ))
    check("filter_field_add success", result.get("success") is True,
          detail=str(result)[:150])
    saved_field = _extract_filter_field(client.last_saved)
    check("сохранённый alias == 'Категория животных' (из DS)",
          saved_field["alias"] == "Категория животных",
          detail=f"got {saved_field['alias']!r}")
    check("title__ru тоже = русский alias",
          saved_field["title__ru"] == "Категория животных",
          detail=f"got {saved_field['title__ru']!r}")
    check("name остался 'product'", saved_field["name"] == "product")

    section("_filter_field_add: explicit alias > dataset (END-TO-END)")
    client = FakeClient()
    client.setup_dataset(100, fields=[
        {"name": "product", "alias": "Категория животных"},
    ])
    client.setup_report(1, make_report(component_idx=0, dataset_id=100))
    result = run(_filter_field_add(
        client, report_id=1, component_idx=0,
        field_name="product", alias="Мой alias", field_type="string",
        dataset_id=None,
    ))
    check("explicit alias принимается", result.get("success") is True)
    saved_field = _extract_filter_field(client.last_saved)
    check("сохранённый alias == 'Мой alias' (не DS)",
          saved_field["alias"] == "Мой alias",
          detail=f"got {saved_field['alias']!r}")

    section("_filter_field_add: fallback на field_name (END-TO-END)")
    client = FakeClient()
    client.setup_dataset(100, fields=[
        {"name": "code", "alias": ""},  # backend сохранил пустую строку
    ])
    client.setup_report(1, make_report(component_idx=0, dataset_id=100))
    result = run(_filter_field_add(
        client, report_id=1, component_idx=0,
        field_name="code", alias=None, field_type="string",
        dataset_id=None,
    ))
    check("без alias в DS → fallback (success)", result.get("success") is True)
    saved_field = _extract_filter_field(client.last_saved)
    check("сохранённый alias == field_name 'code'",
          saved_field["alias"] == "code",
          detail=f"got {saved_field['alias']!r}")

    section("_filter_field_add: dataset недоступен → fallback (END-TO-END)")
    client = FakeClient()
    client.setup_missing_dataset(100)  # 404 на dataset.get
    client.setup_report(1, make_report(component_idx=0, dataset_id=100))
    result = run(_filter_field_add(
        client, report_id=1, component_idx=0,
        field_name="product", alias=None, field_type="string",
        dataset_id=None,
    ))
    check("dataset 404 не ломает filter_field_add",
          result.get("success") is True, detail=str(result)[:150])
    saved_field = _extract_filter_field(client.last_saved)
    check("сохранённый alias == field_name (fallback при 404)",
          saved_field["alias"] == "product",
          detail=f"got {saved_field['alias']!r}")

    print(f"\n===\nResult: {ok} OK, {fail} FAIL")
    sys.exit(0 if fail == 0 else 1)


if __name__ == "__main__":
    main()
