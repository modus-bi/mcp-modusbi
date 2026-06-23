"""XSS regression tests: sanitize_html on the add_text_block /
add_chart_with_conclusion paths.

text_block_helper.add_text_block_component and
layout_helper.add_chart_with_text_pair write config.description, and the
component_operations → add_text_block path goes around _add_component /
_update_component where the standard sanitize_html lives
(core/validation.py). These tests confirm sanitization on those paths.

Coverage:
  1. sanitize_html directly — what it strips (<script>, on*=, javascript:)
     and what it keeps (h2-h4/p/a href/table/pre, inline CSS).
  2. add_text_block_component — description AND description__ru AND title
     are sanitized in the saved config.
  3. add_chart_with_text_pair — the text part of add_chart_with_conclusion
     is sanitized, legitimate markup is preserved.

Run:
    python -m app.tests.test_sanitize_textblock
"""
import asyncio
import sys
from pathlib import Path

_project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_project_root))

from app.core.validation import sanitize_html
from app.tools.text_block_helper import add_text_block_component
from app.tools.layout_helper import add_chart_with_text_pair
import app.tools.component_crud as component_crud


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


def section(title: str) -> None:
    print(f"\n=== {title} ===")


# Mix of dangerous and legitimate HTML
EVIL_HTML = (
    '<h3>Вывод</h3>'
    '<script>alert(1)</script>'
    '<p onclick="evil()">Текст <a href="javascript:alert(2)">ссылка</a></p>'
    '<img src=x onerror=alert(3)>'
    '<p><a href="https://modus.bi/docs">Документация</a></p>'
)


def _no_xss(html: str) -> bool:
    low = (html or "").lower()
    return ("<script" not in low and "onclick" not in low
            and "onerror" not in low and "javascript:" not in low)


class _MockClient:
    """Mock client: get отдаёт пустой отчёт, update перехватывает payload."""

    def __init__(self, captured: dict):
        self._captured = captured

    async def api_call(self, resource: str, action: str, **kwargs):
        if resource == "reports" and action == "get":
            return {"status": 200, "data": [{
                "ID": 5,
                "grid": {"layouts": {"lg": []}, "components": {}},
            }]}
        if resource == "reports" and action == "update":
            self._captured["report"] = (kwargs.get("data") or [None])[0]
            return {"status": 200}
        return {"status": 200, "data": []}


def main() -> None:
    section("sanitize_html — что режет")
    out = sanitize_html(EVIL_HTML)
    check("<script>...</script> вырезан целиком",
          "<script" not in out and "alert(1)" not in out, detail=out)
    check("onclick= удалён, тег <p> сохранён",
          "onclick" not in out and "<p>Текст" in out, detail=out)
    check("onerror= удалён", "onerror" not in out, detail=out)
    check("javascript: URI заблокирован",
          "javascript:" not in out and "blocked:" in out, detail=out)

    section("sanitize_html — что оставляет (легитимная разметка)")
    check("<h3> сохранён", "<h3>Вывод</h3>" in out, detail=out)
    check("<a href=https://...> сохранён",
          '<a href="https://modus.bi/docs">Документация</a>' in out, detail=out)
    legit = ('<h3>Раздел</h3><p><strong>Вывод.</strong></p>'
             '<table style="font-size:13px"><tr><td style="padding:8px">x</td>'
             '</tr></table><pre>code\nline2</pre>'
             '<ul><li>пункт</li></ul>')
    check("типовая разметка отчётов проходит без изменений (identity)",
          sanitize_html(legit) == legit, detail=sanitize_html(legit))
    check("None / пустая строка — passthrough",
          sanitize_html(None) is None and sanitize_html("") == "")

    section("Путь 1: add_text_block_component (component_crud add_text_block)")
    captured: dict = {}
    client = _MockClient(captured)
    res = asyncio.run(add_text_block_component(
        client, report_id=5,
        title='Вывод<script>steal()</script>',
        text_content=EVIL_HTML,
    ))
    check("вызов успешен", bool(res.get("success")), detail=str(res))
    cfg = captured["report"]["grid"]["components"]["0"]["config"]
    desc = cfg.get("description") or ""
    check("description: XSS вырезан", _no_xss(desc), detail=desc)
    check("description: легитимные теги остались",
          "<h3>Вывод</h3>" in desc and 'href="https://modus.bi/docs"' in desc,
          detail=desc)
    check("description__ru санитизирован идентично",
          cfg.get("description__ru") == desc, detail=str(cfg.get("description__ru")))
    check("title санитизирован",
          _no_xss(cfg.get("title") or "") and "Вывод" in (cfg.get("title") or ""),
          detail=str(cfg.get("title")))

    section("Путь 2: add_chart_with_text_pair (add_chart_with_conclusion)")
    chart_calls: dict = {}

    async def fake_add_component(**kwargs):
        chart_calls.update(kwargs)
        return {"success": True, "component": {"idx": "0"}}

    captured2: dict = {}
    client2 = _MockClient(captured2)
    orig_add = component_crud._add_component
    component_crud._add_component = fake_add_component
    try:
        res2 = asyncio.run(add_chart_with_text_pair(
            client2, report_id=5,
            chart_config={
                "type": "HsBarAMchartsChart",
                "title": "График",
                "dataset_id": 2,
                "category_field": "cat",
                "value_field": "val",
            },
            text_html=EVIL_HTML,
            text_title='Вывод<script>steal()</script>',
        ))
    finally:
        component_crud._add_component = orig_add

    check("вызов успешен", bool(res2.get("success")), detail=str(res2))
    cfg2 = captured2["report"]["grid"]["components"]["0"]["config"]
    desc2 = cfg2.get("description") or ""
    check("текст-блок: XSS вырезан", _no_xss(desc2), detail=desc2)
    check("текст-блок: легитимные теги остались",
          "<h3>Вывод</h3>" in desc2 and 'href="https://modus.bi/docs"' in desc2,
          detail=desc2)
    check("текст-блок: description__ru санитизирован идентично",
          cfg2.get("description__ru") == desc2,
          detail=str(cfg2.get("description__ru")))
    check("текст-блок: title санитизирован",
          _no_xss(cfg2.get("title") or ""), detail=str(cfg2.get("title")))
    check("график добавлен через _add_component (пара собрана)",
          chart_calls.get("component_type") == "HsBarAMchartsChart",
          detail=str(chart_calls))

    print(f"\n===\nResult: {ok} OK, {fail} FAIL")
    sys.exit(0 if fail == 0 else 1)


if __name__ == "__main__":
    main()
