# Параллельные координаты

Тип компонента: `HsParallelCoordsChart`

## Описание

Диаграмма «Параллельные координаты» предназначена для многомерного сравнения объектов по набору показателей с разными шкалами и единицами измерения. Каждый показатель отображается на собственной вертикальной оси, а каждый объект — линией, проходящей через все оси. Шкалы автоматически нормируются, поэтому на одном графике можно сопоставлять величины разного порядка (секунды, штуки, рубли, оценки от 1 до 5).

Под диаграммой располагается таблица-компаньон, а сами оси поддерживают интерактив: выделение диапазона на оси (brush) фильтрует линии, а перетаскивание заголовка оси меняет порядок осей. Цвет линий задаётся градиентом по значению на первой (левой) оси.

## Когда применять

- Сравнение множества объектов (от 5 до 100+) сразу по нескольким числовым показателям.
- Показатели имеют разные шкалы и единицы измерения, которые нельзя сопоставить напрямую.
- Поиск кластеров похожих объектов — линии со схожим профилем визуально группируются.
- Анализ компромиссов (trade-offs): высокий показатель A против низкого показателя B.
- Поиск аномалий и выбросов среди большого числа записей.

## Когда не подходит

- Менее трёх показателей — лучше столбчатая или радарная диаграмма.
- Менее трёх объектов — недостаточно данных для визуального сравнения, лучше таблица.
- Нужны точные числовые значения — лучше таблица.
- Чисто категориальные данные без числовых метрик — строковые оси поддерживаются, но малоинформативны.
- Тренд по времени — лучше линейная диаграмма или временные ряды.

## Поля и оси

В отличие от столбчатых и линейных диаграмм, у параллельных координат нет отдельных осей категорий и серий. Используются только две полки:

- **Фильтры** — поля, связывающие компонент с глобальными фильтрами отчёта (по совпадению `alias`). При срабатывании фильтра компонент перезапрашивает данные.
- **Значения** — все показатели для параллельных осей. Каждое поле полки становится отдельной вертикальной осью; порядок полей определяет порядок осей слева направо.

Особенности полки значений:

- Числовые поля (`number`, `calculated`) строят линейную шкалу `[min, max]`; строковые (`string`) — шкалу по уникальным значениям.
- **Первое числовое поле задаёт цветовой градиент** линий (от `colorMin` к `colorMax`), поэтому его выбор и положение влияют на восприятие.
- Рекомендуется первым ставить строковое поле-идентификатор (название объекта): оно автоматически попадает в нижнюю таблицу.
- Все показатели одного объекта должны лежать в **одной строке** датасета — каждый показатель отдельной колонкой.

### Правила агрегации

Агрегация для этого типа не применяется: компонент работает с «сырыми» строками — каждая строка датасета становится одной линией через все оси. Поэтому при добавлении на все поля принудительно выставляется отсутствие агрегации (`agg = null`). Если нужны предагрегированные показатели — считайте их заранее в SQL датасета (`GROUP BY`), а диаграмме отдавайте готовые строки.

## Параметры добавления

Помимо привязки к датасету и полям, при добавлении доступны параметры:

| Параметр | Назначение |
|----------|-----------|
| `x`, `y`, `w`, `h` | Позиция и размер компонента в сетке отчёта |
| `category_field` | Поле-идентификатор объекта (строковое); попадает на полку значений первым и в нижнюю таблицу |
| `value_field` | Показатели-оси: одно поле или несколько через запятую (`"acceleration,horsepower,rating"`) |
| `config_overrides` | Слаги тонкой настройки (`visuals.colorMin`, `visuals.colorMax`, `parallel.tableSize` и общие оформительские) |

## Формат данных

Каждый объект — одна строка; каждый показатель — отдельная колонка. Первым полем удобно поместить строковый идентификатор объекта.

```sql
SELECT
  model_name,        -- string: название (попадёт в нижнюю таблицу)
  acceleration,      -- number: разгон до 100 км/ч
  horsepower,        -- number: мощность
  engine_volume,     -- number: объём двигателя
  customer_rating    -- number: оценка
FROM cars
ORDER BY model_name
```

## Пример

Параллельные координаты по нескольким характеристикам, идентификатор объекта — в `category_field`, показатели-оси — списком в `value_field`:

```python
component_crud(
    action="add",
    report_id=35,
    component_type="HsParallelCoordsChart",
    title="Сравнение моделей по характеристикам",
    dataset_id=54,
    category_field="model_name",
    value_field="acceleration,horsepower,engine_volume,customer_rating",
    x=0, y=0, w=24, h=16,
)
```

Тот же компонент с настройкой цветового градиента и высоты нижней таблицы через слаги:

```python
component_crud(
    action="add",
    report_id=35,
    component_type="HsParallelCoordsChart",
    title="Сравнение моделей",
    dataset_id=54,
    category_field="model_name",
    value_field="acceleration,horsepower,engine_volume,customer_rating",
    x=0, y=0, w=24, h=16,
    config_overrides={
        "visuals.colorMin": "#2d6a4f",
        "visuals.colorMax": "#e76f51",
        "parallel.tableSize": 150,
    },
)
```

Здесь `component_crud` — это RPC-метод MCP-сервера (вызов инструмента), а не REST-эндпоинт; `component_idx` в других действиях — 0-based индекс компонента в отчёте.

## JSON-конфигурация

Сервер собирает и хранит конфигурацию компонента в JSON. Ниже — аннотированная структура: рядом с каждым ключом указано, что он задаёт и каким слагом управляется (полное соответствие — в таблице «Все настройки»).

```jsonc
{
  "type": "HsParallelCoordsChart",            // тип компонента (его отдаёт component_crud action="types_list")
  "config": {
    "title": "Сравнение моделей",             // заголовок компонента
    "chartType": "parallelCoordsChart",       // внутренний тип диаграммы (фиксирован)
    "showtitle": true,                        // показывать заголовок            ← слаг showtitle
    "noexport": false,                        // запретить экспорт в Excel       ← слаг noexport
    "nocopy": false,                          // запретить копирование данных    ← слаг nocopy
    "autoApply": true,                        // автообновление при изменении фильтров
    "bgColor": "rgba(255, 255, 255, 1)",      // цвет фона компонента            ← слаг bgColor
    "margin": { "t": 25, "r": 60, "b": 10, "l": 60 },  // отступы SVG-области (px)
    "outline": { "enabled": false, "width": 4 },        // рамка   ← слаги outline.enabled/width
    "colorMin": "#b0071d",                    // цвет линий при минимуме 1-й оси ← слаг visuals.colorMin
    "colorMax": "#231480",                    // цвет линий при максимуме 1-й оси ← слаг visuals.colorMax
    "inversions": [],                         // список имён полей с инвертированными осями (name, не alias)
    "tableSize": 100,                         // высота нижней таблицы (px)       ← слаг parallel.tableSize
    "exportFromTable": false,                 // экспортировать только поля нижней таблицы
    "axes": [                                 // оси компонента (поля привязываются параметрами при добавлении)
      { "name": "filters", "type": "filters", "title": "Фильтры", "fields": [] },   // полка фильтров
      {
        "name": "Значения", "type": "values", "title": "Значения",                  // полка значений (оси-измерения)
        "selectedFieldIndex": -2,             // индекс выбранного поля (-2 = ни одно не выбрано; управляется UI)
        "sortable": true,
        "fields": [                           // каждое поле = отдельная вертикальная ось; порядок = слева направо; agg=null у всех (норма: работа с «сырыми» строками)
          { "name": "model_name",   "alias": "Модель",   "type": "string", "agg": null, "datasetId": 54, "addToTable": false },
          { "name": "acceleration", "alias": "Разгон",   "type": "number", "agg": null, "datasetId": 54, "addToTable": false },
          { "name": "horsepower",   "alias": "Мощность", "type": "number", "agg": null, "datasetId": 54, "addToTable": true  }
        ]
      }
    ]
  }
}
```

> Цветовой градиент строится по значению на **первой числовой оси** — от `colorMin` к `colorMax`. Если первое поле строковое (идентификатор), цвет определяется по первому числовому полю в порядке осей. Строковое поле-идентификатор автоматически попадает в нижнюю таблицу; числовое поле добавляется в таблицу флагом `addToTable: true`. Чтобы инвертировать ось («меньше — лучше»), укажите техническое имя поля (`name`, не `alias`) в массиве `inversions`.

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
| Отступ Низ | `margin.b` | `(margin.b)` | int | `10` |  |
| Отступ Лево | `margin.l` | `(margin.l)` | int | `60` |  |
| Внутренний отступ | `margin.pad` | `(margin.pad)` | int | `0` |  |
| Отступ Право | `margin.r` | `(margin.r)` | int | `60` |  |
| Отступ Верх | `margin.t` | `(margin.t)` | int | `25` |  |

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
- [Словарь терминов](../../../GLOSSARY.md)
- [Концепция: JSON-конфиг и слаги](../../concepts/components-json-slugs.md)
- [Концепция: рендер-контракт](../../concepts/render-contract.md)
- [Справочник настроек (слаги)](../slugs/by-type.md)
- [Рецепты подготовки данных](../data-recipes.md)
- [Стилизация компонентов](../styling.md)
- [Фильтры и каскады](../filter-patterns.md)
- [Радарная диаграмма](radar-chart.md)
- [Таблица](table.md)
- [Пузырьковая диаграмма](bubble-chart.md)
- [Таблица сравнения](comparison.md)
