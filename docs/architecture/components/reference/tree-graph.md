# Граф-дерево

Тип компонента: `HsTreeGraph`

> Основные термины — см. [Словарь терминов](../../../GLOSSARY.md) (identity, linkage, config_overrides, слаг).

## Описание

Граф-дерево визуализирует иерархические и сетевые структуры: каждый узел — это одна строка датасета, а связи между узлами строятся по паре полей «идентификатор узла» и «идентификатор родителя». Подходит для оргструктур, дерева территорий, деревьев решений и любых parent-child связей.

Компонент поддерживает два режима раскладки: иерархическое дерево (корень и ветви) и силовой (force-directed) граф для сетевых структур без строгой иерархии. Узлы можно интерактивно сворачивать и разворачивать, перетаскивать и масштабировать.

## Когда применять

- Оргструктуры: компания → дирекции → отделы → группы.
- Иерархии территорий: страна → округа → регионы → районы.
- Деревья решений и классификации.
- Parent-child связи между сущностями (каталоги, рубрикаторы, BOM-структуры).
- Сетевые структуры без строгой иерархии — в режиме силового графа.

## Когда не подходит

- Один узел имеет несколько родителей (направленный граф со множеством связей) — модель дерева хранит ровно одного родителя на узел.
- Очень большие сети (сотни и тысячи узлов) — раскладка замедляется; ограничьте выборку фильтрами.
- Простое сравнение величин или доли целого — берите столбчатую или круговую диаграмму.
- Иерархия с числовой метрикой на каждом уровне как площадь — рассмотрите [Солнечные лучи](sunburst.md).

## Поля и оси

У графа-дерева три смысловые оси плюс ось фильтров. Привязка полей при добавлении нестандартная — её важно запомнить:

- **Идентификатор узла** (ось `identity`, «Признак») — ровно одно поле, уникальный ключ узла. Задаётся параметром `category_field`. Идентификатор **должен быть числовым**: фронтенд ищет корень по числовому сравнению, и строковый ключ нарушит поиск корня и раскладку дерева. В датасете формируйте числовой id — через `ROW_NUMBER()` или существующий числовой столбец.
- **Идентификатор родителя** (ось `linkage`, «Связь») — ровно одно поле, ссылка на `identity` родителя. Задаётся **первым** значением в `value_field`. Корень дерева (верхний узел без родителя):
  - рекомендуется — `parent_id IS NULL` (для числовых ключей);
  - альтернатива — `identity = linkage`, то есть узел ссылается сам на себя (для строковых ключей, **не рекомендуется**).
- **Значения** (ось `values`, «Значения») — метки, цвет и размер узлов. Это **все поля `value_field` начиная со второго**. Каждое поле играет роль по своему типу: метка узла, цвет узла (HEX из данных) или размер узла.
- **Фильтры** (ось `filters`) — поля для связи с глобальными фильтрами отчёта.

Цвет узла из данных передаётся HEX-строкой (`5294de` или `#5294de`) и имеет приоритет над цветом по умолчанию; его удобно вычислять условием (CASE) в SQL датасета. Размер узла задаётся числовым полем.

Агрегация для графа-дерева не применяется: компонент ожидает плоский parent-child набор строк без `GROUP BY`. Все поля сохраняются с пустой агрегацией автоматически.

## Параметры добавления

Помимо привязки к датасету и полям, при добавлении доступны параметры:

| Параметр | Назначение |
|----------|-----------|
| `x`, `y`, `w`, `h` | Позиция и размер компонента в сетке отчёта |
| `category_field` | Поле идентификатора узла (ось `identity`) — числовое |
| `value_field` | Список полей: первое → родитель (`linkage`), остальные → значения (метка/цвет/размер) |
| `config_overrides` | Слаги оформления и режима графа (`graph.layout`, `graph.zoomable`, `graph.initialZoom` и общие) |

## Формат данных

Нужен плоский parent-child набор: по строке на узел, числовой идентификатор узла и ссылка на родителя. Дополнительные колонки (название, цвет, размер) идут в значения.

| id (узел) | parent_id (родитель) | name (метка) | color (цвет) |
|-----------|----------------------|--------------|--------------|
| 1 | `NULL` | Корень | `5294de` |
| 2 | 1 | Узел 1 | `5294de` |
| 3 | 1 | Узел 2 | `e53935` |
| 4 | 2 | Лист 1 | `8bc34a` |

Пример SQL датасета с числовым id, меткой и цветом по уровню:

```sql
SELECT
    t.id                          AS id,          -- идентификатор узла (identity)
    t.parent_id                   AS parent_id,   -- родитель (linkage), NULL у корня
    t.name                        AS name,        -- метка узла
    CASE
        WHEN t.level = 1 THEN '5294de'            -- цвет узла, HEX без #
        WHEN t.level = 2 THEN 'e53935'
        ELSE '909090'
    END                           AS color
FROM tree_table t
ORDER BY t.level, t.parent_id NULLS FIRST, t.id;  -- NULLS FIRST: PostgreSQL/Oracle
-- Для MySQL: ORDER BY CASE WHEN t.parent_id IS NULL THEN 0 ELSE 1 END, t.level, t.parent_id, t.id;
```

## Пример

Минимальное дерево: узел + родитель + метка. Значения `report_id` и `dataset_id` ниже — примеры, подставьте свои.

```python
component_crud(
    action="add",
    report_id=<report_id>,
    component_type="HsTreeGraph",
    title="Иерархия регионов",
    dataset_id=<dataset_id>,
    category_field="id",                 # → identity (числовой ключ узла)
    value_field="parent_id,name",        # parent_id → linkage, name → метка узла
    x=0, y=0, w=24, h=16,
)
```

Дерево с цветом узлов из данных и горизонтальной раскладкой:

```python
component_crud(
    action="add",
    report_id=<report_id>,
    component_type="HsTreeGraph",
    title="Организационная структура",
    dataset_id=<dataset_id>,
    category_field="id",
    value_field="parent_id,dept_name,dept_color",   # dept_color — HEX-цвет узла
    x=0, y=16, w=48, h=16,
    config_overrides={
        "graph.zoomable": True,
        "balloon.visible": True,
    },
)
```

Силовой граф для сетевых связей (без строгой иерархии) — переключается слагом `graph.layout`:

```python
component_crud(
    action="add",
    report_id=<report_id>,
    component_type="HsTreeGraph",
    title="Граф зависимостей",
    dataset_id=<dataset_id>,
    category_field="service_id",
    value_field="depends_on,service_name",
    x=0, y=0, w=48, h=16,
    config_overrides={
        "graph.layout": "ForceDirectedLayout",
        "graph.zoomable": True,
        "graph.initialZoom": 0.8,
    },
)
```

Здесь `component_crud` — это RPC-метод MCP-сервера (вызов инструмента), а не REST-эндпоинт; `component_idx` в других действиях — 0-based индекс компонента в отчёте. Если идентификатор узла строковый, сервер вернёт предупреждение: приведите ключ к числовому виду.

## JSON-конфигурация

Сервер собирает и хранит конфигурацию компонента в JSON. Ниже — аннотированная структура графа-дерева: рядом с каждым ключом указано, что он задаёт и каким слагом управляется (полное соответствие — в таблице «Все настройки»).

```jsonc
{
  "type": "HsTreeGraph",                          // тип компонента (его отдаёт component_crud action="types_list")
  "config": {
    "title": "Иерархия регионов",                 // заголовок компонента
    "chartType": "treeGraph",                     // внутренний тип (фиксирован)
    "visualType": "tree",                         // визуальный тип (фиксирован)
    "layout": "TreeLayout",                       // раскладка: дерево | силовой граф  ← слаг graph.layout
    "model": {                                    // модель графа (фиксирована)
      "class": "go.TreeModel",                    //   движок графов: один родитель на узел
      "nodeKeyProperty": "identity",              //   ключ узла берётся из оси identity
      "nodeParentKeyProperty": "linkage"          //   ключ родителя берётся из оси linkage
    },
    "showtitle": true,                            // показывать заголовок            ← слаг showtitle
    "zoomable": true,                             // вписывать весь граф в контейнер ← слаг graph.zoomable
    "initialZoom": 0.7,                           // начальный масштаб при zoomable=false ← слаг graph.initialZoom
    "bgColor": "rgba(255, 255, 255, 1)",          // цвет фона                       ← слаг bgColor
    "margin":  { "l": 0, "r": 0, "t": 0, "b": 0, "pad": 0 },   // отступы            ← слаги margin.l/r/t/b/pad
    "outline": { "enabled": false, "width": 4 },               // рамка              ← слаги outline.enabled/width
    "balloon": {                                  // всплывающая подсказка на узле
      "visible": false,                           //   показывать                    ← слаг balloon.visible
      "fontsize": 12                              //   размер шрифта                  ← слаг balloon.fontSize
    },
    "axes": [                                     // оси данных (поля привязываются параметрами при добавлении)
      { "name": "filters",  "type": "filters",  "fields": [] },               // фильтры компонента
      { "name": "identity", "type": "identity", "fields": [                    // идентификатор узла ← category_field
          { "name": "id", "alias": "id", "type": "number", "agg": null }
      ]},
      { "name": "linkage",  "type": "linkage",  "fields": [                    // идентификатор родителя ← 1-е value_field
          { "name": "parent_id", "alias": "parent_id", "type": "number", "agg": null }
      ]},
      { "name": "values",   "type": "values",   "fields": [                    // метки/цвет/размер ← остальные value_field
          { "name": "name", "alias": "name", "type": "string", "agg": null }
      ]}
    ]
  }
}
```

> Раскладку, масштаб и автовписывание задают слаги `graph.layout`, `graph.initialZoom` и `graph.zoomable` через `config_overrides`. Все поля графа-дерева сохраняются с `agg: null` — агрегация для этого типа не применяется.

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
| вкл | `balloon.visible` | `(balloon.visible)` | bool | `False` |  |

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
| Начальный масштаб | `graph.initialZoom` | `(initialZoom)` | float | `0.7` | только этот тип |
| Тип графа | `graph.layout` | `(layout)` | enum | `TreeLayout` | только этот тип |
| Автомасштабирование | `graph.zoomable` | `(zoomable)` | bool | `True` | только этот тип |
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
- [Солнечные лучи (иерархия)](sunburst.md)
