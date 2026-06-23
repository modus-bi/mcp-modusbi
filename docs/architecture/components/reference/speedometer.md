# Спидометр (стрелочный индикатор)

Тип компонента: `HsSpeedometerV2AMcharts`

Базовые термины (слаг, config, датасет, ось) — в [../../../GLOSSARY.md](../../../GLOSSARY.md).

## Описание

Спидометр — это стрелочный индикатор (тахометр): он показывает одно числовое значение в виде стрелки на круговой градуированной шкале с цветными зонами. Применяется для мониторинга ключевого показателя относительно заданного диапазона: «где сейчас находится метрика» — в зелёной, жёлтой или красной зоне.

Компонент рассчитан на единичное значение. Дополнительно он поддерживает несколько стрелок на одной шкале, разбивку по категориям, пороговые отсечки-маркеры (threshold) и настройку углов шкалы (от полного тахометра до полукруга или кольцевого прогресс-бара).

## Когда применять

- Мониторинг одного KPI (выручка, загрузка, процент выполнения плана) относительно целевого диапазона.
- Наглядная индикация состояния «норма / внимание / критично» через цветные зоны шкалы.
- Прогресс-бар «факт vs цель» — стрелка плюс отсечка целевого уровня.
- Несколько показателей на одной шкале (до нескольких стрелок) или разбивка по категории.

## Когда не подходит

- Тренд по времени — лучше линейная или площадная диаграмма.
- Сравнение многих величин между собой — лучше столбчатая диаграмма.
- Доли частей целого — лучше круговая диаграмма.
- KPI-число без шкалы (значение + подпись + тренд) — лучше панель показателей.
- Множество строк данных — лучше таблица.

## Поля и оси

Компонент использует три типа полей данных:

- **Показатель (значения)** — числовое поле, задающее положение стрелки. Обязательно хотя бы одно поле. Каждое поле создаёт отдельную стрелку со своей дугой-заливкой; технически поддерживается несколько стрелок. Для значения нужна агрегация (см. ниже).
- **Категории** (необязательно) — одно текстовое поле-разрез: индикатор строит по стрелке на каждое уникальное значение категории. Если ось пуста — отображается один индикатор. Агрегация для категорий не применяется.
- **Фильтры** (необязательно) — поля компонента, подключающие его к глобальным фильтрам отчёта.

Шкала задаётся не данными, а параметрами: минимум/максимум (`grid.min` / `grid.max`), углы (`grid.startAngle` / `grid.endAngle`), число делений и цветовые зоны (`grid.gradeCount` + `grid.paletteColors`). Если максимум не задан, шкала берёт максимум из данных.

Углы задаются в диапазоне 0–360 градусов (значения вне диапазона отклоняются). Полный круг: `startAngle=0`, `endAngle=360`. Классический тахометр (полукруг снизу): `startAngle≈210`, `endAngle≈330`. Полукруг сверху: `startAngle=0`, `endAngle=180`.

### Отсечка (threshold)

Чтобы показать целевой уровень, на ось значений добавляют второе поле и помечают его ролью отсечки — в объекте поля проставляется ключ `"valueType": "threshold"`. Такое поле не создаёт стрелку, а рисует маркер-полоску на шкале — удобно для пары «факт + цель». Аналогично роли `minimum` / `maximum` позволяют задать границы шкалы динамически из данных, а не константой.

### Правила агрегации

Агрегация управляет тем, как несколько строк датасета сводятся к одному числу под стрелкой:

- **Предагрегированный датасет** (значение уже посчитано в SQL) — укажите агрегацию явно (например, `aggregation="max"`): без агрегации поле значений считается неготовым и стрелка не рисуется.
- **Сырой датасет, нужна сумма** — `aggregation="sum"`; среднее — `aggregation="avg"` (аналогично `min`, `max`, `count`).
- Поскольку спидометр показывает одно значение, при наличии категорий отображается последняя запись выборки — учитывайте сортировку категорий.

## Параметры добавления

Помимо привязки к датасету и полям, при добавлении доступны параметры:

| Параметр | Назначение |
|----------|-----------|
| `report_id` | Числовой идентификатор отчёта, в который добавляется компонент |
| `x`, `y`, `w`, `h` | Позиция и размер компонента в сетке отчёта |
| `category_field` | Поле-разрез для нескольких стрелок (необязательно) |
| `value_field` | Числовое поле — значение стрелки |
| `aggregation` | Агрегация значения (`sum`, `avg`, `min`, `max`, `count`) |
| `config_overrides` | Слаги шкалы, зон и оформления (см. таблицу настроек) |
| `preset` | Готовый визуальный пресет оформления |

## Формат данных

Особого формата не требуется. Для одного индикатора достаточно одной числовой метрики. Шкала (минимум, максимум, зоны) настраивается параметрами, а не данными. Для разбивки на несколько стрелок добавьте текстовое поле в `category_field`. Для пары «факт + цель» добавьте второе значение и пометьте его ролью отсечки.

## Пример

Минимальный индикатор по предагрегированному датасету:

```python
component_crud(
    action="add",
    report_id={REPORT_ID},
    component_type="HsSpeedometerV2AMcharts",
    title="Выручка за месяц",
    dataset_id={DATASET_ID},
    value_field="revenue",
    aggregation="sum",
    x=0, y=0, w=8, h=9,
)
```

Индикатор с настройкой шкалы: явный максимум, три цветные зоны (красный → жёлтый → зелёный) и тахометрические углы — через `config_overrides`:

```python
component_crud(
    action="add",
    report_id={REPORT_ID},
    component_type="HsSpeedometerV2AMcharts",
    title="Выполнение плана, %",
    dataset_id={DATASET_ID},
    value_field="plan_percent",
    aggregation="avg",
    x=0, y=0, w=8, h=9,
    config_overrides={
        "grid.min": 0,
        "grid.max": 100,
        "grid.startAngle": 210,   # классический тахометр (углы в диапазоне 0–360)
        "grid.endAngle": 330,
        "grid.gradeCount": 3,
        "grid.paletteColors": ["#FF5433", "#FFC300", "#00D361"],
        "grid.width": 18,
    },
)
```

Разбивка на несколько стрелок по категории — поле-разрез задаётся через `category_field`:

```python
component_crud(
    action="add",
    report_id={REPORT_ID},
    component_type="HsSpeedometerV2AMcharts",
    title="Продажи по сезонам",
    dataset_id={DATASET_ID},
    category_field="season",
    value_field="amount",
    aggregation="sum",
    x=0, y=9, w=24, h=10,
    config_overrides={
        "grid.max": 50000,
        "legend.visible": True,
        "legend.position": "bottom-center",
    },
)
```

Здесь `component_crud` — это RPC-метод MCP-сервера (вызов инструмента), а не REST-эндпоинт; `component_idx` в других действиях — 0-based индекс компонента в отчёте.

## JSON-конфигурация

Сервер собирает и хранит конфигурацию компонента в JSON. Ниже — аннотированная структура спидометра после добавления компонента с привязанным полем: рядом с ключами указано, что они задают и каким слагом управляются (полное соответствие — в таблице «Все настройки»). Поля данных в массиве `axes` заполняются параметрами `value_field`, `category_field`, `aggregation` при вызове `component_crud(action="add", ...)`.

```jsonc
{
  "type": "HsSpeedometerV2AMcharts",            // тип компонента (его отдаёт component_crud action="types_list")
  "config": {
    "title": "Выручка за месяц",                // заголовок компонента
    "chartType": "speedometer_v2",              // тип графика — фиксирован фронтендом, не менять
    "visualType": "gauge",                      // тип отрисовки — фиксирован фронтендом, не менять
    "showtitle": true,                          // показывать заголовок            ← слаг showtitle
    "bgColor": "rgba(255, 255, 255, 1)",        // цвет фона контейнера            ← слаг bgColor
    "backgroundColor": null,                    // цвет «лица» циферблата          ← слаг gauge.backgroundColor
    "startAngle": 0,                            // начальный угол шкалы (градусы, 0–360)  ← слаг grid.startAngle
    "endAngle": 360,                            // конечный угол шкалы (градусы, 0–360)   ← слаг grid.endAngle
    "roundLimits": false,                       // округлять границы шкалы         ← слаг grid.roundLimits
    "usePrefixes": false,                       // префиксы K/M/G на подписях шкалы
    "margin":  { "l": 10, "r": 10, "t": 5, "b": 10, "pad": 0 },   // отступы       ← слаги margin.l/r/t/b/pad
    "outline": { "enabled": false, "width": 4 },                  // рамка         ← слаги outline.enabled/width
    "legend": {                                 // легенда (актуальна при 2+ стрелках/категории)
      "visible": false,                         //   показывать                    ← слаг legend.visible
      "position": "auto",                       //   позиция                       ← слаг legend.position
      "order": "normal"                         //   порядок (normal|reversed)     ← слаг legend.order
    },
    "grid": {                                   // круговая шкала
      "visible": true,                          //   показывать шкалу
      "width": 15,                              //   ширина полосы шкалы (px)       ← слаг grid.width
      "minimum": 0,                             //   минимум шкалы                  ← слаг grid.min
      "maximum": 100,                           //   максимум шкалы                 ← слаг grid.max
      "tickCount": 5,                           //   число основных делений         ← слаг grid.tickCount
      "minorTickCount": 5,                      //   вспомогательных делений         ← слаг grid.minorTickCount
      "labelFrequency": 1,                      //   частота подписей делений        ← слаг grid.labelFrequency
      "palette": {                              //   цветовые зоны шкалы
        "gradeCount": 2,                        //     число зон (длина colors)      ← слаг grid.gradeCount
        "gradientMode": false,                  //     плавный градиент между зонами  ← слаг grid.gradientMode
        "invert": false,                        //     инверсия порядка цветов        ← слаг grid.paletteInvert
        "colors": ["#00D361", "#FF5433"]        //     цвета зон (от min к max)        ← слаг grid.paletteColors
      }
    },
    // массивы fields ниже заполняются только при привязке полей (category_field, value_field, фильтры)
    "axes": [                                   // оси данных (поля привязываются параметрами при добавлении)
      { "name": "filters",    "type": "filters",    "fields": [] },              // фильтры компонента
      { "name": "Категории",  "type": "categories", "fields": [] },              // ось категорий  ← category_field
      { "name": "Показатель", "type": "values",     "visible": true, "fields": [ // ось значений   ← value_field + aggregation
          { "name": "revenue", "alias": "Выручка", "type": "number", "agg": "sum", "datasetId": 0 }
          // agg ← параметр aggregation при добавлении; datasetId — id привязанного датасета
          // второе поле с "valueType": "threshold" → отсечка (маркер цели, без стрелки)
      ]}
    ]
  }
}
```

> Цвет «лица» циферблата (`gauge.backgroundColor`) пишется в `config.backgroundColor`; цвет фона контейнера — это отдельный ключ `bgColor`. Число элементов в `grid.palette.colors` должно совпадать с `grid.gradeCount`.

Каждый ключ внутри `config` соответствует строке в таблице ниже. Колонка **JSON-путь** показывает, где значение хранится в конфиге. Запись в `(скобках)` обрабатывается секционно — итоговое значение пишется в указанный раздел конфига.

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
| вкл | `legend.visible` | `(legend.visible)` | bool | `False` |  |

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
| enable | `labels.visible` | `(labels.visible)` | bool | `True` |  |

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
| Отступ Низ | `margin.b` | `(margin.b)` | int | `10` |  |
| Отступ Лево | `margin.l` | `(margin.l)` | int | `10` |  |
| Внутренний отступ | `margin.pad` | `(margin.pad)` | int | `0` |  |
| Отступ Право | `margin.r` | `(margin.r)` | int | `10` |  |
| Отступ Верх | `margin.t` | `(margin.t)` | int | `5` |  |

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
| — | `fontSize` | `(fontSize)` | int | `12` |  |
| Цвет фона | `gauge.backgroundColor` | `backgroundColor` | color | — | только этот тип |
| Градиент | `gradient` | _секционно_ | bool | `False` |  |
| — | `nocopy` | `(nocopy)` | bool | `False` |  |
| — | `noexport` | `(noexport)` | bool | `False` |  |
| Заголовок | `showtitle` | `(showtitle)` | bool | `True` |  |

### Шкала

| UI-контрол | MCP-слаг | JSON-путь | Тип | По умолчанию | Прим. |
|---|---|---|---|---|---|
| Конечный угол | `grid.endAngle` | `endAngle` | int | `360` | только этот тип |
| Максимум | `grid.max` | `grid.maximum` | float | `100` | только этот тип |
| Минимум | `grid.min` | `grid.minimum` | float | `0` | только этот тип |
| Мелких делений | `grid.minorTickCount` | `(grid.minorTickCount)` | int | `5` | только этот тип |
| Округл. мин/макс | `grid.roundLimits` | `roundLimits` | bool | `False` | только этот тип |
| Начальный угол | `grid.startAngle` | `startAngle` | int | `0` | только этот тип |
| Крупных делений | `grid.tickCount` | `(grid.tickCount)` | int | `5` | только этот тип |

### Шкала/Отсечки

| UI-контрол | MCP-слаг | JSON-путь | Тип | По умолчанию | Прим. |
|---|---|---|---|---|---|
| Количество цветов (зоны) | `grid.gradeCount` | `grid.palette.gradeCount` | int | `2` | только этот тип |

### Шкала/индикатор

| UI-контрол | MCP-слаг | JSON-путь | Тип | По умолчанию | Прим. |
|---|---|---|---|---|---|
| — | `grid.color` | `(grid.color)` | color | — | только этот тип |
| — | `grid.gradientMode` | `grid.palette.gradientMode` | bool | `False` | только этот тип |
| — | `grid.labelFrequency` | `(grid.labelFrequency)` | int | `1` | только этот тип |
| — | `grid.labelsColor` | `(grid.labelsColor)` | color | — | только этот тип |
| — | `grid.paletteColors` | `grid.palette.colors` | any | — | только этот тип |
| — | `grid.paletteInvert` | `grid.palette.invert` | bool | `False` | только этот тип |
| — | `grid.width` | `(grid.width)` | int | `15` | только этот тип |

<!-- AUTO-TABLE:END -->

## Связанные

- [Каталог компонентов](../README.md)
- [Концепция: JSON-конфиг и слаги](../../concepts/components-json-slugs.md)
- [Справочник настроек (слаги)](../slugs/by-type.md)
- [Рецепты подготовки данных](../data-recipes.md)
- [Стилизация компонентов](../styling.md)
- [Фильтры и каскады](../filter-patterns.md)
