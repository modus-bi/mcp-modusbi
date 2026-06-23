"""
MCP Prompts for ModusBI.

Prompts are user-driven templates that provide structured instructions for LLM.
Unlike Tools (which LLM calls automatically), Prompts are explicitly selected by users.

Available Prompts:
 1. create_dashboard      - Step-by-step dashboard creation (+ customization)
 2. style_report          - Report CSS styling + presets
 3. query_data            - Build dataset queries (+ variables)
 4. export_report         - Export report to PDF/PNG/PPTX
 5. analyze_dataset       - Analyze dataset structure
 6. customize_component   - Visual customization via slugs / presets / overrides
 7. add_filters           - Add interactive filters + cascades
 8. add_conditional_formatting - Table/pivot conditional formatting rules
 9. manage_variables      - Report variables & categories CRUD
10. create_report_from_template - Create report from template (6 templates)
"""

from typing import Any


def get_prompts() -> list[dict[str, Any]]:
    """Return list of all available prompts for registration."""
    return [
        {
            "name": "create_dashboard",
            "description": "Пошаговое создание дашборда с выбором датасета, компонентов и стилизацией",
            "arguments": [
                {
                    "name": "dataset_name",
                    "description": "Название датасета (опционально)",
                    "required": False
                },
                {
                    "name": "report_name",
                    "description": "Название отчёта",
                    "required": False
                }
            ]
        },
        {
            "name": "style_report",
            "description": "Стилизация отчёта: CSS + presets (minimal, presentation, dashboard, dark, print, kpi)",
            "arguments": [
                {
                    "name": "report_id",
                    "description": "ID отчёта для стилизации",
                    "required": True
                },
                {
                    "name": "style_type",
                    "description": "Тип стилизации: colors, headers, tables, charts",
                    "required": False
                }
            ]
        },
        {
            "name": "query_data",
            "description": "Построение запроса к датасету с фильтрами, агрегацией и переменными",
            "arguments": [
                {
                    "name": "dataset_id",
                    "description": "ID датасета",
                    "required": True
                },
                {
                    "name": "question",
                    "description": "Вопрос на естественном языке",
                    "required": False
                }
            ]
        },
        {
            "name": "export_report",
            "description": "Экспорт отчёта в PDF, PNG или PPTX",
            "arguments": [
                {
                    "name": "report_id",
                    "description": "ID отчёта для экспорта",
                    "required": True
                },
                {
                    "name": "format",
                    "description": "Формат: pdf, png, pptx",
                    "required": False
                }
            ]
        },
        {
            "name": "analyze_dataset",
            "description": "Анализ структуры датасета: поля, типы, рекомендации по визуализации",
            "arguments": [
                {
                    "name": "dataset_id",
                    "description": "ID датасета для анализа",
                    "required": True
                }
            ]
        },
        {
            "name": "customize_component",
            "description": "Визуальная настройка компонента: slug-параметры, 6 presets, config_overrides",
            "arguments": [
                {
                    "name": "report_id",
                    "description": "ID отчёта",
                    "required": True
                },
                {
                    "name": "component_idx",
                    "description": "Индекс компонента в отчёте",
                    "required": True
                },
                {
                    "name": "preset",
                    "description": "Быстрый пресет: minimal, presentation, dashboard, dark, print, kpi",
                    "required": False
                }
            ]
        },
        {
            "name": "add_filters",
            "description": "Добавление интерактивных фильтров, каскадных зависимостей и globalCategories",
            "arguments": [
                {
                    "name": "report_id",
                    "description": "ID отчёта",
                    "required": True
                },
                {
                    "name": "component_idx",
                    "description": "Индекс FilterControlPanel компонента (опционально)",
                    "required": False
                }
            ]
        },
        {
            "name": "add_conditional_formatting",
            "description": "Условное форматирование для таблиц и сводных таблиц (цвет, индикаторы, правила)",
            "arguments": [
                {
                    "name": "report_id",
                    "description": "ID отчёта",
                    "required": True
                },
                {
                    "name": "component_idx",
                    "description": "Индекс table или pivotChart компонента",
                    "required": True
                }
            ]
        },
        {
            "name": "manage_variables",
            "description": "Управление переменными отчёта (globalVariables) и категориями (globalCategories)",
            "arguments": [
                {
                    "name": "report_id",
                    "description": "ID отчёта",
                    "required": True
                }
            ]
        },
        {
            "name": "create_report_from_template",
            "description": "Создать отчёт по шаблону — KPI Dashboard, Ranking, Comparison, Simple Report и другие",
            "arguments": [
                {
                    "name": "template",
                    "description": "Название шаблона: kpi_dashboard | ranking | comparison | simple | geo_analytics | factor_analysis",
                    "required": True
                },
                {
                    "name": "dataset_id",
                    "description": "ID датасета для компонентов",
                    "required": True
                },
                {
                    "name": "report_name",
                    "description": "Название нового отчёта (опционально)",
                    "required": False
                },
                {
                    "name": "group_id",
                    "description": "ID группы для отчёта (опционально)",
                    "required": False
                }
            ]
        },
    ]


# =============================================================================
# Prompt message generators
# =============================================================================

def create_dashboard_prompt(
    dataset_name: str | None = None,
    report_name: str | None = None
) -> list[dict]:
    """Generate messages for create_dashboard prompt."""
    context = ""
    if dataset_name:
        context += f"\nИспользуй датасет: {dataset_name}"
    if report_name:
        context += f"\nНазови отчёт: {report_name}"

    return [
        {
            "role": "user",
            "content": {
                "type": "text",
                "text": f"""Помоги создать дашборд. Выполни следующие шаги:

1. Покажи список доступных датасетов (dataset_operations action="list")
2. После выбора датасета покажи его поля (dataset_operations action="fields_list")
3. Покажи список групп отчётов (report_operations action="groups_list")
4. Создай новый отчёт в выбранной группе (report_operations action="create")
5. Покажи типы компонентов (component_crud action="types_list")

## Справочник типов компонентов (27 типов)

### Графики (Charts)
- **HsBarAMchartsChart** — Столбчатая | category_field + value_field, orientation, stacking | Рейтинги, сравнения
- **HsLineAMchartsChart** — Линейная | category_field + value_field | Тренды, динамика
- **HsAreaAMchartsChart** — Площадная (с заливкой) | category_field + value_field, stacking | Тренды с объёмом, накопления
- **HsPieAMchartsChart** — Круговая | category_field + value_field | Доли/структура (до 8 сегментов)
- **HsRadarAMchartsChart** — Радарная (паутина) | category_field + value_field | Профили, многомерное сравнение (5-12 осей)
- **HsBubbleAMchartsChart** — Пузырьковая | 2 value_field + size_field | 3D-сравнение (X, Y, размер)
- **HsSpeedometerV2AMcharts** — Стрелочный индикатор | value_field (1 метрика), grid config | KPI со шкалой, план/факт
- **HsSunburstChart** — Солнечные лучи | category_field (иерархия) + value_field | Иерархическая структура с drill-down
- **HsParallelCoordsChart** — Параллельные координаты | value_field (несколько числовых) | Многомерный анализ объектов

### Таблицы
- **HsTableReactabularChart** — Таблица | value_field (через запятую), aggregation="none" | Детальные данные
- **HsPivotChart** — Сводная | row_fields, column_fields, value_field | Перекрёстный анализ (строки×столбцы)
- **HsComparisonChart** — Таблица сравнения | category_field=объект(string), column_fields=показатель(string), value_field=значение(number) | Сравнение 2 объектов с дельтой. ВАЖНО: нужен UNPIVOT-датасет (объект|показатель|значение)

### Карты
- **HsMapLeafletChart** — Карта Leaflet | value_field, затем map_set_geokeys | Геоданные (bubble/choropleth)
- **HsTilemapChart** — Плиточная карта РФ | category_field (регион) + value_field | Показатели по субъектам РФ
- **HsTreeMap** — Treemap | category_field + value_field | Иерархия с площадью ∝ значению

### KPI
- **HsTotalsPanelV2** — KPI-карточка | value_field, aggregation, preset="kpi" | Ключевая метрика крупным шрифтом

### Фильтры
- **HsFilterControlPanel** — Dropdown-фильтр | value_field + dataset_id | Интерактивная фильтрация
- **HsHierarchicalFilterPanel** — Иерархический фильтр | поля на оси filters по уровням | Зависимые уровни (округ→регион→город)
- **HsSwitchControlPanel** — Переключатель разрезов | управляет globalCategories | Смена группировки на всех графиках

### Навигация
- **HsPageContainer** — Вкладки внутри отчёта | page_add для страниц | Разбиение на табы
- **HsTabsPanel** — Навигация между отчётами | кнопки-ссылки | Меню верхнего уровня

### Контент
- **HsSubheaderComponent** — Заголовок | title (без данных) | Разделение секций
- **HsTextBlock** — Текстовый HTML | text_content | Описания, выводы
- **HsTreeGraph** — Граф GoJS | identity + linkage поля | Оргструктуры, деревья
- **HsIframe** — Встроенная страница | URL | Внешние виджеты, видео
- **HsImagePanel** — Изображение | URL или base64 | Логотипы, иллюстрации
- **HsAudioplayer** — Плеер аудио | value_field (аудио URL) | Речевая аналитика (нишевый)

6. **ВАЖНО: Настрой русские alias на датасете ПЕРЕД добавлением компонентов!**
   Бэкенд запрещает менять alias полей после привязки к компонентам.
   dataset_operations(action="update", dataset_id=<ID>, field_aliases={{"region": {{"alias": "Регион"}}, ...}})

   ### Особые паттерны для специальных типов компонентов

   **ComparisonChart (HsComparisonChart) — Сравнение двух объектов:**
   Требует UNPIVOT-датасет с 3 полями: объект (string), показатель (string), значение (number).
   ```
   SQL UNPIVOT: SELECT region, metric_name, metric_value FROM (
     SELECT region, 'Кол-во продаж' as metric_name, COUNT(*)::NUMERIC as metric_value FROM ... GROUP BY region
     UNION ALL
     SELECT region, 'Сумма' as metric_name, SUM(amount)::NUMERIC as metric_value FROM ... GROUP BY region
   ) t
   ```
   Создание: component_crud(action="add", component_type="HsComparisonChart",
     category_field="region", column_fields="metric_name", value_field="metric_value", aggregation="sum")
   Потом: config_overrides={{"comparison.object1": "Объект А", "comparison.object2": "Объект Б"}}

   **TreeGraph (HsTreeGraph) — Граф связей:**
   Требует числовые ID (frontend делает Number(identity)). Датасет: id (integer), parent_id, label, measure.
   category_field="id" (identity), value_field="parent_id,label,measure" (linkage + values), aggregation="" (без группировки)

7. Добавь компоненты по моему выбору (component_crud action="add")
8. Настрой расположение компонентов (component_crud action="layout_update")
9. Предложи визуальную настройку:
   - Покажи доступные presets (component_crud action="list_presets")
   - Или покажи slugs для типа компонента (component_crud action="list_slugs")
   - Примени выбранный стиль (component_crud action="update" preset="..." или config_overrides={{...}})
10. При необходимости добавь фильтры:
   - Создай FilterControlPanel: component_crud action="add" component_type="HsFilterControlPanel"
   - Добавь поле фильтра: component_filters action="filter_field_add" value_field="region" alias="Регион" field_type="string" dataset_id=DS
   - ⚠️ **КРИТИЧНО**: filter_field_add нужно вызвать на КАЖДОМ data-компоненте (графики, таблицы, KPI, карты), не только на FilterControlPanel!
     Без этого глобальный фильтр создаётся, но data-компоненты НЕ реагируют на выбор.
   - ВСЕГДА передавай: field_type="string" (иначе слайдер вместо dropdown), alias="Русское название", dataset_id
{context}
Начни с показа списка датасетов."""
            }
        }
    ]


def style_report_prompt(
    report_id: int,
    style_type: str | None = None
) -> list[dict]:
    """Generate messages for style_report prompt."""
    style_hint = ""
    if style_type:
        style_hint = f"\nСфокусируйся на стилизации: {style_type}"

    return [
        {
            "role": "user",
            "content": {
                "type": "text",
                "text": f"""Помоги стилизовать отчёт ID={report_id}. Есть два уровня стилизации:

**Уровень 1: CSS (глобально на весь отчёт)**
1. Получи текущие стили (style_operations action="get" report_id={report_id})
2. Покажи доступные CSS классы (style_operations action="classes_list")
3. Покажи примеры стилизации (style_operations action="examples_list")
4. Предложи улучшения и примени (style_operations action="update")

**Уровень 2: Presets и slugs (на отдельные компоненты)**
5. Получи список компонентов (report_operations action="components_list" report_id={report_id})
6. Для каждого компонента можно:
   - Применить preset: component_crud action="update" preset="presentation"
     Доступные presets: minimal, presentation, dashboard, dark, print, kpi
   - Или точечно через slugs: component_crud action="update" config_overrides={{"legend.visible": true, "bgColor": "#f5f5f5"}}
   - Посмотреть доступные slugs: component_crud action="list_slugs" component_type="barChart"
{style_hint}
Начни с получения текущих стилей."""
            }
        }
    ]


def query_data_prompt(
    dataset_id: int,
    question: str | None = None
) -> list[dict]:
    """Generate messages for query_data prompt."""
    question_text = ""
    if question:
        question_text = f"\n\nМой вопрос: {question}"

    return [
        {
            "role": "user",
            "content": {
                "type": "text",
                "text": f"""Помоги построить запрос к датасету ID={dataset_id}.

1. Получи информацию о датасете (dataset_operations action="get" dataset_id={dataset_id})
2. Покажи поля датасета с типами (dataset_operations action="fields_list")
3. Проверь есть ли переменные отчёта, которые можно использовать в запросе
   (report_operations action="variables_list" — если работаем в контексте отчёта)
4. На основе полей предложи варианты запросов:
   - Простой запрос всех данных
   - Агрегированный запрос с группировкой
   - Запрос с фильтрацией
   - Параметризованный запрос с variables
5. После моего выбора выполни запрос (dataset_query, можно передать variables={{}})
{question_text}
Начни с получения информации о датасете."""
            }
        }
    ]


def export_report_prompt(
    report_id: int,
    format: str | None = None
) -> list[dict]:
    """Generate messages for export_report prompt."""
    format_text = format or "pdf"

    return [
        {
            "role": "user",
            "content": {
                "type": "text",
                "text": f"""Экспортируй отчёт ID={report_id} в формат {format_text.upper()}.

1. Проверь что отчёт существует (report_operations action="get" report_id={report_id})
2. Покажи конфигурацию экспорта (report_operations action="export_info")
3. Выполни экспорт (report_operations action="export" format="{format_text}")
4. Покажи путь к файлу

Начни с проверки отчёта."""
            }
        }
    ]


def analyze_dataset_prompt(
    dataset_id: int
) -> list[dict]:
    """Generate messages for analyze_dataset prompt."""
    return [
        {
            "role": "user",
            "content": {
                "type": "text",
                "text": f"""Проанализируй датасет ID={dataset_id}.

1. Получи метаданные датасета (dataset_operations action="get" dataset_id={dataset_id})
2. Получи список полей с типами (dataset_operations action="fields_list")
3. Выполни тестовый запрос для примера данных (dataset_query limit=5)
4. Проанализируй:
   - Какие поля числовые (подходят для агрегации: SUM, AVG, COUNT)
   - Какие поля категориальные (подходят для группировки и фильтрации)
   - Какие поля временные (подходят для трендов и drill-down по дате)
5. Предложи варианты визуализации:
   - Какие типы компонентов подойдут (component_crud action="types_list")
   - Подсказка: bar — рейтинги, line/area — тренды, pie — структура, radar — профили,
     bubble — 3D-сравнение, speedometer — KPI со шкалой, sunburst — иерархия,
     parallel — многомерный анализ, tilemap — регионы РФ, table — детали,
     pivot — перекрёстный анализ, comparison — сравнение 2 объектов,
     map — геоданные, treemap — иерархия площадью
   - Для каждого типа — рекомендуемые slugs (component_crud action="list_slugs")
   - Какие метрики можно рассчитать (включая calc fields)
   - Рекомендуемые фильтры и drill-down иерархии

Начни с получения метаданных датасета."""
            }
        }
    ]


# =============================================================================
# Additional prompt generators
# =============================================================================

def customize_component_prompt(
    report_id: int,
    component_idx: int,
    preset: str | None = None
) -> list[dict]:
    """Generate messages for customize_component prompt."""
    if preset:
        return [
            {
                "role": "user",
                "content": {
                    "type": "text",
                    "text": f"""Примени preset "{preset}" к компоненту {component_idx} отчёта {report_id}.

1. Получи текущую конфигурацию компонента (component_crud action="get" report_id={report_id} component_idx={component_idx})
2. Примени preset (component_crud action="update" report_id={report_id} component_idx={component_idx} preset="{preset}")
3. Покажи что изменилось

Доступные presets: minimal, presentation, dashboard, dark, print, kpi"""
                }
            }
        ]

    return [
        {
            "role": "user",
            "content": {
                "type": "text",
                "text": f"""Помоги настроить визуальное оформление компонента {component_idx} в отчёте {report_id}.

Есть 3 уровня визуальной настройки:

**Уровень 1 — Атомарные параметры** (быстро):
component_crud action="update" legend_visible=true legend_position="bottom" bg_color="#f5f5f5"

**Уровень 2 — Config overrides через slugs** (точечно):
component_crud action="update" config_overrides={{"legend.visible": true, "axes.categoryTitle": true, "margin.t": 20}}
Имена слагов точные — сверяй через list_slugs (не выдумывай вроде "axes.category.title"/"margin.top").
Текст заголовка оси задаётся alias-ом поля датасета, НЕ слагом.
Для просмотра доступных slugs: component_crud action="list_slugs" component_type="..."
Чтобы получить UI-название и секцию панели у каждого слага: slug_category="ui:<секция>" (напр. "ui:legend").

**Уровень 3 — Presets** (быстрая тема):
component_crud action="update" preset="presentation"
Доступные presets: component_crud action="list_presets"

Выполни шаги:
1. Получи текущую конфигурацию (component_crud action="get" report_id={report_id} component_idx={component_idx})
2. Определи тип компонента
3. Покажи доступные slugs для этого типа (component_crud action="list_slugs")
4. Покажи доступные presets (component_crud action="list_presets")
5. Предложи варианты настройки на основе типа компонента
6. После моего выбора примени настройки

Начни с получения конфигурации компонента."""
            }
        }
    ]


def add_filters_prompt(
    report_id: int,
    component_idx: int | None = None
) -> list[dict]:
    """Generate messages for add_filters prompt."""
    component_hint = ""
    if component_idx is not None:
        component_hint = f"\nИспользуй FilterControlPanel: component_idx={component_idx}"

    return [
        {
            "role": "user",
            "content": {
                "type": "text",
                "text": f"""Помоги добавить интерактивные фильтры в отчёт ID={report_id}.

Фильтры в ModusBI работают через:
- **FilterControlPanel** — визуальный компонент-фильтр (dropdown/multiselect)
- **filter axis** — каждый компонент может иметь свои поля фильтрации
- **globalCategories** — категории привязанные к отчёту (report_operations)
- **cascade (filterBy)** — зависимые фильтры (город зависит от региона)

## Два паттерна размещения фильтров

### Паттерн A: Раздельные фильтры (РЕКОМЕНДУЕТСЯ для production)
Каждый фильтр — **отдельный HsFilterControlPanel** с 1 полем.
Располагаются горизонтально в одной строке (типовой паттерн production-дашбордов).
- Профессиональный внешний вид
- Горизонтальная раскладка
- Индивидуальная рамка и стиль

Пример (3 фильтра, grid 48 col):
```
component_crud(action="add", component_type="HsFilterControlPanel",
  title="Фильтры", value_field="region", dataset_id=<DS>, x=0, y=0, w=16, h=3)
component_crud(action="add", component_type="HsFilterControlPanel",
  title="Фильтры", value_field="category", dataset_id=<DS>, x=16, y=0, w=16, h=3)
component_crud(action="add", component_type="HsFilterControlPanel",
  title="Фильтры", value_field="severity", dataset_id=<DS>, x=32, y=0, w=16, h=3)
```

Стилизация каждого:
```
component_crud(action="update", component_idx=<N>,
  config_overrides={{"outline.enabled": true, "outline.width": 1,
    "outline.color": "rgba(179,179,179,1)", "bgColor": "rgba(255,255,255,1)",
    "margin.l": 5, "margin.r": 5, "margin.t": 0, "margin.b": 0}})
```

HD breakpoint (60 cols, 5 фильтров):
  Filter 1: x=0,  y=0, w=12, h=3
  Filter 2: x=12, y=0, w=12, h=3
  Filter 3: x=24, y=0, w=12, h=3
  Filter 4: x=36, y=0, w=12, h=3
  Filter 5: x=48, y=0, w=12, h=3

### Паттерн B: Единый фильтр (для простых отчётов)
Один HsFilterControlPanel с несколькими полями (вертикальная раскладка).

## Шаги

1. Покажи компоненты отчёта (report_operations action="components_list" report_id={report_id})
2. Определи количество фильтров:
   - 4+ фильтров → **Паттерн A** (раздельные)
   - 1-3 фильтра → **Паттерн B** (единый) или A по желанию
3. Создай FilterControlPanel:
   - Паттерн A: по 1 компоненту на фильтр (см. выше)
   - Паттерн B: component_crud action="add" component_type="HsFilterControlPanel" title="Фильтры" report_id={report_id}
4. Добавь поля фильтров: component_filters action="filter_field_add" value_field="region" alias="Регион" field_type="string" dataset_id=DS
   ⚠️ **ОБЯЗАТЕЛЬНЫЕ параметры**: field_type="string" (без него — слайдер!), alias (русское название), dataset_id
5. ⚠️ **КРИТИЧНО**: Добавь те же filter fields на КАЖДЫЙ data-компонент (графики, таблицы, KPI, карты):
   component_filters action="filter_field_add" report_id=R component_idx=<КАЖДЫЙ data-компонент> value_field="region" alias="Регион" field_type="string" dataset_id=DS
   Без этого глобальный фильтр создаётся, но data-компоненты НЕ реагируют на выбор.
6. При необходимости настрой каскадные зависимости.
   ⚠️ `alias` и `depends_on` принимают **финальный alias фильтра**, который был сохранён в globalFilters (русский, если поле в датасете имеет русский alias). Если филльтр-поле было добавлено с `alias=None`, MCP подставит alias из dataset, а не name. Проверь через `component_filters(action="filter_fields_list", report_id=R, component_idx=I)` и используй точное значение alias.
   component_filters action="filter_set_cascade" alias="Город" depends_on="Регион"
7. Стилизуй раздельные фильтры (outline + bgColor) — см. Паттерн A

## Альтернативные типы фильтрации

- **HsHierarchicalFilterPanel** — иерархический фильтр с зависимыми уровнями.
  Поля на оси filters определяют иерархию (первое = верхний уровень).
  Пример: ФО → Регион → Город. Выбор на верхнем уровне фильтрует нижние.

- **HsSwitchControlPanel** — переключатель разрезов аналитики.
  Меняет поле группировки (globalCategories) для всех графиков одновременно.
  Не фильтрует данные, а переключает измерение (напр. Регион / Продукт / Месяц).
{component_hint}
Начни с просмотра компонентов отчёта."""
            }
        }
    ]


def add_conditional_formatting_prompt(
    report_id: int,
    component_idx: int
) -> list[dict]:
    """Generate messages for add_conditional_formatting prompt."""
    return [
        {
            "role": "user",
            "content": {
                "type": "text",
                "text": f"""Помоги настроить условное форматирование для компонента {component_idx} в отчёте {report_id}.

Условное форматирование работает для table и pivotChart через config.rules[].

Каждое правило (rule) содержит:
- **name** — название правила
- **fieldId** — поле для проверки условия
- **cons** — условия: {{"0": {{"operator": ">=", "value": 100}}, "1": {{"operator": null, "value": null}}}}
  Операторы: >=, <=, >, <, =
- **color** — цвет текста (hex)
- **background** — цвет фона (hex)
- **wholeRow** — применять ко всей строке (bool)
- **indicatorType** — иконка: null, "up", "down", "dot", "up2", "down2", "dot2"
- **indicatorColor** — цвет иконки
- **isTextBold**, **isTextItalic**, **isTextUnderline** — стиль текста

Выполни шаги:

1. Получи конфигурацию компонента (component_crud action="get" report_id={report_id} component_idx={component_idx})
2. Проверь что это table или pivotChart
3. Покажи текущие правила (rules) если есть
4. Покажи поля компонента для выбора
5. Помоги составить правило, например:
   - Выделять красным ячейки где значение < 0
   - Выделять зелёным где значение > 1000
   - Добавить стрелку ↑ для роста, ↓ для падения
6. Примени правило через config_overrides:
   component_crud action="update" config_overrides={{
     "rules.0.name": "Отрицательные значения",
     "rules.0.fieldId": "revenue",
     "rules.0.cons.operator": "<",
     "rules.0.cons.value": 0,
     "rules.0.color": "#ffffff",
     "rules.0.background": "#f44336",
     "rules.0.wholeRow": true
   }}

Начни с получения конфигурации компонента."""
            }
        }
    ]


_VALID_TEMPLATES = frozenset({
    "kpi_dashboard", "ranking", "comparison", "simple", "geo_analytics", "factor_analysis",
})


def create_report_from_template_prompt(
    template: str,
    dataset_id: int,
    report_name: str | None = None,
    group_id: int | None = None,
) -> list[dict]:
    """Generate messages for create_report_from_template prompt."""
    if template not in _VALID_TEMPLATES:
        return [{"role": "user", "content": {"type": "text",
                "text": f"Неизвестный шаблон: {template}. Допустимые: {', '.join(sorted(_VALID_TEMPLATES))}"}}]
    name_hint = f' с названием "{report_name}"' if report_name else ""
    group_hint = f" в группу {group_id}" if group_id else ""

    templates_info = """
## Доступные шаблоны (grid 48 cols)

### kpi_dashboard — KPI Dashboard (4-6 KPI + графики + таблица)
Компоненты: HsPageContainer (табы) + 4× HsTotalsPanelV2 (KPI) + HsBarAMchartsChart + HsMapLeafletChart + HsTableReactabularChart
Layout (48 cols): Табы w=48 h=3 → KPI 4×(w=12 h=3) → Bar w=48 h=7 → Map w=24 h=8 + Table w=24 h=8
Стиль «BI-эталон» (всё data-bound, НЕ статический HTML): значение — native HsTotalsPanelV2 + слаги
visuals.value.font.size/color, subtitle; иконка-кружок — report-CSS `#panel_<idx> .titleText::before`
с Material Icons-лигатурой (FontAwesome нет; эмодзи = tofu); спарклайн — отдельный HsLineAMchartsChart
с axes.categoryLabels/valueLabels=false. Раскладка 5/ряд: hd w12, lg задавать отдельно w9 (иначе «лесенка»).

### ranking — Рейтинг (Bar + Treemap + Table)
Компоненты: HsSubheaderComponent + HsBarAMchartsChart (horizontal) + HsTreeMap + HsTableReactabularChart + 2× HsBarAMchartsChart
Layout (48 cols): Subheader w=48 h=3 → Bar w=24 h=7 + Treemap w=24 h=7 → Table w=48 h=8 → 2× Bar w=24 h=6

### comparison — Сравнение (KPI + Stacked Bar + Pie + Text)
Компоненты: 4× HsTotalsPanelV2 + HsBarAMchartsChart (stacked) + HsPieAMchartsChart + HsTextBlock + HsTableReactabularChart
Layout (48 cols): KPI 4×(w=12 h=3) → Bar w=24 h=7 + Pie w=24 h=7 → Text w=48 h=3 → Table w=48 h=8

### simple — Простой отчёт (Filter + Chart + Table)
Компоненты: FilterControlPanel + HsBarAMchartsChart + HsTableReactabularChart
Layout (48 cols): Filter w=48 h=3 → Bar w=48 h=10 → Table w=48 h=14

### geo_analytics — Гео-аналитика (Filter + KPI + Map + Table)
Компоненты: FilterControlPanel + 3× HsTotalsPanelV2 + HsMapLeafletChart + HsTableReactabularChart
Layout (48 cols): Filter w=48 h=3 → KPI 3×(w=16 h=3) → Map w=48 h=10 → Table w=48 h=8
**ВАЖНО:** После scaffold карты, вызови map_set_geokeys для геопривязки:
- Bubble (круги на координатах): config_overrides={{"latfield": "lat", "lonfield": "lng"}}
- Choropleth (раскраска полигонов): config_overrides={{"geo_type": "file.geojson.json", "geofield": "NAME"}}
Датасет должен содержать поля lat/lng для bubble-режима.

### factor_analysis — Факторный анализ (KPI + Bar + Table)
Компоненты: 3× HsTotalsPanelV2 + HsBarAMchartsChart + HsTableReactabularChart
Layout (48 cols): KPI 3×(w=16 h=3) → Bar w=48 h=8 → Table w=48 h=8
"""

    return [
        {
            "role": "user",
            "content": {
                "type": "text",
                "text": f"""Создай отчёт по шаблону **{template}**{name_hint}{group_hint}.
Используй dataset_id={dataset_id}.

{templates_info}

## Пошаговая инструкция

1. **Получи поля датасета:**
   dataset_operations(action="fields_list", dataset_id={dataset_id})

2. **Создай отчёт:**
   report_operations(action="create", name="{report_name or f'Отчёт {template}'}", group_id={group_id or 1})

3. **Добавь компоненты по шаблону {template}** — используй batch_operations(action="components_add") для добавления всех компонентов за 1 вызов:
   batch_operations(
     action="components_add",
     report_id=<new_report_id>,
     components=[
       {{"component_type": "...", "title": "...", "dataset_id": {dataset_id},
         "value_field": "<поле из датасета>", "category_field": "<поле категории>",
         "x": 0, "y": 0, "w": 12, "h": 2, "preset": "dashboard"}},
       ...
     ]
   )

4. **Настрой фильтры** (если шаблон предусматривает):
   - На FilterControlPanel: component_filters(action="filter_field_add", report_id=R, component_idx=FILTER_IDX, value_field="region", alias="Регион", field_type="string", dataset_id=DS)
   - ⚠️ **На КАЖДОМ data-компоненте** (графики, таблицы, KPI, карты) — тот же filter_field_add с тем же alias и field_type="string"!
     Без этого глобальный фильтр создаётся, но компоненты НЕ реагируют.
   - ОБЯЗАТЕЛЬНЫЕ параметры: field_type="string" (иначе слайдер!), alias (русское!), dataset_id

5. **Покажи результат:**
   Предоставь ссылку на отчёт и ASCII-превью layout.

**ВАЖНО:**
- Выбирай поля для value_field и category_field из реальных полей датасета (шаг 1)
- Для KPI выбирай числовые поля с бизнес-смыслом (revenue, count, amount)
- Для category выбирай строковые поля (region, category, name)
- Для таблиц используй aggregation="none"
- Используй preset="dashboard" для графиков, preset="kpi" для KPI
- **Фильтры**: для production-quality используй раздельные FilterControlPanel (1 поле = 1 компонент, горизонтально).
  Стилизуй каждый: outline.enabled=true, outline.width=1, outline.color="rgba(179,179,179,1)", bgColor="rgba(255,255,255,1)"
- ⚠️ **field_aliases (русские названия полей) ОБЯЗАТЕЛЬНО задавать ДО добавления компонентов!**
  Бэкенд запрещает менять alias полей после привязки к компонентам (HTTP 400).
  Сразу после создания датасета:
  dataset_operations(action="update", dataset_id=<ID>, field_aliases={{"region": {{"alias": "Регион"}}, "amount": {{"alias": "Сумма"}}}})
  Только потом добавлять компоненты.

Начни с получения полей датасета."""
            }
        }
    ]


def manage_variables_prompt(
    report_id: int
) -> list[dict]:
    """Generate messages for manage_variables prompt."""
    return [
        {
            "role": "user",
            "content": {
                "type": "text",
                "text": f"""Помоги управлять переменными и категориями отчёта ID={report_id}.

**Переменные (globalVariables)** — параметры отчёта, доступные компонентам:
- Используются в dataset_query через variables={{...}}
- Позволяют параметризовать запросы

**Категории (globalCategories)** — привязаны к globalFilters:
- Определяют какие фильтры доступны на уровне отчёта
- Связаны с FilterControlPanel компонентами

Выполни шаги:

1. Покажи текущие переменные (report_operations action="variables_list" report_id={report_id})
2. Покажи текущие категории (report_operations action="categories_list" report_id={report_id})
3. Предложи варианты:
   - Добавить переменную: report_operations action="variable_add"
   - Обновить переменную: report_operations action="variable_update"
   - Удалить переменную: report_operations action="variable_delete"
   - Добавить категорию: report_operations action="category_add"
   - Обновить категорию: report_operations action="category_update"
   - Удалить категорию: report_operations action="category_delete"
4. После изменений покажи настройки отчёта (report_operations action="get_options")

Начни с показа текущих переменных и категорий."""
            }
        }
    ]


# =============================================================================
# Prompt dispatcher
# =============================================================================

def get_prompt_messages(name: str, arguments: dict | None = None) -> list[dict]:
    """
    Get messages for a prompt by name.

    Args:
        name: Prompt name
        arguments: Prompt arguments

    Returns:
        List of messages for the prompt
    """
    args = arguments or {}

    def _require(key: str) -> list[dict] | None:
        if not args.get(key):
            return [{"role": "user", "content": {"type": "text", "text": f"Ошибка: требуется {key}"}}]
        return None

    match name:
        case "create_dashboard":
            return create_dashboard_prompt(
                dataset_name=args.get("dataset_name"),
                report_name=args.get("report_name")
            )
        case "style_report":
            if err := _require("report_id"):
                return err
            return style_report_prompt(
                report_id=int(args["report_id"]),
                style_type=args.get("style_type")
            )
        case "query_data":
            if err := _require("dataset_id"):
                return err
            return query_data_prompt(
                dataset_id=int(args["dataset_id"]),
                question=args.get("question")
            )
        case "export_report":
            if err := _require("report_id"):
                return err
            return export_report_prompt(
                report_id=int(args["report_id"]),
                format=args.get("format")
            )
        case "analyze_dataset":
            if err := _require("dataset_id"):
                return err
            return analyze_dataset_prompt(
                dataset_id=int(args["dataset_id"])
            )
        case "customize_component":
            if err := _require("report_id"):
                return err
            if err := _require("component_idx"):
                return err
            return customize_component_prompt(
                report_id=int(args["report_id"]),
                component_idx=int(args["component_idx"]),
                preset=args.get("preset")
            )
        case "add_filters":
            if err := _require("report_id"):
                return err
            cidx = args.get("component_idx")
            return add_filters_prompt(
                report_id=int(args["report_id"]),
                component_idx=int(cidx) if cidx else None
            )
        case "add_conditional_formatting":
            if err := _require("report_id"):
                return err
            if err := _require("component_idx"):
                return err
            return add_conditional_formatting_prompt(
                report_id=int(args["report_id"]),
                component_idx=int(args["component_idx"])
            )
        case "manage_variables":
            if err := _require("report_id"):
                return err
            return manage_variables_prompt(
                report_id=int(args["report_id"])
            )
        case "create_report_from_template":
            if err := _require("template"):
                return err
            if err := _require("dataset_id"):
                return err
            return create_report_from_template_prompt(
                template=args["template"],
                dataset_id=int(args["dataset_id"]),
                report_name=args.get("report_name"),
                group_id=int(args["group_id"]) if args.get("group_id") else None,
            )
        case _:
            return [{"role": "user", "content": {"type": "text", "text": f"Неизвестный prompt: {name}"}}]
