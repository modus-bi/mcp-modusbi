"""Unit tests для estimate_h() — эвристика расчёта высоты HsTextBlock.

Helper в app/tools/text_block_helper.py обходит фронтовый кламп высоты до 88px.
Тесты фиксируют калибровку эвристики, чтобы она не деградировала при правках.

Run:
    python -m app.tests.test_text_block_helper
"""
import sys

from app.tools.text_block_helper import estimate_h, apply_textblock_layout_workaround


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


def in_range(v: int, lo: int, hi: int) -> bool:
    return lo <= v <= hi


def main() -> None:
    section("Граничные случаи — empty / very short")
    h = estimate_h("")
    check("empty content → 3 (минимум)", h == 3, detail=f"got {h}")
    h = estimate_h("<p>Short</p>")
    check("very short → 3 (через fallback по plain_len)", h == 3, detail=f"got {h}")

    section("Таблицы — styled vs minimal")
    styled_table = (
        '<h3>Веса</h3><table style="font-size:13px">'
        '<tr><th style="padding:8px">Метрика</th><th style="padding:8px">Вес</th></tr>'
        + '<tr><td style="padding:8px">x</td><td style="padding:8px">y</td></tr>' * 4
        + '</table>'
    )
    h = estimate_h(styled_table)
    check(f"styled 4tr+header: h≈10-12 (~33px row)",
          in_range(h, 9, 13), detail=f"got {h}")

    minimal_table = '<h3>Test</h3><table>' + '<tr><td>x</td></tr>' * 5 + '</table>'
    h = estimate_h(minimal_table)
    check(f"minimal 5tr: h≈6-8 (~18px row)",
          in_range(h, 5, 9), detail=f"got {h}")

    section("REGRESSION: множественные <pre> блоки")
    two_pre = '<pre>line1\nline2</pre><pre>line3\nline4\nline5</pre>'
    h = estimate_h(two_pre)
    # Учитываются оба <pre> (5 строк суммарно) — h≈5-6, не только первый.
    check("оба <pre> учтены, не только первый",
          h >= 5, detail=f"got {h}")

    section("REGRESSION: trailing \\n в <pre> не даёт фантомную строку")
    pre_with_trailing = '<pre>line1\nline2\n</pre>'  # фактически 2 строки
    pre_no_trailing = '<pre>line1\nline2</pre>'      # тоже 2 строки
    h1 = estimate_h(pre_with_trailing)
    h2 = estimate_h(pre_no_trailing)
    check("trailing \\n не меняет результат",
          h1 == h2, detail=f"trailing={h1} vs no_trailing={h2}")

    section("REGRESSION: множественные <table> с разной стилизацией")
    # Первая голая, вторая стилизована — должна сработать styled-калибровка
    mixed_tables = (
        '<table>' + '<tr><td>x</td></tr>' * 3 + '</table>'
        + '<table style="font-size:13px">'
        + '<tr><td style="padding:8px">y</td></tr>' * 3 + '</table>'
    )
    h = estimate_h(mixed_tables)
    # 6tr суммарно. Если cтилизация определена правильно — styled (~33px),
    # h≈10-12. Если нет — minimal (~18px), h≈6-8.
    check("styled-таблица найдена не только в первом блоке",
          h >= 9, detail=f"got {h}")

    section("Headings — h2/h3")
    h = estimate_h("<h2>Заголовок раздела</h2><p>Один параграф.</p>")
    check("h2+p: h в [3, 6]", in_range(h, 3, 6), detail=f"got {h}")

    section("Список — <li>")
    list_html = "<ul>" + "<li>пункт</li>" * 5 + "</ul>"
    h = estimate_h(list_html)
    check("список 5 пунктов: h в [4, 8]", in_range(h, 4, 8), detail=f"got {h}")

    section("Section-box / callout-box — visual containers")
    section_box = (
        '<div style="background:#f6f8fa;border:1px solid #d0d7de;padding:16px">'
        '<h3>Title</h3><p>Body.</p></div>'
    )
    h_with = estimate_h(section_box)
    h_without = estimate_h('<h3>Title</h3><p>Body.</p>')
    check("section-box добавляет ≥1 row",
          h_with > h_without, detail=f"with={h_with} without={h_without}")

    section("Диапазон [3, 32] всегда соблюдается")
    huge = "<p>x</p>" * 1000
    h = estimate_h(huge)
    check("огромный контент клампится до 32",
          h == 32, detail=f"got {h}")

    section("apply_textblock_layout_workaround — обход фронтового клампа")
    entry = {"modified": False, "i": "5"}
    apply_textblock_layout_workaround(entry, "HsTextBlock")
    check("HsTextBlock → modified=True", entry["modified"] is True, detail=str(entry))
    check("HsTextBlock → group=-1", entry.get("group") == -1, detail=str(entry))

    entry = {"modified": False, "i": "5"}
    apply_textblock_layout_workaround(entry, "HsBarAMchartsChart")
    check("non-textblock → modified=False (no-op)",
          entry["modified"] is False, detail=str(entry))
    check("non-textblock → group НЕ добавлен",
          "group" not in entry, detail=str(entry))

    entry = {"modified": False, "i": "5"}
    apply_textblock_layout_workaround(entry, "")
    check("empty type → no-op (защита от опечаток)",
          entry["modified"] is False and "group" not in entry, detail=str(entry))

    e = {"modified": False}
    result = apply_textblock_layout_workaround(e, "HsTextBlock")
    check("возвращает тот же dict для chaining", result is e)

    section("REGRESSION: 4 callsites вызывают workaround")
    # Проверяем что во всех файлах добавления компонента импорт+вызов есть.
    # Это статический контракт — без него будущий рефакторинг может «забыть»
    # вызов и кламп высоты текстового блока вернётся.
    import pathlib
    repo_root = pathlib.Path(__file__).resolve().parents[2]
    # Минимум вызовов с открывающей скобкой в каждом файле.
    # component_crud.py: 3 callsites (_add_component, _add_no_dataset_component,
    # _copy_component) → ≥3 вызова. batch_operations.py: 1 callsite → ≥1 вызов.
    file_min_calls = {
        "app/tools/component_crud.py": 3,
        "app/tools/batch_operations.py": 1,
    }
    for path, min_calls in file_min_calls.items():
        body = (repo_root / path).read_text(encoding="utf-8")
        check(f"{path}: импорт apply_textblock_layout_workaround",
              "apply_textblock_layout_workaround" in body,
              detail=f"workaround не упомянут в {path}")
        # `name(` — это вызов, импорт без скобки не считается.
        n = body.count("apply_textblock_layout_workaround(")
        check(f"{path}: ≥{min_calls} вызов(а)",
              n >= min_calls, detail=f"got {n}")

    print(f"\n===\nResult: {ok} OK, {fail} FAIL")
    sys.exit(0 if fail == 0 else 1)


if __name__ == "__main__":
    main()
