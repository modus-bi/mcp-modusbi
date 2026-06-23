"""Unit tests for export_data.py — CSV/XLSX export.

component_csv must not crash on the bare-list recordsets/create
response (the usual shape) and must build columns from real row keys
(rows are flat dicts, there are no fields/rows sub-keys).

component_xlsx must send the CMD body for exports/reportToXlsx
manually via raw_post — api_call() has no command_id/export/options
kwargs (the fake client below mirrors that signature, so any
illegal kwarg would TypeError).

Everything runs against fakes.

Run:
    python -m app.tests.test_data_export
"""
import asyncio
import base64
import csv
import io
import sys
import tempfile
from pathlib import Path

from app.tools.export_data import (
    export_component_to_csv,
    export_component_to_xlsx,
    export_operations,
    _build_xlsx_payload,
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


def section(name: str) -> None:
    print(f"\n=== {name} ===")


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------

class FakeInstance:
    """Minimal stand-in for app.core.instances.Instance."""
    token = "fake-token"

    def get_api_url(self, object_name, object_id=None):
        base = "https://fake.local/v1/api"
        if object_id is not None:
            return f"{base}/{object_name}/{object_id}"
        return f"{base}/{object_name}"


class FakeResponse:
    def __init__(self, status_code=200, json_data=None, text=""):
        self.status_code = status_code
        self._json = json_data if json_data is not None else {}
        self.text = text

    def json(self):
        return self._json


class FakeClient:
    """Mirrors InstanceClient surface used by export_data.py.

    api_call signature copies the actual one (instances.py) on purpose:
    passing command_id/export/options kwargs would raise TypeError here.
    """

    def __init__(self, report=None, recordset_response=None, xlsx_response=None):
        self.instance = FakeInstance()
        self.report = report
        self.recordset_response = recordset_response
        self.xlsx_response = xlsx_response or FakeResponse()
        self.api_calls = []
        self.raw_posts = []

    async def api_call(self, object_name, command_name, object_id=None,
                       data=None, retry=True):
        self.api_calls.append((object_name, command_name, object_id))
        if object_name == "reports" and command_name == "get":
            return {"status": 200, "data": [self.report]}
        if object_name == "recordsets" and command_name == "create":
            if isinstance(self.recordset_response, Exception):
                raise self.recordset_response
            return self.recordset_response
        raise AssertionError(f"unexpected api_call: {object_name}/{command_name}")

    async def raw_post(self, url, *, json=None, headers=None, timeout=30.0):
        self.raw_posts.append(
            {"url": url, "json": json, "headers": headers, "timeout": timeout}
        )
        return self.xlsx_response


def make_report(name="export_r1"):
    """Report wrapper with one table component (idx 0) bound to a dataset."""
    return {
        "name": name,
        "grid": {
            "components": {
                "0": {
                    "type": "HsTableReactabularChart",
                    "config": {
                        "caption": "Test Table",
                        "datasetId": 2,
                        "axes": [
                            {"name": "categories", "fields": [
                                {"name": "region", "alias": "Region",
                                 "id": "f1", "type": "string"}
                            ]},
                            {"name": "values", "fields": [
                                {"name": "value", "alias": "Value",
                                 "id": "f2", "type": "number", "agg": "sum"}
                            ]},
                        ],
                    },
                }
            }
        },
    }


ROWS = [
    {"region": "Region A", "value": 100},
    {"region": "Region B", "value": 200},
    {"region": "Region C", "value": 300},
]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

async def test_csv_list_response(tmp):
    section("component_csv — bare list response (recordsets shape)")
    client = FakeClient(report=make_report(), recordset_response=list(ROWS))
    r = await export_component_to_csv(
        client, 5, 0, output_dir=tmp, filename="t_list")
    check("success is True", r.get("success") is True, str(r))
    check("rows_count == 3", r.get("rows_count") == 3, str(r.get("rows_count")))
    check("columns built from row keys", r.get("columns_count") == 2)

    path = Path(r.get("saved_path", ""))
    check("file written", path.exists())
    content = path.read_text(encoding="utf-8-sig")
    parsed = list(csv.reader(io.StringIO(content)))
    check("header == real row keys",
          parsed[0] == ["region", "value"], str(parsed[0]))
    check("first data row matches",
          parsed[1] == ["Region A", "100"], str(parsed[1]))
    check("3 data rows in file", len(parsed) == 4, f"got {len(parsed) - 1}")


async def test_csv_dict_response(tmp):
    section("component_csv — dict {status, data} response (no crash)")
    client = FakeClient(report=make_report(),
                        recordset_response={"status": 200, "data": list(ROWS)})
    r = await export_component_to_csv(
        client, 5, 0, output_dir=tmp, filename="t_dict")
    check("success is True", r.get("success") is True, str(r))
    check("rows_count == 3", r.get("rows_count") == 3)
    check("file written", Path(r.get("saved_path", "")).exists())


async def test_csv_error_and_empty(tmp):
    section("component_csv — error/empty responses → envelope, no crash")
    client = FakeClient(report=make_report(),
                        recordset_response={"status": 500, "message": "boom"})
    r = await export_component_to_csv(client, 5, 0, output_dir=tmp)
    check("dict error → success False", r.get("success") is False)
    check("error mentions backend message", "boom" in r.get("error", ""))
    check("hint present", bool(r.get("hint")))

    client = FakeClient(report=make_report(), recordset_response=[])
    r = await export_component_to_csv(client, 5, 0, output_dir=tmp)
    check("empty list → success False, no crash", r.get("success") is False)

    client = FakeClient(report=make_report(),
                        recordset_response={"status": 200, "data": []})
    r = await export_component_to_csv(client, 5, 0, output_dir=tmp)
    check("dict with empty data → success False, no crash",
          r.get("success") is False)

    # Non-dict rows (unexpected format) must not crash either
    client = FakeClient(report=make_report(),
                        recordset_response=[["Region A", 100]])
    r = await export_component_to_csv(client, 5, 0, output_dir=tmp)
    check("non-dict rows → success False, no crash", r.get("success") is False)


async def test_csv_limit(tmp):
    section("component_csv — limit applied")
    client = FakeClient(report=make_report(), recordset_response=list(ROWS))
    r = await export_component_to_csv(
        client, 5, 0, output_dir=tmp, filename="t_lim", limit=2)
    check("success is True", r.get("success") is True)
    check("was_limited is True", r.get("was_limited") is True)
    check("rows_count == 2", r.get("rows_count") == 2)


def make_xlsx_response(filename="export.xlsx", file_bytes=b"PK\x03\x04fake"):
    return FakeResponse(200, {
        "status": 200,
        "data": [{"filename": filename,
                  "data": base64.b64encode(file_bytes).decode()}],
    })


def test_xlsx_payload_unit():
    section("_build_xlsx_payload — CMD body shape (contract)")
    export_request = {"columns": [], "parameters": {}, "dataset": {}}
    p = _build_xlsx_payload(5, export_request)
    check("object.name == exports", p["object"]["name"] == "exports")
    check("object.id == 4", p["object"]["id"] == 4)
    check("command.name == reportToXlsx",
          p["command"]["name"] == "reportToXlsx")
    check("command.id == report_id", p["command"]["id"] == 5)
    check("export section is top-level passthrough",
          p["export"] is export_request)
    check("data == []", p["data"] == [])
    check("options == []", p["options"] == [])


async def test_xlsx_full_path(tmp):
    section("component_xlsx — payload sent via raw_post")
    client = FakeClient(report=make_report(),
                        xlsx_response=make_xlsx_response())
    r = await export_component_to_xlsx(
        client, 5, 0, output_dir=tmp, filename="t_xlsx")
    check("success is True", r.get("success") is True, str(r))
    check("exactly one raw_post sent", len(client.raw_posts) == 1)

    post = client.raw_posts[0]
    check("url targets /exports", post["url"].endswith("/exports"), post["url"])
    check("Authorization header present",
          post["headers"].get("Authorization") == "Bearer fake-token")

    payload = post["json"]
    check("payload object == {name: exports, id: 4}",
          payload.get("object") == {"name": "exports", "id": 4})
    check("payload command == {name: reportToXlsx, id: 5}",
          payload.get("command") == {"name": "reportToXlsx", "id": 5})
    exp = payload.get("export", {})
    check("export.columns built from component axes",
          isinstance(exp.get("columns"), list) and len(exp["columns"]) == 2)
    check("export.dataset.dataset_id == 2",
          exp.get("dataset", {}).get("dataset_id") == 2)
    check("export.report_id == 5", exp.get("report_id") == 5)
    check("payload data/options are empty lists",
          payload.get("data") == [] and payload.get("options") == [])

    # No api_call with illegal kwargs happened: only reports/get was made
    check("api_call used only for reports/get",
          client.api_calls == [("reports", "get", 5)])

    path = Path(r.get("saved_path", ""))
    check("xlsx file written", path.exists())
    check("file bytes decoded from base64",
          path.read_bytes() == b"PK\x03\x04fake")
    check("file_size reported", r.get("file_size") == len(b"PK\x03\x04fake"))


async def test_xlsx_http_error(tmp):
    section("component_xlsx — HTTP/API errors → envelope, no crash")
    client = FakeClient(report=make_report(),
                        xlsx_response=FakeResponse(500, {}))
    r = await export_component_to_xlsx(client, 5, 0, output_dir=tmp)
    check("HTTP 500 → success False", r.get("success") is False)
    check("error mentions HTTP 500", "500" in r.get("error", ""))
    check("hint present", bool(r.get("hint")))

    client = FakeClient(
        report=make_report(),
        xlsx_response=FakeResponse(200, {"status": 400, "message": "bad export"}))
    r = await export_component_to_xlsx(client, 5, 0, output_dir=tmp)
    check("body status 400 → success False", r.get("success") is False)
    check("error carries backend message", r.get("error") == "bad export")


async def test_dispatcher_envelope(tmp):
    section("Dispatcher: raw exceptions wrapped into {success: False, error, hint}")
    client = FakeClient(report=make_report(),
                        recordset_response=RuntimeError("connection dropped"))
    r = await export_operations(
        client, "component_csv", report_id=5, component_idx=0, output_dir=tmp)
    check("component_csv exception → success False (not raised)",
          r.get("success") is False, str(r))
    check("error + hint present",
          bool(r.get("error")) and bool(r.get("hint")))

    class BoomClient(FakeClient):
        async def raw_post(self, url, *, json=None, headers=None, timeout=30.0):
            raise RuntimeError("network down")

    client = BoomClient(report=make_report())
    r = await export_operations(
        client, "component_xlsx", report_id=5, component_idx=0, output_dir=tmp)
    check("component_xlsx exception → success False (not raised)",
          r.get("success") is False, str(r))
    check("error + hint present",
          bool(r.get("error")) and bool(r.get("hint")))

    # require() guard still intact
    r = await export_operations(None, "component_csv")
    check("missing params → require() envelope",
          r.get("success") is False and set(r.get("missing", [])) ==
          {"report_id", "component_idx"})


async def main():
    with tempfile.TemporaryDirectory(prefix="modusbi_export_test_") as tmp:
        await test_csv_list_response(tmp)
        await test_csv_dict_response(tmp)
        await test_csv_error_and_empty(tmp)
        await test_csv_limit(tmp)
        test_xlsx_payload_unit()
        await test_xlsx_full_path(tmp)
        await test_xlsx_http_error(tmp)
        await test_dispatcher_envelope(tmp)

    print(f"\n===\nResult: {ok} OK, {fail} FAIL")
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
