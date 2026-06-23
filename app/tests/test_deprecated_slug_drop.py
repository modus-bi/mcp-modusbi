"""deprecated-слаги дропаются в validate (не попадают в cleaned → корректный slugs_applied).

validate выдаёт warning по deprecated и исключает слаг из cleaned (делает continue),
поэтому диспетчер apply его пропускает, а счётчик slugs_applied его не учитывает.
"""
from app.tools.config_schema import validate_config_overrides


def test_deprecated_excluded_from_cleaned():
    cleaned, warnings = validate_config_overrides(
        {"viewType.resetEnabled": True, "viewType.showAll": True}, "HsFilterControlPanel"
    )
    assert "viewType.resetEnabled" not in cleaned
    assert "viewType.showAll" not in cleaned
    assert any("DEPRECATED" in w for w in warnings)


def test_live_slug_survives_alongside_deprecated():
    cleaned, _ = validate_config_overrides(
        {"viewType.resetEnabled": True, "viewType.multiselect": True}, "HsFilterControlPanel"
    )
    assert cleaned == {"viewType.multiselect": True}


def test_deprecated_area_fillopacity_dropped():
    cleaned, warnings = validate_config_overrides({"visuals.fillOpacity": 0.7}, "HsAreaChart")
    assert "visuals.fillOpacity" not in cleaned
    assert any("DEPRECATED" in w for w in warnings)


def test_slugs_applied_count_excludes_deprecated():
    """Счётчик (len cleaned) не учитывает deprecated."""
    cleaned, _ = validate_config_overrides(
        {"viewType.resetEnabled": True, "viewType.showAll": True, "viewType.searchEnabled": True},
        "HsFilterControlPanel",
    )
    assert len(cleaned) == 1  # только searchEnabled, не 3
