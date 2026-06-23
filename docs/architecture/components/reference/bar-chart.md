# Столбчатая диаграмма

Тип компонента: `HsBarAMchartsChart`

## Описание

Столбчатая диаграмма (гистограмма) показывает числовые значения в виде столбцов и предназначена для визуального сравнения величин между категориями. Поддерживает вертикальную и горизонтальную ориентацию, несколько серий данных (рядом, стек, 100%-структура), дополнительную ось значений, прокрутку по категориям и настраиваемую точность чисел.

Это один из самых универсальных типов диаграмм: им удобно показывать «кто больше», ранжировать категории и раскладывать значение на составляющие.

## Когда применять

- Сравнение значений между категориями (примерно до 15 категорий на экране).
- Ранжирование категорий по убыванию или возрастанию.
- Сравнение нескольких серий — рядом (кластеризованные столбцы) или стеком.
- Показ структуры: доля каждой серии в общем объёме (100%-стек).
- Комбинированные диаграммы с двумя осями значений (разные единицы измерения).

## Когда не подходит

- Тренд по времени — лучше линейная или площадная диаграмма.
- Пропорции одного набора (части целого) — лучше круговая диаграмма.
- Очень много категорий (десятки) — лучше таблица или горизонтальная ориентация с прокруткой.
- Много серий (больше 5–6) — восприятие ухудшается, рассмотрите таблицу.

## Поля и оси

Компонент использует четыре типа полей данных:

- **Категории** — текстовое (или дата/число) поле, задающее столбцы. Можно указать несколько полей — они образуют иерархический разрез (например, год → квартал → месяц); на диаграмме можно интерактивно переходить между уровнями. Агрегация для категорий не применяется.
- **Значения** — числовое поле, задающее высоту столбцов. Для значений агрегация обязательна.
- **Серии** (необязательно) — поле-разрез, делящее каждую категорию на несколько окрашенных столбцов. Если пусто — все данные идут одной серией.
- **Дополнительная ось значений** (необязательно) — вторая шкала для метрик с другим масштабом.

### Правила агрегации

Агрегация управляет тем, как несколько строк датасета сводятся к одному значению столбца:

- **Предагрегированный датасет** (значения уже посчитаны через `GROUP BY` в SQL) — передавайте агрегацию явно (например, `aggregation="max"`). На готовой группе любая агрегация вернёт то же единственное значение, но указать её необходимо: без агрегации поле значений считается неготовым и диаграмма выходит пустой.
- **Сырой датасет, нужна сумма по категории** — `aggregation="sum"`.
- **Среднее по категории** — `aggregation="avg"` (аналогично `min`, `max`, `count`).
- Значение `aggregation="none"` означает «не агрегировать» — для столбчатой диаграммы оно почти не используется (характерно для таблиц, где нужно показать все строки).

Если поле значений осталось без агрегации, диаграмма обычно выходит пустой.

## Параметры добавления

Помимо привязки к датасету и полям, при добавлении компонента доступны параметры:

| Параметр | Назначение |
|----------|-----------|
| `x`, `y`, `w`, `h` | Позиция и размер компонента в сетке отчёта |
| `orientation` | Ориентация столбцов: `"v"` (вертикально) или `"h"` (горизонтально) |
| `stacking` | Режим серий: `"none"` (рядом), `"normal"` (стек), `"percent"` (100%-структура) |
| `series_field` | Поле-разрез для нескольких серий |
| `aggregation` | Агрегация значений (`sum`, `avg`, `min`, `max`, `count`, `none`) |
| `preset` | Готовый визуальный пресет оформления |

## Формат данных

Особого формата не требуется: подойдёт обычная таблица «категория + числовая метрика». Для нескольких серий добавьте текстовое поле-разрез в ось серий. Для временных рядов (по дням, месяцам, годам) дата выступает категорией — поместите поле даты в `category_field`, и диаграмма построит временную шкалу.

## Пример

Вертикальная столбчатая диаграмма по предагрегированному датасету:

```python
component_crud(
    action="add",
    report_id=35,
    component_type="HsBarAMchartsChart",
    title="Продажи по регионам",
    dataset_id=54,
    category_field="region",
    value_field="summa_rub",
    aggregation="sum",
    orientation="v",
    x=0, y=0, w=24, h=14,
    legend_visible=True,
)
```

Горизонтальная диаграмма со скруглением и градиентом — задаётся параметром `orientation="h"` плюс `config_overrides`:

```python
component_crud(
    action="add",
    report_id=35,
    component_type="HsBarAMchartsChart",
    title="Топ продуктов",
    dataset_id=54,
    category_field="product",
    value_field="sales",
    aggregation="sum",
    orientation="h",
    config_overrides={
        "visuals.columnBorderRadius": 4,
        "data.baseColor": "#3366CC",
        "data.colorStep": 6,
        "legend.visible": False,
    },
)
```

Несколько серий рядом (кластеризованные столбцы): поле-разрез задаётся через `series_field`:

```python
component_crud(
    action="add",
    report_id=35,
    component_type="HsBarAMchartsChart",
    title="Продажи по регионам и типам товара",
    dataset_id=54,
    category_field="region",
    value_field="sales",
    series_field="product_type",
    aggregation="sum",
    stacking="none",
    x=0, y=14, w=24, h=14,
    config_overrides={
        "visuals.clustered": True,
        "legend.visible": True,
    },
)
```

Здесь `component_crud` — это RPC-метод MCP-сервера (вызов инструмента), а не REST-эндпоинт; `component_idx` в других действиях — 0-based индекс компонента в отчёте.

## JSON-конфигурация

Сервер собирает и хранит конфигурацию компонента в JSON. Ниже — аннотированная структура столбчатой диаграммы: рядом с каждым ключом указано, что он задаёт и каким слагом управляется (полное соответствие — в таблице «Все настройки»).

```jsonc
{
  "type": "HsBarAMchartsChart",                 // тип компонента (его отдаёт component_crud action="types_list")
  "config": {
    "title": "Продажи по регионам",             // заголовок компонента
    "chartType": "barChart",                    // внутренний тип диаграммы (фиксирован)
    "orientation": "v",                         // ориентация: "v"|"h"  (параметр orientation при добавлении)
    "showtitle": true,                          // показывать заголовок            ← слаг showtitle
    "bgColor": "rgba(255, 255, 255, 1)",        // цвет фона                       ← слаг bgColor
    "baseColor": "#1F77B4",                     // базовый цвет столбцов           ← слаг data.baseColor
    "colorStep": 0,                             // шаг яркости между сериями       ← слаг data.colorStep
    "margin":  { "l": 5, "r": 10, "t": 10, "b": 5, "pad": 0 },    // отступы       ← слаги margin.l/r/t/b/pad
    "outline": { "enabled": false, "width": 4 },                  // рамка         ← слаги outline.enabled/width
    "legend": {                                 // легенда
      "visible": true,                          //   показывать                    ← слаг legend.visible
      "position": "auto",                       //   позиция                       ← слаг legend.position
      "order": "normal"                         //   порядок (normal|reversed)     ← слаг legend.order
    },
    "axes": [                                   // оси данных (поля привязываются параметрами при добавлении)
      { "name": "filters",    "type": "filters",    "fields": [] },              // фильтры компонента
      { "name": "categories", "type": "categories", "fields": [                  // ось категорий ← category_field
          { "name": "region", "alias": "Регион", "type": "string", "datasetId": 54 }
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

> Точность чисел задаётся не ключом `precision` (его в конфиге столбчатой диаграммы нет), а слагами `numberPrecision` и `percentPrecision` через `config_overrides`.

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
| базовый цвет | `data.baseColor` | `(baseColor)` | color | — | только этот тип |
| Сглаживание | `style.smoothing` | `(styleCommons.smoothing)` | float | `0` | только этот тип |
| тип визуализации | `visuals.chartType` | `visualType` | str | — | только этот тип |
| палитра | `visuals.colorPalette` | `(visuals[0].colorPalette)` | any | `pal_2018` |  |

### Стилизация

| UI-контрол | MCP-слаг | JSON-путь | Тип | По умолчанию | Прим. |
|---|---|---|---|---|---|
| Шаг яркости | `data.colorStep` | `(colorStep)` | int | `0` | только этот тип |
| — | `style.autoColor` | `(styleCommons.autoColor)` | enum | `False` | только этот тип |

### Стиль элементов

| UI-контрол | MCP-слаг | JSON-путь | Тип | По умолчанию | Прим. |
|---|---|---|---|---|---|
| — | `visuals.autoColor` | `styleCommons.autoColor` | bool | `True` |  |
| — | `visuals.clustered` | `styleCommons.clustered` | bool | `False` | только этот тип |
| — | `visuals.columnBorderRadius` | `(visuals[0].columnBorderRadius)` | int | `0` | только этот тип |
| Ширина столбцов | `visuals.columnWidth` | `styleCommons.columnWidth` | int | `80` | только этот тип |
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

<!-- AUTO-TABLE:END -->

## Связанные

- [Каталог компонентов](../README.md)
- [Концепция: JSON-конфиг и слаги](../../concepts/components-json-slugs.md)
- [Справочник настроек (слаги)](../slugs/by-type.md)
- [Рецепты подготовки данных](../data-recipes.md)
- [Стилизация компонентов](../styling.md)
- [Фильтры и каскады](../filter-patterns.md)
