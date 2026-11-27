"""Resolve existing table, title and filter edits before allowing a write."""
import re

from .chart_axis_requests import QUOTED, _clean, _date_format


FIELD_TOOL = "giga_set_field_display"
TITLE_TOOL = "giga_rename_component"
FILTER_TOOL = "giga_select_filter"
TABLE = re.compile(r"\b(?:таблиц|таблич|в списк)\w*", re.I)
NAMED_COMPONENT = re.compile(r'\b(?:таблиц\w*|табличк\w*|карточк\w*|график\w*|диаграмм\w*|фильтр\w*|компонент\w*)\s+[«"]([^»"]+)[»"]', re.I)
COLUMN = re.compile(r"\b(?:колонк|столб(?:ец|цы|цов|це|ца)|шапк|пол[ея]|алиас)\w*", re.I)
RENAME = re.compile(r"переимен|назов|назван|назыв|подпиш|переподпиш|заголов|\bзаг\b|напиши|алиас|\bимя\b|→|подпис", re.I)
CHART = re.compile(r"график|диаграмм|гистограмм|столбчат|столбик|\bлини\w*|линейн", re.I)
FILTER = re.compile(r"фильтр|срез|заказчик|клиент|покупател", re.I)
FILTER_ACTION = re.compile(r"выбер|выбери|остав|покаж|отфильтр|сними|сброс|включ|переключ|только|нужен|выбрать|срез", re.I)
UNRELATED = re.compile(r"^\s*(?:а теперь|вместо этого|отмени|создай|добавь|удали|построй|покажи, как)\b", re.I)


def _title(component):
    title = (component.get("filter") or {}).get("alias") or (component.get("spec") or {}).get("title") or component.get("title")
    return title if isinstance(title, str) and title else component["key"]


def _matches(text, names):
    phrase = f" {_clean(text)} "
    return any((value := _clean(name)) and f" {value} " in phrase for name in names if isinstance(name, str))


def _stems(text):
    ignored = {"граф", "диаг", "гист", "лини", "лине", "стол", "табл", "карт", "комп", "пере", "назо", "назв", "заг", "подп", "пока", "филь"}
    return {word[:4] for word in _clean(text).split() if len(word) >= 4 and word[:4] not in ignored}


def _named_component(text):
    named = NAMED_COMPONENT.search(text)
    if named and not re.search(r'\bшапк\w*\s*$', text[:named.start()],re.I):
        return named
    return None


def _component_candidates(text, choices, *, by_type=False):
    if named := _named_component(text):
        return [c for c in choices if _clean(named[1]) in {_clean(_title(c)),_clean(c['key'])}]
    exact = [c for c in choices if _matches(text, (_title(c),c["key"]))]
    if exact:
        return exact
    if by_type:
        if TABLE.search(text):
            choices = [c for c in choices if c.get("kind") == "table"]
        elif re.search(r"карточк|\bkpi\b|\bкпи\b|компонент\w*\s+с\s+общей суммой", text,re.I):
            choices = [c for c in choices if c.get("kind") == "kpi"]
        elif CHART.search(text):
            kind = "line" if re.search(r"\bлини\w*|линейн",text,re.I) else "bar" if re.search(r"столбчат|столбик|гистограмм",text,re.I) else None
            choices = [c for c in choices if c.get("kind") in {"bar","line","donut","native"} and (kind is None or kind in {c.get("kind"),c.get("chart_type")})]
    if len(choices) > 1:
        words = _stems(text)
        ranked = [(len(words & _stems(_title(c))),c) for c in choices]
        best = max(score for score,_ in ranked)
        if best:
            return [c for score,c in ranked if score == best]
    return choices


def _literal(text):
    match = QUOTED.fullmatch(text.strip().rstrip('.').strip())
    return (match[1] or match[2]) if match else text.strip().rstrip('.')


def _new_name(text, known):
    quotes = list(QUOTED.finditer(text))
    if quotes:
        last = quotes[-1]
        value = last[1] or last[2]
        prefix = text[:last.start()]
        separates = re.search(r'(?:\b(?:в|на|как)\s*|→\s*|[—:]\s*|пусть будет\s*)$',prefix,re.I)
        named = _named_component(text)
        existing_reference = named and named.end() == last.end() and RENAME.search(text[last.end():])
        if not existing_reference and (_clean(value) not in known or separates):
            return value, text[:last.start()] + ' ' + text[last.end():]
    if plain := re.search(r'(?:→|\bалиас\b\s*[:—]|\bзаголовок\s*[:—]|\bназвание\s*[:—])\s*([^«"\n]+)$',text,re.I):
        return _literal(plain[1]), text[:plain.start()]
    return None,text


def _ask(family, missing, question, choices=(), **context):
    return {'status':'clarify','question':question,'choices':list(dict.fromkeys(choice for choice in choices if 0 < len(choice) <= 120)),
            'guarded_edit':{'family':family,'missing':missing,**context}}


def _ready(tool, component, **arguments):
    return {'status':'ready','tool':tool,'component_title':_title(component),'arguments':{'key':component['key'],**arguments}}


def _table_fields(table):
    overrides = {field['field']:field.get('label') for field in table.get('field_display',[]) if field.get('field') and field.get('label')}
    return {m['field']:overrides.get(m['field'],m.get('label') or m['field']) for m in (table.get('spec') or {}).get('metrics',[]) if m.get('field')}


def _select_field(text, fields):
    exact = [field for field,label in fields.items() if _matches(text,(field,label))]
    if exact:
        return exact
    reference = _stems(text)
    scores = [(len(reference & _stems(label)),field) for field,label in fields.items()]
    top = max((score for score,_ in scores),default=0)
    return [field for score,field in scores if top and score == top]


def _resolve_column(query, tables, source_fields, pending):
    if not tables:
        return None
    table = next((c for c in tables if c['key'] == pending.get('key')),None)
    change = pending.get('change')
    label, field = pending.get('label'), pending.get('field')
    date_format = pending.get('date_format')
    if table is None:
        candidates = _component_candidates(query,tables)
        if len(candidates) != 1:
            return _ask('column','table','В какой таблице изменить столбец?', [_title(c) for c in candidates or tables], request=pending.get('request') or query)
        table = candidates[0]
        if pending.get('missing') == 'table':
            query = pending.get('request') or query
    fields = _table_fields(table)
    key = table['key']
    name = _title(table)
    step = pending.get('missing')
    if step == 'order' or step == 'change' and re.search(r'поряд|перестав',query,re.I):
        return _resolve_order(query,table,fields)
    bare = QUOTED.sub(' ',query)
    if step == 'date_format' or not change and re.search(r'формат|дат|месяц',bare,re.I) and (not RENAME.search(bare) or _date_format(query)):
        change = 'date'
    if not change and (RENAME.search(query) or re.search(r'подпис|шапк|вместо',query,re.I)):
        change = 'label'
    if not change:
        return _ask('column','change',f'Что изменить в столбцах таблицы «{name}»?', ['Подпись столбца','Формат даты','Порядок столбцов'],key=key)
    if change == 'date':
        schema = source_fields.get(table.get('dataset_id'),[])
        fields = {f['name']:fields[f['name']] for f in schema if f.get('type') in {'date','datetime','timestamp'} and f.get('name') in fields}
        date_format = date_format or _date_format(query)
    reference = query
    if change == 'label':
        if step == 'label':
            label = _literal(query)
        elif not label:
            known = {_clean(x) for x in [name,*fields,*fields.values()]}
            label,reference = _new_name(query,known)
    if field not in fields:
        if named := _named_component(reference):
            reference = reference[:named.start()] + ' ' + reference[named.end():]
        candidates = _select_field(reference,fields)
        if change == 'date' and not candidates and len(fields) == 1:
            candidates = list(fields)
        if len(candidates) != 1:
            return _ask('column','field',f'Какой столбец таблицы «{name}» изменить?', fields.values(),key=key,change=change,label=label,date_format=date_format)
        field = candidates[0]
    if change == 'label' and not label:
        return _ask('column','label',f'Как назвать столбец «{fields[field]}» в таблице «{name}»?', key=key,field=field,change=change)
    if change == 'date' and not date_format:
        return _ask('column','date_format',f'В каком формате показать даты в столбце «{fields[field]}»?', ['01.2026','янв. 2026','январь 2026'], key=key,field=field,change=change)
    return _ready(FIELD_TOOL,table,field=field,**({'label':label} if change=='label' else {'date_format':date_format}))


def _resolve_order(query, table, fields):
    parts = [_literal(item.strip()) for item in re.split(r'[,;→\n]+',query)]
    by_name = {_clean(label):field for field,label in fields.items()}
    by_name.update({_clean(field):field for field in fields})
    order = [by_name.get(_clean(item)) for item in parts]
    if len(order) != len(fields) or set(order) != set(fields):
        current = ', '.join(f'«{label}»' for label in fields.values())
        return _ask('column','order',f'В каком порядке поставить столбцы? Перечислите их через запятую. Сейчас: {current}.', key=table['key'])
    spec = table['spec']
    metrics = {metric['field']:metric for metric in spec['metrics']}
    columns = [dict({k:metrics[field][k] for k in ('format','decimals','cell_rules') if k in metrics[field]}, field=field,label=fields[field]) for field in order]
    layout = {k:spec[k] for k in ('row','width','height') if k in spec}
    return _ready('giga_set_table',table,dataset_id=table['dataset_id'],title=_title(table),columns=columns,columns_mode='replace',**layout)


def _resolve_title(query, eligible, pending):
    if not eligible:
        return None
    component = next((c for c in eligible if c['key'] == pending.get('key')),None)
    title = pending.get('title')
    if pending.get('missing') == 'title':
        title, reference = _literal(query),''
    elif not title:
        title,reference = _new_name(query,{_clean(_title(c)) for c in eligible})
    else:
        reference = query
    if component is None:
        candidates = _component_candidates(reference,eligible,by_type=True)
        if len(candidates) != 1:
            kind = 'график' if CHART.search(reference) else 'компонент'
            return _ask('title','component',f'Какой {kind} переименовать?', [_title(c) for c in candidates or eligible],title=title)
        component = candidates[0]
    if not title:
        return _ask('title','title',f'Как назвать компонент «{_title(component)}»?', key=component['key'])
    return _ready(TITLE_TOOL,component,title=title)


def _requested_values(query, label, allowed):
    text = re.sub(r'^\s*[ВУСК]\s+', '', query.strip())
    exact, unknown = [], []
    for quoted in (a or b for a,b in QUOTED.findall(text)):
        if _clean(quoted) == _clean(label):
            continue
        candidates = [v for v in allowed if _clean(v) == _clean(quoted) or _clean(v).split()[-1:] == [_clean(quoted)]]
        if len(candidates) == 1:
            exact.append(candidates[0])
        else:
            unknown.append(quoted)
    for value in sorted(allowed,key=len,reverse=True):
        if value and _clean(value) != _clean(label) and _matches(text,(value,)):
            exact.append(value)
    for code in re.findall(r'(?<!\w)(?:[А-ЯЁA-Z]|\d+)(?!\w)', QUOTED.sub(' ',text)):
        matching = [v for v in allowed if _clean(v).split()[-1:] == [_clean(code)]]
        if len(matching) == 1:
            exact.append(matching[0])
        elif not any(_matches(v,(code,)) for v in exact):
            unknown.append(code)
    return list(dict.fromkeys(exact)),list(dict.fromkeys(unknown))


def _resolve_filter(query, filters, read_values, pending):
    if not filters:
        return None
    chosen = next((c for c in filters if c['key'] == pending.get('key')),None)
    if chosen is None:
        candidates = _component_candidates(query,filters)
        if len(candidates) != 1:
            return _ask('filter','filter','Какой фильтр изменить?', [_title(c) for c in candidates], request=pending.get('request') or query)
        chosen = candidates[0]
    if pending.get('missing') == 'filter':
        query = pending.get('request') or query
    label = _title(chosen)
    if re.search(r'сними\s+фильтр|сбрось|верни\s+всех|очисти\s+фильтр',query,re.I):
        return _ready(FILTER_TOOL,chosen,values=[])
    allowed = read_values(chosen['key'])
    if re.search(r'\bостальны[ех]\b', query,re.I):
        query = re.split(r'\bостальны[ех]\b',query,1,flags=re.I)[0]
    values, unknown = _requested_values(query,label,allowed)
    if unknown:
        return _ask('filter','value',f'Какое значение выбрать в фильтре «{label}»? Вариант «{unknown[0]}» отсутствует в источнике.', allowed,key=chosen['key'])
    if not values:
        return _ask('filter','value',f'Какое значение выбрать в фильтре «{label}»?', allowed,key=chosen['key'])
    return _ready(FILTER_TOOL,chosen,values=values)


def resolve_component_edit(query, components, source_fields, read_values, previous=None):
    """Resolve supported edit requests or return a question with a concrete missing input."""
    pending = (previous or {}).get('guarded_edit') or {}
    if UNRELATED.search(query):
        pending = {}
    family = pending.get('family')
    bare = QUOTED.sub(' ',query)
    if not family:
        if re.search(r'^\s*(?:какие|какой сейчас|что сейчас|перечисли|покажи значения фильтра)\b',bare,re.I) or re.search(r'\b(?:создай|добавь|удали|привяжи)\b',bare,re.I):
            return None
        if re.search(r'(?:отсортируй|сортировк\w*|сортируй)\b.*\b(?:строк\w*|по\s+колонк\w*|по\s+столбц\w*)',bare,re.I):
            return None
        table_column = TABLE.search(bare) and (COLUMN.search(bare) or re.search(r'дат|только заголовок|в списке.*название\s+\s*на',bare,re.I))
        if table_column or COLUMN.search(bare) and not CHART.search(bare) and re.search(r'столб|колонк',bare,re.I):
            family = 'column'
        elif RENAME.search(bare) and not re.search(r'алиас|\bпол[ея]\b|\bос[ьи]\b|фильтр',bare,re.I):
            family = 'title'
        elif FILTER_ACTION.search(bare) and not TABLE.search(bare) and (FILTER.search(bare) or re.search(r'только строки.*отч[её]т',bare,re.I)):
            family = 'filter'
    if family == 'column':
        return _resolve_column(query,[c for c in components if c.get('key') and c.get('kind')=='table'],source_fields,pending)
    if family == 'title':
        return _resolve_title(query,[c for c in components if c.get('key') and c.get('kind') in {'bar','line','donut','kpi','table','native','rich_text'}],pending)
    if family == 'filter':
        return _resolve_filter(query,[c for c in components if c.get('key') and c.get('kind')=='filter'],read_values,pending)
    return None
