# Панель фильтра

Тип компонента: `HsFilterControlPanel`

## Описание

Панель фильтра — это управляющий компонент дашборда, который выводит фильтры прямо в области отчёта (а не в боковой панели). Пользователь выбирает значения по списку, по диапазону или по периоду, и эти значения попадают в общие фильтры отчёта (`globalFilters`), влияя на все привязанные виджеты.

Один компонент содержит одно или несколько полей фильтрации на единственной оси `filters`. Ключ связи с общими фильтрами — `alias` поля: его значение становится ключом в `report.globalFilters`. Через этот alias панель синхронизируется с глобальным состоянием фильтров: несколько панелей с одинаковым alias управляют одним и тем же фильтром.

В отличие от диаграмм, у панели фильтра нет осей категорий/значений и агрегаций. Но датасет ей нужен: из него берутся доступные значения фильтра. Поле добавляется не параметрами `*_field` при создании, а отдельным вызовом `filter_field_add` (см. ниже).

## Когда применять

- Нужно показать ключевые фильтры (дата, регион, товар) прямо в шапке дашборда.
- Конечным пользователям удобнее управлять отбором кнопками, чекбоксами, слайдером или периодом, а не через боковую панель.
- Нужны каскадные (зависимые) фильтры: выбор в одном определяет доступные значения в другом.
- Нужна кнопка «Применить» для пакетного обновления данных после выбора нескольких значений.

## Когда не подходит

- Фильтрация нужна только одному виджету — добавьте поле на ось `filters` самого виджета (локальный фильтр), без отдельной панели.
- Фильтров очень много и они используются редко — практичнее боковая панель.
- Нужна древовидная иерархия значений — используйте иерархический фильтр (`HsHierarchicalFilterPanel`).
- Нужно переключать страницы/вкладки, а не отбирать данные — используйте панель вкладок (`HsTabsPanel`) или переключатель (`HsSwitchControlPanel`).

## Поля фильтра

Все поля размещаются на единственной оси `filters`. У каждого поля важны:

- **`alias`** — отображаемое название и одновременно ключ в `globalFilters`. Поля с одинаковым alias (в панели и на виджетах) образуют один общий фильтр.
- **`type`** — тип данных поля: `string`, `number` или `date`. От него зависят доступные режимы (диапазон/период для чисел и дат, список значений для строк).
- Агрегация для полей фильтра не применяется (всегда отсутствует).

Поле добавляется методом `component_filters(action="filter_field_add", ...)`. Этот же вызов автоматически создаёт запись в `globalFilters` по alias. Параметр `depends_on` задаёт каскадную зависимость от родительского фильтра (по его alias).

**Критично:** чтобы выбранное значение реально фильтровало данные, одно и то же поле нужно добавить через `filter_field_add` не только в саму панель, но и в КАЖДЫЙ фильтруемый data-компонент (график, таблицу, KPI, карту). Подробности, паттерны размещения (A — раздельные панели, B — единая панель с несколькими полями), каскады и обязательный CSS-фикс наложения выпадающих списков (z-index) — в [Фильтры и каскады](../filter-patterns.md).

### Тип отображения (viewType)

Визуальное представление фильтра задаётся слагом `viewType.displayType` (json-путь `filterType`). Базовые значения:

| Значение | Отображение | Особенности |
|----------|-------------|-------------|
| `dropdown` (по умолчанию) | Выпадающий список | Множественный выбор, инверсия, поиск, скрытие пустых строк. В конфиге `filterType: null` |
| `panel` | Чекбоксы | Все значения как чекбоксы; множественный выбор включается принудительно |
| `slider` | Слайдер | Полоса с ползунком для дискретных значений |
| `period` | Период | Date range picker; режим «по диапазону» для дат |
| `buttons` | Кнопки | Значения как кликабельные кнопки |
| `twofield` | По двум датам | Два отдельных поля ОТ/ДО; требует два поля на оси `filters` |

Дополнительно слаг принимает синонимы, которые нормализуются сервером в базовые значения: `list`, `radio`, `checkbox` → `panel`; `datepicker` → `period`. Значение `dropdown` пишется в конфиг как `filterType: null`.

## Параметры добавления

Сам компонент добавляется методом `component_crud(action="add")`. Поля фильтра — отдельными вызовами `filter_field_add`. При добавлении компонента доступны:

| Параметр | Назначение |
|----------|-----------|
| `x`, `y`, `w`, `h` | Позиция и размер панели в сетке отчёта |
| `dataset_id` | Набор данных — источник значений фильтра |
| `config_overrides` | Слаги оформления и поведения (`viewType.*`, `outline.*`, `bgColor`, `margin.*`) |

Параметры `filter_field_add` (метод `component_filters`):

| Параметр | Назначение |
|----------|-----------|
| `report_id`, `component_idx` | Отчёт и 0-based индекс компонента |
| `value_field` | Техническое имя поля в датасете (используется в SQL) |
| `alias` | Русское отображаемое имя; оно же — ключ в `globalFilters` |
| `field_type` | Тип данных поля: `string`, `number`, `date` |
| `dataset_id` | Датасет поля (передавайте явно) |
| `depends_on` | Alias родительского фильтра — создаёт каскадную зависимость |

## Пример

Добавление панели фильтра и привязка строкового поля «Регион», которое фильтрует и сам фильтр, и таблицу:

```python
# 1) добавить панель фильтра (датасет — источник значений)
component_crud(
    action="add",
    report_id=35,
    component_type="HsFilterControlPanel",
    title="Регион",
    dataset_id=54,
    x=0, y=0, w=20, h=3,
    config_overrides={
        "viewType.displayType": "dropdown",
        "viewType.multiselect": True,
        "outline.enabled": True,
        "outline.width": 1,
        "outline.color": "rgba(179,179,179,1)",
        "bgColor": "rgba(255,255,255,1)",
        "margin.l": 5,
        "margin.r": 5,
    },
)

# 2) поле в самой панели (component_idx — индекс панели в отчёте)
component_filters(
    action="filter_field_add",
    report_id=35,
    component_idx=0,
    value_field="region",
    alias="Регион",
    field_type="string",
    dataset_id=54,
)

# 3) то же поле на КАЖДОМ фильтруемом виджете (иначе данные не отфильтруются)
component_filters(
    action="filter_field_add",
    report_id=35,
    component_idx=1,           # таблица
    value_field="region",
    alias="Регион",
    field_type="string",
    dataset_id=54,
)
```

Каскад «Год → Дата»: дочернее поле зависит от родительского через `depends_on` (передаётся alias родителя):

```python
component_filters(
    action="filter_field_add",
    report_id=35,
    component_idx=2,           # вторая панель — дочерний фильтр
    value_field="order_date",
    alias="Дата",
    field_type="date",
    dataset_id=54,
    depends_on="Год",          # alias родительского фильтра
)
```

Здесь `component_crud` и `component_filters` — это RPC-методы MCP-сервера (вызовы инструментов), а не REST-эндпоинты; `component_idx` — 0-based индекс компонента в отчёте.

## JSON-конфигурация

Сервер собирает и хранит конфигурацию панели в JSON. Ниже — аннотированная структура: рядом с ключами указано, что они задают и каким слагом управляются (полное соответствие — в таблице «Все настройки»).

```jsonc
{
  "type": "HsFilterControlPanel",             // тип компонента
  "config": {
    "title": "Регион",                        // заголовок панели
    "chartType": "FilterControlPanel",        // внутренний тип (фиксирован)
    "showtitle": false,                       // показывать заголовок            ← слаг showtitle
    "autoApply": true,                         // применять выбор сразу (по умолч. true; read-only слаг) ← слаг viewType.autoApply
    "noexport": true,                          // не экспортировать (для этого типа по умолч. true) ← слаг noexport
    "nocopy": true,                            // запрет копирования              ← слаг nocopy
    "bgColor": "rgba(255, 255, 255, 1)",      // цвет фона                       ← слаг bgColor
    "margin":  { "l": 0, "r": 0, "t": 0, "b": 0, "pad": 0 },   // отступы        ← слаги margin.l/r/t/b/pad
    "outline": { "enabled": false, "width": 4 },               // рамка          ← слаги outline.enabled/width

    // --- поведение фильтра (слаги viewType.*) ---
    "filterType": null,                        // тип отображения: null = dropdown (по умолч.) ← слаг viewType.displayType
    "multipleChoice": true,                    // множественный выбор             ← слаг viewType.multiselect
    "updateOnApply": false,                    // обновлять только по «Применить» ← слаг viewType.updateOnApply
    "updateOnCloseDropdown": false,            // обновлять при закрытии списка   ← слаг viewType.updateOnCloseDropdown
    "searchInBaseMode": false,                 // поиск значений в базе           ← слаг viewType.searchEnabled
    "inversed": false,                         // инвертированный отбор (NOT IN)  ← слаг viewType.inversed
    "hideEmptyLines": false,                   // скрывать пустые строки          ← слаг viewType.hideEmptyLines
    "sortSelectedOptionsToTop": false,         // выбранные значения наверху      ← слаг viewType.sortSelectedOptionsToTop
    "addInversedFilter": false,                // кнопка-переключатель инверсии   ← слаг viewType.addInvertedSwitch
    "clearSelection": false,                   // кнопка очистки выбора           ← слаг viewType.clearSelection
    "unlimitedSearch": false,                  // поиск без лимита значений       ← слаг viewType.unlimitedSearch

    "axes": [                                  // единственная ось — filters
      {
        "name": "filters",
        "type": "filters",
        "title": "Фильтры",
        "selectedFieldIndex": 0,
        "fields": [                            // поля добавляются через filter_field_add
          {
            "name": "region",                  // техническое имя поля (SQL)
            "alias": "Регион",                 // ключ в report.globalFilters
            "type": "string",                  // тип данных: string|number|date
            "datasetId": 54,
            "agg": null,                        // у фильтров агрегации нет
            "global": true                      // поле панели всегда попадает в общие фильтры
          }
        ]
      }
    ]
  }
}
```

> Связь с общими фильтрами: `axes[filters].fields[].alias` совпадает с ключом в `report.globalFilters`. Например, поле с alias `"Регион"` управляет `globalFilters["Регион"]`. Состояние выбора (`selected`, `cons`, `filterMode`) хранится в `globalFilters`, а не в самом компоненте.

> Момент обновления данных задают записываемые слаги `viewType.updateOnApply` (обновлять только по кнопке «Применить», по умолч. `false`) и `viewType.updateOnCloseDropdown` (обновлять при закрытии списка, по умолч. `false`). Ключ `autoApply` (по умолч. `true`) отображение читает напрямую; через слаги он не переписывается (read-only) — режим обновления настраивайте слагами `updateOn*`.

Каждый ключ внутри `config` соответствует строке в таблице ниже. Колонка **JSON-путь** показывает, где значение хранится в конфиге; путь в `(скобках)` обрабатывается секционно.

> Таблица ниже сгенерирована автоматически из схемы слагов сервера. Если в ней найдена ошибка, её правят в `config_schema.py` и пересобирают документацию скриптом `scripts/gen_component_tables.py` — не в этом файле.

<!-- AUTO-TABLE:START (регенерируется scripts/gen_component_tables.py — правьте config_schema.py, не этот блок) -->

## Все настройки (config_overrides)

Полный перечень слагов этого типа — специфичные для типа и общие оформительские. Колонки: **UI-контрол** — название в панели настроек портала (пусто = прямого UI-контрола нет, настройка только через `config_overrides`); **MCP-слаг** — ключ в `config_overrides`; **JSON-путь** — куда настройка пишется в конфиг и откуда её читает отображение (это и есть «фронт-ключ»; путь в `(скобках)` обрабатывается секционно — итоговый ключ внутри указанной секции конфига); **Тип**; **По умолчанию**. Полный справочник по всем типам — [Справочник настроек](../slugs/by-type.md).

### Данные

| UI-контрол | MCP-слаг | JSON-путь | Тип | По умолчанию | Прим. |
|---|---|---|---|---|---|
| Анимация обновления | `hideSpinner` | `(hideSpinner)` | bool | `False` |  |

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
| — | `nocopy` | `(nocopy)` | bool | `True` |  |
| — | `noexport` | `(noexport)` | bool | `True` |  |
| Заголовок | `showtitle` | `(showtitle)` | bool | `False` |  |

### Тип фильтра

| UI-контрол | MCP-слаг | JSON-путь | Тип | По умолчанию | Прим. |
|---|---|---|---|---|---|
| — | `viewType.addInvertedSwitch` | `addInversedFilter` | bool | `False` | только этот тип |
| — | `viewType.autoApply` | `autoApply` | bool | `True` | только этот тип |
| — | `viewType.clearSelection` | `clearSelection` | bool | `False` | только этот тип |
| — | `viewType.displayType` | `filterType` | enum | `dropdown` | только этот тип |
| — | `viewType.hideEmptyLines` | `hideEmptyLines` | bool | `False` | только этот тип |
| — | `viewType.inversed` | `inversed` | bool | `False` | только этот тип |
| — | `viewType.multiselect` | `multipleChoice` | bool | `True` | только этот тип |
| — | `viewType.resetEnabled` | `resetEnabled` | bool | `False` | устар. |
| — | `viewType.searchEnabled` | `searchInBaseMode` | bool | `False` | только этот тип |
| — | `viewType.showAll` | `showAll` | bool | `False` | устар. |
| — | `viewType.sortSelectedOptionsToTop` | `sortSelectedOptionsToTop` | bool | `False` | только этот тип |
| — | `viewType.unlimitedSearch` | `unlimitedSearch` | bool | `False` | только этот тип |
| — | `viewType.updateOnApply` | `updateOnApply` | bool | `False` | только этот тип |
| — | `viewType.updateOnCloseDropdown` | `updateOnCloseDropdown` | bool | `False` | только этот тип |

<!-- AUTO-TABLE:END -->

## Связанные

- [Каталог компонентов](../README.md)
- [Концепция: JSON-конфиг и слаги](../../concepts/components-json-slugs.md)
- [Справочник настроек (слаги)](../slugs/by-type.md)
- [Фильтры и каскады](../filter-patterns.md)
- [Иерархический фильтр](hierarchical-filter.md)
