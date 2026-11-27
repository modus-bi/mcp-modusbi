import copy
import pytest
from app.tests.test_gigachat_profile import fixture, call
from app.tools.gigachat_geo import canonical_region, validate_tree, validate_points, REGIONS
from app.tools.gigachat_styles import STYLES
from app.tools.gigachat_profile import META


def source(portal, rows):
    portal.db.execute("DELETE FROM source")
    portal.db.executemany("INSERT INTO source VALUES(?,?,?,?,?)",rows)


@pytest.mark.asyncio
async def test_source_probe_infers_raw_text_with_group_aggregate_and_slice(fixture):
    p,m,_=fixture
    before=copy.deepcopy(p.reports)
    result=await call(m,"giga_query_dataset",dataset_id=1,group_by=["customer"],filters=[{"field":"customer","values":["А"]}],metrics=[{"label":"Заказчик","field":"customer","kind":"raw"},{"label":"Факт","field":"actual","kind":"sum"}])
    assert result["success"] and result["rows"]==[{"group_0":"А","metric_0":"А","metric_1":100,"source_row_count":1}],result
    assert result["columns"][1]["metric"]["format"]=="text"
    assert p.reports==before and p.calls[("reports","update")]==0


@pytest.mark.asyncio
async def test_rename_preserves_geometry_filter_layout_and_style(fixture):
    p,m,_=fixture
    source(p,[("Группа1",1,40,None,"5294de"),("Группа1",2,0,1,"8bc34a")])
    assert (await call(m,"giga_set_tree",report_id=42,key="tree",title="Дерево",dataset_id=1,node_field="plan",parent_field="zero",label_field="customer",size_field="actual",color_field="html"))["success"]
    await call(m,"giga_bind_report_filter",report_id=42,key="group",label="Группа",bindings=[{"dataset_id":1,"field":"customer"}])
    await call(m,"giga_apply_dashboard_preset",report_id=42,style="warm_minimalism")
    before=copy.deepcopy(p.reports[42])
    assert (await call(m,"giga_rename_component",report_id=42,key="tree",title="Новая подпись"))["success"]
    expected=copy.deepcopy(before)
    cfg=expected["grid"]["components"]["0"]["config"]
    cfg[META]["spec"]["title"]="Новая подпись"
    for name in ("caption","caption__ru","title"):
        if isinstance(cfg.get(name),dict):cfg[name]["text"]="Новая подпись"
        else:cfg[name]="Новая подпись"
    assert p.reports[42]==expected
    assert not (await call(m,"giga_rename_component",report_id=42,key="tree",title="Новая подпись"))["changed"]
    assert (await call(m,"giga_inspect_report",report_id=42))["checks_passed"]


@pytest.mark.asyncio
async def test_renderer_replacement_is_explicit_and_atomic(fixture):
    p,m,_=fixture
    source(p,[("Группа1",1,40,None,"5294de")])
    await call(m,"giga_set_tree",report_id=42,key="tree",title="Дерево",dataset_id=1,node_field="plan",parent_field="zero",label_field="customer",size_field="",color_field="")
    before=copy.deepcopy(p.reports[42]);writes=p.calls[("reports","update")]
    for tool,args in [("giga_set_header",{"key":"tree","title":"Название","period":"2026"}),
        ("giga_upsert_components",{"components":[{"key":"tree","title":"Текст","kind":"text","text":"Подпись","category":""}]}),
        ("giga_set_visualization",{"visualization":{"key":"tree","title":"Гистограмма","dataset_id":1,"component_type":"HsBarAMchartsChart","axes":[{"axis":"categories","fields":["customer"]},{"axis":"values","metrics":[{"label":"Факт","field":"actual","kind":"sum"}]}]}})]:
        result=await call(m,tool,report_id=42,**args)
        assert not result["success"] and "COMPONENT_REPLACEMENT_REQUIRED" in str(result),result
        assert p.reports[42]==before and p.calls[("reports","update")]==writes
    result=await call(m,"giga_upsert_components",report_id=42,replace_kind=True,components=[{"key":"tree","title":"Текст","kind":"text","text":"Намеренная замена","category":""}])
    assert result["success"] and p.reports[42]["grid"]["components"]["0"]["type"]=="HsTextBlock"


@pytest.mark.asyncio
async def test_readability_guard_rejects_map_compression_before_write(fixture):
    p,m,_=fixture
    source(p,[("А",55,37,10,"pointA")])
    await call(m,"giga_set_map",report_id=42,key="map",title="Карта",dataset_id=1,point_field="html",latitude_field="plan",longitude_field="actual",metric={"label":"Сумма","field":"zero","kind":"sum"})
    before=copy.deepcopy(p.reports[42])
    result=await call(m,"giga_arrange_report",report_id=42,placements=[{"key":"map","row":4,"height":8}])
    assert not result["success"] and "READABLE_HEIGHT" in str(result)
    assert p.reports[42]==before


@pytest.mark.parametrize("raw,canonical",[("Москва","г. Москва"),("Санкт-Петербург","г. Санкт-Петербург"),("Республика Татарстан","Республика Татарстан (Татарстан)"),("Новосибирская область","Новосибирская область")])
def test_regions_use_native_dictionary(raw,canonical):
    assert canonical_region(raw)==canonical
    assert len(REGIONS)==90
    assert all(canonical_region(r["name"])==r["name"] for r in REGIONS)


@pytest.mark.parametrize("name",[None,"","Москов","Неизвестный район"])
def test_no_fuzzy_or_empty_region_loss(name):
    with pytest.raises(ValueError):canonical_region(name)


@pytest.mark.asyncio
async def test_tree_roles_merge_and_filter_before_and_after(fixture):
    p,m,_=fixture
    source(p,[("Группа1",1,40,None,"5294de"),("Группа1",2,0,1,"8bc34a"),("Группа2",3,50,None,"e53935")])
    await call(m,"giga_bind_report_filter",report_id=42,key="group",label="Группа",bindings=[{"dataset_id":1,"field":"customer"}])
    result=await call(m,"giga_set_tree",report_id=42,key="tree",title="Дерево",dataset_id=1,node_field="plan",parent_field="zero",label_field="customer",size_field="actual",color_field="html")
    assert result["success"],result
    cfg=p.reports[42]["grid"]["components"]["1"]["config"]
    values=next(a for a in cfg["axes"] if a["type"]=="values")["fields"]
    assert {f["name"]:f["valueType"] for f in values}=={"customer":"value","actual":"size","html":"color"}
    update=await call(m,"giga_set_visualization",report_id=42,visualization={"key":"tree","title":"Дерево обновлено","component_type":"HsTreeGraph","dataset_id":1,"axes":[{"axis":"values","metrics":[{"label":"Размер","field":"actual","kind":"raw"}]}]})
    assert update["success"],update
    assert (await call(m,"giga_inspect_report",report_id=42))["checks_passed"]
    assert (await call(m,"giga_select_filter",report_id=42,key="group",values=["Группа1"]))["success"]
    assert len((await call(m,"giga_inspect_report",report_id=42))["data"]["tree"]["rows"])==2
    assert (await call(m,"giga_select_filter",report_id=42,key="group",values=[]))["success"]
    assert len((await call(m,"giga_inspect_report",report_id=42))["data"]["tree"]["rows"])==3


@pytest.mark.parametrize("rows",[[{"id":1,"parent":1}],[{"id":1,"parent":2},{"id":2,"parent":1}],[{"id":1,"parent":None},{"id":1,"parent":None}],[{"id":1,"parent":2}],[{"id":2**53,"parent":None}],[{"id":0,"parent":False}]])
def test_invalid_graphs_are_rejected(rows):
    with pytest.raises(ValueError):validate_tree(rows,"id","parent")


@pytest.mark.asyncio
async def test_filter_orphans_fail_atomically(fixture):
    p,m,_=fixture
    source(p,[("Родитель",1,40,None,"5294de"),("Ребёнок",2,20,1,"8bc34a")])
    assert (await call(m,"giga_set_tree",report_id=42,key="tree",title="Дерево",dataset_id=1,node_field="plan",parent_field="zero",label_field="customer",size_field="actual",color_field="html"))["success"]
    await call(m,"giga_bind_report_filter",report_id=42,key="group",label="Группа",bindings=[{"dataset_id":1,"field":"customer"}])
    old=copy.deepcopy(p.reports[42]);writes=p.calls[("reports","update")]
    result=await call(m,"giga_select_filter",report_id=42,key="group",values=["Ребёнок"])
    assert not result["success"] and "orphan" in result["error"]
    assert p.reports[42]==old and p.calls[("reports","update")]==writes


@pytest.mark.asyncio
async def test_map_adds_coordinates_once_and_preserves_filter(fixture):
    p,m,_=fixture
    source(p,[("Группа1",55,37,10,"pointA"),("Группа1",55,37,20,"pointA"),("Группа2",55,37,30,"pointB")])
    args=dict(report_id=42,key="map",title="Карта",dataset_id=1,point_field="html",latitude_field="plan",longitude_field="actual",metric={"label":"Сумма","field":"zero","kind":"sum"})
    assert (await call(m,"giga_set_map",**args))["success"]
    assert not (await call(m,"giga_set_map",**args))["changed"]
    await call(m,"giga_bind_report_filter",report_id=42,key="group",label="Группа",bindings=[{"dataset_id":1,"field":"customer"}])
    assert (await call(m,"giga_select_filter",report_id=42,key="group",values=["Группа1"]))["success"]
    result=await call(m,"giga_inspect_report",report_id=42)
    assert result["checks_passed"]
    assert result["data"]["map"]["rows"]==[{"html":"pointA","plan":55,"actual":37,"zero":30}]


@pytest.mark.parametrize("points",[[{"id":1,"lat":91,"lon":0}],[{"id":1,"lat":0,"lon":181}],[{"id":1,"lat":None,"lon":0}],[{"id":1,"lat":1,"lon":0},{"id":1,"lat":2,"lon":0}]])
def test_invalid_coordinates_not_averaged(points):
    with pytest.raises(ValueError):validate_points(points,["id"],"lat","lon")


def test_point_ids_are_safe_and_zero_coordinates_are_valid():
    with pytest.raises(ValueError):validate_points([{"id":2**53,"lat":0,"lon":0}],["id"],"lat","lon")
    validate_points([{"id":"9007199254740993","lat":0,"lon":0},{"id":"another","lat":0,"lon":0}],["id"],"lat","lon")


@pytest.mark.asyncio
@pytest.mark.parametrize("container",["axes","axesDefault","filters","filtersDefault"])
async def test_inspect_detects_lost_filter_binding(fixture,container):
    p,m,_=fixture
    await call(m,"giga_set_kpi",report_id=42,key="kpi",title="Сумма",dataset_id=1,metric={"label":"Сумма","field":"actual","kind":"sum"})
    await call(m,"giga_bind_report_filter",report_id=42,key="group",label="Группа",bindings=[{"dataset_id":1,"field":"customer"}])
    cfg=p.reports[42]["grid"]["components"]["0"]["config"]
    if container in {"axes","axesDefault"}:next(a for a in cfg[container] if a["type"]=="filters")["fields"]=[]
    else:cfg[container]["customer"].pop("global")
    inspected=await call(m,"giga_inspect_report",report_id=42)
    assert not inspected["checks_passed"] and any("FILTER_BINDING_DRIFT" in i for i in inspected["issues"])


@pytest.mark.asyncio
async def test_tilemap_canonical_names_and_filtered_inspection(fixture):
    p,m,_=fixture
    source(p,[("Москва",1,100,0,"Группа1"),("г. Москва",2,200,0,"Группа2"),("Республика Татарстан",3,150,0,"Группа1")])
    result=await call(m,"giga_set_tilemap",report_id=42,key="tilemap",title="Регионы",dataset_id=1,region_field="customer",metric={"label":"Сумма","field":"actual","kind":"sum"})
    assert result["success"],result
    data=(await call(m,"giga_inspect_report",report_id=42))["data"]["tilemap"]["rows"]
    assert {r["customer"]:r["actual"] for r in data}=={"г. Москва":300,"Республика Татарстан (Татарстан)":150}
    await call(m,"giga_bind_report_filter",report_id=42,key="group",label="Группа",bindings=[{"dataset_id":1,"field":"html"}])
    assert (await call(m,"giga_select_filter",report_id=42,key="group",values=["Группа1"]))["success"]
    assert (await call(m,"giga_inspect_report",report_id=42))["checks_passed"]


@pytest.mark.asyncio
@pytest.mark.parametrize("style",list(STYLES))
async def test_styles_preserve_data_and_are_idempotent(fixture,style):
    p,m,_=fixture
    await call(m,"giga_set_kpi",report_id=42,key="kpi",title="Сумма",dataset_id=1,metric={"label":"Сумма","kind":"sum","field":"actual"})
    before=(await call(m,"giga_inspect_report",report_id=42))["data"]
    assert (await call(m,"giga_apply_dashboard_preset",report_id=42,style=style))["success"]
    assert (await call(m,"giga_inspect_report",report_id=42))["data"]==before
    assert not (await call(m,"giga_apply_dashboard_preset",report_id=42,style=style))["changed"]
