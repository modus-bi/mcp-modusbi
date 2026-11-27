"""Bind a KPI edit to the selected card and an independently resolved source measure."""
import re

KPI_TOOL = "giga_update_kpi"
CARD = re.compile(r"\b(?:карточк\w*|kpi|кпи)\b", re.I)
CARD_REFERENCE = re.compile(r'\b(?:карточк\w*|kpi|кпи)\s+[«"]([^»"]+)[»"]', re.I)
NUMERIC = {"number", "numeric", "integer", "int", "float", "double", "decimal"}
AGGREGATIONS = {
    "avg": r"средн\w*|усредн\w*",
    "max": r"максим\w*|сам\w+\s+больш\w+|наибольш\w+",
    "min": r"миним\w*|сам\w+\s+мал\w+|наименьш\w+",
    "sum": r"сумм\w*|слож\w*|общ\w+\s+итог\w*",
}
GENERIC = {"пока", "поме", "тепе", "выве", "знач", "объе", "объем", "сред", "макс", "мини", "строк", "сумм", "исто", "сохр", "поле", "агре", "цифр", "вмест", "общи", "общу", "отчет", "всем", "весь", "слож", "срез", "бери", "счит", "само", "самы", "боль", "мал", "числ", "заме", "долж", "карточ", "рубл", "итог"}


def _normalize(text):
    return " ".join(re.findall(r"[а-яёa-z0-9_]+", text.lower().replace("ё", "е")))


def _stems(text, *, measure=False):
    result = set()
    for word in _normalize(text).split():
        if len(word) < 4 or any(word.startswith(prefix) for prefix in GENERIC):
            continue
        if measure and word.startswith(("факт", "выполн")):
            result.add("выполн")
        elif measure and word.startswith("просроч"):
            result.add("просроч")
        elif measure and word.startswith("оплат") and not word.startswith("оплаче"):
            continue
        else:
            result.add(word[:4])
    return result


def _title(card):
    return card["spec"].get("title") or card.get("title") or card["key"]


def _question(text, missing, choices=()):
    return {"status":"clarify", "question":text, "kpi_missing":missing, "choices":list(choices)}


def resolve_kpi_request(query, components, sources, pending=None):
    pending = pending or {}
    continued = pending.get("kpi_missing") and len(query) <= 160 and not re.search(r"\b(?:создай|добавь|удали|переименуй)\b", query, re.I)
    text = ((pending.get("original_request", "") + " ") if continued else "") + query
    if not CARD.search(text) or re.search(r"\b(?:назови|переименуй|заголовок|название|создай|добавь|удали|количество строк|число строк)\b", text,re.I):
        return None
    cards = [c for c in components if c.get("key") and c.get("kind") == "kpi" and (c.get("spec") or {}).get("metrics")]
    if not cards:
        return None
    normalized = f" {_normalize(text)} "
    exact = [c for c in cards if any(f" {_normalize(v)} " in normalized for v in (_title(c),c["key"]))]
    named = CARD_REFERENCE.search(query)
    if named and not any(_normalize(named[1]) in {_normalize(_title(c)),_normalize(c["key"])} for c in cards):
        return _question("В какой из существующих карточек изменить расчёт?", "card", [_title(c) for c in cards])
    if continued and pending.get("kpi_missing") == "card":
        selected = [c for c in cards if _normalize(query) in {_normalize(_title(c)),_normalize(c["key"])}]
        exact = selected or exact
    hint = re.search(r"\b(?:карточк\w*|kpi|кпи)\s+(?:с\s+)?([а-яё]+)", text,re.I)
    targets = exact or cards
    if not exact and hint:
        words = _stems(hint[1],measure=True)
        matched = [c for c in cards if words & _stems(_title(c),measure=True)]
        targets = matched or targets

    aggregate_text = text.lower()
    if re.search(r"\bне\s+\w+\s*,?\s+а\s+", aggregate_text):
        aggregate_text = re.split(r"\bне\s+\w+\s*,?\s+а\s+", aggregate_text,maxsplit=1)[1]
    aggregates = [kind for kind, pattern in AGGREGATIONS.items() if re.search(pattern,aggregate_text)]
    if len(aggregates) > 1 and "вместо" in aggregate_text:
        tail = re.split(r"\b(?:выведи|покажи|показывай)\b",aggregate_text)[-1]
        aggregates = [kind for kind, pattern in AGGREGATIONS.items() if re.search(pattern,tail)]
    change_words = re.search(r"покаж|показыва|цифр|посчитай|помен|замен|исправ|поправ|бери|расч[её]т|агрегир|вывед|нужн|теперь",text,re.I)
    if not aggregates and not change_words:
        return None
    if len(targets) != 1:
        return _question("В какой карточке изменить расчёт?", "card", [_title(c) for c in targets])
    card = targets[0]
    metric = card["spec"]["metrics"][0]
    if len(aggregates) > 1:
        return _question("Какой способ расчёта применить к карточке?", "aggregation", ["Сумма", "Среднее", "Минимум", "Максимум"])

    measure_text = text
    for name in (_title(card), card["key"]):
        measure_text = re.sub(re.escape(name), " ", measure_text, flags=re.I)
    if hint and _stems(hint[1],measure=True) & _stems(_title(card),measure=True):
        measure_text = re.sub(re.escape(hint[0]), " ", measure_text, flags=re.I)
    measure_text = re.sub(r"\b(?:карточк\w*|kpi|кпи)\b", " ", measure_text, flags=re.I)
    measure_text = re.sub(r"\bвместо\s+общ\w+\s+итог\w*", " ", measure_text, flags=re.I)
    if re.search(r"\bне\s+\w+\s*,?\s+а\s+",measure_text):
        measure_text = re.split(r"\bне\s+\w+\s*,?\s+а\s+",measure_text,maxsplit=1)[-1]
    if re.search(r"процент|дол[яию]|%",measure_text,re.I) and metric.get("format") != "percent":
        return None
    schema = sources.get(card.get("dataset_id") or card["spec"].get("dataset_id"), [])
    fields = [f for f in schema if f.get("type") in NUMERIC and f.get("name")]
    searchable = f" {_normalize(measure_text)} "
    exact_fields = [f for f in fields if f" {_normalize(f['name'])} " in searchable]
    if not exact_fields and re.search(r"\b[\w]+_[\w]+\b",measure_text):
        return _question("Какое исходное поле использовать? Указанного поля среди числовых полей карточки нет.", "measure")
    candidates = exact_fields
    if not candidates:
        terms = _stems(measure_text,measure=True)
        if metric.get("format") in {"rubles", "number"} and not re.search(r"процент|дол[яию]|%", measure_text,re.I):
            fields = [f for f in fields if "%" not in (f.get("alias") or "") or f["name"] == metric.get("field")]
        scores = []
        for field in fields:
            alias = field.get("alias") or ""
            first_word = _normalize(alias).split()[:1]
            primary = _stems(" ".join(first_word),measure=True)
            scores.append((len(terms & _stems(alias,measure=True)) + len(terms & primary), field))
        highest = max((n for n,_ in scores),default=0)
        candidates = [f for score,f in scores if highest and score == highest]
    if len(candidates) > 1:
        return _question("Какой показатель использовать в карточке?", "measure", [f.get("alias") or f["name"] for f in candidates])
    if not aggregates and not candidates:
        return _question(f"Какой показатель нужно посчитать в карточке «{_title(card)}»?", "measure")
    if candidates:
        field = candidates[0]["name"]
    elif re.search(r"оплат|просроч|выручк|задолж|прибыл|убыт|остаток|марж",measure_text,re.I):
        return _question("Какое поле датасета считать?", "measure")
    else:
        field = metric.get("field")
    if not field:
        return _question("Какое поле использовать для нового расчёта?", "measure")
    aggregation = aggregates[0] if aggregates else metric.get("kind")
    if aggregation not in AGGREGATIONS:
        return _question("Какой способ расчёта использовать для нового показателя?", "aggregation", ["Сумма", "Среднее", "Минимум", "Максимум"])
    return {"status":"ready", "arguments":{"key":card["key"],"field":field,"aggregation":aggregation}, "card":_title(card)}
