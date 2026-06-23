"""Unit tests for the MCP-boundary error envelope (server.py) + enum sync.

Covers:
- _tool_error_envelope / _dispatch_safe в server.py конвертируют
  APIError/NotFoundError/ValidationError из api_call в
  {"success": False, "error", "status_code", ...} вместо голого
  «Error executing tool: HTTP 404»;
- ResetModeLiteral/ResetTypeLiteral синхронизированы с рантайм-whitelist
  component_filters (_VALID_RESET_MODES={'min','max'}, _VALID_RESET_TYPES={'always'});
- LinkTargetLiteral сужен до рантайма component_axes._VALID_LINK_TARGETS;
- NotFoundError принимает object_id= (паттерн всех call-sites) без TypeError.

Run:
    python -m app.tests.test_tool_error_envelope
"""
import asyncio
import inspect
import sys
from typing import get_args

from app import server
from app.core.exceptions import APIError, NotFoundError, ValidationError
from app.tools.component_axes import _VALID_LINK_TARGETS
from app.tools.component_filters import _VALID_RESET_MODES, _VALID_RESET_TYPES


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


async def _raises(exc: Exception) -> dict:
    raise exc


async def _returns(value: dict) -> dict:
    return value


def main() -> None:
    section("_tool_error_envelope")
    env = server._tool_error_envelope(APIError("HTTP 404: Объект не найден", status_code=404))
    check("APIError → success False", env.get("success") is False, detail=str(env))
    check("APIError → error text", "404" in env.get("error", ""), detail=str(env))
    check("APIError → status_code из details", env.get("status_code") == 404, detail=str(env))
    check("404 → hint присутствует", bool(env.get("hint")), detail=str(env))

    env = server._tool_error_envelope(ValidationError("invalid field 'x'"))
    check("ValidationError → success False", env.get("success") is False, detail=str(env))
    check("ValidationError → status_code None", env.get("status_code") is None, detail=str(env))

    env = server._tool_error_envelope(NotFoundError("Report 999 not found", object_id=999))
    check("NotFoundError → success False", env.get("success") is False, detail=str(env))
    check("NotFoundError → hint присутствует", bool(env.get("hint")), detail=str(env))

    section("_dispatch_safe")
    res = asyncio.run(server._dispatch_safe(_raises(APIError("HTTP 404: нет", status_code=404))))
    check("APIError пойман → envelope", res.get("success") is False and res.get("status_code") == 404, detail=str(res))

    res = asyncio.run(server._dispatch_safe(_raises(NotFoundError("Report 1 not found", object_id=1))))
    check("NotFoundError пойман → envelope", res.get("success") is False, detail=str(res))

    res = asyncio.run(server._dispatch_safe(_raises(ValidationError("bad"))))
    check("ValidationError пойман → envelope", res.get("success") is False, detail=str(res))

    res = asyncio.run(server._dispatch_safe(_returns({"success": True, "data": 1})))
    check("успешный результат — passthrough", res == {"success": True, "data": 1}, detail=str(res))

    propagated = False
    try:
        asyncio.run(server._dispatch_safe(_raises(RuntimeError("init failed"))))
    except RuntimeError:
        propagated = True
    check("RuntimeError НЕ глотается", propagated)

    section("Обёртки tools используют _dispatch_safe")
    wrapped_tools = [
        "report_operations", "reportgroup_operations", "dataset_operations",
        "component_crud", "component_filters", "component_axes",
        "component_styling", "batch_operations", "style_operations",
        "data_export_operations", "security_operations", "report_template",
    ]
    for tool_name in wrapped_tools:
        fn = getattr(server, tool_name, None)
        src = inspect.getsource(fn) if fn is not None else ""
        check(f"{tool_name} → _dispatch_safe", "_dispatch_safe(" in src)

    section("reset_mode/reset_type enum sync (schema ↔ runtime)")
    check(
        "ResetModeLiteral == _VALID_RESET_MODES",
        set(get_args(server.ResetModeLiteral)) == _VALID_RESET_MODES,
        detail=f"{get_args(server.ResetModeLiteral)} vs {_VALID_RESET_MODES}",
    )
    check(
        "ResetTypeLiteral == _VALID_RESET_TYPES",
        set(get_args(server.ResetTypeLiteral)) == _VALID_RESET_TYPES,
        detail=f"{get_args(server.ResetTypeLiteral)} vs {_VALID_RESET_TYPES}",
    )
    check("'parent'/'all'/'none' убраны из ResetModeLiteral",
          not ({"parent", "all", "none"} & set(get_args(server.ResetModeLiteral))))

    section("link_target enum sync (schema ↔ runtime)")
    check(
        "LinkTargetLiteral == _VALID_LINK_TARGETS",
        set(get_args(server.LinkTargetLiteral)) == set(_VALID_LINK_TARGETS),
        detail=f"{get_args(server.LinkTargetLiteral)} vs {_VALID_LINK_TARGETS}",
    )

    section("NotFoundError: object_id= больше не TypeError")
    try:
        e = NotFoundError("Report 999 not found", object_id=999)
        check("конструируется без TypeError", True)
        check("message verbatim", str(e) == "Report 999 not found", detail=str(e))
        check("details.resource_id", e.details.get("resource_id") == 999, detail=str(e.details))
    except TypeError as te:
        check("конструируется без TypeError", False, detail=str(te))

    # канонический вызов (resource + resource_id) не сломан
    e = NotFoundError("Report", resource_id=5)
    check("каноническая форма сохранена", str(e) == "Report с ID 5 не найден", detail=str(e))

    print(f"\n===\nResult: {ok} OK, {fail} FAIL")
    sys.exit(0 if fail == 0 else 1)


if __name__ == "__main__":
    main()
