# Солнечные лучи (Sunburst)

Тип компонента: `HsSunburstChart`

**Создание через API:** нет — компонент добавляется только через веб-интерфейс конструктора отчётов. Примеры с `component_crud` ниже актуальны для управления уже добавленным компонентом (обновление настроек, позиции, привязок).

## Описание

Диаграмма «Солнечные лучи» визуализирует иерархические данные в виде концентрических колец. Каждый уровень иерархии — отдельное кольцо: внутреннее кольцо соответствует верхнему уровню, внешние кольца — вложенным уровням. Размер сектора пропорционален числовому значению с полки «Значения».

Компонент поддерживает интерактивный drill-down (раскрытие выбранного сектора как нового центра), режим фильтрации (клики устанавливают глобальный фильтр отчёта), управление количеством видимых колец и гибкую настройку подписей. Это удобный способ показать вклад частей в целое сразу на нескольких уровнях вложенности.

## Когда применять

- Иерархические данные с двумя и более уровнями вложенности (регион → район, категория → подкатегория, раздел → статья).
- Анализ структуры «часть–целое» одновременно на нескольких уровнях.
- Сравнение пропорций между родительскими и дочерними элементами.
- Интерактивный обзор иерархии: drill-down вглубь и возврат к корню.
- Использование диаграммы как интерактивного фильтра дашборда (режим фильтрации).

## Когда не подходит

- Плоские данные без иерархии — нагляднее круговая диаграмма.
- Много категорий на одном уровне (больше 15) — подписи становятся нечитаемыми.
- Нужно точное сравнение значений — точнее столбчатая диаграмма.
- Временные ряды — лучше линейная диаграмма.

## Поля и оси

Компонент использует три типа полей данных:

- **Категории** — текстовые поля, задающие иерархию. **Каждое поле — это отдельное кольцо**: первое поле образует внутреннее кольцо (корень), второе — следующее кольцо, и так далее. Можно указать несколько полей через запятую (`category_field="регион,район"`); порядок полей задаёт порядок колец от центра к краю. Агрегация для категорий не применяется.
- **Значения** — одно числовое поле, определяющее размер каждого сектора. Для значений агрегация обязательна. Поддерживается ровно одно поле-значение.
- **Фильтры** — локальные фильтры компонента (как правило, не используются; фильтрация выполняется через режим фильтрации или внешние панели фильтров).

### Правила агрегации

Агрегация управляет тем, как несколько строк датасета сводятся к одному значению сектора:

- **Сырой датасет, нужна сумма по уровню** — `aggregation="sum"` (самый частый случай: значения дочерних элементов суммируются вверх по иерархии).
- **Среднее по уровню** — `aggregation="avg"` (аналогично `min`, `max`, `count`).
- **Предагрегированный датасет** (значения уже посчитаны в SQL) — передавайте агрегацию явно (например, `aggregation="max"`): на готовой группе она вернёт то же единственное значение, но без агрегации поле значений считается неготовым и диаграмма выходит пустой.

Если поле значений осталось без агрегации, диаграмма обычно выходит пустой.

## Параметры (привязка и позиция)

Компонент добавляется в отчёт через веб-интерфейс. Привязку полей, позицию и тонкие настройки задают как в редакторе, так и через MCP-вызовы управления (`component_crud`) над уже добавленным компонентом:

| Параметр | Назначение |
|----------|-----------|
| `x`, `y`, `w`, `h` | Позиция и размер компонента в сетке отчёта (рекомендуется `h ≥ 14`, иначе кольца сжимаются) |
| `category_field` | Поля иерархии через запятую; порядок = порядок колец от центра к краю |
| `value_field` | Числовое поле — размер секторов |
| `aggregation` | Агрегация значений (`sum`, `avg`, `min`, `max`, `count`) |
| `config_overrides` | Тонкая настройка через слаги (см. раздел «Все настройки») |

## Формат данных

Подойдёт обычная таблица, где каждая строка содержит уровни иерархии и числовую метрику, например `округ | район | значение`. Сервер сам сгруппирует данные по уровням и просуммирует (или иначе агрегирует) значения дочерних элементов. Достаточно двух категорийных колонок и одной числовой; число уровней иерархии не ограничено двумя.

## Пример

Примеры ниже показывают целевую конфигурацию через вызовы `component_crud`. Так как компонент создаётся в редакторе, эти параметры применяют к уже добавленному компоненту (либо воспроизводят вручную в панели настроек).

Диаграмма с двухуровневой иерархией по сырому датасету:

```python
component_crud(
    action="add",
    report_id=35,
    component_type="HsSunburstChart",
    title="Структура округов и районов",
    dataset_id=3,
    category_field="okrug,rayon",
    value_field="value",
    aggregation="sum",
    x=0, y=0, w=24, h=16,
)
```

Диаграмма как интерактивный фильтр дашборда (клики устанавливают глобальный фильтр; невыбранные сектора становятся серыми):

```python
component_crud(
    action="add",
    report_id=35,
    component_type="HsSunburstChart",
    title="Фильтр по структуре",
    dataset_id=3,
    category_field="okrug,rayon",
    value_field="value",
    aggregation="sum",
    x=0, y=16, w=24, h=16,
    config_overrides={
        "sunburst.filterMode": True,
        "sunburst.minPercent": 2,
        "sunburst.ellipsisLength": 10,
    },
)
```

Постепенное раскрытие: показать сначала одно кольцо и дать кнопки `+`/`−`, обрезать длинные подписи и скрыть подписи у мелких секторов:

```python
component_crud(
    action="add",
    report_id=35,
    component_type="HsSunburstChart",
    title="Структура расходов",
    dataset_id=3,
    category_field="razdel,podrazdel,statya",
    value_field="summa",
    aggregation="sum",
    config_overrides={
        "sunburst.visibleLayers": 1,
        "sunburst.layerButtons": True,
        "sunburst.minPercent": 3,
        "sunburst.ellipsisLength": 12,
        "sunburst.splittedMode": True,
        "sunburst.precision": 0,
    },
)
```

Здесь `component_crud` — это RPC-метод MCP-сервера (вызов инструмента), а не REST-эндпоинт; `component_idx` в других действиях — 0-based индекс компонента в отчёте.

## JSON-конфигурация

Сервер собирает и хранит конфигурацию компонента в JSON. Ниже — аннотированная структура диаграммы «Солнечные лучи»: рядом с каждым ключом указано, что он задаёт и каким слагом управляется (полное соответствие — в таблице «Все настройки»).

```jsonc
{
  "type": "HsSunburstChart",                  // тип компонента (его отдаёт component_crud action="types_list")
  "config": {
    "title": "Структура округов и районов",   // заголовок компонента
    "chartType": "sunburstChart",             // внутренний тип диаграммы (фиксирован)
    "visualType": "sunburst",                 // визуальный тип (фиксирован)
    "showtitle": true,                        // показывать заголовок            ← слаг showtitle
    "noexport": false,                        // запретить экспорт               ← слаг noexport
    "nocopy": false,                          // запретить копирование           ← слаг nocopy
    "bgColor": "rgba(255, 255, 255, 1)",      // цвет фона                       ← слаг bgColor
    "filterMode": false,                      // режим фильтрации (клики → фильтр) ← слаг sunburst.filterMode
    "darkLabels": false,                      // чёрные подписи на всех кольцах    ← слаг sunburst.darkLabels
    "splittedMode": false,                    // двустрочные подписи (по пробелу)  ← слаг sunburst.splittedMode
    "ellipsisLength": null,                   // лимит длины подписи в символах    ← слаг sunburst.ellipsisLength
    "minPercent": 0,                          // мин. % сектора для показа подписи ← слаг sunburst.minPercent
    "precision": 0,                           // знаков после запятой в тултипе    ← слаг sunburst.precision
    "layerExpand": false,                     // разворот: false=послойно/true=посекторно ← слаг sunburst.layerExpand
    "visibleLayersNumber": null,              // начальное число видимых колец (JSON-ключ visibleLayersNumber) ← слаг sunburst.visibleLayers
    "layerButtons": false,                    // кнопки +/- управления уровнями    ← слаг sunburst.layerButtons
    "colorsEnabled": true,                    // true=палитра, false=монохром      ← слаг sunburst.colorsEnabled
    "font": {                                 // шрифт подписей
      "size": 0.8,                            //   размер (em)                     ← слаг sunburst.fontSize
      "family": "Arial"                       //   семейство                       ← слаг sunburst.fontFamily
    },
    "margin":  { "l": 5, "r": 10, "t": 10, "b": 5, "pad": 0 },    // отступы       ← слаги margin.l/r/t/b/pad
    "outline": { "enabled": false, "width": 4 },                  // рамка         ← слаги outline.enabled/width
    "legend":  { "visible": true, "position": "auto" },           // легенда
    "axes": [                                 // оси данных (поля привязываются параметрами при добавлении)
      { "name": "filters",    "type": "filters",    "fields": [] },              // локальные фильтры
      { "name": "categories", "type": "categories", "selectedFieldIndex": -2, "fields": [  // уровни иерархии (-2 = все кольца активны) ← category_field
          { "name": "okrug", "alias": "Округ", "type": "string", "agg": null, "datasetId": 3 },  // 1-е кольцо (корень)
          { "name": "rayon", "alias": "Район", "type": "string", "agg": null, "datasetId": 3 }   // 2-е кольцо
      ]},
      { "name": "values",     "type": "values",     "fields": [                  // значения ← value_field + aggregation
          { "name": "value", "alias": "Значение", "type": "number", "agg": "sum", "datasetId": 3 }
      ]}
    ],
    "visuals": []                             // визуальные параметры (по умолчанию пусто)
  }
}
```

> Порядок полей в оси `categories` важен: первое поле — внутреннее кольцо (корень), каждое следующее — кольцо наружу. Поле значений всегда одно.

> Кнопки `+`/`−` появляются только при заданном `visibleLayersNumber` (слаг `sunburst.visibleLayers`) **и** `layerButtons=true` (слаг `sunburst.layerButtons`) одновременно.

> Drill-down работает по умолчанию (при `filterMode=false`): клик по сектору раскрывает его как новый центр, клик по центральному кругу возвращает к корню. Режим фильтрации включается слагом `sunburst.filterMode: true` — тогда клики не раскрывают, а устанавливают глобальный фильтр отчёта. Состояние drill-down — временное (интерактивное) и в конфиг не сохраняется.

> Слаг `sunburst.layerExpand` задаёт способ раскрытия: `false` (по умолчанию) — открывается один следующий уровень целиком (послойно); `true` — при клике раскрываются сразу все подуровни выбранного сектора (посекторно).

> Слаг `sunburst.precision` задаёт число знаков после запятой в значении внутри всплывающей подсказки (тултипа) при наведении на сектор; на сами кольца не влияет.

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
| Цвет фона | `bgColor` | _секционно_ | color | `rgba(255,255,255,1)` |  |
| Цвет фона 2 | `bgColor2` | _секционно_ | color | — |  |
| — | `fontSize` | `(fontSize)` | int | `12` |  |
| Градиент | `gradient` | _секционно_ | bool | `False` |  |
| — | `nocopy` | `(nocopy)` | bool | `False` |  |
| — | `noexport` | `(noexport)` | bool | `False` |  |
| Заголовок | `showtitle` | `(showtitle)` | bool | `True` |  |

<!-- AUTO-TABLE:END -->

## Цвета и палитра

Цвет внутреннего кольца берётся из палитры отчёта по индексу сектора, внешние кольца — осветлённые оттенки того же цвета. Палитра задаётся на уровне отчёта; компонент использует активную палитру автоматически при `sunburst.colorsEnabled=true` (значение по умолчанию). При `sunburst.colorsEnabled=false` все корневые сектора красятся одним цветом (монохромный режим).

Палитра по умолчанию — `pal_2018` (10 цветов). Доступны также альтернативные палитры отчёта: тёплые, синие, зелёно-серые тона, яркая (насыщенная) и монохромная (оттенки серого), а также настраиваемая палитра пользователя. Слаг выбора палитры компонента — `visuals.colorPalette` (см. таблицу «Все настройки»).

## Связанные

- [Каталог компонентов](../README.md)
- [Концепция: JSON-конфиг и слаги](../../concepts/components-json-slugs.md)
- [Справочник настроек (слаги)](../slugs/by-type.md)
- [Рецепты подготовки данных](../data-recipes.md)
- [Стилизация компонентов](../styling.md)
- [Фильтры и каскады](../filter-patterns.md)
- [Круговая диаграмма](pie-chart.md)
