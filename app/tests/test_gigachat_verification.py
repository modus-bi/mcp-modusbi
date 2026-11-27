"""Verification plans follow saved semantics and execute as ordinary source probes."""
import copy
import pytest
from app.tests.test_gigachat_profile import fixture, call
from app.tools.gigachat_verification import verification_plan,query_identity
from app.tools.component_crud import _get_component_data
from app.tools.component_crud import BREAKPOINT_COLS


@pytest.mark.asyncio
async def test_source_plan_is_derived_deduplicated_and_executable(fixture):
    p,m,_=fixture
    for key,kind in [('bar','bar'),('line','bar')]:
        result=await call(m,'giga_upsert_components',report_id=42,components=[{'key':key,'kind':kind,'title':'Факт','dataset_id':1,'category':'customer','metrics':[{'field':'actual','kind':'sum','label':key}]}])
        assert result['success'],result
    await call(m,'giga_set_kpi',report_id=42,key='ratio',title='Выполнение',dataset_id=1,metric={'kind':'ratio_of_sums','numerator':'actual','denominator':'plan','label':'Доля','format':'percent'})
    await call(m,'giga_bind_report_filter',report_id=42,key='filter',label='Заказчик',bindings=[{'dataset_id':1,'field':'customer'}])
    snapshot=await call(m,'giga_inspect_report',report_id=42)
    plan=snapshot['verification_plan']
    assert plan['status']=='source_comparison_required' and len(plan['queries'])==2
    assert any(set(q['components'])=={'bar','line'} for q in plan['queries'])
    assert plan['filters'][0]['bindings']==[{'dataset_id':1,'field':'customer'}]
    writes=p.calls[('reports','update')]
    for q in plan['queries']:
        result=await call(m,q['tool'],**q['arguments'])
        assert result['success'] and not result['truncated']
    assert p.calls[('reports','update')]==writes
    assert not snapshot['business_data_verified']


def test_plan_preserves_raw_row_grain_and_field_identity():
    spec={'dataset_id':7,'axes':[{'axis':'identity','fields':['id']},{'axis':'linkage','fields':['parent']},{'axis':'values','fields':['label','size'],'metrics':[]}]}
    plan=verification_plan([{'key':'tree','kind':'native','spec':spec}])
    q=plan['queries'][0]['arguments']
    assert q['group_by']==[] and {m['field'] for m in q['metrics']}=={'id','parent','label','size'}
    assert all(m['kind']=='raw' for m in q['metrics'])


@pytest.mark.asyncio
async def test_pivot_preview_uses_native_order_and_aggregate_despite_legacy_fields(fixture):
    p,m,_=fixture
    p.db.execute("INSERT INTO source VALUES('А',0,5,0,'X')")
    spec={'key':'pivot','component_type':'HsPivotChart','title':'Минимум','dataset_id':1,'axes':[{'axis':'rows','fields':['customer']},{'axis':'values','metrics':[{'field':'actual','kind':'min','label':'Факт'}]}]}
    assert (await call(m,'giga_set_visualization',report_id=42,visualization=spec))['success']
    comp=p.reports[42]['grid']['components']['0'];cfg=comp['config']
    assert 'type' not in cfg and cfg['chartType']=='pivotChart'
    rows=next(a for a in cfg['axes'] if a['type']=='rows')['fields']
    rows[0].pop('order',None);rows[0]['pivotOrder']='desc'
    values=next(a for a in cfg['axes'] if a['type']=='values')['fields']
    values[0]['agg']='max';values[0]['pivotAgg']='min'
    queries=[];original=p.api_call
    async def capture(entity,action,object_id=None,data=None):
        if entity=='recordsets' and action=='create':queries.append(copy.deepcopy(data[0]))
        return await original(entity,action,object_id=object_id,data=data)
    p.api_call=capture
    data=await _get_component_data(p,42,0,100)
    assert data['success'] and next(r['actual'] for r in data['rows'] if r['customer']=='А')==5
    assert queries[-1]['order'][0]['direction']=='desc'


@pytest.mark.asyncio
async def test_comparison_inactive_compatibility_axis_is_not_a_projected_column(fixture):
    p,m,_=fixture
    spec={'key':'compare','component_type':'HsComparisonChart','title':'Сравнение','dataset_id':1,'axes':[{'axis':'objects','fields':['customer']},{'axis':'indicators','fields':['html']},{'axis':'values','metrics':[{'field':'actual','kind':'sum','label':'Факт'}]}],'compare_values':['А','Б']}
    result=await call(m,'giga_set_visualization',report_id=42,visualization=spec)
    assert result['success'],result
    data=await _get_component_data(p,42,0,100)
    assert data['success'] and len(data['columns'])==3
    assert not any(b['axis']=='series' for b in data['column_bindings'])
    assert set(data['rows'][0])=={'customer','html','actual'}


@pytest.mark.asyncio
async def test_readable_layout_isolates_controls_and_dense_axes_and_checks_labels(fixture):
    p,m,_=fixture
    specs=[{'key':'sun','component_type':'HsSunburstChart','title':'Иерархия','dataset_id':1,'row':2,'height':14,'axes':[{'axis':'categories','fields':['customer','html']},{'axis':'values','metrics':[{'field':'actual','kind':'sum','label':'Факт'}]}],'field_labels':[{'field':'customer','label':'Заказчик'}]},
           {'key':'parallel','component_type':'HsParallelCoordsChart','title':'Координаты','dataset_id':1,'row':2,'axes':[{'axis':'values','fields':['plan','actual','zero']}]}]
    for spec in specs:assert (await call(m,'giga_set_visualization',report_id=42,visualization=spec))['success']
    assert (await call(m,'giga_bind_report_filter',report_id=42,key='filter',label='Заказчик',bindings=[{'dataset_id':1,'field':'customer'}]))['success']
    report=p.reports[42];comps=report['grid']['components'];sun=comps['0']['config']
    assert sun['_mcp_gigachat']['spec']['height']>=26 and sun['splittedMode']
    layout={item['i']:item for item in report['grid']['layouts']['hd']}
    assert layout['1']['w']==BREAKPOINT_COLS['hd']
    assert layout['2']['h']==4 and layout['2']['y']<layout['0']['y']
    field=next(a for a in sun['axes'] if a['type']=='categories')['fields'][0]
    assert field['name']=='customer' and field['title']=='Заказчик'
    field['title']='Wrong label'
    assert not (await call(m,'giga_inspect_report',report_id=42))['checks_passed']


@pytest.mark.asyncio
async def test_table_omitted_format_follows_schema_without_dropping_columns(fixture):
    p,m,_=fixture
    args={'report_id':42,'key':'table','title':'Данные','dataset_id':1,'columns':[{'field':'customer','label':'Заказчик'},{'field':'plan','label':'План'},{'field':'actual','label':'Факт'}]}
    result=await call(m,'giga_set_table',**args)
    assert result['success'],result
    snapshot=await call(m,'giga_inspect_report',report_id=42)
    metrics=snapshot['components'][0]['spec']['metrics']
    assert [(x['field'],x['format']) for x in metrics]==[('customer','text'),('plan','number'),('actual','number')]
    assert len(snapshot['data']['table']['columns'])==3
    before=copy.deepcopy(p.reports[42]);args['columns'][0]['format']='number'
    result=await call(m,'giga_set_table',**args)
    assert not result['success'] and p.reports[42]==before


@pytest.mark.asyncio
async def test_many_graphs_in_one_logical_row_reflow_to_two_per_actual_row(fixture):
    p,m,_=fixture
    specs=[{'key':'bar_'+str(i),'kind':'bar','title':'Факт','dataset_id':1,'row':1,'category':'customer','metrics':[{'field':'actual','label':'Факт','kind':'sum'}]} for i in range(7)]
    result=await call(m,'giga_upsert_components',report_id=42,components=specs)
    assert result['success'],result
    snapshot=await call(m,'giga_inspect_report',report_id=42)
    from collections import Counter
    assert max(Counter(x['y'] for x in snapshot['layouts']['hd']).values())<=2
    assert snapshot['checks_passed']


@pytest.mark.asyncio
async def test_table_auto_format_preserves_existing_html_and_rejects_numeric_rules_on_text(fixture):
    p,m,_=fixture
    args={'report_id':42,'key':'table','title':'Данные','dataset_id':1,'columns':[{'field':'html','label':'Описание','format':'html'},{'field':'actual','label':'Факт','format':'percent','decimals':2}]}
    assert (await call(m,'giga_set_table',**args))['success']
    args['columns']=[{'field':'html','label':'Обновлённое описание'},{'field':'customer','label':'Заказчик'}]
    assert (await call(m,'giga_set_table',**args))['success']
    snapshot=await call(m,'giga_inspect_report',report_id=42)
    assert {x['field']:x['format'] for x in snapshot['components'][0]['spec']['metrics']}=={'html':'html','actual':'percent','customer':'text'}
    before=copy.deepcopy(p.reports[42])
    args.update(key='invalid',columns=[{'field':'customer','label':'Заказчик','cell_rules':[{'operator':'gt','value':1,'background':'#FFFFFF'}]}])
    assert not (await call(m,'giga_set_table',**args))['success']
    assert p.reports[42]==before


@pytest.mark.asyncio
async def test_independent_query_requires_explicit_raw_or_aggregate_kind(fixture):
    from mcp.server.fastmcp.exceptions import ToolError
    p,m,_=fixture
    with pytest.raises(ToolError,match='kind'):
        await call(m,'giga_query_dataset',dataset_id=1,metrics=[{'field':'customer','label':'Заказчик'}])
    assert p.calls[('recordsets','create')]==0
    result=await call(m,'giga_query_dataset',dataset_id=1,metrics=[{'kind':'raw','field':'customer','label':'Заказчик'}])
    assert result['success'] and {r['metric_0'] for r in result['rows']}=={'А','Б'}


@pytest.mark.asyncio
async def test_comparison_defaults_to_all_indicators_and_supports_explicit_subset(fixture):
    p,m,_=fixture
    spec={'key':'comparison','component_type':'HsComparisonChart','title':'Сравнение','dataset_id':1,'axes':[{'axis':'objects','fields':['customer']},{'axis':'indicators','fields':['html']},{'axis':'values','metrics':[{'field':'actual','kind':'sum','label':'Факт'}]}],'compare_values':['А','Б'],'indicator_values':['<p>A</p>']}
    assert (await call(m,'giga_set_visualization',report_id=42,visualization=spec))['success']
    snapshot=await call(m,'giga_inspect_report',report_id=42)
    assert set(snapshot['components'][0]['spec']['indicator_values'])=={'<p>A</p>','<p>B</p>'}
    spec['indicator_mode']='selected'
    assert (await call(m,'giga_set_visualization',report_id=42,visualization=spec))['success']
    snapshot=await call(m,'giga_inspect_report',report_id=42)
    assert snapshot['components'][0]['spec']['indicator_values']==['<p>A</p>']


@pytest.mark.asyncio
async def test_truncated_source_query_never_claims_complete_and_time_is_raw_text(fixture):
    p,m,_=fixture
    result=await call(m,'giga_query_dataset',dataset_id=1,metrics=[{'kind':'raw','field':'customer','label':'Заказчик'}],limit=1)
    assert result['success'] and result['truncated'] and not result['query_complete']
    assert result['execution_completed'] and 'limit=1000' in result['next_action']
    p.fields[1]['type']='time';p.db.execute("UPDATE source SET plan='12:30:00'")
    result=await call(m,'giga_query_dataset',dataset_id=1,metrics=[{'kind':'raw','field':'plan','label':'Время'}])
    assert result['success'] and result['query_complete'] and {r['metric_0'] for r in result['rows']}=={'12:30:00'}


@pytest.mark.asyncio
async def test_count_rows_and_count_nonnull_field_have_distinct_semantics(fixture):
    p,m,_=fixture
    p.db.execute("UPDATE source SET actual=NULL WHERE customer='Б'")
    result=await call(m,'giga_query_dataset',dataset_id=1,metrics=[{'kind':'count','label':'Все строки'},{'kind':'count','field':'actual','label':'Заполненные'}])
    assert result['success'],result
    assert result['rows']==[{'metric_0':2,'metric_1':1,'source_row_count':2}]
    assert (await call(m,'giga_upsert_components',report_id=42,components=[{'key':'rows','kind':'kpi','title':'Количество строк','dataset_id':1,'category':'','metrics':[{'kind':'count','label':'Строки'}]}]))['success']
    snapshot=await call(m,'giga_inspect_report',report_id=42)
    assert snapshot['checks_passed']
    assert list(snapshot['data']['rows']['rows'][0].values())==['2']


@pytest.mark.asyncio
async def test_count_field_still_requires_real_field_and_rejects_sql(fixture):
    p,m,_=fixture
    for field in ['*','unknown','COUNT(*)']:
        result=await call(m,'giga_query_dataset',dataset_id=1,metrics=[{'kind':'count','field':field,'label':'Строки'}])
        assert not result['success'],result
    assert p.calls[('recordsets','create')]==0


@pytest.mark.asyncio
async def test_native_count_without_field_compiles_as_count_star(fixture):
    p,m,_=fixture
    spec={'key':'counts','component_type':'HsBarAMchartsChart','title':'Количество строк','dataset_id':1,'axes':[{'axis':'categories','fields':['customer']},{'axis':'values','metrics':[{'kind':'count','label':'Строки'}]}]}
    result=await call(m,'giga_set_visualization',report_id=42,visualization=spec)
    assert result['success'],result
    cfg=p.reports[42]['grid']['components']['0']['config']
    value=next(a for a in cfg['axes'] if a['type']=='values')['fields'][0]
    assert value['calc']=='COUNT(*)' and value['type']=='calculated' and value['agg'] is None
    snapshot=await call(m,'giga_inspect_report',report_id=42)
    assert snapshot['checks_passed'],snapshot
    assert all(1 in row.values() for row in snapshot['data']['counts']['rows'])


@pytest.mark.asyncio
async def test_numeric_axes_require_explicit_metrics_before_any_write(fixture):
    p,m,_=fixture
    spec={'key':'bubble','component_type':'HsBubbleAMchartsChart','title':'Пузыри','dataset_id':1,'axes':[{'axis':'categories','fields':['customer']},{'axis':'xvalues','fields':['plan']},{'axis':'yvalues','fields':['actual']},{'axis':'values','metrics':[{'field':'zero','kind':'sum','label':'Размер'}]}]}
    before=copy.deepcopy(p.reports[42])
    result=await call(m,'giga_set_visualization',report_id=42,visualization=spec)
    assert not result['success'] and 'AXIS_METRICS_REQUIRED' in result['error']
    assert p.reports[42]==before and p.calls[('reports','update')]==0
    for axis in spec['axes'][1:3]:
        field=axis.pop('fields')[0];axis['metrics']=[{'kind':'sum','field':field,'label':field}]
    assert (await call(m,'giga_set_visualization',report_id=42,visualization=spec))['success']
    assert (await call(m,'giga_inspect_report',report_id=42))['checks_passed']
    cfg=p.reports[42]['grid']['components']['0']['config']
    assert cfg['strictMinMaxEnabled'] and cfg['strictMinMaxPadding']==20


@pytest.mark.asyncio
async def test_explicit_raw_coordinates_with_aggregate_have_executable_source_grain(fixture):
    p,m,_=fixture
    spec={'key':'bubble','component_type':'HsBubbleAMchartsChart','title':'Пузыри','dataset_id':1,'axes':[{'axis':'categories','fields':['customer']},{'axis':'xvalues','metrics':[{'field':'plan','kind':'raw','label':'X'}]},{'axis':'yvalues','metrics':[{'field':'actual','kind':'raw','label':'Y'}]},{'axis':'values','metrics':[{'field':'zero','kind':'sum','label':'Размер'}]}]}
    assert (await call(m,'giga_set_visualization',report_id=42,visualization=spec))['success']
    snapshot=await call(m,'giga_inspect_report',report_id=42)
    assert snapshot['checks_passed'],snapshot
    query=snapshot['verification_plan']['queries'][0]['arguments']
    assert set(query['group_by'])=={'customer','plan','actual'}
    result=await call(m,'giga_query_dataset',**query)
    assert result['success'] and result['query_complete'] and len(result['rows'])==2


@pytest.mark.asyncio
async def test_numeric_axes_reject_raw_text_metric(fixture):
    p,m,_=fixture
    spec={'key':'bar','component_type':'HsBarAMchartsChart','title':'Значения','dataset_id':1,'axes':[{'axis':'categories','fields':['customer']},{'axis':'values','metrics':[{'field':'html','kind':'raw','label':'Недопустимое значение'}]}]}
    result=await call(m,'giga_set_visualization',report_id=42,visualization=spec)
    assert not result['success'] and 'NUMERIC_AXIS_REQUIRED' in result['error']
    assert p.calls[('reports','update')]==0


@pytest.mark.asyncio
async def test_mixed_source_probe_separates_detail_without_changing_aggregate_grain(fixture):
    p,m,_=fixture
    metrics=[{'kind':'ratio_of_sums','numerator':'actual','denominator':'plan','label':'Доля'},{'kind':'raw','field':'actual','label':'Факт'},{'kind':'raw','field':'plan','label':'План'}]
    result=await call(m,'giga_query_dataset',dataset_id=1,metrics=metrics,filters=[{'field':'customer','values':['А']}])
    assert result['success'] and result['grain_split'] and result['query_complete']
    assert result['rows']==[{'metric_0':1.0,'source_row_count':1}]
    assert [c['metric']['kind'] for c in result['columns']]==['ratio_of_sums']
    detail=result['diagnostic_detail']
    assert detail['rows']==[{'metric_0':100.0,'metric_1':100.0}]
    assert detail['criteria']['filters']==result['criteria']['filters']==[{'field':'customer','values':['А']}]
    assert result['criteria']['group_by']==detail['criteria']['group_by']==[]
    assert not result['atomic_snapshot_guaranteed'] and p.calls[('reports','update')]==0


@pytest.mark.asyncio
async def test_split_details_retain_group_keys_and_truncation_blocks_completeness(fixture):
    p,m,_=fixture
    metrics=[{'kind':'sum','field':'actual','label':'Факт'},{'kind':'raw','field':'plan','label':'План'}]
    result=await call(m,'giga_query_dataset',dataset_id=1,metrics=metrics,group_by=['customer'],limit=1)
    assert result['success'] and result['grain_split'] and result['truncated'] and not result['query_complete']
    detail=result['diagnostic_detail']
    assert {c['metric']['field'] for c in detail['columns']}=={'plan','customer'}
    assert detail['truncated'] and detail['criteria']['group_by']==[]
    assert result['criteria']['group_by']==['customer']


@pytest.mark.asyncio
async def test_split_validates_every_metric_before_any_recordset_query(fixture):
    p,m,_=fixture
    for raw_field in ['unknown','COUNT(*)']:
        result=await call(m,'giga_query_dataset',dataset_id=1,metrics=[{'kind':'sum','field':'actual','label':'Факт'},{'kind':'raw','field':raw_field,'label':'Недопустимое поле'}])
        assert not result['success']
    result=await call(m,'giga_query_dataset',dataset_id=1,metrics=[{'kind':'ratio_of_sums','denominator':'plan','label':'Нет числителя'},{'kind':'raw','field':'actual','label':'Факт'}])
    assert not result['success'] and p.calls[('recordsets','create')]==0


@pytest.mark.asyncio
async def test_pure_raw_incompatible_grouping_is_not_automatically_reinterpreted(fixture):
    p,m,_=fixture
    result=await call(m,'giga_query_dataset',dataset_id=1,metrics=[{'kind':'raw','field':'actual','label':'Факт'}],group_by=['customer'])
    assert not result['success'] and 'RAW_GROUPING_CONFLICT' in result['error']
    assert p.calls[('recordsets','create')]==0


@pytest.mark.asyncio
async def test_split_detail_failure_never_returns_partial_success(fixture):
    p,m,_=fixture
    original=p.api_call
    async def fail_detail(entity,action,object_id=None,data=None):
        result=await original(entity,action,object_id,data)
        if entity=='recordsets' and not any(f.get('alias')=='source_row_count' for f in data[0].get('select',[])):
            return {'status':400,'data':[]}
        return result
    p.api_call=fail_detail
    result=await call(m,'giga_query_dataset',dataset_id=1,metrics=[{'kind':'sum','field':'actual','label':'Итог'},{'kind':'raw','field':'plan','label':'Строки'}])
    assert not result['success'] and 'rows' not in result and p.calls[('recordsets','create')]==2


@pytest.mark.asyncio
async def test_detail_column_cap_does_not_silently_drop_group_context(fixture):
    p,m,_=fixture
    groups=[f'group{i}' for i in range(10)]
    p.fields += [{'name':name,'alias':name,'type':'string'} for name in groups]
    metrics=[{'kind':'sum','field':'actual','label':'Итог'}]+[{'kind':'raw','field':'plan','label':f'Строки{i}'} for i in range(23)]
    result=await call(m,'giga_query_dataset',dataset_id=1,metrics=metrics,group_by=groups)
    assert not result['success'] and 'DETAIL_COLUMN_LIMIT' in result['error']
    assert p.calls[('recordsets','create')]==0


@pytest.mark.parametrize('kind,used',[('ratio_of_sums',{'numerator':'actual','denominator':'plan'}),('difference_of_sums',{'numerator':'actual','denominator':'plan'}),('constant',{'constant':1}),('sum',{'field':'actual'}),('avg',{'field':'actual'}),('min',{'field':'actual'}),('max',{'field':'actual'}),('raw',{'field':'actual'}),('count',{'field':'actual'})])
def test_source_identity_only_uses_sql_significant_metric_properties(kind,used):
    base={'kind':kind,'label':'Метрика',**used};noisy={**base,**{k:v for k,v in {'field':'unused','numerator':'unused_n','denominator':'unused_d','constant':77}.items() if k not in used}}
    identify=lambda metric:query_identity({'dataset_id':1,'metrics':[metric]})
    assert identify(base)==identify(noisy)
    changed={**base, next(iter(used)):2 if kind=='constant' else 'other'}
    assert identify(base)!=identify(changed)
