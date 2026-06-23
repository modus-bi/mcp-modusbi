"""Unit + regression tests for app/tools/schema_slim.py.

strip_titles() не должен удалять ключ "title" из любого dict
начиная с depth>=1, чтобы не удалить параметр функции с именем `title`,
если он попадает в `properties.title`. Затронутые tools:
  - component_crud (title параметр)
  - component_axes (title параметр)
  - batch_operations (ComponentSpec.title в $defs)

Эти тесты фиксируют контракт: имена параметров (под `properties.X`)
никогда не исчезают из JSON-schema, даже если совпадают с meta-ключами
JSON Schema (`title`, `description`, `format` и т.д.).

Run:
    python -m app.tests.test_schema_slim
"""
import sys
import inspect

from app.tools.schema_slim import slim_schema, strip_titles, apply_slim_to_mcp


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


def main() -> None:
    section("strip_titles — meta-title удаляется внутри property descriptor")
    schema = {
        "type": "object",
        "title": "MyTool",  # top-level — keep
        "properties": {
            "report_id": {"type": "integer", "title": "Report Id"},
            "title": {"type": "string", "title": "Title"},  # parameter named 'title'!
        },
    }
    out = strip_titles(schema)
    check("top-level title сохранён", out.get("title") == "MyTool", detail=str(out))
    check("meta-title 'Report Id' удалён",
          "title" not in out["properties"]["report_id"],
          detail=str(out["properties"]["report_id"]))

    section("strip_titles — ИМЯ параметра 'title' НЕ удаляется")
    check("параметр 'title' под properties сохранён",
          "title" in out["properties"],
          detail=str(out["properties"]))
    check("его внутренний meta-title удалён (отделено от имени)",
          "title" not in out["properties"]["title"],
          detail=str(out["properties"]["title"]))

    section("strip_titles — $defs не теряет имена моделей с именем 'title'")
    schema_with_defs = {
        "type": "object",
        "$defs": {
            "ComponentSpec": {
                "type": "object",
                "title": "ComponentSpec",  # meta-title модели — должен удалиться
                "properties": {
                    "title": {"type": "string", "title": "Title"},  # поле модели
                },
            },
        },
    }
    out2 = strip_titles(schema_with_defs)
    check("ComponentSpec в $defs сохранён",
          "ComponentSpec" in out2["$defs"], detail=str(out2.get("$defs", {})))
    check("meta-title самой модели ComponentSpec удалён",
          "title" not in out2["$defs"]["ComponentSpec"], detail=str(out2["$defs"]["ComponentSpec"]))
    check("поле 'title' внутри ComponentSpec сохранено",
          "title" in out2["$defs"]["ComponentSpec"]["properties"],
          detail=str(out2["$defs"]["ComponentSpec"]["properties"]))

    section("slim_schema — anyOf:[T, null] → T")
    schema = {"properties": {"x": {"anyOf": [{"type": "string"}, {"type": "null"}]}}}
    out = slim_schema(schema)
    check("anyOf:[str,null] схлопнут в просто str",
          out["properties"]["x"].get("type") == "string"
          and "anyOf" not in out["properties"]["x"],
          detail=str(out))
    check("default:null добавлен", out["properties"]["x"].get("default") is None,
          detail=str(out))

    section("slim_schema — идемпотентность")
    once = slim_schema(schema)
    twice = slim_schema(once)
    check("slim_schema(slim_schema(x)) == slim_schema(x)", once == twice)

    section("strip_titles — идемпотентность")
    once = strip_titles({"title": "Top", "properties": {"title": {"type": "string", "title": "T"}}})
    twice = strip_titles(once)
    check("strip_titles идемпотентен", once == twice, detail=f"{once} vs {twice}")

    section("REGRESSION: для всех зарегистрированных tools — signature ⊆ schema")
    from app.server import mcp
    issues = []
    for tname, tool in mcp._tool_manager._tools.items():
        fn = tool.fn if hasattr(tool, "fn") else None
        if not fn:
            continue
        sig_params = set(inspect.signature(fn).parameters.keys())
        sig_params -= {"self", "cls", "ctx", "mcp", "kwargs", "args"}
        schema_props = set((tool.parameters or {}).get("properties", {}).keys())
        missing = sig_params - schema_props
        if missing:
            issues.append(f"{tname}: missing in schema — {sorted(missing)}")
    check(f"все параметры всех tools видны клиенту через JSON-schema "
          f"({len(mcp._tool_manager._tools)} tools проверено)",
          not issues, detail="; ".join(issues))

    section("REGRESSION: title в скомпилированной schema конкретных tools")
    for tname in ("component_crud", "component_axes"):
        props = (mcp._tool_manager._tools[tname].parameters or {}).get("properties", {})
        check(f"{tname}.properties.title присутствует",
              "title" in props, detail=f"keys: {sorted(props.keys())[:5]}…")
        if "title" in props:
            check(f"{tname}.title.description непустой",
                  bool(props["title"].get("description")), detail=str(props["title"]))

    section("REGRESSION: ComponentSpec.title в batch_operations.$defs")
    schema_batch = mcp._tool_manager._tools["batch_operations"].parameters or {}
    cs = (schema_batch.get("$defs") or {}).get("ComponentSpec", {})
    cs_props = cs.get("properties", {})
    check("ComponentSpec.title сохранён в $defs",
          "title" in cs_props, detail=f"props: {sorted(cs_props.keys())[:5]}…")

    print(f"\n===\nResult: {ok} OK, {fail} FAIL")
    sys.exit(0 if fail == 0 else 1)


if __name__ == "__main__":
    main()
