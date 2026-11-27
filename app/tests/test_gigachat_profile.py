"""Behavior tests through public MCP tools, with a separate SQL/data oracle."""
import copy
import json
import sqlite3
import asyncio
from collections import Counter
from types import SimpleNamespace

import pytest
from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ToolError

from app.core.security import SecurityMode, get_security_mode, resolve_effective_mode, set_security_mode
from app.tools.gigachat_models import Metric, DashboardComponent
from app.tools.gigachat_profile import META, metric_sql, layout_issues, build
from app.tools.gigachat_tools import register_gigachat_tools
from app.tools.builders import COMPONENT_TYPE_MAP


class Portal:
    def __init__(self):
        self.instance = SimpleNamespace(name="fixture")
        self.calls = Counter()
        self.reports = {42: {"ID": 42, "name": "fixture", "caption": "Fixture", "groupID": 1,
                            "grid": {"components": {}, "layouts": {}}, "globalFilters": {}, "options": {"CSStext": "/* preserved */"}}}
        self.fields = [{"name": n, "alias": n, "type": t} for n, t in [("customer", "string"), ("plan", "number"), ("actual", "number"), ("zero", "number"), ("html", "string")]]
        self.db = sqlite3.connect(":memory:")
        self.db.execute("CREATE TABLE source(customer TEXT, plan REAL, actual REAL, zero REAL, html TEXT)")
        self.db.executemany("INSERT INTO source VALUES(?,?,?,?,?)", [("А", 100, 100, 0, "<p>A</p>"), ("Б", 900, 450, 0, "<p>B</p>")])
        self.db.create_function("TO_CHAR", 2, self.to_char)
        self.fail_recordsets = False
        self.drop_write = False
        self.lose_write_response = False
        self.fail_readback = False
        self.lose_create_response = False

    @staticmethod
    def to_char(value, picture):
        if value is None:
            return None
        decimal_mark = "D" if "D" in picture else "."
        decimals = len(picture.split(decimal_mark)[1]) if decimal_mark in picture else 0
        return format(value, ("," if "G" in picture or "," in picture else "") + f".{decimals}f")

    async def api_call(self, entity, action, object_id=None, data=None):
        await asyncio.sleep(0)  # Exercise interleaving, not synchronous fake IO.
        self.calls[(entity, action)] += 1
        if entity == "reports" and action == "get":
            if self.fail_readback and self.calls[("reports", "update")]:
                raise ConnectionError("readback unavailable")
            return {"status": 200, "data": [copy.deepcopy(self.reports[object_id])]}
        if entity == "reports" and action == "update":
            if not self.drop_write:
                self.reports[object_id] = copy.deepcopy(data[0])
            if self.lose_write_response:
                raise ConnectionError("response lost after commit")
            return {"status": 200}
        if entity == "reports" and action == "list":
            return {"status": 200, "data": list(copy.deepcopy(self.reports).values())}
        if entity == "reports" and action == "create":
            created = copy.deepcopy(data[0])
            created["ID"] = max(self.reports) + 1
            self.reports[created["ID"]] = created
            if self.lose_create_response:
                raise ConnectionError("create committed, response lost")
            return {"status": 200, "data": [created]}
        if entity == "reportgroups":
            return {"status": 200, "data": [{"ID": 1, "name": "Тестовая группа"}]}
        if entity == "components":
            return {"status": 200, "data": [{"type": name, "caption": name} for name in COMPONENT_TYPE_MAP]}
        if entity == "datasets" and action == "list":
            return {"status": 200, "data": [{"ID": 1, "name": "fixture", "caption": "Тест", "query": "DO_NOT_RETURN_SQL"}]}
        if entity == "datasets":
            return {"status": 200, "data": [{"ID": object_id, "name": "fixture", "fields": copy.deepcopy(self.fields)}]}
        if entity == "recordsets" and action == "create":
            if self.fail_recordsets:
                return {"status": 400, "data": []}
            q = data[0]
            columns = []
            for f in q.get("select", []):
                expression = f.get("calc") or '"' + f["name"] + '"'
                if f.get("aggr"):
                    expression = f["aggr"].upper() + "(" + expression + ")"
                columns.append(expression + ' AS "' + f["alias"] + '"')
            sql = "SELECT " + (", ".join(columns) if columns else "*") + " FROM source"
            parameters, conditions = [], []
            for f in q.get("where", []):
                parameters += f["values"]
                conditions.append('"' + f["name"] + '" IN (' + ",".join("?" for _ in f["values"]) + ")")
            if conditions:
                sql += " WHERE " + " AND ".join(conditions)
            if q.get("group"):
                sql += " GROUP BY " + ",".join(f.get("calc") or '"' + f["name"] + '"' for f in q["group"])
            sql += " LIMIT " + str(q.get("limit", 20))
            cursor = self.db.execute(sql, parameters)
            names = [x[0] for x in cursor.description]
            return {"status": 200, "data": [dict(zip(names, row)) for row in cursor.fetchall()]}
        raise AssertionError((entity, action))


@pytest.fixture
def fixture():
    previous = get_security_mode()
    set_security_mode(SecurityMode.READWRITE)
    portal, mcp = Portal(), FastMCP("test")
    auth = []

    async def client():
        auth.append(True)
        return portal

    register_gigachat_tools(mcp, client)
    yield portal, mcp, auth
    portal.db.close()
    set_security_mode(previous)


async def call(mcp, tool_name, **kwargs):
    result = await mcp.call_tool(tool_name, kwargs)
    return result[1] if isinstance(result, tuple) else json.loads(result[0].text)


async def kpi(mcp, key="completion", **metric):
    return await call(mcp, "giga_set_kpi", report_id=42, key=key, title="Выполнение", dataset_id=1,
                      metric={"label": "Выполнение", "kind": "ratio_of_sums", "numerator": "actual", "denominator": "plan", "format": "percent", **metric})


@pytest.mark.asyncio
async def test_public_kpi_repeated_and_after_reconnect(fixture):
    portal, mcp, _ = fixture
    first, second = await kpi(mcp), await kpi(mcp)
    assert first["success"] and first["changed"]
    assert second["success"] and second["changed"] is False
    assert portal.calls[("reports", "update")] == 1
    assert len(portal.reports[42]["grid"]["components"]) == 1
    assert len(portal.reports[42]["grid"]["layouts"]["lg"]) == 1
    assert list(first["preview_rows"]["completion"][0].values()) == ["55%"]
    fresh = FastMCP("fresh")

    async def client():
        return portal

    register_gigachat_tools(fresh, client)
    assert (await kpi(fresh))["changed"] is False


@pytest.mark.asyncio
async def test_field_display_changes_presentation_and_preserves_binding(fixture):
    portal, mcp, _ = fixture
    portal.fields[0]["type"] = "date"
    portal.db.execute("UPDATE source SET customer=CASE customer WHEN 'А' THEN '2026-03-01' ELSE '2026-01-01' END")
    chart = {"key": "by_month", "kind": "bar", "title": "По месяцам", "dataset_id": 1,
             "category": "customer", "metrics": [{"label": "План", "field": "plan"}]}
    assert (await call(mcp, "giga_upsert_components", report_id=42, components=[chart]))["success"]
    args = {"report_id": 42, "key": "by_month", "field": "customer", "label": "Месяц", "order": "asc", "date_format": "MMM YYYY"}
    result = await call(mcp, "giga_set_field_display", **args)
    assert result["success"] and result["changed"]
    assert not (await call(mcp, "giga_set_field_display", **args))["changed"]
    assert (await call(mcp, "giga_upsert_components", report_id=42, components=[{**chart, "title": "Новый заголовок"}]))["success"]
    cfg = portal.reports[42]["grid"]["components"]["0"]["config"]
    for axes in (cfg["axes"], cfg["axesDefault"]):
        date_field = next(a for a in axes if a["type"] == "categories")["fields"][0]
        assert (date_field["name"], date_field["alias"], date_field["order"]) == ("customer", "Месяц", "asc")
    assert cfg["dateFormat"] == "MMM YYYY"
    assert not (await call(mcp, "giga_inspect_report", report_id=42, include_data=False))["issues"]
    before = portal.calls[("reports", "update")]
    assert not (await call(mcp, "giga_set_field_display", **{**args, "field": "plan"}))["success"]
    assert portal.calls[("reports", "update")] == before


@pytest.mark.asyncio
async def test_chart_axis_title_leaves_component_and_field_names_intact(fixture):
    portal, mcp, _ = fixture
    portal.fields[0]["type"] = "date"
    portal.db.execute("UPDATE source SET customer=CASE customer WHEN 'А' THEN '2026-03-01' ELSE '2026-01-01' END")
    chart = {"key":"by_month", "kind":"bar", "title":"По месяцам", "dataset_id":1, "category":"customer",
             "metrics":[{"label":"План", "field":"plan"}]}
    assert (await call(mcp, "giga_upsert_components", report_id=42, components=[chart]))["success"]
    args = {"report_id":42, "key":"by_month", "axis":"categories", "title":"Месяц отчёта", "order":"desc", "date_format":"MMMM YYYY"}
    first = await call(mcp, "giga_set_chart_axis", **args)
    assert first["success"] and first["changed"]
    assert not (await call(mcp, "giga_set_chart_axis", **args))["changed"]
    assert (await call(mcp, "giga_upsert_components", report_id=42, components=[{**chart,"title":"Название графика"}]))["success"]
    cfg = portal.reports[42]["grid"]["components"]["0"]["config"]
    assert cfg["caption"] == "Название графика" and cfg["dateFormat"] == "MMMM YYYY"
    for axes in (cfg["axes"], cfg["axesDefault"]):
        axis = next(a for a in axes if a["type"] == "categories")
        assert axis["title"] == "Месяц отчёта" and axis["showtitle"]
        assert (axis["fields"][0]["name"],axis["fields"][0]["alias"],axis["fields"][0]["order"]) == ("customer","customer","desc")
    assert not (await call(mcp, "giga_set_chart_axis", **{**args,"axis":"values"}))["success"]


@pytest.mark.asyncio
async def test_update_existing_kpi_preserves_title_filter_and_layout(fixture):
    portal, mcp, _ = fixture
    args = {"report_id": 42, "key": "plan", "title": "План за период", "dataset_id": 1,
            "metric": {"label": "План", "kind": "sum", "field": "plan", "format": "rubles", "decimals": 2}}
    assert (await call(mcp, "giga_set_kpi", **args))["success"]
    assert (await call(mcp, "giga_bind_report_filter", report_id=42, key="customer", label="Заказчик",
                       bindings=[{"dataset_id": 1, "field": "customer"}]))["success"]
    assert (await call(mcp, "giga_select_filter", report_id=42, key="customer", values=["Б"]))["success"]
    before = copy.deepcopy(portal.reports[42])
    result = await call(mcp, "giga_update_kpi", report_id=42, key="plan", field="actual", aggregation="avg")
    assert result["success"] and result["changed"]
    after = portal.reports[42]
    assert before["grid"]["layouts"] == after["grid"]["layouts"]
    assert before["globalFilters"] == after["globalFilters"]
    assert before["grid"]["components"]["1"] == after["grid"]["components"]["1"]
    cfg = after["grid"]["components"]["0"]["config"]
    assert cfg["caption"] == "План за период"
    metric = cfg[META]["spec"]["metrics"][0]
    assert (metric["field"], metric["kind"], metric["format"], metric["decimals"]) == ("actual", "avg", "rubles", 2)
    assert cfg["subtitle__ru"] == "Среднее · actual"
    assert next(v for v in cfg["visuals"] if v["anchor"] == "subcaption")["visible"] is True
    assert not (await call(mcp, "giga_update_kpi", report_id=42, key="plan", aggregation="avg"))["changed"]
    assert not (await call(mcp, "giga_update_kpi", report_id=42, key="plan", field="customer"))["success"]


@pytest.mark.asyncio
async def test_filter_supports_visible_multi_selection_without_duplicates(fixture):
    portal, mcp, _ = fixture
    args = dict(report_id=42, key="customer", label="Заказчик", bindings=[{"dataset_id": 1, "field": "customer"}])
    assert (await call(mcp, "giga_bind_report_filter", **args))["success"]
    assert (await call(mcp, "giga_select_filter", report_id=42, key="customer", values=["А", "Б", "А"]))["success"]
    before_read = copy.deepcopy(portal.reports[42])
    values = await call(mcp, "giga_list_filter_values", report_id=42, key="customer")
    assert values == {"success": True, "key": "customer", "label": "Заказчик", "values": ["А", "Б"]}
    assert portal.reports[42] == before_read
    assert (await call(mcp, "giga_bind_report_filter", **args))["success"]
    report = portal.reports[42]
    cfg = report["grid"]["components"]["0"]["config"]
    assert cfg["multipleChoice"] is True and cfg["selectedValue"] == ["А", "Б"]
    assert report["globalFilters"]["Заказчик"]["selected"] == ["А", "Б"]


@pytest.mark.asyncio
async def test_filter_subset_reset_and_rename_preserve_selection(fixture):
    portal, mcp, _ = fixture
    await kpi(mcp)
    args = dict(report_id=42, key="customer", label="Заказчик", bindings=[{"dataset_id": 1, "field": "customer"}])
    assert (await call(mcp, "giga_bind_report_filter", **args))["success"]
    assert (await call(mcp, "giga_select_filter", report_id=42, key="customer", values=["Б"]))["success"]
    selected = await call(mcp, "giga_inspect_report", report_id=42)
    assert list(selected["data"]["completion"]["rows"][0].values()) == ["50%"]
    args["label"] = "Клиент"
    assert (await call(mcp, "giga_bind_report_filter", **args))["success"]
    report = portal.reports[42]
    assert "Заказчик" not in report["globalFilters"]
    assert report["globalFilters"]["Клиент"]["selected"] == ["Б"]
    for c in report["grid"]["components"].values():
        assert not any(f.get("alias") == "Заказчик" for a in c["config"]["axes"] for f in a["fields"])
    assert (await call(mcp, "giga_select_filter", report_id=42, key="customer", values=[]))["success"]
    reset = await call(mcp, "giga_inspect_report", report_id=42)
    assert list(reset["data"]["completion"]["rows"][0].values()) == ["55%"]
    assert report is not portal.reports[42]
    assert portal.reports[42]["globalFilters"]["Клиент"]["selected"] == []


@pytest.mark.asyncio
async def test_new_components_auto_bind_and_rebinding_is_idempotent(fixture):
    portal, mcp, _ = fixture
    await kpi(mcp)
    args = dict(report_id=42, key="customer", label="Заказчик", bindings=[{"dataset_id": 1, "field": "customer"}])
    await call(mcp, "giga_bind_report_filter", **args)
    before = portal.calls[("reports", "update")]
    assert (await call(mcp, "giga_bind_report_filter", **args))["changed"] is False
    assert portal.calls[("reports", "update")] == before
    await kpi(mcp, key="second")
    for c in portal.reports[42]["grid"]["components"].values():
        filters = next(a["fields"] for a in c["config"]["axes"] if a["type"] == "filters")
        assert len(filters) == 1 and filters[0]["global"]


@pytest.mark.asyncio
async def test_bad_field_query_and_value_fail_before_write(fixture):
    portal, mcp, _ = fixture
    invalid = await kpi(mcp, numerator="unknown")
    assert invalid["success"] is False
    assert portal.calls[("reports", "update")] == 0
    portal.fail_recordsets = True
    assert (await kpi(mcp))["success"] is False
    assert (await call(mcp, "giga_read_dataset", dataset_id=1))["success"] is False
    assert portal.calls[("reports", "update")] == 0
    portal.fail_recordsets = False
    await kpi(mcp)
    await call(mcp, "giga_bind_report_filter", report_id=42, key="customer", label="Заказчик", bindings=[{"dataset_id": 1, "field": "customer"}])
    before = portal.calls[("reports", "update")]
    assert (await call(mcp, "giga_select_filter", report_id=42, key="customer", values=["nonexistent"]))["success"] is False
    assert portal.calls[("reports", "update")] == before


@pytest.mark.asyncio
async def test_silent_server_ignore_and_lost_reply_not_success(fixture):
    portal, mcp, _ = fixture
    portal.drop_write = True
    ignored = await kpi(mcp)
    assert ignored["success"] is False and ignored["changed"] is False
    assert ignored["write_attempted"] is True
    assert ignored["configuration_verified"] is False
    portal.drop_write, portal.lose_write_response = False, True
    ambiguous = await kpi(mcp)
    assert ambiguous["success"] is False and ambiguous["changed"] is None
    assert ambiguous["commit_state"] == "unknown"
    portal.lose_write_response = False
    recovered = await kpi(mcp)
    assert recovered["success"] and recovered["changed"] is False
    assert len(portal.reports[42]["grid"]["components"]) == 1


@pytest.mark.asyncio
async def test_write_succeeded_readback_failed_is_explicit(fixture):
    portal, mcp, _ = fixture
    portal.fail_readback = True
    result = await kpi(mcp)
    assert result["success"] is False and result["changed"] is None
    assert result["commit_state"] == "acknowledged_readback_failed"


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", ["readonly", "readwrite", "demo"])
@pytest.mark.parametrize("ceiling", ["readonly", "readwrite", "demo"])
async def test_security_public_entries_all_mode_ceiling_pairs(fixture, mode, ceiling):
    portal, mcp, auth = fixture
    effective = resolve_effective_mode(mode, ceiling)
    set_security_mode(SecurityMode(effective))
    if effective == "readwrite":
        assert (await kpi(mcp))["success"]
        assert portal.calls[("reports", "update")] == 1
        return
    operations = [
        ("giga_create_report", dict(name="new_report", caption="Новый", group_id=1)),
        ("giga_set_kpi", dict(report_id=42, key="plan", title="План", dataset_id=1, metric={"label": "План", "field": "plan"})),
        ("giga_upsert_components", dict(report_id=42, components=[{"key": "header", "kind": "text", "title": "Шапка", "text": "<p>Шапка</p>", "category": ""}])),
        ("giga_set_table", dict(report_id=42, key="table", title="Таблица", dataset_id=1, columns=[{"label": "Заказчик", "field": "customer", "format": "text"}])),
        ("giga_set_header", dict(report_id=42, key="header", title="Отчёт", period="I квартал")),
        ("giga_set_rich_text", dict(report_id=42, key="conclusions", title="Выводы", dataset_id=1, field="html")),
        ("giga_bind_report_filter", dict(report_id=42, key="customer", label="Заказчик", bindings=[{"dataset_id": 1, "field": "customer"}])),
        ("giga_select_filter", dict(report_id=42, key="customer", values=[])),
        ("giga_arrange_report", dict(report_id=42, placements=[{"key": "plan", "row": 1}])),
        ("giga_remove_components", dict(report_id=42, keys=["plan"]))]
    operations.append(("giga_apply_dashboard_preset", dict(report_id=42)))
    operations += [("giga_set_bar_options", dict(report_id=42, key="bar", horizontal=True, stacked=True)),
                   ("giga_set_table_rules", dict(report_id=42, key="table", field="actual", rules=[]))]
    operations.append(("giga_set_visualization", dict(report_id=42, visualization={"key": "native", "component_type": "HsAreaAMchartsChart", "title": "Факт", "dataset_id": 1, "axes": []})))
    operations += [("giga_set_tree",dict(report_id=42,key="tree",title="Дерево",dataset_id=1,node_field="plan",parent_field="zero",label_field="customer",size_field="actual",color_field="html")),
                   ("giga_set_map",dict(report_id=42,key="map",title="Карта",dataset_id=1,point_field="customer",latitude_field="plan",longitude_field="actual",metric={"label":"Сумма","field":"zero","kind":"sum"})),
                   ("giga_set_tilemap",dict(report_id=42,key="tilemap",title="Регионы",dataset_id=1,region_field="customer",metric={"label":"Сумма","field":"actual","kind":"sum"}))]
    for name, kwargs in operations:
        result = await call(mcp, name, **kwargs)
        assert result["success"] is False and result["error_code"] == "SECURITY_MODE"
    assert not auth
    assert portal.calls[("reports", "update")] == 0


@pytest.mark.asyncio
async def test_layout_many_components_and_data_fields_are_complete(fixture):
    portal, mcp, _ = fixture
    for i in range(6):
        assert (await kpi(mcp, key="metric_" + str(i)))["success"]
    report = portal.reports[42]
    assert not layout_issues(report)
    for bp in ("hd", "lg"):
        assert len({x["y"] for x in report["grid"]["layouts"][bp]}) == 1
    fields = await call(mcp, "giga_read_dataset", dataset_id=1, limit=1)
    assert fields["fields_count"] == len(portal.fields)
    assert fields["fields"][-1]["name"] == "html"
    assert fields["truncated"] is True


@pytest.mark.asyncio
async def test_zero_percent_and_zero_plan_are_not_hidden(fixture):
    portal, mcp, _ = fixture
    zero = await kpi(mcp, numerator="zero")
    assert list(zero["preview_rows"]["completion"][0].values()) == ["0%"]
    undefined = await kpi(mcp, denominator="zero")
    assert list(undefined["preview_rows"]["completion"][0].values()) == ["н/д"]
    portal.db.execute("DELETE FROM source")
    empty = await kpi(mcp)
    assert list(empty["preview_rows"]["completion"][0].values()) == ["н/д"]


def test_ratio_sql_independent_weighted_oracle():
    connection = sqlite3.connect(":memory:")
    connection.execute("CREATE TABLE source(plan REAL, actual REAL)")
    connection.executemany("INSERT INTO source VALUES(?,?)", [(100, 100), (900, 450)])
    expression = metric_sql(Metric(label="Выполнение", kind="ratio_of_sums", numerator="actual", denominator="plan"))
    assert connection.execute("SELECT " + expression + " FROM source").fetchone()[0] == pytest.approx(0.55)
    connection.close()


@pytest.mark.asyncio
async def test_wire_schemas_no_refs_unions_or_json_encoded_objects(fixture):
    _, mcp, _ = fixture
    tools = await mcp.list_tools()
    assert len(tools) == 29
    for tool in tools:
        wire = json.dumps(tool.inputSchema, ensure_ascii=False)
        assert '"$ref"' not in wire and '"anyOf"' not in wire
        assert "description" in wire
    upsert = next(t for t in tools if t.name == "giga_upsert_components")
    assert upsert.inputSchema["properties"]["components"]["type"] == "array"
    assert "table" not in upsert.inputSchema["properties"]["components"]["items"]["properties"]["kind"]["enum"]
    table = next(t for t in tools if t.name == "giga_set_table")
    assert "kind" not in table.inputSchema["properties"]["columns"]["items"]["properties"]


@pytest.mark.asyncio
async def test_same_keys_in_different_reports_do_not_collide(fixture):
    portal, mcp, _ = fixture
    portal.reports[43] = copy.deepcopy(portal.reports[42])
    portal.reports[43]["ID"] = 43
    await kpi(mcp)
    await call(mcp, "giga_set_kpi", report_id=43, key="completion", title="Другой", dataset_id=1, metric={"label": "План", "kind": "sum", "field": "plan"})
    assert len(portal.reports[42]["grid"]["components"]) == len(portal.reports[43]["grid"]["components"]) == 1
    assert portal.reports[42]["grid"]["components"]["0"]["config"]["caption"] != portal.reports[43]["grid"]["components"]["0"]["config"]["caption"]


@pytest.mark.asyncio
async def test_inspect_rejects_missing_layout_and_duplicate_keys(fixture):
    portal, mcp, _ = fixture
    await kpi(mcp)
    saved = copy.deepcopy(portal.reports[42])
    portal.reports[42]["grid"]["layouts"] = {}
    missing = await call(mcp, "giga_inspect_report", report_id=42)
    assert missing["checks_passed"] is False
    assert any("missing layout" in i for i in missing["issues"])
    portal.reports[42] = saved
    portal.reports[42]["grid"]["components"]["1"] = copy.deepcopy(saved["grid"]["components"]["0"])
    duplicates = await call(mcp, "giga_inspect_report", report_id=42)
    assert duplicates["checks_passed"] is False
    assert len(duplicates["data"]) == 2
    assert any("duplicate stable" in i for i in duplicates["issues"])


@pytest.mark.asyncio
async def test_concurrent_same_key_creates_once(fixture):
    portal, mcp, _ = fixture
    a, b = await asyncio.gather(kpi(mcp), kpi(mcp))
    assert a["success"] and b["success"]
    assert portal.calls[("reports", "update")] == 1
    assert len(portal.reports[42]["grid"]["components"]) == 1


@pytest.mark.asyncio
async def test_discovery_and_create_need_no_external_ids(fixture):
    portal, mcp, _ = fixture
    found = await call(mcp, "giga_find_datasets", names=["fixture"])
    assert found["exact_match"] and found["items"][0]["dataset_id"] == 1
    assert "DO_NOT_RETURN_SQL" not in json.dumps(found)
    groups = await call(mcp, "giga_list_report_groups")
    assert groups["items"][0]["group_id"] == 1
    args = dict(name="new_report", caption="Новый отчёт", group_id=1)
    created = await call(mcp, "giga_create_report", **args)
    repeated = await call(mcp, "giga_create_report", **args)
    assert created["success"] and repeated["success"]
    assert created["report_id"] == repeated["report_id"]
    assert repeated["changed"] is False
    assert portal.calls[("reports", "create")] == 1


def test_chart_visual_settings_survive_compilation():
    spec = DashboardComponent(key="bars", kind="bar", title="Оплата", dataset_id=1,
        category="customer", horizontal=True, stacked=True,
        metrics=[Metric(label="Сумма", field="actual"), Metric(label="План", field="actual")])
    fields = {n: {"type": t} for n, t in [("customer", "string"), ("html", "string"), ("actual", "number")]}
    cfg = build(spec, 42, fields)["config"]
    assert cfg["orientation"] == "h" and cfg["groupMode"] == "stack"
    assert cfg["legend"]["position"] == "bottom-center"
    assert next(a for a in cfg["axes"] if a["type"] == "values")["selectedFieldIndex"] == -2


def test_native_chart_keeps_target_and_color_value_fields():
    fields = {n: {"type": t} for n, t in [("customer", "string"), ("actual", "number"), ("plan", "number")]}
    line = DashboardComponent(key="line", kind="line", title="Факт и план", dataset_id=1, category="customer",
        metrics=[Metric(label="Факт", kind="ratio_of_sums", numerator="actual", denominator="plan", format="percent"),
                 Metric(label="План", kind="constant", constant=1, format="percent")])
    cfg = build(line, 42, fields)["config"]
    values = next(a for a in cfg["axes"] if a["type"] == "values")
    assert values["selectedFieldIndex"] == -2 and len(values["fields"]) == 2
    assert cfg["visuals"][1]["anchor"] == values["fields"][1]["id"]
    assert cfg["visuals"][1]["lineMode"] == "dash"
    pie = DashboardComponent(key="pie", kind="donut", title="Статусы", dataset_id=1, category="customer",
        metrics=[Metric(label="Сумма", field="actual")], colors=[{"value": "А", "color": "#328678"}])
    cfg = build(pie, 42, fields)["config"]
    values = next(a for a in cfg["axes"] if a["type"] == "values")
    assert values["selectedFieldIndex"] == -2 and values["fields"][1]["valueType"] == "color"
    assert next(a for a in cfg["axesDefault"] if a["type"] == "values")["fields"] == values["fields"]


@pytest.mark.asyncio
async def test_table_order_and_conditional_cells_use_raw_thresholds(fixture):
    portal, mcp, _ = fixture
    result = await call(mcp, "giga_set_table", report_id=42, key="table", title="Таблица", dataset_id=1,
        columns=[{"label": "Заказчик", "field": "customer", "format": "text"},
            {"label": "Порог", "field": "zero", "cell_rules": [
                {"operator": "gt", "value": 0, "background": "#F7E4E6"}]}])
    assert result["success"], result
    rows = result["preview_rows"]["table"]
    assert all('background:transparent' in next(v for k, v in r.items() if k != "customer") for r in rows)
    assert all('>0</span>' in next(v for k, v in r.items() if k != "customer") for r in rows)
    cfg = portal.reports[42]["grid"]["components"]["0"]["config"]
    assert [c["visibleOrder"] for c in cfg["columns"].values()] == [1, 2]
    assert list(cfg["columns"].values())[1]["isHtml"]


@pytest.mark.asyncio
async def test_concurrent_report_create_is_serialized(fixture):
    portal, mcp, _ = fixture
    args = dict(name="same_report", caption="Новый", group_id=1)
    first, second = await asyncio.gather(call(mcp, "giga_create_report", **args), call(mcp, "giga_create_report", **args))
    assert first["success"] and second["success"] and first["report_id"] == second["report_id"]
    assert portal.calls[("reports", "create")] == 1


@pytest.mark.asyncio
async def test_lost_report_create_response_never_claims_no_change(fixture):
    portal, mcp, _ = fixture
    portal.lose_create_response = True
    result = await call(mcp, "giga_create_report", name="lost_report", caption="Новый", group_id=1)
    assert result["success"] is False and result["changed"] is None
    assert result["commit_state"] == "unknown" and result["error_code"] == "WRITE_NOT_VERIFIED"
    assert any(r["name"] == "lost_report" for r in portal.reports.values())
    portal.lose_create_response = False
    repeated = await call(mcp, "giga_create_report", name="lost_report", caption="Новый", group_id=1)
    assert repeated["success"] and not repeated["changed"]
    assert portal.calls[("reports", "create")] == 1


@pytest.mark.asyncio
async def test_change_visual_kind_preserves_key_and_filter(fixture):
    portal, mcp, _ = fixture
    await kpi(mcp)
    await call(mcp, "giga_bind_report_filter", report_id=42, key="customer", label="Заказчик", bindings=[{"dataset_id": 1, "field": "customer"}])
    result = await call(mcp, "giga_upsert_components", report_id=42, replace_kind=True, components=[{
        "key": "completion", "kind": "bar", "title": "Сравнение", "dataset_id": 1, "category": "customer",
        "metrics": [{"label": "Факт", "field": "actual"}, {"label": "План", "field": "plan"}]}])
    assert result["success"], result
    components = portal.reports[42]["grid"]["components"]
    assert len(components) == 2
    assert components["0"]["config"][META]["kind"] == "bar"
    assert next(a for a in components["0"]["config"]["axes"] if a["type"] == "filters")["fields"][0]["alias"] == "Заказчик"


@pytest.mark.asyncio
async def test_remove_managed_component_preserves_other_components(fixture):
    portal, mcp, _ = fixture
    await kpi(mcp, key="extra")
    await kpi(mcp, key="keep")
    result = await call(mcp, "giga_remove_components", report_id=42, keys=["extra"])
    assert result["success"] and result["changed"]
    assert [c["key"] for c in result["components"]] == ["keep"]
    assert not layout_issues(portal.reports[42])
    again = await call(mcp, "giga_remove_components", report_id=42, keys=["extra"])
    assert again["success"] and not again["changed"]
    await call(mcp, "giga_bind_report_filter", report_id=42, key="customer", label="Заказчик", bindings=[{"dataset_id": 1, "field": "customer"}])
    denied = await call(mcp, "giga_remove_components", report_id=42, keys=["keep", "customer"])
    assert not denied["success"] and len(portal.reports[42]["grid"]["components"]) == 2


@pytest.mark.asyncio
async def test_preset_compacts_layout_without_touching_metrics(fixture):
    portal, mcp, _ = fixture
    await kpi(mcp)
    await call(mcp, "giga_upsert_components", report_id=42, components=[{
        "key": "header", "kind": "text", "title": "Период", "text": "<h3>Отчёт</h3><p>Период</p>", "category": "", "height": 20}])
    original = copy.deepcopy(portal.reports[42]["grid"]["components"]["0"]["config"]["axes"])
    result = await call(mcp, "giga_apply_dashboard_preset", report_id=42)
    assert result["success"] and result["applied_preset"] == "light_dashboard"
    saved = portal.reports[42]
    assert saved["grid"]["components"]["0"]["config"]["axes"] == original
    assert saved["grid"]["components"]["1"]["config"][META]["spec"]["height"] == 3
    assert "/* preserved */" in saved["options"]["CSStext"]
    again = await call(mcp, "giga_apply_dashboard_preset", report_id=42)
    assert again["success"] and not again["changed"]
    await call(mcp, "giga_arrange_report", report_id=42, placements=[{"key": "completion", "row": 1}])
    assert portal.reports[42]["grid"]["components"]["0"]["config"][META]["spec"]["height"] == 5
    style = await call(mcp, "giga_inspect_report", report_id=42, include_style=True, include_data=False)
    assert set(style["style"]["managed_panel_ids"]) == {"panel_0", "panel_1"}


@pytest.mark.asyncio
async def test_header_is_static_escaped_and_idempotent(fixture):
    portal, mcp, _ = fixture
    args = dict(report_id=42, key="header", title="Отчёт <1>", period="I квартал & дата")
    result = await call(mcp, "giga_set_header", **args)
    assert result["success"]
    cfg = portal.reports[42]["grid"]["components"]["0"]["config"]
    assert "&lt;1&gt;" in cfg["description"] and "&amp;" in cfg["description"]
    assert not cfg.get("axes") and cfg[META]["spec"]["height"] == 3
    assert not (await call(mcp, "giga_set_header", **args))["changed"]


@pytest.mark.asyncio
async def test_decimal_percent_does_not_depend_on_database_locale(fixture):
    portal, mcp, _ = fixture

    def russian_to_char(value, picture):
        rendered = Portal.to_char(value, picture)
        return rendered.replace(",", " ").replace(".", ",") if "D" in picture or "G" in picture else rendered

    portal.db.create_function("TO_CHAR", 2, russian_to_char)
    result = await kpi(mcp, decimals=2)
    assert result["success"]
    assert next(iter(result["preview_rows"]["completion"][0].values())) == "55,00%"


@pytest.mark.asyncio
async def test_narrow_bar_options_preserve_metrics(fixture):
    portal, mcp, _ = fixture
    await call(mcp, "giga_upsert_components", report_id=42, components=[{
        "key": "bar", "kind": "bar", "title": "Факт", "dataset_id": 1, "category": "customer", "metrics": [{"label": "Факт", "field": "actual"}]}])
    original = copy.deepcopy(portal.reports[42]["grid"]["components"]["0"]["config"][META]["spec"])
    cfg = portal.reports[42]["grid"]["components"]["0"]["config"]
    local = {"id": "local_customer", "name": "customer", "alias": "Локальный", "type": "string", "datasetId": 1}
    next(a for a in cfg["axes"] if a["type"] == "filters")["fields"] = [local]
    cfg["axesDefault"] = copy.deepcopy(cfg["axes"])
    cfg["filters"] = {"customer": {"selected": ["Б"], "nonglobal": True}}
    cfg["legend"]["position"] = "top-center"
    original_axes = copy.deepcopy(cfg["axes"])
    original_layout = copy.deepcopy(portal.reports[42]["grid"]["layouts"])
    result = await call(mcp, "giga_set_bar_options", report_id=42, key="bar", horizontal=True, stacked=True)
    assert result["success"]
    saved = portal.reports[42]["grid"]["components"]["0"]["config"][META]["spec"]
    assert saved["metrics"] == original["metrics"] and saved["horizontal"] and saved["stacked"]
    cfg = portal.reports[42]["grid"]["components"]["0"]["config"]
    assert cfg["axes"] == original_axes and cfg["legend"]["position"] == "top-center"
    assert cfg["filters"]["customer"]["selected"] == ["Б"]
    assert portal.reports[42]["grid"]["layouts"] == original_layout
    assert len(result["preview_rows"]["bar"]) == 1
    assert not (await call(mcp, "giga_set_bar_options", report_id=42, key="bar", horizontal=True, stacked=True))["changed"]


@pytest.mark.asyncio
async def test_narrow_table_rules_preserve_columns(fixture):
    portal, mcp, _ = fixture
    await call(mcp, "giga_set_table", report_id=42, key="table", title="Факт", dataset_id=1,
        columns=[{"label": "Заказчик", "field": "customer", "format": "text"}, {"label": "Факт", "field": "actual"}])
    cfg = portal.reports[42]["grid"]["components"]["0"]["config"]
    customer_id = next(a for a in cfg["axes"] if a["type"] == "values")["fields"][0]["id"]
    cfg["columns"][customer_id]["width"] = 321
    cfg["filters"] = {"customer": {"selected": ["Б"], "nonglobal": True}}
    next(a for a in cfg["axes"] if a["type"] == "filters")["fields"] = [{"id": "local", "name": "customer", "type": "string", "datasetId": 1}]
    result = await call(mcp, "giga_set_table_rules", report_id=42, key="table", field="actual",
        rules=[{"operator": "gt", "value": 0, "background": "#EAF4F0"}])
    assert result["success"]
    saved = portal.reports[42]["grid"]["components"]["0"]["config"][META]["spec"]
    assert [m["field"] for m in saved["metrics"]] == ["customer", "actual"]
    assert all("#EAF4F0" in next(v for k,v in r.items() if k != "customer") for r in result["preview_rows"]["table"])
    cfg = portal.reports[42]["grid"]["components"]["0"]["config"]
    assert cfg["columns"][customer_id]["width"] == 321 and cfg["filters"]["customer"]["selected"] == ["Б"]
    assert len(result["preview_rows"]["table"]) == 1




@pytest.mark.asyncio
async def test_table_merge_preserves_columns_ids_rules_widths_and_local_filter(fixture):
    portal, mcp, _ = fixture
    args = dict(report_id=42, key="table", title="Таблица", dataset_id=1)
    await call(mcp, "giga_set_table", **args, columns=[{"field": "customer", "label": "Заказчик", "format": "text"},
        {"field": "actual", "label": "Факт", "decimals": 2, "cell_rules": [{"operator": "gt", "value": 0, "background": "#EAF4F0"}]}])
    cfg = portal.reports[42]["grid"]["components"]["0"]["config"]
    cfg["filters"] = {"customer": {"selected": ["Б"]}}
    next(a for a in cfg["axes"] if a["type"] == "filters")["fields"] = [{"id": "local", "name": "customer", "type": "string", "datasetId": 1}]
    customer_id = next(iter(cfg["columns"]))
    cfg["columns"][customer_id]["width"] = 321
    result = await call(mcp, "giga_set_table", **args, columns=[{"field": "plan", "label": "План"}, {"field": "actual", "label": "Факт"}])
    assert result["success"], result
    cfg = portal.reports[42]["grid"]["components"]["0"]["config"]
    metrics = cfg[META]["spec"]["metrics"]
    assert [m["field"] for m in metrics] == ["customer", "actual", "plan"]
    assert metrics[1]["decimals"] == 2 and metrics[1]["cell_rules"]
    assert next(iter(cfg["columns"])) == customer_id and cfg["columns"][customer_id]["width"] == 321
    assert cfg["filters"]["customer"]["selected"] == ["Б"]
    assert len(result["preview_rows"]["table"]) == 1
    repeat = await call(mcp, "giga_set_table", **args, columns=[{"field": "plan", "label": "План"}, {"field": "actual", "label": "Факт"}])
    assert repeat["success"] and not repeat["changed"]


@pytest.mark.asyncio
async def test_table_explicit_replace_and_duplicate_fields(fixture):
    portal, mcp, _ = fixture
    args = dict(report_id=42, key="table", title="Таблица", dataset_id=1)
    await call(mcp, "giga_set_table", **args, columns=[{"field": "actual", "label": "Факт"}, {"field": "plan", "label": "План"}])
    assert (await call(mcp, "giga_set_table", **args, columns_mode="replace", columns=[{"field": "plan", "label": "План"}]))["success"]
    before = copy.deepcopy(portal.reports[42])
    with pytest.raises(ToolError, match="DUPLICATE_TABLE_FIELD"):
        await call(mcp, "giga_set_table", **args, columns=[{"field": "plan", "label": "План"}, {"field": "plan", "label": "Факт"}])
    assert portal.reports[42] == before








@pytest.mark.asyncio
async def test_inspect_detects_native_formula_drift_without_trusting_meta(fixture):
    portal, mcp, _ = fixture
    await kpi(mcp)
    assert (await call(mcp, "giga_inspect_report", report_id=42))["checks_passed"]
    cfg = portal.reports[42]["grid"]["components"]["0"]["config"]
    next(a for a in cfg["axes"] if a["type"] == "values")["fields"][0]["calc"] = "123"
    result = await call(mcp, "giga_inspect_report", report_id=42)
    assert not result["checks_passed"] and any("NATIVE_DEFINITION_DRIFT" in issue for issue in result["issues"])


@pytest.mark.asyncio
async def test_independent_source_probe_weighted_ratio_filter_null_and_no_writes(fixture):
    portal, mcp, _ = fixture
    set_security_mode(SecurityMode.READONLY)
    args = dict(dataset_id=1, metrics=[{"label": "Доля", "kind": "ratio_of_sums", "numerator": "actual", "denominator": "plan", "format": "percent"}])
    total = await call(mcp, "giga_query_dataset", **args)
    assert total["success"] and total["rows"][0]["metric_0"] == pytest.approx(.55)
    assert total["rows"][0]["source_row_count"] == 2
    selected = await call(mcp, "giga_query_dataset", **args, filters=[{"field": "customer", "values": ["Б"]}])
    assert selected["rows"][0]["metric_0"] == pytest.approx(.5)
    grouped = await call(mcp, "giga_query_dataset", **args, group_by=["customer"])
    assert {r["group_0"]: r["metric_0"] for r in grouped["rows"]} == {"А": 1, "Б": .5}
    zero = await call(mcp, "giga_query_dataset", dataset_id=1, metrics=[{**args["metrics"][0], "denominator": "zero"}])
    assert zero["rows"][0]["metric_0"] is None
    portal.db.execute("DELETE FROM source")
    assert (await call(mcp, "giga_query_dataset", **args))["rows"][0]["metric_0"] is None
    assert portal.calls[("reports", "update")] == portal.calls[("reports", "create")] == 0


@pytest.mark.asyncio
async def test_source_probe_invalid_inputs_fail_before_recordset(fixture):
    portal, mcp, _ = fixture
    for metric, options in [({"label": "Wrong", "field": "not_a_field"}, {}),
        ({"label": "Wrong", "field": "customer"}, {}),
        ({"label": "Wrong", "field": "plan); DROP TABLE source"}, {}),
        ({"label": "Plan", "field": "plan"}, {"filters": [{"field": "unknown", "values": ["Б"]}]}),
        ({"label": "Plan", "field": "plan"}, {"group_by": ["customer", "customer"]})]:
        result = await call(mcp, "giga_query_dataset", dataset_id=1, metrics=[{'kind':'sum',**metric}], **options)
        assert not result["success"]
    assert portal.calls[("recordsets", "create")] == portal.calls[("reports", "update")] == 0


@pytest.mark.asyncio
async def test_sample_profiles_do_not_claim_full_dataset_uniqueness(fixture):
    _, mcp, _ = fixture
    result = await call(mcp, "giga_read_dataset", dataset_id=1, limit=1)
    assert result["truncated"] and result["fields_count"] == 5
    assert "sample" in result["sample_scope"]
    assert next(p for p in result["sample_profiles"] if p["field"] == "plan")["max_in_sample"] == 100


@pytest.mark.asyncio
async def test_native_inspection_renderer_options_types_and_aggregation_normalization(fixture):
    portal, mcp, _ = fixture
    await call(mcp, "giga_upsert_components", report_id=42, components=[{"key": "bar", "kind": "bar", "category": "customer", "title": "Факт", "dataset_id": 1, "horizontal": True, "stacked": True, "metrics": [{"label": "Факт", "field": "actual"}]}])
    cfg = portal.reports[42]["grid"]["components"]["0"]["config"]
    categories = next(a for a in cfg["axes"] if a["type"] == "categories")["fields"]
    categories[0]["agg"] = ""
    portal.fields[0]["alias"] = "Renamed source label"
    assert (await call(mcp, "giga_inspect_report", report_id=42))["checks_passed"]
    cfg["orientation"] = "v"
    assert not (await call(mcp, "giga_inspect_report", report_id=42))["checks_passed"]
    cfg["orientation"] = "h"
    value = next(a for a in cfg["axes"] if a["type"] == "values")["fields"][0]
    value["type"] = "string"
    assert not (await call(mcp, "giga_inspect_report", report_id=42))["checks_passed"]


@pytest.mark.asyncio
async def test_merge_renames_localized_title_and_inspect_rejects_render_column_drift(fixture):
    portal, mcp, _ = fixture
    args = dict(report_id=42, key="table", dataset_id=1, columns=[{"field": "plan", "label": "План"}])
    await call(mcp, "giga_set_table", **args, title="Old")
    await call(mcp, "giga_set_table", **args, title="New")
    cfg = portal.reports[42]["grid"]["components"]["0"]["config"]
    assert cfg["caption__ru"]["text"] == cfg["title"]["text"] == cfg["caption"] == "New"
    assert (await call(mcp, "giga_inspect_report", report_id=42))["checks_passed"]
    next(iter(cfg["columns"].values()))["visibleOrder"] = 99
    assert not (await call(mcp, "giga_inspect_report", report_id=42))["checks_passed"]


def native_axes(component_type):
    dim = lambda axis, *fields: {"axis": axis, "fields": list(fields)}
    measure = lambda axis, *fields: {"axis": axis, "metrics": [{"label": name, "field": name, "kind": "raw" if component_type in {"HsTreeGraph", "HsParallelCoordsChart"} else "sum"} for name in fields]}
    if component_type == "HsBubbleAMchartsChart":
        return [dim("categories", "customer"), measure("xvalues", "plan"), measure("yvalues", "actual"), measure("values", "zero")]
    if component_type == "HsParallelCoordsChart":
        return [{"axis": "values", "fields": ["customer"], "metrics": measure("values", "plan", "actual")["metrics"]}]
    if component_type == "HsPivotChart":
        return [dim("rows", "customer"), dim("columns", "plan"), measure("values", "actual")]
    if component_type == "HsComparisonChart":
        return [dim("objects", "customer"), dim("indicators", "html"), measure("values", "actual")]
    if component_type == "HsTreeGraph":
        return [dim("identity", "plan"), dim("linkage", "zero"), measure("values", "actual")]
    if component_type == "HsMapLeafletChart":
        return [dim("categories", "customer"), {"axis": "values", "metrics": [{"label": name, "field": name, "kind": "max"} for name in ("plan", "actual", "zero")]}]
    if component_type == "HsSpeedometerV2AMcharts":
        return [measure("values", "actual")]
    if component_type in {"HsFilterControlPanel", "HsHierarchicalFilterPanel"}:
        return [dim("filters", "customer")]
    if component_type == "HsSwitchControlPanel":
        return [dim("categories", "customer")]
    return [dim("categories", "customer"), measure("values", "actual")]


@pytest.mark.asyncio
@pytest.mark.parametrize("component_type", [
    "HsBarAMchartsChart", "HsLineAMchartsChart", "HsAreaAMchartsChart", "HsPieAMchartsChart", "HsRadarAMchartsChart",
    "HsStockAMchartsChart", "HsSpeedometerV2AMcharts", "HsBubbleAMchartsChart", "HsSunburstChart", "HsTreeMap",
    "HsParallelCoordsChart", "HsPivotChart", "HsComparisonChart", "HsTreeGraph", "HsMapLeafletChart", "HsTilemapChart",
    ])
async def test_native_axis_types_query_before_commit_and_readback(fixture, component_type):
    portal, mcp, _ = fixture
    if component_type == "HsStockAMchartsChart":
        portal.fields[0]["type"] = "date"
        portal.db.execute("UPDATE source SET customer=CASE customer WHEN 'А' THEN '2026-01-01' ELSE '2026-02-01' END")
    if component_type == "HsMapLeafletChart":
        portal.db.execute("UPDATE source SET plan=55, actual=37")
    if component_type == "HsTreeGraph":
        portal.db.execute("UPDATE source SET zero=NULL")
    if component_type == "HsTilemapChart":
        portal.db.execute("UPDATE source SET customer=CASE customer WHEN 'А' THEN 'Москва' ELSE 'Новосибирская область' END")
    spec = {"key": "native", "title": "Native", "component_type": component_type, "dataset_id": 1,
        "axes": native_axes(component_type), "maximum": 1000}
    if component_type == "HsComparisonChart":
        spec["compare_values"] = ["А", "Б"]
    if component_type == "HsMapLeafletChart":
        spec.update(latitude_field="plan", longitude_field="actual")
    result = await call(mcp, "giga_set_visualization", report_id=42, visualization=spec)
    assert result["success"], result
    assert portal.calls[("reports", "update")] == 1
    inspected = await call(mcp, "giga_inspect_report", report_id=42)
    assert inspected["checks_passed"], inspected["issues"]
    rows = inspected["data"]["native"]["rows"]
    assert len(rows) in {1, 2}
    if component_type in {"HsPivotChart", "HsComparisonChart"}:
        assert sorted(r["actual"] for r in rows) == [100, 450]


@pytest.mark.asyncio
async def test_native_unknown_axis_missing_axes_and_catalog_readonly(fixture):
    portal, mcp, _ = fixture
    set_security_mode(SecurityMode.READONLY)
    catalog = await call(mcp, "giga_list_visualizations")
    assert catalog["success"] and len(catalog["items"]) == len(COMPONENT_TYPE_MAP) == 28
    assert all(item["available_on_portal"] for item in catalog["items"])
    set_security_mode(SecurityMode.READWRITE)
    for axes in ([], [{"axis": "unknown", "fields": ["plan"]}]):
        result = await call(mcp, "giga_set_visualization", report_id=42, visualization={"key": "bubble", "title": "Bubble", "component_type": "HsBubbleAMchartsChart", "dataset_id": 1, "axes": axes})
        assert not result["success"]
    assert portal.calls[("reports", "update")] == portal.calls[("recordsets", "create")] == 0


@pytest.mark.asyncio
async def test_native_table_cannot_bypass_merge_and_invalid_axis_types_are_rejected(fixture):
    portal, mcp, _ = fixture
    cases = [
        ("HsTableReactabularChart", [{"axis": "values", "fields": ["plan"]}]),
        ("HsSpeedometerV2AMcharts", [{"axis": "values", "fields": ["html"]}]),
        ("HsStockAMchartsChart", [{"axis": "categories", "fields": ["customer"]}, {"axis": "values", "metrics": [{"label": "Факт", "field": "actual", "kind": "sum"}]}]),
        ("HsTreeGraph", [{"axis": "identity", "fields": ["plan", "actual"]}, {"axis": "linkage", "fields": ["zero"]}, {"axis": "values", "fields": ["html"]}]),
    ]
    for kind, axes in cases:
        result = await call(mcp, "giga_set_visualization", report_id=42, visualization={"key": "invalid", "component_type": kind, "title": "Invalid", "dataset_id": 1, "axes": axes})
        assert not result["success"]
    assert portal.calls[("reports", "update")] == portal.calls[("recordsets", "create")] == 0


@pytest.mark.asyncio
async def test_comparison_selected_axes_and_filters_are_verified(fixture):
    portal, mcp, _ = fixture
    result = await call(mcp, "giga_set_visualization", report_id=42, visualization={"key": "comparison", "component_type": "HsComparisonChart", "title": "Сравнение", "dataset_id": 1, "axes": native_axes("HsComparisonChart"), "compare_values": ["А", "Б"]})
    assert result["success"]
    cfg = portal.reports[42]["grid"]["components"]["0"]["config"]
    assert next(a for a in cfg["axes"] if a["type"] == "series")["selectedFieldIndex"] == -1
    assert next(a for a in cfg["axes"] if a["type"] == "values")["selectedFieldIndex"] == 0
    assert next(a for a in cfg["axes"] if a["type"] == "series")["fields"][0]["name"] == "customer"
    assert cfg["filters"]["html"]["selected"] == ["<p>A</p>", "<p>B</p>"]
    cfg["filters"]["customer"]["selected"] = ["А"]
    inspected = await call(mcp, "giga_inspect_report", report_id=42)
    assert not inspected["checks_passed"] and any("COMPARISON_SELECTION_DRIFT" in e for e in inspected["issues"])


@pytest.mark.asyncio
async def test_comparison_indicator_subset_and_inactive_series_drift(fixture):
    portal, mcp, _ = fixture
    result = await call(mcp, "giga_set_visualization", report_id=42, visualization={"key": "comparison", "component_type": "HsComparisonChart", "title": "Сравнение", "dataset_id": 1, "axes": native_axes("HsComparisonChart"), "compare_values": ["А", "Б"], "indicator_values": ["<p>A</p>"],"indicator_mode":"selected"})
    assert result["success"]
    inspected = await call(mcp, "giga_inspect_report", report_id=42)
    assert len(inspected["data"]["comparison"]["rows"]) == 1
    await call(mcp, "giga_bind_report_filter", report_id=42, key="customer_filter", label="Заказчик", bindings=[{"dataset_id": 1, "field": "customer"}])
    assert (await call(mcp, "giga_inspect_report", report_id=42))["checks_passed"]
    cfg = portal.reports[42]["grid"]["components"]["0"]["config"]
    next(a for a in cfg["axes"] if a["type"] == "series")["selectedFieldIndex"] = 0
    assert not (await call(mcp, "giga_inspect_report", report_id=42))["checks_passed"]


@pytest.mark.asyncio
async def test_comparison_auto_indicators_never_truncates_after_null(fixture):
    portal, mcp, _ = fixture
    portal.db.execute("DELETE FROM source")
    portal.db.executemany("INSERT INTO source VALUES(?,?,?,?,?)", [("А", 1, 1, 0, None)] + [("А", 1, 1, 0, f"I{i:03}") for i in range(101)])
    result = await call(mcp, "giga_set_visualization", report_id=42, visualization={"key": "comparison", "component_type": "HsComparisonChart", "title": "Сравнение", "dataset_id": 1, "axes": native_axes("HsComparisonChart"), "compare_values": ["А", "Б"]})
    assert not result["success"]
    assert portal.calls[("reports", "update")] == 0


@pytest.mark.asyncio
async def test_native_schema_enum_and_irrelevant_gauge_bounds(fixture):
    portal,mcp,_=fixture
    tools={t.name:t for t in await mcp.list_tools()}
    props=tools["giga_set_visualization"].inputSchema["properties"]["visualization"]["properties"]
    assert props["kind"]["enum"]==["native"] and "const" not in props["kind"]
    assert "HsPivotChart" in props["component_type"]["enum"] and "HsPivotTable" not in props["component_type"]["enum"]
    native_schema=tools["giga_set_visualization"].inputSchema["properties"]["visualization"]
    assert "axes" in native_schema["required"]
    assert "kind" in props["axes"]["items"]["properties"]["metrics"]["items"]["required"]
    result=await call(mcp,"giga_set_visualization",report_id=42,visualization={"key":"pivot","component_type":"HsPivotChart","title":"Pivot","dataset_id":1,"axes":native_axes("HsPivotChart"),"minimum":0,"maximum":0})
    assert result["success"]


@pytest.mark.asyncio
async def test_calculated_execution_mode_drift_is_rejected(fixture):
    portal,mcp,_=fixture
    await kpi(mcp)
    cfg=portal.reports[42]["grid"]["components"]["0"]["config"]
    value=next(a for a in cfg["axes"] if a["type"]=="values")["fields"][0]
    value["draft"]=False
    assert not (await call(mcp,"giga_inspect_report",report_id=42))["checks_passed"]
