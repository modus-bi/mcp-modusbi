"""
Helper для добавления текстовых блоков HsTextBlock с HTML контентом.

⚠️ Важно про высоту (h) text-блоков
====================================
Frontend ModusBI ограничивает HsTextBlock фиксированной высотой 88px
(= 4 row × 22px), если в layout entry стоит `"modified": false` и
отсутствует `"group"`.

При ручном изменении высоты через UI в layout entry устанавливается
```
{"h": <new_h>, "modified": true, "group": -1, ...}
```
и только после этого фронт уважает h. Поэтому helper ОБЯЗАН ставить эти
поля при создании, иначе любой блок выше 88px рендерится обрезанным.

Авто-расчёт h
-------------
Если в position не указан h, helper использует estimate_h(text_content) для
расчёта по содержимому HTML. Калибровка эмпирически выверена на реальных
отчётах (1 grid row ≈ 22px):
  - <h2> ......... 2.0 row (lede heading + margin)
  - <h3> ......... 1.7 row (section heading + margin)
  - <tr> ......... 1.45 row (~32px на строку с padding cells)
  - <pre> line ... 0.9 row (~20px на строку кода font 13px)
  - <p> .......... 1.0 row (~22px на параграф)
  - <li> ......... 1.2 row (~26px на пункт)
  - section box .. +1.5 row (border + padding контейнера)
  - callout box .. +1.0 row (border-left + padding)
Округление через math.ceil — лучше дать на 1 row больше, чем недодать
(гарантия отсутствия скролла на длинных таблицах).
"""

import math
import re
from typing import Any

from ..core.validation import sanitize_html


def apply_textblock_layout_workaround(layout_entry: dict, component_type: str) -> dict:
    """Mutate layout_entry in-place — обход фронт-ограничения для HsTextBlock.

    Frontend ModusBI ограничивает HsTextBlock высотой 88px, если в layout
    entry стоит `modified: false` или нет `group`. Только при
    `modified: true` и `group: -1` фронт уважает h из layout. См.
    text_block_helper module docstring.

    Использовать в КАЖДОМ месте, где строится layout entry для возможного
    HsTextBlock (component_crud._add_component, _add_no_dataset_component,
    _copy_component, batch_operations._add_multiple_components). Пустой
    no-op для всех остальных типов компонентов.

    Возвращает тот же dict для chaining (на случай list comprehension).
    """
    if component_type == "HsTextBlock":
        layout_entry["modified"] = True
        layout_entry["group"] = -1
    return layout_entry


def estimate_h(content: str) -> int:
    """Эвристика: расчёт `h` (grid row) по HTML-содержимому text-блока.

    Используется helper'ом, если в position не задан h. Калибровка см. в
    module-level docstring выше. Возвращает int в диапазоне [3, 32].

    Учитывает наличие inline-стилей: stylish-таблица (с padding/font-size
    на ячейках) рендерится крупнее (~33px tr), голая table без стилей —
    мельче (~18px tr).
    """
    if not content:
        return 3

    tr_count = content.count("<tr>")
    # Все <pre> блоки, не только первый. rstrip("\n") — чтобы trailing \n
    # не давал лишнюю фантомную строку при count("\n") + 1.
    pre_blocks = re.findall(r"<pre[^>]*>(.*?)</pre>", content, re.DOTALL)
    pre_lines = sum(b.rstrip("\n").count("\n") + 1 for b in pre_blocks if b)

    p_count = content.count("</p>")
    li_count = content.count("</li>")
    h3_count = content.count("</h3>")
    h2_count = content.count("</h2>")

    has_section_box = "background:#f6f8fa" in content or "border:1px solid #d0d7de" in content
    has_callout_box = "border-left:4px solid" in content

    # Стилизованная ли таблица? Признаки: inline-style на td/tr/table с
    # padding или font-size. Голая <table><tr><td>...</td></tr></table>
    # рендерится в ~18px на строку, стилизованная — в ~33px. Если ХОТЯ БЫ
    # одна из таблиц стилизована — считаем что styled (отчёт обычно
    # однородный, и недосчёт хуже пересчёта).
    table_styled = False
    if tr_count > 0:
        for t in re.findall(r"<table[^>]*>.*?</table>", content, re.DOTALL):
            if "padding:" in t or "font-size:" in t:
                table_styled = True
                break

    # Аналогично для <pre>: styled (background, padding) рендерится крупнее.
    pre_styled = False
    if pre_lines > 0:
        for p in re.findall(r"<pre[^>]*>.*?</pre>", content, re.DOTALL):
            if "padding:" in p or "background:" in p:
                pre_styled = True
                break

    h = 0.0
    h += 2.0 * h2_count          # h2 (lede)
    h += 1.7 * h3_count          # h3 (section title)
    if tr_count > 0:
        if table_styled:
            h += 1.45             # styled header
            h += 1.45 * tr_count  # styled tr (~33px)
        else:
            h += 1.0              # minimal header
            h += 0.85 * tr_count  # minimal tr (~18px)
    if pre_lines > 0:
        if pre_styled:
            h += 1.0              # padding styled code-блока
            h += 0.9 * pre_lines
        else:
            h += 0.5              # минимальный padding
            h += 0.85 * pre_lines  # ~18px code line
    h += 1.0 * p_count
    h += 1.2 * li_count
    if has_section_box:
        h += 1.5
    if has_callout_box:
        h += 1.0

    if h < 3:
        plain_len = len(re.sub(r"<[^>]+>", "", content))
        if plain_len < 80:
            h = 3
        elif plain_len < 200:
            h = 4
        else:
            h = 5

    return max(3, min(32, math.ceil(h)))


async def add_text_block_component(
    client,
    report_id: int,
    title: str,
    text_content: str,
    position: dict | None = None,
    showtitle: bool = False
) -> dict[str, Any]:
    """
    Добавить текстовый блок на дашборд.

    ⚠️ Про h: 1 grid row ≈ 22px. Калибровка для HsTextBlock:
      - короткий lede / 1-строчный callout ..... h=5  (110px)
      - 2-3 предложения / список 3-4 пункта .... h=7-10
      - секция с h3 + таблица 3-5 строк ........ h=18-22
      - секция с h3 + таблица 6-9 строк ........ h=24-30
      - секция с code-block 10-20 строк ........ h=20-30

    Helper автоматически выставляет `"modified": true` и `"group": -1`
    в каждом layout entry — без этих полей фронт ModusBI ограничивает блок
    высотой 88px независимо от h.

    Args:
        client: API client
        report_id: ID отчета
        title: Заголовок блока
        text_content: HTML содержимое блока (sanitized автоматически).
                      Поддерживается inline CSS, <table>, <pre><code>, <h2-h4>,
                      <p>, <ul>/<ol>/<li>, <strong>/<em>, <code>.
        position: Позиция в gride {"x": 0, "y": 0, "w": 60, "h": 14}.
                  Без указания — авто-pack под существующие компоненты.
                  Если "h" не указан в position — авто-расчёт через
                  estimate_h(text_content) по html-структуре.
        showtitle: Показывать ли заголовок (default: False — title прячется)

    Returns:
        {"success": True, "component_idx": "..."} or {"success": False, "error": "..."}

    Example (короткий callout):
        add_text_block_component(
            client, report_id=35, title="Вывод",
            text_content="<p><strong>Продажи выросли в этом регионе.</strong></p>",
            position={"x": 0, "y": 10, "w": 60, "h": 5}  # 110px — 1-2 строки
        )

    Example (большая секция с таблицей):
        add_text_block_component(
            client, report_id=35, title="weights-section",
            text_content='''
              <h3>Веса метрик</h3>
              <table><tr><th>Метрика</th><th>Вес</th></tr>
                <tr><td>Completeness</td><td>0.30</td></tr>
                ... 5 rows ...
              </table>
            ''',
            position={"x": 0, "y": 20, "w": 60, "h": 22}  # 484px
        )
    """
    # XSS: этот путь (component_operations → add_text_block) идёт МИМО
    # _add_component/_update_component, где живёт штатный sanitize_html, а
    # docstring обещает «sanitized автоматически». Режем <script>, on*= и
    # javascript: прямо здесь — до estimate_h и записи в config. Легитимную
    # разметку (<h2-h4>/<p>/<a href>, <table>, <pre>, inline CSS)
    # sanitize_html не трогает.
    title = sanitize_html(title)
    text_content = sanitize_html(text_content)

    # Get report
    get_response = await client.api_call("reports", "get", object_id=report_id)
    if get_response.get("status") != 200:
        return {"success": False, "error": get_response.get("message", "Error")}

    data = get_response.get("data", [])
    if not data:
        return {"success": False, "error": f"Report {report_id} not found"}

    report = data[0]

    # Get grid
    grid = report.get("grid") or {}
    layouts = grid.get("layouts") or {}
    components = grid.get("components") or {}

    # Component index
    existing_keys = [int(k) for k in components.keys() if k.isdigit()]
    component_idx = str(max(existing_keys) + 1) if existing_keys else "0"

    # Determine position
    if position is None:
        max_y = 0
        for layout_items in layouts.values():
            if isinstance(layout_items, list):
                for item in layout_items:
                    if isinstance(item, dict):
                        max_y = max(max_y, item.get("y", 0) + item.get("h", 4))
        position = {"x": 0, "y": max_y, "w": 24}

    # Авто-расчёт h по содержимому, если не указан явно.
    # estimate_h учитывает h2/h3/tr/pre/p/li/section_box/callout_box.
    if "h" not in position or position.get("h") is None:
        position = {**position, "h": estimate_h(text_content)}

    # Build text block config
    text_block_config = {
        "type": "HsTextBlock",
        "config": {
            "title": title,
            "description": text_content,
            "description__ru": text_content,
            "chartType": "textBlock",
            "autoApply": True,
            "dirty": False,
            "filters": {},
            "filtersDefault": {},
            "margin": {"l": 10, "r": 10, "t": 10, "b": 10, "pad": 0},
            "maximizable": True,
            "nocopy": False,
            "noexport": True,
            "outline": {"enabled": False, "width": 4},
            "showtitle": showtitle,
            "visuals": []
        }
    }

    # Layout configs for breakpoints
    layout_configs = {
        "hd": {"w": 30, "h": 16}, "lg": {"w": 24, "h": 14},
        "md": {"w": 20, "h": 14}, "sm": {"w": 15, "h": 14},
        "xs": {"w": 14, "h": 12}, "xxs": {"w": 10, "h": 10}
    }

    for bp, size in layout_configs.items():
        if bp not in layouts:
            layouts[bp] = []
        entry = {
            "x": position.get("x", 0),
            "y": position.get("y", 0),
            "w": position.get("w", size["w"]),
            "h": position.get("h", size["h"]),
            "minH": 2,
            "minW": 2 if bp in ["sm", "xs", "xxs"] else 3,
            "i": component_idx,
            "modified": False,
            "zIndex": len(components) + 1,
            "priority": -1
        }
        # CRITICAL: фронт ограничивает высотой 88px без modified=True+group=-1.
        # Используем ОДИН helper и здесь, и в _add_component/_copy_component/batch —
        # чтобы фикс жил в одном месте. См. apply_textblock_layout_workaround выше.
        apply_textblock_layout_workaround(entry, "HsTextBlock")
        layouts[bp].append(entry)

    components[component_idx] = text_block_config
    grid["layouts"] = layouts
    grid["components"] = components
    report["grid"] = grid

    # Save
    update_response = await client.api_call("reports", "update", object_id=report_id, data=[report])

    if update_response.get("status") != 200:
        return {"success": False, "error": update_response.get("message", "Error updating report")}

    return {
        "success": True,
        "message": "Text block added successfully",
        "report_id": report_id,
        "component": {
            "idx": component_idx,
            "type": "HsTextBlock",
            "title": title,
            "position": position
        }
    }
