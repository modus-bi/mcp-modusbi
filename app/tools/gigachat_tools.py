"""Opt-in MCP tool catalogue for GigaChat and other compact-schema clients."""
from __future__ import annotations

import copy
from html import escape
from typing import Annotated, Literal
from mcp.types import ToolAnnotations
from pydantic import Field

from ..core.exceptions import APIError, NotFoundError, SecurityError, ValidationError
from ..core.security import check_action
from .gigachat_models import DashboardComponent, ChartComponent, TableColumn, CellRule, DatasetFilter, Metric, Placement, ValueFilter, NativeVisualization, VisualizationMetric
from .gigachat_profile import GigaChatProfile, WriteOutcomeError
from .schema_slim import slim_schema, strip_titles
from .gigachat_styles import STYLES

GIGACHAT_WORKFLOW = """Универсальный цикл построения отчёта Modus BI.
1. Найди источники, прочитай все поля, подписи, типы, единицы, описания и примеры. Обоснуй смысл выбранных полей по задаче и данным. Не выбирай денежное поле только по сходству типа или позиции.
2. До построения проверь расчёты через giga_query_dataset: суммы, зерно группировки, отношение сумм, нулевые знаменатели. Это независимый запрос к источнику, а не чтение уже построенного графика. Статистика sample не доказывает уникальность всего источника.
3. Сохраняй стабильные key. Названия графиков, карт, дерева, таблиц и KPI меняй через giga_rename_component: поля, фильтры и оформление сохраняются. Не заменяй график текстом. Добавляя столбцы, используй default merge: отсутствующие сохраняются. replace означает намеренное удаление остальных столбцов или смену вида/источника. Для настройки оформления используй узкие инструменты.
Для дерева предпочитай giga_set_tree, для Leaflet giga_set_map, для Tilemap giga_set_tilemap: передавай роли полей один раз, MCP сам добавит native-оси, сохранит типы и проверит географию. Общий фильтр создаётся отдельно через giga_bind_report_filter и сохраняется при обновлении компонентов. Стиль выбирай из giga_list_report_styles, применяй через giga_apply_dashboard_preset.
4. После изменений вызови giga_inspect_report: verification_plan автоматически содержит независимые запросы по реальным полям, зерну и формулам сохранённого отчёта. Выполни их реальными function calls giga_query_dataset, сопоставь возвращённые числа с data отчёта и требованиями пользователя. Затем реально выбери общий фильтр, перечитай отчёт, повтори запросы с тем же фильтром, сбрось выбор и перечитай. Код в тексте ответа не выполняется и не доказывает проверку; никогда не придумывай результаты функций. Проверки с truncated=true не завершены.
5. При ошибке исправляй конкретное поле/компонент и повторяй проверку. Перед завершением сверь весь накопленный список требований, включая предыдущие задания. checks_passed означает техническую согласованность, не правильность бизнес-смысла. Если данных недостаточно для выбора поля, явно назови неопределённость.
6. Визуальную приёмку в браузере подтверждай отдельно; сервер её не выполняет. Не передавай SQL, ключи моделей или ручные контракты отчёта.
7. Оформление: выбирай понятные подписи столбцов и метрик. Для native-размерностей и raw-осей используй field_labels=[{field,label}], сохраняя точные source fields. Избегай технических имён в заголовках; MCP сам выделяет больше места сводной, параллельным координатам и карте регионов.
8. Comparison по умолчанию indicator_mode=all сохраняет все показатели источника. Режим selected и indicator_values применяй только для явно требуемого ограниченного набора. Не оставляй один пробный показатель вместо полного отчёта. В giga_query_dataset всегда явно указывай metrics[].kind, особенно raw для исходных строк.
9. В числовых осях values/xvalues/yvalues диаграмм используй metrics с явным kind и точным field, не fields: агрегирование выбирай по задаче. Bubble требует все три числовые оси X/Y/размер. fields служат размерностям; raw values через fields допустимы для Tree/Parallel. Ошибку AXIS_METRICS_REQUIRED исправляй переносом того же поля в metrics, сохраняя остальные оси.
10. giga_query_dataset при смешении агрегатов и raw-полей вне group_by возвращает два явных блока: rows/columns — агрегаты, diagnostic_detail — raw-строки с ключами групп. Это разные независимые чтения, не связывай строки по позиции. Все поля сохраняются, SUM для raw автоматически не подставляется. При truncated=true хотя бы один блок неполон.
"""


def inline_schema(schema):
    """Remove local $refs and nullable unions from wire schema only."""
    root = copy.deepcopy(schema)

    def walk(node, path=()):
        if isinstance(node, list):
            return [walk(n, path) for n in node]
        if not isinstance(node, dict):
            return node
        if "$ref" in node:
            ref = node["$ref"]
            if not ref.startswith("#/") or ref in path:
                raise ValueError("Recursive/external schemas are not supported by this profile")
            target = root
            for part in ref[2:].split("/"):
                target = target[part]
            node = {**target, **{k: v for k, v in node.items() if k != "$ref"}}
            return walk(node, (*path, ref))
        result = {k: walk(v, path) for k, v in node.items() if k != "$defs"}
        if "const" in result:
            result["enum"] = [result.pop("const")]
        if "properties" in result:
            for name, prop in result["properties"].items():
                prop.setdefault("description", name)
        return result

    result = strip_titles(slim_schema(walk(root)))
    result.setdefault("description", "Параметры инструмента.")
    return result


def register_gigachat_tools(mcp, get_client):
    """Replace catalogue only when explicitly selected, preserving native logic."""
    if getattr(mcp, "_modus_tool_profile", "standard") == "gigachat":
        return
    original_names = tuple(mcp._tool_manager._tools)

    async def invoke(action, method, **kwargs):
        try:
            check_action(action)  # Before auth/client acquisition, including readonly.
            service = GigaChatProfile(await get_client())
            return await getattr(service, method)(**kwargs)
        except WriteOutcomeError as error:
            return {"success": False, "changed": error.changed, "commit_state": error.commit_state,
                    "configuration_verified": False, "error_code": "WRITE_NOT_VERIFIED", "error": str(error),
                    "hint": "Сначала giga_inspect_report. Не повторяйте запись вслепую."}
        except (ValueError, APIError, NotFoundError, ValidationError, SecurityError) as error:
            return {"success": False, "changed": False, "error": str(error),
                    "error_code": "SECURITY_MODE" if isinstance(error, SecurityError) else "INVALID_OR_FAILED_OPERATION",
                    "hint": "Исправьте указанные параметры. Не повторяйте неизменённый вызов. При неоднозначной ошибке записи сначала giga_inspect_report."}

    def annotation(title, readonly=False):
        return ToolAnnotations(title=title, readOnlyHint=readonly, destructiveHint=not readonly,
                               idempotentHint=True, openWorldHint=True)

    @mcp.tool(annotations=annotation("Найти существующие датасеты по имени", True))
    async def giga_find_datasets(names: Annotated[list[str], Field(min_length=1, max_length=20, description="Массив точных имён датасетов. Для трёх источников передайте три отдельных элемента массива.")],
                                 limit: Annotated[int, Field(ge=1, le=100, description="Лимит найденных источников.")] = 10) -> dict:
        """Найти ID источника по имени. Возвращает только имя/ID/подпись, без SQL и настроек подключения."""
        return await invoke("list", "find_many", names=names, limit=limit)

    @mcp.tool(annotations=annotation("Прочитать доступные группы отчётов", True))
    async def giga_list_report_groups() -> dict:
        """Получить существующие группы перед созданием отчёта. Никакие группы не создаются."""
        return await invoke("groups_list", "list_groups")

    @mcp.tool(annotations=annotation("Типы визуализаций портала и поддерживаемые оси", True))
    async def giga_list_visualizations() -> dict:
        """Полный каталог native-типов исходного MCP: доступность на портале, оси, минимумы полей и особенности. Сначала прочитайте каталог. KPI/обычная таблица/заголовок имеют отдельные короткие инструменты; для остальных типов используйте giga_set_visualization. Создание и данные не являются доказательством отрисовки."""
        return await invoke("get", "list_visualizations")

    @mcp.tool(annotations=annotation("Показать доступные BI-стили отчётов", True))
    async def giga_list_report_styles() -> dict:
        """Каталог адаптаций для BI: Чистый минимализм, Швейцарский, Современный корпоративный и Тёплый минимализм. Стиль меняет оформление, сохраняет поля/формулы/фильтры и смысловые цвета данных. Применять через giga_apply_dashboard_preset(style=...). Проверка CSS не доказывает красивое отображение: нужна отдельная браузерная приёмка."""
        check_action("get")
        return {"success":True,"items":[{"style":k,**v} for k,v in STYLES.items()]}

    @mcp.tool(annotations=annotation("Создать визуализацию через типизированные native-оси"))
    async def giga_set_visualization(report_id: Annotated[int, Field(gt=0, description="ID текущего отчёта.")], visualization: NativeVisualization,
                                     fields_mode: Annotated[Literal["merge","replace"],Field(description="Для дерева/карт merge сохраняет пропущенные поля/оси; replace явно заменяет весь набор.")] = "merge") -> dict:
        """Построить тип из giga_list_visualizations через исходные Modus builders. Сохраняет стабильный key, проверяет поля и запрос до записи. Оси задаются явно: dimensions в fields, расчёты в metrics. Bubble требует xvalues/yvalues/values; pivot — rows/columns/values; tree — numeric identity/linkage и raw values; comparison — objects/indicators/values и два compare_values. Для обычной таблицы и KPI предпочтительны giga_set_table/giga_set_kpi."""
        return await invoke("update", "upsert", report_id=report_id, components=[visualization], native_mode=fields_mode)

    @mcp.tool(annotations=annotation("Создать дерево по ролям полей, без ручной настройки осей"))
    async def giga_set_tree(report_id:int, key:str, title:str, dataset_id:int,
                            node_field:str, parent_field:str, label_field:str, size_field:str,
                            color_field:Annotated[str,Field(description="Поле цвета; пустая строка только если цвета нет.")], row:int=3) -> dict:
        """Предпочтительно для дерева: укажи точные имена ID, родителя, подписи, размера и цвета. MCP сам сохраняет raw-типы, роли и все поля; проверяет unique ID, cycles и родителей. Общий фильтр привяжи через giga_bind_report_filter; новые компоненты подхватывают существующий фильтр. Родитель вне среза даёт явную ошибку, не потерю ветки."""
        metrics=[{"label":name,"field":name,"kind":"raw"} for name in [label_field,color_field,size_field] if name]
        spec=NativeVisualization(key=key,title=title,dataset_id=dataset_id,component_type="HsTreeGraph",label_field=label_field,color_field=color_field,size_field=size_field,row=row,height=26,
            axes=[{"axis":"identity","fields":[node_field]},{"axis":"linkage","fields":[parent_field]},{"axis":"values","metrics":metrics}])
        return await invoke("update","upsert",report_id=report_id,components=[spec])

    @mcp.tool(annotations=annotation("Создать карту точек: координаты привязываются автоматически"))
    async def giga_set_map(report_id:int, key:str, title:str, dataset_id:int,
                           point_field:str, latitude_field:str, longitude_field:str, metric:Metric, row:int=4) -> dict:
        """Предпочтительно для Leaflet: ID точки, широта, долгота и числовая метрика. Не дублируй координаты в metrics/axes. MCP сам добавляет координаты в данные, проверяет диапазон и одну пару на ID. Повтор ID с одинаковыми координатами допустим для суммы. Общий фильтр — giga_bind_report_filter."""
        spec=NativeVisualization(key=key,title=title,dataset_id=dataset_id,component_type="HsMapLeafletChart",latitude_field=latitude_field,longitude_field=longitude_field,row=row,height=24,
            axes=[{"axis":"categories","fields":[point_field]},{"axis":"values","metrics":[metric.model_dump()]}])
        return await invoke("update","upsert",report_id=report_id,components=[spec])

    @mcp.tool(annotations=annotation("Создать Tilemap с проверкой каждого региона"))
    async def giga_set_tilemap(report_id:int, key:str, title:str, dataset_id:int,
                               region_field:str, metric:Metric, row:int=5) -> dict:
        """Предпочтительно для Tilemap: поле региона и числовая метрика. MCP сам сопоставляет названия со всем native-справочником; г./город и скобочные официальные уточнения распознаются без ручного словаря отчёта. Неизвестный/пустой регион отклоняется до записи. Исходное поле не изменяется. Общий фильтр — giga_bind_report_filter."""
        spec=NativeVisualization(key=key,title=title,dataset_id=dataset_id,component_type="HsTilemapChart",row=row,height=26,
            axes=[{"axis":"categories","fields":[region_field]},{"axis":"values","metrics":[metric.model_dump()]}])
        return await invoke("update","upsert",report_id=report_id,components=[spec])

    @mcp.tool(annotations=annotation("Поля и строки существующего датасета", True))
    async def giga_read_dataset(dataset_id: Annotated[int, Field(gt=0, description="ID существующего датасета.")],
                                limit: Annotated[int, Field(ge=1, le=100, description="Лимит строк, все поля возвращаются независимо от лимита.")] = 20) -> dict:
        """Прочитать ВСЕ имена/типы/подписи полей, строки и статистику образца без SQL. Статистика выборки не доказывает уникальность ключа или диапазон всего источника. Для проверки зерна/итогов используйте giga_query_dataset."""
        return await invoke("get", "read_dataset", dataset_id=dataset_id, limit=limit)

    @mcp.tool(annotations=annotation("Независимо проверить расчёт на исходном датасете", True))
    async def giga_query_dataset(dataset_id: Annotated[int, Field(gt=0, description="ID изученного источника.")],
                                 metrics: Annotated[list[VisualizationMetric], Field(min_length=1, max_length=24, description="Каждый показатель ОБЯЗАТЕЛЬНО задаёт kind: raw для исходных строк, sum/avg/min/max/count для агрегатов. Возвращаются исходные числа, percent=доля.")],
                                 group_by: Annotated[list[str], Field(max_length=10, description="Точные поля группировки для проверки зерна, например дата/заказчик. [] = общий итог.")] = [],
                                 filters: Annotated[list[ValueFilter], Field(max_length=10, description="Фильтры источника для того же среза, что в отчёте. [] = все строки.")] = [],
                                 limit: Annotated[int, Field(ge=1, le=1000, description="Максимум возвращаемых групп/строк.")] = 100) -> dict:
        """Только чтение: вычислить суммы, взвешенные доли и другие метрики прямо из источника, независимо от конфигурации отчёта. Возвращает group_N/metric_N с явной картой полей и source_row_count для агрегатов. Сначала изучите имена, подписи, типы и строки, обоснуйте выбор поля по задаче; затем сравните числовой результат и фильтр с giga_inspect_report. Успешный запрос сам по себе не доказывает смысл выбранного поля. SQL и эталон отчёта не принимаются."""
        return await invoke("get", "query_dataset", dataset_id=dataset_id, metrics=metrics, group_by=group_by, filters=filters, limit=limit)

    @mcp.tool(annotations=annotation("Создать или найти отчёт по техническому имени"))
    async def giga_create_report(name: Annotated[str, Field(description="Уникальное техническое имя: латиница, цифры и подчёркивания.")],
                                 caption: Annotated[str, Field(description="Русское название отчёта.")],
                                 group_id: Annotated[int, Field(gt=0, description="ID согласованной группы отчётов.")]) -> dict:
        """Создать один отчёт. Повтор с тем же именем и группой возвращает существующий ID. Не меняет источники и права."""
        return await invoke("create", "create_report", name=name, caption=caption, group_id=group_id)

    @mcp.tool(annotations=annotation("Создать или заменить KPI целиком без дубля"))
    async def giga_set_kpi(report_id: Annotated[int, Field(gt=0, description="ID текущего отчёта.")],
                           key: Annotated[str, Field(description="Стабильный ключ KPI, например plan. Повтор обновляет этот KPI.")],
                           title: Annotated[str, Field(description="Подпись KPI.")],
                           dataset_id: Annotated[int, Field(gt=0, description="ID датасета.")], metric: Metric,
                           row: Annotated[int, Field(ge=0, le=100, description="Логический ряд, все KPI обычно row=1.")] = 1) -> dict:
        """Задать KPI одним вызовом: метрика + формат. Денежный итог kind=sum; взвешенный процент kind=ratio_of_sums, format=percent. Никаких SQL/индексов/сгенерированных имён. Сохранение только после проверки запроса."""
        return await invoke("update", "upsert", report_id=report_id, components=[DashboardComponent(key=key, kind="kpi", title=title, dataset_id=dataset_id, metrics=[metric], row=row, height=6)])

    @mcp.tool(annotations=annotation("Создать или заменить полное описание компонентов"))
    async def giga_upsert_components(report_id: Annotated[int, Field(gt=0, description="ID текущего отчёта.")],
                                      components: Annotated[list[ChartComponent], Field(min_length=1, max_length=30, description="Полные определения KPI, графиков, статического текста. Таблицы: giga_set_table; динамический текст: giga_set_rich_text.")],
                                      replace_kind: Annotated[bool, Field(description="Только намеренная замена вида компонента или его источника. Для смены названия false и giga_rename_component.")] = False) -> dict:
        """Задать графики, статический текст и KPI. Для таблиц вызывайте giga_set_table, для выводов из данных — giga_set_rich_text. metrics — ПОЛНЫЙ список. Повтор ключа обновляет без дубля. Линия: category=поле даты, ratio_of_sums и constant=1 с format=percent, без series. Кольцо: category=поле статуса, ОДНА сумма. Гистограмма статусов: category=заказчик, series=статус, ОДНА сумма. Все определения проверяются до единственной записи."""
        return await invoke("update", "upsert", report_id=report_id, components=components, replace_kind=replace_kind)

    @mcp.tool(annotations=annotation("Переименовать компонент, сохранив поля и настройки"))
    async def giga_rename_component(report_id: Annotated[int, Field(gt=0, description="ID текущего отчёта.")],
                                    key: Annotated[str, Field(description="Существующий стабильный ключ графика, дерева, карты, таблицы или KPI.")],
                                    title: Annotated[str, Field(min_length=1, max_length=240, description="Новый заголовок обычным текстом.")]) -> dict:
        """Изменить только название компонента данных. Сохраняет вид, все поля, роли, ID, формулы, фильтры, размеры и стиль. Для переименования не пересоздавайте компонент через text или другой вид. Статический заголовок отчёта: giga_set_header; подпись фильтра: giga_bind_report_filter."""
        return await invoke("update", "rename", report_id=report_id, key=key, title=title)

    @mcp.tool(annotations=annotation("Задать статический заголовок и период отчёта"))
    async def giga_set_header(report_id: Annotated[int, Field(gt=0, description="ID текущего отчёта.")],
                              key: Annotated[str, Field(description="Стабильный ключ заголовка, например header.")],
                              title: Annotated[str, Field(min_length=1, max_length=240, description="Название дашборда обычным текстом.")],
                              period: Annotated[str, Field(min_length=1, max_length=1000, description="Период и дата состояния оплаты обычным текстом.")]) -> dict:
        """Создать компактный статический заголовок: title + period. Датасет не нужен. Это не KPI и не Rich text из данных. Не помещайте сюда изменяемые итоговые суммы или проценты. Повтор того же key обновляет заголовок."""
        spec = DashboardComponent(key=key, kind="text", title=title, text=f"<h1>{escape(title)}</h1><p>{escape(period)}</p>", row=0, height=3)
        return await invoke("update", "upsert", report_id=report_id, components=[spec])

    @mcp.tool(annotations=annotation("Построить таблицу из готовых полей датасета"))
    async def giga_set_table(report_id: Annotated[int, Field(gt=0, description="ID текущего отчёта.")],
                             key: Annotated[str, Field(description="Стабильный ключ таблицы.")],
                             title: Annotated[str, Field(description="Русский заголовок таблицы.")],
                             dataset_id: Annotated[int, Field(gt=0, description="ID датасета с готовыми итогами по строкам.")],
                             columns: Annotated[list[TableColumn], Field(min_length=1, max_length=24, description="Столбцы field,label,format: по умолчанию добавляются/обновляются по field; остальные сохраняются. Без SUM или усреднения процентов.")],
                             row: Annotated[int, Field(ge=0, le=100, description="Логический ряд.")] = 5,
                             width: Annotated[int, Field(ge=1, le=12, description="Доля ширины ряда.")] = 1,
                             height: Annotated[int, Field(ge=3, le=100, description="Высота в строках сетки.")] = 12,
                             columns_mode: Annotated[Literal["merge", "replace"], Field(description="merge сохраняет пропущенные столбцы и порядок, добавляет новые. replace явно заменяет полный список.")] = "merge") -> dict:
        """Создать/обновить таблицу. По умолчанию columns объединяется по field: пропущенные столбцы сохраняются; новые добавляются. Для удаления явно columns_mode=replace. Для сумм и процентов укажите готовые поля. Нули видимы."""
        spec = DashboardComponent(key=key, kind="table", title=title, dataset_id=dataset_id, row=row, width=width, height=height,
            metrics=[Metric(kind="raw", **c.model_dump(exclude_unset=True)) for c in columns])
        return await invoke("update", "upsert", report_id=report_id, components=[spec], table_mode=columns_mode)

    @mcp.tool(annotations=annotation("Показать динамический текст из поля датасета"))
    async def giga_set_rich_text(report_id: Annotated[int, Field(gt=0, description="ID текущего отчёта.")],
                                 key: Annotated[str, Field(description="Стабильный ключ блока выводов.")],
                                 title: Annotated[str, Field(description="Русский заголовок.")],
                                 dataset_id: Annotated[int, Field(gt=0, description="ID датасета с текстами по заказчикам.")],
                                 field: Annotated[str, Field(description="Точное имя поля HTML, например conclusion_html.")],
                                 row: Annotated[int, Field(ge=0, le=100, description="Логический ряд.")] = 6) -> dict:
        """Отобразить HTML каждой строки как карточку. Общий фильтр автоматически отбирает записи. Четыре записи — два столбца, одна запись — вся ширина. Высота по содержимому, без внутренней прокрутки."""
        spec = DashboardComponent(key=key, kind="rich_text", title=title, dataset_id=dataset_id, row=row,
            metrics=[Metric(kind="raw", field=field, label=title, format="html")], height=24)
        return await invoke("update", "upsert", report_id=report_id, components=[spec])

    @mcp.tool(annotations=annotation("Настроить ориентацию и накопление существующей гистограммы"))
    async def giga_set_bar_options(report_id: Annotated[int, Field(gt=0, description="ID текущего отчёта.")],
                                   key: Annotated[str, Field(description="Стабильный ключ существующей гистограммы.")],
                                   horizontal: Annotated[bool, Field(description="true = горизонтальная.")],
                                   stacked: Annotated[bool, Field(description="true = накопление статусов в одном столбце.")]) -> dict:
        """Изменить только horizontal/stacked по ключу. Датасет, поля, цвета, фильтры и размеры сохраняются. Не пересылайте таблицу или полный отчёт для этой настройки."""
        return await invoke("update", "patch_component", report_id=report_id, key=key, horizontal=horizontal, stacked=stacked)

    @mcp.tool(annotations=annotation("Настроить подсветку одного существующего столбца таблицы"))
    async def giga_set_table_rules(report_id: Annotated[int, Field(gt=0, description="ID текущего отчёта.")],
                                   key: Annotated[str, Field(description="Стабильный ключ существующей таблицы.")],
                                   field: Annotated[str, Field(description="Точное имя уже добавленного столбца датасета.")],
                                   rules: Annotated[list[CellRule], Field(max_length=5, description="Правила по порядку, первое совпадение. Процент сравнивается как доля: 1=100%, 0.7=70%. [] очищает подсветку.")]) -> dict:
        """Изменить только условное форматирование одного поля. Все столбцы и данные таблицы сохраняются. Для выполнения плана задайте пороги по исходной доле; для просрочки положительное значение — operator=gt,value=0. Не пересылайте всю таблицу ради подсветки."""
        return await invoke("update", "patch_component", report_id=report_id, key=key, rule_field=field, rules=rules)

    @mcp.tool(annotations=annotation("Связать единый фильтр со всеми компонентами"))
    async def giga_bind_report_filter(report_id: Annotated[int, Field(gt=0, description="ID текущего отчёта.")],
                                       key: Annotated[str, Field(description="Стабильный ключ фильтра, например customer.")],
                                       label: Annotated[str, Field(description="Общее русское имя фильтра, например Заказчик.")],
                                       bindings: Annotated[list[DatasetFilter], Field(min_length=1, max_length=30, description="Для каждого датасета отчёта укажите поле общего среза с одинаковым смыслом и типом: например группа, подразделение, заказчик.")],
                                       row: Annotated[int, Field(ge=0, le=100, description="Ряд фильтра.")] = 2) -> dict:
        """Создать одну панель и связать ВСЕ компоненты отчёта атомарно. Например customer_name во всех трёх витринах, не денежное поле. Новые компоненты связываются автоматически. Отсутствующее/несовместимое поле даёт ошибку до записи."""
        return await invoke("update", "bind_filter", report_id=report_id, key=key, label=label, bindings=bindings, row=row)

    @mcp.tool(annotations=annotation("Выбрать значения общего фильтра или сбросить"))
    async def giga_select_filter(report_id: Annotated[int, Field(gt=0, description="ID текущего отчёта.")],
                                  key: Annotated[str, Field(description="Стабильный ключ существующего фильтра.")],
                                  values: Annotated[list[str], Field(max_length=100, description="Точные значения источника, например Заказчик Б. Пустой список [] = сброс.")]) -> dict:
        """Выбрать значения по стабильному ключу. Проверяет существование значений; [] очищает панель И globalFilters. Не сокращайте Заказчик Б до Б."""
        return await invoke("update", "select_filter", report_id=report_id, key=key, values=values)

    @mcp.tool(annotations=annotation("Удалить лишние созданные компоненты по ключам"))
    async def giga_remove_components(report_id: Annotated[int, Field(gt=0, description="ID текущего отчёта.")],
                                     keys: Annotated[list[str], Field(min_length=1, max_length=30, description="Стабильные ключи лишних компонентов текущего отчёта.")]) -> dict:
        """Удалить только компоненты этого профиля по key, например лишнюю таблицу после замены её графиком. Общий фильтр и чужие компоненты не удаляются. Повтор отсутствующего ключа безопасен."""
        return await invoke("delete", "remove", report_id=report_id, keys=keys)

    @mcp.tool(annotations=annotation("Изменить размещение без изменения показателей"))
    async def giga_arrange_report(report_id: Annotated[int, Field(gt=0, description="ID текущего отчёта.")],
                                   placements: Annotated[list[Placement], Field(min_length=1, max_length=30, description="Позиции существующих ключей: row, относительная width и height.")]) -> dict:
        """Разместить компоненты по рядам на ВСЕХ брейкпоинтах. Пример: KPI один row, bar width=2 и donut width=1 на следующем. Без ручных x/y и пересечений."""
        return await invoke("update", "arrange", report_id=report_id, placements=placements)

    @mcp.tool(annotations=annotation("Применить светлое оформление и стандартное размещение"))
    async def giga_apply_dashboard_preset(report_id: Annotated[int, Field(gt=0, description="ID текущего отчёта.")],
                                          style:Annotated[Literal["corporate_clean","clean_minimalism","swiss","warm_minimalism"],Field(description="Стиль из giga_list_report_styles. Сохраняет поля, данные и общие фильтры.")]="corporate_clean") -> dict:
        """Применить проверенный light_dashboard к компонентам профиля: компактный заголовок, KPI в одном ряду, фильтр отдельно, bar 2/3 + donut 1/3, затем линия, таблица и выводы. Числа KPI 32 px, подписи 15 px, заголовки 26/16 px, светлые поверхности. Чужой CSS сохраняется. Перед вызовом прочитайте giga_inspect_report с include_style=true. Условное форматирование таблицы задаётся отдельно через columns.cell_rules в giga_set_table."""
        return await invoke("update", "apply_preset", report_id=report_id, style=style)

    @mcp.tool(annotations=annotation("Проверить сохранённую конфигурацию и данные", True))
    async def giga_inspect_report(report_id: Annotated[int, Field(gt=0, description="ID текущего отчёта.")],
                                   include_data: Annotated[bool, Field(description="Прочитать строки компонентов; false возвращает только состояние.")] = True,
                                   include_style: Annotated[bool, Field(description="Вернуть текущий CSS, реальные ID панелей и поддержанные классы перед оформлением.")] = False) -> dict:
        """Прочитать фактическое состояние, стабильные ключи, метрики, фильтры, данные и ошибки размещения. fingerprint показывает изменение отчёта. Не доказывает правильность бизнес-метрик и отображение в браузере; browser_verified всегда false."""
        return await invoke("get", "inspect", report_id=report_id, include_data=include_data, include_style=include_style)

    for name in original_names:
        mcp.remove_tool(name)
    mcp._mcp_server.instructions = GIGACHAT_WORKFLOW
    for tool in mcp._tool_manager._tools.values():
        tool.parameters = inline_schema(tool.parameters)
    mcp._modus_tool_profile = "gigachat"
