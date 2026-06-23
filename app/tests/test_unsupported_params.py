"""check_unsupported_params возвращает warnings для silent-ignored.

column_fields / series_field на chart-типе кроме pivot/comparison не
поддерживаются. builders.check_unsupported_params(component_type, ...)
возвращает list[str] с подсказками. Caller (component_crud._add_component,
batch_operations._add_multiple_components) добавляет их в response.warnings.

Run:
    python -m app.tests.test_unsupported_params
"""
import sys

from app.tools.builders import check_unsupported_params, COLUMN_FIELDS_SUPPORTED_TYPES


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
    section("COLUMN_FIELDS_SUPPORTED_TYPES — sanity")
    check("содержит HsPivotChart", "HsPivotChart" in COLUMN_FIELDS_SUPPORTED_TYPES)
    check("содержит HsComparisonChart",
          "HsComparisonChart" in COLUMN_FIELDS_SUPPORTED_TYPES)
    check("НЕ содержит HsBarAMchartsChart",
          "HsBarAMchartsChart" not in COLUMN_FIELDS_SUPPORTED_TYPES)

    section("column_fields на SUPPORTED — без warning")
    w = check_unsupported_params("HsPivotChart", column_fields="year,quarter")
    check("HsPivotChart + column_fields → 0 warnings", w == [], detail=str(w))

    w = check_unsupported_params("HsComparisonChart", column_fields="metric_name")
    check("HsComparisonChart + column_fields → 0 warnings",
          w == [], detail=str(w))

    section("column_fields на UNSUPPORTED chart-типах → warning")
    for ct in ("HsBarAMchartsChart", "HsLineAMchartsChart", "HsPieAMchartsChart",
               "HsTreeMap", "HsSunburstChart"):
        w = check_unsupported_params(ct, column_fields="year")
        check(f"{ct} + column_fields → 1 warning",
              len(w) == 1, detail=str(w))
        check(f"  warning упоминает {ct}",
              ct in w[0], detail=w[0] if w else "")
        check(f"  warning указывает на supported types",
              "HsPivotChart" in w[0], detail=w[0] if w else "")

    section("column_fields=None или '' — без warning")
    w = check_unsupported_params("HsBarAMchartsChart", column_fields=None)
    check("None → 0 warnings", w == [], detail=str(w))

    w = check_unsupported_params("HsBarAMchartsChart", column_fields="")
    check("'' → 0 warnings", w == [], detail=str(w))

    section("series_field после B1: 0 warnings на supported chart types")
    # series_field теперь реально применяется на bar/line/area/stock
    w = check_unsupported_params("HsBarAMchartsChart", series_field="product")
    check("BarChart (supported) + series_field → 0 warnings",
          w == [], detail=str(w))
    w = check_unsupported_params("HsLineAMchartsChart", series_field="product")
    check("LineChart (supported) + series_field → 0 warnings",
          w == [], detail=str(w))

    # На НЕ-supported типах warning остаётся
    w = check_unsupported_params("HsPieAMchartsChart", series_field="product")
    check("PieChart (NOT supported) + series_field → 1 warning",
          len(w) == 1, detail=str(w))
    w = check_unsupported_params("HsTextBlock", series_field="product")
    check("TextBlock + series_field → 1 warning", len(w) == 1)

    w = check_unsupported_params("HsBarAMchartsChart", series_field=None)
    check("series_field=None → 0 warnings", w == [], detail=str(w))

    section("оба параметра вместе на BarChart: column_fields warn, series no")
    w = check_unsupported_params(
        "HsBarAMchartsChart", column_fields="year", series_field="product",
    )
    # column_fields warning остался (BarChart не в COLUMN_FIELDS_SUPPORTED)
    # series_field warning ушёл (BarChart в SERIES_FIELD_SUPPORTED)
    check("BarChart + column_fields + series_field → 1 warning (только column_fields)",
          len(w) == 1, detail=str(w))
    check("warning про column_fields",
          "column_fields" in w[0] if w else False)

    section("Edge: пустые параметры без типа")
    w = check_unsupported_params("HsBarAMchartsChart")
    check("без параметров → 0 warnings", w == [])

    print(f"\n===\nResult: {ok} OK, {fail} FAIL")
    sys.exit(0 if fail == 0 else 1)


if __name__ == "__main__":
    main()
