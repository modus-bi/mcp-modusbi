"""viewType.displayType value_map (slug-значения → реальные фронт-значения filterType).

Slug принимает дружелюбные алиасы [dropdown,list,radio,checkbox,slider,datepicker],
а фронт filterType читает [null,panel,slider,period,buttons,twofield] — пересечение
только "slider". value_map транслирует алиасы в реальные значения при path_write.
"""
import pytest

from app.tools.config_schema import (
    apply_slug_overrides,
    validate_config_overrides,
)

CT = "HsFilterControlPanel"


@pytest.mark.parametrize(
    "slug_value, expected_filter_type",
    [
        ("dropdown", None),       # дефолт-дропдаун = null
        ("list", "panel"),        # список → панель чекбоксов
        ("radio", "panel"),
        ("checkbox", "panel"),
        ("datepicker", "period"), # выбор даты → period
        ("slider", "slider"),     # сквозное (реальное фронт-значение)
        ("panel", "panel"),       # реальные фронт-значения проходят без изменений
        ("period", "period"),
        ("buttons", "buttons"),
        ("twofield", "twofield"),
    ],
)
def test_displaytype_translates_to_frontend_filtertype(slug_value, expected_filter_type):
    cleaned, _ = validate_config_overrides({"viewType.displayType": slug_value}, CT)
    assert "viewType.displayType" in cleaned, f"{slug_value} должен пройти валидацию"
    cfg = apply_slug_overrides({}, cleaned, CT)
    assert cfg.get("filterType") == expected_filter_type


def test_displaytype_invalid_value_rejected():
    cleaned, warnings = validate_config_overrides({"viewType.displayType": "bogus"}, CT)
    assert "viewType.displayType" not in cleaned
    assert warnings


def test_multiselect_unchanged_path_write():
    """value_map не должен ломать прочие path_write-слаги панели фильтра."""
    cleaned, _ = validate_config_overrides({"viewType.multiselect": True}, CT)
    cfg = apply_slug_overrides({}, cleaned, CT)
    assert cfg.get("multipleChoice") is True


def test_value_map_only_affects_mapped_slugs():
    """Слаги без value_map пишут значение verbatim (регресс-страховка диспетчера)."""
    cleaned, _ = validate_config_overrides({"viewType.searchEnabled": True}, CT)
    cfg = apply_slug_overrides({}, cleaned, CT)
    assert cfg.get("searchInBaseMode") is True
