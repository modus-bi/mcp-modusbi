"""Report-derived source probes, independent of any business example or model."""
import hashlib
import json


def metric_calculation(metric):
    kind=metric.get('kind','sum')
    roles=('numerator','denominator') if kind in {'ratio_of_sums','difference_of_sums'} else ('constant',) if kind=='constant' else ('field',)
    result={'kind':kind}
    for key in roles:
        value=metric.get(key,0.0 if key=='constant' else '')
        if key=='constant':value=float(value) or 0.0
        if value not in (None,''):result[key]=value
    return result


def query_identity(arguments):
    """Names/formatting do not change the source calculation being checked."""
    return {
        'dataset_id': arguments['dataset_id'],
        'group_by': sorted(arguments.get('group_by', [])),
        'metrics': sorted((
            metric_calculation(m)
            for m in arguments.get('metrics', [])
        ), key=lambda m: json.dumps(m, sort_keys=True)),
    }


def verification_plan(components):
    """Derive probes from saved semantic roles, never a handwritten report gold."""
    queries = {}
    filters = []
    for component in components:
        spec = component.get('spec') or {}
        if component.get('kind') == 'filter':
            continue
        dataset_id = spec.get('dataset_id')
        if not dataset_id:
            continue
        axes = spec.get('axes', [])
        metrics = list(spec.get('metrics', []))
        dimensions = list(dict.fromkeys([spec[n] for n in ('category', 'series') if spec.get(n)]))
        for axis in axes:
            if axis['axis'] in {'values', 'xvalues', 'yvalues'}:
                metrics += axis.get('metrics', [])
                metrics += [{'kind': 'raw', 'field': f, 'label': f} for f in axis.get('fields', [])]
            else:
                dimensions += axis.get('fields', [])
        dimensions = list(dict.fromkeys(dimensions))
        if not metrics:
            continue
        aggregated = any(m['kind'] != 'raw' for m in metrics)
        if aggregated:
            # An explicitly raw numeric axis is part of the actual grouping
            # grain when other axes aggregate. Never emit invalid mixed SQL.
            dimensions = list(dict.fromkeys(dimensions + [m['field'] for m in metrics if m['kind']=='raw']))
        else:
            metrics += [{'kind': 'raw', 'field': f, 'label': f} for f in dimensions]
            dimensions = []
        canonical = {}
        for metric in metrics:
            metric = {**metric_calculation(metric),'label':metric.get('label') or metric.get('field') or 'Показатель'}
            # Formatting is intentionally removed: compare typed source values.
            metric={k:v for k,v in metric.items() if v not in (None,'') and (k!='constant' or metric['kind']=='constant')}
            canonical[json.dumps(query_identity({'dataset_id': dataset_id, 'metrics': [metric]}), sort_keys=True)] = metric
        metrics = list(canonical.values())
        for start in range(0, len(metrics), 24):
            args = {'dataset_id': dataset_id, 'metrics': metrics[start:start+24],
                    'group_by': dimensions, 'filters': [], 'limit': 1000}
            identity = query_identity(args)
            qid = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()[:16]
            item = queries.setdefault(qid, {'id': qid, 'tool': 'giga_query_dataset', 'arguments': args, 'components': []})
            item['components'].append(component['key'])
    return {'status': 'source_comparison_required', 'queries': list(queries.values()),
            'filters': filters, 'browser_verified': False,
            'scope': 'Actual saved fields, grain and calculations. Execute these source probes, compare returned values with report data, repeat with the shared filter and reset. Truncated probes are incomplete; do not claim success. Local component selections may restrict the displayed subset. Business meaning and browser readability require separate verification.'}
