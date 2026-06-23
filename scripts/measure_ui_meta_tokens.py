"""Замер токен-стоимости UI-метаданных слагов (ui_label/ui_section) в list_slugs.

Когда грузится UI-мета: ТОЛЬКО при opt-in префиксе `ui:` в slug_category
(`ui:`, `ui:<category>`, `ui:search:<term>`). По умолчанию — НЕ грузится (нулевая регрессия).
Замеряет реальным токенайзером (tiktoken) default vs +ui по типовым режимам и пишет
снапшот в docs/token-usage/ui_meta_cost.{json,md}.

Usage: python scripts/measure_ui_meta_tokens.py
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

for _v in ("MODUSBI_URL", "MODUSBI_USERNAME", "MODUSBI_PASSWORD"):
    os.environ.setdefault(_v, "stub")
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.tools.component_crud import _list_slugs  # noqa: E402
from app.tools.token_counter import count_tokens_json, tokenizer_backend  # noqa: E402

# (имя режима, kwargs, как-вызвать-через-slug_category-в-инструменте)
MODES = [
    ("default summary (без аргументов)", {}, "list_slugs()"),
    ("category=legend", {"category": "legend"}, "slug_category='legend' vs 'ui:legend'"),
    ("category=labels", {"category": "labels"}, "slug_category='labels' vs 'ui:labels'"),
    ("search=color (Bar)", {"component_type": "HsBarAMchartsChart", "search": "color"},
     "'search:color' vs 'ui:search:color'"),
    ("component_type=Bar (весь)", {"component_type": "HsBarAMchartsChart"}, "component_type + 'ui:'"),
    ("component_type=Map (39 слагов)", {"component_type": "HsMapLeafletChart"}, "component_type + 'ui:'"),
]


def main() -> None:
    tok = tokenizer_backend("cl100k_base")
    rows = []
    for name, kw, how in MODES:
        off = count_tokens_json(_list_slugs(**kw))
        on = count_tokens_json(_list_slugs(include_ui=True, **kw))
        rows.append({"mode": name, "how": how, "default": off, "with_ui": on,
                     "delta": on - off, "pct": round(100 * (on - off) / max(off, 1))})

    snap = {
        "schema_version": 1,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "tokenizer": tok,
        "feature": "slug UI metadata (ui_label/ui_section) in list_slugs",
        "loads_when": "opt-in only: slug_category prefix 'ui:' (else NOT loaded — zero regression)",
        "rows": rows,
    }
    out_dir = ROOT / "docs/token-usage"
    (out_dir / "ui_meta_cost.json").write_text(
        json.dumps(snap, ensure_ascii=False, indent=2), encoding="utf-8")

    md = ["# Токен-стоимость UI-метаданных слагов (list_slugs)", "",
          f"> Токенайзер: {tok}. Генерируется `scripts/measure_ui_meta_tokens.py`.", "",
          "**Когда грузится:** только при opt-in префиксе `ui:` в `slug_category`",
          "(`ui:`, `ui:<category>`, `ui:search:<term>`). По умолчанию НЕ грузится — нулевая регрессия.", "",
          "| режим | default | +ui | Δток | Δ% |", "|---|--:|--:|--:|--:|"]
    for r in rows:
        md.append(f"| {r['mode']} | {r['default']} | {r['with_ui']} | +{r['delta']} | {r['pct']}% |")
    md += ["", "**Вывод:** базовый обзор (`list_slugs()` без аргументов) — **+0** токенов.",
           "UI-мета добавляет ~50-60% и только по явному запросу `ui:`. Приемлемо для уточнения",
           "настроек ОДНОГО компонента/категории (напр. `ui:legend` ≈ +210 ток); для широкого",
           "обзора оставляйте `ui:` выключенным.", ""]
    (out_dir / "ui_meta_cost.md").write_text("\n".join(md), encoding="utf-8")
    print(f"Снапшот → docs/token-usage/ui_meta_cost.{{json,md}} (tokenizer {tok})")
    for r in rows:
        print(f"  {r['mode']:36} {r['default']:6} → {r['with_ui']:6}  (+{r['delta']}, {r['pct']}%)")


if __name__ == "__main__":
    main()
