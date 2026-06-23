# Древовидная карта (TreeMap)

Тип компонента: `HsTreeMap`

## Описание

Древовидная карта показывает иерархические данные в виде вложенных прямоугольников. Площадь каждого блока пропорциональна его числовому значению, поэтому крупные категории сразу видны как самые большие прямоугольники. Иерархия задаётся несколькими полями категорий: первое поле — верхний уровень (крупные блоки), следующие — вложенные подуровни.

Компонент удобен для анализа структуры «целое → части» сразу на нескольких уровнях вложенности и для быстрого визуального обнаружения самых крупных и самых мелких элементов. При двух и более уровнях иерархии работает интерактивное раскрытие (зум): клик по блоку показывает его дочерние элементы, кнопка возврата поднимает на уровень выше.

## Когда применять

- Иерархические данные с числовым показателем (бюджет по округам → регионам, расходы по статьям → подстатьям).
- Анализ структуры «целое → части» с несколькими уровнями детализации.
- Сравнение пропорций категорий на одной плоскости, без осей.
- Быстрый поиск крупнейших и наименьших элементов в наборе.
- Использование диаграммы как интерактивного фильтра дашборда (режим фильтрации).

## Когда не подходит

- Плоские данные без иерархии — нагляднее столбчатая или круговая диаграмма.
- Нужно точное сравнение чисел — точнее таблица: площади блоков не дают читать значения с высокой точностью.
- Слишком много мелких категорий (несколько десятков) — блоки становятся нечитаемыми.
- Временные ряды и тренды — лучше линейная или площадная диаграмма.

## Поля и оси

Компонент использует четыре оси (полки) данных:

- **Категории (иерархия)** — текстовые поля, задающие вложенные блоки. **Порядок полей задаёт уровни:** первое поле — верхний уровень, второе — дочерний, и так далее. Поддерживается один и более уровней; при одном поле карта одноуровневая. Агрегация к полям категорий не применяется. В параметрах добавления несколько уровней передаются одной строкой через запятую: `category_field="округ,регион"`.
- **Значения** — числовое поле, определяющее площадь блоков. Для него агрегация обязательна (см. ниже). Размер прямоугольника пропорционален агрегированному значению.
- **Серии** (необязательно) — поле-разрез для группировки по цвету: каждому значению серии назначается цвет из палитры отчёта. Если серия задана, ось категорий может оставаться пустой — данные группируются по серии.
- **Фильтры** — поля для локальной фильтрации компонента и связи с глобальными фильтрами отчёта по совпадению `alias`.

Цвет блоков по умолчанию берётся из палитры отчёта. Для постоянного или условного цвета добавляют вычисляемое поле цвета в ось значений — см. раздел JSON-конфигурации.

### Правила агрегации

Агрегация управляет тем, как несколько строк датасета сводятся к одному числу для блока:

- **Предагрегированный датасет** (значения уже посчитаны через `GROUP BY` в SQL) — передавайте агрегацию явно (например, `aggregation="max"`). На готовой группе любая агрегация вернёт то же единственное значение, но указать её необходимо: без агрегации поле значений считается неготовым и карта выходит пустой.
- **Сырой датасет, нужна сумма по категории** — `aggregation="sum"`.
- **Среднее по категории** — `aggregation="avg"` (аналогично `min`, `max`, `count`).

Если поле значений осталось без агрегации, карта обычно выходит пустой.

## Параметры добавления

Помимо привязки к датасету и полям, при добавлении компонента доступны параметры:

| Параметр | Назначение |
|----------|-----------|
| `x`, `y`, `w`, `h` | Позиция и размер компонента в сетке отчёта |
| `category_field` | Поля иерархии; несколько уровней — через запятую (`"округ,регион"`) |
| `value_field` | Числовое поле, задающее площадь блоков |
| `series_field` | Поле-разрез для группировки по цвету (необязательно) |
| `aggregation` | Агрегация значений (`sum`, `avg`, `min`, `max`, `count`) |
| `preset` | Готовый визуальный пресет оформления |

## Формат данных

Особого формата не требуется: подойдёт обычная таблица «категория + числовая метрика». Для нескольких уровней иерархии добавьте в датасет соответствующие текстовые поля (округ, регион, город) и перечислите их по порядку вложенности в `category_field`. Числовое поле метрики идёт в `value_field` с агрегацией.

## Пример

Двухуровневая карта по предагрегированному датасету (округ → регион):

```python
component_crud(
    action="add",
    report_id=35,
    component_type="HsTreeMap",
    title="Бюджет по округам и регионам",
    dataset_id=54,
    category_field="fed_okrug,region",
    value_field="summa_rub",
    aggregation="sum",
    x=0, y=0, w=48, h=16,
)
```

Одноуровневая карта со скрытыми подписями (только цветные блоки, значения — во всплывающей подсказке):

```python
component_crud(
    action="add",
    report_id=35,
    component_type="HsTreeMap",
    title="Структура расходов",
    dataset_id=54,
    category_field="category",
    value_field="amount",
    aggregation="sum",
    config_overrides={
        "labels.visible": False,
        "balloon.visible": True,
    },
)
```

Карта как интерактивный фильтр дашборда (клик по блоку фильтрует остальные компоненты):

```python
component_crud(
    action="add",
    report_id=35,
    component_type="HsTreeMap",
    title="Округа",
    dataset_id=54,
    category_field="fed_okrug",
    value_field="summa_rub",
    aggregation="sum",
    config_overrides={
        "treemap.filterMode": True,
    },
)
```

Здесь `component_crud` — это RPC-метод MCP-сервера (вызов инструмента), а не REST-эндпоинт; `component_idx` в других действиях — 0-based индекс компонента в отчёте.

## JSON-конфигурация

Сервер собирает и хранит конфигурацию компонента в JSON. Ниже — аннотированная структура древовидной карты: рядом с каждым ключом указано, что он задаёт и каким слагом управляется (полное соответствие — в таблице «Все настройки»).

```jsonc
{
  "type": "HsTreeMap",                            // тип компонента (его отдаёт component_crud action="types_list")
  "config": {
    "title": "Бюджет по округам",                 // заголовок компонента
    "chartType": "treeMap",                       // внутренний тип диаграммы (фиксирован)
    "showtitle": true,                            // показывать заголовок            ← слаг showtitle
    "noexport": false,                            // запретить экспорт               ← слаг noexport
    "nocopy": false,                              // запретить копирование данных    ← слаг nocopy
    "filterMode": false,                          // режим фильтрации: клик по блоку фильтрует дашборд ← слаг treemap.filterMode
    "bgColor": "rgba(255, 255, 255, 1)",          // цвет фона                       ← слаг bgColor
    "margin":  { "l": 15, "r": 15, "t": 15, "b": 0, "pad": 0 },   // отступы         ← слаги margin.l/r/t/b/pad
    "outline": { "enabled": false, "width": 4 },                  // рамка           ← слаги outline.enabled/width
    "balloon": { "visible": true },               // всплывающая подсказка при наведении ← слаг balloon.visible
    "labels":  {                                  // подписи на блоках
      "visible": true,                            //   показывать подписи            ← слаг labels.visible
      "position": "auto"                          //   позиция подписи
    },
    // "precision": 1,                             // знаков после запятой (добавляется при настройке) ← слаг treemap.precision
    "axes": [                                      // оси данных (поля привязываются параметрами при добавлении)
      { "name": "filters",    "title": "Фильтры",  "type": "filters",    "fields": [] },        // фильтры компонента
      { "name": "Категории",  "title": "Категории","type": "categories", "fields": [            // иерархия ← category_field
          { "name": "fed_okrug", "alias": "Округ",  "type": "string", "datasetId": 54, "agg": null },   // 1-й уровень
          { "name": "region",    "alias": "Регион", "type": "string", "datasetId": 54, "agg": null }    // 2-й уровень (вложенный)
      ]},
      { "name": "series",     "title": "Серии",    "type": "series",     "fields": [] },        // ось серий-разреза ← series_field
      { "name": "Значения",   "title": "Значения", "type": "values",     "fields": [            // площадь блоков ← value_field + aggregation
          { "name": "summa_rub", "alias": "Сумма, руб", "type": "number", "datasetId": 54, "agg": "sum" }
      ], "sortable": true }
    ]
  }
}
```

> Цвет блоков задаётся вычисляемым полем в оси «Значения»: поле типа `calculated` с `alias` в виде HEX-цвета в обратных кавычках (`` `7EC576` `` или `` `#669966` ``) красит все блоки, а SQL-выражение `CASE … THEN ` … ` ELSE NULL END` — окрашивает отдельные блоки по условию (`NULL` означает «оставить цвет по умолчанию»). Если поле цвета и серия не заданы — используется палитра отчёта.

> Точность чисел (`treemap.precision`) не входит в базовый конфиг при добавлении: ключ `precision` появляется при настройке и задаётся через `config_overrides`.

Каждый ключ внутри `config` соответствует строке в таблице ниже. Колонка **JSON-путь** показывает, где значение хранится в конфиге. Для вложенных параметров используется запись `объект.раздел.ключ` (например, `labels.value.fontsize` — это ключ `fontsize` внутри `labels.value`). Пустой путь означает верхний уровень `config`.

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
| — | `labels.valuesFontSize` | `labels.value.fontsize` | int | `12` | только этот тип |
| — | `labels.valuesTopMargin` | `labels.value.topMargin` | int | `5` | только этот тип |
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
| Отступ Низ | `margin.b` | `(margin.b)` | int | `0` |  |
| Отступ Лево | `margin.l` | `(margin.l)` | int | `15` |  |
| Внутренний отступ | `margin.pad` | `(margin.pad)` | int | `0` |  |
| Отступ Право | `margin.r` | `(margin.r)` | int | `15` |  |
| Отступ Верх | `margin.t` | `(margin.t)` | int | `15` |  |

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
| Подзаголовок | `subtitle` | `(subtitle)` | str | `` | только этот тип |
| Точность чисел | `treemap.precision` | `precision` | int | `-1` | только этот тип |

### Режим фильтра

| UI-контрол | MCP-слаг | JSON-путь | Тип | По умолчанию | Прим. |
|---|---|---|---|---|---|
| enable (checkbox) | `treemap.filterMode` | `filterMode` | bool | `False` | только этот тип |

<!-- AUTO-TABLE:END -->

## Связанные

- [Каталог компонентов](../README.md)
- [Концепция: JSON-конфиг и слаги](../../concepts/components-json-slugs.md)
- [Справочник настроек (слаги)](../slugs/by-type.md)
- [Рецепты подготовки данных](../data-recipes.md)
- [Стилизация компонентов](../styling.md)
- [Фильтры и каскады](../filter-patterns.md)
- [Солнечные лучи (Sunburst)](sunburst.md)
- [Столбчатая диаграмма](bar-chart.md)
- [Круговая диаграмма](pie-chart.md)
