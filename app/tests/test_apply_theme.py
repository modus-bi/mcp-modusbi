"""apply_theme — brand-pack CSS из 5-цветной темы.

style_operations(action='apply_theme', theme={5 цветов}) генерит
CSS и применяет к отчёту. По умолчанию mode='merge' — добавляет к
существующему CSS, чтобы кастомные правки не потерять.

Run:
    python -m app.tests.test_apply_theme
"""
import asyncio
import sys

from app.tools.style_operations import (
    _build_theme_css,
    _apply_theme,
    _THEME_DEFAULT,
)


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


class FakeClient:
    def __init__(self, current_css: str = ""):
        self.current_css = current_css
        self.last_saved_css = None

    async def api_call(self, entity, action, object_id=None, **kwargs):
        if entity == "reports" and action == "get":
            # Поле в options называется CSStext (не css) — см. _get_style
            return {
                "status": 200,
                "data": [{
                    "ID": object_id,
                    "name": "test",
                    "options": {"CSStext": self.current_css},
                }],
            }
        if entity == "reports" and action == "update":
            data = kwargs.get("data")
            if isinstance(data, list) and data:
                self.last_saved_css = (
                    data[0].get("options", {}).get("CSStext", "")
                )
                # Update self.current_css чтобы следующий get вернул новое
                self.current_css = self.last_saved_css
            return {"status": 200, "data": [{}]}
        return {"status": 200, "data": [{}]}


def run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


def main() -> None:
    section("_build_theme_css: генерирует все 6 групп")
    css = _build_theme_css({"primary": "#1F77B4"})
    check("содержит header gradient",
          ".hsHeader.hsHeader__report" in css)
    check("содержит chart bars fix",
          ".amcharts-graph-column" in css)
    check("содержит filter panel",
          ".hsFilterControlPanel" in css)
    check("содержит table styling",
          ".hsTableReactabularChart" in css)
    check("содержит modal/buttons",
          ".btn-primary" in css)
    check("содержит scrollbar",
          "::-webkit-scrollbar-thumb" in css)

    section("Custom theme подставляется в CSS")
    css = _build_theme_css({
        "primary": "#1B7B45",
        "accent": "#FF6B35",
    })
    check("primary='#1B7B45' в CSS", "#1B7B45" in css)
    check("accent='#FF6B35' в CSS", "#FF6B35" in css)

    section("Default theme когда поле отсутствует")
    css = _build_theme_css({"primary": "#1B7B45"})
    # text и secondary должны быть из default
    check(f"default text={_THEME_DEFAULT['text']} в CSS",
          _THEME_DEFAULT["text"] in css)
    check(f"default secondary={_THEME_DEFAULT['secondary']} в CSS",
          _THEME_DEFAULT["secondary"] in css)

    section("_apply_theme MERGE: добавляет к существующему CSS")
    client = FakeClient(current_css=".custom-rule { color: red; }")
    result = run(_apply_theme(
        client, report_id=35,
        theme={"primary": "#1B7B45"},
        mode="merge",
    ))
    check("success=True", result.get("success") is True,
          detail=str(result)[:150])
    saved = client.last_saved_css or ""
    check("existing CSS сохранён в saved",
          ".custom-rule { color: red; }" in saved,
          detail=saved[:200])
    check("новая тема добавлена",
          "#1B7B45" in saved)
    check("разделитель \\n\\n между блоками",
          ".custom-rule { color: red; }" in saved
          and saved.find(".custom-rule") < saved.find("#1B7B45"))

    section("_apply_theme REPLACE: затирает существующий CSS")
    client = FakeClient(current_css=".old-rule { font-size: 99px; }")
    result = run(_apply_theme(
        client, report_id=35,
        theme={"primary": "#1B7B45"},
        mode="replace",
    ))
    check("success=True", result.get("success") is True)
    saved = client.last_saved_css or ""
    check("existing CSS НЕ в saved (replace)",
          ".old-rule" not in saved, detail=saved[:200])
    check("новая тема применена", "#1B7B45" in saved)

    section("MERGE на пустом current CSS")
    client = FakeClient(current_css="")
    result = run(_apply_theme(
        client, report_id=35,
        theme={"primary": "#1B7B45"},
        mode="merge",
    ))
    check("success=True", result.get("success") is True)
    saved = client.last_saved_css or ""
    check("CSS применён", "#1B7B45" in saved)
    check("нет двойного \\n\\n в начале",
          not saved.startswith("\n"))

    section("Unknown mode → error")
    client = FakeClient()
    result = run(_apply_theme(
        client, report_id=35,
        theme={"primary": "#1B7B45"},
        mode="garbage",
    ))
    check("success=False", result.get("success") is False)
    check("error упоминает mode",
          "mode" in result.get("error", "").lower())

    section("Минимальная theme (только primary) работает")
    client = FakeClient()
    result = run(_apply_theme(
        client, report_id=35,
        theme={"primary": "#1B7B45"},
        mode="replace",
    ))
    check("success=True даже при 1 ключе",
          result.get("success") is True)

    print(f"\n===\nResult: {ok} OK, {fail} FAIL")
    sys.exit(0 if fail == 0 else 1)


if __name__ == "__main__":
    main()
