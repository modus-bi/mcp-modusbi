# Лепестковая диаграмма (радар)

Тип компонента: `HsRadarAMchartsChart`.

## Описание

Лепестковая диаграмма (радар, «паутина», «звезда») показывает значения нескольких показателей на радиальной шкале: категории располагаются по кругу как лучи (лепестки), а величина каждого показателя — это удалённость точки от центра. Соединённые точки образуют замкнутый профиль (контур), который можно залить цветом.

Радар удобен, когда нужно сравнить профили целиком — характеристики продуктов, компетенции сотрудников, метрики по регионам — и увидеть форму, а не точные числа. Несколько профилей накладываются друг на друга для сравнения.

## Когда применять

- Сравнение нескольких показателей по одному набору категорий «одним взглядом».
- Сравнение профилей: 2–3 объекта по общему набору признаков (наложенные контуры).
- Иллюстрация сбалансированности или перекоса показателей по нескольким направлениям.
- Оптимально 3–12 категорий (лепестков).

## Когда не подходит

- Больше 12 категорий — диаграмма становится нечитаемой, лучше столбчатая.
- Одна категория или один показатель — радиальная форма не даёт пользы.
- Точный анализ отдельных значений — столбчатая или линейная диаграмма читается точнее.
- Временные ряды — лучше линейная или площадная диаграмма.
- Показатели с сильно различающимся масштабом без нормализации — профиль искажается; рассмотрите логарифмическую шкалу.

## Поля и оси

Компонент использует следующие типы полей данных:

- **Категории** — текстовое поле, задающее лепестки (лучи) радара. Обычно одно поле. Агрегация для категорий не применяется.
- **Значения** — числовое поле, задающее удалённость точки от центра. Для значений агрегация обязательна. Несколько числовых полей дают несколько профилей (контуров) на одном радаре.
- **Фильтры** (необязательно) — поля-фильтры компонента; связываются с глобальными фильтрами отчёта.

Ось серий у радара остаётся пустой: дополнительные профили (контуры) создаются не разрезом по полю серий, а добавлением нескольких числовых полей на ось значений (см. «Параметры добавления»).

### Правила агрегации

Агрегация управляет тем, как несколько строк датасета сводятся к одному значению в лепестке:

- **Предагрегированный датасет** (значения уже посчитаны через `GROUP BY` в SQL) — передавайте агрегацию явно (например, `aggregation="max"`). Без агрегации поле значений считается неготовым и радар выходит пустым.
- **Сырой датасет, нужна сумма по категории** — `aggregation="sum"`.
- **Среднее по категории** — `aggregation="avg"` (аналогично `min`, `max`, `count`, `none`).

Если поле значений осталось без агрегации, диаграмма обычно выходит пустой.

## Параметры добавления

Помимо привязки к датасету и полям, при добавлении компонента доступны параметры:

| Параметр | Назначение |
|----------|-----------|
| `category_field` | Поле-категория — задаёт лепестки (лучи) радара (обязательно) |
| `value_field` | Числовое поле — задаёт удалённость точки от центра (обязательно) |
| `x`, `y`, `w`, `h` | Позиция и размер компонента в сетке отчёта |
| `aggregation` | Агрегация значений (`sum`, `avg`, `min`, `max`, `count`, `none`) |
| `legend_visible` | Показывать легенду |
| `preset` | Готовый визуальный пресет оформления |

Несколько профилей задаются перечислением нескольких числовых полей на оси значений (через `config_overrides` или последующее обновление компонента), а не отдельным параметром серий.

## Формат данных

Подойдёт обычная таблица с одной колонкой-категорией (лепестки) и одной или несколькими колонками-метриками. Категория (например, регион или навык) задаёт лепестки, каждая числовая метрика становится отдельным профилем (контуром) на одном радаре — это позволяет визуально сравнивать их формы. Для сравнения двух показателей добавьте на ось значений два числовых поля.

## Пример

Радар по одному показателю (лепестки — города):

```python
component_crud(
    action="add",
    report_id=35,
    component_type="HsRadarAMchartsChart",
    title="Продажи по городам",
    dataset_id=54,
    category_field="city",
    value_field="summa_rub",
    aggregation="sum",
    x=0, y=0, w=20, h=14,
    legend_visible=True,
)
```

Тип сетки «Паутина» (многоугольная) и увеличенный диаметр через `config_overrides`:

```python
component_crud(
    action="add",
    report_id=35,
    component_type="HsRadarAMchartsChart",
    title="Компетенции сотрудника",
    dataset_id=54,
    category_field="skill_name",
    value_field="score",
    aggregation="max",
    x=0, y=14, w=20, h=14,
    config_overrides={
        "grid.gridType": "polygons",
        "radius": 55,
        "legend.visible": False,
    },
)
```

Контурный радар без заливки (только линия профиля):

```python
component_crud(
    action="add",
    report_id=35,
    component_type="HsRadarAMchartsChart",
    title="Профиль показателей",
    dataset_id=54,
    category_field="region",
    value_field="value",
    aggregation="sum",
    config_overrides={
        "grid.filled": False,
        "grid.radarLabels": True,
    },
)
```

Здесь `component_crud` — это RPC-метод MCP-сервера (вызов инструмента), а не REST-эндпоинт; `component_idx` в других действиях — 0-based индекс компонента в отчёте.

## JSON-конфигурация

Сервер собирает и хранит конфигурацию компонента в JSON. Ниже — аннотированная структура (с пояснительными комментариями рядом с ключами) лепестковой диаграммы: для каждого ключа указано, что он задаёт и каким слагом управляется (полное соответствие — в таблице «Все настройки»).

```jsonc
{
  "type": "HsRadarAMchartsChart",                // тип компонента (его отдаёт component_crud action="types_list")
  "config": {
    "title": "Продажи по городам",               // заголовок компонента
    "chartType": "radarChart",                   // внутренний тип диаграммы (фиксирован)
    "visualType": "radar",                       // визуальное представление (фиксировано)
    "filled": true,                              // заливка профиля цветом         ← слаг grid.filled
    "showtitle": true,                           // показывать заголовок            ← слаг showtitle
    "noexport": false,                           // запретить экспорт               ← слаг noexport
    "nocopy": false,                             // запретить копирование данных    ← слаг nocopy
    "bgColor": "rgba(255, 255, 255, 1)",         // цвет фона                       ← слаг bgColor
    "margin":  { "l": 5, "r": 5, "t": 0, "b": 5, "pad": 0 },     // отступы         ← слаги margin.l/r/t/b/pad
    "outline": { "enabled": false, "width": 4 },                 // рамка           ← слаги outline.enabled/width
    "legend": {                                  // легенда
      "visible": true,                           //   показывать                    ← слаг legend.visible
      "position": "auto",                        //   позиция                       ← слаг legend.position
      "order": "normal"                          //   порядок (normal|reversed)     ← слаг legend.order
    },
    "labels": {                                  // подписи значений на профиле
      "visible": false,                          //   показывать                    ← слаг labels.visible
      "position": "auto",                        //   позиция                       ← слаг labels.position
      "outer": { "fontsize": 10, "color": "rgba(68,68,68,1)" }  // шрифт ← слаги labels.outer.fontsize/color
    },
    "axes": [                                    // оси данных (поля привязываются параметрами при добавлении)
      { "name": "filters",    "type": "filters",    "fields": [] },              // фильтры компонента
      { "name": "categories", "type": "categories", "scaleType": "category",     // ось лепестков ← category_field
        "fields": [
          { "name": "city", "alias": "Город", "type": "string", "datasetId": 54 }
      ]},
      { "name": "series",     "type": "series",     "fields": [] },              // ось серий — у радара всегда пустая
      { "name": "values",     "type": "values",                                 // ось значений ← value_field + aggregation
        "visible": true,                         //   видимость оси значений
        "showtitle": false,                      //   заголовок оси
        "showscale": true,                       //   показывать шкалу (деления)
        "showgrid": true,                        //   показывать сетку
        "gridType": "circles",                   //   тип сетки: circles|polygons   ← слаг grid.gridType
        "showlabels": true,                      //   подписи значений на шкале
        "radarlabels": true,                     //   подписи категорий у лепестков  ← слаг grid.radarLabels
        "fields": [
          { "name": "summa_rub", "alias": "Сумма, руб", "type": "number", "agg": "sum", "datasetId": 54 }
        ]
      }
    ],
    "visuals": []                                // визуальные параметры профилей: массив (по элементу на серию)
  }
}
```

> Диаметр радара задаётся слагом `radius` — процент от контейнера (0–100), по умолчанию `80` (см. таблицу «Все настройки» ниже). Меньшее значение, например `55`, уменьшает диаметр; большее — увеличивает. Тип сетки переключается слагом `grid.gridType`: `circles` — круговая (Радар), `polygons` — многоугольная (Паутина). Полный перечень параметров и их значений — в разделе «Все настройки (config_overrides)».

Каждый ключ внутри `config` соответствует строке в таблице ниже. Колонка **JSON-путь** показывает, где значение хранится в конфиге. Для вложенных параметров используется запись `объект[раздел].ключ` (например, `axes[values].gridType` — это ключ `gridType` внутри оси значений в `config.axes`). Пустой путь означает верхний уровень `config`.

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
| Размер шрифта | `labels.outer.fontsize` | `(labels.outer.fontsize)` | int | `10` |  |
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
| Диаметр | `radius` | `(radius)` | int | `80` | только этот тип |
| Заголовок | `showtitle` | `(showtitle)` | bool | `True` |  |

### Прочее

| UI-контрол | MCP-слаг | JSON-путь | Тип | По умолчанию | Прим. |
|---|---|---|---|---|---|
| заливка области | `grid.filled` | `filled` | bool | `True` | только этот тип |

### Ось Значения

| UI-контрол | MCP-слаг | JSON-путь | Тип | По умолчанию | Прим. |
|---|---|---|---|---|---|
| Тип сетки (Радар/Паутина) | `grid.gridType` | `axes[values].gridType` | enum | `circles` | только этот тип |
| Подписи категорий | `grid.radarLabels` | `axes[values].radarlabels` | bool | `True` | только этот тип |

<!-- AUTO-TABLE:END -->

## Связанные

- [Каталог компонентов](../README.md)
- [Концепция: JSON-конфиг и слаги](../../concepts/components-json-slugs.md)
- [Справочник настроек (слаги)](../slugs/by-type.md)
- [Рецепты подготовки данных](../data-recipes.md)
- [Стилизация компонентов](../styling.md)
- [Фильтры и каскады](../filter-patterns.md)
