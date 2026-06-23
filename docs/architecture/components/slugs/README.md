# Справочник слагов: соответствие MCP ↔ UI ↔ JSON

> Генерируется из `app/tools/config_schema.py` (SLUG_SCHEMA) — единый источник истины для всех
> слаг-файлов (этот каталог, [by-type.md](by-type.md), [aliases.md](aliases.md), [slug-table.json](slug-table.json)).
> Регенерация: `python3 scripts/gen_slug_catalog.py`.

**Слаг** — короткое плоское имя одной настройки компонента (например `legend.visible`, `margin.l`,
`colors.palette`). Слаги передаются словарём `config_overrides` в инструменты `component_crud` и
`component_styling`; сервер сам раскладывает каждый слаг в нужный **JSON-путь** внутри конфигурации
компонента, откуда его читает фронтенд портала при отрисовке.

У одной настройки три имени:

- **UI-контрол** — как настройка называется в панели справа на портале (то, что видит пользователь);
- **MCP-слаг** — ключ, который ассистент передаёт в `config_overrides`;
- **JSON-путь** — куда значение ложится в конфигурации (это и есть «фронт-ключ», который читает рендер).

Как применить слаг:

```text
component_crud(action="update", report_id=<id>, component_idx=0,
               config_overrides={"legend.visible": false, "margin.l": 12})
```

Подробно про саму идею слагов и зачем три имени — в концепции
[components-json-slugs.md](../../concepts/components-json-slugs.md). Те же слаги, **сгруппированные по
типам компонентов**, — в [by-type.md](by-type.md); устаревшие имена и псевдонимы — в
[aliases.md](aliases.md). Машиночитаемые данные этой таблицы — в [slug-table.json](slug-table.json).

## Как читать таблицу

- **MCP-слаг** — ключ для `config_overrides`.
- **UI-контрол** — название в панели настроек портала. Пусто (`—`) = прямого контрола в UI нет,
  настройка задаётся только через `config_overrides`.
- **Секция** — раздел панели настроек, где находится контрол.
- **JSON-путь** — фронт-ключ в конфигурации компонента, **фактический путь записи** (трассирован;
  для большинства слагов совпадает с путём по схеме). `(в скобках)` — ключ обрабатывается секционно
  (итоговое имя внутри своей секции конфига). Машиночитаемый [slug-table.json](slug-table.json) хранит
  оба варианта пути (поля `json` и `effective`).
- **Тип** и **По умолчанию** — из схемы слагов.
- **Применяется к** — типы компонентов, к которым относится слаг; «оформительские» = общие настройки
  (контейнер/диаграммы в целом).
- **Статус** — `устар.` (использовать новое имя, см. aliases.md) или `инверт.` (значение пишется
  с инверсией, например «скрыть» ↔ «показать»).

Всего слагов: **365**. Кроме них есть **шаблонные семейства**, задаваемые по образцу
(свой ключ на каждую серию / поле / правило) и потому поимённо в таблицу не вынесенные: анкерные
`visuals.{anchor}.{prop}` (на серию графика), колоночные `columns.{field}.{prop}` (на поле
таблицы/сводной), правила условного форматирования `rules.{n}.{prop}` — их разбор в [by-type.md](by-type.md).

| MCP-слаг | UI-контрол | Секция | JSON-путь | Тип | По умолчанию | Применяется к | Статус |
|---|---|---|---|---|---|---|---|
| `audio.backgroundColor` | Цвет фона индикатора | Общие | `(backgroundColor)` | color | — | audioplayer |  |
| `audio.progressBarBackgroundColor` | Progress Bar Background Color | Аудиоплеер | `(progressBarBackgroundColor)` | color | — | audioplayer |  |
| `audio.progressBarColor` | Progress Bar Color | Аудиоплеер | `(progressBarColor)` | color | `rgba(0, 139, 139, 1)` | audioplayer |  |
| `audio.uploadURL` | Upload URL | Аудиоплеер | `resource.uploadURL` | str | — | audioplayer |  |
| `audio.url` | Url | Аудиоплеер | `resource.url` | str | — | audioplayer |  |
| `axes.autoZoom` | Auto Zoom | Оси | `axes[values].autoZoom` | bool | `False` | оформительские |  |
| `axes.categoryGrid` | Сетка | Ось Кат. | `axes[categories].showgrid` | bool | `False` | оформительские |  |
| `axes.categoryLabelAngle` | Category Label Angle | Оси | `axes[categories].tickangle` | int | `0` | оформительские |  |
| `axes.categoryLabels` | Category Labels | Оси | `axes[categories].showlabels` | bool | `True` | оформительские |  |
| `axes.categoryMaxLabelWidth` | Category Max Label Width | Оси | `axes[categories].maxLabelWidth` | int | `0` | оформительские |  |
| `axes.categoryMinGridWidth` | Category Min Grid Width | Оси | `axes[categories].minGridWidth` | int | `0` | оформительские |  |
| `axes.categoryScale` | Category Scale | Оси | `axes[categories].showscale` | bool | `True` | оформительские |  |
| `axes.categoryScrollable` | Category Scrollable | Оси | `axes[categories].scrollable` | bool | `False` | оформительские |  |
| `axes.categoryScrollbar` | Category Scrollbar | Оси | `axes[categories].fixedZoom` | bool | `False` | оформительские |  |
| `axes.categoryTitle` | Category Title | Оси | `axes[categories].showtitle` | bool | `False` | оформительские |  |
| `axes.customZoom` | Custom Zoom | Оси | `axes[categories].customZoom` | bool | `False` | оформительские |  |
| `axes.firstLabel` | First Label | Оси | `axes[values].showFirstLabel` | bool | `True` | оформительские |  |
| `axes.firstTick` | First Tick | Оси | `axes[values].showFirstTick` | bool | `True` | оформительские |  |
| `axes.labelsAccuracy` | Labels Accuracy | Оси | `axes[values].labelsAccuracy` | int | `2` | оформительские |  |
| `axes.lastLabel` | Last Label | Оси | `axes[values].showLastLabel` | bool | `True` | оформительские |  |
| `axes.lastTick` | Last Tick | Оси | `axes[values].showLastTick` | bool | `True` | оформительские |  |
| `axes.rangeMode` | Range Mode | Оси | `axes[values].rangeMode` | enum | `normal` | оформительские |  |
| `axes.scaleType` | Scale Type | Оси | `axes[values].scaleType` | enum | `-` | оформительские |  |
| `axes.selectedFieldIndex` | Selected Field Index | Оси | `axes[values].selectedFieldIndex` | int | `-2` | оформительские |  |
| `axes.sortable` | Sortable | Оси | `axes[values].sortable` | bool | `True` | оформительские |  |
| `axes.valueGrid` | Сетка | Ось Знач. | `axes[values].showgrid` | bool | `False` | оформительские |  |
| `axes.valueLabels` | Подписи шкалы | Ось Знач. | `axes[values].showlabels` | bool | `True` | оформительские |  |
| `axes.valueScale` | Value Scale | Оси | `axes[values].showscale` | bool | `True` | оформительские |  |
| `axes.valueShowMax` | Value Show Max | Оси | `axes[values].showMax` | bool | `False` | оформительские |  |
| `axes.valueShowMin` | Value Show Min | Оси | `axes[values].showMin` | bool | `False` | оформительские |  |
| `axes.valueTitle` | Value Title | Оси | `axes[values].showtitle` | bool | `False` | оформительские |  |
| `balloon.bgColor` | Bg Color | Всплывающая подсказка | `balloon.bgcolor` | color | — | оформительские |  |
| `balloon.combine` | Combine | Всплывающая подсказка | `balloon.allSeriesPop` | bool | `False` | оформительские | инверт. |
| `balloon.fontColor` | Font Color | Всплывающая подсказка | `balloon.color` | color | — | оформительские |  |
| `balloon.fontSize` | Размер шрифта | Всплыв. | `balloon.fontsize` | int | `12` | оформительские |  |
| `balloon.template` | Шаблон | Всплыв. | `balloonTemplate` | str | — | оформительские |  |
| `balloon.visible` | вкл | Всплыв. | `(balloon.visible)` | bool | `True` | оформительские |  |
| `balloonTemplate` | Balloon Template | Общие | `(balloonTemplate)` | str | — | pieChart |  |
| `bgColor` | Цвет фона | Общие | `(bgColor  [per-type: totalsPanelV2→backgroundColor, imagePanel→backgroundColor, iframe→backgroundColor, speedometerV2→backgroundColor])` | color | `rgba(255,255,255,1)` | оформительские |  |
| `bgColor2` | Цвет фона 2 | Общие | `(bgColor2  [per-type: totalsPanelV2→backgroundColor2])` | color | — | оформительские |  |
| `bubble.bigNumberSuffixes` | Big Number Suffixes | Пузырьковая диаграмма | `bigNumberSuffixes` | any | `[]` | bubbleChart |  |
| `bubble.filterMode` | Режим фильтра | Общие | `filterMode` | bool | `True` | bubbleChart |  |
| `bubble.legendForColor` | enable | Легенда цвета | `legendForColor.enabled` | bool | `False` | bubbleChart |  |
| `bubble.legendForSize` | enable / Граф. представление | Легенда размера | `legendForSize.enabled` | bool | `False` | bubbleChart |  |
| `bubble.precision` | Цвет фона / Отступы / Точность / Формат даты | Общие | `precision` | int | `-1` | bubbleChart |  |
| `bubble.showScrollbars` | Show Scrollbars | Пузырьковая диаграмма | `hideScrollbars` | bool | `True` | bubbleChart | инверт. |
| `bubble.strictMinMax` | Режим точн. масшт. | Общие | `strictMinMaxEnabled` | bool | `False` | bubbleChart |  |
| `bubble.zoomToEdges` | Учёт размеров пузырьков | Общие | `zoomToBubbleEdges` | bool | `False` | bubbleChart |  |
| `comparison.object1` | Объект 1 | Объекты | `(object1)` | str | — | comparisonChart |  |
| `comparison.object2` | Объект 2 | Объекты | `(object2)` | str | — | comparisonChart |  |
| `comparison.precision` | Точность чисел | Общие | `(precision)` | int | `-1` | comparisonChart |  |
| `comparison.showDelta` | Дельта | Дельта/Процент | `(showDelta)` | bool | `False` | comparisonChart |  |
| `comparison.showPercent` | Процент | Дельта/Процент | `(showPercent)` | bool | `False` | comparisonChart |  |
| `data.autofillEmptySeries` | Дополнять пустые Кат./Серии | Данные | `series.autoFill` | bool | `False` | оформительские |  |
| `data.baseColor` | базовый цвет | Осн.стиль | `(baseColor)` | color | — | barChart, pieChart |  |
| `data.colorStep` | Шаг яркости | Стилизация | `(colorStep)` | int | `0` | barChart, pieChart |  |
| `data.intervalRefresh` | Интервальное обновление | Данные | `refresh` | bool | `False` | оформительские |  |
| `data.intervalSeconds` | Interval Seconds | Данные | `refreshTime` | int | `60` | оформительские |  |
| `data.rowsLimit` | Лимит при запросе | Данные | `rowsLimit` | int | `5000` | оформительские |  |
| `data.rowsLimitToExport` | Лимит при экспорте | Данные | `rowsLimitToExport` | int | `0` | оформительские |  |
| `data.rowsLimitToShow` | Rows Limit To Show | Данные | `rowsLimitToShow` | int | `0` | оформительские |  |
| `data.seriesLimitToShow` | Series Limit To Show | Данные | `seriesLimitToShow` | int | `0` | оформительские |  |
| `delta.delta` | Тип расчёта (Цель) | Стиль(Trend) | `visuals[trend].hasTarget` | bool | `False` | totalsPanelV2 |  |
| `delta.percent` | В процентах | Стиль(Trend) | `visuals[trend].absolute (inverted)` | bool | `False` | totalsPanelV2 |  |
| `expandH` | Expand H | Общие | `(expandH)` | bool | `False` | barChart, lineChart, areaChart, pieChart, stockChart |  |
| `expandV` | Expand V | Общие | `(expandV)` | bool | `False` | barChart, lineChart, areaChart, pieChart, stockChart |  |
| `flip` | Отразить зеркально | Вид панели | `(flip)` | bool | `False` | totalsPanelV2 |  |
| `fontSize` | Font Size | Общие | `(fontSize)` | int | `12` | оформительские |  |
| `gauge.backgroundColor` | Цвет фона | Общие | `backgroundColor` | color | — | speedometerV2 |  |
| `gradient` | Градиент | Общие | `(gradient  [per-type: totalsPanelV2→gradientEnabled])` | bool | `False` | оформительские |  |
| `gradientDirection` | Направление градиента (°) | Фон | `gradientDirection` | int | `0` | totalsPanelV2 |  |
| `graph.initialZoom` | Начальный масштаб | Общие | `(initialZoom)` | float | `0.7` | treeGraph |  |
| `graph.layout` | Тип графа | Общие | `(layout)` | enum | `TreeLayout` | treeGraph |  |
| `graph.zoomable` | Автомасштабирование | Общие | `(zoomable)` | bool | `True` | treeGraph |  |
| `grid.color` | Color | Шкала/индикатор | `(grid.color)` | color | — | speedometerV2 |  |
| `grid.endAngle` | Конечный угол | Шкала | `endAngle` | int | `360` | speedometerV2 |  |
| `grid.filled` | заливка области | (top, нет UI) | `filled` | bool | `True` | radarChart |  |
| `grid.gradeCount` | Количество цветов (зоны) | Шкала/Отсечки | `grid.palette.gradeCount` | int | `3` | speedometerV2 |  |
| `grid.gradientMode` | Gradient Mode | Шкала/индикатор | `grid.palette.gradientMode` | bool | `False` | speedometerV2 |  |
| `grid.gridType` | Тип сетки (Радар/Паутина) | Ось Значения | `axes[values].gridType` | enum | `circles` | radarChart |  |
| `grid.labelFrequency` | Label Frequency | Шкала/индикатор | `(grid.labelFrequency)` | int | `1` | speedometerV2 |  |
| `grid.labelsColor` | Labels Color | Шкала/индикатор | `(grid.labelsColor)` | color | — | speedometerV2 |  |
| `grid.max` | Максимум | Шкала | `grid.maximum` | float | `100` | speedometerV2 |  |
| `grid.min` | Минимум | Шкала | `grid.minimum` | float | `0` | speedometerV2 |  |
| `grid.minorTickCount` | Мелких делений | Шкала | `(grid.minorTickCount)` | int | `2` | speedometerV2 |  |
| `grid.paletteColors` | Palette Colors | Шкала/индикатор | `grid.palette.colors` | any | — | speedometerV2 |  |
| `grid.paletteInvert` | Palette Invert | Шкала/индикатор | `grid.palette.invert` | bool | `False` | speedometerV2 |  |
| `grid.radarLabels` | Подписи категорий | Ось Значения | `axes[values].radarlabels` | bool | `True` | radarChart |  |
| `grid.roundLimits` | Округл. мин/макс | Шкала | `roundLimits` | bool | `False` | speedometerV2 |  |
| `grid.startAngle` | Начальный угол | Шкала | `startAngle` | int | `0` | speedometerV2 |  |
| `grid.tickCount` | Крупных делений | Шкала | `(grid.tickCount)` | int | `5` | speedometerV2 |  |
| `grid.width` | Width | Шкала/индикатор | `(grid.width)` | int | `20` | speedometerV2 |  |
| `hideSpinner` | Анимация обновления | Данные | `(hideSpinner)` | bool | `False` | оформительские |  |
| `hierFilter.bothChoice` | Both Choice | Иерархический фильтр | `(bothChoice)` | bool | `True` | hierarchicalFilterPanel |  |
| `hierFilter.filterTitle` | Filter Title | Иерархический фильтр | `(filterTitle)` | str | — | hierarchicalFilterPanel |  |
| `hierFilter.headerWidth` | Header Width | Иерархический фильтр | `(headerWidth)` | int | `0` | hierarchicalFilterPanel |  |
| `hierFilter.hideTitle` | Hide Title | Иерархический фильтр | `(hideTitle)` | bool | `False` | hierarchicalFilterPanel |  |
| `hierFilter.inversed` | Inversed | Иерархический фильтр | `(inversed)` | bool | `False` | hierarchicalFilterPanel |  |
| `hierFilter.multipleChoice` | Multiple Choice | Иерархический фильтр | `(multipleChoice)` | bool | `True` | hierarchicalFilterPanel |  |
| `hierFilter.noLoadOptions` | No Load Options | Иерархический фильтр | `(noLoadOptions)` | bool | `True` | hierarchicalFilterPanel |  |
| `hierFilter.searchInBaseMinNumber` | Search In Base Min Number | Иерархический фильтр | `(searchInBaseMinNumber)` | int | `1` | hierarchicalFilterPanel |  |
| `hierFilter.searchInBaseMode` | Search In Base Mode | Иерархический фильтр | `(searchInBaseMode)` | bool | `False` | hierarchicalFilterPanel |  |
| `hierFilter.sortSelectedOptionsToTop` | Sort Selected Options To Top | Иерархический фильтр | `(sortSelectedOptionsToTop)` | bool | `False` | hierarchicalFilterPanel |  |
| `hierFilter.updateOnApply` | Update On Apply | Иерархический фильтр | `(updateOnApply)` | bool | `False` | hierarchicalFilterPanel |  |
| `hierFilter.updateOnCloseDropdown` | Update On Close Dropdown | Иерархический фильтр | `(updateOnCloseDropdown)` | bool | `True` | hierarchicalFilterPanel |  |
| `iframe.linkName` | Link Name | iFrame | `link.name` | str | — | iframe |  |
| `iframe.linkTarget` | Link Target | iFrame | `link.target` | enum | `_self` | iframe |  |
| `image.backgroundPosition` | Background Position | Общие | `(backgroundPosition)` | enum | `center center` | imagePanel |  |
| `image.backgroundSize` | Background Size | Общие | `(backgroundSize)` | enum | `contain` | imagePanel |  |
| `image.backgroundStyle` | Background Style | Общие | `(backgroundStyle)` | enum | `no-repeat` | imagePanel |  |
| `image.linkName` | Link Name | Общие | `link.name` | str | — | imagePanel |  |
| `image.linkTarget` | Link Target | Общие | `link.target` | enum | `_self` | imagePanel |  |
| `image.src` | Src | Общие | `image` | any | — | imagePanel |  |
| `image.titleColor` | Title Color | Общие | `(titleColor)` | color | — | imagePanel |  |
| `image.titleSize` | Title Size | Общие | `(titleSize)` | str | — | imagePanel |  |
| `labels.angle` | Angle | Подписи | `(labels.angle)` | int | `0` | оформительские |  |
| `labels.bypassCollisions` | Bypass Collisions | Подписи | `bypassCheckCollisions` | bool | `False` | оформительские |  |
| `labels.fontSize` | enable / шрифт подписей / шрифт значений / интервал | Подписи | `labels.inner.fontsize` | int | `12` | оформительские |  |
| `labels.groupCount` | Group Count | Подписи | `(labels.groupCount)` | int | `9` | pieChart |  |
| `labels.groupPercent` | — | (slug без UI) | `(labels.groupPercent)` | float | `0.5` | pieChart |  |
| `labels.groupedTitle__ru` | Заголовок группы «Прочее» | Общие | `(labels.groupedTitle__ru)` | str | — | pieChart |  |
| `labels.hidePercent` | Скрыть если <N% | Подписи | `(labels.hidePercent)` | float | `0` | оформительские |  |
| `labels.inner.fontsize` | Fontsize | Подписи | `(labels.inner.fontsize)` | int | `12` | оформительские |  |
| `labels.labelsColor` | Labels Color | Подписи | `labels.inner.color` | color | — | оформительские |  |
| `labels.outer.color` | Color | Подписи | `(labels.outer.color)` | color | `rgba(68,68,68,1)` | оформительские |  |
| `labels.outer.fontsize` | Размер шрифта | Подписи | `(labels.outer.fontsize)` | int | `12` | оформительские |  |
| `labels.outerLabelsAngle` | Outer Labels Angle | Подписи | `(labels.outerLabelsAngle)` | int | `0` | pieChart |  |
| `labels.position` | Position | Подписи | `(labels.position)` | enum | `auto` | оформительские |  |
| `labels.switchControlNumberOfSegments` | Управление кол-вом сегментов | Общие | `(labels.switchControlNumberOfSegments)` | bool | `False` | pieChart |  |
| `labels.template` | Template | Подписи | `(labels.template)` | str | — | оформительские |  |
| `labels.valuesFontSize` | Values Font Size | Подписи | `labels.value.fontsize` | int | `12` | treeMap |  |
| `labels.valuesTopMargin` | Values Top Margin | Подписи | `labels.value.topMargin` | int | `5` | treeMap |  |
| `labels.visible` | enable | Подписи | `(labels.visible)` | bool | `False` | оформительские |  |
| `labelsTemplate` | Шаблон | Подписи | `(labelsTemplate)` | str | `[[percents]]%` | pieChart |  |
| `legend.bgColor` | Bg Color | Легенда | `(legend.bgcolor)` | color | — | оформительские |  |
| `legend.borderColor` | Border Color | Легенда | `(legend.bordercolor)` | color | — | оформительские |  |
| `legend.borderWidth` | Border Width | Легенда | `(legend.borderwidth)` | int | `0` | оформительские |  |
| `legend.fontSize` | Размер шрифта | Легенда | `(legend.fontSize)` | int | `12` | оформительские |  |
| `legend.order` | Реверс | Легенда | `(legend.order)` | enum | `normal` | оформительские |  |
| `legend.orientation` | Orientation | Легенда | `(legend.orientation)` | enum | `h` | оформительские |  |
| `legend.percent` | Percent | Легенда | `(legend.percent)` | bool | `False` | оформительские |  |
| `legend.position` | Положение | Легенда | `(legend.position)` | enum | `auto` | оформительские |  |
| `legend.reverse` | Реверс | Легенда | `((section-derived / transform))` | bool | `False` | оформительские |  |
| `legend.visible` | вкл | Легенда | `(legend.visible)` | bool | `True` | оформительские |  |
| `link.operation` | Другая операция | Клик | `(link.operation)` | str | — | оформительские |  |
| `main.extraAxis` | Extra Axis | Общие | `(main.extraAxis)` | bool | `False` | barChart, lineChart, areaChart |  |
| `map.annotationOpacity` | Яркость аннотации | Описание | `annotationOpacity` | float | `0.8` | mapLeaflet |  |
| `map.annotationText` | Annotation Text | Карта | `annotation` | str | — | mapLeaflet |  |
| `map.autoCenter` | Авто центровка | Общие | `(autoCenter)` | bool | `True` | mapLeaflet |  |
| `map.background.allowTiles` | Карта | Фон | `(background.allowTiles)` | bool | `True` | mapLeaflet |  |
| `map.background.allowTiles2` | Железные дороги | Фон | `(background.allowTiles2)` | bool | `False` | mapLeaflet |  |
| `map.background.backgroundColor` | Background Color | Карта | `(background.backgroundColor)` | color | `gray` | mapLeaflet |  |
| `map.background.tileUrl` | Tile Url | Карта | `(background.tileUrl)` | str | `{s}.tile.osm.org/{z}/{x}/{y}.png` | mapLeaflet |  |
| `map.center.lat` | Lat | Карта | `(center.lat)` | float | `55.751` | mapLeaflet |  |
| `map.center.lng` | Lng | Карта | `(center.lng)` | float | `37.618` | mapLeaflet |  |
| `map.clusterMarkers` | — | (нет UI) | `clusterMarkers` | bool | `False` | mapLeaflet | устар. |
| `map.filterMode` | Режим фильтра | Общие | `(filterMode)` | bool | `False` | mapLeaflet |  |
| `map.initialZoom` | — | (нет UI) | `initialZoom` | int | `5` | mapLeaflet |  |
| `map.legend.discrete` | Дискретные цвета | Легенда | `(legend.discrete)` | bool | `False` | mapLeaflet |  |
| `map.legend.gradeNumber` | Grade Number | Карта | `(legend.gradeNumber)` | int | `5` | mapLeaflet |  |
| `map.legend.invertColors` | Invert Colors | Карта | `(legend.invertColors)` | bool | `False` | mapLeaflet |  |
| `map.legend.position` | Расположение | Легенда | `(legend.position)` | enum | `bottomright` | mapLeaflet |  |
| `map.legend.visible` | Visible | Карта | `(legend.visible)` | bool | `True` | mapLeaflet |  |
| `map.legend.withFilters` | With Filters | Карта | `(legend.withFilters)` | bool | `False` | mapLeaflet |  |
| `map.markers.clustering` | Кластеризация | Подписи | `markers.clusterizationOff` | bool | `False` | mapLeaflet | инверт. |
| `map.markers.clusteringThreshold` | Clustering Threshold | Карта | `markers.clusterizationSize` | int | `50` | mapLeaflet |  |
| `map.markers.fixedExtent` | Fixed Extent | Карта | `(markers.fixedExtent)` | bool | `False` | mapLeaflet |  |
| `map.markers.gradeNumberForSize` | Grade Number For Size | Карта | `(markers.gradeNumberForSize)` | int | `3` | mapLeaflet |  |
| `map.markers.isLinearScale` | Is Linear Scale | Карта | `(markers.isLinearScale)` | bool | `False` | mapLeaflet |  |
| `map.markers.labelMinZoom` | Label Min Zoom | Карта | `markers.minZoomLevel` | int | `0` | mapLeaflet |  |
| `map.markers.labelsSize` | Labels Size | Карта | `(markers.labelsSize)` | int | `12` | mapLeaflet |  |
| `map.markers.maxSize` | Max Size | Карта | `(markers.maxSize)` | int | `50` | mapLeaflet |  |
| `map.markers.maxValue` | Max Value | Карта | `(markers.maxValue)` | float | `100.0` | mapLeaflet |  |
| `map.markers.maxValueColor` | Max Value Color | Карта | `(markers.maxValueColor)` | color | `red` | mapLeaflet |  |
| `map.markers.minSize` | Min Size | Карта | `(markers.minSize)` | int | `0` | mapLeaflet |  |
| `map.markers.showLabels` | Show Labels | Карта | `(markers.showLabels)` | bool | `True` | mapLeaflet |  |
| `map.markers.showMaxValue` | Show Max Value | Карта | `markers.maxValueShow` | bool | `False` | mapLeaflet |  |
| `map.markers.showTooltip` | Show Tooltip | Карта | `(markers.showTooltip)` | bool | `True` | mapLeaflet |  |
| `map.markers.showValues` | Показывать значения | Подписи | `(markers.showValues)` | bool | `False` | mapLeaflet |  |
| `map.markers.tooltipSize` | Tooltip Size | Карта | `markers.tooltipTextSize` | int | `12` | mapLeaflet |  |
| `map.markers.tooltipWordWrap` | Tooltip Word Wrap | Карта | `markers.lineWrap` | bool | `False` | mapLeaflet |  |
| `map.markers.valuesPrecision` | Values Precision | Карта | `(markers.valuesPrecision)` | int | `-1` | mapLeaflet |  |
| `map.multilayerMode` | Многослойный режим | Общие | `(multilayerMode)` | bool | `False` | mapLeaflet |  |
| `map.showSmallObjects` | Show Small Objects | Карта | `(showSmallObjects)` | bool | `False` | mapLeaflet |  |
| `map.titleBrightness` | Яркость заголовка | Общие | `titleOpacity` | float | `0.8` | mapLeaflet |  |
| `margin.b` | Отступ Низ | Отступы | `(margin.b)` | int | `5` | оформительские |  |
| `margin.l` | Отступ Лево | Отступы | `(margin.l)` | int | `5` | оформительские |  |
| `margin.pad` | Внутренний отступ | Отступы | `(margin.pad)` | int | `0` | оформительские |  |
| `margin.r` | Отступ Право | Отступы | `(margin.r)` | int | `10` | оформительские |  |
| `margin.t` | Отступ Верх | Отступы | `(margin.t)` | int | `10` | оформительские |  |
| `nocopy` | Nocopy | Общие | `(nocopy)` | bool | `False` | оформительские |  |
| `noexport` | Noexport | Общие | `(noexport)` | bool | `False` | оформительские |  |
| `numberPrecision` | Точность чисел | Общие | `(numberPrecision  [per-type: totalsPanelV2→precision])` | int | `-1` | оформительские |  |
| `orientation` | Ориентация | Общие | `(orientation)` | enum | `v` | оформительские |  |
| `outline.color` | Цвет | Рамка | `(outline.color)` | color | `#DDDFE4` | оформительские |  |
| `outline.enabled` | вкл | Рамка | `(outline.enabled)` | bool | `False` | оформительские |  |
| `outline.width` | Ширина | Рамка | `(outline.width)` | int | `4` | оформительские |  |
| `parallel.tableSize` | Высота таблицы (px) | Общие | `tableSize` | int | `100` | parallelCoordsChart |  |
| `percentPrecision` | Точность проц. | Общие | `(percentPrecision)` | int | `2` | оформительские |  |
| `pivot.autoHeightEnabled` | Auto Height Enabled | Сводная таблица | `(autoHeightEnabled)` | bool | `True` | pivotChart |  |
| `pivot.autoWidthEnabled` | Auto Width Enabled | Сводная таблица | `(autoWidthEnabled)` | bool | `True` | pivotChart |  |
| `pivot.borderColor` | Border Color | Сводная таблица | `(borderColor)` | color | — | pivotChart |  |
| `pivot.dateFormat` | Формат даты | Общие | `(dateFormat)` | str | `DD.MM.YYYY` | pivotChart |  |
| `pivot.fontFamily` | Font Family | Сводная таблица | `(fontFamily)` | str | — | pivotChart |  |
| `pivot.groupByOptimization` | Group By Optimization | Сводная таблица | `(groupByOptimization)` | bool | `False` | pivotChart |  |
| `pivot.headerAling` | Выравнивание в шапке | Стилизация | `headerHorTextAlignment` | enum | `left` | pivotChart |  |
| `pivot.headerBackgroundColor` | Header Background Color | Сводная таблица | `(headerBackgroundColor)` | color | — | pivotChart |  |
| `pivot.headerFontSize` | Header Font Size | Сводная таблица | `(headerFontSize)` | int | — | pivotChart |  |
| `pivot.headerHeight` | Header Height | Сводная таблица | `headerHorCellHeight` | int | `0` | pivotChart |  |
| `pivot.headerHorWordWrapEnabled` | Высота шапки / Перенос строк | Стилизация | `headerHorWordWrapEnabled` | bool | `False` | pivotChart |  |
| `pivot.headerTextColor` | Header Text Color | Сводная таблица | `(headerTextColor)` | color | — | pivotChart |  |
| `pivot.hideMeasuresHeader` | Скрыть заголовок значений | Общие | `(hideMeasuresHeader)` | bool | `False` | pivotChart |  |
| `pivot.nullVisible` | Отображение нулевых | Общие | `(nullVisible)` | bool | `False` | pivotChart |  |
| `pivot.numbersEnabled` | Нумерация строк | Общие | `numbers.enabled` | bool | `False` | pivotChart |  |
| `pivot.precision` | Точность чисел | Общие | `precision` | int | `-1` | pivotChart |  |
| `pivot.showPanel` | Show Panel | Сводная таблица | `(showPanel)` | bool | `False` | pivotChart |  |
| `pivot.theme` | Тема/Цвет линий/Шрифт/Цвета шапки/Размер шапки | Стилизация | `(theme)` | enum | — | pivotChart |  |
| `radius` | Диаметр | Общие | `(radius)` | int | `80` | pieChart, radarChart |  |
| `regimes.autoWidth` | Автоширина колонок | Режимы | `settings.AllowAutoWidth` | bool | `True` | оформительские |  |
| `regimes.cellHeight` | Cell Height | Режимы таблицы | `fixCellHeight` | int | `32` | оформительские |  |
| `regimes.columnDrag` | Column Drag | Режимы таблицы | `settings.AllowColumnDnD` | bool | `True` | оформительские |  |
| `regimes.fixedColumns` | Закреплённых колонок | Режимы | `fixNumber` | int | `0` | оформительские |  |
| `regimes.headerHeight` | Header Height | Режимы таблицы | `fixHeaderHeight` | int | `32` | оформительские |  |
| `regimes.multilineHeader` | Multiline Header | Режимы таблицы | `settings.AllowMultilineHeader` | bool | `True` | оформительские |  |
| `regimes.resizable` | Resizable | Режимы таблицы | `settings.AllowResizable` | bool | `True` | оформительские |  |
| `regimes.subtotals` | Подытоги | Режимы | `subMode` | bool | `False` | оформительские |  |
| `regimes.totals` | Итоги | Режимы | `subAllMode` | bool | `False` | оформительские |  |
| `scrollbars` | Scrollbars | Общие | `(scrollbars)` | bool | `False` | оформительские |  |
| `showDonut` | Вид (Пирог/Бублик) | Стилизация | `(showDonut)` | bool | `False` | pieChart |  |
| `showtitle` | Заголовок | Общие | `(showtitle)` | bool | `True` | оформительские |  |
| `sort.headerClickSort` | Смена сортировки нажатием | Сортировка | `sortTapable` | bool | `True` | оформительские |  |
| `sort.multiColumnSort` | По нескольким колонкам | Сортировка | `sortMultiple` | bool | `False` | оформительские |  |
| `stacking` | Стекинг | Общие | `(stacking)` | enum | `none` | оформительские |  |
| `stock.altAxisEnabled` | enable | Доп.диаграмма | `altAxis.enabled` | bool | `False` | stockChart |  |
| `stock.dateAxisMaxWidth` | Макс.ширина подписи | Осн.диаграмма | `dateAxis.maxWidth` | int | `0` | stockChart |  |
| `stock.dateAxisMinGridDistance` | Мин.ширина сетки | Осн.диаграмма | `dateAxis.minGridDistance` | int | `30` | stockChart |  |
| `stock.dateAxisTickangle` | Наклон подписей | Осн.диаграмма | `dateAxis.tickangle` | int_or_null | — | stockChart |  |
| `stock.dateAxisZigzag` | Два уровня подписей | Осн.диаграмма | `dateAxis.zigzag` | bool | `False` | stockChart |  |
| `stock.dateFormat` | формат даты | (нет UI) | `(dateFormat)` | str | `yyyy-MM-dd` | stockChart |  |
| `stock.dateRangePanel` | Ввод диапазона дат | Общие | `(dateRangePanel)` | bool | `False` | stockChart |  |
| `stock.dateZoomPanel` | Кнопки зумирования | Общие | `(dateZoomPanel)` | bool | `False` | stockChart |  |
| `stock.refresh` | Интервальное обновление | Данные | `(refresh)` | bool | `False` | stockChart |  |
| `stock.scrollbarDisabled` | enable (инверт.) | Скроллбар | `scrollbar.disabled` | bool | `False` | stockChart |  |
| `style.autoColor` | Auto Color | Стиль | `(styleCommons.autoColor)` | enum | `False` | lineChart, areaChart, barChart |  |
| `style.clustered` | Clustered | Стиль | `(styleCommons.clustered)` | bool | — | lineChart, areaChart |  |
| `style.labelsEnabled` | вкл | Подписи | `labels.visible` | bool | — | lineChart, areaChart |  |
| `style.lineMode` | Line Mode | Стиль | `(styleCommons.lineMode)` | enum | — | lineChart, areaChart |  |
| `style.lineWidth` | Толщина линии | Осн. стиль | `(styleCommons.lineWidth)` | int | `2` | lineChart, areaChart |  |
| `style.markerMode` | Marker Mode | Стиль | `(styleCommons.markerMode)` | str | `circle` | lineChart, areaChart |  |
| `style.markerWidth` | Размер маркера | Осн. стиль | `(styleCommons.markerWidth)` | int | `0` | lineChart, areaChart |  |
| `style.outlineWidth` | Ширина ободка | Осн. стиль | `(styleCommons.outlineWidth)` | int | `0` | lineChart, areaChart |  |
| `style.smoothing` | Сглаживание | Осн. стиль | `(styleCommons.smoothing)` | float | `0` | lineChart, areaChart, barChart |  |
| `style.visType` | Vis Type | Стиль | `(styleCommons.visType)` | enum | — | lineChart, areaChart |  |
| `subtitle` | Подзаголовок | Общие | `(subtitle)` | str | — | barChart, lineChart, pieChart, stockChart, sunburstChart, parallelCoordsChart, treeGraph, treeMap, totalsPanelV2, subheader, table |  |
| `summColor` | (Цвет итога) | Стилизация | `(summColor)` | color | `rgba(0,0,0,1)` | pieChart |  |
| `summEnabled` | Отображать итог | Стилизация | `(summEnabled)` | bool | `False` | pieChart |  |
| `summFontSize` | Шрифт итога | Стилизация | `(summFontSize)` | int | `32` | pieChart |  |
| `sunburst.colorsEnabled` | Многоцветность | Стилизация | `(colorsEnabled)` | bool | `True` | sunburstChart |  |
| `sunburst.darkLabels` | Тёмные подписи | Общие | `(darkLabels)` | bool | `False` | sunburstChart |  |
| `sunburst.ellipsisLength` | Лимит длины подписи | Общие | `(ellipsisLength)` | int | `15` | sunburstChart |  |
| `sunburst.filterMode` | Режим фильтра | Общие | `(filterMode)` | bool | `False` | sunburstChart |  |
| `sunburst.fontFamily` | Тип шрифта | Стилизация | `(font.family)` | str | `Arial` | sunburstChart |  |
| `sunburst.fontSize` | Размер шрифта | Стилизация | `(font.size)` | float | `0.8` | sunburstChart |  |
| `sunburst.layerButtons` | Кнопки управления слоями | Общие | `(layerButtons)` | bool | `False` | sunburstChart |  |
| `sunburst.layerExpand` | Тип разворачивания | Общие | `(layerExpand)` | bool | `False` | sunburstChart |  |
| `sunburst.minPercent` | Порог скрывания подписей % | Общие | `(minPercent)` | float | `0.0` | sunburstChart |  |
| `sunburst.precision` | Точность чисел | Общие | `(precision)` | int | `0` | sunburstChart |  |
| `sunburst.splittedMode` | Двустрочные подписи | Общие | `(splittedMode)` | bool | `False` | sunburstChart |  |
| `sunburst.visibleLayers` | Начальное кол-во слоёв | Общие | `visibleLayersNumber` | int | `2` | sunburstChart |  |
| `switch.filterType` | Filter Type | Переключатель | `(filterType)` | enum | `column` | SwitchControlPanel |  |
| `switch.selectorTitleOverride` | Selector Title Override | Переключатель | `(selectorTitleOverride)` | str | — | SwitchControlPanel |  |
| `table.headersBackground` | Цвет фона/текста заголовков, зебры, тема | Стилизация | `headersBackground` | color | — | table |  |
| `table.headersColor` | Headers Color | Таблица | `headersColor` | color | — | table |  |
| `table.linkByForRow` | Гиперссылка строки | Общие | `linkByForRow` | str | — | table |  |
| `table.precision` | Точность чисел | Общие | `precision` | int | `-1` | table |  |
| `table.showNumberLineInHeader` | Отобразить кол-во строк | Общие | `showNumberLineInHeader` | bool | `False` | table |  |
| `table.theme` | Theme | Таблица | `theme` | enum | — | table |  |
| `table.zebraColor` | Zebra Color | Таблица | `zebraColor` | color | — | table |  |
| `table.zebraType` | Тип «зебры» | Стилизация | `zebraType` | enum | `none` | table |  |
| `tabs.autoApply` | Auto Apply | Вкладки | `(autoApply)` | bool | `True` | tabsPanel |  |
| `tabs.height` | Height | Вкладки | `(height)` | int | `33` | tabsPanel |  |
| `tabs.orientation` | Ориентация (В/Г) | Общие | `(orientation)` | enum | `h` | tabsPanel |  |
| `tabs.visuals` | Visuals | Вкладки | `visuals` | any | `[]` | tabsPanel |  |
| `text.maximizable` | Maximizable | Общие | `(maximizable)` | bool | `True` | textBlock |  |
| `text.noexport` | Noexport | Общие | `(noexport)` | bool | `True` | textBlock |  |
| `textAlign` | Выравнивание текста | Макет | `textAlign` | enum | `center` | totalsPanelV2 |  |
| `tilemap.allowTiles` | через slug | (Фон плиток) | `(background.allowTiles)` | bool | `True` | tilemapChart |  |
| `tilemap.autoZoom` | Автомасштаб | Общие | `(autoZoom)` | bool | `True` | tilemapChart |  |
| `tilemap.bgTileColor` | Bg Tile Color | Плиточная карта | `(background.backgroundColor)` | color | `gray` | tilemapChart |  |
| `tilemap.deltaK` | enable / Коэф. разделителя | Группир. | `grouping.deltaK` | float | `0.15` | tilemapChart |  |
| `tilemap.endColor` | End Color | Плиточная карта | `(legend.color[1])` | color | `red` | tilemapChart |  |
| `tilemap.filterMode` | Режим фильтра | Общие | `(filterMode)` | bool | `False` | tilemapChart |  |
| `tilemap.grouping` | enable / Коэф. разделителя | Группир. | `grouping.enabled` | bool | `True` | tilemapChart |  |
| `tilemap.legendVisible` | видимость / позиция | Легенда | `(legend.visible)` | bool | `True` | tilemapChart |  |
| `tilemap.legendX` | Legend X | Плиточная карта | `legend.positionX` | enum | `right` | tilemapChart |  |
| `tilemap.legendY` | Legend Y | Плиточная карта | `legend.positionY` | enum | `bottom` | tilemapChart |  |
| `tilemap.nameFontSize` | Размер текста | Плитки | `(tiles.nameFontSize)` | int | `12` | tilemapChart |  |
| `tilemap.popup` | Подсказка (popup) | Плитки | `popupEnabled` | bool | `False` | tilemapChart |  |
| `tilemap.specialTiles` | Отмечать города | Плитки | `(tiles.specialTiles)` | bool | `False` | tilemapChart |  |
| `tilemap.startColor` | Цвет 1 / Цвет 2 (шкала) | Легенда | `(legend.color[0])` | color | `blue` | tilemapChart |  |
| `tilemap.tileSize` | Размер плитки | Плитки | `(tileSize)` | int | `40` | tilemapChart |  |
| `tilemap.tileType` | Тип плиток | Плитки | `(tiles.type)` | enum | `square` | tilemapChart |  |
| `totals.grandSumsFixed` | Закрепить общие итоги | Итоги | `isGrandSumsFixed` | bool | `False` | pivotChart |  |
| `totals.noGrandSumsX` | Скрыть общие итоги по строкам | Итоги | `isNoGrandSumsX` | bool | `False` | pivotChart |  |
| `totals.noGrandSumsY` | No Grand Sums Y | Итоги | `isNoGrandSumsY` | bool | `False` | pivotChart |  |
| `totals.noSums` | Скрыть промежуточные итоги по строкам | Итоги | `isNoSums` | bool | `False` | pivotChart |  |
| `totals.sumColumnAtLeft` | Общие итоги слева/сверху, скрыть по колонкам | Итоги | `sumColumnAtLeft` | bool | `False` | pivotChart |  |
| `totals.sumRowAtTop` | Sum Row At Top | Итоги | `sumRowAtTop` | bool | `False` | pivotChart |  |
| `treemap.filterMode` | enable (checkbox) | Режим фильтра | `filterMode` | bool | `True` | treeMap |  |
| `treemap.precision` | Точность чисел | Общие | `precision` | int | `-1` | treeMap |  |
| `truncateTitle` | Обрезать заголовок | Макет | `truncateTitle` | bool | `False` | totalsPanelV2 |  |
| `viewType.addInvertedSwitch` | Add Inverted Switch | Тип фильтра | `addInversedFilter` | bool | `False` | FilterControlPanel |  |
| `viewType.autoApply` | Auto Apply | Тип фильтра | `autoApply` | bool | `True` | FilterControlPanel |  |
| `viewType.clearSelection` | Clear Selection | Тип фильтра | `clearSelection` | bool | `False` | FilterControlPanel |  |
| `viewType.displayType` | Display Type | Тип фильтра | `filterType` | enum | `dropdown` | FilterControlPanel |  |
| `viewType.hideEmptyLines` | Hide Empty Lines | Тип фильтра | `hideEmptyLines` | bool | `False` | FilterControlPanel |  |
| `viewType.inversed` | Inversed | Тип фильтра | `inversed` | bool | `False` | FilterControlPanel |  |
| `viewType.multiselect` | Multiselect | Тип фильтра | `multipleChoice` | bool | `True` | FilterControlPanel |  |
| `viewType.resetEnabled` | Reset Enabled | Тип фильтра | `resetEnabled` | bool | `False` | FilterControlPanel | устар. |
| `viewType.searchEnabled` | Search Enabled | Тип фильтра | `searchInBaseMode` | bool | `False` | FilterControlPanel |  |
| `viewType.showAll` | Show All | Тип фильтра | `showAll` | bool | `False` | FilterControlPanel | устар. |
| `viewType.sortSelectedOptionsToTop` | Sort Selected Options To Top | Тип фильтра | `sortSelectedOptionsToTop` | bool | `False` | FilterControlPanel |  |
| `viewType.unlimitedSearch` | Unlimited Search | Тип фильтра | `unlimitedSearch` | bool | `False` | FilterControlPanel |  |
| `viewType.updateOnApply` | Update On Apply | Тип фильтра | `updateOnApply` | bool | `False` | FilterControlPanel |  |
| `viewType.updateOnCloseDropdown` | Update On Close Dropdown | Тип фильтра | `updateOnCloseDropdown` | bool | `False` | FilterControlPanel |  |
| `visuals.autoColor` | Auto Color | Стиль элементов | `styleCommons.autoColor` | bool | `True` | оформительские |  |
| `visuals.bubbleMaxSize` | Радиус макс | Общие | `maxRadius` | int | `30` | bubbleChart |  |
| `visuals.bubbleMinSize` | Радиус мин | Общие | `minRadius` | int | `3` | bubbleChart |  |
| `visuals.caption.color` | Цвет заголовка | Заголовок | `(visuals[0].color)` | color | — | totalsPanelV2 |  |
| `visuals.caption.font.size` | Размер заголовка (em) | Заголовок | `(visuals[0].font.size)` | float | `1.0` | totalsPanelV2 |  |
| `visuals.caption.font.weight` | Жирность заголовка | Заголовок | `(visuals[0].font.weight)` | int | `400` | totalsPanelV2 |  |
| `visuals.caption.visible` | Показывать заголовок | Заголовок | `(visuals[0].visible)` | bool | `True` | totalsPanelV2 |  |
| `visuals.chartType` | тип визуализации | Осн.стиль | `visualType` | str | — | barChart |  |
| `visuals.clustered` | Clustered | Стиль элементов | `styleCommons.clustered` | bool | `False` | barChart | инверт. |
| `visuals.colorMax` | Цвет максимума | Общие+Стилизация | `colorMax` | color | `#eac736` | parallelCoordsChart |  |
| `visuals.colorMin` | Цвет минимума | Общие+Стилизация | `colorMin` | color | `#d94e5d` | parallelCoordsChart |  |
| `visuals.colorPalette` | палитра | Осн.стиль | `(visuals[0].colorPalette)` | any | `pal_2018` | оформительские |  |
| `visuals.columnBorderRadius` | Column Border Radius | Стиль элементов | `(visuals[0].columnBorderRadius)` | int | `0` | barChart |  |
| `visuals.columnWidth` | Ширина столбцов | Стиль элем. | `styleCommons.columnWidth` | int | `80` | barChart |  |
| `visuals.fillOpacity` | Цвет заливки | Стиль элем. | `((deprecated → не пишется))` | float | `0.5` | areaChart | устар. |
| `visuals.innerRadius` | Inner Radius | Стиль элементов | `innerRadius` | int | `0` | pieChart |  |
| `visuals.lineDashStyle` | Line Dash Style | Стиль элементов | `styleCommons.lineMode` | enum | `solid` | lineChart, areaChart |  |
| `visuals.lineWidth` | Толщина | Стилизация (series) | `(visuals[0].lineWidth)` | int | `2` | lineChart, areaChart |  |
| `visuals.mainColor` | Основной цвет | Стиль элем. | `(visuals[0].mainColor)` | color | — | оформительские |  |
| `visuals.markerLabels` | Marker Labels | Стиль элементов | `(visuals[0].markerLabels)` | bool | `False` | lineChart, areaChart, bubbleChart |  |
| `visuals.markerSize` | Marker Size | Стиль элементов | `styleCommons.markerWidth` | int | `5` | lineChart, areaChart |  |
| `visuals.markerType` | Marker Type | Стиль элементов | `styleCommons.markerMode` | enum | `circle` | lineChart, areaChart |  |
| `visuals.smoothing` | Smoothing | Стиль элементов | `(visuals[0].smoothing)` | bool | `False` | lineChart, areaChart |  |
| `visuals.startAngle` | Start Angle | Стиль элементов | `startAngle` | int | `0` | pieChart |  |
| `visuals.subcaption.color` | Цвет подзаголовка | Подзаголовок | `(visuals[0].color)` | color | — | totalsPanelV2 |  |
| `visuals.subcaption.font.size` | Размер подзаголовка (em) | Подзаголовок | `(visuals[0].font.size)` | float | `1.0` | totalsPanelV2 |  |
| `visuals.subcaption.visible` | Показывать подзаголовок | Подзаголовок | `(visuals[0].visible)` | bool | `True` | totalsPanelV2 |  |
| `visuals.trend.color` | Цвет индикатора тренда | Тренд | `(visuals[0].color)` | color | — | totalsPanelV2 |  |
| `visuals.trend.visible` | Показывать индикатор тренда | Тренд | `(visuals[0].visible)` | bool | `True` | totalsPanelV2 |  |
| `visuals.value.color` | Цвет значения | Значение | `(visuals[0].color)` | color | — | totalsPanelV2 |  |
| `visuals.value.decimals` | Знаков после запятой (значение) | Значение | `(visuals[0].decimals)` | int | `-1` | totalsPanelV2 |  |
| `visuals.value.font.family` | Шрифт значения | Значение | `(visuals[0].font.family)` | str | — | totalsPanelV2 |  |
| `visuals.value.font.size` | Размер значения (em) | Значение | `(visuals[0].font.size)` | float | `2.8` | totalsPanelV2 |  |
| `visuals.value.font.style` | Начертание значения | Значение | `(visuals[0].font.style)` | enum | `normal` | totalsPanelV2 |  |
| `visuals.value.font.weight` | Жирность значения | Значение | `(visuals[0].font.weight)` | int | `600` | totalsPanelV2 |  |
| `visuals.value.link` | Ссылка по клику (значение) | Значение | `(visuals[0].link)` | str | — | totalsPanelV2 |  |
| `visuals.value.linkTarget` | Открывать ссылку в | Значение | `(visuals[0].linkTarget)` | enum | `_blank` | totalsPanelV2 |  |
| `visuals.value.outlineColor` | Цвет обводки значения | Значение | `(visuals[0].outlineColor)` | color | — | totalsPanelV2 |  |
| `visuals.value.outlineWidth` | Ширина обводки значения (px) | Значение | `(visuals[0].outlineWidth)` | int | `0` | totalsPanelV2 |  |
| `visuals.value.visible` | Показывать значение | Значение | `(visuals[0].visible)` | bool | `True` | totalsPanelV2 |  |
