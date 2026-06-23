"""
Style operations for MCP Server.

Actions:
- get: Get report CSS
- update: Update report CSS
- validate: Validate CSS
- classes_list: List available CSS classes
- examples_list: Get CSS examples
"""

import logging

from typing import Any

from ..core.exceptions import require
from ..core.security import check_action
from .css_schema import CSSSchemaProvider

logger = logging.getLogger(__name__)


# CSS schema provider
_css_schema = CSSSchemaProvider()


async def _get_style(client, report_id: int) -> dict[str, Any]:
    """Get report CSS."""
    response = await client.api_call("reports", "get", object_id=report_id)

    if response.get("status") != 200:
        return {"success": False, "error": response.get("message", "Unknown error")}

    data = response.get("data", [])
    if not data:
        return {"success": False, "error": f"Report {report_id} not found"}

    report = data[0]
    options = report.get("options", {})

    return {
        "success": True,
        "report_id": report.get("ID"),
        "report_name": report.get("name") or options.get("name__ru"),
        "current_css": options.get("CSStext", "")
    }


async def _update_style(client, report_id: int, css: str) -> dict[str, Any]:
    """Update report CSS."""
    # Get current report
    get_response = await client.api_call("reports", "get", object_id=report_id)

    if get_response.get("status") != 200:
        return {"success": False, "error": get_response.get("message", "Error getting report")}

    data = get_response.get("data", [])
    if not data:
        return {"success": False, "error": f"Report {report_id} not found"}

    report = data[0]

    # Update CSStext
    if "options" not in report:
        report["options"] = {}

    old_css = report["options"].get("CSStext", "")
    report["options"]["CSStext"] = css

    # Send update
    update_response = await client.api_call("reports", "update", object_id=report_id, data=[report])

    if update_response.get("status") != 200:
        return {"success": False, "error": update_response.get("message", "Error updating")}

    return {
        "success": True,
        "report_id": report_id,
        "message": "CSS updated successfully",
        "old_css": old_css,
        "new_css": css
    }


def _validate_css(css: str) -> dict[str, Any]:
    """Validate CSS code."""
    return _css_schema.validate_css(css)


def _list_classes(category: str = "all") -> dict[str, Any]:
    """Get CSS classes reference."""
    return _css_schema.get_classes(category)


def _list_examples(category: str = "all") -> dict[str, Any]:
    """Get CSS examples."""
    return _css_schema.get_examples(category)


# brand-pack CSS generator. Принимает 5-цветную тему и
# генерирует ~150 строк CSS покрывающих header, charts, filter, table,
# modal, scrollbar. Решает MCP_LIMITATIONS §6.3 — без него для каждого
# отчёта приходилось писать CSS вручную.
_THEME_DEFAULT = {
    "primary": "#1F77B4",     # основной (header, chart fill, buttons)
    "secondary": "#E3F2FD",   # вторичный (filter bg, hover)
    "bg": "#FFFFFF",          # фон отчёта
    "accent": "#FF6B35",      # акцент (badges, alerts)
    "text": "#1A1A1A",        # основной текст
}


def _build_theme_css(theme: dict) -> str:
    """Сгенерировать CSS из 5-цветной темы.

. Покрывает 6 групп селекторов: header gradient, chart bars,
    filter panel, table striped + headers, modal/buttons, scrollbar.
    """
    t = {**_THEME_DEFAULT, **(theme or {})}
    p, s, bg, a, tc = t["primary"], t["secondary"], t["bg"], t["accent"], t["text"]

    return f"""/* apply_theme: автогенерированная тема
   primary={p}, secondary={s}, bg={bg}, accent={a}, text={tc} */

/* === Header (top bar отчёта) === */
.hsHeader.hsHeader__report {{
  background: linear-gradient(135deg, {p} 0%, {p}cc 100%);
  color: {bg};
}}
.hsHeader.hsHeader__report .hs-header-title {{
  color: {bg};
  font-weight: 600;
}}

/* === Chart bars (fallback против #FFFFFF) === */
.amcharts-graph-column[fill="#FFFFFF"],
.amcharts-graph-column[fill="#ffffff"],
.amcharts-graph-line[stroke="#FFFFFF"] {{
  fill: {p} !important;
  stroke: {p} !important;
}}

/* === Filter panel === */
.hsFilterControlPanel {{
  background: {bg};
  border: 1px solid {s};
}}
.hsFilterControlPanel .filter-label {{
  color: {tc};
  font-weight: 500;
}}
.hsFilterControlPanel select:hover,
.hsFilterControlPanel .filter-item:hover {{
  background: {s};
}}
.hsFilterControlPanel .filter-active {{
  background: {p};
  color: {bg};
}}

/* === Table striped + headers === */
.hsTableReactabularChart thead th {{
  background: {p};
  color: {bg};
  font-weight: 600;
  border-bottom: 2px solid {p};
}}
.hsTableReactabularChart tbody tr:nth-child(even) {{
  background: {s};
}}
.hsTableReactabularChart tbody tr:hover {{
  background: {a}33;  /* accent с прозрачностью 20% */
}}

/* === Modal & buttons === */
.modal-header {{
  background: {p};
  color: {bg};
}}
.btn-primary,
.hsButton.primary {{
  background: {p};
  border-color: {p};
  color: {bg};
}}
.btn-primary:hover {{
  background: {p}cc;  /* slightly darker */
}}
.btn-accent,
.hsButton.accent {{
  background: {a};
  border-color: {a};
  color: {bg};
}}

/* === Scrollbar === */
::-webkit-scrollbar-thumb {{
  background: {p}80;  /* 50% opacity */
  border-radius: 4px;
}}
::-webkit-scrollbar-thumb:hover {{
  background: {p};
}}

/* === Body text & background === */
.hsReport {{
  background: {bg};
  color: {tc};
}}
"""


def _build_kpi_icons_css(kpi_icons: dict) -> str:
    """Сгенерировать CSS background-image для KPI компонентов.

. Стандартный HsTotalsPanelV2 не имеет нативного icon-slot,
    но картинка цепляется CSS-ом на .componentBody через background-image.

    Args:
        kpi_icons: dict {component_idx: icon_url} ИЛИ {component_idx: {url, size, position}}.
            component_idx — индекс компонента в отчёте (как в layout `i`).
            icon_url — URL/data:URI картинки.
    """
    if not kpi_icons:
        return ""
    rules = []
    for idx, spec in kpi_icons.items():
        if isinstance(spec, str):
            url = spec
            size = "32px"
            position = "top 12px right 12px"
        elif isinstance(spec, dict):
            url = spec.get("url", "")
            size = spec.get("size", "32px")
            position = spec.get("position", "top 12px right 12px")
        else:
            continue
        if not url:
            continue
        rules.append(
            f"/* KPI icon for component idx={idx} */\n"
            f".react-grid-item[data-i=\"{idx}\"] .hsTotalsPanelV2 .componentBody,\n"
            f".react-grid-item[data-i=\"{idx}\"] .totalsPanelV2 .componentBody {{\n"
            f"  background-image: url('{url}');\n"
            f"  background-position: {position};\n"
            f"  background-size: {size};\n"
            f"  background-repeat: no-repeat;\n"
            f"  padding-right: 56px;\n"
            f"}}"
        )
    if not rules:
        return ""
    return "/* === KPI icons === */\n" + "\n\n".join(rules) + "\n"


async def _apply_theme(
    client, report_id: int, theme: dict, mode: str = "merge",
    kpi_icons: dict | None = None,
) -> dict:
    """Применить brand-pack CSS к отчёту.

    Args:
        theme: dict с 5 ключами: primary, secondary, bg, accent, text.
            Можно частичный — отсутствующие берутся из _THEME_DEFAULT.
        mode: 'merge' (append к существующему CSS) | 'replace' (затирает).
            Default 'merge' чтобы не удалять кастомные правки.
        kpi_icons: {component_idx: url} или
            {component_idx: {url, size, position}}. Генерит CSS
            background-image для KPI компонентов (нативный icon slot
            у HsTotalsPanelV2 отсутствует).
    """
    if mode not in ("merge", "replace"):
        return {"success": False, "error": f"Unknown mode: {mode}. Use 'merge' or 'replace'."}

    theme_css = _build_theme_css(theme)
    # добавить KPI icons если передано
    if kpi_icons:
        kpi_css = _build_kpi_icons_css(kpi_icons)
        if kpi_css:
            theme_css = theme_css.rstrip() + "\n\n" + kpi_css

    if mode == "replace":
        return await _update_style(client, report_id, theme_css)

    # merge mode: append к существующему. _get_style возвращает поле
    # `current_css` (не `css`) — это содержимое options.CSStext в API.
    current = await _get_style(client, report_id)
    if not current.get("success"):
        return current  # error pass-through
    existing_css = current.get("current_css") or ""
    merged = (existing_css.rstrip() + "\n\n" + theme_css) if existing_css.strip() else theme_css
    return await _update_style(client, report_id, merged)


async def style_operations(
    client,
    action: str,
    report_id: int | None = None,
    css: str | None = None,
    category: str = "all",
    theme: dict | None = None,
    mode: str = "merge",
    kpi_icons: dict | None = None,
) -> dict[str, Any]:
    """
    CSS styling operations for reports.

    Actions:
    - get: Get report CSS
    - update: Update report CSS
    - validate: Validate CSS
    - classes_list: List available CSS classes
    - examples_list: Get CSS examples
    - apply_theme: генерация CSS из 5-цветной темы
    """
    match action:
        case "get":
            err = require(
                {"report_id": report_id},
                tool="style_operations", action="get",
                types={"report_id": "int"},
                example="style_operations(action='get', report_id=35)",
            )
            if err:
                return err
            return await _get_style(client, report_id)

        case "update":
            check_action("update")
            err = require(
                {"report_id": report_id, "css": css},
                tool="style_operations", action="update",
                types={"report_id": "int", "css": "str (CSS text)"},
                example="style_operations(action='update', report_id=35, css='.hsGridPanel { border-radius: 8px; }')",
            )
            if err:
                return err
            return await _update_style(client, report_id, css)

        case "validate":
            err = require(
                {"css": css},
                tool="style_operations", action="validate",
                types={"css": "str (CSS text)"},
                example="style_operations(action='validate', css='.foo { color: red; }')",
            )
            if err:
                return err
            return _validate_css(css)

        case "classes_list":
            return _list_classes(category)

        case "examples_list":
            return _list_examples(category)

        case "apply_theme":
            check_action("update")
            err = require(
                {"report_id": report_id, "theme": theme},
                tool="style_operations", action="apply_theme",
                types={
                    "report_id": "int",
                    "theme": "dict {primary, secondary, bg, accent, text}",
                },
                example=(
                    "style_operations(action='apply_theme', report_id=35, "
                    "theme={'primary':'#1B7B45','secondary':'#E8F5E9',"
                    "'bg':'#FFFFFF','accent':'#FF6B35','text':'#1A1A1A'}, "
                    "mode='merge')"
                ),
            )
            if err:
                return err
            return await _apply_theme(client, report_id, theme, mode=mode, kpi_icons=kpi_icons)

        case _:
            return {"error": f"Unknown action: {action}"}
