"""UI-мета слагов: полнота + структура (CI-guard, чтобы новые слаги не дрейфовали)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.tools.config_schema import SLUG_SCHEMA, SLUG_UI_META, enrich_slug


def test_ui_meta_covers_all_slugs():
    """Каждый слаг SLUG_SCHEMA должен иметь UI-мету (label+section)."""
    missing = [s for s in SLUG_SCHEMA if s not in SLUG_UI_META]
    assert not missing, f"слаги без UI-меты (запусти scripts/gen_slug_ui_meta.py): {missing}"
    for s, m in SLUG_UI_META.items():
        assert m.get("ui_label") and m.get("ui_section"), f"{s}: пустой ui_label/ui_section"


def test_enrich_slug_adds_ui_fields():
    """enrich_slug добавляет ui_label/ui_section, не мутируя SLUG_SCHEMA."""
    slug = next(iter(SLUG_SCHEMA))
    enriched = enrich_slug(slug, SLUG_SCHEMA[slug])
    assert "ui_label" in enriched and "ui_section" in enriched
    assert "ui_label" not in SLUG_SCHEMA[slug]  # не мутировали оригинал
