# Рендер-манифест — сводка (per-component render-contract)

> Генерируется `scripts/gen_render_manifest.py` из slug_json_table + slug_ui_verdicts (эмпирика).
> Полный машинный вид — `render_manifest.json`. Назначение: единый контракт «что рендер читает»,
> против которого можно валидировать json_path в CI (см. test_render_dead_contract).

| компонент | renders | render-dead | config-only | прочее |
|---|--:|--:|--:|--:|
| FilterControlPanel | 2 | 1 | 9 | 2 |
| GENERIC | 50 | 17 | 23 | 6 |
| SwitchControlPanel | 2 | 0 | 0 | 0 |
| areaChart | 13 | 5 | 0 | 2 |
| audioplayer | 0 | 0 | 0 | 5 |
| barChart | 7 | 5 | 0 | 0 |
| bubbleChart | 8 | 2 | 1 | 0 |
| comparisonChart | 0 | 0 | 0 | 5 |
| hierarchicalFilterPanel | 6 | 0 | 5 | 1 |
| iframe | 2 | 0 | 0 | 0 |
| imagePanel | 4 | 0 | 4 | 0 |
| lineChart | 14 | 5 | 0 | 1 |
| mapLeaflet | 10 | 5 | 18 | 6 |
| parallelCoordsChart | 4 | 0 | 0 | 0 |
| pieChart | 8 | 8 | 2 | 1 |
| pivotChart | 16 | 1 | 3 | 4 |
| radarChart | 4 | 0 | 0 | 0 |
| speedometerV2 | 11 | 5 | 0 | 0 |
| stockChart | 8 | 3 | 1 | 1 |
| subheader | 1 | 0 | 0 | 0 |
| sunburstChart | 8 | 1 | 2 | 2 |
| table | 8 | 1 | 0 | 0 |
| tabsPanel | 2 | 0 | 1 | 1 |
| textBlock | 1 | 0 | 1 | 0 |
| tilemapChart | 8 | 4 | 4 | 0 |
| totalsPanelV2 | 2 | 0 | 2 | 0 |
| treeGraph | 4 | 0 | 0 | 0 |
| treeMap | 4 | 0 | 1 | 0 |
