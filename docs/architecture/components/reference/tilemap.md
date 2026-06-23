# Плиточная карта

Тип компонента: `HsTilemapChart`

## Описание

Плиточная карта показывает регионы России в виде равных прямоугольных или шестиугольных плиток: одна плитка — один субъект РФ. Цвет плитки кодирует числовой показатель по непрерывной шкале (от начального цвета к конечному), а на самой плитке выводится её код и до двух числовых значений. Плитки группируются по федеральным округам с цветной обводкой групп.

В отличие от географической карты, плиточная карта не использует координаты и реальные контуры территорий — у всех регионов одинаковый размер, поэтому мелкие субъекты не теряются, а крупные не доминируют. Это делает её удобной для честного сравнения показателей между регионами. Привязка к территории выполняется по названию региона (текстовое поле категорий), а не по геокодам.

## Когда применять

- Сравнение показателя между всеми субъектами РФ, когда важна равная заметность каждого региона.
- Сводка «одно-два числа на регион»: значение и, при необходимости, дельта/второй показатель.
- Группировка регионов по федеральным округам с цветовой обводкой.
- Просмотр динамики показателя по годам через ось «Тренд».
- Дашборды, где не нужна точная география (контуры, координаты).

## Когда не подходит

- Нужны реальные контуры территорий, координаты или произвольные регионы (страны, города, районы) — используйте геокарту.
- Территории — не субъекты РФ: плиточная сетка фиксирована под регионы России.
- Больше двух числовых метрик на регион — на плитке помещается максимум два значения.
- Иерархические данные (вложенные категории) — используйте treemap или «солнечные лучи».

## Поля и оси

Компонент использует поля четырёх осей:

- **Категории** — текстовое поле с названиями регионов. **Обязательная ось.** Значения должны совпадать с эталонными названиями регионов в системе, иначе плитка не находит соответствия и остаётся без данных. Агрегация для категорий не применяется.
- **Значения** — числовое поле, задающее цвет плитки и выводимое на ней число. Поддерживается **до двух полей** (слот 0 и слот 1) — два числа на одной плитке. Для значений агрегация обязательна.
- **Тренд** (необязательно) — поле временного разреза, обычно «Год» (число). При заполнении появляется переключатель, позволяющий смотреть данные в динамике. Внимание: в плиточной карте ось временного разреза называется именно **«Тренд»**, а не «Серии», как в других компонентах.
- **Фильтры** — локальные фильтры компонента.

> **Параметр `series_field` для плиточной карты не работает.** При добавлении он применяется только к многосерийным графикам (bar/line/area/stock) и для `HsTilemapChart` игнорируется (с предупреждением). Чтобы заполнить ось «Тренд», добавьте поле года напрямую — через интерфейс или через `config.axes[series].fields` в JSON.

### Привязка к территории

Плиточная карта привязывается к регионам **по названию**, а не по геоключам: вызывать `map_set_geokeys` для неё не нужно (этот метод относится к географической карте). Достаточно положить в ось категорий поле с эталонными названиями регионов (например, `Москва`, `Санкт-Петербург`, `Московская область`). Иные написания или аббревиатуры приведут к пустым плиткам. Если плитки массово остаются серыми (без данных) — значения в поле категорий не совпадают с эталонными названиями субъектов РФ.

### Правила агрегации

Агрегация управляет тем, как несколько строк датасета сводятся к одному значению плитки:

- **Сырой датасет, нужна сумма по региону** — `aggregation="sum"`.
- **Среднее по региону** — `aggregation="avg"` (аналогично `min`, `max`, `count`).
- **Предагрегированный датасет** (значения уже посчитаны в SQL) — передавайте агрегацию явно (например, `aggregation="max"`): на готовой группе она вернёт то же единственное значение, но без агрегации поле значений считается неготовым и плитки выходят без цвета.

Если поле значений осталось без агрегации, карта обычно выходит без заливки.

## Параметры добавления

Помимо привязки к датасету и полям, при добавлении компонента доступны параметры:

| Параметр | Назначение |
|----------|-----------|
| `x`, `y`, `w`, `h` | Позиция и размер компонента в сетке отчёта |
| `category_field` | Поле с названиями регионов (ось «Категории») |
| `value_field` | Числовое поле — цвет и значение плитки (до двух полей через запятую) |
| `aggregation` | Агрегация значений (`sum`, `avg`, `min`, `max`, `count`) |
| `config_overrides` | Тонкая настройка через слаги (форма плиток, шкала, группировка — см. «Все настройки») |

## Формат данных

Подойдёт обычная таблица «регион + числовая метрика», где регион записан эталонным названием субъекта РФ. Минимально требуются ось **Категории** (названия регионов) и ось **Значения** (числовой показатель) — без них компонент не отрисуется. Для двух чисел на плитке добавьте второе числовое поле в ось значений. Для динамики по годам добавьте числовое поле года в ось «Тренд» — карта построит переключатель периодов.

## Пример

Базовая плиточная карта — один показатель по регионам:

```python
component_crud(
    action="add",
    report_id=35,
    component_type="HsTilemapChart",
    title="Показатель по регионам",
    dataset_id=54,
    category_field="region",
    value_field="indicator",
    aggregation="sum",
    x=0, y=0, w=24, h=16,
)
```

Шестиугольные плитки, зелёно-красная шкала, маркеры-звёздочки для городов федерального значения — задаётся через `config_overrides`:

```python
component_crud(
    action="add",
    report_id=35,
    component_type="HsTilemapChart",
    title="Выручка по регионам",
    dataset_id=54,
    category_field="region",
    value_field="revenue",
    aggregation="sum",
    config_overrides={
        "tilemap.tileType": "hex",
        "tilemap.startColor": "#4CAF50",
        "tilemap.endColor": "#F44336",
        "tilemap.specialTiles": True,
        "tilemap.grouping": True,
        "tilemap.deltaK": 0.2,
        "tilemap.legendX": "left",
        "tilemap.legendY": "top",
    },
)
```

Динамика по годам — поле года выносится на ось «Тренд». Параметр `series_field` для плиточной карты не применяется (см. раздел «Поля и оси»), поэтому ось «Тренд» заполняют напрямую — через интерфейс или записью поля года в `config.axes[series].fields` при обновлении конфигурации компонента:

```jsonc
// ось series внутри config.axes
{ "name": "series", "type": "series", "title": "Тренд", "fields": [
    { "name": "year", "alias": "Год", "type": "number", "datasetId": 54 }
]}
```

В примерах выше `config_overrides` показан в синтаксисе Python (`True`/`False`). В JSON-конфигурации те же значения записываются как `true`/`false`.

Здесь `component_crud` — это RPC-метод MCP-сервера (вызов инструмента), а не REST-эндпоинт; `component_idx` в других действиях — 0-based индекс компонента в отчёте.

## JSON-конфигурация

Сервер собирает и хранит конфигурацию компонента в JSON. Ниже — аннотированная структура плиточной карты: рядом с каждым ключом указано, что он задаёт и каким слагом управляется (полное соответствие — в таблице «Все настройки»). Часть слагов `tilemap.*` пишется в верхнеуровневые ключи (`scale.*`, `tiles.*`), часть — во вложенные пути (`grouping.*`, `legend.*`, `popupEnabled`).

```jsonc
{
  "type": "HsTilemapChart",                     // тип компонента (его отдаёт component_crud action="types_list")
  "config": {
    "title": "Показатель по регионам",          // заголовок компонента
    "chartType": "tilemapChart",                // внутренний тип (фиксирован)
    "showtitle": true,                          // показывать заголовок            ← слаг showtitle
    "bgColor": "rgba(255, 255, 255, 1)",        // цвет фона компонента            ← слаг bgColor
    "margin":  { "l": 0, "r": 0, "t": 0, "b": 0, "pad": 0 },       // отступы      ← слаги margin.l/r/t/b/pad
    "outline": { "enabled": false, "width": 4 },                   // рамка        ← слаги outline.enabled/width
    "scale": {                                  // цветовая шкала плиток
      "startColor": "blue",                     //   цвет минимального значения    ← слаг tilemap.startColor
      "endColor": "red"                         //   цвет максимального значения    ← слаг tilemap.endColor
    },
    "tiles": {                                  // форма и подписи плиток
      "type": "square",                         //   форма: square | hex            ← слаг tilemap.tileType
      "nameFontSize": "normal",                 //   шрифт кода региона              ← слаг tilemap.nameFontSize
      "specialTiles": false                     //   звёздочки для городов фед. знач.← слаг tilemap.specialTiles
    },
    "grouping": {                               // группировка по федеральным округам
      "enabled": true,                          //   обводка групп ФО               ← слаг tilemap.grouping
      "deltaK": 0.15                            //   зазор между группами (0..0.5)   ← слаг tilemap.deltaK
    },
    "legend": {                                 // легенда цветовой шкалы
      "visible": true,                          //   показывать                     ← слаг tilemap.legendVisible
      "positionX": "right",                     //   по горизонтали: left | right    ← слаг tilemap.legendX
      "positionY": "bottom"                     //   по вертикали: top | bottom       ← слаг tilemap.legendY
    },
    "autoZoom": true,                           // авто-масштаб под контейнер        ← слаг tilemap.autoZoom
    "tileSize": 40,                             // базовый размер плитки в px; при autoZoom=true служит основой для расчёта масштаба ← слаг tilemap.tileSize
    "popupEnabled": false,                      // popup при наведении на плитку      ← слаг tilemap.popup
    "axes": [                                   // оси данных (поля привязываются параметрами при добавлении)
      { "name": "filters",    "type": "filters",    "title": "Фильтры",   "fields": [] },          // локальные фильтры
      { "name": "categories", "type": "categories", "title": "Категории", "fields": [               // ось регионов ← category_field
          { "name": "region", "alias": "Регион", "type": "string", "datasetId": 54 }
      ]},
      { "name": "series",     "type": "series",     "title": "Тренд",     "fields": [] },           // ось «Тренд» ← series_field
      { "name": "values",     "type": "values",     "title": "Значения",  "fields": [               // ось значений ← value_field + aggregation
          { "name": "indicator", "alias": "Показатель", "type": "number", "agg": "sum", "datasetId": 54 }
          // у поля значений может стоять "hideResult": true — поле участвует
          // в расчётах (например, дельты тренда), но не выводится на плитке
      ], "sortable": true }
    ]
  }
}
```

> Скрытые от пользователя режимы — фоновые плитки без данных (слаг `tilemap.allowTiles`, ключ `background.allowTiles`), цвет таких плиток (`tilemap.bgTileColor` → `background.backgroundColor`) и режим выделения регионов (`tilemap.filterMode`) — настраиваются теми же слагами `config_overrides`. Полный перечень — в таблице ниже.

### Числовые слоты в `tiles.*`

Когда на плитке выводятся два значения, их форматирование задаётся пер-слотно. В объектах `tiles.fontSize`, `tiles.precision`, `tiles.maxLength` ключ — это **числовой индекс слота**, а не `field.id`: `"0"` — первое поле в `values.fields`, `"1"` — второе.

```jsonc
{
  "tiles": {
    "fontSize":  { "0": "normal", "1": "smaller" },  // шрифт значения по слоту
    "precision": { "0": 0, "1": 2 }                  // знаков после запятой по слоту
  }
}
```

Использовать в этих ключах `field.id` вместо индекса слота (`{ "indicator_id_123": "normal" }`) — частая ошибка: форматирование не применится.

Каждый ключ внутри `config` соответствует строке в таблице ниже. Колонка **JSON-путь** показывает, где значение хранится в конфиге. Для вложенных параметров используется запись `объект.ключ` (например, `grouping.enabled`). Пустой путь означает верхний уровень `config`.

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

- [Словарь терминов](../../../GLOSSARY.md)
- [Каталог компонентов](../README.md)
- [Географическая карта (Leaflet)](map.md)
- [Древовидная карта (TreeMap)](treemap.md)
- [Солнечные лучи (Sunburst)](sunburst.md)
- [Концепция: JSON-конфиг и слаги](../../concepts/components-json-slugs.md)
- [Справочник настроек (слаги)](../slugs/by-type.md)
- [Рецепты подготовки данных](../data-recipes.md)
- [Стилизация компонентов](../styling.md)
- [Фильтры и каскады](../filter-patterns.md)
