#!/usr/bin/env python3
"""Генератор ПУБЛИЧНЫХ [G]-файлов документации в public_docs/.

Запуск из корня репозитория:
    python3 scripts/gen_public_docs.py

Источники — код и данные репозитория (НЕ правятся, только читаются):
  - app/tools/config_schema.py  (SLUG_SCHEMA, _SLUG_ALIASES, COLUMN_PROPS, RULE_PROPS, ...)
  - app/tools/component_crud.py (множество creatable-типов)
  - app/server.py               (@mcp.tool / @mcp.prompt; живая интроспекция FastMCP)
  - docs/architecture/readiness/audit/*.json|*.md (готовность, ограничения)
  - docs/scorecard/*.json        (scorecard)
  - docs/architecture/readiness/audit/frontend_support.json (версия фронта)

Все выводы ОБЕЗЛИЧИВАЮТСЯ: убираются тикеты, имена стадий/итераций, даты-снапшоты,
тестовые домены/креды, внутренние пути-артефакты, вердикты-ярлыки как термины.
Скрипт идемпотентен: повторный запуск перезаписывает файлы.
"""
from __future__ import annotations

import json
import re
import sys
from collections import defaultdict, Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

PUBLIC = ROOT / "docs"

# --- импорт кода-источника ----------------------------------------------------
from app.tools.config_schema import (  # noqa: E402
    SLUG_SCHEMA, COLUMN_PROPS, RULE_PROPS, _SLUG_ALIASES, _ANCHORED_VISUAL_PROPS,
)

GEN_NOTE = "регенерируется scripts/gen_public_docs.py"


# =============================================================================
# ОБЕЗЛИЧИВАНИЕ
# =============================================================================
# Паттерны утечек, которые должны быть вычищены из ЛЮБОГО публичного вывода.
_TICKET_RE = re.compile(r"\b[A-Z]{2,}-?\d+\w*")          # AIAG-38, RALPH-1, CC3 ...
# Внутренние ID-коды аудита: одна-две буквы + цифры.
_AUDITID_RE = re.compile(r"(?<![\w.])(?:=)?(?:[A-ZА-Я]{1,2})-?\d+[A-Za-zА-Яа-я-]*(?![\w.])")
_ITER_RE = re.compile(r"\biter-?\d+\b", re.I)
_STAGE_RE = re.compile(r"(?:Этап|Фаза|Фазa|Wave|Волна|Пилот|пилот)\s*\d*", re.I)
_DATE_RE = re.compile(r"\b20\d{2}[-./]\d{1,2}[-./]\d{1,2}\b")
_ASOF_RE = re.compile(r"по состоянию на[^.\n]*", re.I)
_DOMAIN_RE = re.compile(r"(?:devcopy\.)?modusbi\.ru|mcpe2e", re.I)
_PROGRESS_RE = re.compile(r"_PROGRESS|_progress|FINDINGS_FOR_DEVS|coverage_reconciliation", re.I)
_FILEREF_RE = re.compile(r"`?[\w./-]+\.(?:py|js|md|json)`?(?::\d+(?:-\d+)?)?", re.I)
_WEBPACK_RE = re.compile(r"webpack\s*\d+|app\.[0-9a-f]+\.\.?js|\bбандл\b|\bbundle\b", re.I)
_GH_RE = re.compile(r"github\.com/[\w./-]+", re.I)

# Вердикты-ярлыки как ТЕРМИНЫ → нейтральные формулировки.
_LABEL_MAP = [
    (re.compile(r"render-dead", re.I), "не подтверждено"),
    (re.compile(r"config-only", re.I), "частично"),
    (re.compile(r"silent-ignore", re.I), "без видимого эффекта"),
    (re.compile(r"\bambiguous\b", re.I), "требует уточнения"),
    (re.compile(r"\bambig\b", re.I), "требует уточнения"),
    (re.compile(r"\brejected\b", re.I), "не принято"),
    (re.compile(r"\bno-effect\b", re.I), "без видимого эффекта"),
    (re.compile(r"\bno-slug\b", re.I), "без отдельного параметра"),
    (re.compile(r"\borphan\b", re.I), "устаревший"),
    (re.compile(r"\bwontfix\b", re.I), "не планируется"),
    (re.compile(r"баг(?:а|ом|и)?\s+фронт\w*", re.I), "ограничение системы"),
    (re.compile(r"баг(?:а|ом|и)?\s+бэк\w*", re.I), "ограничение системы"),
    (re.compile(r"баг\s+фронт\w*", re.I), "ограничение системы"),
    (re.compile(r"фронт-?баг", re.I), "ограничение системы"),
    (re.compile(r"\bбаг\b", re.I), "ограничение"),
    # английский технический жаргон → нейтрально
    (re.compile(r"render-?crash", re.I), "сбой отображения"),
    (re.compile(r"config-?applied", re.I), "применяется на уровне конфигурации"),
    (re.compile(r"\bmismatch\b", re.I), "несоответствие"),
    (re.compile(r"\bguard\w*\b", re.I), "проверка"),
    (re.compile(r"\bredundant\b", re.I), "избыточно"),
    (re.compile(r"\bno-?op\b", re.I), "без эффекта"),
    (re.compile(r"\bguardrail\b", re.I), "защитная проверка"),
    (re.compile(r"\bhardcode\w*\b", re.I), "фиксировано в системе"),
    (re.compile(r"\bDEPRECATED\b", re.I), "устарел"),
    (re.compile(r"\blegacy\b", re.I), "устаревший"),
]

# Имена сторонних библиотек/движков рендера и внутренних механизмов → обобщённо.
_VENDOR_MAP = [
    (re.compile(r"\breactabular\b", re.I), "табличный движок"),
    (re.compile(r"\bGoJS\b", re.I), "движок графов"),
    (re.compile(r"amCharts\d*", re.I), "движок диаграмм"),
    (re.compile(r"\bamcharts\b", re.I), "движок диаграмм"),
    (re.compile(r"\bLeaflet\b", re.I), "движок карт"),
    (re.compile(r"\bD3-?\w*", re.I), "движок отрисовки"),
    (re.compile(r"\bMSOLAP\b|\bXMLA\b|\bMDX\b", re.I), "OLAP-источник"),
]

# Внутренний механизм «MCP пишет / фронт читает X» → обобщённая формулировка.
_MECH_MAP = [
    (re.compile(r"MCP\s+пиш\w+", re.I), "сервер записывает"),
    (re.compile(r"фронт\w*\s+(?:чита\w+|жд/?[её]т|игнор\w+|форс\w+|деструкт\w+|знает|рису\w+)", re.I),
     "отображение"),
    (re.compile(r"\bfront\b|\bback\b", re.I), "система"),
]

# Слова-владельцы/вендоры → нейтрализация.
_OWNER_MAP = [
    (re.compile(r"\bowner\s*=\s*\w+", re.I), ""),
    (re.compile(r"вендор\w*", re.I), "система"),
]


def scrub(text: str) -> str:
    """Жёсткое обезличивание строки для публичного вывода."""
    if not text:
        return text
    s = text
    for rx, repl in _MECH_MAP:
        s = rx.sub(repl, s)
    for rx, repl in _LABEL_MAP:
        s = rx.sub(repl, s)
    for rx, repl in _VENDOR_MAP:
        s = rx.sub(repl, s)
    for rx, repl in _OWNER_MAP:
        s = rx.sub(repl, s)
    s = _ASOF_RE.sub("", s)
    s = _GH_RE.sub("внутренний репозиторий", s)
    s = _PROGRESS_RE.sub("внутренний реестр", s)
    s = _WEBPACK_RE.sub("рендер", s)
    s = _DOMAIN_RE.sub("портал", s)
    s = _DATE_RE.sub("", s)
    s = _ITER_RE.sub("", s)
    s = _STAGE_RE.sub("", s)
    # ссылки на внутренние файлы-источники с :line — убрать
    s = _FILEREF_RE.sub("внутренний модуль", s)
    s = _TICKET_RE.sub("", s)
    s = _AUDITID_RE.sub("", s)
    # схлопнуть мусор после вырезаний
    s = re.sub(r"\(\s*[,.;·—-]*\s*\)", "", s)
    s = re.sub(r"[ \t]{2,}", " ", s)
    s = re.sub(r"\s+([,.;:])", r"\1", s)
    s = re.sub(r"^[\s,;·—-]+", "", s)
    return s.strip()


# внутренние реализационные термины (НЕ публичные имена слагов) — нейтрализуем/вырезаем
_IMPL_TERM_RE = re.compile(
    r"\bjson_path\b|\bchartType\b|\bvalueType\b|\bvisuals\[[^\]]*\]"
    r"|\btop-?level\b|\bnested\b|\bbuilder\b|\bvalidate\b|\bschema\b|\bvalidator\b"
    r"|\bconfig-\u043f\u0430\u043d\u0435\u043b\w*|\bapplies_to\b|error-?envelope|\benvelope\b"
    r"|\bDOM\b|\binterpolateHcl\b|linkCount=\d+|nodeData|linkage|raw-\u043a\u043b\u044e\u0447"
    r"|MCP-\w+|\u0447\u0435\u0440\u0435\u0437 MCP|\bMCP\b|slugs?_applied:\d+"
    r"|render-active|by[- ]design|no-dataset|task_id|resource\.url"
    r"|UI-toggle|UI-save|console-pollution|\bgroupingMode\b|\u0433\u0435\u0439\u0442\w*",
    re.I,
)


def scrub_symptom(text: str) -> str:
    """Obezlichivanie + obobshchenie tekhnicheskogo simptoma dlya publichnogo spiska.

    Publichnye imena slagov v `kavychkakh` SOKHRANYAEM (oni v slug-reference),
    no snimaem vnutrennie json-puti posle strelki, realizatsionnye terminy, audit-ID, vendor.
    """
    s = scrub(text)
    arrow = "\u2192"
    # ubrat tselevuyu chast posle strelki (vnutrennii json-put), code-span ili bez
    s = re.sub(arrow + r"\s*`[^`]*`", "", s)
    s = re.sub(arrow + r"\s*[\w.\[\]{}\"'/]+", "", s)
    s = re.sub(r"\s*" + arrow + r"\s*", " ", s)
    # vnutrennie realizatsionnye terminy
    s = _IMPL_TERM_RE.sub("", s)
    # standalone front/back mentions -> neutral
    s = re.sub(r"\u0444\u0440\u043e\u043d\u0442-\u043a\u043b\u044e\u0447\w*", "\u043a\u043b\u044e\u0447\u0438 \u043e\u0442\u043e\u0431\u0440\u0430\u0436\u0435\u043d\u0438\u044f", s)
    s = re.sub(r"\u0444\u0440\u043e\u043d\u0442\u043e\u043c", "\u0441\u0438\u0441\u0442\u0435\u043c\u043e\u0439", s)
    s = re.sub(r"\u043d\u0430 \u0444\u0440\u043e\u043d\u0442\u0435", "\u043f\u0440\u0438 \u043e\u0442\u043e\u0431\u0440\u0430\u0436\u0435\u043d\u0438\u0438", s)
    s = re.sub(r"\u0444\u0440\u043e\u043d\u0442 \u0445\u0430\u0440\u0434\u043a\u043e\u0434\w*", "\u0437\u043d\u0430\u0447\u0435\u043d\u0438\u0435 \u0444\u0438\u043a\u0441\u0438\u0440\u043e\u0432\u0430\u043d\u043e", s)
    s = re.sub(r"\u0444\u0440\u043e\u043d\u0442", "\u043e\u0442\u043e\u0431\u0440\u0430\u0436\u0435\u043d\u0438\u0435", s)
    # leftover literals: inputDateFormat:"...", chrome-шапка, stroke, dangling :"color"
    s = re.sub(r"`?inputDateFormat:\s*\"[^\"]*\"`?", "", s)
    s = re.sub(r"chrome-\u0448\u0430\u043f\w*", "\u0441\u043b\u0443\u0436\u0435\u0431\u043d\u043e\u0439 \u0448\u0430\u043f\u043a\u0438", s)
    s = re.sub(r"\bstroke\b", "\u043b\u0438\u043d\u0438\u0438", s)
    s = re.sub(r"`?:\s*\"color\"`?", "", s)
    s = re.sub(r"\bview-mode\b", "\u0440\u0435\u0436\u0438\u043c\u0435 \u043f\u0440\u043e\u0441\u043c\u043e\u0442\u0440\u0430", s)
    s = re.sub(r"write-\u0441\u043b\u043e\u043c\w*", "\u043d\u0435 \u0441\u043e\u0445\u0440\u0430\u043d\u044f\u0435\u0442\u0441\u044f", s)
    s = re.sub(r"\btype:\s*\"?\w+\"?", "", s)
    # pustye code-spany i osirotevshie skobki
    s = re.sub(r"`\s*`", "", s)
    s = re.sub(r"\(\s*[;,.\u00b7\u2014\u2013-]*\s*\)", "", s)
    s = re.sub(r"\s*[\u2014\u2013-]\s*$", "", s)
    s = re.sub(r"[ \t]{2,}", " ", s)
    s = re.sub(r"\s+([,.;:])", r"\1", s)
    s = re.sub(r"^[\s,;:\u00b7\u2014\u2013-]+", "", s)
    s = re.sub(r"[\s,;:\u00b7\u2014\u2013]+$", "", s)
    return s.strip()


def header(*, source: str) -> str:
    return (
        f"<!-- GENERATED from {source}; "
        f"edit there, then run scripts/gen_public_docs.py -->\n"
        f"<!-- {GEN_NOTE} -->\n"
    )


def write(rel: str, text: str) -> None:
    path = PUBLIC / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    if not text.endswith("\n"):
        text += "\n"
    path.write_text(text, encoding="utf-8")
    n_lines = text.count("\n")
    n_bytes = len(text.encode("utf-8"))
    print(f"  written {path.relative_to(ROOT)}  ({n_lines} строк, {n_bytes} байт)")


# =============================================================================
# СБОР ФАКТОВ ИЗ КОДА
# =============================================================================
def count_creatable() -> tuple[int, list[str]]:
    """Число и список creatable-типов из component_crud.py (множество _creatable)."""
    src = (ROOT / "app/tools/component_crud.py").read_text(encoding="utf-8")
    m = re.search(r"_creatable\s*=\s*\{(.*?)\n\s*\}", src, re.S)
    if not m:
        return 0, []
    items = re.findall(r'"([^"]+)"', m.group(1))
    # отбросить возможные не-типовые строки (комментарии не попадают в findall кавычек)
    items = [x for x in items if x.startswith("Hs")]
    return len(items), sorted(set(items))


def count_decorator(deco: str) -> int:
    src = (ROOT / "app/server.py").read_text(encoding="utf-8")
    return len(re.findall(rf"^@mcp\.{deco}\b", src, re.M))


def frontend_version() -> str | None:
    fs = ROOT / "docs/architecture/readiness/audit/frontend_support.json"
    if fs.exists():
        try:
            d = json.loads(fs.read_text(encoding="utf-8"))
            v = d.get("latest_verified")
            if v:
                return str(v)
            versions = d.get("versions")
            if isinstance(versions, dict) and versions:
                return sorted(versions.keys())[-1]
        except Exception:
            pass
    vfile = ROOT / "VERSIONING.md"
    if vfile.exists():
        m = re.search(r"\b(\d+\.\d+\.\d+)\b", vfile.read_text(encoding="utf-8"))
        if m:
            return m.group(1)
    return None


def latest_scorecard() -> Path | None:
    d = ROOT / "docs/scorecard"
    if not d.exists():
        return None
    jsons = sorted(d.glob("*.json"))
    return jsons[-1] if jsons else None


# =============================================================================
# ГЛОБАЛЬНЫЕ ФАКТЫ (используются в нескольких файлах)
# =============================================================================
N_SLUGS = len(SLUG_SCHEMA)
N_CREATABLE, CREATABLE = count_creatable()
N_TOOLS = count_decorator("tool")
N_PROMPTS = count_decorator("prompt")
FE_VERSION = frontend_version()


# Перевод частых англоязычных формулировок устаревания на русский (для публичного вывода).
_DEPR_RU = [
    (re.compile(r"no such frontend key[;,]?\s*see\s+", re.I), "нет такого параметра отображения; использовать "),
    (re.compile(r"no such frontend key", re.I), "нет такого параметра отображения"),
    (re.compile(r"use anchored\s+", re.I), "использовать по-серийный "),
    (re.compile(r"with alpha", re.I), "с прозрачностью"),
    (re.compile(r"\borphan\b[:\s]*", re.I), "устарел: "),
]


def translate_depr(text: str) -> str:
    s = text
    for rx, repl in _DEPR_RU:
        s = rx.sub(repl, s)
    return s


def fmt_type(e: dict) -> str:
    t = e["type"]
    if t == "enum":
        return f"enum: {'/'.join(map(str, e.get('values', [])))}"
    if t in ("int", "float") and ("min" in e or "max" in e):
        return f"{t} [{e.get('min', '')}..{e.get('max', '')}]"
    return t


# =============================================================================
# 1) _stats.json
# =============================================================================
def gen_stats() -> dict:
    stats = {
        "slugs": N_SLUGS,
        "component_types_creatable": N_CREATABLE,
        "tools": N_TOOLS,
        "prompts": N_PROMPTS,
        "frontend_version": FE_VERSION,
        "generated_note": GEN_NOTE,
    }
    path = PUBLIC / "_stats.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(stats, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"  written {path.relative_to(ROOT)}  ({len(json.dumps(stats))} байт)")
    return stats


# =============================================================================
# 2) components/slugs/by-type.md
# =============================================================================
def gen_slug_reference() -> None:
    groups = defaultdict(list)
    for slug, e in sorted(SLUG_SCHEMA.items()):
        section = slug.split(".")[0] if "." in slug else "(верхний уровень)"
        groups[section].append((slug, e))

    out = [header(source="app/tools/config_schema.py (SLUG_SCHEMA)")]
    out += [
        "# Справочник слагов config_overrides",
        "",
        f"> Слагов: **{N_SLUGS}** (+ анкерные `visuals.{{anchor}}.{{prop}}`, "
        f"колоночные `columns.{{field}}.{{prop}}`, правила `rules.{{n}}.{{prop}}`).",
        "",
        "Слаги — плоские ключи словаря `config_overrides` для визуальной настройки компонентов.",
        "",
        "Колонки таблицы:",
        "- **Слаг** — ключ в `config_overrides`.",
        "- **Тип** — тип значения (enum/int/float/bool/str/color).",
        "- **Default** — значение по умолчанию.",
        "- **json_path** — фактический путь записи в config (пусто = секционный обработчик / верхний уровень).",
        "- **applies_to** — типы компонентов, к которым применим (пусто = все).",
        "- **Прим.** — примечания; «устарел» = слаг сохранён для совместимости, использовать замену из примечания.",
        "",
    ]
    for section in sorted(groups):
        out += [f"## {section}", "",
                "| Слаг | Тип | Default | json_path | applies_to | Прим. |",
                "|---|---|---|---|---|---|"]
        for slug, e in groups[section]:
            dep = e.get("deprecated")
            note = ""
            if dep:
                # нейтрально: «устарел», замена из значения deprecated, но обезличенная
                repl = scrub(translate_depr(str(dep)))
                note = f"устарел — {repl}" if repl else "устарел"
            if e.get("invert"):
                note = (note + "; " if note else "") + "значение инвертируется"
            jp = e.get("json_path", "") or ""
            at = ", ".join(e.get("applies_to", [])) or "все"
            note = scrub(note)
            out.append(f"| `{slug}` | {fmt_type(e)} | `{e.get('default')}` | `{jp}` | {at} | {note} |")
        out.append("")

    out += [
        "## Анкерные visuals (по-сериям / по-элементам)", "",
        "`visuals.{anchor}.{prop}` — пишет в элемент `config.visuals[]` с `anchor == {anchor}` "
        "(имя серии у line/area/radar/stock; `value`/`caption`/`subcaption`/`trend` у KPI).",
        "",
        "Поддерживаемые prop: " + ", ".join(f"`{p}`" for p in sorted(_ANCHORED_VISUAL_PROPS)) + ".",
        "",
        "## Колоночные слаги (table/pivot/comparison)", "",
        "`columns.{fieldName|fieldId}.{prop}` — props: "
        + ", ".join(f"`{p}`" for p in sorted(COLUMN_PROPS)) + ".",
        "",
        "## Правила условного форматирования (table/pivot)", "",
        "`rules.{n}.{prop}` — props: " + ", ".join(f"`{p}`" for p in sorted(RULE_PROPS)) + ".",
        "",
    ]
    write("architecture/components/slugs/by-type.md", "\n".join(out))


# =============================================================================
# 3) versioning/slug-migration.md
# =============================================================================
def gen_slug_migration() -> None:
    out = [header(source="app/tools/config_schema.py (_SLUG_ALIASES + deprecated-флаги SLUG_SCHEMA)")]
    out += [
        "# Слаги: псевдонимы и устаревшие имена",
        "",
        "Сервер принимает часть слагов под альтернативными (старыми) именами и помечает часть имён",
        "как устаревшие. Это не история версий, а текущее поведение приёма имён: псевдоним",
        "автоматически приводится к актуальному слагу, устаревшее имя принимается, но рекомендуется",
        "использовать актуальное.",
        "",
        "## Псевдонимы (альтернативное имя → актуальное)",
        "",
        "| Старый слаг | Актуальный слаг |",
        "|---|---|",
    ]
    if _SLUG_ALIASES:
        for old, new in sorted(_SLUG_ALIASES.items()):
            out.append(f"| `{old}` | `{new}` |")
    else:
        out.append("| _нет активных псевдонимов_ | — |")
    out += [
        "",
        "## Устаревшие слаги (использовать замену)",
        "",
        "| Слаг | Статус | Замена / комментарий |",
        "|---|---|---|",
    ]
    dep = [(s, e.get("deprecated")) for s, e in sorted(SLUG_SCHEMA.items()) if e.get("deprecated")]
    if dep:
        for slug, reason in dep:
            out.append(f"| `{slug}` | устарел | {scrub(translate_depr(str(reason)))} |")
    else:
        out.append("| _нет устаревших слагов_ | — | — |")
    out += [
        "",
        "> Замена применяется автоматически на стороне сервера; устаревшие слаги принимаются, "
        "но рекомендуется переходить на актуальные имена.",
        "",
    ]
    write("architecture/components/slugs/aliases.md", "\n".join(out))


# =============================================================================
# 4) scorecard/README.md
# =============================================================================
def gen_scoreboard() -> None:
    sc_path = latest_scorecard()
    out = [header(source="docs/scorecard/*.json (последний отчёт)")]
    out += ["# Scorecard — сводка качества MCP-сервера", ""]

    if not sc_path:
        out += ["> Отчёт scorecard не найден.", ""]
        write("scorecard/README.md", "\n".join(out))
        return

    data = json.loads(sc_path.read_text(encoding="utf-8"))
    sc = data.get("scorecard", {})
    inventory = data.get("inventory", {})
    findings = data.get("findings", [])

    total = sc.get("total_score", {})
    score = total.get("value", "?")
    max_score = total.get("max", 100)
    tool_count = N_TOOLS  # из кода — единый источник, без рассинхрона

    def light(pct: float) -> str:
        if pct >= 90:
            return "🟢"
        if pct >= 70:
            return "🟡"
        return "🔴"

    overall_pct = (score / max_score * 100) if isinstance(score, (int, float)) and max_score else 0
    out += [
        f"**Итоговый балл:** {score}/{max_score} {light(overall_pct)}",
        f"**Инструментов:** {tool_count}",
        "",
        "Детерминированная оценка качества: соответствие контракту, безопасность, эргономика и гигиена метаданных.",
        "",
        "## Оси оценки",
        "",
        "| Ось | Балл | Светофор |",
        "|---|---|:--:|",
    ]
    axis_titles = {
        "conformance": "Соответствие контракту",
        "security": "Безопасность",
        "ergonomics": "Эргономика",
        "metadata": "Метаданные",
    }
    cats = sc.get("category_scores", {})
    for key in ("conformance", "security", "ergonomics", "metadata"):
        info = cats.get(key, {})
        s = info.get("score", "?")
        m = info.get("max_score", 100)
        pct = (s / m * 100) if isinstance(s, (int, float)) and m else 0
        out.append(f"| {axis_titles.get(key, key)} | {s}/{m} | {light(pct)} |")

    sev = Counter(f.get("severity", "?") for f in findings)
    out += [
        "",
        "## Замечания",
        "",
        f"Ошибок: {sev.get('error', 0)} · предупреждений: {sev.get('warning', 0)} · "
        f"информационных: {sev.get('info', 0)}.",
        "",
    ]
    if findings:
        out += ["| Класс | Замечание |", "|---|---|"]
        seen = set()
        for f in findings:
            title = scrub(str(f.get("title", "")))
            bucket = axis_titles.get(f.get("bucket"), f.get("bucket", "—"))
            kk = (bucket, title)
            if kk in seen or not title:
                continue
            seen.add(kk)
            out.append(f"| {bucket} | {title} |")
        out.append("")
    else:
        out += ["Замечаний нет — все оси на максимуме.", ""]
    write("scorecard/README.md", "\n".join(out))


# =============================================================================
# 5) readiness/components-readiness.md
# =============================================================================
# Канонизация имён компонентов из verdicts['on'] в человекочитаемые.
_COMP_CANON = {
    "bar": "Столбчатая диаграмма (Bar)",
    "line": "Линейная диаграмма (Line)",
    "area": "Диаграмма с областями (Area)",
    "pie": "Круговая диаграмма (Pie)",
    "radar": "Лепестковая диаграмма (Radar)",
    "stock": "Биржевая диаграмма (Stock)",
    "speedometer": "Спидометр (Speedometer)",
    "bubble": "Пузырьковая диаграмма (Bubble)",
    "sunburst": "Sunburst",
    "treemap": "Древовидная карта (TreeMap)",
    "parallel": "Параллельные координаты (Parallel)",
    "pivot": "Сводная таблица (Pivot)",
    "comparison": "Диаграмма сравнения (Comparison)",
    "treegraph": "Граф-дерево (TreeGraph)",
    "map": "Карта (Map)",
    "tilemap": "Картограмма (Tilemap)",
    "filterControl": "Панель фильтра (FilterControl)",
    "hierFilter": "Иерархический фильтр (HierarchicalFilter)",
    "hierfilter": "Иерархический фильтр (HierarchicalFilter)",
    "switch": "Переключатель (Switch)",
    "imagePanel": "Панель изображения (ImagePanel)",
    "iframe": "Встраиваемый фрейм (Iframe)",
    "textBlock": "Текстовый блок (TextBlock)",
    "tabsPanel": "Панель вкладок (TabsPanel)",
    "totals": "Панель показателей (TotalsPanelV2)",
    "audioplayer": "Аудиоплеер (Audioplayer)",
    "table": "Таблица (Table)",
}
# не-компонентные ключи в verdicts (общие группы) — исключить из матрицы по типам.
_NON_COMPONENT = {"generic", "balloon", "data", "deprecated", "bar/line/area",
                  "generic@bar", "generic@totals"}


def _canon_component(on: str) -> str | None:
    if on in _NON_COMPONENT:
        return None
    base = on.split("@")[0]
    return _COMP_CANON.get(on) or _COMP_CANON.get(base)


def gen_components_readiness() -> None:
    vpath = ROOT / "docs/architecture/readiness/audit/slug_ui_verdicts.json"
    out = [header(source="docs/architecture/readiness/audit/slug_ui_verdicts.json + component_status.md")]
    out += [
        "# Готовность компонентов",
        "",
        "Матрица готовности по типам компонентов: создаётся ли через MCP, как отображается, "
        "и насколько покрыт визуальными параметрами.",
        "",
        "Светофор отображения (по совокупности проверенных параметров):",
        "- ✅ **рисуется** — большинство визуальных параметров отображается корректно;",
        "- 🟡 **частично** — отображается, часть параметров действует только на уровне конфигурации;",
        "- 🔴 **не подтверждено** — отображение части параметров не подтверждено.",
        "",
    ]
    if FE_VERSION:
        out += [f"> Версия фронтенда: **{FE_VERSION}**.", ""]

    # агрегируем вердикты по компоненту
    agg: dict[str, Counter] = defaultdict(Counter)
    if vpath.exists():
        verdicts = json.loads(vpath.read_text(encoding="utf-8")).get("verdicts", {})
        for slug, rec in verdicts.items():
            comp = _canon_component(str(rec.get("on", "")))
            if comp is None:
                continue
            agg[comp][rec.get("v", "na")] += 1

    # технические типы → канон (для отметки creatable)
    type_to_canon = {
        "HsBarAMchartsChart": "Столбчатая диаграмма (Bar)",
        "HsLineAMchartsChart": "Линейная диаграмма (Line)",
        "HsAreaAMchartsChart": "Диаграмма с областями (Area)",
        "HsPieAMchartsChart": "Круговая диаграмма (Pie)",
        "HsRadarAMchartsChart": "Лепестковая диаграмма (Radar)",
        "HsStockAMchartsChart": "Биржевая диаграмма (Stock)",
        "HsSpeedometerV2AMcharts": "Спидометр (Speedometer)",
        "HsBubbleAMchartsChart": "Пузырьковая диаграмма (Bubble)",
        "HsSunburstChart": "Sunburst",
        "HsTreeMap": "Древовидная карта (TreeMap)",
        "HsParallelCoordsChart": "Параллельные координаты (Parallel)",
        "HsPivotChart": "Сводная таблица (Pivot)",
        "HsComparisonChart": "Диаграмма сравнения (Comparison)",
        "HsTreeGraph": "Граф-дерево (TreeGraph)",
        "HsMapLeafletChart": "Карта (Map)",
        "HsTilemapChart": "Картограмма (Tilemap)",
        "HsFilterControlPanel": "Панель фильтра (FilterControl)",
        "HsHierarchicalFilterPanel": "Иерархический фильтр (HierarchicalFilter)",
        "HsTotalsPanelV2": "Панель показателей (TotalsPanelV2)",
        "HsTableReactabularChart": "Таблица (Table)",
        "HsTextBlock": "Текстовый блок (TextBlock)",
        "HsTabsPanel": "Панель вкладок (TabsPanel)",
        "HsSwitchControlPanel": "Переключатель (Switch)",
        "HsAudioplayer": "Аудиоплеер (Audioplayer)",
        "HsIframe": "Встраиваемый фрейм (Iframe)",
        "HsImagePanel": "Панель изображения (ImagePanel)",
        "HsSubheaderComponent": "Подзаголовок (Subheader)",
        "HsPageContainer": "Контейнер страниц (PageContainer)",
    }
    creatable_canon = {type_to_canon.get(t) for t in CREATABLE}

    def render_light(c: Counter) -> tuple[str, str]:
        total = sum(c.values())
        if total == 0:
            return "🟡", "проверка покрытия не завершена"
        ok = c.get("ok", 0)
        partial = c.get("cfg", 0) + c.get("amb", 0)
        unconf = c.get("dead", 0) + c.get("rej", 0) + c.get("na", 0)
        ok_pct = ok / total
        if ok_pct >= 0.6:
            return "✅", f"{ok} из {total} параметров отображаются"
        if ok + partial >= unconf:
            return "🟡", f"{ok} отображаются, {partial} на уровне конфигурации"
        return "🔴", f"отображение части параметров ({unconf} из {total}) не подтверждено"

    # упорядочим по числу проверенных параметров (desc), затем по имени
    rows = []
    all_comps = set(agg) | {c for c in creatable_canon if c}
    for comp in sorted(all_comps, key=lambda c: (-sum(agg.get(c, Counter()).values()), c)):
        c = agg.get(comp, Counter())
        creatable = "✅" if comp in creatable_canon else "—"
        light, note = render_light(c)
        n = sum(c.values())
        rows.append((comp, creatable, f"{n}", light, note))

    out += [
        "| Компонент | Создаётся через MCP | Параметров проверено | Отображение | Примечание |",
        "|---|:--:|:--:|:--:|---|",
    ]
    for comp, creatable, n, light, note in rows:
        out.append(f"| {comp} | {creatable} | {n} | {light} | {note} |")
    out += [
        "",
        f"> Создаваемых через MCP типов компонентов: **{N_CREATABLE}**. "
        "Прочерк в колонке «Создаётся через MCP» — тип присутствует на портале, "
        "но создаётся другим способом.",
        "",
    ]
    write("architecture/readiness/components-readiness.md", "\n".join(out))


# =============================================================================
# 6) readiness/findings.md
# =============================================================================
def _parse_findings_table(md: str) -> list[tuple[str, str, str]]:
    """Возвращает (симптом, влияние, класс) из реестра находок.

    Источник — markdown-таблица в FINDINGS.md (колонки: ID|Компонент|Симптом|...|Статус).
    Берём только Симптом → обезличиваем; влияние/класс выводим из статусного значка нейтрально.
    """
    rows = []
    status_class = {
        "🔴": ("ограничивает отдельную возможность", "ограничение"),
        "🟡": ("частичное", "нюанс"),
        "🟠": ("требует доработки", "доработка"),
        "⚪": ("настраивается иначе", "особенность"),
        "⚠️": ("незначительное", "особенность"),
        "ℹ️": ("информационное", "заметка"),
        "📄": ("уточнение документации", "документация"),
        "🟢": ("устранено", "закрыто"),
        "🔵": ("устранено", "закрыто"),
    }
    for line in md.splitlines():
        line = line.strip()
        if not line.startswith("|") or line.startswith("|---") or "| ID |" in line:
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < 4:
            continue
        # эвристика: колонки [ID, Компонент, Симптом, ..., Статус]
        symptom = cells[2] if len(cells) >= 3 else ""
        status = cells[-1]
        impact, klass = ("ограничение отдельной возможности", "ограничение")
        for emo, (imp, kl) in status_class.items():
            if emo in status:
                impact, klass = imp, kl
                break
        # пропускаем уже закрытые/документационные — публичный список = АКТУАЛЬНЫЕ ограничения
        if any(e in status for e in ("🟢", "🔵", "📄", "ℹ️")):
            continue
        sym = scrub_symptom(symptom)
        # отбрасываем пустые/мусорные/слишком короткие (потеряли смысл после чистки)
        words = [w for w in re.split(r"\s+", sym) if len(w) > 1]
        if not sym or len(sym) < 15 or len(words) < 3:
            continue
        # отбрасываем строки, где после чистки остались внутренние символы-пути
        if re.search(r"[→\[\]{}]|json|chartType", sym):
            continue
        rows.append((sym, impact, klass))
    return rows


def gen_findings() -> None:
    src = ROOT / "docs/architecture/readiness/audit/FINDINGS.md"
    out = [header(source="docs/architecture/readiness/audit/FINDINGS.md (обезличенный реестр ограничений)")]
    out += [
        "# Известные ограничения",
        "",
        "Публичный список известных ограничений и особенностей компонентов. "
        "Где возможно — приведена нейтральная формулировка и характер влияния. "
        "Закрытые и чисто документационные пункты в список не включены.",
        "",
        "| Симптом | Влияние | Класс |",
        "|---|---|---|",
    ]
    seen = set()
    if src.exists():
        rows = _parse_findings_table(src.read_text(encoding="utf-8"))
        for sym, impact, klass in rows:
            key = sym[:60].lower()
            if key in seen:
                continue
            seen.add(key)
            out.append(f"| {sym} | {impact} | {klass} |")
    if len(out) <= 7:  # только заголовок таблицы
        out.append("| _актуальных ограничений не зафиксировано_ | — | — |")
    out += [
        "",
        "> Список носит справочный характер и обновляется по мере развития системы.",
        "",
    ]
    write("architecture/readiness/findings.md", "\n".join(out))


# =============================================================================
# 7) reference/cheatsheet.md
# =============================================================================
def gen_cheatsheet(tools_meta: list[dict]) -> None:
    out = [header(source="derived: SLUG_SCHEMA + component_crud (_creatable) + server.py")]
    out += [
        "# Шпаргалка",
        "",
        f"Слагов: **{N_SLUGS}** · создаваемых типов: **{N_CREATABLE}** · "
        f"инструментов: **{N_TOOLS}** · промптов: **{N_PROMPTS}**"
        + (f" · версия фронта: **{FE_VERSION}**" if FE_VERSION else "")
        + ".",
        "",
        "## Частые задачи → слаги",
        "",
    ]
    # подбор частотных слагов по префиксам-секциям
    task_slugs = [
        ("Заголовок / подписи", ["showtitle", "subtitle", "truncateTitle"]),
        ("Легенда", ["legend.visible", "legend.position", "legend.fontSize"]),
        ("Оси", ["axes.valueTitle", "axes.categoryTitle", "axes.valueGrid", "axes.categoryLabels"]),
        ("Фон и рамка", ["bgColor", "outline.enabled", "outline.color", "outline.width"]),
        ("Отступы", ["margin.l", "margin.r", "margin.t", "margin.b"]),
        ("Цвета / палитра", ["data.baseColor", "data.colorStep"]),
        ("Подписи значений", ["labels.visible", "labels.precision"]),
    ]
    out += ["| Задача | Слаги |", "|---|---|"]
    for task, slugs in task_slugs:
        present = [s for s in slugs if s in SLUG_SCHEMA]
        if not present:
            # подобрать по префиксу
            pref = slugs[0].split(".")[0]
            present = [s for s in SLUG_SCHEMA if s.startswith(pref + ".")][:4]
        if present:
            out.append(f"| {task} | " + " ".join(f"`{s}`" for s in present) + " |")
    out += ["", "## Частые действия инструментов", ""]
    # вытащим action-перечни из реальных схем
    action_lines = []
    for t in tools_meta:
        acts = t.get("actions")
        if acts:
            shown = acts[:8]
            more = " …" if len(acts) > 8 else ""
            action_lines.append(f"- **`{t['name']}`** — " + ", ".join(f"`{a}`" for a in shown) + more)
    out += action_lines[:12]

    out += ["", "## Типы компонентов (создаются через MCP)", ""]
    # короткие человекочитаемые имена
    nice = sorted(
        re.sub(r"^Hs|AMcharts.*$|Chart$|Panel$|Component$|V2.*$", "", t) or t
        for t in CREATABLE
    )
    out.append(", ".join(f"`{n}`" for n in nice if n) + ".")
    out += [
        "",
        f"Полный список технических типов — `component_crud(action=\"types_list\")` ({N_CREATABLE} создаваемых).",
        "",
        "## Базовые шаги создания отчёта",
        "",
        "1. `report_operations(action=\"create\", ...)` — создать отчёт.",
        "2. `dataset_operations(action=\"create\", ...)` — подготовить семантический слой.",
        "3. `component_crud(action=\"add\", ...)` — добавить компонент.",
        "4. `component_filters(action=\"filter_field_add\", ...)` — связать фильтры.",
        "5. `style_operations(action=\"update\", ...)` — применить CSS отчёта.",
        "",
        "Быстрый путь — готовые шаблоны: `report_template(action=\"list\")` → "
        "`report_template(action=\"scaffold\", template=...)`.",
        "",
    ]
    write("start/reference/cheatsheet.md", "\n".join(out))


# =============================================================================
# 8) tools/tool-reference.md  (живая интроспекция FastMCP)
# =============================================================================
def collect_tools_meta() -> tuple[list[dict], str]:
    """Возвращает (список метаданных инструментов, способ сбора)."""
    meta: list[dict] = []
    method = "fallback"
    try:
        import asyncio
        import app.server as srv  # noqa: F401

        async def _list():
            return await srv.mcp.list_tools()

        tools = asyncio.run(_list())
        for t in tools:
            name = getattr(t, "name", None)
            desc = (getattr(t, "description", "") or "").strip()
            first_line = scrub(desc.splitlines()[0]) if desc else ""
            schema = getattr(t, "inputSchema", {}) or {}
            props = schema.get("properties", {}) or {}
            actions = []
            if "action" in props and isinstance(props["action"], dict):
                actions = props["action"].get("enum", []) or []
            params = sorted(p for p in props if p != "action")
            meta.append({
                "name": name,
                "summary": first_line,
                "actions": list(actions),
                "params": params,
            })
        method = "introspection"
    except Exception as e:  # noqa: BLE001
        print(f"  (интроспекция не удалась: {e!r}; фолбэк на разбор server.py)")
        meta = _fallback_tools_meta()
        method = "fallback"
    if not meta:
        meta = _fallback_tools_meta()
        method = "fallback"
    return meta, method


def _fallback_tools_meta() -> list[dict]:
    src = (ROOT / "app/server.py").read_text(encoding="utf-8")
    meta = []
    for m in re.finditer(r"@mcp\.tool\([^)]*\)\s*\nasync def (\w+)\(", src):
        name = m.group(1)
        meta.append({"name": name, "summary": "", "actions": [], "params": []})
    return meta


def gen_tool_reference(tools_meta: list[dict], method: str) -> None:
    out = [header(source="app/server.py (живая интроспекция FastMCP mcp.list_tools)")]
    out += [
        "# Справочник инструментов",
        "",
        "Инструменты MCP-сервера ModusBI — это RPC-методы протокола JSON-RPC (Model Context Protocol). "
        "Снаружи интерфейс — JSON-RPC; при обращении к порталу сервер использует HTTP-вызовы "
        "вида action/command (не чистый REST).",
        "",
        f"Всего инструментов: **{N_TOOLS}**. Многие инструменты диспетчеризуют поведение по параметру "
        "`action` — ниже перечислены реальные значения `action` из схемы инструмента.",
        "",
    ]
    for t in sorted(tools_meta, key=lambda x: x["name"] or ""):
        out += [f"## `{t['name']}`", ""]
        if t.get("summary"):
            out += [t["summary"], ""]
        acts = t.get("actions") or []
        if acts:
            out += [
                "**Действия (`action`):**",
                "",
                ", ".join(f"`{a}`" for a in acts) + ".",
                "",
            ]
        params = t.get("params") or []
        if params:
            shown = params[:18]
            more = " …" if len(params) > 18 else ""
            out += ["**Параметры:** " + ", ".join(f"`{p}`" for p in shown) + more + ".", ""]
    if method != "introspection":
        out += [
            "> Справка собрана разбором исходного кода сервера; "
            "детальная пер-action справка дополняется.",
            "",
        ]
    write("architecture/tools/tool-reference.md", "\n".join(out))


# =============================================================================
# MAIN
# =============================================================================
def main() -> int:
    print(f"Генерация публичных доков в {PUBLIC.relative_to(ROOT)}/")
    print(f"  факты из кода: слагов={N_SLUGS}, create-типов={N_CREATABLE}, "
          f"tools={N_TOOLS}, prompts={N_PROMPTS}, frontend={FE_VERSION}")

    stats = gen_stats()
    gen_slug_reference()
    gen_slug_migration()
    gen_scoreboard()
    gen_components_readiness()
    # readiness/findings.md — НЕ генерируется механически: исходный FINDINGS.md написан
    # внутренней стенографией, которая не переживает regex-обезличивание (ломается в обрывки).
    # Этот файл курируется вручную (писатель + ревью) и обновляется отдельно. gen_findings() сохранён ниже,
    # но из конвейера исключён намеренно.
    # gen_findings()

    tools_meta, method = collect_tools_meta()
    print(f"  tool-reference: способ = {method} ({len(tools_meta)} инструментов)")
    gen_cheatsheet(tools_meta)
    gen_tool_reference(tools_meta, method)

    print("Готово. _stats.json:")
    print(json.dumps(stats, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
