"""
MCP Server for ModusBI.

FastMCP-based server with:
- 19 tools grouped by domain
- User-driven prompt templates
- Single-instance per process (multi-portal via N mcpServers entries)
- Security modes: readonly, readwrite, demo

Prompts (user-driven):
- create_dashboard: Step-by-step dashboard creation
- style_report: CSS styling + presets for reports
- query_data: Build dataset queries (+ variables)
- export_report: Export to PDF/PNG/PPTX
- analyze_dataset: Analyze dataset structure
- customize_component: Visual config via slug overrides / 6 presets / overrides
- add_filters: Interactive filters + cascades + globalCategories
- add_conditional_formatting: Table/pivot conditional formatting rules
- manage_variables: Report variables & categories CRUD
- create_report_from_template: Create report from template (kpi_dashboard, ranking, etc.)

Tools (LLM-driven):
- instance_operations: Portal instance info (single-instance per process)
- report_operations: CRUD reports + export + clone
- dataset_operations: CRUD datasets / semantic layer
- datasource_operations: Data sources management
- dataset_query: Query data from datasets
- query_batch: Batch SQL queries
- sql_query_validate: Validate SQL, get schema
- dataset_create_from_sql: Create dataset with semantic layer
- preflight_check_datasource: Deep check if datasource can execute queries
- style_operations: Report-level CSS styling
- reportgroup_operations: Report groups management
- data_export_operations: Export data to CSV/Excel
- batch_operations: Batch operations for multiple objects
- report_template: Scaffold reports from predefined templates (kpi_dashboard, ranking, etc.)
- security_operations: Row Level Security (RLS) management

Usage:
    python -m app.server

    # With security mode:
    python -m app.server --readonly
    python -m app.server --demo
"""

import argparse
import contextlib
import logging
import os
import sys
from contextlib import asynccontextmanager
from typing import Annotated, Any, Literal

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations
from pydantic import Field

from .tools.param_docs import CANONICAL
from .tools.profiles import DEFER_META


# Shorthand builders to reduce boilerplate across 19 public tools
def _ro_ann(title: str) -> ToolAnnotations:
    """Read-only tool annotations — safe for auto-execution."""
    return ToolAnnotations(
        title=title,
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=True,
    )


def _rw_ann(title: str, *, destructive: bool = True, idempotent: bool = False) -> ToolAnnotations:
    """Write-capable tool annotations — may modify portal state."""
    return ToolAnnotations(
        title=title,
        readOnlyHint=False,
        destructiveHint=destructive,
        idempotentHint=idempotent,
        openWorldHint=True,
    )

from .core.instances import Instance, InstanceManager
from .core.security import SecurityMode, set_security_mode, get_security_mode
from .core.exceptions import APIError, NotFoundError, ValidationError

logger = logging.getLogger(__name__)

# Literal type aliases for strict JSON Schema enum in tool signatures
from .tools.action_types import (
    InstanceAction, ReportAction, DatasetAction,
    ComponentCrudAction, ComponentFiltersAction, ComponentAxesAction,
    ComponentStylingAction,
    DatasourceAction, StyleAction, ReportGroupAction,
    DataExportAction, BatchAction, ReportTemplateAction, SecurityAction,
)

# Reusable enum-like literals exposed through JSON Schema
AggregationLiteral = Literal["sum", "avg", "max", "min", "count", "none", ""]
BreakpointLiteral = Literal["hd", "lg", "md", "sm", "xs", "xxs"]
OrientationLiteral = Literal["horizontal", "vertical"]
StackingLiteral = Literal["stacked", "normal", "percent"]
PresetLiteral = Literal["minimal", "presentation", "dashboard", "dark", "print", "kpi"]
FieldTypeLiteral = Literal["string", "number", "date", "datetime", "boolean"]
ValueFieldsTypeLiteral = Literal["number", "string"]
ExportFormatLiteral = Literal["pdf", "png", "pptx"]
# resetMode каскада фильтров: к какому значению сбрасывать дочерний фильтр
# при смене родителя. Фронт поддерживает только "min"/"max"
# (docs/infrastructure/globalFilters.md, component_filters._VALID_RESET_MODES).
ResetModeLiteral = Literal["min", "max"]
# resetType каскада: когда сбрасывать — фронт поддерживает только "always".
ResetTypeLiteral = Literal["always"]
# pivot_link_set: фронт поддерживает только _blank/_self
# (component_axes._VALID_LINK_TARGETS).
LinkTargetLiteral = Literal["_blank", "_self"]

# Import tool implementations
from .tools.report_operations import report_operations as _report_operations
from .tools.dataset_operations import dataset_operations as _dataset_operations
from .tools.datasource_operations import datasource_operations as _datasource_operations
from .tools.query_execute import (
    query_batch as _query_batch,
    dataset_query as _dataset_query,
    sql_query_validate as _sql_query_validate,
    dataset_create_from_sql as _dataset_create_from_sql,
    preflight_check_datasource as _preflight_check_datasource
)
from .tools.component_operations import component_operations as _component_operations
from .tools.style_operations import style_operations as _style_operations
from .tools.batch_operations import batch_operations as _batch_operations
from .tools.report_template import report_template as _report_template
from .tools.reportgroup_operations import reportgroup_operations as _reportgroup_operations
from .tools.export_data import export_operations as _export_data_operations
from .tools.security_operations import security_operations as _security_operations
from .tools.schemas import (
    BatchQuerySpec,
    ComponentSpec,
    GroupClause,
    LayoutSpec,
    OrderClause,
    ReportGroupOptions,
    SelectField,
    WhereClause,
)
from .prompts import get_prompts, get_prompt_messages


# Глобальный менеджер инстансов (инициализируется в lifespan)
_instance_manager: InstanceManager | None = None


def get_instance_manager() -> InstanceManager:
    """Возвращает глобальный менеджер инстансов."""
    if _instance_manager is None:
        raise RuntimeError("InstanceManager не инициализирован. Сервер не запущен?")
    return _instance_manager


def _tool_error_envelope(e: Exception) -> dict[str, Any]:
    """Единый error-envelope для исключений API-слоя на границе MCP.

    api_call (core/instances.py) поднимает APIError на non-200 раньше
    tool-guard'ов — без этой обёртки пользователь видел голое
    «Error executing tool: HTTP 404» вместо {"success": False, ...}.
    """
    details = getattr(e, "details", None)
    status_code = details.get("status_code") if isinstance(details, dict) else None
    envelope: dict[str, Any] = {
        "success": False,
        "error": str(e),
    }
    if status_code is not None:
        envelope["status_code"] = status_code
    if status_code == 404 or isinstance(e, NotFoundError):
        envelope["hint"] = (
            "Объект не найден — проверьте id (list-action поможет найти существующие)."
        )
    return envelope


async def _dispatch_safe(coro) -> dict[str, Any]:
    """Await вызова диспетчера, конвертируя API-исключения в envelope.

    Ловим ТОЛЬКО ожидаемые ошибки API-слоя (APIError / NotFoundError /
    ValidationError) — прочие исключения (RuntimeError init и др.)
    пробрасываются как есть.
    """
    try:
        return await coro
    except (APIError, NotFoundError, ValidationError) as e:
        return _tool_error_envelope(e)


def _validate_modusbi_url(raw_url: str) -> str:
    """Validate and normalize MODUSBI_URL env var.

    Returns the cleaned URL ready for `Instance.base_url`. Raises RuntimeError
    with an actionable message on bad input. Logs warning for unusual but
    not-fatal cases (path / query / fragment).
    """
    from urllib.parse import urlparse

    url = raw_url.strip()
    if not url:
        raise RuntimeError(
            "MODUSBI_URL is empty. "
            "Set it to your portal URL, e.g. 'https://portal.modusbi.ru'. "
            "Fix in your mcp.json env block — see build/INSTALL.md."
        )

    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise RuntimeError(
            f"Invalid MODUSBI_URL scheme '{parsed.scheme or '(empty)'}': "
            f"must be 'http' or 'https'. "
            f"Got: {url!r}. Expected example: 'https://portal.modusbi.ru'. "
            f"Fix in your mcp.json env block — see build/INSTALL.md."
        )
    if not parsed.netloc:
        raise RuntimeError(
            f"Invalid MODUSBI_URL: missing hostname. "
            f"Got: {url!r}. Expected example: 'https://portal.modusbi.ru'. "
            f"Fix in your mcp.json env block — see build/INSTALL.md."
        )

    if parsed.path and parsed.path != "/":
        logger.warning(
            "MODUSBI_URL contains a path '%s' — this is unusual. "
            "ModusBI API paths (/v1/api/...) will be appended to it. "
            "If you see 404s, check whether your reverse-proxy actually "
            "expects this prefix.",
            parsed.path,
        )
    if parsed.query:
        logger.warning(
            "MODUSBI_URL contains query string '?%s' — will be ignored "
            "when building API URLs.",
            parsed.query,
        )
    if parsed.fragment:
        logger.warning(
            "MODUSBI_URL contains fragment '#%s' — will be ignored.",
            parsed.fragment,
        )

    # Reconstruct keeping scheme + netloc + path (no query/fragment).
    # Strip trailing slash from path — Instance.api_base_url will rstrip again
    # but doing it here makes logs cleaner.
    path = parsed.path.rstrip("/") if parsed.path else ""
    return f"{parsed.scheme}://{parsed.netloc}{path}"


@asynccontextmanager
async def server_lifespan(server):
    """
    Lifespan контекст для инициализации сервера.

    Single-instance per process — конфиг читается из env vars при старте:
    - MODUSBI_URL, MODUSBI_USERNAME, MODUSBI_PASSWORD (обязательные)
    - MODUSBI_INSTANCE_NAME (опциональный, для логов; default "default")
    - MODUSBI_INSTANCE_DESCRIPTION (опциональный)

    Multi-portal сценарии — через несколько entries в mcp.json, каждая
    со своими env vars (см. INSTALL.md «Multiple portals»).

    stdout защищён от случайного вывода через contextlib.redirect_stdout —
    любой print() в процессе init уходит в stderr, не ломая JSON-RPC протокол.
    """
    global _instance_manager

    with contextlib.redirect_stdout(sys.stderr):
        # Проверяем обязательные env vars
        missing = []
        for var in ("MODUSBI_URL", "MODUSBI_USERNAME", "MODUSBI_PASSWORD"):
            if not os.environ.get(var):
                missing.append(var)
        if missing:
            logger.error(
                "Missing required env vars: %s. "
                "All three must be set: MODUSBI_URL, MODUSBI_USERNAME, MODUSBI_PASSWORD. "
                "Configure in mcp.json env block — see build/INSTALL.md.",
                ", ".join(missing)
            )
            raise RuntimeError(f"Missing required env vars: {', '.join(missing)}")

        # Валидируем URL формат (схема, hostname, predicting сюрпризы с path/query)
        base_url = _validate_modusbi_url(os.environ["MODUSBI_URL"])

        instance_name = os.environ.get("MODUSBI_INSTANCE_NAME", "default")
        instance = Instance(
            name=instance_name,
            base_url=base_url,
            username=os.environ["MODUSBI_USERNAME"],
            password=os.environ["MODUSBI_PASSWORD"],
            description=os.environ.get("MODUSBI_INSTANCE_DESCRIPTION", ""),
        )
        _instance_manager = InstanceManager(instance)

        try:
            await _instance_manager.authenticate()
            logger.info(
                "Connected to '%s' (%s)",
                instance_name,
                instance.base_url,
            )
        except Exception as e:
            logger.warning("Could not authenticate to '%s': %s", instance_name, e)

        logger.info("Security mode: %s", get_security_mode().value)

    try:
        yield {"instances": _instance_manager}
    finally:
        if _instance_manager is not None:
            await _instance_manager.aclose()  # close shared httpx pool
        _instance_manager = None


SERVER_INSTRUCTIONS = """\
ModusBI MCP Server — платформа BI-отчётов и дашбордов для портала ModusBI.

Типичные workflow:

1. Создание отчёта с нуля:
   report_operations(action="create", ...) → dataset_operations(action="create", ...)
   → component_crud(action="add", ...) → component_filters(action="filter_field_add", ...)
   → style_operations(action="update", ...) [CSS]

2. Готовые шаблоны (быстрее):
   report_template(action="list") → report_template(action="scaffold", template=...)
   Шаблоны: kpi_dashboard, ranking, comparison, factor_analysis, geo_analytics, simple.

3. Работа с данными:
   - dataset_query — SQL-like запрос к семантическому слою (readonly)
   - sql_query_validate — проверка SQL до create dataset
   - query_batch — несколько запросов одним вызовом

4. Batch-операции:
   - batch_operations(action="components_add", report_id=..., components=[...])
   - batch_operations(action="reports_export", report_ids=[...], format="pdf")

Ключевые конвенции:
 - "report" = отчёт/дашборд, "component" = виджет, "dataset" = семантический слой.
 - component_idx — 0-based индекс (НЕ id).
 - 30 типов компонентов; component_crud(action="types_list") — список.
 - Визуальная настройка — 3 уровня: атомарные params (legend_visible, bg_color),
   config_overrides (slug-ключи, см. config_schema.SLUG_SCHEMA), presets (minimal/presentation/dashboard/dark/print/kpi).

Режим безопасности:
 - По умолчанию readonly (с версии 1.0.0). Доступны: list/get/summary/*_list/validate/export.
 - Для create/update/delete — запуск с --readwrite.
 - Ошибка "требует режим: readwrite" → сервер запущен в readonly.

Подсказки по ошибкам:
 - {success: False, error, missing: [...], expected_types: {...}, hint, example} —
   заполнить недостающие параметры из example и повторить вызов.
 - {error: "Unknown action: X"} — использовать help-action: component_crud(action="help").

Административные tools (не в главных workflow):
 - instance_operations — info о текущем портале (single-instance per process)
 - datasource_operations — управление подключениями к БД
 - security_operations — Row Level Security (RLS)
 - preflight_check_datasource — глубокая проверка перед использованием

Multi-portal: настраивается через несколько mcpServers entries в mcp.json
(один процесс = один портал). См. INSTALL.md «Multiple portals».

Когда НЕ использовать этот сервер:
 - Не-ModusBI источники данных (только ModusBI API).
 - Управление пользователями/правами (только RLS через security_operations).
"""

# Создаём FastMCP сервер
mcp = FastMCP(
    "modusbi",
    instructions=SERVER_INSTRUCTIONS,
    lifespan=server_lifespan,
    json_response=True,
)


# =============================================================================
# TOOLS: instance_operations
# =============================================================================

@mcp.tool(annotations=_ro_ann("Portal instance information (read-only)"), meta=DEFER_META)
async def instance_operations(
    action: InstanceAction,
) -> dict[str, Any]:
    """
    Get information about the configured portal instance.

    Single-instance per process model: the portal is configured via env vars
    in mcp.json. To work with multiple portals, configure multiple mcpServers
    entries — see INSTALL.md "Multiple portals" section.

    Actions:
    - list: List configured instance (always 1 in this model — for compat).
    - get_active: Get current instance info (URL, name, token state).

    Returns:
        list: {instances: [{name, base_url, is_active, description}]}
        get_active: {instance: {name, base_url, token_valid, ...}}
    """
    manager = get_instance_manager()
    if action == "list":
        return {"instances": manager.list()}
    elif action == "get_active":
        return {"instance": manager.get_active().to_dict(include_token=True)}
    return {"error": f"Unknown action: {action}"}


# =============================================================================
# TOOLS: report_operations
# =============================================================================

@mcp.tool(annotations=_rw_ann("Report CRUD + export + clone"))
async def report_operations(
    action: ReportAction,
    report_id: Annotated[int | None, Field(description=CANONICAL["report_id"])] = None,
    name: Annotated[str | None, Field(description=CANONICAL["name"] + " For action='help', pass the action name to describe.")] = None,
    caption: Annotated[str | None, Field(description=CANONICAL["caption"])] = None,
    group_id: Annotated[int | None, Field(description=CANONICAL["group_id"])] = None,
    remark: Annotated[str | None, Field(description=CANONICAL["remark"])] = None,
    parent_id: Annotated[int, Field(description=CANONICAL["parent_id"])] = 0,
    description: Annotated[str, Field(description=CANONICAL["description"])] = "",
    ord: Annotated[int, Field(description=CANONICAL["ord"])] = 0,
    format: ExportFormatLiteral = "pdf",
    page_size: Annotated[str, Field(description=CANONICAL["page_size"])] = "A4",
    page_orientation: Annotated[str, Field(description=CANONICAL["page_orientation"])] = "portrait",
    output_dir: Annotated[str | None, Field(description=CANONICAL["output_dir"])] = None,
    filename: Annotated[str | None, Field(description=CANONICAL["filename"])] = None,
    timeout: Annotated[int, Field(description=CANONICAL["timeout"])] = 120,
    global_filters: Annotated[dict | None, Field(description="Map alias → {'enabled': True, 'selected': [...]} for cross-component filtering.")] = None,
    variable_name: Annotated[str | None, Field(description=CANONICAL["variable_name"])] = None,
    variable_value: Annotated[str | list[str] | None, Field(description=CANONICAL["variable_value"])] = None,
    category_name: Annotated[str | None, Field(description=CANONICAL["category_name"])] = None,
    category_selected: Annotated[str | None, Field(description=CANONICAL["category_selected"])] = None,
    category_options: Annotated[list[str] | None, Field(description=CANONICAL["category_options"])] = None,
    cell_mode: Annotated[str | None, Field(description=CANONICAL["cell_mode"])] = None,
    allow_overlap_mode: Annotated[bool | None, Field(description=CANONICAL["allow_overlap_mode"])] = None,
    free_pane_movement: Annotated[bool | None, Field(description=CANONICAL["free_pane_movement"])] = None,
    no_gap_mode: Annotated[bool | None, Field(description=CANONICAL["no_gap_mode"])] = None,
    recalculated_cell_mode: Annotated[bool | None, Field(description=CANONICAL["recalculated_cell_mode"])] = None,
    grouping_mode: Annotated[bool | None, Field(description=CANONICAL["grouping_mode"])] = None,
    limit: Annotated[int, Field(description=CANONICAL["limit"])] = 50,
    offset: Annotated[int, Field(description=CANONICAL["offset"])] = 0,
) -> dict[str, Any]:
    """
    CRUD for reports + components_list + export (pdf/pptx) + variables/categories + clone.

    Actions: help, list, get, create, update, delete, summary, components_list, groups_list,
             export, export_info, variables_list/add/update/delete, categories_list/add/update/delete,
             get_options, update_options, clone, global_filters_list, global_filter_delete.

    ⚠️ DESTRUCTIVE actions:
    - delete: permanently deletes the report AND cascades to all its components, filters,
              layouts, variables. This action is irreversible and cannot be undone.
              Consider report_operations(action='get') first to backup the report config.
    - variables_delete / categories_delete / global_filter_delete: permanently removes
              the specified entity from the report; cannot be undone.
    - update / update_options: overwrites specified fields — previous values are lost.

    For examples: report_operations(action="help", name="<action_name>")

    list/groups_list are paginated (limit=50, offset=0).
    clone copies all components, filters, variables. export requires reports service reachable.

    ⚠️ Destructive actions: delete, variables_delete, categories_delete, global_filter_delete
    (permanently removes data, cannot be undone without a prior backup).
    Requires readwrite mode: create, update, delete, clone, *_add, *_update, *_delete.
    """
    if action == "help":
        from .tools.help_texts import _help, HELP_REPORT
        return _help(name, HELP_REPORT)

    manager = get_instance_manager()
    client = await manager.get_client()

    return await _dispatch_safe(_report_operations(
        client=client,
        action=action,
        report_id=report_id,
        name=name,
        caption=caption,
        group_id=group_id,
        remark=remark,
        parent_id=parent_id,
        description=description,
        ord=ord,
        format=format,
        page_size=page_size,
        page_orientation=page_orientation,
        output_dir=output_dir,
        filename=filename,
        timeout=timeout,
        global_filters=global_filters,
        variable_name=variable_name,
        variable_value=variable_value,
        category_name=category_name,
        category_selected=category_selected,
        category_options=category_options,
        cell_mode=cell_mode,
        allow_overlap_mode=allow_overlap_mode,
        free_pane_movement=free_pane_movement,
        no_gap_mode=no_gap_mode,
        recalculated_cell_mode=recalculated_cell_mode,
        grouping_mode=grouping_mode,
        limit=limit,
        offset=offset,
    ))


# =============================================================================
# TOOLS: dataset_operations
# =============================================================================

@mcp.tool(annotations=_rw_ann("Dataset (semantic layer) CRUD"))
async def dataset_operations(
    action: DatasetAction,
    dataset_id: Annotated[int | None, Field(description=CANONICAL["dataset_id"])] = None,
    name: Annotated[str | None, Field(description=CANONICAL["name"])] = None,
    caption: Annotated[str | None, Field(description=CANONICAL["caption"])] = None,
    datasource_id: Annotated[int | None, Field(description=CANONICAL["datasource_id"])] = None,
    sql: Annotated[str | None, Field(description=CANONICAL["query"])] = None,
    rls: Annotated[bool | None, Field(description=CANONICAL["rls"])] = None,
    sql_rls: Annotated[str | None, Field(description=CANONICAL["query_rls"])] = None,
    field_aliases: Annotated[dict | None, Field(description="Map field name → {'alias': '...', 'description': '...'}. MUST be set BEFORE binding dataset to components.")] = None,
    limit: Annotated[int, Field(description=CANONICAL["limit"])] = 50,
    offset: Annotated[int, Field(description=CANONICAL["offset"])] = 0,
) -> dict[str, Any]:
    """
    CRUD for datasets (semantic layer on top of datasources).

    Actions: help, list, get, fields_list, create, update, delete.
    For examples: dataset_operations(action="help", name="<action>")

    ⚠️ DESTRUCTIVE actions:
    - delete: permanently deletes the dataset. This action is irreversible and cannot be
              undone. WARNING: it breaks every report and component that references the
              dataset — they will fail to load until rebuilt or redirected to another dataset.
    - update: overwrites specified fields (query / field_aliases / rls). Changing query
              may break existing component bindings.

    ⚠️ field_aliases MUST be set BEFORE binding dataset to components — backend rejects
    alias changes on fields already used in components (HTTP 400). Workflow:
    create → set field_aliases → THEN add components.

    Prefer dataset_create_from_sql over create (it validates SQL). action="update" with
    query also auto-validates SQL. list is paginated (limit=50, offset=0).

    ⚠️ Destructive actions: delete (permanently removes dataset, cannot be undone;
    breaks dependent reports/components).
    Requires readwrite mode: create, update, delete.
    """
    if action == "help":
        from .tools.help_texts import _help, HELP_DATASET
        return _help(name, HELP_DATASET)

    manager = get_instance_manager()
    client = await manager.get_client()

    return await _dispatch_safe(_dataset_operations(
        client=client,
        action=action,
        dataset_id=dataset_id,
        name=name,
        caption=caption,
        datasource_id=datasource_id,
        query=sql,
        rls=rls,
        query_rls=sql_rls,
        field_aliases=field_aliases,
        limit=limit,
        offset=offset,
    ))


# =============================================================================
# TOOLS: component_crud (split from component_operations)
# =============================================================================

@mcp.tool(annotations=_rw_ann("Component CRUD + layout"))
async def component_crud(
    action: ComponentCrudAction,
    report_id: Annotated[int | None, Field(description=CANONICAL["report_id"])] = None,
    component_idx: Annotated[int | None, Field(description=CANONICAL["component_idx"])] = None,
    component_idx_2: Annotated[int | None, Field(description="Second component index for swap action.")] = None,
    component_type: Annotated[str | None, Field(description=CANONICAL["component_type"])] = None,
    title: Annotated[str | None, Field(description=CANONICAL["title"])] = None,
    dataset_id: Annotated[int | None, Field(description=CANONICAL["dataset_id"])] = None,
    dataset_name: Annotated[str | None, Field(description=CANONICAL["dataset_name"])] = None,
    category_field: Annotated[str, Field(description=CANONICAL["category_field"])] = "",
    value_field: Annotated[str | None, Field(description=CANONICAL["value_field"])] = None,
    aggregation: AggregationLiteral = "",
    value_fields_type: ValueFieldsTypeLiteral = "number",
    position: Annotated[dict | None, Field(description="Component position/size {'x':int, 'y':int, 'w':int, 'h':int} (grid units).")] = None,
    x: Annotated[int | None, Field(description=CANONICAL["x"])] = None,
    y: Annotated[int | None, Field(description=CANONICAL["y"])] = None,
    w: Annotated[int | None, Field(description=CANONICAL["w"])] = None,
    h: Annotated[int | None, Field(description=CANONICAL["h"])] = None,
    z_index: Annotated[int | None, Field(description="Integer stacking order; higher is rendered above lower (e.g. 100 for dropdowns).")] = None,
    limit: Annotated[int, Field(description=CANONICAL["limit"])] = 100,
    field_titles: Annotated[dict | None, Field(description="Map technical field name → human-readable label, e.g. {region: Регион}.")] = None,
    where_filter: Annotated[list[dict] | None, Field(description="Filter conditions list [{'field':'x', 'operator':'=', 'value':'...'}] applied to the component.")] = None,
    text_content: Annotated[str | None, Field(description=CANONICAL["text_content"])] = None,
    row_fields: Annotated[str | None, Field(description=CANONICAL["row_fields"])] = None,
    column_fields: Annotated[str | None, Field(description=CANONICAL["column_fields"])] = None,
    size_field: Annotated[str | None, Field(description=CANONICAL["size_field"])] = None,
    series_field: Annotated[str | None, Field(description="Dataset field name used for multi-series grouping (e.g. 'product' for one bar per category × series). Frontend builds N series from distinct values. Supported: HsBar/Line/Area/StockAMchartsChart.")] = None,
    subheader_field: Annotated[str | None, Field(description="For HsTotalsPanelV2: secondary value field rendered as subheader (under main KPI value).")] = None,
    info_fields: Annotated[str | None, Field(description="For HsTotalsPanelV2: comma-separated extra info-strings (e.g. 'avg_price,total_count') rendered as info-rows below KPI.")] = None,
    legend_visible: Annotated[bool | None, Field(description=CANONICAL["legend_visible"])] = None,
    legend_position: Annotated[str | None, Field(description=CANONICAL["legend_position"])] = None,
    labels_visible: Annotated[bool | None, Field(description=CANONICAL["labels_visible"])] = None,
    orientation: OrientationLiteral | None = None,
    bg_color: Annotated[str | None, Field(description=CANONICAL["bg_color"])] = None,
    stacking: StackingLiteral | None = None,
    config_overrides: Annotated[dict | None, Field(description=CANONICAL["config_overrides"])] = None,
    preset: PresetLiteral | None = None,
    target_report_id: Annotated[int | None, Field(description="Destination report ID when copying a component across reports.")] = None,
    breakpoint: BreakpointLiteral | None = None,
    slug_category: Annotated[str | None, Field(description=CANONICAL["slug_category"])] = None,
) -> dict[str, Any]:
    """
    Component CRUD + layout + slug introspection.

    Actions: help, types_list, get, add, add_text_block, add_chart_with_conclusion,
             update, delete, data, copy, layout_update, layout_get_breakpoints,
             layout_update_breakpoint, swap, list_slugs, list_presets.

    ⚠️ DESTRUCTIVE actions:
    - delete: permanently removes the component and cascades to its layouts,
              filter bindings, conditional rules and calc fields. This action is
              irreversible and cannot be undone.
    - update / layout_update / layout_update_breakpoint: overwrites specified
              fields (title / dataset / axes / position). Previous values are lost.

    For per-action details and examples: component_crud(action="help", value_field="add")
    For the actions list: component_crud(action="help")

    Tables ALWAYS use aggregation="none". text_content is sanitized (no <script>).
    Visuals: Level 1 (legend_visible/bg_color/stacking/...), Level 2 (config_overrides with flat slug keys),
    Level 3 (preset name).

    ⚠️ Destructive actions: delete (permanently deletes component + cascading
    layouts/filters, cannot be undone).
    Requires readwrite mode: add, add_text_block, add_chart_with_conclusion, update,
    delete, copy, layout_update, layout_update_breakpoint, swap.
    """
    if action == "help":
        from .tools.help_texts import _help, HELP_COMPONENT_CRUD
        return _help(slug_category or value_field, HELP_COMPONENT_CRUD)

    manager = get_instance_manager()
    client = await manager.get_client()

    return await _dispatch_safe(_component_operations(
        client=client,
        action=action,
        report_id=report_id,
        component_idx=component_idx,
        component_idx_2=component_idx_2,
        component_type=component_type,
        title=title,
        dataset_id=dataset_id,
        dataset_name=dataset_name,
        category_field=category_field,
        value_field=value_field,
        aggregation=aggregation,
        value_fields_type=value_fields_type,
        position=position,
        x=x,
        y=y,
        w=w,
        h=h,
        z_index=z_index,
        limit=limit,
        field_titles=field_titles,
        where_filter=where_filter,
        text_content=text_content,
        row_fields=row_fields,
        column_fields=column_fields,
        size_field=size_field,
        series_field=series_field,
        subheader_field=subheader_field,
        info_fields=info_fields,
        legend_visible=legend_visible,
        legend_position=legend_position,
        labels_visible=labels_visible,
        orientation=orientation,
        bg_color=bg_color,
        stacking=stacking,
        config_overrides=config_overrides,
        preset=preset,
        target_report_id=target_report_id,
        breakpoint=breakpoint,
        slug_category=slug_category,
    ))


# =============================================================================
# TOOLS: component_filters (split from component_operations)
# =============================================================================

@mcp.tool(annotations=_rw_ann("Component filters CRUD"))
async def component_filters(
    action: ComponentFiltersAction,
    report_id: Annotated[int | None, Field(description=CANONICAL["report_id"])] = None,
    component_idx: Annotated[int | None, Field(description=CANONICAL["component_idx"])] = None,
    value_field: Annotated[str | None, Field(description=CANONICAL["value_field"])] = None,
    dataset_id: Annotated[int | None, Field(description=CANONICAL["dataset_id"])] = None,
    alias: Annotated[str | None, Field(description=CANONICAL["alias"])] = None,
    field_type: FieldTypeLiteral | None = None,
    depends_on: Annotated[str | None, Field(description=CANONICAL["depends_on"])] = None,
    reset_mode: Annotated[ResetModeLiteral | None, Field(description="Cascade reset target when the parent filter changes: 'min' (reset child to minimum value) or 'max' (to maximum). Written to globalFilters[alias].resetMode.")] = None,
    reset_type: Annotated[ResetTypeLiteral | None, Field(description="When to reset the child filter on parent change: 'always' (the only value supported by the frontend). Written to globalFilters[alias].resetType.")] = None,
    # filters_grid_layout пробрасывает component_indices/cols/...
    # через config_overrides для convenience action.
    config_overrides: Annotated[dict | None, Field(description=CANONICAL["config_overrides"])] = None,
) -> dict[str, Any]:
    """
    Filter axis + global filter + cascade + grid layout management.

    Actions: help, set_global_filter, reset_global_filters, filter_fields_list,
             filter_field_add, filter_field_remove, filter_set_cascade,
             filters_grid_layout.

    ⚠️ DESTRUCTIVE: filter_field_remove permanently removes filter binding
    (re-add with dataset_id, alias, field_type); reset_global_filters clears
    all global filter selections (irreversible from MCP, users re-select).

    For examples: component_filters(action="help", value_field="filter_field_add")

    filter_set_cascade reset rules (optional): reset_mode='min'|'max' — value the
    child filter resets to when the parent changes; reset_type='always' — reset on
    every parent change (the only value the frontend supports).

    CRITICAL: filter_field_add must be called on EVERY data-component
    (chart/table/KPI/map), not only on the FilterControlPanel — otherwise
    dropdown shows values but data is not filtered.

    Requires readwrite mode: set_global_filter, reset_global_filters,
    filter_field_add, filter_field_remove, filter_set_cascade,
    filters_grid_layout.
    """
    if action == "help":
        from .tools.help_texts import _help, HELP_COMPONENT_FILTERS
        return _help(value_field, HELP_COMPONENT_FILTERS)

    manager = get_instance_manager()
    client = await manager.get_client()

    return await _dispatch_safe(_component_operations(
        client=client,
        action=action,
        report_id=report_id,
        component_idx=component_idx,
        value_field=value_field,
        dataset_id=dataset_id,
        alias=alias,
        field_type=field_type,
        depends_on=depends_on,
        reset_mode=reset_mode,
        reset_type=reset_type,
        config_overrides=config_overrides,
    ))


# =============================================================================
# TOOLS: component_axes (split from component_operations)
# =============================================================================

@mcp.tool(annotations=_rw_ann("Component axes, calc fields, pages"), meta=DEFER_META)
async def component_axes(
    action: ComponentAxesAction,
    report_id: Annotated[int | None, Field(description=CANONICAL["report_id"])] = None,
    component_idx: Annotated[int | None, Field(description=CANONICAL["component_idx"])] = None,
    value_field: Annotated[str | None, Field(description=CANONICAL["value_field"])] = None,
    title: Annotated[str | None, Field(description=CANONICAL["title"])] = None,
    dataset_id: Annotated[int | None, Field(description=CANONICAL["dataset_id"])] = None,
    calc_expression: Annotated[str | None, Field(description=CANONICAL["calc_expression"])] = None,
    target_axis: Annotated[str | None, Field(description=CANONICAL["target_axis"])] = None,
    page_id: Annotated[int | None, Field(description=CANONICAL["page_id"])] = None,
    field_id: Annotated[str | None, Field(description=CANONICAL["field_id"])] = None,
    target_url: Annotated[str | None, Field(description=CANONICAL["target_url"])] = None,
    link_target: LinkTargetLiteral = "_blank",
    field_index: Annotated[int | None, Field(description=CANONICAL["field_index"])] = None,
    drill_category_id: Annotated[str | None, Field(description=CANONICAL["drill_category_id"])] = None,
    drill_direction: Annotated[str | None, Field(description=CANONICAL["drill_direction"])] = None,
    drill_selected: Annotated[str | None, Field(description=CANONICAL["drill_selected"])] = None,
    config_overrides: Annotated[dict | None, Field(description=CANONICAL["config_overrides"])] = None,
) -> dict[str, Any]:
    """
    Calc fields, PageContainer pages, pivot drill-through links, drill-down hierarchy,
    TabsPanel buttons, conditional formatting rules, map geokeys.

    Actions: help, calc_fields_* (list/add/update/remove), page_* (list/add/remove/rename),
             pivot_link_set/remove, drill_* (get/add_level/delete_level/change_level/toggle_date_range/set_field),
             conditional_rule_* (add/list/delete), geodata_list, map_set_geokeys, map_get_geokeys,
             tabs_button_* (list/add/delete).

    ⚠️ DESTRUCTIVE actions:
    - calc_fields_remove: permanently deletes the calculated field. Irreversible and
              cannot be undone — the expression is lost.
    - page_remove: permanently deletes a PageContainer page AND all components bound to
              that page. This action is irreversible and cannot be undone.
    - pivot_link_remove: permanently removes the pivot drill-through link configuration.
    - drill_delete_level: permanently deletes a level from the drill-down hierarchy.
              Cannot be undone — the level configuration is lost.
    - conditional_rule_delete: permanently deletes the conditional formatting rule
              (colors, indicators, thresholds). Irreversible.
    - tabs_button_delete: permanently removes a navigation button from a TabsPanel.
              Cannot be undone.
    - calc_fields_update / map_set_geokeys / drill_change_level: overwrites existing
              configuration — previous state is lost.

    For details: component_axes(action="help", value_field="<action>")

    ⚠️ Destructive actions: calc_fields_remove, page_remove, pivot_link_remove,
    drill_delete_level, conditional_rule_delete, tabs_button_delete (permanently deletes
    configuration, cannot be undone).
    Requires readwrite mode: calc_fields_add/update/remove, page_add/remove/rename,
    pivot_link_set/remove, drill_add_level/delete_level/change_level/toggle_date_range/set_field,
    conditional_rule_add/delete, map_set_geokeys, tabs_button_add/delete.
    """
    if action == "help":
        from .tools.help_texts import _help, HELP_COMPONENT_AXES
        return _help(value_field, HELP_COMPONENT_AXES)

    manager = get_instance_manager()
    client = await manager.get_client()

    return await _dispatch_safe(_component_operations(
        client=client,
        action=action,
        report_id=report_id,
        component_idx=component_idx,
        value_field=value_field,
        title=title,
        dataset_id=dataset_id,
        calc_expression=calc_expression,
        target_axis=target_axis,
        page_id=page_id,
        field_id=field_id,
        target_url=target_url,
        link_target=link_target,
        field_index=field_index,
        drill_category_id=drill_category_id,
        drill_direction=drill_direction,
        drill_selected=drill_selected,
        config_overrides=config_overrides,
    ))


# =============================================================================
# TOOLS: component_styling (split from component_operations)
# =============================================================================

@mcp.tool(annotations=_rw_ann("Component visual styling"))
async def component_styling(
    action: ComponentStylingAction,
    report_id: Annotated[int | None, Field(description=CANONICAL["report_id"])] = None,
    component_idx: Annotated[int | None, Field(description=CANONICAL["component_idx"])] = None,
    value_field: Annotated[str | None, Field(description=CANONICAL["value_field"])] = None,
    field_index: Annotated[int | None, Field(description=CANONICAL["field_index"])] = None,
    config_overrides: Annotated[dict | None, Field(description=CANONICAL["config_overrides"])] = None,
) -> dict[str, Any]:
    """
    Conditional formatting, field sorting, map geo-binding (subset of component_axes).

    Actions: conditional_rule_add/list/delete, field_sort_set, geodata_list,
             map_set_geokeys, map_get_geokeys. (These also live in component_axes.)

    ⚠️ DESTRUCTIVE actions:
    - conditional_rule_delete: permanently deletes the conditional formatting rule
              (colors, indicators, thresholds). This action is irreversible and cannot
              be undone — the rule config is lost.
    - field_sort_set / map_set_geokeys: overwrites existing sort/geokey configuration —
              previous values are lost.

    For details: component_styling(action="help", value_field="<action>")

    ⚠️ Destructive actions: conditional_rule_delete (permanently removes formatting
    rule, cannot be undone).
    Requires readwrite mode: conditional_rule_add, conditional_rule_delete,
    field_sort_set, map_set_geokeys.
    """
    if action == "help":
        from .tools.help_texts import _help, HELP_COMPONENT_STYLING
        return _help(value_field, HELP_COMPONENT_STYLING)

    manager = get_instance_manager()
    client = await manager.get_client()

    return await _dispatch_safe(_component_operations(
        client=client,
        action=action,
        report_id=report_id,
        component_idx=component_idx,
        value_field=value_field,
        field_index=field_index,
        config_overrides=config_overrides,
    ))



# =============================================================================
# TOOLS: datasource_operations
# =============================================================================

@mcp.tool(annotations=_rw_ann("Datasource management"), meta=DEFER_META)
async def datasource_operations(
    action: DatasourceAction,
    datasource_id: Annotated[int | None, Field(description=CANONICAL["datasource_id"])] = None,
    table_name: Annotated[str | None, Field(description=CANONICAL["table_name"])] = None,
    schema: Annotated[str, Field(description=CANONICAL["schema"])] = "public",
    limit: Annotated[int, Field(description=CANONICAL["limit"])] = 50,
    offset: Annotated[int, Field(description=CANONICAL["offset"])] = 0,
) -> dict[str, Any]:
    """
    Read-only operations for data sources (database connections).

    Datasources are database connections. ⚠️ create/update/delete are NOT supported via MCP
    by design — destructive/mutating operations on datasources would permanently break every
    dataset and report using the connection, so they must be performed through the web portal
    or the direct HTTP API where an admin can confirm the change.

    Actions:
    - list: List all datasources (read-only)
    - get: Get datasource info by ID (read-only)
    - tables_list: List database tables (datasource_id required; read-only)
    - table_fields: Get table fields (datasource_id, table_name required; schema for PostgreSQL)
    - check_connection: Check connection status (datasource_id required; read-only)

    Example - List datasources:
        datasource_operations(action='list')

    Example - Get datasource info:
        datasource_operations(action="get", datasource_id=1)

    Example - List tables:
        datasource_operations(action="tables_list", datasource_id=1)

    Example - Get table fields:
        datasource_operations(
            action="table_fields",
            datasource_id=1,
            table_name="users",
            schema="public"
        )

    Example - Check connection:
        datasource_operations(action="check_connection", datasource_id=1)

    Returns:
        list: {success, count, items: [{id, name, caption, parent_id}]}
        get: {success, datasource: {id, name, host, database, ...}}
        tables_list: {success, datasource_id, items: [{name, schema}]}
        table_fields: {success, table_name, items: [{name, type, nullable}]}
        check_connection: {success, connected: bool, message}
    """
    manager = get_instance_manager()
    client = await manager.get_client()

    return await _datasource_operations(
        client=client,
        action=action,
        datasource_id=datasource_id,
        table_name=table_name,
        schema=schema,
        limit=limit,
        offset=offset,
    )


# =============================================================================
# TOOLS: Data Query Operations
# =============================================================================

@mcp.tool(annotations=_ro_ann("Dataset SQL-like query (read-only)"), meta=DEFER_META)
async def dataset_query(
    dataset_id: Annotated[int, Field(description=CANONICAL["dataset_id"])],
    select: Annotated[list[SelectField] | None, Field(description=CANONICAL["select"])] = None,
    where: Annotated[list[WhereClause] | None, Field(description=CANONICAL["where"])] = None,
    group: Annotated[list[GroupClause] | None, Field(description=CANONICAL["group"])] = None,
    order: Annotated[list[OrderClause] | None, Field(description=CANONICAL["order"])] = None,
    limit: Annotated[int, Field(description=CANONICAL["limit"])] = 1000,
    variables: Annotated[dict[str, list] | None, Field(description=CANONICAL["variables"])] = None,
) -> dict[str, Any]:
    """
    Query data from a dataset (semantic model).

    This is the primary way to get data from ModusBI.

    Args:
        dataset_id: Dataset ID (NOT datasource_id!)
        select: Fields to select, e.g. [{"name": "amount", "aggr": "sum"}]
        where: Filter conditions, e.g. [{"name": "region", "op": "=", "value": "Moscow"}]
        group: Grouping fields, e.g. [{"name": "region"}]
        order: Ordering, e.g. [{"name": "amount", "dir": "desc"}]
        limit: Max rows (default 1000); 0 = вернуть 0 строк (только метаданные полей), отрицательный — ошибка
        variables: SQL variables for :variable_name substitution.
            Format: {"var_name": ["value1", "value2"]}

    Example - Get all data:
        dataset_query(dataset_id=5)

    Example - Aggregated query:
        dataset_query(
            dataset_id=5,
            select=[{"name": "region"}, {"name": "amount", "aggr": "sum"}],
            group=[{"name": "region"}],
            order=[{"name": "amount", "dir": "desc"}]
        )

    Example - With SQL variables:
        dataset_query(dataset_id=42, variables={"region": ["Moscow"], "year": [2024]})

    Returns:
        {success, dataset_id, fields, rows, rows_count}
    """
    manager = get_instance_manager()
    client = await manager.get_client()

    # Normalise Pydantic models back to plain dicts for the dispatcher.
    select_dicts = [s.model_dump(exclude_none=True, mode="json") for s in select] if select else None
    where_dicts = [w.model_dump(exclude_none=True, mode="json") for w in where] if where else None
    group_dicts = [g.model_dump(exclude_none=True, mode="json") for g in group] if group else None
    order_dicts = [o.model_dump(exclude_none=True, mode="json") for o in order] if order else None

    return await _dataset_query(
        client=client,
        dataset_id=dataset_id,
        select=select_dicts,
        where=where_dicts,
        group=group_dicts,
        order=order_dicts,
        limit=limit,
        variables=variables
    )


@mcp.tool(annotations=_ro_ann("Batch SQL queries (read-only)"), meta=DEFER_META)
async def query_batch(
    dataset_id: Annotated[int, Field(description=CANONICAL["dataset_id"])],
    queries: Annotated[list[BatchQuerySpec], Field(description=CANONICAL["queries"])],
) -> dict[str, Any]:
    """
    Execute multiple queries on a dataset in a single request.

    More efficient than multiple single queries.

    Each query should have:
    - id: Unique identifier (string)
    - params: Query parameters (select, where, group, order, etc.)

    Example:
        queries = [
            {"id": "total", "params": {"select": [{"name": "amount", "aggr": "sum"}]}},
            {"id": "by_region", "params": {"select": [...], "group": [{"name": "region"}]}}
        ]

    Returns results for each query with its id.

    KNOWN PORTAL ISSUE: the portal may answer HTTP 200 with empty data for a
    contract-valid batch. MCP detects this and returns success:false with
    warning "portal returned empty data (known issue)".
    Workaround: call dataset_query once per query — the single-query path works.
    """
    manager = get_instance_manager()
    client = await manager.get_client()

    # Normalise Pydantic models back to plain dicts for the dispatcher.
    queries_dicts = [q.model_dump(exclude_none=True, mode="json") for q in queries]

    return await _query_batch(
        client=client,
        dataset_id=dataset_id,
        queries=queries_dicts
    )


@mcp.tool(annotations=_ro_ann("SQL validation (read-only)"), meta=DEFER_META)
async def sql_query_validate(
    sql_query: Annotated[str, Field(description=CANONICAL["sql_query"])],
    datasource_id: Annotated[int, Field(description=CANONICAL["datasource_id"])] = 1,
) -> dict[str, Any]:
    """
    Validate SQL query and get result fields structure.

    Validates SQL and returns field definitions.

    NOT a sandbox: the portal "validates" SQL by EXECUTING it on the live
    datasource. MCP therefore allows only a SINGLE SELECT (or WITH ... SELECT)
    statement — DML/DDL and multi-statement SQL are rejected on the MCP side
    with success:false ("only single SELECT allowed").

    Use this BEFORE creating a dataset to:
    - Check SQL syntax
    - Get field types and names
    - Preview dataset structure

    Args:
        sql_query: SQL query to validate
        datasource_id: Datasource ID (driver), default 1 = PostgreSQL

    Example:
        sql_query_validate(
            sql_query="SELECT id, name, amount FROM sales",
            datasource_id=1
        )

    Returns:
        {success, valid, fields: [{name, type, alias}], fields_count}
    """
    manager = get_instance_manager()
    client = await manager.get_client()

    return await _sql_query_validate(
        client=client,
        sql_query=sql_query,
        datasource_id=datasource_id
    )


@mcp.tool(annotations=_rw_ann("Create dataset with semantic layer"))
async def dataset_create_from_sql(
    sql_query: Annotated[str, Field(description=CANONICAL["sql_query"])],
    datasource_id: Annotated[int, Field(description=CANONICAL["datasource_id"])],
    name: Annotated[str, Field(description=CANONICAL["name"])],
    caption: Annotated[str | None, Field(description=CANONICAL["caption"])] = None,
) -> dict[str, Any]:
    """
    Create dataset from SQL — VALIDATES SQL, infers field types, builds semantic layer in one call.

    RECOMMENDED over dataset_operations(action="create") (that one skips validation).

    Write SQL with ORIGINAL (latin) column names (AS names). Set human-readable labels via
    dataset_operations(action="update", field_aliases={...}) right after — aliases MUST
    be set BEFORE binding to components (backend blocks edits after binding).

    Tips: include ORDER BY for chart sorting, use ::INTEGER on EXTRACT, ROUND(...) for
    percents. ORDER BY is preserved by the API.

    Args:
        sql_query: SQL (with WHERE/ORDER BY as needed)
        datasource_id: datasource connection ID (NOT driver type — derived automatically)
        name: dataset name (latin)
        caption: human-readable caption

    Returns:
        {success, dataset: {id, name, fields_count}, fields: [...]}
    """
    from .core.security import check_action
    check_action("create")

    manager = get_instance_manager()
    client = await manager.get_client()

    return await _dataset_create_from_sql(
        client=client,
        sql_query=sql_query,
        datasource_id=datasource_id,
        name=name,
        caption=caption
    )


@mcp.tool(annotations=_ro_ann("Datasource preflight check (read-only)"), meta=DEFER_META)
async def preflight_check_datasource(
    datasource_id: Annotated[int, Field(description=CANONICAL["datasource_id"])],
) -> dict[str, Any]:
    """
    Preflight check: verify datasource can actually execute queries.

    This goes beyond check_connection by actually trying a simple SQL query.
    Use this before expensive operations to fail fast with clear diagnostics.

    The check performs two steps:
    1. Basic connection check (same as check_connection)
    2. Simple SQL query execution (SELECT 1)

    Args:
        datasource_id: Datasource ID to check

    Example:
        preflight_check_datasource(datasource_id=1)

    Returns:
        {
            success: bool,
            datasource_id: int,
            connected: bool,      # Basic connection works
            can_query: bool,      # SQL execution works
            message?: str,        # Success message
            error?: str,          # Error description
            hint?: str            # Troubleshooting hint
        }

    Use cases:
    - Before running dataset_query on a new dataset
    - Diagnosing why queries fail with HTTP 500
    - Validating datasource configuration
    """
    manager = get_instance_manager()
    client = await manager.get_client()

    return await _preflight_check_datasource(
        client=client,
        datasource_id=datasource_id
    )


# =============================================================================
# TOOLS: style_operations
# =============================================================================

@mcp.tool(annotations=_rw_ann("Report-level CSS (overwrites)"))
async def style_operations(
    action: StyleAction,
    report_id: Annotated[int | None, Field(description=CANONICAL["report_id"])] = None,
    css: Annotated[str | None, Field(description=CANONICAL["css"])] = None,
    category: Annotated[str, Field(description=CANONICAL["category"])] = "all",
    # apply_theme — brand-pack CSS из 5-цветной темы
    theme: Annotated[dict | None, Field(description="Theme colors {primary, secondary, bg, accent, text}. Used by action='apply_theme'.")] = None,
    mode: Annotated[str, Field(description="For apply_theme: 'merge' (append to existing CSS, default) or 'replace' (overwrite all)." )] = "merge",
    # kpi_icons — CSS background-image для KPI (нативного icon-slot нет)
    kpi_icons: Annotated[dict | None, Field(description="For apply_theme: {component_idx: url} or {component_idx: {url, size, position}}. Adds CSS background-image to KPI components.")] = None,
) -> dict[str, Any]:
    """
    CSS styling operations for reports.

    ## ⚠️ IMPORTANT: CSS Update Workflow (destructive overwrite)
    **ALWAYS study available classes, examples, and current CSS before updating!**
    ⚠️ action="update" is DESTRUCTIVE — it permanently REPLACES all CSS. Previous styles
    are overwritten and cannot be undone without a prior backup. You must:
    1. GET available CSS classes with action="classes_list" (know what's possible)
    2. GET styling examples with action="examples_list" (see recommended patterns)
    3. GET current CSS with action="get" (see what's already applied) — THIS IS YOUR BACKUP
    4. Analyze and merge your new styles with existing ones
    5. Then UPDATE with the complete merged CSS

    Actions:
    - classes_list: List available ModusBI CSS classes - STUDY THESE FIRST! (read-only)
    - examples_list: Get CSS styling examples - LEARN PATTERNS! (read-only)
    - get: Get current report CSS (report_id required) - READ BEFORE UPDATE! (read-only)
    - update: ⚠️ DESTRUCTIVE — permanently overwrites and replaces ALL report CSS with the
              supplied string. Previous styles are deleted and cannot be undone. Always GET
              the current CSS first and merge before calling update.
    - validate: Validate CSS syntax (css required; read-only)

    Categories for classes_list/examples_list:
    header, tables, charts, maps, filters, grid, components, all

    Example - Correct workflow:
        # Step 1: Learn available CSS classes for the category you need
        style_operations(action="classes_list", category="charts")
        # Returns: {classes: [{name: ".amcharts-graph", description: "Chart lines"}]}

        # Step 2: Get styling examples to understand patterns
        style_operations(action="examples_list", category="charts")
        # Returns: {examples: [{name: "Dark theme", css: "...", description: "..."}]}

        # Step 3: Get current CSS to see what's already applied
        current = style_operations(action="get", report_id=35)
        # Returns: {success: true, css: ".existing { color: red; }"}

        # Step 4: Merge existing + new styles and update
        style_operations(
            action="update",
            report_id=35,
            css=".existing { color: red; } .amcharts-graph { stroke: #1976d2; }"
        )

    Returns:
        get: {success, report_id, css: str}
        update: {success, message}
        validate: {success, valid: bool, errors: [...]}
        classes_list: {success, category, classes: [{name, description}]}
        examples_list: {success, category, examples: [{name, css, description}]}

    ⚠️ Destructive actions: update (permanently overwrites all CSS; previous styles are
    irreversibly deleted, cannot be undone).
    Requires readwrite mode: update.
    """
    manager = get_instance_manager()
    client = await manager.get_client()

    return await _dispatch_safe(_style_operations(
        client=client,
        action=action,
        report_id=report_id,
        css=css,
        category=category,
        theme=theme,
        mode=mode,
        kpi_icons=kpi_icons,
    ))


# =============================================================================
# TOOLS: reportgroup_operations
# =============================================================================

@mcp.tool(annotations=_rw_ann("Report group (folder) CRUD"), meta=DEFER_META)
async def reportgroup_operations(
    action: ReportGroupAction,
    group_id: Annotated[int | None, Field(description=CANONICAL["group_id"])] = None,
    name: Annotated[str | None, Field(description=CANONICAL["name"])] = None,
    caption: Annotated[str | None, Field(description=CANONICAL["caption"])] = None,
    parent_id: Annotated[int | None, Field(description=CANONICAL["parent_id"])] = None,
    menu: Annotated[bool | None, Field(description=CANONICAL["menu"])] = None,
    is_extended: Annotated[bool | None, Field(description=CANONICAL["is_extended"])] = None,
    group_options: Annotated[ReportGroupOptions | None, Field(description=CANONICAL["options"])] = None,
    image: Annotated[str | None, Field(description=CANONICAL["image"])] = None,
    previous_group_id: Annotated[int | None, Field(description=CANONICAL["previous_group_id"])] = None,
    limit: Annotated[int, Field(description=CANONICAL["limit"])] = 50,
    offset: Annotated[int, Field(description=CANONICAL["offset"])] = 0,
) -> dict[str, Any]:
    """
    CRUD operations for report groups (folders for organizing reports).

    Organize reports into hierarchical groups.

    Actions:
    - list: List all report groups (read-only)
    - get: Get group by ID (group_id required; read-only)
    - create: Create group (name required; caption, parent_id, menu, options optional)
    - update: Update group (group_id required; name, caption, parent_id, menu optional) —
              overwrites specified fields
    - delete: ⚠️ DESTRUCTIVE — permanently deletes the report group. This action is
              irreversible and cannot be undone. WARNING: nested groups and reports that
              reference the deleted group via parent_id will be orphaned and may become
              inaccessible through the portal's folder tree.
    - move: Move group to new parent (group_id, parent_id required; previous_group_id optional)

    Example - List all groups:
        reportgroup_operations(action='list')

    Example - Get group info:
        reportgroup_operations(action="get", group_id=20)

    Example - Create group:
        reportgroup_operations(
            action="create",
            name="Sales Reports",
            caption="Sales Department Dashboards",
            parent_id=1,
            menu=True
        )

    Example - Move group:
        reportgroup_operations(
            action="move",
            group_id=25,
            parent_id=20
        )

    Returns:
        list: {success, count, groups: [{id, name, caption, parent_id, menu}]}
        get: {success, group: {id, name, caption, parent_id, menu, reports_count}}
        create: {success, group_id, message}
        update: {success, message}
        delete: {success, message}
        move: {success, message}

    ⚠️ Destructive actions: delete (permanently removes group, cannot be undone;
    orphans nested groups/reports that reference it via parent_id).
    Requires readwrite mode: create, update, delete, move.
    """
    manager = get_instance_manager()
    client = await manager.get_client()

    # Normalise Pydantic model back to plain dict for the dispatcher.
    options_dict = group_options.model_dump(exclude_none=True, mode="json") if group_options else None

    return await _dispatch_safe(_reportgroup_operations(
        client=client,
        action=action,
        group_id=group_id,
        name=name,
        caption=caption,
        parent_id=parent_id,
        menu=menu,
        is_extended=is_extended,
        options=options_dict,
        image=image,
        previous_group_id=previous_group_id,
        limit=limit,
        offset=offset,
    ))


@mcp.tool(annotations=_ro_ann("Data export to files (read-only)"), meta=DEFER_META)
async def data_export_operations(
    action: DataExportAction,
    report_id: Annotated[int | None, Field(description=CANONICAL["report_id"])] = None,
    component_idx: Annotated[int | None, Field(description=CANONICAL["component_idx"])] = None,
    output_dir: Annotated[str | None, Field(description=CANONICAL["output_dir"])] = None,
    filename: Annotated[str | None, Field(description=CANONICAL["filename"])] = None,
    limit: Annotated[int, Field(description=CANONICAL["limit"])] = 10000,
    format: Annotated[str, Field(description=CANONICAL["format"])] = "csv",
    include_subtotals: Annotated[bool, Field(description=CANONICAL["include_subtotals"])] = False,
    include_totals: Annotated[bool, Field(description=CANONICAL["include_totals"])] = False,
) -> dict[str, Any]:
    """
    Data export operations for components (CSV/Excel).

    Export component data to files.

    Actions:
    - component_csv: Export component data to CSV (local, no dependencies)
    - component_xlsx: Export component data to Excel (via API reportToXlsx)
    - info: Get export directory configuration

    Export location priority:
    1. output_dir parameter
    2. MODUSBI_EXPORT_DIR env var
    3. ~/Downloads/modusbi_exports

    Example - Export to CSV:
        data_export_operations(
            action="component_csv",
            report_id=35,
            component_idx=0,
            filename="sales_data"
        )

    Example - Export to Excel:
        data_export_operations(
            action="component_xlsx",
            report_id=35,
            component_idx=0,
            include_totals=True
        )

    Example - Get export directory info:
        data_export_operations(action="info")

    Returns:
        component_csv: {success, file_path, rows_count, format: "csv"}
        component_xlsx: {success, file_path, rows_count, format: "xlsx"}
        info: {success, export_dir, env_var, exists: bool}
    """
    manager = get_instance_manager()
    client = await manager.get_client()

    return await _dispatch_safe(_export_data_operations(
        client=client,
        action=action,
        report_id=report_id,
        component_idx=component_idx,
        output_dir=output_dir,
        filename=filename,
        limit=limit,
        format=format,
        include_subtotals=include_subtotals,
        include_totals=include_totals
    ))


@mcp.tool(annotations=_rw_ann("Batch operations for multiple objects"), meta=DEFER_META)
async def batch_operations(
    action: BatchAction,
    report_id: Annotated[int | None, Field(description=CANONICAL["report_id"])] = None,
    report_ids: Annotated[list[int] | None, Field(description=CANONICAL["report_ids"])] = None,
    components: Annotated[list[ComponentSpec] | None, Field(description=CANONICAL["components"])] = None,
    layouts: Annotated[list[LayoutSpec] | None, Field(description=CANONICAL["layouts"])] = None,
    indices: Annotated[list[int] | None, Field(description=CANONICAL["indices"])] = None,
    css: Annotated[str | None, Field(description=CANONICAL["css"])] = None,
    format: ExportFormatLiteral = "pdf",
    output_dir: Annotated[str | None, Field(description=CANONICAL["output_dir"])] = None,
) -> dict[str, Any]:
    """
    Batch operations for multiple objects at once.

    Actions:
    - components_add: Add multiple components (report_id, components list)
    - components_delete: ⚠️ DESTRUCTIVE — permanently deletes multiple components at once
              (report_id, indices list). This action is irreversible and cannot be undone.
              Each deletion cascades to layouts/filters of the removed component. Double-check
              the indices list before calling — a wrong index permanently removes the wrong
              component.
    - layouts_update: Update multiple layouts (report_id, layouts list) — overwrites each
              target layout's fields
    - styles_apply: ⚠️ Applies CSS to multiple reports at once (report_ids, css). Each target
              report's CSS is permanently overwritten — previous styles are deleted and
              cannot be undone per-report without a prior backup.
    - reports_export: Export multiple reports (report_ids, format) — read-only on portal state

    Example - Add multiple components:
        batch_operations(
            action="components_add",
            report_id=35,
            components=[
                {"type": "HsBarAMchartsChart", "title": "Sales", ...},
                {"type": "HsPieAMchartsChart", "title": "Distribution", ...}
            ]
        )

    Example - Export multiple reports to PDF:
        batch_operations(
            action="reports_export",
            report_ids=[35, 36, 37],
            format="pdf"
        )

    Returns:
        components_add: {success, added: int, results: [...]}
        components_delete: {success, deleted: int}
        layouts_update: {success, updated: int}
        styles_apply: {success, applied: int, report_ids: [...]}
        reports_export: {success, exported: int, files: [...]}

    ⚠️ Destructive actions: components_delete (permanently removes components in bulk,
    cannot be undone), styles_apply (overwrites CSS of every target report, previous
    styles irreversibly deleted).
    Requires readwrite mode: components_add, components_delete, layouts_update,
    styles_apply.
    """
    manager = get_instance_manager()
    client = await manager.get_client()

    # Normalise Pydantic models back to plain dicts for the dispatcher.
    components_dicts = (
        [c.model_dump(exclude_none=True, mode="json") for c in components]
        if components else None
    )
    layouts_dicts = (
        [l.model_dump(exclude_none=True, mode="json") for l in layouts]
        if layouts else None
    )

    return await _dispatch_safe(_batch_operations(
        client=client,
        action=action,
        report_id=report_id,
        report_ids=report_ids,
        components=components_dicts,
        layouts=layouts_dicts,
        indices=indices,
        css=css,
        format=format,
        output_dir=output_dir
    ))


# =============================================================================
# TOOLS: report_template (scaffold reports from predefined layouts)
# =============================================================================

@mcp.tool(annotations=_rw_ann("Scaffold reports from predefined templates"))
async def report_template(
    action: ReportTemplateAction,
    template: Annotated[str | None, Field(description=CANONICAL["template"])] = None,
    report_id: Annotated[int | None, Field(description=CANONICAL["report_id"])] = None,
    dataset_id: Annotated[int | None, Field(description=CANONICAL["dataset_id"])] = None,
    name: Annotated[str | None, Field(description=CANONICAL["name"])] = None,
    group_id: Annotated[int | None, Field(description=CANONICAL["group_id"])] = None,
    category_field: Annotated[str | None, Field(description="Dataset field bound as category/dimension in scaffolded slots (filter panels, chart X-axis, table first column).")] = None,
    value_field: Annotated[str | None, Field(description="Comma-separated metric fields to bind at scaffold: KPI slots cycle through them, charts use the first, tables get category+all metrics. Without it scaffold creates a skeleton with placeholder 'value'.")] = None,
) -> dict[str, Any]:
    """
    Report template operations: list available templates, preview layouts, scaffold reports.

    Actions:
    - list: List all available templates with descriptions and ASCII previews (read-only)
    - preview: Detailed ASCII layout + component breakdown for a template (read-only)
    - scaffold: Create report and populate with template components (1 GET + 1 PUT).
              ⚠️ When report_id is provided, scaffold APPENDS components to that report.
              When report_id is omitted, a new report is created. Components added by
              scaffold persist and must be removed via component_crud(action="delete")
              if unwanted — there is no automatic "undo scaffold" action.

    Templates: kpi_dashboard, ranking, comparison, factor_analysis, geo_analytics, simple

    Example - List templates:
        report_template(action='list')

    Example - Preview a template:
        report_template(action="preview", template="kpi_dashboard")

    Example - Scaffold new report from template (with field binding):
        report_template(action="scaffold", template="kpi_dashboard", dataset_id=10,
                       name="Sales Dashboard", group_id=20,
                       category_field="region", value_field="amount,qty,profit")
        # KPI слоты получат amount/qty/profit по кругу, график region+amount,
        # таблица region+все метрики. Без category/value_field — каркас с
        # placeholder 'value' (привязка вручную через component_crud update).

    Example - Add template to existing report:
        report_template(action="scaffold", template="simple", report_id=35, dataset_id=10)

    Returns:
        list: {success, count, templates: [{name, description, component_count, component_types, ascii_preview}]}
        preview: {success, template, ascii_layout, components: [{idx, type, title, x, y, w, h, needs_data}]}
        scaffold: {success, report_id, report_created, template, components, added, next_steps}

    ⚠️ Destructive actions: none outright, but scaffold creates/mutates portal state that
    must be manually rolled back (component_crud delete / report_operations delete) — it
    cannot be undone automatically.
    Requires readwrite mode: scaffold.
    """
    manager = get_instance_manager()
    client = await manager.get_client()

    return await _dispatch_safe(_report_template(
        client=client,
        action=action,
        template=template,
        report_id=report_id,
        dataset_id=dataset_id,
        name=name,
        group_id=group_id,
        category_field=category_field or None,
        value_field=value_field or None,
    ))


# =============================================================================
# TOOLS: security_operations
# =============================================================================

@mcp.tool(annotations=_rw_ann("Row Level Security (RLS) CRUD"), meta=DEFER_META)
async def security_operations(
    action: SecurityAction,
    dataset_id: Annotated[int | None, Field(description=CANONICAL["dataset_id"])] = None,
    enabled: Annotated[bool | None, Field(description=CANONICAL["enabled"])] = None,
    rls_query: Annotated[str | None, Field(description=CANONICAL["rls_query"])] = None,
) -> dict[str, Any]:
    """
    Manage Row Level Security (RLS) for datasets.

    RLS in ModusBI filters data per-user using query_rls with :current_user_id placeholder.

    Actions:
    - status: Get RLS status for dataset (dataset_id required; read-only)
    - enable: Enable RLS for dataset (dataset_id required)
    - disable: ⚠️ DESTRUCTIVE — permanently disables RLS for the dataset. WARNING: this
              immediately exposes all rows to every user who has access to the dataset,
              removing the per-user data filter. Cannot be undone without re-enabling
              and re-entering the filter query (previous query string is preserved, but
              security posture change is effective immediately).
    - update_filter: ⚠️ DESTRUCTIVE — overwrites and permanently replaces the RLS filter
              query. Previous rls_query is deleted and cannot be recovered unless you
              backed it up via action="status" first. An incorrect filter may leak data
              to users who should not see it, or block legitimate users entirely.
    - list_enabled: List all datasets with RLS enabled (read-only)
    - test: Test RLS filter with sample data (dataset_id required; read-only)

    Example - Check RLS status:
        security_operations(action="status", dataset_id=5)

    Example - Enable RLS with filter:
        security_operations(
            action="update_filter",
            dataset_id=5,
            rls_query="user_id = :current_user_id"
        )

    Example - List all RLS-enabled datasets:
        security_operations(action="list_enabled")

    Returns:
        status: {success, dataset_id, rls_enabled: bool, rls_query: str}
        enable: {success, message, rls_enabled: true}
        disable: {success, message, rls_enabled: false}
        update_filter: {success, message, rls_query}
        list_enabled: {success, datasets_with_rls: [...], count}
        test: {success, test_result: "passed"|"failed", rows_returned}

    ⚠️ Destructive actions: disable (permanently removes the per-user data filter until
    re-enabled), update_filter (overwrites rls_query; previous filter is irreversibly
    deleted). Both have immediate security impact and cannot be undone without a backup
    taken via action="status".
    Requires readwrite mode: enable, disable, update_filter.
    """
    manager = get_instance_manager()
    client = await manager.get_client()

    return await _dispatch_safe(_security_operations(
        client=client,
        action=action,
        dataset_id=dataset_id,
        enabled=enabled,
        rls_query=rls_query
    ))


# =============================================================================
# PROMPTS (6 user-driven templates)
# =============================================================================

@mcp.prompt()
async def create_dashboard(
    dataset_name: str | None = None,
    report_name: str | None = None
) -> list[dict]:
    """
    Пошаговое создание дашборда с выбором датасета и компонентов.

    Workflow:
    1. Показать список датасетов
    2. Выбрать датасет и показать его поля
    3. Создать отчёт в нужной группе
    4. Добавить компоненты (диаграммы, таблицы)
    5. Настроить layout и стили
    """
    return get_prompt_messages("create_dashboard", {
        "dataset_name": dataset_name,
        "report_name": report_name
    })


@mcp.prompt()
async def style_report(
    report_id: int,
    style_type: str | None = None
) -> list[dict]:
    """
    Стилизация отчёта с помощью CSS.

    Показывает текущие стили, доступные классы и примеры.
    После одобрения применяет новые стили.
    """
    return get_prompt_messages("style_report", {
        "report_id": report_id,
        "style_type": style_type
    })


@mcp.prompt()
async def query_data(
    dataset_id: int,
    question: str | None = None
) -> list[dict]:
    """
    Построение запроса к датасету с фильтрами и агрегацией.

    Анализирует поля датасета и помогает построить
    оптимальный запрос для получения нужных данных.
    """
    return get_prompt_messages("query_data", {
        "dataset_id": dataset_id,
        "question": question
    })


@mcp.prompt()
async def export_report(
    report_id: int,
    format: str | None = None
) -> list[dict]:
    """
    Экспорт отчёта в PDF, PNG или PPTX.

    Проверяет отчёт и выполняет экспорт в указанном формате.
    """
    return get_prompt_messages("export_report", {
        "report_id": report_id,
        "format": format
    })


@mcp.prompt()
async def analyze_dataset(
    dataset_id: int
) -> list[dict]:
    """
    Анализ структуры датасета: поля, типы, связи.

    Получает метаданные, анализирует типы полей и
    предлагает варианты визуализации.
    """
    return get_prompt_messages("analyze_dataset", {
        "dataset_id": dataset_id
    })


@mcp.prompt()
async def customize_component(
    report_id: int,
    component_idx: int,
    preset: PresetLiteral | None = None
) -> list[dict]:
    """
    Визуальная настройка компонента: slug-параметры (config_schema.SLUG_SCHEMA), 6 presets, config_overrides.

    3 уровня настройки:
    - Level 1: Атомарные параметры (legend_visible, bg_color)
    - Level 2: Config overrides через slugs (config_overrides={"slug.key": value})
    - Level 3: Presets (minimal, presentation, dashboard, dark, print, kpi)
    """
    return get_prompt_messages("customize_component", {
        "report_id": report_id,
        "component_idx": component_idx,
        "preset": preset
    })


@mcp.prompt()
async def add_filters(
    report_id: int,
    component_idx: int | None = None
) -> list[dict]:
    """
    Добавление интерактивных фильтров, каскадных зависимостей и globalCategories.

    Создаёт FilterControlPanel, добавляет поля фильтрации,
    настраивает каскады (filterBy) и категории отчёта.
    """
    return get_prompt_messages("add_filters", {
        "report_id": report_id,
        "component_idx": component_idx
    })


@mcp.prompt()
async def add_conditional_formatting(
    report_id: int,
    component_idx: int
) -> list[dict]:
    """
    Условное форматирование для таблиц и сводных таблиц (цвет, индикаторы, правила).

    Настраивает config.rules[] через config_overrides с RULE_PROPS:
    цвет фона/текста, индикаторы (up/down/dot), условия (>=, <=, >, <, =).
    """
    return get_prompt_messages("add_conditional_formatting", {
        "report_id": report_id,
        "component_idx": component_idx
    })


@mcp.prompt()
async def manage_variables(
    report_id: int
) -> list[dict]:
    """
    Управление переменными отчёта (globalVariables) и категориями (globalCategories).

    Переменные параметризуют запросы (dataset_query variables={...}).
    Категории привязаны к globalFilters и FilterControlPanel.
    """
    return get_prompt_messages("manage_variables", {
        "report_id": report_id
    })


@mcp.prompt()
async def create_report_from_template(
    template: str,
    dataset_id: int,
    report_name: str | None = None,
    group_id: Annotated[int | None, Field(description="Numeric ID of the report group (folder).")] = None,
) -> list[dict]:
    """
    Создать отчёт по шаблону: kpi_dashboard, ranking, comparison, simple, geo_analytics, factor_analysis.

    Шаблон определяет набор компонентов, layout и preset-стилизацию.
    Все компоненты добавляются одним batch-вызовом.
    """
    return get_prompt_messages("create_report_from_template", {
        "template": template,
        "dataset_id": dataset_id,
        "report_name": report_name,
        "group_id": group_id,
    })


# =============================================================================
# POST-REGISTRATION SCHEMA SLIM
# =============================================================================
# Strip `anyOf:[T, null]` wrappers from Pydantic-generated schemas so the
# tools/list envelope is smaller for every LLM client. Runtime Pydantic
# validation is untouched — this only rewrites JSON we ship over the wire.
from .tools.schema_slim import apply_slim_to_mcp as _apply_slim_to_mcp

_apply_slim_to_mcp(mcp)


# =============================================================================
# MAIN
# =============================================================================

def main():
    """Точка входа для запуска сервера."""
    parser = argparse.ArgumentParser(description="ModusBI MCP Server")
    parser.add_argument("--readonly", action="store_true", help="Read-only mode (default)")
    parser.add_argument("--readwrite", action="store_true",
                        help="Enable write operations (create/update/delete). USE WITH CAUTION.")
    parser.add_argument("--demo", action="store_true", help="Demo mode (readonly + limits)")
    parser.add_argument(
        "--security-ceiling",
        choices=["readonly", "readwrite", "demo"],
        default=os.environ.get("MODUSBI_SECURITY_CEILING", "readwrite"),
        help="Maximum allowed security mode — strictest of (CLI mode, ceiling) wins. "
             "Default: readwrite (no ceiling). Use 'readonly' to hard-block writes "
             "even if --readwrite is passed."
    )
    parser.add_argument("--transport", choices=["stdio", "http"], default="stdio",
                        help="Transport type (default: stdio)")
    parser.add_argument("--log-level", default="INFO",
                        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
                        help="Logging verbosity (to stderr)")
    parser.add_argument(
        "--log-format",
        choices=["text", "json"],
        default=os.environ.get("MODUSBI_LOG_FORMAT", "text"),
        help="Log line format. 'text' (default) — human-readable; 'json' — one JSON "
             "per line for production parsing (ELK/Loki/Datadog). Both go to stderr.",
    )

    args = parser.parse_args()

    # Все логи идут в stderr — stdout оставляем чистым под JSON-RPC.
    if args.log_format == "json":
        # JSON formatter for production log aggregation
        import json as _json

        class _JsonFormatter(logging.Formatter):
            def format(self, record):
                payload = {
                    "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
                    "level": record.levelname,
                    "logger": record.name,
                    "msg": record.getMessage(),
                }
                if record.exc_info:
                    payload["exc"] = self.formatException(record.exc_info)
                # Audit log markers like "audit:report_create" — extract for downstream filtering
                if isinstance(record.msg, str) and record.msg.startswith("audit:"):
                    payload["audit"] = True
                return _json.dumps(payload, ensure_ascii=False)

        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(_JsonFormatter())
        root = logging.getLogger()
        root.handlers = [handler]
        root.setLevel(getattr(logging, args.log_level))
    else:
        logging.basicConfig(
            stream=sys.stderr,
            level=getattr(logging, args.log_level),
            format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        )

    # Устанавливаем режим безопасности из CLI.
    if args.readwrite:
        chosen_mode = "readwrite"
    elif args.demo:
        chosen_mode = "demo"
    else:
        # Default since 1.0.0 — безопаснее для автономных клиентов.
        chosen_mode = "readonly"

    # Apply ceiling — strictest of (CLI mode, ceiling) wins.
    # See app/core/security.py:MODE_STRICTNESS for the ranking.
    from app.core.security import resolve_effective_mode
    ceiling = args.security_ceiling
    final_mode = resolve_effective_mode(chosen_mode, ceiling)
    if final_mode != chosen_mode:
        logger.warning(
            "Security ceiling '%s' overrides CLI mode '%s' → '%s'",
            ceiling, chosen_mode, final_mode,
        )

    set_security_mode(SecurityMode(final_mode))

    if final_mode == "readwrite":
        logger.warning("Server started in READWRITE mode — destructive actions enabled.")
    elif final_mode == "demo":
        logger.info("Server started in DEMO mode (readonly + rate limits).")
    else:
        logger.info("Server started in READONLY mode (use --readwrite to enable writes).")

    mcp.run(transport=args.transport)


if __name__ == "__main__":
    main()
