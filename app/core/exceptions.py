"""
Кастомные исключения MCP сервера ModusBI.

Иерархия исключений:
- ModusBIError (базовое)
  - AuthenticationError (401, проблемы с токеном)
  - APIError (общие ошибки API)
  - NotFoundError (404, объект не найден)
  - ValidationError (400, невалидные данные)
  - SecurityError (403, недостаточно прав / неверный режим)
  - InstanceError (ошибки работы с инстансами)
"""

import re


# Паттерны для маскирования внутренней информации портала из error messages
# до того как они попадут в LLM-context. Помогает при prompt-injection-сценариях:
# LLM не должен видеть имена внутренних таблиц/схем/Go-traces.
_SENSITIVE_PATTERNS = [
    # Go runtime: goroutine N [...] / file.go:NNN
    (re.compile(r"goroutine\s+\d+\s+\[[^\]]*\]", re.I), "goroutine ***"),
    (re.compile(r"/[\w/.\-]+\.go:\d+(?:\s+\+0x[\da-fA-F]+)?"), "***.go:NNN"),
    # SQL: schema "..." / table "..." / constraint "..."
    (re.compile(r"\b(schema|relation|constraint|index|sequence)\s+[\"']?(\w+)[\"']?", re.I),
     r"\1 ***"),
    # PG verbose error prefix
    (re.compile(r"pq:\s+", re.I), ""),
]


def mask_sensitive(text: str | None) -> str | None:
    """Strip portal-internal markers (table names, Go traces) from error text.

    Preserves non-sensitive content (HTTP status, generic messages,
    type hints). If `text` is None, returns None.

    Used in error_response(details=...) to make sure portal-internal
    details don't leak into LLM context window.
    """
    if text is None:
        return None
    for pattern, replacement in _SENSITIVE_PATTERNS:
        text = pattern.sub(replacement, text)
    return text


def error_response(
    message: str,
    hint: str | None = None,
    details: str | dict | None = None,
    **extra
) -> dict:
    """
    Standardized error response for MCP tools.

    Args:
        message: Short human-readable error message
        hint: Actionable guidance for the LLM on how to recover
        details: Technical details (traceback str or structured dict)
        **extra: Additional fields merged into response (e.g. report_id, index)

    Returns:
        {success: False, error: message, hint?: str, details?: any, **extra}
    """
    result: dict = {"success": False, "error": message}
    if hint:
        result["hint"] = hint
    if details is not None:
        result["details"] = details
    result.update(extra)
    return result


def missing_params(
    required: list[str],
    tool: str,
    action: str | None = None,
    example: str | None = None,
    types: dict[str, str] | None = None,
) -> dict:
    """
    Standardized response for missing required parameters.

    Args:
        required: List of missing parameter names (only ones actually missing)
        tool: Name of the tool being called (for help hint)
        action: Action being performed (optional)
        example: Concrete example call (optional)
        types: Optional map {param_name: type_hint} for the missing params

    Returns:
        {success: False, error, missing: [...], expected_types?: {...},
         hint: "...", example?: "..."}
    """
    help_call = f"{tool}(action='help'" + (f", value_field='{action}'" if action else "") + ")"
    result: dict = {
        "success": False,
        "error": "Missing required parameters",
        "missing": list(required),
        "hint": f"Provide all required params. See {help_call} for parameter details.",
    }
    if types:
        result["expected_types"] = {k: types[k] for k in required if k in types}
    if example:
        result["example"] = example
    return result


def require(
    provided: dict,
    tool: str,
    action: str | None = None,
    example: str | None = None,
    types: dict[str, str] | None = None,
) -> dict | None:
    """
    Validate required parameters and report ALL missing at once.

    Unlike early-return `if not all([...])` pattern, this helper inspects each
    param individually and returns the complete list of missing ones, so the
    LLM fixes them all in one retry instead of discovering them one by one.

    A value is considered missing when it is None, "" (empty string),
    [] (empty list), or {} (empty dict).

    Args:
        provided: Map {param_name: actual_value} of parameters to check
        tool: Name of the tool for the help hint
        action: Action being performed (for help targeting)
        example: Concrete example call
        types: Optional map {param_name: "int | None" / "str" / ...}

    Returns:
        None if every value is present.
        dict with structured error otherwise (see missing_params).
    """
    missing: list[str] = []
    for name, value in provided.items():
        if value is None or value == "" or value == [] or value == {}:
            missing.append(name)
    if not missing:
        return None
    return missing_params(
        missing,
        tool=tool,
        action=action,
        example=example,
        types=types,
    )


class ModusBIError(Exception):
    """Базовое исключение MCP сервера ModusBI."""

    def __init__(self, message: str, code: str | None = None, details: dict | None = None):
        self.message = message
        self.code = code or "MODUSBI_ERROR"
        self.details = details or {}
        super().__init__(message)

    def to_dict(self) -> dict:
        """Преобразует исключение в dict для ответа."""
        return {
            "success": False,
            "error": {
                "code": self.code,
                "message": self.message,
                "details": self.details
            }
        }


class AuthenticationError(ModusBIError):
    """Ошибка авторизации (401)."""

    def __init__(self, message: str = "Ошибка авторизации", details: dict | None = None):
        super().__init__(message, code="AUTHENTICATION_ERROR", details=details)


class APIError(ModusBIError):
    """Общая ошибка API."""

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        details: dict | None = None
    ):
        details = details or {}
        if status_code:
            details["status_code"] = status_code
        super().__init__(message, code="API_ERROR", details=details)


class NotFoundError(ModusBIError):
    """Объект не найден (404)."""

    def __init__(
        self,
        resource: str,
        resource_id: int | str | None = None,
        details: dict | None = None,
        object_id: int | str | None = None,
    ):
        # Фактические call-sites (report/dataset/component/reportgroup tools)
        # используют паттерн NotFoundError(f"Report {id} not found", object_id=id) —
        # раньше kwarg object_id поднимал TypeError (unexpected keyword) ВМЕСТО
        # NotFoundError. Принимаем object_id как синоним resource_id; если
        # resource — уже готовое сообщение, не дописываем «не найден».
        if resource_id is None and object_id is not None:
            resource_id = object_id

        details = details or {}
        details["resource"] = resource
        if resource_id is not None:
            details["resource_id"] = resource_id

        lowered = resource.lower()
        if object_id is not None or "not found" in lowered or "не найден" in lowered:
            message = resource  # готовое сообщение от caller'а
        else:
            message = f"{resource} не найден"
            if resource_id is not None:
                message = f"{resource} с ID {resource_id} не найден"

        super().__init__(message, code="NOT_FOUND", details=details)


class ValidationError(ModusBIError):
    """Ошибка валидации данных (400)."""

    def __init__(
        self,
        message: str,
        field: str | None = None,
        details: dict | None = None
    ):
        details = details or {}
        if field:
            details["field"] = field
        super().__init__(message, code="VALIDATION_ERROR", details=details)


class SecurityError(ModusBIError):
    """Ошибка безопасности (403) - операция запрещена в текущем режиме."""

    def __init__(
        self,
        message: str = "Операция запрещена в текущем режиме",
        action: str | None = None,
        current_mode: str | None = None,
        required_mode: str | None = None,
        details: dict | None = None
    ):
        details = details or {}
        if action:
            details["action"] = action
        if current_mode:
            details["current_mode"] = current_mode
        if required_mode:
            details["required_mode"] = required_mode
        super().__init__(message, code="SECURITY_ERROR", details=details)


class InstanceError(ModusBIError):
    """Ошибка работы с инстансами порталов."""

    def __init__(
        self,
        message: str,
        instance_name: str | None = None,
        details: dict | None = None
    ):
        details = details or {}
        if instance_name:
            details["instance"] = instance_name
        super().__init__(message, code="INSTANCE_ERROR", details=details)
