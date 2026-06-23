# Карта

Тип компонента: `HsMapLeafletChart`

## Описание

Карта отображает данные на интерактивной географической подложке. Числовые значения из [датасета](../../../GLOSSARY.md#датасет-dataset) привязываются к территориям или к точкам с координатами, и карта показывает их цветом (заливка территорий) либо размером кругов. Поверх тайловой подложки накладываются геоданные — полигоны территорий (страны, федеральные округа, регионы, районы) или маркеры-точки.

Компонент поддерживает два режима привязки данных:

- **Хороплет (choropleth)** — заливка полигонов из предзагруженных геоданных (GeoJSON — формат географических данных) по числовому показателю. Территории окрашиваются по градиенту или по дискретным диапазонам.
- **Точки (bubble)** — круги (пузыри) на координатах, взятых прямо из полей датасета (широта/долгота). Размер круга пропорционален значению.

Дополнительно карта умеет: иерархический drill-down по уровням территорий (округ → регион → район), режим фильтра (клик по территории фильтрует другие [компоненты](../../../GLOSSARY.md#компонент-component)), кластеризацию точек и совмещение нескольких слоёв на одной карте.

> Важно: геопривязка — двухшаговый процесс. Сначала добавьте компонент (`component_crud`), затем привяжите геоданные (`map_set_geokeys`). Без второго шага карта остаётся пустой — см. [Геопривязка: обязательный шаг](#геопривязка-обязательный-шаг-map_set_geokeys).

## Когда применять

- Данные с географической привязкой: показатели по странам, округам, регионам, районам.
- Сравнение территорий по числовому показателю через цветовую градацию (хороплет).
- Отметки объектов с координатами: магазины, точки происшествий, склады (режим точек).
- Drill-down по иерархии территорий с переходом на более мелкий уровень кликом.
- Карта как интерактивный фильтр дашборда (клик по территории фильтрует остальные компоненты).

## Когда не подходит

- У данных нет географической привязки — используйте столбчатую диаграмму или таблицу.
- Территорий мало (2–3) — проще показать столбчатой диаграммой.
- Нужна точная числовая детализация — дополните карту таблицей или KPI-панелью.
- Нужны произвольные GPS-точки без предзагруженных геослоёв — режим хороплета работает только с геоданными, загруженными на портал; для точек используйте режим bubble (координаты из данных).

## Поля и оси

Компонент использует три оси:

- **Категории** (`category_field`) — текстовое поле-ключ привязки. В режиме хороплета его значения должны совпадать с ключом в геоданных (название территории, аббревиатура, код). В режиме точек оно служит группировкой/подписью маркеров. Можно указать несколько полей в порядке от крупного к мелкому — это даёт иерархический drill-down. Агрегация для категорий не применяется.
- **Значения** (`value_field`) — числовое поле, задающее цвет территории или размер круга. Для значений агрегация обязательна. Допускаются вычисляемые поля (тип `calculated`, агрегация встроена в формулу). В режиме точек в значения передают также поля координат.
- **Фильтры** — поля фильтрации компонента; связаны с глобальными фильтрами отчёта по alias. Типично дублируют поля иерархии (округ → регион → район).

Оси серий у карты нет.

### Геопривязка: обязательный шаг `map_set_geokeys`

Карта, добавленная через `component_crud`, ещё не знает, к каким геоданным привязать категории — без привязки она не отрисуется (см. [Рендер-контракт](../../concepts/render-contract.md): отображение читает только заданные ключи конфига). Поэтому после добавления компонента обязателен вызов `component_styling(action="map_set_geokeys", ...)`:

- **Точки (bubble):** передайте поля координат — `config_overrides={"latfield": "lat", "lonfield": "lng"}`. Сервер проставляет служебный маркер `geodataId: -1`, и карта рисует круги в позициях из данных, без загрузки GeoJSON.
- **Хороплет (choropleth):** передайте имя файла геоданных и ключ привязки в нём — `config_overrides={"geo_type": "fo.geojson.json", "geofield": "NAME"}`. Значения поля категорий должны совпадать с этим ключом в геоданных.

Узнать, какие геоданные загружены на портал, можно через `component_styling(action="geodata_list")`; посмотреть текущую привязку — через `component_styling(action="map_get_geokeys", ...)`.

### Правила агрегации

Агрегация управляет тем, как несколько строк датасета сводятся к одному значению на территорию/точку:

- **Предагрегированный датасет** (значения уже посчитаны через `GROUP BY` в SQL) — передавайте агрегацию явно (например, `aggregation="max"`): без неё поле значений считается неготовым и карта выходит пустой.
- **Сырой датасет** (строки без `GROUP BY` в SQL), **сумма по территории** — `aggregation="sum"` (аналогично `avg`, `min`, `max`, `count`).
- Вычисляемое поле в значениях задаётся с `agg=null` — агрегация встроена в формулу.

## Параметры добавления

Помимо привязки к датасету и полям, при добавлении доступны параметры:

| Параметр | Назначение |
|----------|-----------|
| `x`, `y`, `w`, `h` | Позиция и размер компонента в сетке отчёта |
| `category_field` | Поле-ключ привязки к территории (или группировки точек) |
| `value_field` | Числовое поле для цвета/размера |
| `aggregation` | Агрегация значений (`sum`, `avg`, `min`, `max`, `count`) |
| `config_overrides` | Слаги оформления (`map.*`, легенда, маркеры, фон) |

Геопривязка задаётся отдельным шагом — `map_set_geokeys` (см. выше), а не параметром `component_crud`.

## Формат данных

- **Режим хороплета:** таблица «ключ территории + числовая метрика». Ключ должен совпадать с полем привязки в геоданных (название, аббревиатура, код).
- **Режим точек:** таблица с полями широты и долготы плюс метрика. Координаты должны быть числовыми (в SQL приводите строки к числу, например `lat::numeric`), иначе точки не отрисуются. Минимальный запрос: `SELECT city, incidents, lat::numeric AS lat, lon::numeric AS lon FROM incidents_by_city`.
- Для drill-down добавьте в категории несколько полей-уровней (округ, регион, район) от крупного к мелкому.

## Пример

Хороплет — заливка регионов по числу инцидентов (предагрегированный датасет):

```python
# 1. Добавить компонент карты
component_crud(
    action="add",
    report_id=35,
    component_type="HsMapLeafletChart",
    title="Инциденты по регионам",
    dataset_id=54,
    category_field="region",   # значения должны совпасть с ключом в геоданных
    value_field="amount",
    aggregation="sum",
    x=0, y=0, w=24, h=16,
)
# → component_idx="0"

# 2. Привязать геоданные (без этого карта не отрисуется)
component_styling(
    action="map_set_geokeys",
    report_id=35,
    component_idx=0,
    config_overrides={"geo_type": "regions_rf.geojson", "geofield": "NAME"},
)
```

Точки (bubble) — круги на координатах из датасета:

```python
component_crud(
    action="add",
    report_id=35,
    component_type="HsMapLeafletChart",
    title="Происшествия по координатам",
    dataset_id=54,
    category_field="region",   # подпись/группировка точек
    value_field="incidents",   # размер круга
    aggregation="sum",
    x=0, y=16, w=24, h=16,
)
component_styling(
    action="map_set_geokeys",
    report_id=35,
    component_idx=1,
    config_overrides={"latfield": "lat", "lonfield": "lng"},
)
```

Дискретная легенда и оформление маркеров через `config_overrides`:

```python
component_crud(
    action="update",
    report_id=35,
    component_idx=0,
    config_overrides={
        "map.legend.discrete": True,
        "map.legend.gradeNumber": 5,
        "map.markers.showValues": True,
        "map.markers.valuesPrecision": 0,   # точность значений: -1 = авто, 0 = целые, 2 = два знака
        "map.background.allowTiles": True,
    },
)
```

Здесь `component_crud` и `component_styling` — это RPC-методы MCP-сервера (вызовы инструментов), а не REST-эндпоинты; `component_idx` — 0-based индекс компонента в отчёте (первый компонент = 0, второй = 1, и т.д.).

## JSON-конфигурация

Сервер собирает и хранит конфигурацию компонента в JSON. Ниже — аннотированная структура карты: рядом с ключами указано, что они задают и каким слагом управляются (полное соответствие — в таблице «Все настройки»). Геопривязка (`geokeys`) добавляется отдельным шагом `map_set_geokeys` и здесь показана как комментарий.

```jsonc
{
  "type": "HsMapLeafletChart",                  // тип компонента (его отдаёт component_crud action="types_list")
  "config": {
    "title": "Инциденты по регионам",           // заголовок компонента
    "chartType": "mapLeaflet",                  // внутренний тип (фиксирован)
    "visualType": "map",                        // визуальное представление (фиксировано)
    "showtitle": true,                          // показывать заголовок            ← слаг showtitle
    "bgColor": "rgba(255, 255, 255, 1)",        // цвет фона компонента            ← слаг bgColor
    "margin":  { "l": 5, "r": 10, "t": 10, "b": 5, "pad": 0 },   // отступы        ← слаги margin.l/r/t/b/pad
    "outline": { "enabled": false, "width": 4 },                 // рамка          ← слаги outline.enabled/width
    "autoCenter": true,                         // авто-центровка по данным        ← слаг map.autoCenter
    "filterMode": false,                        // режим фильтра (клик фильтрует)  ← слаг map.filterMode
    "multilayerMode": false,                    // многослойный режим              ← слаг map.multilayerMode
    "legend": {                                 // легенда карты
      "visible": true,                          //   показывать                    ← слаг map.legend.visible
      "position": "bottomright",                //   угол: bottomright|topright|topleft|bottomleft ← слаг map.legend.position
      "discrete": false,                        //   дискретные диапазоны          ← слаг map.legend.discrete
      "gradeNumber": 5                          //   число диапазонов (discrete)   ← слаг map.legend.gradeNumber
    },
    "markers": {                                // подписи и точки
      "showLabels": true,                       //   подписи территорий            ← слаг map.markers.showLabels
      "showTooltip": true,                      //   подсказка при наведении       ← слаг map.markers.showTooltip
      "showValues": false,                      //   значения поверх территорий    ← слаг map.markers.showValues
      "clusterizationOff": true                 //   кластеризация точек (хранится инвертированным) ← слаг map.markers.clustering
    },
    "background": {                             // тайловая подложка
      "allowTiles": true                        //   фоновая карта вкл             ← слаг map.background.allowTiles
    },
    "axes": [                                   // оси данных (поля привязываются параметрами при добавлении)
      { "name": "filters",    "type": "filters",    "fields": [] },              // фильтры компонента
      { "name": "categories", "type": "categories", "fields": [                  // ключ привязки ← category_field
          { "name": "region", "alias": "Регион", "type": "string", "datasetId": 54 }
      ]},
      { "name": "values",     "type": "values",     "fields": [                  // цвет/размер   ← value_field + aggregation
          { "name": "amount", "alias": "Количество", "type": "number", "agg": "sum", "datasetId": 54 }
      ], "sortable": true }
    ]
    // "geokeys": { ... }                        // добавляется через map_set_geokeys; не задаётся вручную:
    //   choropleth: { "<id поля категории>": { "type": "regions_rf.geojson", "geofield": "NAME" } }
    //   bubble:     { "<id поля категории>": { "geodataId": -1, "latfield": "lat", "lonfield": "lng" } }
  }
}
```

> Слаги-«сироты» `map.initialZoom`, `map.clusterMarkers`, `map.center.lat`, `map.center.lng` помечены устаревшими: карта центрируется и масштабируется по данным (`autoCenter` и границам слоя), эти ключи отображение не читает.

> Часть слагов пишется в JSON-ключ с другим именем — см. колонку **JSON-путь** в таблице. Например, `map.markers.clustering` хранится как `markers.clusterizationOff` (значение инвертируется: `clustering=true` → `clusterizationOff=false`), а `map.markers.showMaxValue` пишется в `markers.maxValueShow`. Точность значений `map.markers.valuesPrecision` принимает `-1` = авто (по умолчанию), `0` = целые, `2` = два знака; диапазон `-1..10`.

Каждый ключ внутри `config` соответствует строке в таблице ниже. Колонка **JSON-путь** показывает, где значение хранится в конфиге. Для вложенных параметров используется запись `объект[раздел].ключ`. Пустой путь означает верхний уровень `config`.

> Таблица ниже сгенерирована автоматически из схемы слагов сервера. Если в ней найдена ошибка, её правят в `config_schema.py` и пересобирают документацию скриптом `scripts/gen_component_tables.py` — не в этом файле.

<!-- AUTO-TABLE:START (регенерируется scripts/gen_component_tables.py — правьте config_schema.py, не этот блок) -->

## Все настройки (config_overrides)

Полный перечень слагов этого типа — специфичные для типа и общие оформительские. Колонки: **UI-контрол** — название в панели настроек портала (пусто = прямого UI-контрола нет, настройка только через `config_overrides`); **MCP-слаг** — ключ в `config_overrides`; **JSON-путь** — куда настройка пишется в конфиг и откуда её читает отображение (это и есть «фронт-ключ»; путь в `(скобках)` обрабатывается секционно — итоговый ключ внутри указанной секции конфига); **Тип**; **По умолчанию**. Полный справочник по всем типам — [Справочник настроек](../slugs/by-type.md).

### Данные

| UI-контрол | MCP-слаг | JSON-путь | Тип | По умолчанию | Прим. |
|---|---|---|---|---|---|
| Анимация обновления | `hideSpinner` | `(hideSpinner)` | bool | `False` |  |

### Легенда

| UI-контрол | MCP-слаг | JSON-путь | Тип | По умолчанию | Прим. |
|---|---|---|---|---|---|
| Дискретные цвета | `map.legend.discrete` | `(legend.discrete)` | bool | `False` | только этот тип |
| Расположение | `map.legend.position` | `(legend.position)` | enum | `bottomright` | только этот тип |

### Подписи

| UI-контрол | MCP-слаг | JSON-путь | Тип | По умолчанию | Прим. |
|---|---|---|---|---|---|
| Кластеризация | `map.markers.clustering` | `markers.clusterizationOff` | bool | `False` | только этот тип |
| Показывать значения | `map.markers.showValues` | `(markers.showValues)` | bool | `False` | только этот тип |

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
| — | `fontSize` | `(fontSize)` | int | `12` |  |
| Градиент | `gradient` | _секционно_ | bool | `False` |  |
| Авто центровка | `map.autoCenter` | `(autoCenter)` | bool | `True` | только этот тип |
| Режим фильтра | `map.filterMode` | `(filterMode)` | bool | `False` | только этот тип |
| Многослойный режим | `map.multilayerMode` | `(multilayerMode)` | bool | `False` | только этот тип |
| Яркость заголовка | `map.titleBrightness` | `titleOpacity` | float | `0.8` | только этот тип |
| — | `nocopy` | `(nocopy)` | bool | `False` |  |
| — | `noexport` | `(noexport)` | bool | `False` |  |
| Заголовок | `showtitle` | `(showtitle)` | bool | `True` |  |

### Прочее

| UI-контрол | MCP-слаг | JSON-путь | Тип | По умолчанию | Прим. |
|---|---|---|---|---|---|
| — | `map.clusterMarkers` | `clusterMarkers` | bool | `False` | устар. |
| — | `map.initialZoom` | `initialZoom` | int | `5` | только этот тип |

### Карта

| UI-контрол | MCP-слаг | JSON-путь | Тип | По умолчанию | Прим. |
|---|---|---|---|---|---|
| — | `map.annotationText` | `annotation` | str | `` | только этот тип |
| — | `map.background.backgroundColor` | `(background.backgroundColor)` | color | `gray` | только этот тип |
| — | `map.background.tileUrl` | `(background.tileUrl)` | str | `{s}.tile.osm.org/{z}/{x}/{y}.png` | только этот тип |
| — | `map.center.lat` | `(center.lat)` | float | `55.751` | только этот тип |
| — | `map.center.lng` | `(center.lng)` | float | `37.618` | только этот тип |
| — | `map.legend.gradeNumber` | `(legend.gradeNumber)` | int | `5` | только этот тип |
| — | `map.legend.invertColors` | `(legend.invertColors)` | bool | `False` | только этот тип |
| — | `map.legend.visible` | `(legend.visible)` | bool | `True` | только этот тип |
| — | `map.legend.withFilters` | `(legend.withFilters)` | bool | `False` | только этот тип |
| — | `map.markers.clusteringThreshold` | `markers.clusterizationSize` | int | `50` | только этот тип |
| — | `map.markers.fixedExtent` | `(markers.fixedExtent)` | bool | `False` | только этот тип |
| — | `map.markers.gradeNumberForSize` | `(markers.gradeNumberForSize)` | int | `3` | только этот тип |
| — | `map.markers.isLinearScale` | `(markers.isLinearScale)` | bool | `False` | только этот тип |
| — | `map.markers.labelMinZoom` | `markers.minZoomLevel` | int | `0` | только этот тип |
| — | `map.markers.labelsSize` | `(markers.labelsSize)` | int | `12` | только этот тип |
| — | `map.markers.maxSize` | `(markers.maxSize)` | int | `50` | только этот тип |
| — | `map.markers.maxValue` | `(markers.maxValue)` | float | `100.0` | только этот тип |
| — | `map.markers.maxValueColor` | `(markers.maxValueColor)` | color | `red` | только этот тип |
| — | `map.markers.minSize` | `(markers.minSize)` | int | `0` | только этот тип |
| — | `map.markers.showLabels` | `(markers.showLabels)` | bool | `True` | только этот тип |
| — | `map.markers.showMaxValue` | `markers.maxValueShow` | bool | `False` | только этот тип |
| — | `map.markers.showTooltip` | `(markers.showTooltip)` | bool | `True` | только этот тип |
| — | `map.markers.tooltipSize` | `markers.tooltipTextSize` | int | `12` | только этот тип |
| — | `map.markers.tooltipWordWrap` | `markers.lineWrap` | bool | `False` | только этот тип |
| — | `map.markers.valuesPrecision` | `(markers.valuesPrecision)` | int | `-1` | только этот тип |
| — | `map.showSmallObjects` | `(showSmallObjects)` | bool | `False` | только этот тип |

### Описание

| UI-контрол | MCP-слаг | JSON-путь | Тип | По умолчанию | Прим. |
|---|---|---|---|---|---|
| Яркость аннотации | `map.annotationOpacity` | `annotationOpacity` | float | `0.8` | только этот тип |

### Фон

| UI-контрол | MCP-слаг | JSON-путь | Тип | По умолчанию | Прим. |
|---|---|---|---|---|---|
| Карта | `map.background.allowTiles` | `(background.allowTiles)` | bool | `True` | только этот тип |
| Железные дороги | `map.background.allowTiles2` | `(background.allowTiles2)` | bool | `False` | только этот тип |

<!-- AUTO-TABLE:END -->

## Связанные

- [Каталог компонентов](../README.md)
- [Концепция: JSON-конфиг и слаги](../../concepts/components-json-slugs.md)
- [Справочник настроек (слаги)](../slugs/by-type.md)
- [Рецепты подготовки данных](../data-recipes.md)
- [Стилизация компонентов](../styling.md)
- [Фильтры и каскады](../filter-patterns.md)
