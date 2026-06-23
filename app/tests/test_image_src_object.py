"""image.src пишет config.image как объект {path, ID}, не голую строку.

Фронт ImagePanel ждёт config.image как ОБЪЕКТ {path, ID} (upload-based). Голая
строка → config.image.path undefined → React error boundary (`reading 'replace'`)
крашит компонент целиком. Handler оборачивает значение в {path, ID}; пустое → None
(placeholder без краша).
"""
from app.tools.config_schema import apply_slug_overrides, validate_config_overrides

CT = "HsImagePanel"


def test_image_src_writes_object_not_bare_string():
    url = "https://example.com/favicon.ico"
    cleaned, _ = validate_config_overrides({"image.src": url}, CT)
    cfg = apply_slug_overrides({"image": None}, cleaned, CT)
    assert cfg["image"] == {"path": url, "ID": url}
    assert isinstance(cfg["image"], dict), "config.image должен быть объектом (иначе .path краш)"


def test_image_src_empty_resets_to_none():
    for empty in ("", None, False):
        cleaned, _ = validate_config_overrides({"image.src": empty}, CT)
        cfg = apply_slug_overrides({"image": {"path": "x", "ID": "x"}}, cleaned, CT)
        assert cfg["image"] is None


def test_image_link_robust_when_link_missing():
    """image.linkName не должен падать, если config.link отсутствует/None."""
    cleaned, _ = validate_config_overrides({"image.linkName": "https://ya.ru"}, CT)
    cfg = apply_slug_overrides({"image": None}, cleaned, CT)
    assert cfg["link"]["name"] == "https://ya.ru"


def test_image_background_slugs_still_top_level():
    cleaned, _ = validate_config_overrides({"image.backgroundSize": "cover"}, CT)
    cfg = apply_slug_overrides({"image": None}, cleaned, CT)
    assert cfg["backgroundSize"] == "cover"
    assert "src" not in cfg  # регресс: не мусорный cfg["src"]
