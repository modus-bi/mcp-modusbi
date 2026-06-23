# Площадная диаграмма

Тип компонента: `HsAreaAMchartsChart`

## Описание

Площадная диаграмма (диаграмма с областями) — гибрид линейного графика и гистограммы: значения соединяются линией, а область под линией закрашивается цветом. Это одновременно показывает изменение величины и визуально передаёт её объём. Поддерживает несколько серий (несколько закрашенных областей на одном графике), вертикальную и горизонтальную ориентацию, режимы наложения областей (перекрытие, стек, 100 %-структура), легенду и подписи значений.

По устройству площадная диаграмма повторяет линейную и столбчатую: те же оси и те же поля данных — отличается только заливкой области под линией.

## Когда применять

- Динамика показателя во времени, когда важно не только направление тренда, но и масштаб значений.
- Сравнение нескольких метрик на одном графике с акцентом на их накопленный объём.
- Структура суммы по составляющим во времени (стекированные области — вклад каждой части в общий итог).
- Непрерывные данные (временные ряды), где пространство между точками осмысленно.

## Когда не подходит

- Много пересекающихся серий (больше 4–5) — области накладываются и диаграмма становится нечитаемой; лучше линейная диаграмма.
- Дискретные, не связанные между собой категории — лучше столбчатая диаграмма.
- Когда нужны точные числа, а не общий тренд — лучше таблица.
- Доли одного целого в одной точке — лучше круговая диаграмма.

## Поля и оси

Компонент использует четыре типа полей данных:

- **Категории** — текстовое (или дата/число) поле, задающее ось X. Для временных рядов поместите сюда поле даты. Агрегация для категорий не применяется.
- **Значения** — числовое поле, задающее высоту области (ось Y). Несколько полей значений дают несколько закрашенных областей. Для значений агрегация обязательна.
- **Серии** (необязательно) — поле-разрез: каждое уникальное значение создаёт отдельную окрашенную область. Если пусто — данные идут одной серией (либо мультисерия задаётся несколькими полями значений).
- **Дополнительная ось значений** (необязательно) — вторая шкала для метрик с другим масштабом.

### Режимы наложения областей

Когда серий несколько, параметр `stacking` управляет тем, как области соотносятся друг с другом:

- `stacking="none"` — области накладываются друг на друга (перекрытие); видно каждую серию по отдельности.
- `stacking="normal"` — накопление: каждая область ставится поверх предыдущей, верхняя граница показывает сумму всех серий.
- `stacking="percent"` — 100 %-структура: высота нормируется к 100 %, видна доля каждой серии в общем итоге.

Технически `stacking` — это удобный псевдоним: сервер раскладывает его во внутренний ключ конфига `groupMode`.

### Правила агрегации

Агрегация управляет тем, как несколько строк датасета сводятся к одному значению точки:

- **Предагрегированный датасет** (значения уже посчитаны через `GROUP BY` в SQL) — передавайте агрегацию явно (например, `aggregation="max"`). На готовой группе любая агрегация вернёт то же значение, но указать её необходимо: без агрегации поле значений считается неготовым и диаграмма выходит пустой.
- **Сырой датасет, нужна сумма по категории** — `aggregation="sum"`.
- **Среднее по категории** — `aggregation="avg"` (аналогично `min`, `max`, `count`).
- Значение `aggregation="none"` означает «не агрегировать» — для площадной диаграммы практически не используется.

Если поле значений осталось без агрегации, диаграмма обычно выходит пустой. Все поля оси значений должны быть числовыми (`type: "number"`).

## Параметры добавления

Помимо привязки к датасету и полям, при добавлении компонента доступны параметры:

| Параметр | Назначение |
|----------|-----------|
| `x`, `y`, `w`, `h` | Позиция и размер компонента в сетке отчёта |
| `orientation` | Ориентация: `"v"` (категории по X, значения по Y) или `"h"` (категории по Y) |
| `stacking` | Режим серий: `"none"` (перекрытие), `"normal"` (накопление), `"percent"` (100 %-структура) |
| `series_field` | Поле-разрез для нескольких серий |
| `aggregation` | Агрегация значений (`sum`, `avg`, `min`, `max`, `count`, `none`) |
| `preset` | Готовый визуальный пресет оформления |

## Формат данных

Особого формата не требуется: подойдёт обычная таблица «категория + числовая метрика». Для временных рядов (по дням, месяцам, годам) дата выступает категорией — поместите поле даты в `category_field`, и диаграмма построит временную шкалу.

Несколько областей задаются двумя способами:

1. **Несколько полей значений** (`value_field="plan,fact"`) — разные метрики выводятся как отдельные области. Подходит, когда величины уже лежат в отдельных колонках.
2. **Поле-разрез** (`series_field="region"`) — одна метрика разбивается по значениям разреза, каждое значение становится отдельной областью. Подходит, когда данные лежат «в длину» (одна колонка значения + колонка категории-разреза).

## Пример

Площадная диаграмма по одному показателю (предагрегированный датасет):

```python
component_crud(
    action="add",
    report_id=35,
    component_type="HsAreaAMchartsChart",
    title="Динамика продаж",
    dataset_id=54,
    category_field="month",
    value_field="summa_rub",
    aggregation="sum",
    orientation="v",
    x=0, y=0, w=24, h=16,
    legend_visible=True,
)
```

Мультисерия способом 1 — несколько полей значений через запятую дают несколько закрашенных областей:

```python
component_crud(
    action="add",
    report_id=35,
    component_type="HsAreaAMchartsChart",
    title="Сравнение показателей",
    dataset_id=54,
    category_field="month",
    value_field="plan,fact",
    aggregation="sum",
    x=0, y=16, w=24, h=16,
    config_overrides={
        "legend.position": "bottom-center",
        "balloon.combine": True,
    },
)
```

Мультисерия способом 2 — поле-разрез: каждое уникальное значение разреза становится отдельной областью; `stacking="normal"` складывает их в накопительный итог:

```python
component_crud(
    action="add",
    report_id=35,
    component_type="HsAreaAMchartsChart",
    title="Продажи по регионам",
    dataset_id=54,
    category_field="month",
    value_field="sales",
    series_field="region",     # каждый регион — отдельная закрашенная область
    aggregation="sum",
    stacking="normal",         # области накапливаются: верхняя граница = сумма по регионам
    x=0, y=32, w=24, h=16,
)
```

Здесь `component_crud` — это RPC-метод MCP-сервера (вызов инструмента), а не REST-эндпоинт; `component_idx` в других действиях — 0-based индекс компонента в отчёте.

## JSON-конфигурация

Сервер собирает и хранит конфигурацию компонента в JSON. Ниже — аннотированная структура площадной диаграммы: рядом с каждым ключом указано, что он задаёт и каким слагом управляется (полное соответствие — в таблице «Все настройки»).

```jsonc
{
  "type": "HsAreaAMchartsChart",                // тип компонента (его отдаёт component_crud action="types_list")
  "config": {
    "title": "Динамика продаж",                 // заголовок компонента
    "chartType": "areaChart",                   // внутренний тип диаграммы (фиксирован)
    "visualType": "area",                       // визуальное представление (фиксировано)
    "orientation": "v",                         // ориентация: "v"|"h"  (параметр orientation при добавлении)
    "groupMode": "",                            // режим наложения: ""|"stack"|"100%" (параметр stacking при добавлении)
    "showtitle": true,                          // показывать заголовок            ← слаг showtitle
    "noexport": false,                          // запретить экспорт данных        ← слаг noexport
    "nocopy": false,                            // запретить копирование данных    ← слаг nocopy
    "bgColor": "rgba(255, 255, 255, 1)",        // цвет фона                       ← слаг bgColor
    "margin":  { "l": 5, "r": 10, "t": 10, "b": 5, "pad": 0 },    // отступы       ← слаги margin.l/r/t/b/pad
    "outline": { "enabled": false, "width": 4 },                  // рамка         ← слаги outline.enabled/width
    "legend": {                                 // легенда
      "visible": true,                          //   показывать                    ← слаг legend.visible
      "position": "auto",                       //   позиция                       ← слаг legend.position
      "order": "normal"                         //   порядок (normal|reversed)     ← слаг legend.order
    },
    "labels": {                                 // подписи значений на областях
      "visible": false,                         //   показывать                    ← слаг labels.visible
      "position": "auto",                       //   позиция                       ← слаг labels.position
      "inner": {}, "outer": {}                  //   внутренние/внешние подписи     ← слаги labels.inner.*/outer.*
    },
    "axes": [                                   // оси данных (поля привязываются параметрами при добавлении)
      { "name": "filters",    "type": "filters",    "fields": [] },              // фильтры компонента
      { "name": "categories", "type": "categories", "scaleType": "category", "fields": [   // ось категорий ← category_field
          { "name": "month", "alias": "Месяц", "type": "string", "datasetId": 54 }
      ]},
      { "name": "series",     "type": "series",     "fields": [] },              // ось серий-разреза ← series_field
      { "name": "values",     "type": "values",     "sortable": true, "fields": [   // ось значений  ← value_field + aggregation
          { "name": "summa_rub", "alias": "Продажи", "type": "number", "agg": "sum", "datasetId": 54 }
      ]}
    ],
    "visuals": []                               // визуальные параметры серий: массив (по элементу на серию);
                                                // слаги visuals.* пишутся в visuals[0].* — см. таблицу ниже
  }
}
```

> Специфичные для площадной диаграммы слаги: `style.smoothing` (сглаживание линии), `style.lineWidth` (толщина линии), `style.markerWidth` (размер маркера), `style.autoColor` (режим автоцвета). Остальные слаги (цвета, легенда, оси, отступы) — общие для всех типов диаграмм. Все они задаются через `config_overrides` — см. таблицу ниже.

Каждый ключ внутри `config` соответствует строке в таблице ниже. Колонка **JSON-путь** показывает, где значение хранится в конфиге. Для вложенных параметров используется запись `объект[раздел].ключ` (например, `axes[categories].showlabels` — это ключ `showlabels` внутри оси категорий в `config.axes`). Пустой путь означает верхний уровень `config`.

> Таблица ниже сгенерирована автоматически из схемы слагов сервера. Если в ней найдена ошибка, её правят в `config_schema.py` и пересобирают документацию скриптом `scripts/gen_component_tables.py` — не в этом файле.

> Пометка **«только этот тип»** в колонке «Прим.» означает, что слаг работает лишь для площадной (и родственной линейной) диаграммы и не применяется к столбчатой, круговой и прочим типам. Слаги без этой пометки — общие для разных типов графиков.

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
| Цвет заливки | `visuals.fillOpacity` | _секционно_ | float | `0.5` | устар. |
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

### Стилизация (series)

| UI-контрол | MCP-слаг | JSON-путь | Тип | По умолчанию | Прим. |
|---|---|---|---|---|---|
| Толщина | `visuals.lineWidth` | `(visuals[0].lineWidth)` | int | `2` | только этот тип |

<!-- AUTO-TABLE:END -->

## Связанные

- [Каталог компонентов](../README.md)
- [Словарь терминов](../../../GLOSSARY.md)
- [Концепция: JSON-конфиг и слаги](../../concepts/components-json-slugs.md)
- [Справочник настроек (слаги)](../slugs/by-type.md)
- [Рецепты подготовки данных](../data-recipes.md)
- [Стилизация компонентов](../styling.md)
- [Фильтры и каскады](../filter-patterns.md)
