# SLUG_REFERENCE — справочник config_overrides

> **Генерируется из `app/tools/config_schema.py` (SLUG_SCHEMA)** — единственный источник истины.
> Регенерация: `python3 scripts/gen_slug_reference.py`.
> Слагов: **365** (+ анкерные `visuals.{anchor}.{prop}`, колоночные `columns.{field}.{prop}`, правила `rules.{n}.{prop}`).

Колонки: **json_path** — фактический путь записи в config (пусто = top-level/секционный handler);
**applies_to** — internal-типы (пусто = все); ⚠️ = deprecated (мёртвый фронт-ключ, см. подсказку).

См. также: единый справочник-соответствие **UI-контрол ↔ MCP-слаг ↔ JSON-путь** — [README.md](README.md); устаревшие имена — [aliases.md](aliases.md); что такое слаги — [концепция](../../concepts/components-json-slugs.md).

## (top-level)

| Слаг | Тип | Default | json_path | applies_to | Прим. |
|---|---|---|---|---|---|
| `balloonTemplate` | str | `None` | `` | pieChart |  |
| `bgColor` | color | `rgba(255,255,255,1)` | `` | все |  |
| `bgColor2` | color | `None` | `` | все |  |
| `expandH` | bool | `False` | `` | barChart, lineChart, areaChart, pieChart, stockChart |  |
| `expandV` | bool | `False` | `` | barChart, lineChart, areaChart, pieChart, stockChart |  |
| `flip` | bool | `False` | `` | totalsPanelV2 |  |
| `fontSize` | int [6..72] | `12` | `` | все |  |
| `gradient` | bool | `False` | `` | все |  |
| `gradientDirection` | int [-180..180] | `0` | `gradientDirection` | totalsPanelV2 |  |
| `hideSpinner` | bool | `False` | `` | все |  |
| `labelsTemplate` | str | `[[percents]]%` | `` | pieChart |  |
| `nocopy` | bool | `False` | `` | все |  |
| `noexport` | bool | `False` | `` | все |  |
| `numberPrecision` | int [-1..10] | `-1` | `` | все |  |
| `orientation` | enum: v/h | `v` | `` | все |  |
| `percentPrecision` | int [0..10] | `2` | `` | все |  |
| `radius` | int [0..100] | `80` | `` | pieChart, radarChart |  |
| `scrollbars` | bool | `False` | `` | все |  |
| `showDonut` | bool | `False` | `` | pieChart |  |
| `showtitle` | bool | `True` | `` | все |  |
| `stacking` | enum: none/normal/percent | `none` | `` | все |  |
| `subtitle` | str | `` | `` | barChart, lineChart, pieChart, stockChart, sunburstChart, parallelCoordsChart, treeGraph, treeMap, totalsPanelV2, subheader, table |  |
| `summColor` | color | `rgba(0,0,0,1)` | `` | pieChart |  |
| `summEnabled` | bool | `False` | `` | pieChart |  |
| `summFontSize` | int [8..72] | `32` | `` | pieChart |  |
| `textAlign` | enum: left/center/right | `center` | `textAlign` | totalsPanelV2 |  |
| `truncateTitle` | bool | `False` | `truncateTitle` | totalsPanelV2 |  |

## audio

| Слаг | Тип | Default | json_path | applies_to | Прим. |
|---|---|---|---|---|---|
| `audio.backgroundColor` | color | `` | `` | audioplayer |  |
| `audio.progressBarBackgroundColor` | color | `` | `` | audioplayer |  |
| `audio.progressBarColor` | color | `rgba(0, 139, 139, 1)` | `` | audioplayer |  |
| `audio.uploadURL` | str | `None` | `resource.uploadURL` | audioplayer |  |
| `audio.url` | str | `None` | `resource.url` | audioplayer |  |

## axes

| Слаг | Тип | Default | json_path | applies_to | Прим. |
|---|---|---|---|---|---|
| `axes.autoZoom` | bool | `False` | `axes[values].autoZoom` | все |  |
| `axes.categoryGrid` | bool | `False` | `axes[categories].showgrid` | все |  |
| `axes.categoryLabelAngle` | int [-90..90] | `0` | `axes[categories].tickangle` | все |  |
| `axes.categoryLabels` | bool | `True` | `axes[categories].showlabels` | все |  |
| `axes.categoryMaxLabelWidth` | int [0..500] | `0` | `axes[categories].maxLabelWidth` | все |  |
| `axes.categoryMinGridWidth` | int [0..500] | `0` | `axes[categories].minGridWidth` | все |  |
| `axes.categoryScale` | bool | `True` | `axes[categories].showscale` | все |  |
| `axes.categoryScrollable` | bool | `False` | `axes[categories].scrollable` | все |  |
| `axes.categoryScrollbar` | bool | `False` | `axes[categories].fixedZoom` | все |  |
| `axes.categoryTitle` | bool | `False` | `axes[categories].showtitle` | все |  |
| `axes.customZoom` | bool | `False` | `axes[categories].customZoom` | все |  |
| `axes.firstLabel` | bool | `True` | `axes[values].showFirstLabel` | все |  |
| `axes.firstTick` | bool | `True` | `axes[values].showFirstTick` | все |  |
| `axes.labelsAccuracy` | int [0..10] | `2` | `axes[values].labelsAccuracy` | все |  |
| `axes.lastLabel` | bool | `True` | `axes[values].showLastLabel` | все |  |
| `axes.lastTick` | bool | `True` | `axes[values].showLastTick` | все |  |
| `axes.rangeMode` | enum: normal/tozero/tomin/tomax | `normal` | `axes[values].rangeMode` | все |  |
| `axes.scaleType` | enum: -/linear/log | `-` | `axes[values].scaleType` | все |  |
| `axes.selectedFieldIndex` | int [-2..20] | `-2` | `axes[values].selectedFieldIndex` | все |  |
| `axes.sortable` | bool | `True` | `axes[values].sortable` | все |  |
| `axes.valueGrid` | bool | `False` | `axes[values].showgrid` | все |  |
| `axes.valueLabels` | bool | `True` | `axes[values].showlabels` | все |  |
| `axes.valueScale` | bool | `True` | `axes[values].showscale` | все |  |
| `axes.valueShowMax` | bool | `False` | `axes[values].showMax` | все |  |
| `axes.valueShowMin` | bool | `False` | `axes[values].showMin` | все |  |
| `axes.valueTitle` | bool | `False` | `axes[values].showtitle` | все |  |

## balloon

| Слаг | Тип | Default | json_path | applies_to | Прим. |
|---|---|---|---|---|---|
| `balloon.bgColor` | color | `None` | `balloon.bgcolor` | все |  |
| `balloon.combine` | bool | `False` | `balloon.allSeriesPop` | все | значение ИНВЕРТИРУЕТСЯ |
| `balloon.fontColor` | color | `None` | `balloon.color` | все |  |
| `balloon.fontSize` | int [6..40] | `12` | `balloon.fontsize` | все |  |
| `balloon.template` | str | `None` | `balloonTemplate` | все |  |
| `balloon.visible` | bool | `True` | `` | все |  |

## bubble

| Слаг | Тип | Default | json_path | applies_to | Прим. |
|---|---|---|---|---|---|
| `bubble.bigNumberSuffixes` | any | `[]` | `bigNumberSuffixes` | bubbleChart |  |
| `bubble.filterMode` | bool | `True` | `filterMode` | bubbleChart |  |
| `bubble.legendForColor` | bool | `False` | `legendForColor.enabled` | bubbleChart |  |
| `bubble.legendForSize` | bool | `False` | `legendForSize.enabled` | bubbleChart |  |
| `bubble.precision` | int [-1..10] | `-1` | `precision` | bubbleChart |  |
| `bubble.showScrollbars` | bool | `True` | `hideScrollbars` | bubbleChart | значение ИНВЕРТИРУЕТСЯ |
| `bubble.strictMinMax` | bool | `False` | `strictMinMaxEnabled` | bubbleChart |  |
| `bubble.zoomToEdges` | bool | `False` | `zoomToBubbleEdges` | bubbleChart |  |

## comparison

| Слаг | Тип | Default | json_path | applies_to | Прим. |
|---|---|---|---|---|---|
| `comparison.object1` | str | `` | `` | comparisonChart |  |
| `comparison.object2` | str | `` | `` | comparisonChart |  |
| `comparison.precision` | int [-1..5] | `-1` | `` | comparisonChart |  |
| `comparison.showDelta` | bool | `False` | `` | comparisonChart |  |
| `comparison.showPercent` | bool | `False` | `` | comparisonChart |  |

## data

| Слаг | Тип | Default | json_path | applies_to | Прим. |
|---|---|---|---|---|---|
| `data.autofillEmptySeries` | bool | `False` | `series.autoFill` | все |  |
| `data.baseColor` | color | `None` | `` | barChart, pieChart |  |
| `data.colorStep` | int [-20..20] | `0` | `` | barChart, pieChart |  |
| `data.intervalRefresh` | bool | `False` | `refresh` | все |  |
| `data.intervalSeconds` | int [0..600] | `60` | `refreshTime` | все |  |
| `data.rowsLimit` | int [0..1000000] | `5000` | `rowsLimit` | все |  |
| `data.rowsLimitToExport` | int [0..1000000] | `0` | `rowsLimitToExport` | все |  |
| `data.rowsLimitToShow` | int [0..1000000] | `0` | `rowsLimitToShow` | все |  |
| `data.seriesLimitToShow` | int [0..1000] | `0` | `seriesLimitToShow` | все |  |

## delta

| Слаг | Тип | Default | json_path | applies_to | Прим. |
|---|---|---|---|---|---|
| `delta.delta` | bool | `False` | `visuals[trend].hasTarget` | totalsPanelV2 |  |
| `delta.percent` | bool | `False` | `visuals[trend].absolute (inverted)` | totalsPanelV2 |  |

## gauge

| Слаг | Тип | Default | json_path | applies_to | Прим. |
|---|---|---|---|---|---|
| `gauge.backgroundColor` | color | `None` | `backgroundColor` | speedometerV2 |  |

## graph

| Слаг | Тип | Default | json_path | applies_to | Прим. |
|---|---|---|---|---|---|
| `graph.initialZoom` | float [0.01..5.0] | `0.7` | `` | treeGraph |  |
| `graph.layout` | enum: TreeLayout/ForceDirectedLayout | `TreeLayout` | `` | treeGraph |  |
| `graph.zoomable` | bool | `True` | `` | treeGraph |  |

## grid

| Слаг | Тип | Default | json_path | applies_to | Прим. |
|---|---|---|---|---|---|
| `grid.color` | color | `None` | `` | speedometerV2 |  |
| `grid.endAngle` | int [0..360] | `360` | `endAngle` | speedometerV2 |  |
| `grid.filled` | bool | `True` | `filled` | radarChart |  |
| `grid.gradeCount` | int [0..20] | `3` | `grid.palette.gradeCount` | speedometerV2 |  |
| `grid.gradientMode` | bool | `False` | `grid.palette.gradientMode` | speedometerV2 |  |
| `grid.gridType` | enum: circles/polygons | `circles` | `axes[values].gridType` | radarChart |  |
| `grid.labelFrequency` | int [0..10] | `1` | `` | speedometerV2 |  |
| `grid.labelsColor` | color | `None` | `` | speedometerV2 |  |
| `grid.max` | float | `100` | `grid.maximum` | speedometerV2 |  |
| `grid.min` | float | `0` | `grid.minimum` | speedometerV2 |  |
| `grid.minorTickCount` | int [0..10] | `2` | `` | speedometerV2 |  |
| `grid.paletteColors` | any | `None` | `grid.palette.colors` | speedometerV2 |  |
| `grid.paletteInvert` | bool | `False` | `grid.palette.invert` | speedometerV2 |  |
| `grid.radarLabels` | bool | `True` | `axes[values].radarlabels` | radarChart |  |
| `grid.roundLimits` | bool | `False` | `roundLimits` | speedometerV2 |  |
| `grid.startAngle` | int [0..360] | `0` | `startAngle` | speedometerV2 |  |
| `grid.tickCount` | int [0..100] | `5` | `` | speedometerV2 |  |
| `grid.width` | int [1..100] | `20` | `` | speedometerV2 |  |

## hierFilter

| Слаг | Тип | Default | json_path | applies_to | Прим. |
|---|---|---|---|---|---|
| `hierFilter.bothChoice` | bool | `True` | `` | hierarchicalFilterPanel |  |
| `hierFilter.filterTitle` | str | `` | `` | hierarchicalFilterPanel |  |
| `hierFilter.headerWidth` | int [0..100] | `0` | `` | hierarchicalFilterPanel |  |
| `hierFilter.hideTitle` | bool | `False` | `` | hierarchicalFilterPanel |  |
| `hierFilter.inversed` | bool | `False` | `` | hierarchicalFilterPanel |  |
| `hierFilter.multipleChoice` | bool | `True` | `` | hierarchicalFilterPanel |  |
| `hierFilter.noLoadOptions` | bool | `True` | `` | hierarchicalFilterPanel |  |
| `hierFilter.searchInBaseMinNumber` | int [1..10] | `1` | `` | hierarchicalFilterPanel |  |
| `hierFilter.searchInBaseMode` | bool | `False` | `` | hierarchicalFilterPanel |  |
| `hierFilter.sortSelectedOptionsToTop` | bool | `False` | `` | hierarchicalFilterPanel |  |
| `hierFilter.updateOnApply` | bool | `False` | `` | hierarchicalFilterPanel |  |
| `hierFilter.updateOnCloseDropdown` | bool | `True` | `` | hierarchicalFilterPanel |  |

## iframe

| Слаг | Тип | Default | json_path | applies_to | Прим. |
|---|---|---|---|---|---|
| `iframe.linkName` | str | `` | `link.name` | iframe |  |
| `iframe.linkTarget` | enum: _self/_blank | `_self` | `link.target` | iframe |  |

## image

| Слаг | Тип | Default | json_path | applies_to | Прим. |
|---|---|---|---|---|---|
| `image.backgroundPosition` | enum: left top/center top/right top/left center/center center/right center/left bottom/center bottom/right bottom | `center center` | `` | imagePanel |  |
| `image.backgroundSize` | enum: contain/cover/initial/100% auto/auto 100%/100% 100% | `contain` | `` | imagePanel |  |
| `image.backgroundStyle` | enum: no-repeat/repeat-x/repeat-y/repeat | `no-repeat` | `` | imagePanel |  |
| `image.linkName` | str | `` | `link.name` | imagePanel |  |
| `image.linkTarget` | enum: _self/_blank | `_self` | `link.target` | imagePanel |  |
| `image.src` | any | `None` | `image` | imagePanel |  |
| `image.titleColor` | color | `` | `` | imagePanel |  |
| `image.titleSize` | str | `` | `` | imagePanel |  |

## labels

| Слаг | Тип | Default | json_path | applies_to | Прим. |
|---|---|---|---|---|---|
| `labels.angle` | int [-90..90] | `0` | `` | все |  |
| `labels.bypassCollisions` | bool | `False` | `bypassCheckCollisions` | все |  |
| `labels.fontSize` | int [6..40] | `12` | `labels.inner.fontsize` | все |  |
| `labels.groupCount` | int [0..100] | `9` | `` | pieChart |  |
| `labels.groupPercent` | float [0..5] | `0.5` | `` | pieChart |  |
| `labels.groupedTitle__ru` | str | `None` | `` | pieChart |  |
| `labels.hidePercent` | float [0..5] | `0` | `` | все |  |
| `labels.inner.fontsize` | int [6..40] | `12` | `` | все |  |
| `labels.labelsColor` | color | `None` | `labels.inner.color` | все |  |
| `labels.outer.color` | color | `rgba(68,68,68,1)` | `` | все |  |
| `labels.outer.fontsize` | int [6..40] | `12` | `` | все |  |
| `labels.outerLabelsAngle` | int [-90..90] | `0` | `` | pieChart |  |
| `labels.position` | enum: auto/inside/outside | `auto` | `` | все |  |
| `labels.switchControlNumberOfSegments` | bool | `False` | `` | pieChart |  |
| `labels.template` | str | `None` | `` | все |  |
| `labels.valuesFontSize` | int [6..72] | `12` | `labels.value.fontsize` | treeMap |  |
| `labels.valuesTopMargin` | int [0..50] | `5` | `labels.value.topMargin` | treeMap |  |
| `labels.visible` | bool | `False` | `` | все |  |

## legend

| Слаг | Тип | Default | json_path | applies_to | Прим. |
|---|---|---|---|---|---|
| `legend.bgColor` | color | `None` | `` | все |  |
| `legend.borderColor` | color | `None` | `` | все |  |
| `legend.borderWidth` | int [0..5] | `0` | `` | все |  |
| `legend.fontSize` | int [6..40] | `12` | `` | все |  |
| `legend.order` | enum: normal/reversed | `normal` | `` | все |  |
| `legend.orientation` | enum: h/v | `h` | `` | все |  |
| `legend.percent` | bool | `False` | `` | все |  |
| `legend.position` | enum: auto/top-center/bottom-center/middle-left/middle-right/top-left/top-right/bottom-left/bottom-right | `auto` | `` | все |  |
| `legend.reverse` | bool | `False` | `` | все |  |
| `legend.visible` | bool | `True` | `` | все |  |

## link

| Слаг | Тип | Default | json_path | applies_to | Прим. |
|---|---|---|---|---|---|
| `link.operation` | str | `None` | `` | все |  |

## main

| Слаг | Тип | Default | json_path | applies_to | Прим. |
|---|---|---|---|---|---|
| `main.extraAxis` | bool | `False` | `` | barChart, lineChart, areaChart |  |

## map

| Слаг | Тип | Default | json_path | applies_to | Прим. |
|---|---|---|---|---|---|
| `map.annotationOpacity` | float [0.0..1.0] | `0.8` | `annotationOpacity` | mapLeaflet |  |
| `map.annotationText` | str | `` | `annotation` | mapLeaflet |  |
| `map.autoCenter` | bool | `True` | `` | mapLeaflet |  |
| `map.background.allowTiles` | bool | `True` | `` | mapLeaflet |  |
| `map.background.allowTiles2` | bool | `False` | `` | mapLeaflet |  |
| `map.background.backgroundColor` | color | `gray` | `` | mapLeaflet |  |
| `map.background.tileUrl` | str | `{s}.tile.osm.org/{z}/{x}/{y}.png` | `` | mapLeaflet |  |
| `map.center.lat` | float [-90.0..90.0] | `55.751` | `` | mapLeaflet |  |
| `map.center.lng` | float [-180.0..180.0] | `37.618` | `` | mapLeaflet |  |
| `map.clusterMarkers` | bool | `False` | `clusterMarkers` | mapLeaflet | ⚠️ DEPRECATED: кластеризация = map.markers.clustering (clusterizationOff) |
| `map.filterMode` | bool | `False` | `` | mapLeaflet |  |
| `map.initialZoom` | int [1..18] | `5` | `initialZoom` | mapLeaflet |  |
| `map.legend.discrete` | bool | `False` | `` | mapLeaflet |  |
| `map.legend.gradeNumber` | int [2..20] | `5` | `` | mapLeaflet |  |
| `map.legend.invertColors` | bool | `False` | `` | mapLeaflet |  |
| `map.legend.position` | enum: bottomright/topright/topleft/bottomleft | `bottomright` | `` | mapLeaflet |  |
| `map.legend.visible` | bool | `True` | `` | mapLeaflet |  |
| `map.legend.withFilters` | bool | `False` | `` | mapLeaflet |  |
| `map.markers.clustering` | bool | `False` | `markers.clusterizationOff` | mapLeaflet | значение ИНВЕРТИРУЕТСЯ |
| `map.markers.clusteringThreshold` | int [10..200] | `50` | `markers.clusterizationSize` | mapLeaflet |  |
| `map.markers.fixedExtent` | bool | `False` | `` | mapLeaflet |  |
| `map.markers.gradeNumberForSize` | int [1..10] | `3` | `` | mapLeaflet |  |
| `map.markers.isLinearScale` | bool | `False` | `` | mapLeaflet |  |
| `map.markers.labelMinZoom` | int [0..18] | `0` | `markers.minZoomLevel` | mapLeaflet |  |
| `map.markers.labelsSize` | int [8..24] | `12` | `` | mapLeaflet |  |
| `map.markers.maxSize` | int [0..100] | `50` | `` | mapLeaflet |  |
| `map.markers.maxValue` | float | `100.0` | `` | mapLeaflet |  |
| `map.markers.maxValueColor` | color | `red` | `` | mapLeaflet |  |
| `map.markers.minSize` | int [0..50] | `0` | `` | mapLeaflet |  |
| `map.markers.showLabels` | bool | `True` | `` | mapLeaflet |  |
| `map.markers.showMaxValue` | bool | `False` | `markers.maxValueShow` | mapLeaflet |  |
| `map.markers.showTooltip` | bool | `True` | `` | mapLeaflet |  |
| `map.markers.showValues` | bool | `False` | `` | mapLeaflet |  |
| `map.markers.tooltipSize` | int [8..40] | `12` | `markers.tooltipTextSize` | mapLeaflet |  |
| `map.markers.tooltipWordWrap` | bool | `False` | `markers.lineWrap` | mapLeaflet |  |
| `map.markers.valuesPrecision` | int [-1..10] | `-1` | `` | mapLeaflet |  |
| `map.multilayerMode` | bool | `False` | `` | mapLeaflet |  |
| `map.showSmallObjects` | bool | `False` | `` | mapLeaflet |  |
| `map.titleBrightness` | float [0.0..1.0] | `0.8` | `titleOpacity` | mapLeaflet |  |

## margin

| Слаг | Тип | Default | json_path | applies_to | Прим. |
|---|---|---|---|---|---|
| `margin.b` | int [0..100] | `5` | `` | все |  |
| `margin.l` | int [0..100] | `5` | `` | все |  |
| `margin.pad` | int [0..50] | `0` | `` | все |  |
| `margin.r` | int [0..100] | `10` | `` | все |  |
| `margin.t` | int [0..100] | `10` | `` | все |  |

## outline

| Слаг | Тип | Default | json_path | applies_to | Прим. |
|---|---|---|---|---|---|
| `outline.color` | color | `#DDDFE4` | `` | все |  |
| `outline.enabled` | bool | `False` | `` | все |  |
| `outline.width` | int [0..20] | `4` | `` | все |  |

## parallel

| Слаг | Тип | Default | json_path | applies_to | Прим. |
|---|---|---|---|---|---|
| `parallel.tableSize` | int [0..1000] | `100` | `tableSize` | parallelCoordsChart |  |

## pivot

| Слаг | Тип | Default | json_path | applies_to | Прим. |
|---|---|---|---|---|---|
| `pivot.autoHeightEnabled` | bool | `True` | `` | pivotChart |  |
| `pivot.autoWidthEnabled` | bool | `True` | `` | pivotChart |  |
| `pivot.borderColor` | color | `` | `` | pivotChart |  |
| `pivot.dateFormat` | str | `DD.MM.YYYY` | `` | pivotChart |  |
| `pivot.fontFamily` | str | `None` | `` | pivotChart |  |
| `pivot.groupByOptimization` | bool | `False` | `` | pivotChart |  |
| `pivot.headerAling` | enum: left/center/right | `left` | `headerHorTextAlignment` | pivotChart |  |
| `pivot.headerBackgroundColor` | color | `` | `` | pivotChart |  |
| `pivot.headerFontSize` | int [8..72] | `None` | `` | pivotChart |  |
| `pivot.headerHeight` | int [0..300] | `0` | `headerHorCellHeight` | pivotChart |  |
| `pivot.headerHorWordWrapEnabled` | bool | `False` | `headerHorWordWrapEnabled` | pivotChart |  |
| `pivot.headerTextColor` | color | `` | `` | pivotChart |  |
| `pivot.hideMeasuresHeader` | bool | `False` | `` | pivotChart |  |
| `pivot.nullVisible` | bool | `False` | `` | pivotChart |  |
| `pivot.numbersEnabled` | bool | `False` | `numbers.enabled` | pivotChart |  |
| `pivot.precision` | int [-1..10] | `-1` | `precision` | pivotChart |  |
| `pivot.showPanel` | bool | `False` | `` | pivotChart |  |
| `pivot.theme` | enum: None/light | `None` | `` | pivotChart |  |

## regimes

| Слаг | Тип | Default | json_path | applies_to | Прим. |
|---|---|---|---|---|---|
| `regimes.autoWidth` | bool | `True` | `settings.AllowAutoWidth` | все |  |
| `regimes.cellHeight` | int [20..100] | `32` | `fixCellHeight` | все |  |
| `regimes.columnDrag` | bool | `True` | `settings.AllowColumnDnD` | все |  |
| `regimes.fixedColumns` | int [0..10] | `0` | `fixNumber` | все |  |
| `regimes.headerHeight` | int [20..100] | `32` | `fixHeaderHeight` | все |  |
| `regimes.multilineHeader` | bool | `True` | `settings.AllowMultilineHeader` | все |  |
| `regimes.resizable` | bool | `True` | `settings.AllowResizable` | все |  |
| `regimes.subtotals` | bool | `False` | `subMode` | все |  |
| `regimes.totals` | bool | `False` | `subAllMode` | все |  |

## sort

| Слаг | Тип | Default | json_path | applies_to | Прим. |
|---|---|---|---|---|---|
| `sort.headerClickSort` | bool | `True` | `sortTapable` | все |  |
| `sort.multiColumnSort` | bool | `False` | `sortMultiple` | все |  |

## stock

| Слаг | Тип | Default | json_path | applies_to | Прим. |
|---|---|---|---|---|---|
| `stock.altAxisEnabled` | bool | `False` | `altAxis.enabled` | stockChart |  |
| `stock.dateAxisMaxWidth` | int [0..500] | `0` | `dateAxis.maxWidth` | stockChart |  |
| `stock.dateAxisMinGridDistance` | int [10..200] | `30` | `dateAxis.minGridDistance` | stockChart |  |
| `stock.dateAxisTickangle` | int_or_null | `None` | `dateAxis.tickangle` | stockChart |  |
| `stock.dateAxisZigzag` | bool | `False` | `dateAxis.zigzag` | stockChart |  |
| `stock.dateFormat` | str | `yyyy-MM-dd` | `` | stockChart |  |
| `stock.dateRangePanel` | bool | `False` | `` | stockChart |  |
| `stock.dateZoomPanel` | bool | `False` | `` | stockChart |  |
| `stock.refresh` | bool | `False` | `` | stockChart |  |
| `stock.scrollbarDisabled` | bool | `False` | `scrollbar.disabled` | stockChart |  |

## style

| Слаг | Тип | Default | json_path | applies_to | Прим. |
|---|---|---|---|---|---|
| `style.autoColor` | enum: False/gradient/palette | `False` | `` | lineChart, areaChart, barChart |  |
| `style.clustered` | bool | `None` | `` | lineChart, areaChart |  |
| `style.labelsEnabled` | bool | `None` | `labels.visible` | lineChart, areaChart |  |
| `style.lineMode` | enum: None/dot/dash/longdash | `None` | `` | lineChart, areaChart |  |
| `style.lineWidth` | int [1..10] | `2` | `` | lineChart, areaChart |  |
| `style.markerMode` | str | `circle` | `` | lineChart, areaChart |  |
| `style.markerWidth` | int [0..20] | `0` | `` | lineChart, areaChart |  |
| `style.outlineWidth` | int [0..5] | `0` | `` | lineChart, areaChart |  |
| `style.smoothing` | float [0..2.0] | `0` | `` | lineChart, areaChart, barChart |  |
| `style.visType` | enum: None/line/column/bar/area | `None` | `` | lineChart, areaChart |  |

## sunburst

| Слаг | Тип | Default | json_path | applies_to | Прим. |
|---|---|---|---|---|---|
| `sunburst.colorsEnabled` | bool | `True` | `` | sunburstChart |  |
| `sunburst.darkLabels` | bool | `False` | `` | sunburstChart |  |
| `sunburst.ellipsisLength` | int [1..50] | `15` | `` | sunburstChart |  |
| `sunburst.filterMode` | bool | `False` | `` | sunburstChart |  |
| `sunburst.fontFamily` | str | `Arial` | `` | sunburstChart |  |
| `sunburst.fontSize` | float [0.4..2.0] | `0.8` | `` | sunburstChart |  |
| `sunburst.layerButtons` | bool | `False` | `` | sunburstChart |  |
| `sunburst.layerExpand` | bool | `False` | `` | sunburstChart |  |
| `sunburst.minPercent` | float [0.0..100.0] | `0.0` | `` | sunburstChart |  |
| `sunburst.precision` | int [0..10] | `0` | `` | sunburstChart |  |
| `sunburst.splittedMode` | bool | `False` | `` | sunburstChart |  |
| `sunburst.visibleLayers` | int [1..10] | `2` | `visibleLayersNumber` | sunburstChart |  |

## switch

| Слаг | Тип | Default | json_path | applies_to | Прим. |
|---|---|---|---|---|---|
| `switch.filterType` | enum: panel/column | `column` | `` | SwitchControlPanel |  |
| `switch.selectorTitleOverride` | str | `` | `` | SwitchControlPanel |  |

## table

| Слаг | Тип | Default | json_path | applies_to | Прим. |
|---|---|---|---|---|---|
| `table.headersBackground` | color | `None` | `headersBackground` | table |  |
| `table.headersColor` | color | `None` | `headersColor` | table |  |
| `table.linkByForRow` | str | `None` | `linkByForRow` | table |  |
| `table.precision` | int [-1..10] | `-1` | `precision` | table |  |
| `table.showNumberLineInHeader` | bool | `False` | `showNumberLineInHeader` | table |  |
| `table.theme` | enum: theme_classic/theme_blue/theme_dark/theme_compact/theme_compact2/classic/blue/dark/compact/compact2/light | `None` | `theme` | table |  |
| `table.zebraColor` | color | `None` | `zebraColor` | table |  |
| `table.zebraType` | enum: none/odd/even | `none` | `zebraType` | table |  |

## tabs

| Слаг | Тип | Default | json_path | applies_to | Прим. |
|---|---|---|---|---|---|
| `tabs.autoApply` | bool | `True` | `` | tabsPanel |  |
| `tabs.height` | int [20..100] | `33` | `` | tabsPanel |  |
| `tabs.orientation` | enum: h/v | `h` | `` | tabsPanel |  |
| `tabs.visuals` | any | `[]` | `visuals` | tabsPanel |  |

## text

| Слаг | Тип | Default | json_path | applies_to | Прим. |
|---|---|---|---|---|---|
| `text.maximizable` | bool | `True` | `` | textBlock |  |
| `text.noexport` | bool | `True` | `` | textBlock |  |

## tilemap

| Слаг | Тип | Default | json_path | applies_to | Прим. |
|---|---|---|---|---|---|
| `tilemap.allowTiles` | bool | `True` | `` | tilemapChart |  |
| `tilemap.autoZoom` | bool | `True` | `` | tilemapChart |  |
| `tilemap.bgTileColor` | color | `gray` | `` | tilemapChart |  |
| `tilemap.deltaK` | float [0.0..0.5] | `0.15` | `grouping.deltaK` | tilemapChart |  |
| `tilemap.endColor` | color | `red` | `` | tilemapChart |  |
| `tilemap.filterMode` | bool | `False` | `` | tilemapChart |  |
| `tilemap.grouping` | bool | `True` | `grouping.enabled` | tilemapChart |  |
| `tilemap.legendVisible` | bool | `True` | `` | tilemapChart |  |
| `tilemap.legendX` | enum: left/right | `right` | `legend.positionX` | tilemapChart |  |
| `tilemap.legendY` | enum: top/bottom | `bottom` | `legend.positionY` | tilemapChart |  |
| `tilemap.nameFontSize` | int [6..40] | `12` | `` | tilemapChart |  |
| `tilemap.popup` | bool | `False` | `popupEnabled` | tilemapChart |  |
| `tilemap.specialTiles` | bool | `False` | `` | tilemapChart |  |
| `tilemap.startColor` | color | `blue` | `` | tilemapChart |  |
| `tilemap.tileSize` | int [10..100] | `40` | `` | tilemapChart |  |
| `tilemap.tileType` | enum: square/hex | `square` | `` | tilemapChart |  |

## totals

| Слаг | Тип | Default | json_path | applies_to | Прим. |
|---|---|---|---|---|---|
| `totals.grandSumsFixed` | bool | `False` | `isGrandSumsFixed` | pivotChart |  |
| `totals.noGrandSumsX` | bool | `False` | `isNoGrandSumsX` | pivotChart |  |
| `totals.noGrandSumsY` | bool | `False` | `isNoGrandSumsY` | pivotChart |  |
| `totals.noSums` | bool | `False` | `isNoSums` | pivotChart |  |
| `totals.sumColumnAtLeft` | bool | `False` | `sumColumnAtLeft` | pivotChart |  |
| `totals.sumRowAtTop` | bool | `False` | `sumRowAtTop` | pivotChart |  |

## treemap

| Слаг | Тип | Default | json_path | applies_to | Прим. |
|---|---|---|---|---|---|
| `treemap.filterMode` | bool | `True` | `filterMode` | treeMap |  |
| `treemap.precision` | int [-1..10] | `-1` | `precision` | treeMap |  |

## viewType

| Слаг | Тип | Default | json_path | applies_to | Прим. |
|---|---|---|---|---|---|
| `viewType.addInvertedSwitch` | bool | `False` | `addInversedFilter` | FilterControlPanel |  |
| `viewType.autoApply` | bool | `True` | `autoApply` | FilterControlPanel |  |
| `viewType.clearSelection` | bool | `False` | `clearSelection` | FilterControlPanel |  |
| `viewType.displayType` | enum: dropdown/panel/slider/period/buttons/twofield/list/radio/checkbox/datepicker | `dropdown` | `filterType` | FilterControlPanel |  |
| `viewType.hideEmptyLines` | bool | `False` | `hideEmptyLines` | FilterControlPanel |  |
| `viewType.inversed` | bool | `False` | `inversed` | FilterControlPanel |  |
| `viewType.multiselect` | bool | `True` | `multipleChoice` | FilterControlPanel |  |
| `viewType.resetEnabled` | bool | `False` | `resetEnabled` | FilterControlPanel | ⚠️ DEPRECATED: no such frontend key; see viewType.updateOnApply/updateOnCloseDropdown |
| `viewType.searchEnabled` | bool | `False` | `searchInBaseMode` | FilterControlPanel |  |
| `viewType.showAll` | bool | `False` | `showAll` | FilterControlPanel | ⚠️ DEPRECATED: no such frontend key |
| `viewType.sortSelectedOptionsToTop` | bool | `False` | `sortSelectedOptionsToTop` | FilterControlPanel |  |
| `viewType.unlimitedSearch` | bool | `False` | `unlimitedSearch` | FilterControlPanel |  |
| `viewType.updateOnApply` | bool | `False` | `updateOnApply` | FilterControlPanel |  |
| `viewType.updateOnCloseDropdown` | bool | `False` | `updateOnCloseDropdown` | FilterControlPanel |  |

## visuals

| Слаг | Тип | Default | json_path | applies_to | Прим. |
|---|---|---|---|---|---|
| `visuals.autoColor` | bool | `True` | `styleCommons.autoColor` | все |  |
| `visuals.bubbleMaxSize` | int [5..100] | `30` | `maxRadius` | bubbleChart |  |
| `visuals.bubbleMinSize` | int [1..50] | `3` | `minRadius` | bubbleChart |  |
| `visuals.caption.color` | color | `None` | `` | totalsPanelV2 |  |
| `visuals.caption.font.size` | float [0.5..4] | `1.0` | `` | totalsPanelV2 |  |
| `visuals.caption.font.weight` | int [100..900] | `400` | `` | totalsPanelV2 |  |
| `visuals.caption.visible` | bool | `True` | `` | totalsPanelV2 |  |
| `visuals.chartType` | str | `None` | `visualType` | barChart |  |
| `visuals.clustered` | bool | `False` | `styleCommons.clustered` | barChart | значение ИНВЕРТИРУЕТСЯ |
| `visuals.colorMax` | color | `#eac736` | `colorMax` | parallelCoordsChart |  |
| `visuals.colorMin` | color | `#d94e5d` | `colorMin` | parallelCoordsChart |  |
| `visuals.colorPalette` | any | `pal_2018` | `` | все |  |
| `visuals.columnBorderRadius` | int [0..10] | `0` | `` | barChart |  |
| `visuals.columnWidth` | int [10..100] | `80` | `styleCommons.columnWidth` | barChart |  |
| `visuals.fillOpacity` | float [0..1] | `0.5` | `` | areaChart | ⚠️ DEPRECATED: use anchored visuals.<series>.fillColor (rgba with alpha) |
| `visuals.innerRadius` | int [0..45] | `0` | `innerRadius` | pieChart |  |
| `visuals.lineDashStyle` | enum: solid/dot/dash/longdash | `solid` | `styleCommons.lineMode` | lineChart, areaChart |  |
| `visuals.lineWidth` | int [1..10] | `2` | `` | lineChart, areaChart |  |
| `visuals.mainColor` | color | `None` | `` | все |  |
| `visuals.markerLabels` | bool | `False` | `` | lineChart, areaChart, bubbleChart |  |
| `visuals.markerSize` | int [0..20] | `5` | `styleCommons.markerWidth` | lineChart, areaChart |  |
| `visuals.markerType` | enum: circle/square/diamond/triangle-up/triangle-down/triangle-left/triangle-right | `circle` | `styleCommons.markerMode` | lineChart, areaChart |  |
| `visuals.smoothing` | bool | `False` | `` | lineChart, areaChart |  |
| `visuals.startAngle` | int [-360..360] | `0` | `startAngle` | pieChart |  |
| `visuals.subcaption.color` | color | `None` | `` | totalsPanelV2 |  |
| `visuals.subcaption.font.size` | float [0.5..4] | `1.0` | `` | totalsPanelV2 |  |
| `visuals.subcaption.visible` | bool | `True` | `` | totalsPanelV2 |  |
| `visuals.trend.color` | color | `None` | `` | totalsPanelV2 |  |
| `visuals.trend.visible` | bool | `True` | `` | totalsPanelV2 |  |
| `visuals.value.color` | color | `None` | `` | totalsPanelV2 |  |
| `visuals.value.decimals` | int [-1..10] | `-1` | `` | totalsPanelV2 |  |
| `visuals.value.font.family` | str | `None` | `` | totalsPanelV2 |  |
| `visuals.value.font.size` | float [0.5..8] | `2.8` | `` | totalsPanelV2 |  |
| `visuals.value.font.style` | enum: normal/italic | `normal` | `` | totalsPanelV2 |  |
| `visuals.value.font.weight` | int [100..900] | `600` | `` | totalsPanelV2 |  |
| `visuals.value.link` | str | `None` | `` | totalsPanelV2 |  |
| `visuals.value.linkTarget` | enum: _blank/_self | `_blank` | `` | totalsPanelV2 |  |
| `visuals.value.outlineColor` | color | `None` | `` | totalsPanelV2 |  |
| `visuals.value.outlineWidth` | int [0..5] | `0` | `` | totalsPanelV2 |  |
| `visuals.value.visible` | bool | `True` | `` | totalsPanelV2 |  |

## Анкерные visuals (per-series / per-element)

`visuals.{anchor}.{prop}` — пишет в элемент `config.visuals[]` с `anchor == {anchor}`
(имя серии у line/area/radar/stock, `value`/`caption`/`subcaption`/`trend` у KPI).
Поддерживаемые prop: `absolute`, `color`, `colorPalette`, `columnBorderRadius`, `decimals`, `fillColor`, `fillOpacity`, `font.family`, `font.size`, `font.style`, `font.weight`, `hasTarget`, `lineDashStyle`, `lineWidth`, `link`, `linkTarget`, `mainColor`, `markerLabels`, `markerSize`, `markerType`, `negation`, `outlineColor`, `outlineWidth`, `smoothing`, `thresholdForPercent`, `visible`.
Типы: line/area/gauge/KPI/stock/radar. Anchor с точкой в имени серии не адресуется (ограничение).

## Колоночные слаги (table/pivot/comparison)

`columns.{fieldName|fieldId}.{prop}` — props: `alignHorizontal`, `alignVertical`, `colorByFieldId`, `columnNullVisible`, `dateFormat`, `emptyAsNil`, `hidden`, `isHideSame`, `isHtml`, `isLink`, `lineWrap`, `linkBy`, `linkEnabled`, `precision`, `repeatValues`, `rightAlign`, `searchEnabled`, `showGradient`, `showSparkline`, `subtotalsEnabled`, `suffix`, `title`, `titleByOtherField`, `title__ru`, `transparency`, `valueSeparator`, `visibleOrder`, `width`.

## Правила условного форматирования (table/pivot)

`rules.{n}.{prop}` — props: `background`, `color`, `cons.operator`, `cons.value`, `fieldById`, `fieldId`, `hideTypeTotals`, `hideTypeValue`, `indicatorColor`, `indicatorType`, `isTextBold`, `isTextItalic`, `isTextUnderline`, `isTypeHeader`, `logicOr`, `maximum`, `minimum`, `name`, `sparklineColor`, `wholeRow`.

## Алиасы

- `donut` → `showDonut`
