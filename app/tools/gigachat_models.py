"""Explicit dashboard contracts for clients with compact tool schemas.

No provider credentials, model calls or portal-specific dataset IDs belong here.
"""
from __future__ import annotations

import re
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator

DateDisplayFormat = Literal["", "DD.MM.YYYY", "DD.MM.YYYY HH:mm", "MM.YYYY", "MMM YYYY", "MMMM YYYY", "MMM", "MMMM", "YYYY", "YYYY-MM-DD"]
SimpleAggregation = Literal["", "sum", "avg", "min", "max", "count"]


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CellRule(Contract):
    operator: Literal["gt", "gte", "lt", "lte", "eq"] = Field(description="Сравнение исходного числа; для процентов 1 = 100%.")
    value: float = Field(allow_inf_nan=False, description="Порог в исходных единицах.")
    background: str = Field(pattern=r"^#[0-9A-Fa-f]{6}$", description="Фон ячейки #RRGGBB.")


class Metric(Contract):
    label: str = Field(min_length=1, max_length=160, description="Подпись показателя на русском.")
    kind: Literal["sum", "avg", "min", "max", "count", "raw", "ratio_of_sums", "difference_of_sums", "constant"] = Field(default="sum", description="Для ВСЕХ столбцов table используйте raw и готовое поле датасета. Для KPI/графиков sum или ratio_of_sums = SUM(numerator)/SUM(denominator).")
    field: str = Field(default="", description="Точное имя поля для sum/avg/min/max/raw. Для count пустое field считает все строки (COUNT(*)); указанное поле считает только ненулевые значения. Не передавайте SQL или '*'.")
    numerator: str = Field(default="", description="Числитель для ratio_of_sums или уменьшаемое для difference_of_sums.")
    denominator: str = Field(default="", description="Знаменатель для ratio_of_sums или вычитаемое для difference_of_sums.")
    constant: float = Field(default=0.0, allow_inf_nan=False, description="Числовая константа только для kind=constant, например целевой уровень 1.")
    format: Literal["number", "rubles", "percent", "text", "html"] = Field(default="number", description="percent: входная доля 0..1 отображается как 0..100%. html: HTML из поля датасета.")
    decimals: int = Field(default=0, ge=0, le=6, description="Знаков после запятой, 0..6.")
    cell_rules: list[CellRule] = Field(default_factory=list, max_length=5, description="Подсветка числовых ячеек таблицы. Первое совпавшее правило применяется.")


class SeriesColor(Contract):
    value: str = Field(description="Точное значение серии или категории.")
    color: str = Field(pattern=r"^#[0-9A-Fa-f]{6}$", description="Цвет #RRGGBB.")


class DashboardComponent(Contract):
    key: str = Field(pattern=r"^[a-z][a-z0-9_]{0,63}$", description="Стабильный ключ: повторный вызов обновляет этот компонент без дубля.")
    kind: Literal["kpi", "bar", "line", "donut", "table", "rich_text", "text"] = Field(description="bar = гистограмма, line = линейный график, donut = кольцо, table = таблица строк. Не заменяйте требуемый график таблицей.")
    title: str = Field(min_length=1, max_length=240, description="Заголовок компонента.")
    dataset_id: int = Field(default=0, ge=0, description="ID существующего датасета. 0 только для статического text.")
    category: str = Field(default="", description="Поле группировки для диаграммы. Для line это поле даты.")
    series: str = Field(default="", description="Поле серий, например статус оплаты. Не совпадает с category.")
    metrics: list[Metric] = Field(default_factory=list, max_length=24, description="ПОЛНЫЙ список показателей/столбцов, заменяет прежний список. KPI: ровно один показатель.")
    text: str = Field(default="", max_length=20000, description="HTML только статического text. Для динамического HTML используйте rich_text и поле датасета.")
    row: int = Field(default=1, ge=0, le=100, description="Логический ряд. Одинаковый row = компоненты рядом; KPI обычно в одном ряду.")
    width: int = Field(default=1, ge=1, le=12, description="Относительная доля ширины внутри ряда, например bar=2, donut=1.")
    height: int = Field(default=12, ge=3, le=100, description="Высота в строках сетки; text 4, KPI 6, график 14, таблица 12.")
    horizontal: bool = Field(default=False, description="Горизонтальные столбцы для bar.")
    stacked: bool = Field(default=False, description="Накопление серий bar.")
    colors: list[SeriesColor] = Field(default_factory=list, max_length=30, description="Порядок и цвета серий/категорий.")

    @model_validator(mode="after")
    def meaningful(self):
        if self.kind == "text":
            if self.dataset_id or self.metrics or not self.text.strip():
                raise ValueError("text requires nonempty text, no dataset or metrics")
            return self
        if not self.dataset_id or not self.metrics:
            raise ValueError("data component requires dataset_id and metrics")
        if self.kind == "kpi" and len(self.metrics) != 1:
            raise ValueError("KPI requires exactly one metric; use separate stable keys")
        if self.kind == "table" and len({m.field for m in self.metrics}) != len(self.metrics):
            raise ValueError("DUPLICATE_TABLE_FIELD: every table field must be unique")
        if self.kind in {"bar", "line", "donut"} and not self.category:
            raise ValueError(f"Компонент {self.key!r}: заполните category точным именем поля группировки датасета. У кольца это поле статуса, у линии — даты, у гистограммы — заказчика. category не наследуется из соседнего компонента.")
        if (self.kind == "donut" or self.kind in {"bar", "line"} and self.series) and len(self.metrics) != 1:
            raise ValueError(f"Компонент {self.key!r}: кольцо и график с series требуют ровно ОДИН показатель metrics. Удалите дополнительную метрику 'Доля, %': проценты в подсказках рассчитывает диаграмма. Для факта и плана 100% на одной линии не задавайте series.")
        if self.category and self.category == self.series:
            raise ValueError("category and series must be different fields")
        if self.kind == "rich_text" and (len(self.metrics) != 1 or self.metrics[0].format != "html" or self.metrics[0].kind != "raw"):
            raise ValueError("rich_text requires one raw HTML field")
        if self.kind == "kpi" and self.metrics[0].kind == "raw":
            raise ValueError("KPI requires explicit aggregation, not raw")
        if self.kind in {"table", "rich_text"} and any(m.kind not in {"raw", "constant"} for m in self.metrics):
            raise ValueError("Для КАЖДОГО показателя table задайте kind='raw' и field=готовое поле строки датасета, включая суммы и проценты. sum/ratio_of_sums в таблице запрещены; они предназначены для KPI и графиков.")
        if self.kind in {"bar", "line", "donut"} and any(m.kind == "raw" for m in self.metrics):
            raise ValueError("chart requires aggregate metrics")
        for metric in self.metrics:
            if metric.cell_rules and (self.kind != "table" or metric.format in {"text", "html"}):
                raise ValueError("cell_rules apply only to numeric table cells")
            names = [metric.numerator, metric.denominator] if metric.kind in {"ratio_of_sums", "difference_of_sums"} else ([metric.field] if metric.kind != "constant" and not (metric.kind == "count" and not metric.field) else [])
            if metric.kind in {"ratio_of_sums", "difference_of_sums"} and (not metric.numerator or not metric.denominator):
                raise ValueError(f"Показатель {metric.label!r}: нужны ОБА поля numerator и denominator. Для одной суммы используйте kind='sum' и field; для готовой таблицы — giga_set_table.")
            if any(not name or not re.fullmatch(r"[\w .\-]+", name, re.UNICODE) for name in names):
                raise ValueError("Use dataset field names, not SQL expressions")
            if metric.format in {"text", "html"} and metric.kind != "raw":
                raise ValueError("text/html format requires a raw field")
        return self


class DatasetFilter(Contract):
    dataset_id: int = Field(gt=0, description="ID датасета.")
    field: str = Field(min_length=1, description="Точное имя поля фильтра этого датасета.")


class ValueFilter(Contract):
    field: str = Field(min_length=1, description="Точное имя поля источника.")
    values: list[str] = Field(min_length=1, max_length=100, description="Точные значения: OR внутри поля, AND между полями. Пустой filters означает весь источник.")


class VisualizationMetric(Metric):
    kind: Literal["sum", "avg", "min", "max", "count", "raw", "ratio_of_sums", "difference_of_sums", "constant"] = Field(description="Обязательный выбор агрегации. Для Tree/Parallel используйте raw (без агрегации). Для сумм sum, для взвешенного процента ratio_of_sums.")


class VisualizationAxis(Contract):
    axis: str = Field(min_length=1, max_length=40, description="Точное имя оси из giga_list_visualizations: categories, values, xvalues, yvalues, rows, columns, identity, linkage и т.д.")
    fields: list[str] = Field(default_factory=list, max_length=12, description="Размерности: точные поля без агрегации. Числовые values/xvalues/yvalues диаграмм требуют metrics с явным kind, не fields. Исключение: raw values у Tree/Parallel.")
    metrics: list[VisualizationMetric] = Field(default_factory=list, max_length=12, description="Числовые метрики этой оси с явным kind. Не подменяйте размерность метрикой.")


class FieldLabel(Contract):
    field: str = Field(min_length=1, description="Точное исходное поле, имя и привязка сохраняются.")
    label: str = Field(min_length=1, max_length=160, description="Понятная читателю подпись поля на языке отчёта.")


class NativeVisualization(Contract):
    key: str = Field(pattern=r"^[a-z][a-z0-9_]{0,63}$")
    kind: Literal["native"] = "native"
    component_type: Literal["HsBarAMchartsChart", "HsLineAMchartsChart", "HsAreaAMchartsChart", "HsPieAMchartsChart", "HsRadarAMchartsChart", "HsStockAMchartsChart", "HsSpeedometerV2AMcharts", "HsBubbleAMchartsChart", "HsSunburstChart", "HsTreeMap", "HsParallelCoordsChart", "HsPivotChart", "HsComparisonChart", "HsTreeGraph", "HsMapLeafletChart", "HsTilemapChart", "HsFilterControlPanel", "HsHierarchicalFilterPanel", "HsSubheaderComponent", "HsIframe", "HsImagePanel", "HsPageContainer", "HsTotalsPanelV2", "HsTableReactabularChart", "HsTextBlock", "HsTabsPanel", "HsSwitchControlPanel", "HsAudioplayer"] = Field(description="Точный native-тип; выбирайте из enum и каталога. Не выдумывайте имена.")
    title: str = Field(min_length=1, max_length=240)
    dataset_id: int = Field(ge=0, description="Источник для визуализации данных; 0 только для контентных компонентов.")
    axes: list[VisualizationAxis] = Field(max_length=10, description="Обязательные реальные оси из каталога. Bubble: categories, xvalues, yvalues, values. Parallel: все поля на values, kind=raw. Две ступени иерархии передавайте одним categories.fields=[верхний,нижний]. Не пропускайте axes при обновлении.")
    row: int = Field(default=1, ge=0, le=100)
    width: int = Field(default=1, ge=1, le=12)
    height: int = Field(default=14, ge=3, le=100)
    minimum: float = Field(default=0, allow_inf_nan=False, description="Нижняя граница шкалы gauge.")
    maximum: float = Field(default=100, allow_inf_nan=False, description="Верхняя граница шкалы gauge.")
    latitude_field: str = Field(default="", description="Поле широты для Leaflet, должно быть привязано к оси.")
    longitude_field: str = Field(default="", description="Поле долготы для Leaflet, должно быть привязано к оси.")
    label_field: str = Field(default="", description="Текстовая подпись узла дерева.")
    color_field: str = Field(default="", description="Поле цвета узла дерева.")
    size_field: str = Field(default="", description="Поле числового размера узла дерева.")
    compare_values: list[str] = Field(default_factory=list, max_length=2, description="Два точных значения оси objects для comparison.")
    indicator_values: list[str] = Field(default_factory=list, max_length=100, description="Выбранные значения indicators для comparison. Пустой список автоматически получает все distinct значения источника (до100).")
    indicator_mode: Literal['all','selected'] = Field(default='all',description="Comparison: all (по умолчанию) сохраняет все показатели источника; indicator_values не сужает этот режим. selected выбирает только indicator_values для явно требуемого ограниченного набора.")
    donut: bool = Field(default=False, description="Для HsPieAMchartsChart: false=круг, true=кольцо.")
    field_labels: list[FieldLabel] = Field(default_factory=list, max_length=48, description="Подписи исходных полей размерностей и raw-осей: [{field,label}]. Используй человекочитаемые подписи вместо технических имён. Это оформление, не замена полей.")

    @model_validator(mode="after")
    def unique_axes(self):
        if len({f.field for f in self.field_labels}) != len(self.field_labels):
            raise ValueError('Each field label must be specified once')
        if len({a.axis for a in self.axes}) != len(self.axes):
            raise ValueError("Each visualization axis must be specified once")
        if self.component_type=="HsComparisonChart" and len(self.indicator_values)!=len(set(self.indicator_values)):
            raise ValueError("Comparison indicator_values must be unique; duplicates would render repeated rows")
        if self.component_type=='HsComparisonChart' and self.indicator_mode=='selected' and not self.indicator_values:
            raise ValueError('Comparison selected mode requires nonempty indicator_values; use all for full coverage')
        if self.component_type == "HsSpeedometerV2AMcharts" and self.maximum <= self.minimum:
            raise ValueError("maximum must exceed minimum")
        return self


class ChartComponent(DashboardComponent):
    kind: Literal["kpi", "bar", "line", "donut", "text"] = Field(description="bar=гистограмма, line=линия, donut=кольцо. Таблицы: giga_set_table, динамический текст: giga_set_rich_text.")
    metrics: list[Metric] = Field(default_factory=list, max_length=24, description="ПОЛНЫЙ список показателей. donut и bar с series: ОДНА сумма, без отдельного показателя доли. line допускает отношение сумм и константу плана. KPI: один показатель.")
    category: str = Field(description="ОБЯЗАТЕЛЬНЫЙ параметр каждого компонента: donut — поле статуса, bar — поле заказчика, line — поле даты. Для KPI и статического text передайте пустую строку.")


class TableColumn(Contract):
    label: str = Field(min_length=1, max_length=160, description="Русский заголовок столбца.")
    field: str = Field(min_length=1, description="Точное имя готового поля строки датасета. Без агрегации и SQL.")
    format: Literal["number", "rubles", "percent", "text", "html"] = Field(default="number", description="Если не задан, MCP выбирает text для текстовых полей/дат и number для числовых по схеме источника. percent принимает долю 0..1. Явное значение формата проверяется строго.")
    decimals: int = Field(default=0, ge=0, le=6, description="Знаков после запятой.")
    cell_rules: list[CellRule] = Field(default_factory=list, max_length=5, description="Подсветка числовых ячеек в исходных единицах.")


class Placement(Contract):
    key: str = Field(pattern=r"^[a-z][a-z0-9_]{0,63}$", description="Существующий стабильный ключ компонента.")
    row: int = Field(ge=0, le=100, description="Логический ряд, одинаковый row размещает компоненты рядом.")
    width: int = Field(default=0, ge=0, le=12, description="Относительная доля ширины; 0 или отсутствие сохраняет текущую.")
    height: int = Field(default=0, ge=0, le=100, description="Высота в строках сетки; 0 или отсутствие сохраняет текущую. Положительное значение не меньше 3.")

    @model_validator(mode="after")
    def valid_height(self):
        if self.height in {1, 2}:
            raise ValueError("height must be 0 (preserve) or at least 3")
        return self
