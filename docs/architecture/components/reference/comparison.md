# Диаграмма сравнения

Тип компонента: `HsComparisonChart`

## Описание

Диаграмма сравнения сопоставляет показатели **двух объектов** — например, двух регионов, двух подразделений, двух продуктов или двух периодов. Компонент строит табличное представление: строки соответствуют показателям, а колонки — значениям Объекта 1 и Объекта 2. Дополнительно она может вычислять **дельту** (абсолютную разницу) и **процент** отклонения между объектами.

Какие именно два объекта сравнивать, задаётся выбором двух значений из поля на оси «Объекты» (например, два региона из поля «Регион»). Если в данных нет ни одного из выбранных объектов, в таблице показывается строка со средним значением по всем объектам — как эталонный ориентир.

## Когда применять

- Сравнение двух конкретных объектов (регионов, подразделений, продуктов, периодов) сразу по нескольким показателям.
- Анализ отклонений: дельта и процент между двумя объектами.
- План-факт, YoY/MoM, «этот объект против того» в одном компактном виде.
- Сводное сопоставление с разбивкой по дополнительным сериям (например, по годам или кварталам).

## Когда не подходит

- Сравнение более двух объектов одновременно — используйте обычную таблицу или столбчатую диаграмму.
- Детализированные данные без агрегации — используйте обычную таблицу.
- Динамика во времени — используйте линейную или площадную диаграмму.
- Иерархический анализ с проваливанием (drill-down) — используйте сводную таблицу.

## Поля и оси

Компонент использует несколько осей данных:

- **Объекты** (обязательно) — текстовое поле, по значениям которого выбираются Объект 1 и Объект 2 (например, «Регион», «Округ», «Подразделение»). Агрегация к нему не применяется: поле работает как разрез, по которому фильтруются сравниваемые сущности.
- **Показатели** (обязательно для рекомендуемой раскладки) — текстовое поле, уникальные значения которого образуют **строки** таблицы (названия метрик).
- **Значения** (обязательно) — числовое поле, дающее сами сравниваемые величины. Для значений агрегация обязательна.
- **Серии** (необязательно) — дополнительный разрез внутри значений. При его заполнении для каждой серии появляются отдельные колонки значений плюс колонка «Итого». Способ расчёта итогов (`sum`, `avg`, `min`, `max`, `last`) настраивается отдельно для каждого показателя.
- **Фильтры** (необязательно) — поля для ограничения данных компонента.

Рекомендуемая раскладка данных — «длинная» (UNPIVOT): одна строка датасета = один объект + название показателя + значение. Поле объекта идёт в ось «Объекты», название показателя — в ось «Показатели», числовое значение — в ось «Значения».

### Правила агрегации

Агрегация по оси «Значения» управляет тем, как несколько строк датасета сводятся к одному числу в ячейке:

- **Предагрегированный датасет** (значения уже посчитаны через `GROUP BY` в SQL) — передавайте агрегацию явно. Рекомендуется `aggregation="max"`: на готовой группе он вернёт то же значение без повторного суммирования. Без явной агрегации поле значений считается неготовым и таблица выходит пустой.
- **Сырой датасет, нужна сумма по объекту** — `aggregation="sum"`.
- **Среднее, минимум, максимум** — `aggregation="avg"` / `"min"` / `"max"` (аналогично `count`).

Если задана ось «Серии», для каждого показателя дополнительно настраивается способ расчёта строки «Итого» через слаги серии (`sum`, `min`, `max`, `avg`, `last`).

## Параметры добавления

Помимо привязки к датасету и полям, при добавлении доступны параметры:

| Параметр | Назначение |
|----------|-----------|
| `x`, `y`, `w`, `h` | Позиция и размер компонента в сетке отчёта |
| `category_field` | Поле объектов сравнения (ось «Объекты») |
| `column_fields` | Поле названий показателей (ось «Показатели», в JSON — `axes[indicators].fields`) в раскладке UNPIVOT |
| `value_field` | Числовое поле сравниваемых величин (ось «Значения») |
| `aggregation` | Агрегация значений (`sum`, `avg`, `min`, `max`, `count`) |
| `config_overrides` | Слаги тонкой настройки (объекты, дельта/процент, точность, оформление) |

## Формат данных

Рекомендуемый формат — «длинная» таблица: `объект | показатель | значение`. Каждая комбинация объекта и показателя — отдельная строка. Такая раскладка надёжнее всего отрабатывается отображением.

| объект | показатель | значение |
|--------|-----------|----------|
| Москва | Выручка | 150000 |
| Москва | Затраты | 90000 |
| СПб | Выручка | 120000 |
| СПб | Затраты | 70000 |

Датасет может быть и более детальным (с разбивкой по дням, товарам и т.п.) — тогда несколько строк на пару «объект + показатель» сводятся к одному числу агрегацией по оси **Значения**.

Если показатели лежат в датасете отдельными числовыми колонками («широкая» таблица), её предварительно разворачивают в «длинную» — через `UNION ALL` в PostgreSQL или `UNPIVOT` в SQL Server.

## Пример

Диаграмма сравнения двух регионов по нескольким показателям (раскладка UNPIVOT):

```python
component_crud(
    action="add",
    report_id=35,
    component_type="HsComparisonChart",
    title="Сравнение регионов",
    dataset_id=54,
    category_field="region",        # ось «Объекты»
    column_fields="metric_name",    # ось «Показатели» — названия метрик (категориальное поле: «Выручка», «Затраты»)
    value_field="metric_value",     # ось «Значения»
    aggregation="sum",
    x=0, y=0, w=33, h=17,
)
```

Чтобы задать сравниваемые объекты и включить колонки дельты и процента, примените слаги через `config_overrides`:

```python
component_crud(
    action="add",
    report_id=35,
    component_type="HsComparisonChart",
    title="Сравнение регионов",
    dataset_id=54,
    category_field="region",
    column_fields="metric_name",
    value_field="metric_value",
    aggregation="sum",
    config_overrides={
        "comparison.object1": "Москва",   # первый сравниваемый объект
        "comparison.object2": "СПб",      # второй сравниваемый объект
        "comparison.showDelta": True,     # колонка «Дельта»
        "comparison.showPercent": True,   # колонка «Процент»
        "comparison.precision": 2,        # 2 знака после запятой
    },
)
```

Значения слагов `comparison.object1`/`comparison.object2` должны точно совпадать со значениями из поля объектов (с учётом регистра). Сервер транслирует каждый слаг сразу в два места: в `config.object1`/`config.object2` (верхний уровень `config`) **и** в запись сравнения в `config.filters` по полю объектов (тип `by compare`, два выбранных значения) — именно она включает само сравнение. При прямом редактировании JSON оба места нужно синхронизировать вручную.

Здесь `component_crud` — это RPC-метод MCP-сервера (вызов инструмента), а не REST-эндпоинт; `component_idx` в других действиях — 0-based индекс компонента в отчёте.

## JSON-конфигурация

Сервер собирает и хранит конфигурацию компонента в JSON. Ниже — аннотированная структура диаграммы сравнения: рядом с каждым ключом указано, что он задаёт и каким слагом управляется (полное соответствие — в таблице «Все настройки»).

```jsonc
{
  "type": "HsComparisonChart",                  // тип компонента (его отдаёт component_crud action="types_list")
  "config": {
    "title": "Сравнение регионов",              // заголовок компонента
    "chartType": "comparisonChart",             // внутренний тип (фиксирован)
    "showtitle": true,                          // показывать заголовок            ← слаг showtitle
    "noexport": false,                          // запретить экспорт данных        ← слаг noexport
    "nocopy": false,                            // запретить копирование данных    ← слаг nocopy
    "bgColor": "rgba(255, 255, 255, 1)",        // цвет фона                       ← слаг bgColor
    "margin":  { "l": 0, "r": 0, "t": 0, "b": 0, "pad": 0 },      // отступы       ← слаги margin.l/r/t/b/pad
    "outline": { "enabled": false, "width": 4 },                  // рамка         ← слаги outline.enabled/width
    "object1": "Москва",                        // первый сравниваемый объект      ← слаг comparison.object1
    "object2": "СПб",                           // второй сравниваемый объект      ← слаг comparison.object2
    "showDelta": false,                         // колонка «Дельта»                ← слаг comparison.showDelta
    "showPercent": false,                       // колонка «Процент»               ← слаг comparison.showPercent
    "precision": -1,                            // точность чисел (-1 — авто)       ← слаг comparison.precision
    "axes": [                                   // оси данных (поля привязываются параметрами при добавлении)
      { "name": "values",     "type": "values",     "fields": [                  // ось значений   ← value_field + aggregation
          { "name": "metric_value", "alias": "Значение", "type": "number", "agg": "sum", "datasetId": 54 }
      ]},
      { "name": "series",     "type": "series",     "fields": [] },              // ось серий-разреза (необязательна)
      { "name": "indicators", "type": "indicators", "fields": [                  // ось показателей ← column_fields
          { "name": "metric_name", "alias": "Показатель", "type": "string", "datasetId": 54 }
      ]},
      { "name": "objects",    "type": "objects",    "fields": [                  // ось объектов   ← category_field
          { "name": "region", "alias": "Регион", "type": "string", "datasetId": 54 }
      ]},
      { "name": "filters",    "type": "filters",    "fields": [] }               // фильтры компонента
    ]
  }
}
```

> Объекты сравнения хранятся одновременно в `config.object1`/`config.object2` (верхний уровень `config`) и в записи `config.filters` по полю объектов (`type: "by compare"`, два выбранных значения). Слаги `comparison.object1` и `comparison.object2` синхронизируют обе записи. Колонки «Дельта» и «Процент» появляются при `showDelta=true` / `showPercent=true`. Точность чисел задаётся слагом `comparison.precision` (`-1` — авто, `0` — целые, `1`–`5` — знаков после запятой).

Каждый ключ внутри `config` соответствует строке в таблице ниже. Колонка **JSON-путь** показывает, где значение хранится в конфиге. Для вложенных параметров используется запись `объект[раздел].ключ`. Пустой путь означает верхний уровень `config`.

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
| Отступ Низ | `margin.b` | `(margin.b)` | int | `0` |  |
| Отступ Лево | `margin.l` | `(margin.l)` | int | `0` |  |
| Внутренний отступ | `margin.pad` | `(margin.pad)` | int | `0` |  |
| Отступ Право | `margin.r` | `(margin.r)` | int | `0` |  |
| Отступ Верх | `margin.t` | `(margin.t)` | int | `0` |  |

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
| Градиент | `gradient` | _секционно_ | bool | `False` |  |
| — | `nocopy` | `(nocopy)` | bool | `False` |  |
| — | `noexport` | `(noexport)` | bool | `False` |  |
| Заголовок | `showtitle` | `(showtitle)` | bool | `True` |  |

<!-- AUTO-TABLE:END -->

## Связанные

- [Каталог компонентов](../README.md)
- [Концепция: JSON-конфиг и слаги](../../concepts/components-json-slugs.md)
- [Справочник настроек (слаги)](../slugs/by-type.md)
- [Рецепты подготовки данных](../data-recipes.md)
- [Стилизация компонентов](../styling.md)
- [Фильтры и каскады](../filter-patterns.md)
