"""Native frontend contracts with independent non-degenerate source values."""
import copy
import pytest
from mcp.server.fastmcp.exceptions import ToolError
from app.tests.test_gigachat_profile import fixture,call
from app.tools.component_crud import _get_component_data


def rows(p,values):
    p.db.execute("DELETE FROM source")
    p.db.executemany("INSERT INTO source VALUES(?,?,?,?,?)",values)


@pytest.mark.asyncio
async def test_treemap_preserves_two_by_two_hierarchy_and_detects_loss(fixture):
    p,m,_=fixture
    rows(p,[("A",1,0,2,"X"),("A",2,0,3,"Y"),("B",3,0,5,"X"),("B",4,0,7,"Y")])
    spec={"key":"tree_map","component_type":"HsTreeMap","title":"Структура","dataset_id":1,"axes":[{"axis":"categories","fields":["customer","html"]},{"axis":"values","metrics":[{"label":"Размер","field":"zero","kind":"sum"}]}]}
    result=await call(m,"giga_set_visualization",report_id=42,visualization=spec)
    assert result["success"],result
    cfg=p.reports[42]["grid"]["components"]["0"]["config"]
    axes={a["type"]:a for a in cfg["axes"]}
    assert [f["name"] for f in axes["categories"]["fields"]]==["customer"]
    assert [f["name"] for f in axes["series"]["fields"]]==["html"]
    assert axes["categories"]["selectedFieldIndex"]==axes["series"]["selectedFieldIndex"]==0
    assert cfg["axes"]==cfg["axesDefault"]
    snapshot=await call(m,"giga_inspect_report",report_id=42)
    assert snapshot["checks_passed"]
    assert {(r["customer"],r["html"]):r["zero"] for r in snapshot["data"]["tree_map"]["rows"]}=={("A","X"):2,("A","Y"):3,("B","X"):5,("B","Y"):7}
    axes["series"]["fields"]=[]
    assert not (await call(m,"giga_inspect_report",report_id=42))["checks_passed"]


@pytest.mark.asyncio
async def test_treemap_deeper_hierarchy_is_not_silently_flattened(fixture):
    p,m,_=fixture
    result=await call(m,"giga_set_visualization",report_id=42,visualization={"key":"too_deep","component_type":"HsTreeMap","title":"Структура","dataset_id":1,"axes":[{"axis":"categories","fields":["customer","html","plan"]},{"axis":"values","metrics":[{"label":"Размер","field":"actual","kind":"sum"}]}]})
    assert not result["success"] and p.calls[("reports","update")]==0


@pytest.mark.asyncio
@pytest.mark.parametrize("aggr,jan",[("min",5),("max",15),("avg",10),("sum",20)])
async def test_pivot_order_aggregation_and_drift_match_frontend(fixture,aggr,jan):
    p,m,_=fixture;p.fields[1]["type"]="date"
    rows(p,[("A","2026-03-01",10,0,"X"),("A","2026-01-01",5,0,"X"),("A","2026-01-01",15,0,"Y"),("B","2026-02-01",9,0,"Y")])
    queries=[];original=p.api_call
    async def capture(entity,action,object_id=None,data=None):
        if entity=="recordsets" and action=="create":queries.append(copy.deepcopy(data[0]))
        return await original(entity,action,object_id=object_id,data=data)
    p.api_call=capture
    result=await call(m,"giga_set_visualization",report_id=42,visualization={"key":"pivot","component_type":"HsPivotChart","title":"По месяцам","dataset_id":1,"axes":[{"axis":"rows","fields":["customer"]},{"axis":"columns","fields":["plan"]},{"axis":"values","metrics":[{"label":"Факт","field":"actual","kind":aggr}]}]})
    assert result["success"],result
    cfg=p.reports[42]["grid"]["components"]["0"]["config"];axes={a["type"]:a for a in cfg["axes"]}
    assert axes["columns"]["fields"][0]["pivotOrder"]==axes["rows"]["fields"][0]["pivotOrder"]=="asc"
    assert axes["values"]["fields"][0]["pivotAgg"]==aggr
    assert any(q.get("order") and any(o["name"]=="plan" and o["direction"]=="asc" for o in q["order"]) for q in queries)
    snapshot=await call(m,"giga_inspect_report",report_id=42)
    assert snapshot["checks_passed"]
    assert next(r["actual"] for r in snapshot["data"]["pivot"]["rows"] if r["plan"]=="2026-01-01")==jan
    axes["columns"]["fields"][0]["pivotOrder"]="desc"
    assert not (await call(m,"giga_inspect_report",report_id=42))["checks_passed"]
    axes["columns"]["fields"][0]["pivotOrder"]="asc"
    axes["values"]["fields"][0]["pivotAgg"]="max" if aggr!="max" else "min"
    assert not (await call(m,"giga_inspect_report",report_id=42))["checks_passed"]


@pytest.mark.asyncio
async def test_comparison_duplicate_indicator_selection_is_rejected_before_write(fixture):
    p,m,_=fixture
    with pytest.raises(ToolError,match="must be unique"):
        await call(m,"giga_set_visualization",report_id=42,visualization={"key":"compare","component_type":"HsComparisonChart","title":"Сравнение","dataset_id":1,"axes":[],"indicator_values":["X","X"]})
    assert p.calls[("reports","update")]==0


@pytest.mark.asyncio
async def test_dimension_and_count_of_same_field_keep_both_outputs(fixture):
    p,m,_=fixture
    rows(p,[("A",1,5,0,"X"),("A",2,15,0,"Y"),("B",3,9,0,"X")])
    result=await call(m,"giga_set_visualization",report_id=42,visualization={"key":"count","component_type":"HsPivotChart","title":"Количество","dataset_id":1,"axes":[{"axis":"rows","fields":["customer"]},{"axis":"values","metrics":[{"label":"Количество","field":"customer","kind":"count"}]}]})
    assert result["success"]
    assert len(result["preview_bindings"]["count"])==2
    s=await call(m,"giga_inspect_report",report_id=42);data=s["data"]["count"];bindings=data["column_bindings"]
    dimension=next(b["output_name"] for b in bindings if b["axis"]=="rows")
    count=next(b["output_name"] for b in bindings if b["aggregation"]=="count")
    assert s["checks_passed"] and dimension!=count
    assert {r[dimension]:r[count] for r in data["rows"]}=={"A":2,"B":1}
    assert s["components"][0]["field_outputs"]==bindings


@pytest.mark.asyncio
async def test_two_aggregations_of_same_field_do_not_overwrite(fixture):
    p,m,_=fixture
    rows(p,[("A",1,5,0,"X"),("A",2,15,0,"Y"),("B",3,9,0,"X")])
    result=await call(m,"giga_set_visualization",report_id=42,visualization={"key":"stats","component_type":"HsPivotChart","title":"Статистика","dataset_id":1,"axes":[{"axis":"rows","fields":["customer"]},{"axis":"values","metrics":[{"label":"Минимум","field":"actual","kind":"min"},{"label":"Сумма","field":"actual","kind":"sum"}]}]})
    assert result["success"]
    s=await call(m,"giga_inspect_report",report_id=42);data=s["data"]["stats"]
    names={b["aggregation"]:b["output_name"] for b in data["column_bindings"]}
    assert s["checks_passed"] and len(data["columns"])==3 and names["min"]!=names["sum"]
    assert {(r["customer"],r[names["min"]],r[names["sum"]]) for r in data["rows"]}=={("A",5,20),("B",9,9)}


@pytest.mark.asyncio
async def test_long_postgresql_output_binding_matches_truncated_result(fixture):
    p,m,_=fixture
    await call(m,"giga_set_visualization",report_id=42,visualization={"key":"stats","component_type":"HsPivotChart","title":"Статистика","dataset_id":1,"axes":[{"axis":"rows","fields":["customer"]},{"axis":"values","metrics":[{"label":"Минимум","field":"actual","kind":"min"},{"label":"Сумма","field":"actual","kind":"sum"}]}]})
    cfg=p.reports[42]["grid"]["components"]["0"]["config"]
    values=next(a for a in cfg["axes"] if a["type"]=="values")["fields"]
    long_name="Длинное_вычисляемое_поле_"*4
    values.append({"id":"extra_long","name":long_name,"type":"calculated","datasetId":1,"calc":'"actual"',"agg":"max","pivotAgg":"max","title":"Длинное поле"})
    original=p.api_call
    async def pg_names(entity,action,object_id=None,data=None):
        result=await original(entity,action,object_id=object_id,data=data)
        if entity=="recordsets" and action=="create":
            result["data"]=[{k.encode("utf-8")[:63].decode("utf-8",errors="ignore"):v for k,v in row.items()} for row in result["data"]]
        return result
    p.api_call=pg_names
    data=await _get_component_data(p,42,0)
    assert data["success"],data
    assert all(b["output_name"] in data["rows"][0] for b in data["column_bindings"])
    binding=next(b for b in data["column_bindings"] if b["field"]==long_name)
    assert len(binding["output_name"].encode("utf-8"))<=63
