# Круговая диаграмма

Тип компонента: `HsPieAMchartsChart`

## Описание

Круговая диаграмма показывает доли категорий от общего значения метрики: каждый сектор — это вклад одной категории в целое. Поддерживает два режима: классический «пирог» и «пончик» (с пустым центром, куда можно вывести итоговую сумму). Дополнительно умеет группировать мелкие секторы в «Прочее», скрывать подписи незначимых долей и раскрашивать секторы палитрой, монохромным градиентом или индивидуально.

Круговая диаграмма отвечает на вопрос «какова структура» — кто какую долю занимает, — а не «у кого больше в абсолюте».

## Когда применять

- Структура одного показателя: доли товаров, регионов, типов в выручке или количестве.
- Небольшое число категорий (примерно 3–7), доли которых заметно различаются.
- Виджеты-«пончики» с итогом в центре для KPI-дашбордов.

## Когда не подходит

- Много категорий (больше 7–8) — секторы становятся неразличимы; лучше [столбчатая диаграмма](bar-chart.md) или таблица.
- Сравнение абсолютных значений между категориями — нагляднее [столбчатая диаграмма](bar-chart.md).
- Тренд во времени — лучше [линейная](line-chart.md) или [площадная](area-chart.md) диаграмма.
- Доли близки между собой (разница в несколько процентов) — секторы визуально неотличимы.
- Отрицательные значения — круговая диаграмма их не отображает.

## Поля и оси

Компонент использует четыре оси полей данных:

- **Категории** — текстовое поле, задающее секторы: каждое уникальное значение становится отдельным сектором. Обязательно минимум одно поле. Можно указать несколько полей для иерархического разреза. Агрегация для категорий не применяется.
- **Значения** — числовое поле, задающее размер секторов. Обязательно. Для значений агрегация обязательна.
- **Серии** (необязательно) — поле-разрез. Для обычной круговой диаграммы остаётся пустым; заполнять его при добавлении не нужно (параметр `series_field` к этому типу не применяется). Если поле в эту ось добавить позже через правку конфигурации, включается режим анимированной кольцевой диаграммы, которая поочерёдно переключает серии.
- **Фильтры** (необязательно) — поля локальной фильтрации компонента; связываются с глобальными фильтрами отчёта по совпадению псевдонима поля.

### Правила агрегации

Агрегация управляет тем, как несколько строк датасета сводятся к одному значению сектора:

- **Предагрегированный датасет** (значения уже посчитаны через `GROUP BY` в SQL) — передавайте агрегацию явно (например, `aggregation="max"`). На готовой группе любая агрегация вернёт то же единственное значение, но указать её необходимо: без агрегации поле значений считается неготовым и диаграмма выходит пустой.
- **Сырой датасет, нужна сумма по категории** — `aggregation="sum"` (типичный выбор для круговой диаграммы).
- **Среднее по категории** — `aggregation="avg"` (аналогично `min`, `max`, `count`).

Если поле значений осталось без агрегации, диаграмма обычно выходит пустой.

## Параметры добавления

Помимо привязки к датасету и полям, при добавлении компонента доступны параметры:

| Параметр | Назначение |
|----------|-----------|
| `x`, `y`, `w`, `h` | Позиция и размер компонента в сетке отчёта |
| `category_field` | Поле категорий (секторы диаграммы) |
| `value_field` | Числовое поле значений (размер секторов) |
| `aggregation` | Агрегация значений (`sum`, `avg`, `min`, `max`, `count`) |
| `legend_visible` | Показывать легенду |
| `preset` | Готовый визуальный пресет оформления |

Режим «пончик», итог в центре и шаблоны подписей задаются через `config_overrides` (слаги `showDonut`, `summEnabled`, `summFontSize`, `summColor`, `labelsTemplate` — см. раздел «Все настройки»).

## Формат данных

Особого формата не требуется: подойдёт обычная таблица «категория + числовая метрика». Каждая строка датасета — это категория и её значение; диаграмма сама посчитает доли (проценты) от суммы всех секторов. Для анимированной кольцевой диаграммы дополнительно добавьте текстовое поле-разрез в ось серий.

## Пример

Минимальная круговая диаграмма по предагрегированному датасету:

```python
component_crud(
    action="add",
    report_id=35,
    component_type="HsPieAMchartsChart",
    title="Структура продаж по типам товара",
    dataset_id=54,
    category_field="product_type",
    value_field="summa_rub",
    aggregation="sum",
    x=0, y=0, w=24, h=14,
    legend_visible=True,
)
```

Диаграмма-«пончик» с итоговой суммой в центре — задаётся через `config_overrides`:

```python
component_crud(
    action="add",
    report_id=35,
    component_type="HsPieAMchartsChart",
    title="Выручка по округам",
    dataset_id=54,
    category_field="fed_okrug",
    value_field="summa_rub",
    aggregation="sum",
    config_overrides={
        "showDonut": True,
        "summEnabled": True,
        "summFontSize": 28,
        "summColor": "rgba(51,51,51,1)",
        "labels.hidePercent": 3,
        "labelsTemplate": "[[categories]]: [[percents]]%",
    },
)
```

Монохромная окраска секторов и группировка мелких долей в «Прочее»:

```python
component_crud(
    action="add",
    report_id=35,
    component_type="HsPieAMchartsChart",
    title="Доли регионов",
    dataset_id=54,
    category_field="region",
    value_field="sales",
    aggregation="sum",
    config_overrides={
        "data.baseColor": "#4285F4",
        "data.colorStep": -6,
        "labels.groupPercent": 2,
        "labels.groupedTitle__ru": "Прочие регионы",
    },
)
```

Здесь `component_crud` — это RPC-метод MCP-сервера (вызов инструмента), а не REST-эндпоинт; `component_idx` в других действиях — 0-based индекс компонента в отчёте.

## JSON-конфигурация

Сервер собирает и хранит конфигурацию компонента в JSON. Ниже — аннотированная структура круговой диаграммы: рядом с каждым ключом указано, что он задаёт и каким слагом управляется (полное соответствие — в таблице «Все настройки»).

```jsonc
{
  "type": "HsPieAMchartsChart",                 // тип компонента (его отдаёт component_crud action="types_list")
  "config": {
    "title": "Структура продаж по типам товара", // заголовок компонента
    "chartType": "pieChart",                    // внутренний тип диаграммы (фиксирован)
    "visualType": "pie",                        // визуальный тип (фиксирован для этого класса)
    "showtitle": true,                          // показывать заголовок            ← слаг showtitle
    "noexport": false,                          // запретить экспорт               ← слаг noexport
    "nocopy": false,                            // запретить копирование           ← слаг nocopy
    "bgColor": "rgba(255, 255, 255, 1)",        // цвет фона                       ← слаг bgColor
    "margin":  { "l": 5, "r": 5, "t": 10, "b": 5, "pad": 0 },     // отступы при создании ← слаги margin.l/r/t/b/pad
    "outline": { "enabled": false, "width": 4 },                  // рамка         ← слаги outline.enabled/width
    "axes": [                                   // оси данных (поля привязываются параметрами при добавлении)
      { "name": "filters",    "type": "filters",    "fields": [] },              // фильтры компонента
      { "name": "categories", "type": "categories", "scaleType": "category",     // ось категорий ← category_field
        "fields": [
          { "name": "product_type", "alias": "Тип товара", "type": "string", "agg": null, "datasetId": 54 }
      ]},
      { "name": "series",     "type": "series",     "fields": [] },              // ось серий (пусто = обычный «пирог»)
      { "name": "values",     "type": "values",     "fields": [                  // ось значений  ← value_field + aggregation
          { "name": "summa_rub", "alias": "Сумма", "type": "number", "agg": "sum", "datasetId": 54 }
      ]}
    ],
    "legend": {                                 // легенда
      "visible": true,                          //   показывать                    ← слаг legend.visible
      "orientation": "h",                       //   ориентация (h|v)              ← слаг legend.orientation
      "position": "auto"                        //   позиция                       ← слаг legend.position
    },
    "labels": {                                 // подписи секторов
      "visible": true,                          //   показывать                    ← слаг labels.visible
      "position": "auto",                       //   позиция                       ← слаг labels.position
      "hidePercent": 2,                         //   скрывать подписи долей < N%   ← слаг labels.hidePercent
      "groupPercent": 0.5,                      //   группировать секторы < N% в «Прочее» ← слаг labels.groupPercent
      "groupCount": 9,                          //   макс. секторов при группировке по числу ← слаг labels.groupCount
      "switchControlNumberOfSegments": false    //   режим группировки: по числу (true) или % (false) ← слаг labels.switchControlNumberOfSegments
    },
    "visuals": []                               // индивидуальные цвета/подписи секторов (по элементу на сектор)
  }
}
```

> Режим «пончик» (`showDonut`), итог в центре (`summEnabled`, `summFontSize`, `summColor`), внутренний радиус (`visuals.innerRadius`), начальный угол (`visuals.startAngle`), монохромная окраска (`data.baseColor`, `data.colorStep`) и шаблоны подписей/подсказок (`labelsTemplate`, `balloonTemplate`) задаются через `config_overrides` — см. таблицу ниже.

Значения в примере выше — это то, что сервер записывает при создании компонента; они могут отличаться от колонки «По умолчанию» в таблице ниже, где приведены значения по умолчанию из схемы (например, для `margin.r` создание выставляет `5`, а схемное значение — `10`).

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
| базовый цвет | `data.baseColor` | `(baseColor)` | color | — | только этот тип |
| палитра | `visuals.colorPalette` | `(visuals[0].colorPalette)` | any | `pal_2018` |  |

### Стилизация

| UI-контрол | MCP-слаг | JSON-путь | Тип | По умолчанию | Прим. |
|---|---|---|---|---|---|
| Шаг яркости | `data.colorStep` | `(colorStep)` | int | `0` | только этот тип |
| Вид (Пирог/Бублик) | `showDonut` | `(showDonut)` | bool | `False` | только этот тип |
| (Цвет итога) | `summColor` | `(summColor)` | color | `rgba(0,0,0,1)` | только этот тип |
| Отображать итог | `summEnabled` | `(summEnabled)` | bool | `False` | только этот тип |
| Шрифт итога | `summFontSize` | `(summFontSize)` | int | `32` | только этот тип |

### Стиль элементов

| UI-контрол | MCP-слаг | JSON-путь | Тип | По умолчанию | Прим. |
|---|---|---|---|---|---|
| — | `visuals.autoColor` | `styleCommons.autoColor` | bool | `True` |  |
| — | `visuals.innerRadius` | `innerRadius` | int | `0` | только этот тип |
| Основной цвет | `visuals.mainColor` | `(visuals[0].mainColor)` | color | — |  |
| — | `visuals.startAngle` | `startAngle` | int | `0` | только этот тип |

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
| — | `labels.groupCount` | `(labels.groupCount)` | int | `9` | только этот тип |
| Скрыть если <N% | `labels.hidePercent` | `(labels.hidePercent)` | float | `0` |  |
| — | `labels.inner.fontsize` | `(labels.inner.fontsize)` | int | `12` |  |
| — | `labels.labelsColor` | `labels.inner.color` | color | — |  |
| — | `labels.outer.color` | `(labels.outer.color)` | color | `rgba(68,68,68,1)` |  |
| Размер шрифта | `labels.outer.fontsize` | `(labels.outer.fontsize)` | int | `12` |  |
| — | `labels.outerLabelsAngle` | `(labels.outerLabelsAngle)` | int | `0` | только этот тип |
| — | `labels.position` | `(labels.position)` | enum | `auto` |  |
| — | `labels.template` | `(labels.template)` | str | — |  |
| enable | `labels.visible` | `(labels.visible)` | bool | `True` |  |
| Шаблон | `labelsTemplate` | `(labelsTemplate)` | str | `[[percents]]%` | только этот тип |

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
| — | `balloonTemplate` | `(balloonTemplate)` | str | — | только этот тип |
| Цвет фона | `bgColor` | _секционно_ | color | `rgba(255,255,255,1)` |  |
| Цвет фона 2 | `bgColor2` | _секционно_ | color | — |  |
| — | `expandH` | `(expandH)` | bool | `False` | только этот тип |
| — | `expandV` | `(expandV)` | bool | `False` | только этот тип |
| — | `fontSize` | `(fontSize)` | int | `12` |  |
| Градиент | `gradient` | _секционно_ | bool | `False` |  |
| Заголовок группы «Прочее» | `labels.groupedTitle__ru` | `(labels.groupedTitle__ru)` | str | — | только этот тип |
| Управление кол-вом сегментов | `labels.switchControlNumberOfSegments` | `(labels.switchControlNumberOfSegments)` | bool | `False` | только этот тип |
| — | `nocopy` | `(nocopy)` | bool | `False` |  |
| — | `noexport` | `(noexport)` | bool | `False` |  |
| Диаметр | `radius` | `(radius)` | int | `80` | только этот тип |
| Заголовок | `showtitle` | `(showtitle)` | bool | `True` |  |
| Подзаголовок | `subtitle` | `(subtitle)` | str | `` | только этот тип |

### Прочее

| UI-контрол | MCP-слаг | JSON-путь | Тип | По умолчанию | Прим. |
|---|---|---|---|---|---|
| — | `labels.groupPercent` | `(labels.groupPercent)` | float | `0.5` | только этот тип |

<!-- AUTO-TABLE:END -->

## Связанные

- [Каталог компонентов](../README.md)
- [Концепция: JSON-конфиг и слаги](../../concepts/components-json-slugs.md)
- [Справочник настроек (слаги)](../slugs/by-type.md)
- [Рецепты подготовки данных](../data-recipes.md)
- [Стилизация компонентов](../styling.md)
- [Фильтры и каскады](../filter-patterns.md)
- [Столбчатая диаграмма](bar-chart.md)
- [Линейная диаграмма](line-chart.md)
- [Площадная диаграмма](area-chart.md)
