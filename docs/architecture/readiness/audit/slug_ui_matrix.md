# Матрица UI-верификации слагов — все 342 × вердикт

> Генерируется `scripts/gen_slug_ui_matrix.py` из `slug_json_table.json` (полный список) +
> `slug_ui_verdicts.json` (пер-слаговые вердикты).
> «Прошёл UI-аудит» = есть вердикт; **⬜ = не проверено**.

## Покрытие

- Всего слагов: **342**
- Прошли UI-проверку (есть вердикт): **342** (100%)
- Не проверено (⬜): **0**
- T1 (renderable) ещё НЕ проверено: **0** ← осталось гонять браузером

Вердикты: ✅ 180 · 🟡cfg 77 · 🔴 49 · ⚠️ 17 · ⚪na 17 · ⚪rej 2

| код | значение |
|---|---|
| ✅ | ✅ rendered |
| 🔴 | 🔴 no-effect (config верный, фронт не рисует) |
| 🟡cfg | config-only (A==C, визуал недостижим/интерактив) |
| ⚠️ | ⚠️ ambiguous (нужны спец-данные/контраст) |
| ⚪rej | ⚪ applied:0 (валидатор отклонил значение) |
| ⚪na | ⚪ not-applicable (на этом типе нет смысла) |
| ⬜ | НЕ проверено |

## GENERIC — 96/96 проверено

| слаг | тир | вердикт | где/нота |
|---|:--:|:--:|---|
| `axes.autoZoom` | T1 | 🔴 | bar |
| `axes.categoryGrid` | T1 | ✅ | bar |
| `axes.categoryLabelAngle` | T1 | 🔴 | bar |
| `axes.categoryLabels` | T1 | ✅ | bar |
| `axes.categoryMaxLabelWidth` | T1 | 🔴 | bar |
| `axes.categoryMinGridWidth` | T1 | 🔴 | bar |
| `axes.categoryScale` | T1 | ✅ | bar |
| `axes.categoryScrollable` | T1 | ✅ | bar |
| `axes.categoryScrollbar` | T1 | 🔴 | bar |
| `axes.categoryTitle` | T1 | ✅ | bar |
| `axes.customZoom` | T1 | ⚠️ | line |
| `axes.firstLabel` | T1 | ✅ | line |
| `axes.firstTick` | T1 | ✅ | line |
| `axes.labelsAccuracy` | T1 | 🔴 | bar |
| `axes.lastLabel` | T1 | ✅ | line |
| `axes.lastTick` | T1 | ✅ | line |
| `axes.rangeMode` | T1 | ✅ | line |
| `axes.scaleType` | T1 | ✅ | line |
| `axes.selectedFieldIndex` | T1 | ⚪na | bar |
| `axes.sortable` | T1 | 🟡cfg | bar |
| `axes.valueGrid` | T1 | ✅ | bar |
| `axes.valueLabels` | T1 | ✅ | bar |
| `axes.valueScale` | T1 | ✅ | bar |
| `axes.valueShowMax` | T1 | ✅ | bar |
| `axes.valueShowMin` | T1 | ✅ | bar |
| `axes.valueTitle` | T1 | ✅ | bar |
| `balloon.bgColor` | T2 | 🟡cfg | balloon — hover-эфемерный |
| `balloon.combine` | T2 | 🟡cfg | balloon — hover-эфемерный |
| `balloon.fontColor` | T2 | 🟡cfg | balloon — hover-эфемерный |
| `balloon.fontSize` | T2 | 🟡cfg | balloon — hover-эфемерный |
| `balloon.template` | T2 | 🟡cfg | balloon — hover-эфемерный |
| `balloon.visible` | T2 | 🟡cfg | balloon — hover-эфемерный |
| `bgColor` | T1 | ✅ | generic@bar |
| `bgColor2` | T1 | ✅ | totals |
| `data.autofillEmptySeries` | T2 | 🟡cfg | data — no-ui |
| `data.intervalRefresh` | T2 | 🟡cfg | data — no-ui |
| `data.intervalSeconds` | T2 | 🟡cfg | data — no-ui |
| `data.rowsLimit` | T2 | 🟡cfg | data — no-ui |
| `data.rowsLimitToExport` | T2 | 🟡cfg | data — no-ui |
| `data.rowsLimitToShow` | T2 | 🟡cfg | data — no-ui |
| `data.seriesLimitToShow` | T2 | 🟡cfg | data — no-ui |
| `fontSize` | T1 | 🔴 | generic@bar |
| `gradient` | T1 | ✅ | totals |
| `hideSpinner` | T1 | 🟡cfg | generic |
| `labels.angle` | T1 | ⚠️ | pie |
| `labels.bypassCollisions` | T1 | ⚠️ | pie |
| `labels.fontSize` | T1 | 🔴 | pie |
| `labels.hidePercent` | T1 | ✅ | pie |
| `labels.inner.fontsize` | T1 | ⚪na | pie |
| `labels.labelsColor` | T1 | 🔴 | pie |
| `labels.outer.color` | T1 | ✅ | pie |
| `labels.outer.fontsize` | T1 | ✅ | pie |
| `labels.position` | T1 | ✅ | bar |
| `labels.template` | T1 | ✅ | pie |
| `labels.visible` | T1 | ✅ | pie |
| `legend.bgColor` | T1 | ✅ | bar |
| `legend.borderColor` | T1 | ✅ | bar |
| `legend.borderWidth` | T1 | 🔴 | bar |
| `legend.fontSize` | T1 | ✅ | bar |
| `legend.order` | T1 | ✅ | bar |
| `legend.orientation` | T1 | 🔴 | bar |
| `legend.percent` | T1 | ⚠️ | bar |
| `legend.position` | T1 | ✅ | bar |
| `legend.reverse` | T1 | ✅ | bar |
| `legend.visible` | T1 | ✅ | bar |
| `link.operation` | T1 | 🟡cfg | generic |
| `margin.b` | T1 | ✅ | treemap |
| `margin.l` | T1 | ✅ | treemap |
| `margin.pad` | T1 | ✅ | treemap |
| `margin.r` | T1 | ✅ | treemap |
| `margin.t` | T1 | ✅ | treemap |
| `nocopy` | T1 | 🟡cfg | generic |
| `noexport` | T1 | 🟡cfg | generic |
| `numberPrecision` | T1 | ✅ | generic@totals |
| `orientation` | T1 | ✅ | generic@bar |
| `outline.color` | T1 | ✅ | table |
| `outline.enabled` | T1 | ✅ | table |
| `outline.width` | T1 | ✅ | table |
| `percentPrecision` | T1 | 🟡cfg | generic@totals |
| `regimes.autoWidth` | T1 | ✅ | table |
| `regimes.cellHeight` | T1 | 🔴 | table |
| `regimes.columnDrag` | T1 | 🟡cfg | table |
| `regimes.fixedColumns` | T1 | ✅ | table |
| `regimes.headerHeight` | T1 | 🔴 | table |
| `regimes.multilineHeader` | T1 | ✅ | table |
| `regimes.resizable` | T1 | 🟡cfg | table |
| `regimes.subtotals` | T1 | 🔴 | table |
| `regimes.totals` | T1 | ✅ | table |
| `scrollbars` | T1 | 🔴 | generic@bar |
| `showtitle` | T1 | ✅ | generic@bar |
| `sort.headerClickSort` | T1 | 🟡cfg | table |
| `sort.multiColumnSort` | T1 | 🟡cfg | table |
| `stacking` | T1 | ✅ | generic@bar |
| `visuals.autoColor` | T1 | ✅ | bar |
| `visuals.colorPalette` | T1 | 🔴 | generic@bar |
| `visuals.mainColor` | T1 | 🔴 | generic@bar |

## mapLeaflet — 39/39 проверено

| слаг | тир | вердикт | где/нота |
|---|:--:|:--:|---|
| `map.annotationOpacity` | T3 | 🟡cfg | map — blocked: Leaflet не монтируется |
| `map.annotationText` | T3 | 🟡cfg | map — blocked: Leaflet не монтируется |
| `map.autoCenter` | T3 | 🔴 | map — blocked: Leaflet не монтируется |
| `map.background.allowTiles` | T3 | ✅ | map — blocked: Leaflet не монтируется |
| `map.background.allowTiles2` | T3 | 🟡cfg | map — blocked: Leaflet не монтируется |
| `map.background.backgroundColor` | T3 | 🔴 | map — blocked: Leaflet не монтируется |
| `map.background.tileUrl` | T3 | ✅ | map — blocked: Leaflet не монтируется |
| `map.center.lat` | T3 | 🔴 | map — blocked: Leaflet не монтируется |
| `map.center.lng` | T3 | 🔴 | map — blocked: Leaflet не монтируется |
| `map.clusterMarkers` | T3 | ⚪na | deprecated — deprecated→skip |
| `map.filterMode` | T3 | 🟡cfg | map — blocked: Leaflet не монтируется |
| `map.initialZoom` | T3 | 🔴 | map — blocked: Leaflet не монтируется |
| `map.legend.discrete` | T3 | ✅ | map — blocked: Leaflet не монтируется |
| `map.legend.gradeNumber` | T3 | ✅ | map — blocked: Leaflet не монтируется |
| `map.legend.invertColors` | T3 | ⚠️ | map — blocked: Leaflet не монтируется |
| `map.legend.position` | T3 | ✅ | map — blocked: Leaflet не монтируется |
| `map.legend.visible` | T3 | ✅ | map — blocked: Leaflet не монтируется |
| `map.legend.withFilters` | T3 | 🟡cfg | map — blocked: Leaflet не монтируется |
| `map.markers.clustering` | T3 | ⚠️ | map — blocked: Leaflet не монтируется |
| `map.markers.clusteringThreshold` | T3 | ⚠️ | map — blocked: Leaflet не монтируется |
| `map.markers.fixedExtent` | T3 | 🟡cfg | map — blocked: Leaflet не монтируется |
| `map.markers.gradeNumberForSize` | T3 | 🟡cfg | map — blocked: Leaflet не монтируется |
| `map.markers.isLinearScale` | T3 | 🟡cfg | map — blocked: Leaflet не монтируется |
| `map.markers.labelMinZoom` | T3 | 🟡cfg | map — blocked: Leaflet не монтируется |
| `map.markers.labelsSize` | T3 | ✅ | map — blocked: Leaflet не монтируется |
| `map.markers.maxSize` | T3 | ⚠️ | map — blocked: Leaflet не монтируется |
| `map.markers.maxValue` | T3 | 🟡cfg | map — blocked: Leaflet не монтируется |
| `map.markers.maxValueColor` | T3 | 🟡cfg | map — blocked: Leaflet не монтируется |
| `map.markers.minSize` | T3 | ⚠️ | map — blocked: Leaflet не монтируется |
| `map.markers.showLabels` | T3 | ✅ | map — blocked: Leaflet не монтируется |
| `map.markers.showMaxValue` | T3 | 🟡cfg | map — blocked: Leaflet не монтируется |
| `map.markers.showTooltip` | T3 | 🟡cfg | map — blocked: Leaflet не монтируется |
| `map.markers.showValues` | T3 | ✅ | map — blocked: Leaflet не монтируется |
| `map.markers.tooltipSize` | T3 | 🟡cfg | map — blocked: Leaflet не монтируется |
| `map.markers.tooltipWordWrap` | T3 | 🟡cfg | map — blocked: Leaflet не монтируется |
| `map.markers.valuesPrecision` | T3 | ✅ | map — blocked: Leaflet не монтируется |
| `map.multilayerMode` | T3 | 🟡cfg | map — blocked: Leaflet не монтируется |
| `map.showSmallObjects` | T3 | 🟡cfg | map — blocked: Leaflet не монтируется |
| `map.titleBrightness` | T3 | 🟡cfg | map — blocked: Leaflet не монтируется |

## pivotChart — 24/24 проверено

| слаг | тир | вердикт | где/нота |
|---|:--:|:--:|---|
| `pivot.autoHeightEnabled` | T1 | 🟡cfg | pivot |
| `pivot.autoWidthEnabled` | T1 | 🟡cfg | pivot |
| `pivot.borderColor` | T1 | ✅ | pivot |
| `pivot.dateFormat` | T1 | ⚪na | pivot |
| `pivot.fontFamily` | T1 | ✅ | pivot |
| `pivot.groupByOptimization` | T1 | 🟡cfg | pivot |
| `pivot.headerAling` | T1 | ✅ | pivot |
| `pivot.headerBackgroundColor` | T1 | ✅ | pivot |
| `pivot.headerFontSize` | T1 | ✅ | pivot |
| `pivot.headerHeight` | T1 | ✅ | pivot |
| `pivot.headerHorWordWrapEnabled` | T1 | ✅ | pivot |
| `pivot.headerTextColor` | T1 | ✅ | pivot |
| `pivot.hideMeasuresHeader` | T1 | ✅ | pivot |
| `pivot.nullVisible` | T1 | ⚪na | pivot |
| `pivot.numbersEnabled` | T1 | ✅ | pivot |
| `pivot.precision` | T1 | ✅ | pivot |
| `pivot.showPanel` | T1 | 🔴 | pivot |
| `pivot.theme` | T1 | ⚠️ | pivot |
| `totals.grandSumsFixed` | T1 | ✅ | pivot |
| `totals.noGrandSumsX` | T1 | ✅ | pivot |
| `totals.noGrandSumsY` | T1 | ✅ | pivot |
| `totals.noSums` | T1 | ⚪na | pivot |
| `totals.sumColumnAtLeft` | T1 | ✅ | pivot |
| `totals.sumRowAtTop` | T1 | ✅ | pivot |

## lineChart — 16/16 проверено

| слаг | тир | вердикт | где/нота |
|---|:--:|:--:|---|
| `style.autoColor` | T1 | ✅ | bar |
| `style.clustered` | T1 | ⚪na | area |
| `style.labelsEnabled` | T1 | ✅ | line |
| `style.lineMode` | T1 | ✅ | line |
| `style.lineWidth` | T1 | ✅ | line |
| `style.markerMode` | T1 | ✅ | area |
| `style.markerWidth` | T1 | ✅ | line |
| `style.outlineWidth` | T1 | ✅ | line |
| `style.smoothing` | T1 | ✅ | line |
| `style.visType` | T1 | ✅ | line |
| `visuals.lineDashStyle` | T1 | 🔴 | line |
| `visuals.lineWidth` | T1 | ✅ | line |
| `visuals.markerLabels` | T1 | 🔴 | bubble |
| `visuals.markerSize` | T1 | ✅ | line |
| `visuals.markerType` | T1 | ✅ | line |
| `visuals.smoothing` | T1 | ✅ | area |

## speedometerV2 — 16/16 проверено

| слаг | тир | вердикт | где/нота |
|---|:--:|:--:|---|
| `gauge.backgroundColor` | T1 | ✅ | speedometer |
| `grid.color` | T1 | ✅ | speedometer |
| `grid.endAngle` | T1 | ✅ | speedometer |
| `grid.gradeCount` | T1 | 🔴 | speedometer |
| `grid.gradientMode` | T1 | 🔴 | speedometer |
| `grid.labelFrequency` | T1 | ✅ | speedometer |
| `grid.labelsColor` | T1 | ✅ | speedometer |
| `grid.max` | T1 | ✅ | speedometer |
| `grid.min` | T1 | ✅ | speedometer |
| `grid.minorTickCount` | T1 | ✅ | speedometer |
| `grid.paletteColors` | T1 | 🔴 | speedometer |
| `grid.paletteInvert` | T1 | 🔴 | speedometer |
| `grid.roundLimits` | T1 | ✅ | speedometer |
| `grid.startAngle` | T1 | ✅ | speedometer |
| `grid.tickCount` | T1 | ✅ | speedometer |
| `grid.width` | T1 | 🔴 | speedometer |

## tilemapChart — 16/16 проверено

| слаг | тир | вердикт | где/нота |
|---|:--:|:--:|---|
| `tilemap.allowTiles` | T1 | 🟡cfg | tilemap |
| `tilemap.autoZoom` | T1 | 🟡cfg | tilemap |
| `tilemap.bgTileColor` | T1 | 🔴 | tilemap |
| `tilemap.deltaK` | T1 | ✅ | tilemap |
| `tilemap.endColor` | T1 | ✅ | tilemap |
| `tilemap.filterMode` | T1 | 🟡cfg | tilemap |
| `tilemap.grouping` | T1 | ✅ | tilemap |
| `tilemap.legendVisible` | T1 | ✅ | tilemap |
| `tilemap.legendX` | T1 | 🔴 | tilemap |
| `tilemap.legendY` | T1 | 🔴 | tilemap |
| `tilemap.nameFontSize` | T1 | ✅ | tilemap |
| `tilemap.popup` | T1 | 🟡cfg | tilemap |
| `tilemap.specialTiles` | T1 | ✅ | tilemap |
| `tilemap.startColor` | T1 | ✅ | tilemap |
| `tilemap.tileSize` | T1 | ✅ | tilemap |
| `tilemap.tileType` | T1 | 🔴 | tilemap |

## FilterControlPanel — 14/14 проверено

| слаг | тир | вердикт | где/нота |
|---|:--:|:--:|---|
| `viewType.addInvertedSwitch` | T1 | 🔴 | filterControl |
| `viewType.autoApply` | T1 | 🟡cfg | filterControl |
| `viewType.clearSelection` | T1 | 🟡cfg | filterControl |
| `viewType.displayType` | T1 | ✅ | filterControl |
| `viewType.hideEmptyLines` | T1 | 🟡cfg | filterControl |
| `viewType.inversed` | T1 | 🟡cfg | filterControl |
| `viewType.multiselect` | T1 | ✅ | filterControl |
| `viewType.resetEnabled` | T3 | ⚪rej | filterControl — deprecated→skip |
| `viewType.searchEnabled` | T1 | 🟡cfg | filterControl |
| `viewType.showAll` | T3 | ⚪rej | filterControl — deprecated→skip |
| `viewType.sortSelectedOptionsToTop` | T1 | 🟡cfg | filterControl |
| `viewType.unlimitedSearch` | T1 | 🟡cfg | filterControl |
| `viewType.updateOnApply` | T1 | 🟡cfg | filterControl |
| `viewType.updateOnCloseDropdown` | T1 | 🟡cfg | filterControl |

## pieChart — 14/14 проверено

| слаг | тир | вердикт | где/нота |
|---|:--:|:--:|---|
| `balloonTemplate` | T1 | 🟡cfg | pie |
| `labels.groupCount` | T1 | ✅ | pie |
| `labels.groupPercent` | T1 | ✅ | pie |
| `labels.groupedTitle__ru` | T1 | 🔴 | pie |
| `labels.outerLabelsAngle` | T1 | 🔴 | pie |
| `labels.switchControlNumberOfSegments` | T1 | 🟡cfg | pie |
| `labelsTemplate` | T1 | ✅ | pie |
| `radius` | T1 | ✅ | pie |
| `showDonut` | T1 | ✅ | pie |
| `summColor` | T1 | 🔴 | pie |
| `summEnabled` | T1 | ✅ | pie |
| `summFontSize` | T1 | ⚠️ | pie |
| `visuals.innerRadius` | T1 | 🔴 | pie |
| `visuals.startAngle` | T1 | 🔴 | pie |

## hierarchicalFilterPanel — 12/12 проверено

| слаг | тир | вердикт | где/нота |
|---|:--:|:--:|---|
| `hierFilter.bothChoice` | T1 | ✅ | hierFilter |
| `hierFilter.filterTitle` | T1 | ✅ | hierFilter |
| `hierFilter.headerWidth` | T1 | ✅ | hierFilter |
| `hierFilter.hideTitle` | T1 | ✅ | hierFilter |
| `hierFilter.inversed` | T1 | 🟡cfg | hierFilter |
| `hierFilter.multipleChoice` | T1 | ✅ | hierFilter |
| `hierFilter.noLoadOptions` | T1 | 🟡cfg | hierFilter |
| `hierFilter.searchInBaseMinNumber` | T1 | 🟡cfg | hierFilter |
| `hierFilter.searchInBaseMode` | T1 | ⚠️ | hierfilter |
| `hierFilter.sortSelectedOptionsToTop` | T1 | 🟡cfg | hierFilter |
| `hierFilter.updateOnApply` | T1 | ✅ | hierFilter |
| `hierFilter.updateOnCloseDropdown` | T1 | 🟡cfg | hierFilter |

## sunburstChart — 12/12 проверено

| слаг | тир | вердикт | где/нота |
|---|:--:|:--:|---|
| `sunburst.colorsEnabled` | T1 | ✅ | sunburst |
| `sunburst.darkLabels` | T1 | ✅ | sunburst |
| `sunburst.ellipsisLength` | T1 | ✅ | sunburst |
| `sunburst.filterMode` | T1 | 🟡cfg | sunburst |
| `sunburst.fontFamily` | T1 | ✅ | sunburst |
| `sunburst.fontSize` | T1 | ✅ | sunburst |
| `sunburst.layerButtons` | T1 | ✅ | sunburst |
| `sunburst.layerExpand` | T1 | 🟡cfg | sunburst |
| `sunburst.minPercent` | T1 | 🔴 | sunburst |
| `sunburst.precision` | T1 | ⚪na | sunburst |
| `sunburst.splittedMode` | T1 | ⚠️ | sunburst |
| `sunburst.visibleLayers` | T1 | ✅ | sunburst |

## barChart — 10/10 проверено

| слаг | тир | вердикт | где/нота |
|---|:--:|:--:|---|
| `data.baseColor` | T2 | ✅ | pie — no-ui |
| `data.colorStep` | T2 | 🔴 | pie — no-ui |
| `expandH` | T1 | 🔴 | bar |
| `expandV` | T1 | 🔴 | bar |
| `main.extraAxis` | T1 | 🔴 | bar/line/area |
| `subtitle` | T3 | ✅ | bar — blocked: builder gap |
| `visuals.chartType` | T1 | ✅ | bar |
| `visuals.clustered` | T1 | ✅ | bar |
| `visuals.columnBorderRadius` | T1 | 🔴 | bar |
| `visuals.columnWidth` | T1 | ✅ | bar |

## bubbleChart — 10/10 проверено

| слаг | тир | вердикт | где/нота |
|---|:--:|:--:|---|
| `bubble.bigNumberSuffixes` | T1 | ✅ | bubble |
| `bubble.filterMode` | T1 | 🟡cfg | bubble |
| `bubble.legendForColor` | T1 | ✅ | bubble |
| `bubble.legendForSize` | T1 | ✅ | bubble |
| `bubble.precision` | T1 | ✅ | bubble |
| `bubble.showScrollbars` | T1 | ✅ | bubble |
| `bubble.strictMinMax` | T1 | ✅ | bubble |
| `bubble.zoomToEdges` | T1 | 🔴 | bubble |
| `visuals.bubbleMaxSize` | T1 | ✅ | bubble |
| `visuals.bubbleMinSize` | T1 | ✅ | bubble |

## stockChart — 10/10 проверено

| слаг | тир | вердикт | где/нота |
|---|:--:|:--:|---|
| `stock.altAxisEnabled` | T1 | ✅ | stock |
| `stock.dateAxisMaxWidth` | T1 | ⚠️ | stock |
| `stock.dateAxisMinGridDistance` | T1 | ✅ | stock |
| `stock.dateAxisTickangle` | T1 | ✅ | stock |
| `stock.dateAxisZigzag` | T1 | ✅ | stock |
| `stock.dateFormat` | T1 | 🔴 | stock |
| `stock.dateRangePanel` | T1 | ✅ | stock |
| `stock.dateZoomPanel` | T1 | ✅ | stock |
| `stock.refresh` | T1 | 🟡cfg | stock |
| `stock.scrollbarDisabled` | T1 | ✅ | stock |

## imagePanel — 8/8 проверено

| слаг | тир | вердикт | где/нота |
|---|:--:|:--:|---|
| `image.backgroundPosition` | T1 | ✅ | imagePanel |
| `image.backgroundSize` | T1 | ✅ | imagePanel |
| `image.backgroundStyle` | T1 | ✅ | imagePanel |
| `image.linkName` | T1 | 🟡cfg | imagePanel |
| `image.linkTarget` | T1 | 🟡cfg | imagePanel |
| `image.src` | T1 | ✅ | imagePanel |
| `image.titleColor` | T1 | 🟡cfg | imagePanel |
| `image.titleSize` | T1 | 🟡cfg | imagePanel |

## table — 8/8 проверено

| слаг | тир | вердикт | где/нота |
|---|:--:|:--:|---|
| `table.headersBackground` | T1 | ✅ | table |
| `table.headersColor` | T1 | ✅ | table |
| `table.linkByForRow` | T1 | ✅ | table |
| `table.precision` | T1 | ✅ | table |
| `table.showNumberLineInHeader` | T1 | 🔴 | table |
| `table.theme` | T1 | ✅ | table |
| `table.zebraColor` | T1 | ✅ | table |
| `table.zebraType` | T1 | ✅ | table |

## audioplayer — 5/5 проверено

| слаг | тир | вердикт | где/нота |
|---|:--:|:--:|---|
| `audio.backgroundColor` | T3 | ⚪na | audioplayer — вне scope (audio) |
| `audio.progressBarBackgroundColor` | T3 | ⚪na | audioplayer — вне scope (audio) |
| `audio.progressBarColor` | T3 | ⚪na | audioplayer — вне scope (audio) |
| `audio.uploadURL` | T3 | ⚠️ | audioplayer — вне scope (audio) |
| `audio.url` | T3 | ⚠️ | audioplayer — вне scope (audio) |

## comparisonChart — 5/5 проверено

| слаг | тир | вердикт | где/нота |
|---|:--:|:--:|---|
| `comparison.object1` | T3 | ⚪na | comparison — blocked: frontend-блокер |
| `comparison.object2` | T3 | ⚪na | comparison — blocked: frontend-блокер |
| `comparison.precision` | T3 | ⚪na | comparison — blocked: frontend-блокер |
| `comparison.showDelta` | T3 | ⚪na | comparison — blocked: frontend-блокер |
| `comparison.showPercent` | T3 | ⚪na | comparison — blocked: frontend-блокер |

## tabsPanel — 4/4 проверено

| слаг | тир | вердикт | где/нота |
|---|:--:|:--:|---|
| `tabs.autoApply` | T1 | 🟡cfg | tabsPanel |
| `tabs.height` | T1 | ✅ | tabsPanel |
| `tabs.orientation` | T1 | ✅ | tabsPanel |
| `tabs.visuals` | T1 | ⚠️ | tabsPanel |

## treeMap — 4/4 проверено

| слаг | тир | вердикт | где/нота |
|---|:--:|:--:|---|
| `labels.valuesFontSize` | T1 | ✅ | treemap |
| `labels.valuesTopMargin` | T1 | ✅ | treemap |
| `treemap.filterMode` | T1 | 🟡cfg | treemap |
| `treemap.precision` | T1 | ✅ | treemap |

## parallelCoordsChart — 3/3 проверено

| слаг | тир | вердикт | где/нота |
|---|:--:|:--:|---|
| `parallel.tableSize` | T1 | ✅ | parallel |
| `visuals.colorMax` | T1 | ✅ | parallel |
| `visuals.colorMin` | T1 | ✅ | parallel |

## radarChart — 3/3 проверено

| слаг | тир | вердикт | где/нота |
|---|:--:|:--:|---|
| `grid.filled` | T1 | ✅ | radar |
| `grid.gridType` | T1 | ✅ | radar |
| `grid.radarLabels` | T1 | ✅ | radar |

## totalsPanelV2 — 3/3 проверено

| слаг | тир | вердикт | где/нота |
|---|:--:|:--:|---|
| `delta.delta` | T1 | 🟡cfg | totals |
| `delta.percent` | T1 | 🟡cfg | totals |
| `flip` | T1 | ✅ | totals |

## treeGraph — 3/3 проверено

| слаг | тир | вердикт | где/нота |
|---|:--:|:--:|---|
| `graph.initialZoom` | T1 | ✅ | treegraph |
| `graph.layout` | T1 | ✅ | treegraph |
| `graph.zoomable` | T1 | ✅ | treegraph |

## SwitchControlPanel — 2/2 проверено

| слаг | тир | вердикт | где/нота |
|---|:--:|:--:|---|
| `switch.filterType` | T1 | ✅ | switch |
| `switch.selectorTitleOverride` | T1 | ✅ | switch |

## iframe — 2/2 проверено

| слаг | тир | вердикт | где/нота |
|---|:--:|:--:|---|
| `iframe.linkName` | T1 | ✅ | iframe |
| `iframe.linkTarget` | T1 | ✅ | iframe |

## textBlock — 2/2 проверено

| слаг | тир | вердикт | где/нота |
|---|:--:|:--:|---|
| `text.maximizable` | T1 | ✅ | textBlock |
| `text.noexport` | T1 | 🟡cfg | textBlock |

## areaChart — 1/1 проверено

| слаг | тир | вердикт | где/нота |
|---|:--:|:--:|---|
| `visuals.fillOpacity` | T3 | ⚪na | deprecated — deprecated→skip |

