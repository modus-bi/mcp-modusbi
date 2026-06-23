"""
Режимы безопасности MCP сервера ModusBI.

SecurityMode определяет какие операции разрешены:
- READONLY: только чтение (list, get, summary, export)
- READWRITE: чтение и запись (create, update, delete, add)
- DEMO: демо-режим с ограничениями (readonly + лимиты)
"""

from enum import Enum
from functools import wraps
from typing import Callable, Any

from .exceptions import SecurityError


class SecurityMode(Enum):
    """Режимы безопасности сервера."""

    READONLY = "readonly"
    READWRITE = "readwrite"
    DEMO = "demo"


# Действия разрешённые в режиме READONLY
READONLY_ACTIONS = frozenset({
    # Общие
    "list",
    "get",
    "summary",

    # Reports
    "groups_list",
    "components_list",

    # Datasets
    "fields_list",

    # Datasources
    "tables_list",
    "table_fields",
    "check_connection",

    # Styles
    "classes_list",
    "examples_list",
    "validate",

    # Export / выгрузка существующих данных в файлы — портал не мутируется.
    # Эти действия не вызывают check_action (идут в любом режиме); перечислены
    # здесь для информативного вывода get_mode_info().
    "export",          # report_operations — рендер отчёта в файл
    "export_info",     # report_operations — метаданные экспорта
    "component_csv",   # data_export_operations — выгрузка данных компонента
    "component_xlsx",  # data_export_operations
    "info",            # data_export_operations
    # Пакетная выгрузка отчётов — единственное export-действие, которое реально
    # гейтится (batch_operations вызывает check_action("reports_export")).
    "reports_export",

    # Components
    "types_list",
    "data",

    # Instances
    "get_active",
})

# Действия требующие режим READWRITE
READWRITE_ACTIONS = frozenset({
    # CRUD
    "create",
    "update",
    "delete",
    "add",
    "remove",
    "move",

    # Components
    "layout_update",
    "swap",

    # Styles
    "apply",

    # Batch
    "components_add",
    "components_delete",
    "layouts_update",
    "styles_apply",

    # Import
})

# Ограничения для DEMO режима
DEMO_LIMITS = {
    "max_reports": 10,
    "max_components": 5,
    "max_export_per_hour": 3,
    "max_query_rows": 100,
}


# Strictness ranking — readonly (2) > demo (1) > readwrite (0).
# Used to resolve effective mode = max(CLI flag, --security-ceiling).
MODE_STRICTNESS: dict[str, int] = {"readonly": 2, "demo": 1, "readwrite": 0}


def resolve_effective_mode(cli_mode: str, ceiling: str) -> str:
    """Return strictest of (cli_mode, ceiling) using MODE_STRICTNESS."""
    return cli_mode if MODE_STRICTNESS[cli_mode] >= MODE_STRICTNESS[ceiling] else ceiling


def is_action_allowed(action: str, mode: SecurityMode) -> bool:
    """
    Проверяет разрешено ли действие в указанном режиме.

    Args:
        action: Название действия
        mode: Текущий режим безопасности

    Returns:
        True если действие разрешено
    """
    if mode == SecurityMode.READWRITE:
        return True

    if mode == SecurityMode.READONLY:
        return action in READONLY_ACTIONS

    if mode == SecurityMode.DEMO:
        # DEMO = READONLY + некоторые ограничения
        return action in READONLY_ACTIONS

    return False


def get_required_mode(action: str) -> SecurityMode:
    """
    Определяет минимально необходимый режим для действия.

    Args:
        action: Название действия

    Returns:
        Минимально необходимый SecurityMode
    """
    if action in READWRITE_ACTIONS:
        return SecurityMode.READWRITE
    return SecurityMode.READONLY


# Глобальная переменная для хранения текущего режима
_current_mode: SecurityMode = SecurityMode.READWRITE


def set_security_mode(mode: SecurityMode | str) -> None:
    """
    Устанавливает текущий режим безопасности.

    Args:
        mode: SecurityMode или строка ("readonly", "readwrite", "demo")
    """
    global _current_mode
    if isinstance(mode, str):
        mode = SecurityMode(mode)
    _current_mode = mode


def get_security_mode() -> SecurityMode:
    """Возвращает текущий режим безопасности."""
    return _current_mode


def requires_mode(*allowed_modes: SecurityMode):
    """
    Декоратор для проверки режима безопасности.

    Проверяет что текущий режим входит в список разрешённых.
    Если нет — выбрасывает SecurityError.

    Args:
        *allowed_modes: Разрешённые режимы

    Example:
        @requires_mode(SecurityMode.READWRITE)
        async def create_report(...):
            ...

        @requires_mode(SecurityMode.READONLY, SecurityMode.READWRITE)
        async def get_report(...):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            current = get_security_mode()
            if current not in allowed_modes:
                required = ", ".join(m.value for m in allowed_modes)
                raise SecurityError(
                    f"Операция требует режим: {required}",
                    action=func.__name__,
                    current_mode=current.value,
                    required_mode=required
                )
            return await func(*args, **kwargs)
        return wrapper
    return decorator


def check_action(action: str) -> None:
    """
    Проверяет разрешено ли действие в текущем режиме.

    Выбрасывает SecurityError если действие запрещено.

    Args:
        action: Название действия

    Raises:
        SecurityError: Если действие запрещено
    """
    current = get_security_mode()
    if not is_action_allowed(action, current):
        required = get_required_mode(action)
        raise SecurityError(
            f"Действие '{action}' требует режим: {required.value}",
            action=action,
            current_mode=current.value,
            required_mode=required.value
        )


def get_demo_limit(limit_name: str) -> int:
    """
    Возвращает лимит для DEMO режима.

    Args:
        limit_name: Название лимита

    Returns:
        Значение лимита или 0 если не найден
    """
    return DEMO_LIMITS.get(limit_name, 0)


def get_mode_info(mode: SecurityMode | None = None) -> dict:
    """
    Возвращает информацию о режиме.

    Args:
        mode: Режим (по умолчанию текущий)

    Returns:
        dict с информацией о режиме
    """
    if mode is None:
        mode = get_security_mode()

    return {
        "mode": mode.value,
        "readonly_actions": sorted(READONLY_ACTIONS),
        "readwrite_actions": sorted(READWRITE_ACTIONS),
        "demo_limits": DEMO_LIMITS if mode == SecurityMode.DEMO else None,
        "is_readonly": mode == SecurityMode.READONLY,
        "is_demo": mode == SecurityMode.DEMO,
    }
