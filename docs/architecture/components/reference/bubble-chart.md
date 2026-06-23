# Пузырьковая диаграмма

Тип компонента: `HsBubbleAMchartsChart`

## Описание

Пузырьковая диаграмма отображает данные сразу в нескольких измерениях: каждый объект — это пузырёк, положение которого задаётся двумя числовыми показателями (по горизонтали и по вертикали), а размер — третьим числовым показателем. Дополнительно цвет пузырька может кодировать четвёртое измерение. Это делает пузырьковую диаграмму удобным инструментом для поиска кластеров, выбросов и взаимосвязей между метриками.

Типичные применения — портфельный анализ (матрицы вида «рост — доля»), сравнение регионов или продуктов сразу по нескольким метрикам, визуализация корреляций с учётом объёма (например, цена × количество × выручка).

## Когда применять

- Анализ взаимосвязи двух числовых показателей с дополнительным измерением (размер).
- Сравнение объектов (регионов, продуктов, филиалов) сразу по 3–4 метрикам.
- Поиск кластеров и выбросов в многомерных данных.
- Портфельный анализ: матрицы «риск — доходность», «рост — доля рынка».

## Когда не подходит

- Один числовой показатель — лучше столбчатая или линейная диаграмма.
- Тренд по времени — лучше линейная или площадная диаграмма.
- Доли одного целого — лучше круговая диаграмма.
- Очень много объектов (обычно более 20–30 пузырьков на экране) — пузырьки начинают пересекаться, диаграмма теряет читаемость; уменьшите объём данных или используйте таблицу.
- Нужно точно считывать значения — используйте таблицу.

## Поля и оси

В отличие от других диаграмм, пузырьковая использует три оси значений плюс категориальную ось:

- **Категория** — текстовое поле, задающее объекты-пузырьки (подпись и значение для фильтрации). Агрегация не применяется.
- **Значение Y** — числовое поле, координата пузырька по вертикали. Агрегация обязательна (обычно `avg`).
- **Значение X** — числовое поле, координата пузырька по горизонтали. Агрегация обязательна (обычно `avg`).
- **Размер** — числовое поле, задающее радиус пузырька. Агрегация обязательна (обычно `sum` или `avg`). При желании в эту ось можно добавить второе поле — оно задаёт цвет пузырька (см. ниже).
- **Серии** (необязательно) — поле-разрез; обычно не используется, категоризация выполняется через категориальную ось.

При добавлении компонента поля X и Y передаются в параметре `value_field` через запятую. Порядок важен: первое поле — ось Y, второе — ось X (это исторический порядок, обратный привычному «X, Y»). Поле размера передаётся отдельным параметром `size_field`.

### Цвет пузырьков

Цвет можно задать несколькими способами:

- **Автоматически** — если поле цвета не указано, цвета берутся из палитры отчёта.
- **Строковым полем** — добавьте в ось размера второе поле (текстовое, агрегация `max`), значения которого содержат имя цвета или HEX-код без символа `#`.
- **Вычисляемым полем** — добавьте в ось размера вычисляемое поле с выражением `CASE WHEN ... THEN ... END`, где цвета указаны HEX-кодом без `#` в обратных кавычках (например, `` `FF0000` ``). Ветка `ELSE NULL` означает «взять цвет из палитры отчёта». Пример выражения:

  ```sql
  CASE WHEN growth_rate > 10 THEN `00FF00` ELSE `FF0000` END
  ```

### Правила агрегации

Агрегация управляет тем, как несколько строк датасета сводятся к одному пузырьку:

- **Предагрегированный датасет** (значения уже посчитаны через `GROUP BY` в SQL) — агрегацию всё равно нужно указать явно (например, `aggregation="max"`). Это требование отображения: компонент читает агрегацию из поля и без неё считает поле значений неготовым, из-за чего диаграмма выходит пустой.
- **Сырой датасет** — задайте нужную агрегацию по каждому показателю (`avg` для координат, `sum`/`avg` для размера). Для категориальной оси агрегация не применяется.

## Параметры добавления

Помимо привязки к датасету и полям, при добавлении компонента доступны параметры:

| Параметр | Назначение |
|----------|-----------|
| `category_field` | Текстовое поле объектов-пузырьков (категория) |
| `value_field` | Числовые поля координат через запятую: первое — ось Y, второе — ось X |
| `size_field` | Числовое поле размера пузырька (при необходимости — CSV из размера и поля цвета) |
| `aggregation` | Агрегация числовых полей (`sum`, `avg`, `min`, `max`, `count`); обязательна — без неё диаграмма пустая, явного значения по умолчанию нет |
| `x`, `y`, `w`, `h` | Позиция и размер компонента в сетке отчёта |
| `preset` | Готовый визуальный пресет оформления |

## Формат данных

Подойдёт обычная таблица, где каждая строка — отдельный объект: одно текстовое поле для категории и три числовых поля для координат X, Y и размера. Для окраски пузырьков по данным добавьте текстовое поле с цветом (имя или HEX без `#`) либо используйте вычисляемое поле с `CASE WHEN`.

## Пример

Базовая пузырьковая диаграмма: регионы по средней цене (Y) и среднему количеству (X), размер — суммарная выручка:

```python
component_crud(
    action="add",
    report_id=35,
    component_type="HsBubbleAMchartsChart",
    title="Регионы: цена × количество × выручка",
    dataset_id=54,
    category_field="region",
    value_field="price_rub,amount",   # Y = price_rub, X = amount
    size_field="summa_rub",
    aggregation="avg",   # глобально для всех числовых полей; для размера обычно sum или avg
    x=0, y=0, w=28, h=14,
    legend_visible=True,
)
```

Параметр `aggregation` применяется ко всем числовым полям компонента сразу. Если размеру пузырька нужна другая агрегация (например, `sum` при `avg` для координат), задайте её отдельно — через `config_overrides` или правкой поля в оси `values`.

Диаграмма с настройкой размеров пузырьков и фиксированными осями через `config_overrides`:

```python
component_crud(
    action="add",
    report_id=35,
    component_type="HsBubbleAMchartsChart",
    title="Матрица «рост — доля»",
    dataset_id=54,
    category_field="product",
    value_field="growth_rate,market_share",
    size_field="revenue",
    aggregation="avg",
    config_overrides={
        "visuals.bubbleMinSize": 5,
        "visuals.bubbleMaxSize": 35,
        "bubble.strictMinMax": True,
        "bubble.zoomToEdges": True,
        "bubble.showScrollbars": False,
        "bubble.legendForSize": True,
    },
)
```

Здесь `component_crud` — это RPC-метод MCP-сервера (вызов инструмента), а не REST-эндпоинт; `component_idx` в других действиях — 0-based индекс компонента в отчёте.

## JSON-конфигурация

Сервер собирает и хранит конфигурацию компонента в JSON. Ниже — аннотированная структура пузырьковой диаграммы: рядом с каждым ключом указано, что он задаёт и каким слагом управляется (полное соответствие — в таблице «Все настройки»).

В отличие от обычных диаграмм, пузырьковая использует расширенный набор осей: фильтры (`filters`), одну категориальную ось (`categories`), необязательную ось серий-разреза (`series`) и три оси значений — координата Y (`yvalues`), координата X (`xvalues`) и размер (`values`, сюда же опционально добавляется поле цвета).

```jsonc
{
  "type": "HsBubbleAMchartsChart",              // тип компонента (его отдаёт component_crud action="types_list")
  "config": {
    "title": "Регионы: цена × количество × выручка",  // заголовок компонента
    "chartType": "bubble",                      // внутренний тип диаграммы (фиксирован)
    "visualType": "bubble",                     // визуальный тип для отображения
    "showtitle": true,                          // показывать заголовок            ← слаг showtitle
    "noexport": false,                          // запретить экспорт               ← слаг noexport
    "nocopy": false,                            // запретить копирование данных    ← слаг nocopy
    "bgColor": "rgba(255, 255, 255, 1)",        // цвет фона                       ← слаг bgColor
    "margin":  { "l": 5, "r": 10, "t": 10, "b": 5, "pad": 0 },    // отступы       ← слаги margin.l/r/t/b/pad
    "outline": { "enabled": false, "width": 4 },                  // рамка         ← слаги outline.enabled/width
    "minRadius": 3,                             // мин. радиус пузырька (px)       ← слаг visuals.bubbleMinSize
    "maxRadius": 30,                            // макс. радиус пузырька (px)      ← слаг visuals.bubbleMaxSize
    "zoomToBubbleEdges": false,                 // не обрезать крупные пузырьки    ← слаг bubble.zoomToEdges
    "strictMinMaxEnabled": false,               // точное масштабирование осей     ← слаг bubble.strictMinMax
    "hideScrollbars": false,                    // скроллбары: false = видны (слаг инвертирован)  ← слаг bubble.showScrollbars
    "filterMode": true,                         // клик по пузырьку = фильтр       ← слаг bubble.filterMode
    "precision": -1,                            // знаков после запятой (-1 = авто)← слаг bubble.precision
    "bigNumberSuffixes": [],                    // суффиксы больших чисел          ← слаг bubble.bigNumberSuffixes
    "legendForColor": { "enabled": false },     // легенда цвета пузырьков (объект) ← слаг bubble.legendForColor
    "legendForSize":  { "enabled": false },     // легенда размера пузырьков (объект)← слаг bubble.legendForSize
    "legend": {                                 // основная легенда серий
      "visible": true,                          //   показывать                    ← слаг legend.visible
      "position": "auto",                       //   позиция                       ← слаг legend.position
      "order": "normal"                         //   порядок (normal|reversed)     ← слаг legend.order
    },
    "labels": { "visible": false, "position": "auto" },   // подписи на пузырьках  ← слаг labels.visible
    "axes": [                                   // оси данных (поля привязываются параметрами при добавлении)
      { "name": "filters",    "type": "filters",    "fields": [] },              // фильтры компонента
      { "name": "categories", "type": "categories", "fields": [                  // ось категорий  ← category_field
          { "name": "region", "alias": "Регион", "type": "string", "datasetId": 54 }
      ]},
      { "name": "series",     "type": "series",     "fields": [] },              // ось серий-разреза (обычно пуста)
      { "name": "yvalues",    "type": "yvalues",    "fields": [                  // координата Y   ← value_field[0]
          { "name": "price_rub", "alias": "Цена",     "type": "number", "agg": "avg", "datasetId": 54 }
      ]},
      { "name": "xvalues",    "type": "xvalues",    "fields": [                  // координата X   ← value_field[1]
          { "name": "amount",    "alias": "Количество","type": "number", "agg": "avg", "datasetId": 54 }
      ]},
      { "name": "values",     "type": "values",     "fields": [                  // размер (+ цвет) ← size_field
          { "name": "summa_rub",   "alias": "Выручка", "type": "number", "agg": "sum", "datasetId": 54 },  // 1-е поле = размер
          { "name": "color_field", "alias": "Цвет",    "type": "string", "agg": "max", "datasetId": 54 }   // 2-е поле (опционально) = цвет
      ]}
    ],
    "visuals": []                               // визуальные параметры серий: массив (по элементу на серию)
  }
}
```

> Поле размера всегда первое в оси `values`; второе поле (если оно есть) задаёт цвет пузырьков — текстовое со значением цвета или вычисляемое с `CASE WHEN`.

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
| палитра | `visuals.colorPalette` | `(visuals[0].colorPalette)` | any | `pal_2018` |  |

### Стиль элементов

| UI-контрол | MCP-слаг | JSON-путь | Тип | По умолчанию | Прим. |
|---|---|---|---|---|---|
| — | `visuals.autoColor` | `styleCommons.autoColor` | bool | `True` |  |
| Основной цвет | `visuals.mainColor` | `(visuals[0].mainColor)` | color | — |  |
| — | `visuals.markerLabels` | `(visuals[0].markerLabels)` | bool | `False` | только этот тип |

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
| Режим фильтра | `bubble.filterMode` | `filterMode` | bool | `True` | только этот тип |
| Цвет фона / Отступы / Точность / Формат даты | `bubble.precision` | `precision` | int | `-1` | только этот тип |
| Режим точн. масшт. | `bubble.strictMinMax` | `strictMinMaxEnabled` | bool | `False` | только этот тип |
| Учёт размеров пузырьков | `bubble.zoomToEdges` | `zoomToBubbleEdges` | bool | `False` | только этот тип |
| — | `fontSize` | `(fontSize)` | int | `12` |  |
| Градиент | `gradient` | _секционно_ | bool | `False` |  |
| — | `nocopy` | `(nocopy)` | bool | `False` |  |
| — | `noexport` | `(noexport)` | bool | `False` |  |
| Заголовок | `showtitle` | `(showtitle)` | bool | `True` |  |
| Радиус макс | `visuals.bubbleMaxSize` | `maxRadius` | int | `30` | только этот тип |
| Радиус мин | `visuals.bubbleMinSize` | `minRadius` | int | `3` | только этот тип |

### Легенда размера

| UI-контрол | MCP-слаг | JSON-путь | Тип | По умолчанию | Прим. |
|---|---|---|---|---|---|
| enable / Граф. представление | `bubble.legendForSize` | `legendForSize.enabled` | bool | `False` | только этот тип |

### Легенда цвета

| UI-контрол | MCP-слаг | JSON-путь | Тип | По умолчанию | Прим. |
|---|---|---|---|---|---|
| enable | `bubble.legendForColor` | `legendForColor.enabled` | bool | `False` | только этот тип |

### Пузырьковая диаграмма

| UI-контрол | MCP-слаг | JSON-путь | Тип | По умолчанию | Прим. |
|---|---|---|---|---|---|
| — | `bubble.bigNumberSuffixes` | `bigNumberSuffixes` | any | `[]` | только этот тип |
| — | `bubble.showScrollbars` | `hideScrollbars` | bool | `True` | только этот тип |

<!-- AUTO-TABLE:END -->

## Связанные

- [Каталог компонентов](../README.md)
- [Столбчатая диаграмма](bar-chart.md)
- [Линейная диаграмма](line-chart.md)
- [Площадная диаграмма](area-chart.md)
- [Радарная диаграмма](radar-chart.md)
- [Круговая диаграмма](pie-chart.md)
- [Sunburst](sunburst.md)
- [Концепция: JSON-конфиг и слаги](../../concepts/components-json-slugs.md)
- [Справочник настроек (слаги)](../slugs/by-type.md)
- [Рецепты подготовки данных](../data-recipes.md)
- [Стилизация компонентов](../styling.md)
- [Фильтры и каскады](../filter-patterns.md)
