# Биржевая диаграмма (временные ряды)

Тип компонента: `HsStockAMchartsChart`

## Описание

Биржевая диаграмма выводит динамику одной или нескольких числовых метрик во времени. По горизонтальной оси откладываются даты, по вертикальной — значения. Подписи на оси времени формируются автоматически и подстраиваются под ширину компонента: год, месяц, дата или дата-время.

В отличие от обычной линейной диаграммы, биржевая ориентирована на интерактивное исследование длинных временных рядов: встроены прокрутка с мини-графиком, кнопки быстрого выбора периода, поля ручного ввода диапазона дат и возможность вынести отдельную метрику на дополнительную нижнюю панель.

## Когда применять

- Анализ трендов нескольких показателей за длительный период (месяцы, годы).
- Сравнение двух и более временных рядов на одной шкале.
- Интерактивное исследование данных с зумом в конкретный интервал дат.
- Мониторинг метрик с быстрым переключением периодов (месяц, квартал, полгода, год, с начала года).
- Вынос одного показателя на дополнительную панель для сравнения масштабов.

## Когда не подходит

- Данные без временной оси (только категории) — используйте столбчатую диаграмму: ось времени принимает лишь поля типа `date`, строковые и числовые категории по горизонтали не поддерживаются.
- Одно значение за период — используйте KPI-панель или спидометр.
- Малое число точек (меньше 5) — нагляднее столбчатая или линейная диаграмма.

## Поля и оси

Компонент использует следующие типы полей данных:

- **Категории** — поле типа `date`, задающее ось времени. Обязательно одно поле и обязательно дата: строковые и числовые поля в эту ось не принимаются, иначе временная шкала не строится. Агрегация для категорий не применяется; поле автоматически сортируется по возрастанию.
- **Значения** — одно или несколько числовых полей. Каждое поле даёт отдельный ряд (серию) на диаграмме. Для значений агрегация обязательна.
- **Серии** (необязательно) — поле-разрез. Серии задаются двумя способами: несколькими полями значений (каждое поле — отдельный ряд) либо одним полем-разрезом в этой оси (одно значение разбивается на ряды по категориям разреза). Если ось пуста, ряды определяются только полями значений.
- **Фильтры** — локальные фильтры компонента.

### Правила агрегации для диаграмм

Агрегация управляет тем, как несколько строк датасета сводятся к одной точке временного ряда:

- **Предагрегированный датасет** (значения уже посчитаны через `GROUP BY` в SQL) — передавайте агрегацию явно (например, `aggregation="sum"`). Без агрегации поле значений считается неготовым и диаграмма выходит пустой.
- **Сырой датасет, нужна сумма за период** — `aggregation="sum"`.
- **Среднее за период** — `aggregation="avg"` (аналогично `min`, `max`, `count`).
- `aggregation="none"` означает «не агрегировать» и для временных рядов почти не применяется.

Если поле значений осталось без агрегации, диаграмма обычно выходит пустой.

## Параметры добавления

Помимо привязки к датасету и полям, при добавлении компонента доступны параметры:

| Параметр | Назначение |
|----------|-----------|
| `x`, `y`, `w`, `h` | Позиция и размер компонента в сетке отчёта |
| `category_field` | Поле даты для оси времени (обязательно, тип `date`) |
| `value_field` | Числовое поле значений (можно несколько — несколько рядов) |
| `series_field` | Поле-разрез для дополнительного разбиения на серии |
| `aggregation` | Агрегация значений (`sum`, `avg`, `min`, `max`, `count`, `none`) |
| `preset` | Готовый визуальный пресет оформления |

## Формат данных

Подойдёт обычная таблица «дата + числовая метрика». Поле даты помещается в `category_field` — по нему строится временная шкала. Несколько метрик задаются несколькими полями значений: каждое становится отдельным рядом. Даты в датасете ожидаются в формате `yyyy-MM-dd` или `yyyy-MM-dd HH:mm:ss` (например, `2024-01-15` или `2024-01-15 14:30:00`).

Для плавной работы рекомендуется агрегировать данные на уровне датасета (например, по месяцам или годам), если временных меток очень много.

## Пример

Динамика выручки и прибыли по месяцам:

```python
component_crud(
    action="add",
    report_id=35,
    component_type="HsStockAMchartsChart",
    title="Динамика показателей",
    dataset_id=54,
    category_field="month",
    value_field="revenue",
    aggregation="sum",
    x=0, y=0, w=48, h=16,
    legend_visible=True,
)
```

Тот же ряд с включёнными кнопками выбора периода, дополнительной нижней панелью и наклоном подписей оси времени — через `config_overrides`:

```python
component_crud(
    action="add",
    report_id=35,
    component_type="HsStockAMchartsChart",
    title="Выручка и прибыль",
    dataset_id=54,
    category_field="month",
    value_field="revenue",
    aggregation="sum",
    config_overrides={
        "stock.dateZoomPanel": True,
        "stock.dateRangePanel": True,
        "stock.altAxisEnabled": True,
        "stock.dateAxisTickangle": -45,
        "stock.dateAxisMinGridDistance": 50,
    },
)
```

Разрез одной метрики по категориям (например, выручка по регионам — отдельный ряд на каждый регион) — через `series_field`:

```python
component_crud(
    action="add",
    report_id=35,
    component_type="HsStockAMchartsChart",
    title="Выручка по регионам",
    dataset_id=54,
    category_field="month",
    value_field="revenue",
    series_field="region",
    aggregation="sum",
    x=0, y=0, w=48, h=16,
    legend_visible=True,
)
```

Здесь `component_crud` — это RPC-метод MCP-сервера (вызов инструмента), а не REST-эндпоинт; `component_idx` в других действиях — 0-based индекс компонента в отчёте.

## JSON-конфигурация

Сервер собирает и хранит конфигурацию компонента в JSON. Ниже — аннотированная структура биржевой диаграммы: рядом с каждым ключом указано, что он задаёт и каким слагом управляется (полное соответствие — в таблице «Все настройки»).

```jsonc
{
  "type": "HsStockAMchartsChart",               // тип компонента (его отдаёт component_crud action="types_list")
  "config": {
    "title": "Динамика показателей",            // заголовок компонента
    "chartType": "stock",                       // внутренний тип диаграммы (фиксирован)
    "visualType": "stock",                      // визуальный тип (фиксирован)
    "showtitle": true,                          // показывать заголовок            ← слаг showtitle
    "noexport": false,                          // запретить экспорт данных        ← слаг noexport
    "nocopy": false,                            // запретить копирование данных    ← слаг nocopy
    "bgColor": "rgba(255, 255, 255, 1)",        // цвет фона компонента            ← слаг bgColor / параметр bg_color
    "margin":  { "l": 5, "r": 5, "t": 5, "b": 5, "pad": 0 },     // отступы        ← слаги margin.l/r/t/b/pad
    "outline": { "enabled": false, "width": 4 },                 // рамка          ← слаги outline.enabled/width/color
    "axes": [                                   // оси данных (поля привязываются параметрами при добавлении)
      { "name": "filters",    "type": "filters",    "fields": [] },               // фильтры компонента
      { "name": "categories", "type": "categories", "scaleType": "category",      // ось времени ← category_field
        "visible": true, "showscale": true, "showtitle": false,
        "showgrid": false, "showlabels": true, "fields": [
          { "name": "month", "alias": "Месяц", "type": "date",                    // поле обязательно типа date
            "agg": null, "order": "asc", "datasetId": 54 }                        // без агрегации, сортировка по возрастанию
      ]},
      { "name": "series",     "type": "series",     "fields": [] },               // ось серий-разреза ← series_field
      { "name": "values",     "type": "values",                                   // ось значений ← value_field + aggregation
        "visible": true, "showscale": true, "showtitle": false,
        "showgrid": false, "showlabels": true,
        "selectedFieldIndex": -2, "sortable": true, "fields": [                   // какое поле values вынести на доп.панель: индекс поля (0 = первое, -1 = последнее); -2 (умолчание) = доп.панель не используется
          { "name": "revenue", "alias": "Выручка", "type": "number",              // каждое поле values — отдельный ряд
            "agg": "sum", "datasetId": 54 }
      ]}
    ],
    "legend": {                                 // легенда
      "visible": true,                          //   показывать                    ← слаг legend.visible
      "position": "auto",                       //   позиция                       ← слаг legend.position
      "order": "normal"                         //   порядок (normal|reversed)     ← слаг legend.order
    },
    "labels": {                                 // подписи значений на точках
      "visible": false,                         //   показывать                    ← слаг labels.visible
      "position": "auto",                       //   позиция (auto|inside|outside) ← слаг labels.position
      "outer": { "fontsize": 12,                //   размер шрифта подписи         ← слаг labels.outer.fontsize
                 "color": "rgba(68,68,68,1)" }  //   цвет подписи                  ← слаг labels.outer.color
    },
    "visuals": []                               // визуальные параметры серий: массив (по элементу на серию)
  }
}
```

> Кнопки выбора периода, поля ввода диапазона дат, прокрутка, дополнительная нижняя панель и параметры оси времени задаются слагами семейства `stock.*` (см. таблицу «Все настройки»).

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
| Интервальное обновление | `stock.refresh` | `(refresh)` | bool | `False` | только этот тип |

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
| Отступ Низ | `margin.b` | `(margin.b)` | int | `5` |  |
| Отступ Лево | `margin.l` | `(margin.l)` | int | `5` |  |
| Внутренний отступ | `margin.pad` | `(margin.pad)` | int | `0` |  |
| Отступ Право | `margin.r` | `(margin.r)` | int | `5` |  |
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
| — | `expandH` | `(expandH)` | bool | `False` | только этот тип |
| — | `expandV` | `(expandV)` | bool | `False` | только этот тип |
| — | `fontSize` | `(fontSize)` | int | `12` |  |
| Градиент | `gradient` | _секционно_ | bool | `False` |  |
| — | `nocopy` | `(nocopy)` | bool | `False` |  |
| — | `noexport` | `(noexport)` | bool | `False` |  |
| Заголовок | `showtitle` | `(showtitle)` | bool | `True` |  |
| Ввод диапазона дат | `stock.dateRangePanel` | `(dateRangePanel)` | bool | `False` | только этот тип |
| Кнопки зумирования | `stock.dateZoomPanel` | `(dateZoomPanel)` | bool | `False` | только этот тип |
| Подзаголовок | `subtitle` | `(subtitle)` | str | `` | только этот тип |

### Прочее

| UI-контрол | MCP-слаг | JSON-путь | Тип | По умолчанию | Прим. |
|---|---|---|---|---|---|
| формат даты | `stock.dateFormat` | `(dateFormat)` | str | `yyyy-MM-dd` | только этот тип |

### Доп.диаграмма

| UI-контрол | MCP-слаг | JSON-путь | Тип | По умолчанию | Прим. |
|---|---|---|---|---|---|
| enable | `stock.altAxisEnabled` | `altAxis.enabled` | bool | `False` | только этот тип |

### Осн.диаграмма

| UI-контрол | MCP-слаг | JSON-путь | Тип | По умолчанию | Прим. |
|---|---|---|---|---|---|
| Макс.ширина подписи | `stock.dateAxisMaxWidth` | `dateAxis.maxWidth` | int | `0` | только этот тип |
| Мин.ширина сетки | `stock.dateAxisMinGridDistance` | `dateAxis.minGridDistance` | int | `30` | только этот тип |
| Наклон подписей | `stock.dateAxisTickangle` | `dateAxis.tickangle` | int_or_null | — | только этот тип |
| Два уровня подписей | `stock.dateAxisZigzag` | `dateAxis.zigzag` | bool | `False` | только этот тип |

### Скроллбар

| UI-контрол | MCP-слаг | JSON-путь | Тип | По умолчанию | Прим. |
|---|---|---|---|---|---|
| enable (инверт.) | `stock.scrollbarDisabled` | `scrollbar.disabled` | bool | `False` | только этот тип |

<!-- AUTO-TABLE:END -->

## Связанные

- [Каталог компонентов](../README.md)
- [Концепция: JSON-конфиг и слаги](../../concepts/components-json-slugs.md)
- [Справочник настроек (слаги)](../slugs/by-type.md)
- [Рецепты подготовки данных](../data-recipes.md)
- [Стилизация компонентов](../styling.md)
- [Фильтры и каскады](../filter-patterns.md)
- [Линейная диаграмма](line-chart.md)
- [Площадная диаграмма](area-chart.md)
