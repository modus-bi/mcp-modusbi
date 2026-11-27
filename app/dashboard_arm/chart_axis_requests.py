"""Resolve chart-axis edits against the existing report before enabling a write."""
import json
import re


AXIS_TOOL = "giga_set_chart_axis"
QUOTED = re.compile(r'«([^»]+)»|"([^"\n]+)"')
AXIS = re.compile(r"\bос(?:ь|и|ью|ей|ям|ях)\b", re.I)
CHART_REFERENCE = re.compile(r'\b(?:график|диаграмм|гистограмм|лини)\w*\s+(?:с названием\s+)?[«"]([^»"]+)[»"]', re.I)
TIME = re.compile(r"дат[а-я]*|месяц[а-я]*|хронолог|календар|\bгод[уаом]*\b", re.I)
MONTH = re.compile(r"\b(янв|фев|мар|апр|май|мая|июн|июл|авг|сен|окт|ноя|дек)[а-я]*\.?", re.I)
MONTH_NUMBER = {name:index for index,name in enumerate("янв фев мар апр май июн июл авг сен окт ноя дек".split(), 1)}
MONTH_NUMBER["мая"] = 5
STOPWORDS = {"график", "диагр", "линия", "линии", "столб", "месяц", "времен", "отчет"}


def _clean(text):
    return ' '.join(re.findall(r"[а-яёa-z0-9_]+", text.lower().replace('ё', 'е')))


def _stems(text):
    return {word[:4] for word in _clean(text).split() if len(word) >= 4 and not any(word.startswith(stop) for stop in STOPWORDS)}


def _chart_name(chart):
    return chart.get("spec", {}).get("title") or chart.get("title") or chart["key"]


def _order(text):
    newer_first = bool(re.search(r"убыван|от (?:нов\w+|позд\w+|свеж\w+) к (?:стар\w+|ран\w+)|сначала (?:нов\w+|свеж\w+|позд\w+)", text))
    older_first = bool(re.search(r"возрастан|хронолог|как в календар|от (?:ран\w+|стар\w+) к (?:позд\w+|нов\w+|свеж\w+)|сначала (?:стар\w+|ран\w+)", text))
    if newer_first or older_first:
        return None if newer_first and older_first else "desc" if newer_first else "asc"
    dates = list(MONTH.finditer(text))
    if len(dates) > 1:
        relation = text[dates[0].end():dates[1].start()].strip()
        numbers = [MONTH_NUMBER[m[1]] for m in dates]
        if relation in {"до", "перед", "после"} and len(set(numbers)) > 1 and numbers[0] in {min(numbers), max(numbers)}:
            return "asc" if (numbers[0] == max(numbers)) == (relation == "после") else "desc"
    return None


def _date_format(text):
    explicit = re.search(r"(?<![\w.])(DD\.MM\.YYYY HH:mm|DD\.MM\.YYYY|YYYY-MM-DD|MM\.YYYY|MMMM YYYY|MMM YYYY|MMMM|MMM|YYYY)(?![\w.])", text)
    if explicit:
        return explicit[1]
    text = text.lower()
    if re.search(r"\bтолько год\b", text):
        return "YYYY"
    if re.search(r"\b(?:0?[1-9]|[12]\d|3[01])\.\d{2}\.\d{4}\b", text):
        return "DD.MM.YYYY"
    if re.search(r"\b(?:0[1-9]|1[0-2])\.\d{4}\b", text):
        return "MM.YYYY"
    if re.search(r"(?:без года|только названи[ея] месяц)", text):
        return "MMM" if re.search(r"кратк|коротк|сокращ", text) else "MMMM"
    if example := re.search(MONTH.pattern + r"\s+\d{4}\b", text):
        month = example[0].split()[0]
        abbreviated = month.endswith('.') or len(month) <= 4 and month not in {'март', 'май', 'мая', 'июнь', 'июля', 'июль', 'июня'}
        return "MMM YYYY" if abbreviated else "MMMM YYYY"
    if re.search(r"\b(?:с годом|и год|вместе с годом)\b", text):
        if re.search(r"полн\w+", text):
            return "MMMM YYYY"
        if re.search(r"кратк|коротк|сокращ", text):
            return "MMM YYYY"
    return None


def _clarify(question, choices=(), missing=""):
    return {"status":"clarify", "question":question, "choices":list(choices), "axis_missing":missing}


def resolve_chart_axis(query, components, pending=None, image_title=None):
    """Return one grounded patch, a specific question, or no chart-axis intent."""
    pending = pending or {}
    continued = pending.get("axis_missing") and len(query) <= 160 and not re.search(r"\b(?:создай|построй|добавь|удали)\b", query, re.I)
    original = pending.get("original_request", "") if continued else ""
    text = f"{original} {query}".strip()
    bare = QUOTED.sub(" ", text).lower()
    explicit_axis = bool(AXIS.search(bare))
    is_field_alias = re.search(r"(?:алиас|подпис\w+ поля|переимен\w+ поле)", bare)
    non_chart = re.search(r"\b(?:таблиц|таблич|колонк|фильтр|карточк|срез)\w*", bare)
    if is_field_alias or non_chart or not explicit_axis and re.search(r"\bв списк\w*", bare):
        return None
    order = _order(bare)
    date_format = _date_format(text) if TIME.search(text) or explicit_axis or re.search(r"\b(?:MM|MMM|YYYY)\b", text) else None
    date_change = bool(date_format or re.search(r"покороче|формат\w*\s+дат|подпис\w*\s+дат|по (?:имени|названи\w+) месяц", bare))
    sort_change = bool(order or re.search(r"сортир|перестав|поряд\w+|наоборот", bare))
    title_change = explicit_axis and not date_change and bool(re.search(r"назов|переимен|заголов|подпис|названи", bare))
    if not (title_change or explicit_axis or TIME.search(bare) and (sort_change or date_change)):
        return None
    if re.search(r"^\s*(?:что|почему|какие|как сейчас|покажи, как)\b", query, re.I) or re.search(r"\b(?:создай|построй|добавь)\s+(?:нов\w+\s+)?(?:график|диаграмм|гистограмм|лини)", bare):
        return None
    charts = [x for x in components if x.get("key") and x.get("chart_axes")]
    if not charts:
        return _clarify("В каком линейном или столбчатом графике нужно изменить ось?", missing="chart") if explicit_axis else None
    normalized = f" {_clean(text)} "
    exact = [x for x in charts if any(f" {_clean(name)} " in normalized for name in (_chart_name(x),x["key"]))]
    named_chart = CHART_REFERENCE.search(query)
    if named_chart and not any(_clean(named_chart[1]) in {_clean(_chart_name(x)),_clean(x["key"])} for x in charts):
        return _clarify("Не нашёл график с таким названием. В каком графике изменить ось?", [_chart_name(x) for x in charts], "chart")
    if continued and pending.get("axis_missing") == "chart":
        exact_reply = [x for x in charts if _clean(query) in {_clean(_chart_name(x)), _clean(x["key"])}]
        if exact_reply:
            exact = exact_reply
    options = exact or charts
    if not exact:
        kind = "line" if re.search(r"\bлини[яиюй]|линейн", bare) else "bar" if re.search(r"столб(?:чат|ик|ц)|гистограмм", bare) else None
        if kind:
            options = [x for x in charts if x.get("kind") == kind or x.get("chart_type") == kind]
        if len(options) > 1:
            ranks = [(len(_stems(_chart_name(x)) & _stems(bare)), x) for x in options]
            highest = max(rank for rank, _ in ranks)
            if highest:
                options = [x for rank,x in ranks if rank == highest]
    if len(options) != 1:
        choices = [_chart_name(x) for x in (options or charts)]
        return _clarify("В каком графике изменить ось?", choices, "chart")
    chart = options[0]
    title = image_title if title_change else None
    if title_change and not title:
        chart_names = {_clean(_chart_name(x)) for x in charts}
        quoted = [a or b for a,b in QUOTED.findall(text) if _clean(a or b) not in chart_names]
        if len(quoted) == 1:
            title = quoted[0]
        elif continued and pending.get("axis_missing") == "title":
            title = query.strip()
        elif trailing := re.search(r"(?:назови|подпиши)\s+(?:[xyхув]\s+)?ось\s+(.+)$|(?:заголовок|подпись)\s+оси\s*[:—]\s*(.+)$", text, re.I):
            title = trailing[1] or trailing[2]
        if not title or len(title) > 160 or re.search(r"(?:по-другому|иначе|новым названием)$", title, re.I):
            return _clarify(f"Какой заголовок дать оси графика «{_chart_name(chart)}»?", missing="title")
    is_horizontal = bool(chart.get("spec", {}).get("horizontal"))
    horizontal_axis = bool(re.search(r"горизонтальн\w*\s+ос[ьи]|\bось\s*[xх]\b|\bпо\s+[xх]\b", bare))
    vertical_axis = bool(re.search(r"вертикальн\w*\s+ос[ьи]|\bось\s*[yу]\b|\bпо\s+[yу]\b", bare))
    role = None
    if horizontal_axis != vertical_axis:
        role = "values" if horizontal_axis == is_horizontal else "categories"
    if role is None and continued and pending.get("axis_missing") == "axis":
        role = "categories" if _clean(query) == "ось категорий" else "values" if _clean(query) == "ось значений" else None
    both_axes = horizontal_axis and vertical_axis or re.search(r"\b(?:[xх]\s*[,и]\s*[yу]|[yу]\s*[,и]\s*[xх])\b", bare)
    if both_axes:
        return _clarify("Какую ось изменить?", ["Ось категорий", "Ось значений"], "axis")
    if (sort_change or date_change or re.search(r"ос[ьи]\s+(?:времени|дат|месяц|категор)", bare)) and role is None:
        role = "categories"
    if role is None:
        return _clarify(f"Какую ось графика «{_chart_name(chart)}» изменить?", ["Ось категорий", "Ось значений"], "axis")
    fields = chart["chart_axes"].get(role, {}).get("fields", [])
    if sort_change or date_change:
        if role != "categories" or len(fields) != 1 or fields[0].get("type") not in {"date", "datetime", "timestamp"}:
            return _clarify(f"Какое поле даты на оси категорий графика «{_chart_name(chart)}» использовать?", missing="field")
        if sort_change and not order and "наоборот" in bare:
            order = {"asc":"desc", "desc":"asc"}.get(fields[0].get("order"))
        if sort_change and not order:
            return _clarify("В каком порядке показать даты: от ранних к поздним или от поздних к ранним?", ["От ранних к поздним", "От поздних к ранним"], "order")
        if date_change and not date_format:
            return _clarify("Как подписать даты на оси: «янв. 2026», «январь 2026» или «01.2026»?", ["янв. 2026", "январь 2026", "01.2026"], "date_format")
    patch = {k:v for k,v in {"title":title,"order":order,"date_format":date_format}.items() if v}
    if not patch:
        return _clarify("Что изменить на оси: заголовок, формат дат или порядок дат?", missing="setting")
    return {"status":"ready", "arguments":{"key":chart["key"],"axis":role,**patch}, "chart":_chart_name(chart)}


def request_scoped_action(ask, catalogue, decision, report_id, query, tool_name, *, exact_schema=False):
    """Let GigaChat call one allowed tool, then bind the verified change."""
    tool = next(t for t in catalogue if t["name"] == tool_name)
    args = {"report_id":report_id, **decision["arguments"]}
    if exact_schema:
        schema = tool['parameters']
        tool = {**tool, 'parameters':{**schema,
            'properties':{k:schema['properties'][k] for k in args}, 'required':list(args)}}
    messages = [{"role":"system","content":f"Выполни проверенную правку через {tool_name}. Используй только эти параметры: " + json.dumps(args,ensure_ascii=False)},
                {"role":"user","content":query}]
    response = ask(messages,[tool],{"name":tool_name})
    call = response.get("function_call") or {}
    if call.get("name") != tool_name:
        raise ValueError("GigaChat не подтвердил вызов нужного инструмента")
    proposed = call.get("arguments") or {}
    if isinstance(proposed,str):
        proposed = json.loads(proposed)
    if not isinstance(proposed, dict) or any(proposed.get(key) != args[key] for key in ("report_id", "key", "axis") if key in args):
        raise ValueError("GigaChat выбрал другой объект. Изменение остановлено.")
    return args, proposed
