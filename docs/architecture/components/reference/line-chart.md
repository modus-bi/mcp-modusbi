# Линейная диаграмма

Тип компонента: `HsLineAMchartsChart`

## Описание

Линейная диаграмма соединяет точки данных линиями вдоль горизонтальной оси категорий и предназначена для показа трендов, динамики и временных рядов. Поддерживает несколько серий (несколько линий), сглаживание, маркеры на точках, пунктирные линии, дополнительную ось значений, стек и 100%-структуру, а также комбинирование с другими типами визуализации в одном компоненте.

Линейная, столбчатая и площадная диаграммы имеют общую конфигурацию: различаются только внутренний тип (`chartType`) и тип отрисовки по умолчанию (`visualType`). Поэтому большинство настроек и слагов совпадают.

## Когда применять

- Тренд по времени: дата или период на оси категорий, показатель на оси значений.
- Сравнение динамики нескольких показателей — несколько линий на одном поле графика.
- Непрерывные временные ряды, где важна форма кривой, а не отдельные значения.
- Комбинированные диаграммы: одна метрика — линия, другая — столбцы (через дополнительную ось значений).

## Когда не подходит

- Сравнение категорий без временной последовательности — лучше столбчатая диаграмма.
- Накопление объёмов с акцентом на заполненной площади — лучше площадная диаграмма.
- Доли одного набора (части целого) — лучше круговая диаграмма.
- Менее трёх точек данных — линия теряет смысл, рассмотрите панель показателей или таблицу.

## Поля и оси

Компонент использует те же четыре типа полей, что и столбчатая диаграмма:

- **Категории** — поле оси X. Обычно дата или период (для трендов), реже текст или число. Можно указать несколько полей — они образуют иерархический разрез с интерактивным переходом между уровнями. Агрегация для категорий не применяется.
- **Значения** — числовое поле, задающее высоту точки. Каждое поле в оси значений — отдельная линия. Для значений агрегация обязательна.
- **Серии** (необязательно) — поле-разрез: каждое его уникальное значение становится отдельной линией. Если пусто — все данные идут одной линией (или по линии на поле значений).
- **Дополнительная ось значений** (необязательно) — вторая шкала Y для метрик с другим масштабом.

Для оси категорий рекомендуется тип поля `date` при работе с датами — тогда строится временная шкала с автоматическим форматом подписей (по году, месяцу или дню в зависимости от периода данных).

### Правила агрегации

Агрегация управляет тем, как несколько строк датасета сводятся к одной точке:

- **Предагрегированный датасет** (значения уже посчитаны через `GROUP BY` в SQL) — передавайте агрегацию явно (например, `aggregation="max"`). На готовой группе любая агрегация вернёт то же единственное значение, но указать её необходимо: без агрегации поле значений считается неготовым и диаграмма выходит пустой.
- **Сырой датасет, нужна сумма по категории** — `aggregation="sum"`.
- **Среднее по категории** — `aggregation="avg"` (аналогично `min`, `max`, `count`).
- Значение `aggregation="none"` означает «не агрегировать» — для линейной диаграммы почти не используется.

Если поле значений осталось без агрегации, диаграмма обычно выходит пустой.

## Параметры добавления

Помимо привязки к датасету и полям, при добавлении компонента доступны параметры:

| Параметр | Назначение |
|----------|-----------|
| `x`, `y`, `w`, `h` | Позиция и размер компонента в сетке отчёта |
| `orientation` | Ориентация: `"v"` (вертикально) или `"h"` (горизонтально) |
| `stacking` | Режим серий: `"none"` (раздельно), `"normal"` (стек), `"percent"` (100%-структура) |
| `series_field` | Поле-разрез для нескольких линий |
| `aggregation` | Агрегация значений (`sum`, `avg`, `min`, `max`, `count`, `none`) |
| `preset` | Готовый визуальный пресет оформления |

## Формат данных

Особого формата не требуется: подойдёт обычная таблица «категория + числовая метрика». Для тренда поместите поле даты в `category_field` — построится временная шкала. Для нескольких линий либо добавьте текстовое поле-разрез в ось серий (`series_field`), либо передайте несколько числовых полей значений — каждое станет отдельной линией. Несколько полей значений указываются в `value_field` через запятую: `value_field="revenue,profit"`.

## Пример

Линейный график динамики по годам на предагрегированном датасете:

```python
component_crud(
    action="add",
    report_id=35,
    component_type="HsLineAMchartsChart",
    title="Динамика продаж",
    dataset_id=54,
    category_field="year",
    value_field="summa_rub",
    aggregation="sum",
    x=0, y=0, w=24, h=14,
    legend_visible=True,
)
```

Сглаженная линия с маркерами на точках — задаётся через `config_overrides`:

```python
component_crud(
    action="add",
    report_id=35,
    component_type="HsLineAMchartsChart",
    title="Тренд выручки",
    dataset_id=54,
    category_field="month",
    value_field="revenue",
    aggregation="sum",
    config_overrides={
        "style.smoothing": 1.3,
        "visuals.markerType": "circle",
        "visuals.markerSize": 6,
        "visuals.lineWidth": 3,
    },
)
```

Несколько линий по полю-разрезу с легендой:

```python
component_crud(
    action="add",
    report_id=35,
    component_type="HsLineAMchartsChart",
    title="Продажи по типам товара",
    dataset_id=54,
    category_field="month",
    value_field="sales",
    series_field="product_type",
    aggregation="sum",
    x=0, y=14, w=24, h=14,
    config_overrides={
        "legend.visible": True,
        "visuals.lineDashStyle": "solid",
    },
)
```

Здесь `component_crud` — это RPC-метод MCP-сервера (вызов инструмента), а не REST-эндпоинт; `component_idx` в других действиях — 0-based индекс компонента в отчёте.

## JSON-конфигурация

Сервер собирает и хранит конфигурацию компонента в JSON. Ниже — аннотированная структура линейной диаграммы: рядом с каждым ключом указано, что он задаёт и каким слагом управляется (полное соответствие — в таблице «Все настройки»).

```jsonc
{
  "type": "HsLineAMchartsChart",                // тип компонента (его отдаёт component_crud action="types_list")
  "config": {
    "title": "Динамика продаж",                 // заголовок компонента
    "chartType": "lineChart",                   // внутренний тип диаграммы (фиксирован)
    "visualType": "line",                       // тип отрисовки по умолчанию: line|area|column|bar  ← слаг visuals.chartType
    "orientation": "v",                         // ориентация: "v"|"h"  (параметр orientation при добавлении)
    "showtitle": true,                          // показывать заголовок            ← слаг showtitle
    "bgColor": "rgba(255, 255, 255, 1)",        // цвет фона                       ← слаг bgColor
    "baseColor": "#1F77B4",                     // базовый цвет линий              ← слаг data.baseColor
    "colorStep": 0,                             // шаг яркости между сериями       ← слаг data.colorStep
    "margin":  { "l": 5, "r": 10, "t": 10, "b": 5, "pad": 0 },    // отступы       ← слаги margin.l/r/t/b/pad
    "outline": { "enabled": false, "width": 4 },                  // рамка         ← слаги outline.enabled/width
    "legend": {                                 // легенда
      "visible": true,                          //   показывать                    ← слаг legend.visible
      "position": "auto",                       //   позиция                       ← слаг legend.position
      "order": "normal"                         //   порядок (normal|reversed)     ← слаг legend.order
    },
    "labels": {                                 // подписи значений на точках
      "visible": false,                         //   показывать                    ← слаг labels.visible
      "position": "auto"                        //   позиция                       ← слаг labels.position
    },
    "styleCommons": {                           // общие стили всех линий (слаги style.*)
      "smoothing": 0,                           //   сглаживание: 0=ломаная, 1.3=кривая  ← слаг style.smoothing
      "lineMode": null,                         //   тип линии: null|dot|dash|longdash (null = сплошная)  ← слаг visuals.lineDashStyle
      "lineWidth": 2,                           //   толщина линии (px)             ← слаг visuals.lineWidth / style.lineWidth
      "markerMode": "circle",                   //   форма маркера                  ← слаг visuals.markerType
      "markerWidth": 0,                         //   размер маркера (0=скрыт)       ← слаг visuals.markerSize
      "autoColor": false                        //   авто-раскраска серий          ← слаг style.autoColor
    },
    "axes": [                                   // оси данных (поля привязываются параметрами при добавлении)
      { "name": "filters",    "type": "filters",    "fields": [] },              // фильтры компонента
      { "name": "categories", "type": "categories", "scaleType": "category",     // ось категорий ← category_field
        "fields": [
          { "name": "year", "alias": "Год", "type": "date", "datasetId": 54 }    // для трендов тип date + scaleType "date"
      ]},
      { "name": "series",     "type": "series",     "fields": [] },              // ось серий-разреза ← series_field
      { "name": "values",     "type": "values",     "fields": [                  // ось значений  ← value_field + aggregation
          { "name": "summa_rub", "alias": "Продажи", "type": "number", "agg": "sum", "datasetId": 54 }
      ]}
    ],
    "visuals": []                               // визуальные параметры серий: массив (по элементу на серию);
                                                // слаги visuals.* пишутся в visuals[0].* — см. таблицу ниже
  }
}
```

> Каждая линия — это отдельное поле в оси значений (либо отдельное значение поля-разреза в оси серий). Индивидуальный цвет, пунктир или тип линии для конкретной серии задаются объектами в массиве `visuals` с привязкой по имени поля.

Каждый ключ внутри `config` соответствует строке в таблице ниже. Колонка **JSON-путь** показывает, где значение хранится в конфиге. Для вложенных параметров используется запись `объект[раздел].ключ` (например, `axes[categories].showlabels` — это ключ `showlabels` внутри оси категорий в `config.axes`). Пустой путь означает верхний уровень `config`.

> Таблица ниже сгенерирована автоматически из схемы слагов сервера. Если в ней найдена ошибка, её правят в `config_schema.py` и пересобирают документацию скриптом `scripts/gen_component_tables.py` — не в этом файле.

<!-- AUTO-TABLE:START (регенерируется scripts/gen_component_tables.py — правьте config_schema.py, не этот блок) -->

## Все настройки (config_overrides)

Полный перечень слагов этого типа — специфичные для типа и общие оформительские. Колонки: **UI-контрол** — название в панели настроек портала (пусто = прямого UI-контрола нет, настройка только через `config_overrides`); **MCP-слаг** — ключ в `config_overrides`; **JSON-путь** — куда настройка пишется в конфиг и откуда её читает отображение (это и есть «фронт-ключ»; путь в `(скобках)` обрабатывается секционно — итоговый ключ внутри указанной секции конфига); **Тип**; **По умолчанию**. Полный справочник по всем типам — [Справочник настроек](../slugs/by-type.md).

### Данные

| UI-контрол | MCP-слаг | JSON-путь | Тип | По умолчанию | Прим. |
|---|---|---|---|---|---|
| Дополнять пустые Кат./Серии | `data.autofillEmptySeries` | `series.autoFill` | bool | `False` |  |
| Интервальное обновление | `data.intervalRefresh` | `refresh` | bool | `False` |  |
| — | `data.intervalSeconds` | `refreshTime` | int | `60` |  |
| Лимит при запросе | `data.rowsLimit` | `rowsLimit` | int | `5000` |  |
| Лимит при экспорте | `data.rowsLimitToExport` | `rowsLimitToExport` | int | `0` |  |
| — | `data.rowsLimitToShow` | `rowsLimitToShow` | int | `0` |  |
| — | `data.seriesLimitToShow` | `seriesLimitToShow` | int | `0` |  |
| Анимация обновления | `hideSpinner` | `(hideSpinner)` | bool | `False` |  |

### Основной стиль

| UI-контрол | MCP-слаг | JSON-путь | Тип | По умолчанию | Прим. |
|---|---|---|---|---|---|
| Толщина линии | `style.lineWidth` | `(styleCommons.lineWidth)` | int | `2` | только этот тип |
| Размер маркера | `style.markerWidth` | `(styleCommons.markerWidth)` | int | `0` | только этот тип |
| Ширина ободка | `style.outlineWidth` | `(styleCommons.outlineWidth)` | int | `0` | только этот тип |
| Сглаживание | `style.smoothing` | `(styleCommons.smoothing)` | float | `0` | только этот тип |
| палитра | `visuals.colorPalette` | `(visuals[0].colorPalette)` | any | `pal_2018` |  |

### Стилизация

| UI-контрол | MCP-слаг | JSON-путь | Тип | По умолчанию | Прим. |
|---|---|---|---|---|---|
| — | `style.autoColor` | `(styleCommons.autoColor)` | enum | `False` | только этот тип |
| — | `style.clustered` | `(styleCommons.clustered)` | bool | — | только этот тип |
| — | `style.lineMode` | `(styleCommons.lineMode)` | enum | — | только этот тип |
| — | `style.markerMode` | `(styleCommons.markerMode)` | str | `circle` | только этот тип |
| — | `style.visType` | `(styleCommons.visType)` | enum | — | только этот тип |

### Стиль элементов

| UI-контрол | MCP-слаг | JSON-путь | Тип | По умолчанию | Прим. |
|---|---|---|---|---|---|
| — | `visuals.autoColor` | `styleCommons.autoColor` | bool | `True` |  |
| — | `visuals.lineDashStyle` | `styleCommons.lineMode` | enum | `solid` | только этот тип |
| Основной цвет | `visuals.mainColor` | `(visuals[0].mainColor)` | color | — |  |
| — | `visuals.markerLabels` | `(visuals[0].markerLabels)` | bool | `False` | только этот тип |
| — | `visuals.markerSize` | `styleCommons.markerWidth` | int | `5` | только этот тип |
| — | `visuals.markerType` | `styleCommons.markerMode` | enum | `circle` | только этот тип |
| — | `visuals.smoothing` | `(visuals[0].smoothing)` | bool | `False` | только этот тип |

### Оси

| UI-контрол | MCP-слаг | JSON-путь | Тип | По умолчанию | Прим. |
|---|---|---|---|---|---|
| — | `axes.autoZoom` | `axes[values].autoZoom` | bool | `False` |  |
| Сетка | `axes.categoryGrid` | `axes[categories].showgrid` | bool | `False` |  |
| — | `axes.categoryLabelAngle` | `axes[categories].tickangle` | int | `0` |  |
| — | `axes.categoryLabels` | `axes[categories].showlabels` | bool | `True` |  |
| — | `axes.categoryMaxLabelWidth` | `axes[categories].maxLabelWidth` | int | `0` |  |
| — | `axes.categoryMinGridWidth` | `axes[categories].minGridWidth` | int | `0` |  |
| — | `axes.categoryScale` | `axes[categories].showscale` | bool | `True` |  |
| — | `axes.categoryScrollable` | `axes[categories].scrollable` | bool | `False` |  |
| — | `axes.categoryScrollbar` | `axes[categories].fixedZoom` | bool | `False` |  |
| — | `axes.categoryTitle` | `axes[categories].showtitle` | bool | `False` |  |
| — | `axes.customZoom` | `axes[categories].customZoom` | bool | `False` |  |
| — | `axes.firstLabel` | `axes[values].showFirstLabel` | bool | `True` |  |
| — | `axes.firstTick` | `axes[values].showFirstTick` | bool | `True` |  |
| — | `axes.labelsAccuracy` | `axes[values].labelsAccuracy` | int | `2` |  |
| — | `axes.lastLabel` | `axes[values].showLastLabel` | bool | `True` |  |
| — | `axes.lastTick` | `axes[values].showLastTick` | bool | `True` |  |
| — | `axes.rangeMode` | `axes[values].rangeMode` | enum | `normal` |  |
| — | `axes.scaleType` | `axes[values].scaleType` | enum | `-` |  |
| — | `axes.selectedFieldIndex` | `axes[values].selectedFieldIndex` | int | `-2` |  |
| — | `axes.sortable` | `axes[values].sortable` | bool | `True` |  |
| Сетка | `axes.valueGrid` | `axes[values].showgrid` | bool | `False` |  |
| Подписи шкалы | `axes.valueLabels` | `axes[values].showlabels` | bool | `True` |  |
| — | `axes.valueScale` | `axes[values].showscale` | bool | `True` |  |
| — | `axes.valueShowMax` | `axes[values].showMax` | bool | `False` |  |
| — | `axes.valueShowMin` | `axes[values].showMin` | bool | `False` |  |
| — | `axes.valueTitle` | `axes[values].showtitle` | bool | `False` |  |

### Легенда

| UI-контрол | MCP-слаг | JSON-путь | Тип | По умолчанию | Прим. |
|---|---|---|---|---|---|
| — | `legend.bgColor` | `(legend.bgcolor)` | color | — |  |
| — | `legend.borderColor` | `(legend.bordercolor)` | color | — |  |
| — | `legend.borderWidth` | `(legend.borderwidth)` | int | `0` |  |
| Размер шрифта | `legend.fontSize` | `(legend.fontSize)` | int | `12` |  |
| Порядок | `legend.order` | `(legend.order)` | enum | `normal` |  |
| — | `legend.orientation` | `(legend.orientation)` | enum | `h` |  |
| — | `legend.percent` | `(legend.percent)` | bool | `False` |  |
| Положение | `legend.position` | `(legend.position)` | enum | `auto` |  |
| Реверс порядка | `legend.reverse` | _секционно_ | bool | `False` |  |
| вкл | `legend.visible` | `(legend.visible)` | bool | `True` |  |

### Подписи

| UI-контрол | MCP-слаг | JSON-путь | Тип | По умолчанию | Прим. |
|---|---|---|---|---|---|
| — | `labels.angle` | `(labels.angle)` | int | `0` |  |
| — | `labels.bypassCollisions` | `bypassCheckCollisions` | bool | `False` |  |
| enable / шрифт подписей / шрифт значений / интервал | `labels.fontSize` | `labels.inner.fontsize` | int | `12` |  |
| Скрыть если <N% | `labels.hidePercent` | `(labels.hidePercent)` | float | `0` |  |
| — | `labels.inner.fontsize` | `(labels.inner.fontsize)` | int | `12` |  |
| — | `labels.labelsColor` | `labels.inner.color` | color | — |  |
| — | `labels.outer.color` | `(labels.outer.color)` | color | `rgba(68,68,68,1)` |  |
| Размер шрифта | `labels.outer.fontsize` | `(labels.outer.fontsize)` | int | `12` |  |
| — | `labels.position` | `(labels.position)` | enum | `auto` |  |
| — | `labels.template` | `(labels.template)` | str | — |  |
| enable | `labels.visible` | `(labels.visible)` | bool | `False` |  |
| вкл | `style.labelsEnabled` | `labels.visible` | bool | `False` | только этот тип |

### Всплывающая подсказка

| UI-контрол | MCP-слаг | JSON-путь | Тип | По умолчанию | Прим. |
|---|---|---|---|---|---|
| — | `balloon.bgColor` | `balloon.bgcolor` | color | — |  |
| — | `balloon.combine` | `balloon.allSeriesPop` | bool | `False` |  |
| — | `balloon.fontColor` | `balloon.color` | color | — |  |
| Размер шрифта | `balloon.fontSize` | `balloon.fontsize` | int | `12` |  |
| Шаблон | `balloon.template` | `balloonTemplate` | str | — |  |
| вкл | `balloon.visible` | `(balloon.visible)` | bool | `True` |  |

### Отступы

| UI-контрол | MCP-слаг | JSON-путь | Тип | По умолчанию | Прим. |
|---|---|---|---|---|---|
| Отступ Низ | `margin.b` | `(margin.b)` | int | `5` |  |
| Отступ Лево | `margin.l` | `(margin.l)` | int | `5` |  |
| Внутренний отступ | `margin.pad` | `(margin.pad)` | int | `0` |  |
| Отступ Право | `margin.r` | `(margin.r)` | int | `10` |  |
| Отступ Верх | `margin.t` | `(margin.t)` | int | `10` |  |

### Рамка компонента

| UI-контрол | MCP-слаг | JSON-путь | Тип | По умолчанию | Прим. |
|---|---|---|---|---|---|
| Цвет | `outline.color` | `(outline.color)` | color | `#DDDFE4` |  |
| вкл | `outline.enabled` | `(outline.enabled)` | bool | `False` |  |
| Ширина | `outline.width` | `(outline.width)` | int | `4` |  |

### Общие

| UI-контрол | MCP-слаг | JSON-путь | Тип | По умолчанию | Прим. |
|---|---|---|---|---|---|
| Цвет фона | `bgColor` | _секционно_ | color | `rgba(255,255,255,1)` |  |
| Цвет фона 2 | `bgColor2` | _секционно_ | color | — |  |
| — | `expandH` | `(expandH)` | bool | `False` | только этот тип |
| — | `expandV` | `(expandV)` | bool | `False` | только этот тип |
| — | `fontSize` | `(fontSize)` | int | `12` |  |
| Градиент | `gradient` | _секционно_ | bool | `False` |  |
| — | `main.extraAxis` | `(main.extraAxis)` | bool | `False` | только этот тип |
| — | `nocopy` | `(nocopy)` | bool | `False` |  |
| — | `noexport` | `(noexport)` | bool | `False` |  |
| Заголовок | `showtitle` | `(showtitle)` | bool | `True` |  |
| Подзаголовок | `subtitle` | `(subtitle)` | str | `` | только этот тип |

### Стилизация (series)

| UI-контрол | MCP-слаг | JSON-путь | Тип | По умолчанию | Прим. |
|---|---|---|---|---|---|
| Толщина | `visuals.lineWidth` | `(visuals[0].lineWidth)` | int | `2` | только этот тип |

<!-- AUTO-TABLE:END -->

## Связанные

- [Каталог компонентов](../README.md)
- [Концепция: JSON-конфиг и слаги](../../concepts/components-json-slugs.md)
- [Справочник настроек (слаги)](../slugs/by-type.md)
- [Рецепты подготовки данных](../data-recipes.md)
- [Стилизация компонентов](../styling.md)
- [Фильтры и каскады](../filter-patterns.md)
- [Столбчатая диаграмма](bar-chart.md)
