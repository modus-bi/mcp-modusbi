"""
Справочник CSS классов ModusBI.

Содержит документацию по доступным CSS классам,
примеры стилизации и валидатор CSS.
"""

import re
from typing import Any


class CSSSchemaProvider:
    """Провайдер справочника CSS классов ModusBI."""
    
    # Справочник CSS классов
    CSS_CLASSES = {
        "header": {
            ".hsHeader": {
                "description": "Главная шапка отчёта",
                "properties": ["background", "border-bottom", "box-shadow"],
                "example": ".hsHeader { background: linear-gradient(135deg, #1a1f36, #2d3555); }"
            },
            ".hsHeader.hsHeader__report": {
                "description": "Шапка в режиме просмотра отчёта",
                "properties": ["background", "border-image"],
                "example": ".hsHeader.hsHeader__report { border-bottom: 4px solid #3d8bfd; }"
            },
            ".hsHeaderContainer": {
                "description": "Контейнер с названием отчёта",
                "properties": ["background"],
                "example": ".hsHeaderContainer { background: transparent; }"
            },
            ".hsHeaderActions": {
                "description": "Контейнер с кнопками действий (справа)",
                "properties": ["display", "gap"],
                "example": ".hsHeaderActions { display: flex; gap: 8px; }"
            },
            ".hsSubheader": {
                "description": "Подзаголовок/дополнительная панель",
                "properties": ["background"],
                "example": ".hsSubheader { background: transparent; }"
            },
            ".hsHeader h1": {
                "description": "Заголовок отчёта (h1)",
                "properties": ["color", "font-size", "font-weight", "text-shadow"],
                "example": ".hsHeader h1 { color: #fff; font-weight: 700; }"
            },
            ".hsHeader button": {
                "description": "Кнопки в шапке",
                "properties": ["background", "border", "border-radius", "min-width", "min-height"],
                "example": ".hsHeader button { background: rgba(255,255,255,0.08); border-radius: 10px; }"
            },
            ".hsHeader button img": {
                "description": "Иконки в кнопках шапки",
                "properties": ["width", "height", "filter"],
                "example": ".hsHeader button img { width: 22px; filter: brightness(0) invert(1); }"
            },
            ".hsLogo": {
                "description": "Логотип/иконка в левой части шапки (ссылка на главное меню)",
                "properties": ["background", "background-color", "padding", "border-radius", "filter"],
                "example": ".hsLogo { background-color: #3d8bfd !important; }"
            },
            ".hsLogo svg": {
                "description": "SVG иконка внутри логотипа",
                "properties": ["fill", "filter", "width", "height"],
                "example": ".hsLogo svg { filter: brightness(0) invert(1); }"
            }
        },
        "selectors": {
            "#panel_N": {
                "description": "ID контейнера конкретного компонента (N — idx из get_report_components). ⚠️ Не все компоненты имеют .componentHeader (например FilterControlPanel)",
                "properties": ["любые CSS свойства"],
                "example": "#panel_0 .componentHeader { background: red !important; }"
            },
            "#panel_N .componentHeader": {
                "description": "Заголовок конкретного компонента",
                "properties": ["background", "color", "font-size"],
                "example": "#panel_2 .componentHeader { background: linear-gradient(135deg, #f59e0b, #d97706); }"
            },
            "#panel_N .amcharts-axis-label > TSPAN": {
                "description": "Подписи осей конкретной диаграммы (SVG — используйте fill)",
                "properties": ["fill", "font-size", "font-weight"],
                "example": "#panel_8 .amcharts-axis-label > TSPAN { fill: #FF0000; }"
            },
            "#panel_N .hs-table__table": {
                "description": "Таблица конкретного компонента",
                "properties": ["width", "border"],
                "example": "#panel_3 .hs-table__table th { background: #1e40af; color: white; }"
            },
            "#panel_N .amcharts-*": {
                "description": "Любые элементы AMCharts диаграммы (SVG)",
                "properties": ["fill", "stroke", "opacity"],
                "example": "#panel_5 .amcharts-graph-column { fill: #10b981 !important; }"
            }
        },
        "components": {
            ".componentContainer": {
                "description": "Контейнер компонента (обёртка)",
                "properties": ["border", "box-shadow", "border-radius", "background", "overflow"],
                "example": ".componentContainer { border-radius: 14px; background: #fff; }"
            },
            ".componentHeader": {
                "description": "Заголовок компонента (диаграммы, таблицы)",
                "properties": ["background", "color", "font-size", "padding", "border-radius", "font-weight", "text-transform", "letter-spacing"],
                "example": ".componentHeader { background: linear-gradient(135deg, #4f46e5, #7c3aed); color: #fff; }"
            },
            ".componentBody": {
                "description": "Тело компонента (область с данными)",
                "properties": ["background", "padding", "border"],
                "example": ".componentBody { background: #fff; padding: 16px; }"
            },
            ".titleText": {
                "description": "Текст заголовка компонента",
                "properties": ["color", "font-weight"],
                "example": ".componentHeader .titleText { color: #fff; }"
            },
            ".titleText.strongly": {
                "description": "Жирный текст заголовка",
                "properties": ["font-weight"],
                "example": ".titleText.strongly { font-weight: 700; }"
            },
            ".componentContainerForTable": {
                "description": "Специальный контейнер для таблиц",
                "properties": ["overflow", "max-height"],
                "example": ".componentContainerForTable { max-height: 500px; overflow: auto; }"
            }
        },
        "tables": {
            ".hs-table__main": {
                "description": "Основной контейнер таблицы",
                "properties": ["width", "margin", "border-radius", "overflow", "border"],
                "example": ".hs-table__main { border-radius: 10px; overflow: hidden; }"
            },
            ".hs-table__table": {
                "description": "Сама таблица (table element)",
                "properties": ["border-collapse", "border-spacing", "width"],
                "example": ".hs-table__table { border-collapse: separate; border-spacing: 0; }"
            },
            ".hs-table__table th": {
                "description": "Заголовки столбцов таблицы",
                "properties": ["background", "color", "padding", "font-weight", "font-size", "text-transform", "letter-spacing", "border-bottom"],
                "example": ".hs-table__table th { background: linear-gradient(180deg, #334155, #1e293b); color: #f1f5f9; }"
            },
            ".hs-table__table td": {
                "description": "Ячейки таблицы",
                "properties": ["padding", "border-bottom", "background", "color", "font-size", "transition"],
                "example": ".hs-table__table td { padding: 12px 16px; border-bottom: 1px solid #e2e8f0; }"
            },
            ".hs-table__table tr:nth-child(even) td": {
                "description": "Чётные строки (для зебры)",
                "properties": ["background"],
                "example": ".hs-table__table tr:nth-child(even) td { background: #fafbfc; }"
            },
            ".hs-table__table tr:nth-child(odd) td": {
                "description": "Нечётные строки",
                "properties": ["background"],
                "example": ".hs-table__table tr:nth-child(odd) td { background: #fff; }"
            },
            ".hs-table__table tr:hover td": {
                "description": "Строка при наведении",
                "properties": ["background", "color"],
                "example": ".hs-table__table tr:hover td { background: linear-gradient(90deg, #ecfdf5, #d1fae5); }"
            },
            ".hs-table__table tfoot tr td": {
                "description": "Строка итогов (футер)",
                "properties": ["background", "color", "font-weight", "border-top"],
                "example": ".hs-table__table tfoot tr td { background: #fef3c7; font-weight: 700; }"
            },
            ".pure-table": {
                "description": "Базовый класс таблицы (pure.css)",
                "properties": ["border", "width"],
                "example": ".pure-table { border: 1px solid #ddd; }"
            },
            ".pure-table-striped": {
                "description": "Таблица с чередованием строк",
                "properties": [],
                "example": "Автоматически применяется к таблицам"
            },
            ".multilineHeader": {
                "description": "Многострочный заголовок таблицы",
                "properties": [],
                "example": "Используется для таблиц с многострочными заголовками"
            },
            ".sortable": {
                "description": "Сортируемая таблица",
                "properties": [],
                "example": "Добавляется к сортируемым таблицам"
            }
        },
        "charts": {
            ".HsPieAMchartsChart": {
                "description": "Контейнер круговой диаграммы (frontSide)",
                "properties": ["background"],
                "example": ".HsPieAMchartsChart { background: transparent; }"
            },
            ".HsBarAMchartsChart": {
                "description": "Контейнер столбчатой диаграммы (frontSide)",
                "properties": ["background"],
                "example": ".HsBarAMchartsChart { background: transparent; }"
            },
            ".HsLineAMchartsChart": {
                "description": "Контейнер линейного графика (frontSide)",
                "properties": ["background"],
                "example": ".HsLineAMchartsChart { background: transparent; }"
            },
            ".hsChartContainer": {
                "description": "Общий контейнер диаграммы",
                "properties": ["background"],
                "example": ".hsChartContainer { background: #fff; }"
            },
            ".hsChartContainer.amCharts3": {
                "description": "Контейнер AMCharts 3",
                "properties": ["background"],
                "example": ".hsChartContainer.amCharts3 { background: transparent; }"
            },
            ".hsChartContainer.ECharts": {
                "description": "Контейнер ECharts",
                "properties": ["background"],
                "example": ".hsChartContainer.ECharts { background: transparent; }"
            },
            ".hsChartContainer.hasDrillDown": {
                "description": "Диаграмма с drill-down",
                "properties": [],
                "example": "Добавляется к диаграммам с drill-down"
            },
            ".amcharts-main-div": {
                "description": "Главный контейнер AMCharts",
                "properties": ["background"],
                "example": ".amcharts-main-div { background: transparent; }"
            },
            ".amcharts-chart-div": {
                "description": "Область отрисовки диаграммы",
                "properties": ["background"],
                "example": ".amcharts-chart-div { background: transparent; }"
            },
            ".amChartsLegend": {
                "description": "Легенда диаграммы AMCharts",
                "properties": ["font-size", "font-family"],
                "example": ".amChartsLegend { font-size: 12px; }"
            },
            ".amcharts-legend-div": {
                "description": "Контейнер легенды",
                "properties": ["font-size", "color"],
                "example": ".amcharts-legend-div { font-size: 12px; color: #475569; }"
            },
            ".amcharts-legend-label": {
                "description": "Метки в легенде",
                "properties": ["color", "font-weight"],
                "example": ".amcharts-legend-label { color: #334155; font-weight: 500; }"
            },
            ".amcharts-pie-slice": {
                "description": "Сектор круговой диаграммы (SVG)",
                "properties": ["stroke", "stroke-width"],
                "example": ".amcharts-pie-slice { stroke: white; stroke-width: 2; }"
            },
            ".amcharts-pie-label": {
                "description": "Метки на секторах",
                "properties": ["font-size", "fill"],
                "example": ".amcharts-pie-label { font-size: 11px; }"
            }
        },
        "maps": {
            ".HsTreeMap": {
                "description": "Контейнер TreeMap (frontSide)",
                "properties": ["background"],
                "example": ".HsTreeMap { background: #fff; }"
            },
            ".HsTilemapChart": {
                "description": "Контейнер плиточной карты (frontSide)",
                "properties": ["background"],
                "example": ".HsTilemapChart { background: #fff; }"
            },
            ".tilemapContainer": {
                "description": "Внутренний контейнер Tilemap",
                "properties": ["background"],
                "example": ".tilemapContainer { background: #fff; }"
            },
            "[class*=\"tilemap\"] svg rect": {
                "description": "Плитки карты (SVG rect)",
                "properties": ["rx", "stroke", "stroke-width", "fill"],
                "example": "[class*=\"tilemap\"] svg rect { rx: 3; stroke: #fff; }"
            },
            "[class*=\"tilemap\"] svg rect[fill=\"#cccccc\"]": {
                "description": "Серые плитки без данных",
                "properties": ["fill"],
                "example": "[class*=\"tilemap\"] svg rect[fill=\"#cccccc\"] { fill: #e0f2fe; }"
            },
            ".HsMapLeafletChart": {
                "description": "Контейнер карты Leaflet (frontSide)",
                "properties": ["background"],
                "example": ".HsMapLeafletChart { background: #fff; }"
            },
            ".leaflet-container": {
                "description": "Главный контейнер Leaflet",
                "properties": ["background"],
                "example": ".leaflet-container { background: #fff; }"
            },
            ".leaflet-tile-pane": {
                "description": "Панель тайлов карты",
                "properties": [],
                "example": "Содержит тайлы карты"
            },
            ".leaflet-marker-pane": {
                "description": "Панель маркеров",
                "properties": [],
                "example": "Содержит маркеры на карте"
            },
            ".leaflet-popup-pane": {
                "description": "Панель попапов",
                "properties": [],
                "example": "Содержит всплывающие окна"
            },
            ".leaflet-control-container": {
                "description": "Контейнер контролов карты",
                "properties": [],
                "example": "Содержит zoom и другие контролы"
            }
        },
        "pivot": {
            ".HsPivotChart": {
                "description": "Контейнер сводной таблицы (frontSide)",
                "properties": ["background"],
                "example": ".HsPivotChart { background: #fff; }"
            },
            ".pivotCanvas": {
                "description": "Канвас сводной таблицы",
                "properties": ["background"],
                "example": ".pivotCanvas { background: #fff; }"
            },
            ".pivotMain": {
                "description": "Главный контейнер Pivot",
                "properties": ["background"],
                "example": ".pivotMain { background: #fff; }"
            },
            ".pivotContainer": {
                "description": "Внутренний контейнер Pivot",
                "properties": ["background"],
                "example": ".pivotContainer { background: #fff; }"
            },
            ".TitleVer": {
                "description": "Вертикальный заголовок Pivot",
                "properties": ["background", "color"],
                "example": ".TitleVer { background: #f5f5f5; }"
            },
            ".cell": {
                "description": "Ячейка Pivot",
                "properties": ["background", "padding"],
                "example": ".cell { padding: 8px; }"
            },
            ".pivot-header-hor-expander-default": {
                "description": "Горизонтальный экспандер",
                "properties": ["cursor"],
                "example": "Кнопка разворачивания по горизонтали"
            },
            ".pivot-header-ver-expander-default": {
                "description": "Вертикальный экспандер",
                "properties": ["cursor"],
                "example": "Кнопка разворачивания по вертикали"
            },
            ".orb-tgl-btn": {
                "description": "Кнопка переключения Pivot",
                "properties": ["cursor"],
                "example": "Кнопка +/- для разворачивания"
            },
            ".orb-tgl-btn-down": {
                "description": "Кнопка в развёрнутом состоянии",
                "properties": [],
                "example": "Показывает минус (-)"
            },
            ".orb-tgl-btn-right": {
                "description": "Кнопка в свёрнутом состоянии",
                "properties": [],
                "example": "Показывает плюс (+)"
            }
        },
        "filters": {
            ".HsFilterControlPanel": {
                "description": "Панель управления фильтрами (frontSide)",
                "properties": ["background"],
                "example": ".HsFilterControlPanel { background: #fff; }"
            },
            ".hsFilterControlPanel": {
                "description": "Контейнер фильтров",
                "properties": ["background", "border-bottom"],
                "example": ".hsFilterControlPanel { background: linear-gradient(180deg, #fff, #f8fafc); }"
            },
            ".hsFastFiltersPanel": {
                "description": "Панель быстрых фильтров",
                "properties": ["background", "padding"],
                "example": ".hsFastFiltersPanel { background: #f5f5f5; }"
            },
            ".hsFastFilter": {
                "description": "Быстрый фильтр (чип)",
                "properties": ["background", "border-radius", "padding"],
                "example": ".hsFastFilter { background: #e3f2fd; border-radius: 16px; }"
            },
            ".hsFiltersSelector": {
                "description": "Селектор фильтров",
                "properties": ["background"],
                "example": ".hsFiltersSelector { background: #fff; }"
            },
            ".hsFilterSelect": {
                "description": "Выпадающий фильтр",
                "properties": ["border", "border-radius"],
                "example": ".hsFilterSelect { border: 1px solid #ccc; border-radius: 4px; }"
            },
            ".hsFilterRange": {
                "description": "Диапазон фильтра",
                "properties": ["background"],
                "example": ".hsFilterRange { background: #fff; }"
            },
            ".FilterTitle": {
                "description": "Заголовок фильтра",
                "properties": ["color", "font-weight"],
                "example": ".FilterTitle { color: #333; font-weight: 600; }"
            },
            ".view-global-filter-block": {
                "description": "Блок глобального фильтра",
                "properties": ["background"],
                "example": ".view-global-filter-block { background: #f5f5f5; }"
            },
            ".datePicker": {
                "description": "Контейнер датапикера",
                "properties": ["background"],
                "example": ".datePicker { background: #fff; }"
            },
            ".datePicker.period": {
                "description": "Датапикер периода (от-до)",
                "properties": ["background"],
                "example": ".datePicker.period { background: #fff; }"
            },
            ".r-ss-wrap": {
                "description": "Обёртка react-super-select",
                "properties": ["border", "border-radius", "background"],
                "example": ".r-ss-wrap { border: 2px solid #cbd5e1; border-radius: 8px; }"
            },
            ".r-ss-trigger": {
                "description": "Триггер (кнопка) комбобокса",
                "properties": ["background", "padding"],
                "example": ".r-ss-trigger { background: #fff; padding: 8px 12px; }"
            },
            ".r-ss-selection-clear": {
                "description": "Кнопка очистки выбора",
                "properties": ["color"],
                "example": ".r-ss-selection-clear { color: #666; }"
            },
            ".hsMultiselect": {
                "description": "Мультиселект",
                "properties": ["border", "border-radius"],
                "example": ".hsMultiselect { border: 1px solid #ccc; }"
            }
        },
        "grid": {
            ".react-grid-layout": {
                "description": "Сетка расположения компонентов",
                "properties": ["background", "min-height", "padding"],
                "example": ".react-grid-layout { background: linear-gradient(145deg, #f8fafc, #eef4f8); padding: 20px; }"
            },
            ".hsGridLayout": {
                "description": "Сетка ModusBI",
                "properties": ["background"],
                "example": ".hsGridLayout { background: #fafafa; }"
            },
            ".react-grid-item": {
                "description": "Элемент сетки (контейнер компонента)",
                "properties": ["border", "border-radius", "box-shadow", "transition", "overflow"],
                "example": ".react-grid-item { border-radius: 14px; box-shadow: 0 2px 12px rgba(30,58,95,0.08); }"
            },
            ".react-grid-item:hover": {
                "description": "Элемент сетки при наведении (⚠️ НЕ используйте transform - вызывает скачки!)",
                "properties": ["box-shadow", "border-color"],
                "example": ".react-grid-item:hover { box-shadow: 0 8px 24px rgba(30,58,95,0.15); border-color: #38bdf8; }"
            },
            ".hsGridPanel": {
                "description": "Панель сетки ModusBI",
                "properties": ["background"],
                "example": ".hsGridPanel { background: #fff; }"
            },
            ".react-grid-placeholder": {
                "description": "Плейсхолдер при перетаскивании",
                "properties": ["background", "opacity"],
                "example": ".react-grid-placeholder { background: #2196F3; opacity: 0.3; }"
            },
            ".flippable": {
                "description": "Переворачиваемый элемент",
                "properties": [],
                "example": "Добавляется к элементам с flip-анимацией"
            },
            ".hsGridContainer": {
                "description": "Контейнер сетки",
                "properties": ["background"],
                "example": ".hsGridContainer { background: #fafafa; }"
            },
            ".hsGridPanelContainer": {
                "description": "Контейнер панели сетки",
                "properties": ["background"],
                "example": ".hsGridPanelContainer { background: #fff; }"
            }
        },
        "page_container": {
            ".HsPageContainer": {
                "description": "Контейнер страниц (frontSide)",
                "properties": ["background"],
                "example": ".HsPageContainer { background: #fff; }"
            },
            ".hsPageContainer": {
                "description": "Внутренний контейнер страниц",
                "properties": ["background"],
                "example": ".hsPageContainer { background: #fff; }"
            },
            ".CustomizePageContainer": {
                "description": "Кастомизируемый контейнер страниц",
                "properties": ["background"],
                "example": ".CustomizePageContainer { background: #fff; }"
            },
            ".CustomizePageContainerTabs": {
                "description": "Вкладки контейнера страниц",
                "properties": ["background"],
                "example": ".CustomizePageContainerTabs { background: #f5f5f5; }"
            },
            ".CustomizePageContainerTab": {
                "description": "Вкладка контейнера страниц",
                "properties": ["background", "color", "padding"],
                "example": ".CustomizePageContainerTab { background: #fff; padding: 8px 16px; }"
            },
            ".hsTab": {
                "description": "Вкладка ModusBI",
                "properties": ["background", "color", "padding"],
                "example": ".hsTab { background: #fff; }"
            },
            ".contentHeader": {
                "description": "Заголовок контента",
                "properties": ["background"],
                "example": ".contentHeader { background: #f5f5f5; }"
            },
            ".contentContainer": {
                "description": "Контейнер контента",
                "properties": ["background"],
                "example": ".contentContainer { background: #fff; }"
            }
        },
        "icons": {
            ".hsToolIcon": {
                "description": "Базовый класс иконки инструмента",
                "properties": ["color", "cursor"],
                "example": ".hsToolIcon { color: #666; cursor: pointer; }"
            },
            ".hsMaximizeComponent": {
                "description": "Иконка развернуть на весь экран",
                "properties": ["color"],
                "example": ".hsMaximizeComponent { color: #fbbf24; }"
            },
            ".hsDrillDownIcon": {
                "description": "Иконка drill-down",
                "properties": ["color"],
                "example": ".hsDrillDownIcon { color: #666; }"
            },
            ".hsControlPanelIcon": {
                "description": "Иконка контрольной панели",
                "properties": ["color"],
                "example": ".hsControlPanelIcon { color: #666; }"
            },
            ".HsIconMenuButton": {
                "description": "Кнопка меню с иконкой",
                "properties": ["color"],
                "example": ".HsIconMenuButton { color: #666; }"
            }
        },
        "text_block": {
            ".HsTextBlock": {
                "description": "Текстовый блок (frontSide)",
                "properties": ["background"],
                "example": ".HsTextBlock { background: #fff; }"
            },
            ".hsTextBlock": {
                "description": "Внутренний контейнер текстового блока",
                "properties": ["background", "padding"],
                "example": ".hsTextBlock { background: #fff; padding: 16px; }"
            }
        },
        "mui": {
            ".MuiButton-root": {
                "description": "Базовая кнопка MUI",
                "properties": ["background", "color", "border-radius"],
                "example": ".MuiButton-root { border-radius: 8px; }"
            },
            ".MuiButton-containedPrimary": {
                "description": "Основная заполненная кнопка MUI",
                "properties": ["background", "box-shadow"],
                "example": ".MuiButton-containedPrimary { background: linear-gradient(135deg, #6366f1, #8b5cf6); }"
            },
            ".MuiButton-outlined": {
                "description": "Обведённая кнопка MUI",
                "properties": ["border", "color"],
                "example": ".MuiButton-outlined { border: 2px solid #6366f1; }"
            },
            ".MuiIconButton-root": {
                "description": "Кнопка-иконка MUI",
                "properties": ["color"],
                "example": ".MuiIconButton-root { color: #666; }"
            },
            "[role=\"tablist\"]": {
                "description": "Контейнер вкладок MUI",
                "properties": ["background", "border-radius", "padding"],
                "example": "[role=\"tablist\"] { background: #f1f5f9; border-radius: 10px; }"
            },
            "[role=\"tab\"]": {
                "description": "Вкладка MUI",
                "properties": ["background", "color", "border-radius", "padding"],
                "example": "[role=\"tab\"] { background: transparent; color: #64748b; }"
            },
            "[role=\"tab\"][aria-selected=\"true\"]": {
                "description": "Активная вкладка MUI",
                "properties": ["background", "color", "box-shadow"],
                "example": "[role=\"tab\"][aria-selected=\"true\"] { background: linear-gradient(135deg, #6366f1, #8b5cf6); color: #fff; }"
            },
            ".tabButton": {
                "description": "Кнопка вкладки ModusBI",
                "properties": ["background", "color"],
                "example": ".tabButton { background: transparent; }"
            },
            ".MuiCheckbox-root": {
                "description": "Чекбокс MUI",
                "properties": ["color"],
                "example": ".MuiCheckbox-root { color: #6366f1; }"
            }
        },
        "scrollbar": {
            "::-webkit-scrollbar": {
                "description": "Скроллбар (webkit)",
                "properties": ["width", "height"],
                "example": "::-webkit-scrollbar { width: 10px; height: 10px; }"
            },
            "::-webkit-scrollbar-track": {
                "description": "Трек скроллбара",
                "properties": ["background", "border-radius"],
                "example": "::-webkit-scrollbar-track { background: #f1f5f9; border-radius: 5px; }"
            },
            "::-webkit-scrollbar-thumb": {
                "description": "Ползунок скроллбара",
                "properties": ["background", "border-radius", "border"],
                "example": "::-webkit-scrollbar-thumb { background: linear-gradient(180deg, #94a3b8, #64748b); border-radius: 5px; }"
            },
            "::-webkit-scrollbar-thumb:hover": {
                "description": "Ползунок при наведении",
                "properties": ["background"],
                "example": "::-webkit-scrollbar-thumb:hover { background: linear-gradient(180deg, #64748b, #475569); }"
            }
        }
    }
    
    # Примеры стилизации
    CSS_EXAMPLES = {
        "headers": {
            "blue_header": {
                "name": "Синий заголовок",
                "css": """.componentHeader {
    background: linear-gradient(135deg, #1976D2, #2196F3);
    color: white;
    font-weight: 600;
    padding: 12px 16px;
    border-radius: 4px 4px 0 0;
}"""
            },
            "dark_header": {
                "name": "Тёмный заголовок",
                "css": """.componentHeader {
    background: #263238;
    color: #eceff1;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}"""
            },
            "gradient_header": {
                "name": "Градиентный заголовок (фиолетовый)",
                "css": """.componentHeader {
    background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 50%, #8b5cf6 100%);
    color: white;
    padding: 14px 20px;
    font-size: 13px;
    text-transform: uppercase;
    letter-spacing: 0.4px;
}"""
            },
            "report_header_dark": {
                "name": "Тёмная шапка отчёта",
                "css": """.hsHeader,
.hsHeader.hsHeader__report {
    background: linear-gradient(135deg, #1a1f36 0%, #2d3555 100%) !important;
    border-bottom: 4px solid transparent !important;
    border-image: linear-gradient(90deg, #f59e0b, #ec4899, #8b5cf6) 1 !important;
}

.hsHeader h1 {
    color: #ffffff !important;
    font-weight: 700 !important;
}

.hsHeader button {
    background: rgba(255, 255, 255, 0.08) !important;
    border: 1px solid rgba(255, 255, 255, 0.15) !important;
    border-radius: 10px !important;
}

.hsHeader button img {
    filter: brightness(0) invert(1) !important;
}"""
            }
        },
        "tables": {
            "modern_table": {
                "name": "Современная таблица",
                "css": """.hs-table__main {
    border-radius: 10px !important;
    overflow: hidden !important;
    border: 1px solid #e2e8f0 !important;
}

.hs-table__table th {
    background: linear-gradient(180deg, #334155 0%, #1e293b 100%) !important;
    color: #f1f5f9 !important;
    padding: 14px 16px !important;
    font-weight: 600 !important;
    font-size: 12px !important;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    border-bottom: 3px solid #8b5cf6 !important;
}

.hs-table__table td {
    padding: 12px 16px !important;
    border-bottom: 1px solid #e2e8f0 !important;
    color: #334155 !important;
}

.hs-table__table tr:nth-child(even) td {
    background: #fafbfc !important;
}

.hs-table__table tr:hover td {
    background: linear-gradient(90deg, #ecfdf5, #d1fae5) !important;
    color: #065f46 !important;
}"""
            },
            "striped_table": {
                "name": "Полосатая таблица",
                "css": """.hs-table__table tr:nth-child(even) td {
    background: #f5f5f5;
}
.hs-table__table tr:nth-child(odd) td {
    background: white;
}
.hs-table__table th {
    background: #37474f;
    color: white;
}"""
            },
            "table_with_totals": {
                "name": "Таблица с итогами",
                "css": """.hs-table__table tfoot tr td {
    background: linear-gradient(180deg, #fef3c7 0%, #fde68a 100%) !important;
    color: #92400e !important;
    font-weight: 700 !important;
    border-top: 2px solid #f59e0b !important;
}"""
            }
        },
        "charts": {
            "chart_with_shadow": {
                "name": "Диаграмма с тенью",
                "css": """.HsPieAMchartsChart {
    background: white;
    border-radius: 8px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.1);
}
.componentHeader {
    background: #fff;
    color: #333;
    border-bottom: 2px solid #2196F3;
}"""
            },
            "dark_chart": {
                "name": "Тёмная тема",
                "css": """.HsPieAMchartsChart {
    background: #1e1e1e;
}
.amcharts-legend-label {
    fill: #e0e0e0 !important;
}
.componentHeader {
    background: #2d2d2d;
    color: #fff;
}"""
            }
        },
        "maps": {
            "tilemap_no_gray": {
                "name": "Плиточная карта без серых плиток",
                "css": """[class*="tilemap"] svg rect {
    rx: 3 !important;
    stroke: #ffffff !important;
    stroke-width: 1.5 !important;
}

[class*="tilemap"] svg rect[fill="#cccccc"],
[class*="tilemap"] svg rect[fill="#ccc"],
[class*="tilemap"] svg rect[fill="gray"] {
    fill: #e0f2fe !important;
}

[class*="tilemap"] [class*="legend"] {
    background: linear-gradient(135deg, #f8fafc, #f1f5f9) !important;
    border-radius: 8px !important;
    padding: 10px 14px !important;
}"""
            }
        },
        "grid": {
            "modern_grid": {
                "name": "Современная сетка",
                "css": """.react-grid-layout {
    background: linear-gradient(145deg, #f8fafc 0%, #eef4f8 100%) !important;
    min-height: 100vh;
    padding: 20px !important;
}

.react-grid-item {
    border-radius: 14px !important;
    box-shadow: 0 2px 12px rgba(30, 58, 95, 0.08) !important;
    transition: box-shadow 0.3s ease, border-color 0.3s ease !important;
    overflow: hidden !important;
    border: 1px solid rgba(200, 215, 230, 0.5) !important;
}

.react-grid-item:hover {
    box-shadow: 0 8px 24px rgba(30, 58, 95, 0.15) !important;
    border-color: #38bdf8 !important;
}

.componentContainer {
    border: none !important;
    border-radius: 14px !important;
    background: #ffffff !important;
}"""
            }
        },
        "filters": {
            "modern_filters": {
                "name": "Современные фильтры",
                "css": """.FilterControlPanel,
.HsFilterControlPanel {
    background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%) !important;
    border-bottom: 1px solid #e2e8f0 !important;
}

.FilterControlPanel input,
.FilterControlPanel select {
    border: 2px solid #cbd5e1 !important;
    border-radius: 8px !important;
    padding: 10px 14px !important;
    background: #ffffff !important;
    color: #334155 !important;
}

.FilterControlPanel input:focus,
.FilterControlPanel select:focus {
    border-color: #8b5cf6 !important;
    box-shadow: 0 0 0 4px rgba(139, 92, 246, 0.15) !important;
    outline: none !important;
}

.r-ss-wrap,
.hsMultiselect {
    border: 2px solid #cbd5e1 !important;
    border-radius: 8px !important;
}

.r-ss-wrap:hover {
    border-color: #8b5cf6 !important;
}"""
            }
        },
        "colors": {
            "corporate_blue": {
                "name": "Корпоративный синий",
                "css": """.componentHeader {
    background: #0d47a1;
    color: white;
}
.hs-table__table th {
    background: #1565c0;
    color: white;
}
.hs-table__table tr:hover td {
    background: #bbdefb;
}"""
            },
            "green_theme": {
                "name": "Зелёная тема",
                "css": """.componentHeader {
    background: #2e7d32;
    color: white;
}
.hs-table__table th {
    background: #388e3c;
    color: white;
}
.hs-table__table tr:hover td {
    background: #c8e6c9;
}"""
            },
            "purple_theme": {
                "name": "Фиолетовая тема",
                "css": """.componentHeader {
    background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%);
    color: white;
}
.hs-table__table th {
    background: linear-gradient(180deg, #334155 0%, #1e293b 100%);
    color: #f1f5f9;
    border-bottom: 3px solid #8b5cf6;
}"""
            }
        },
        "icons": {
            "golden_icons": {
                "name": "Золотые иконки в заголовках",
                "css": """.componentHeader img,
.componentHeader svg,
.componentHeader [class*="icon"] {
    filter: brightness(0) saturate(100%) invert(85%) sepia(60%) saturate(500%) hue-rotate(10deg) brightness(105%) !important;
}

.hsMaximizeComponent {
    color: #fbbf24 !important;
}

.hsMaximizeComponent:hover {
    color: #f59e0b !important;
}"""
            },
            "white_header_icons": {
                "name": "Белые иконки в шапке",
                "css": """.hsHeader button img {
    width: 22px !important;
    height: 22px !important;
    filter: brightness(0) invert(1) !important;
}

.hsHeader button:hover img {
    filter: brightness(0) invert(1) drop-shadow(0 0 6px rgba(255, 255, 255, 0.6)) !important;
}"""
            },
            "colored_logo": {
                "name": "Цветной логотип в шапке",
                "css": """.hsLogo {
    background-color: #3d8bfd !important;
    border-radius: 8px !important;
}

.hsLogo svg {
    filter: brightness(0) invert(1) !important;
}

.hsLogo:hover {
    background-color: #2563eb !important;
    box-shadow: 0 0 12px rgba(59, 130, 246, 0.5) !important;
}"""
            }
        },
        "scrollbar": {
            "custom_scrollbar": {
                "name": "Кастомный скроллбар",
                "css": """::-webkit-scrollbar {
    width: 10px;
    height: 10px;
}

::-webkit-scrollbar-track {
    background: #f1f5f9;
    border-radius: 5px;
}

::-webkit-scrollbar-thumb {
    background: linear-gradient(180deg, #94a3b8 0%, #64748b 100%);
    border-radius: 5px;
    border: 2px solid #f1f5f9;
}

::-webkit-scrollbar-thumb:hover {
    background: linear-gradient(180deg, #64748b 0%, #475569 100%);
}"""
            }
        },
        "animations": {
            "fade_in": {
                "name": "Анимация появления (только opacity, без transform)",
                "css": """@keyframes fadeIn {
    from { opacity: 0; }
    to { opacity: 1; }
}

.react-grid-item {
    animation: fadeIn 0.4s ease-out;
}"""
            }
        },
        "specific_component": {
            "single_component_header": {
                "name": "Стиль заголовка одного компонента",
                "description": "Используйте #panel_N где N — индекс компонента из get_report_components()",
                "css": """/* Стилизация только компонента с индексом 0 */
#panel_0 .componentHeader {
    background: linear-gradient(135deg, #dc2626, #b91c1c) !important;
    color: white !important;
}

#panel_0 .componentBody {
    border: 2px solid #dc2626 !important;
}"""
            },
            "single_chart_labels": {
                "name": "Подписи осей конкретной диаграммы",
                "description": "Для SVG-элементов используйте fill вместо color",
                "css": """/* Красные подписи осей только для диаграммы panel_8 */
#panel_8 .amcharts-axis-label > TSPAN {
    fill: #FF0000 !important;
}

/* Изменить цвет столбцов диаграммы */
#panel_8 .amcharts-graph-column {
    fill: #10b981 !important;
}"""
            },
            "single_table_style": {
                "name": "Стиль конкретной таблицы",
                "description": "Применяется только к таблице с указанным panel_N",
                "css": """/* Особый стиль для таблицы panel_3 */
#panel_3 .hs-table__table th {
    background: linear-gradient(180deg, #1e40af, #1e3a8a) !important;
    color: white !important;
}

#panel_3 .hs-table__table tr:nth-child(even) td {
    background: #dbeafe !important;
}

#panel_3 .hs-table__table tr:hover td {
    background: #93c5fd !important;
}"""
            }
        }
    }
    
    def get_classes(self, category: str = "all") -> dict[str, Any]:
        """
        Получает справочник CSS классов.
        
        Args:
            category: Категория (all, header, selectors, components, tables, charts, maps, pivot, filters, grid, page_container, icons, text_block, mui, scrollbar)
            
        Returns:
            Справочник классов с описаниями
        """
        if category == "all":
            return {
                "categories": list(self.CSS_CLASSES.keys()),
                "classes": self.CSS_CLASSES,
                "total_classes": sum(len(v) for v in self.CSS_CLASSES.values()),
                "hint": "Используйте category='<название>' для получения конкретной категории"
            }
        
        if category not in self.CSS_CLASSES:
            return {
                "error": f"Неизвестная категория: {category}",
                "available": list(self.CSS_CLASSES.keys())
            }
        
        return {
            "category": category,
            "classes": self.CSS_CLASSES[category],
            "total": len(self.CSS_CLASSES[category])
        }
    
    def get_examples(self, category: str = "all") -> dict[str, Any]:
        """
        Получает примеры CSS стилизации.
        
        Args:
            category: Категория примеров
            
        Returns:
            Примеры с CSS кодом
        """
        if category == "all":
            return {
                "categories": list(self.CSS_EXAMPLES.keys()),
                "examples": self.CSS_EXAMPLES,
                "hint": "Используйте category='<название>' для получения конкретной категории"
            }
        
        if category not in self.CSS_EXAMPLES:
            return {
                "error": f"Неизвестная категория: {category}",
                "available": list(self.CSS_EXAMPLES.keys())
            }
        
        return {
            "category": category,
            "examples": self.CSS_EXAMPLES[category]
        }
    
    def validate_css(self, css: str) -> dict[str, Any]:
        """
        Проверяет валидность CSS кода.
        
        Args:
            css: CSS код для проверки
            
        Returns:
            Результат валидации
        """
        errors = []
        warnings = []
        known_classes_used = []

        # validate ≠ security — CSS уходит в браузер verbatim (Go-сторона
        # не санитайзит). Эвристика опасных конструкций → warning (не error,
        # т.к. возможны легитимные false-positive в строках/url).
        _danger = [
            ("javascript:", "javascript:-URL внутри CSS"),
            ("<script", "HTML <script> внутри CSS"),
            ("expression(", "IE expression() — исполнение JS"),
            ("@import", "@import — подгрузка внешнего CSS"),
            ("behavior:", "IE behavior: — подключение HTC"),
            ("data:text/html", "data:text/html URL"),
        ]
        _low = css.lower()
        for _needle, _what in _danger:
            if _needle in _low:
                warnings.append(
                    f"⚠️ Потенциально опасная конструкция: {_what}. "
                    f"validate НЕ является security-фильтром — CSS попадает "
                    f"в браузер без санитайза."
                )

        # Базовая проверка синтаксиса
        # Проверяем сбалансированность скобок
        if css.count('{') != css.count('}'):
            errors.append("Несбалансированные фигурные скобки { }")
        
        # Ищем использованные селекторы
        selector_pattern = r'([.#][\w-]+)'
        selectors = re.findall(selector_pattern, css)
        
        # Собираем все известные классы
        all_known_classes = set()
        for category in self.CSS_CLASSES.values():
            for class_name in category.keys():
                # Извлекаем имя класса без псевдоселекторов
                base_class = class_name.split(':')[0].split(' ')[0]
                if base_class.startswith('.'):
                    all_known_classes.add(base_class)
        
        # Проверяем использованные селекторы
        for selector in set(selectors):
            if selector.startswith('.'):
                if selector in all_known_classes:
                    known_classes_used.append(selector)
                else:
                    warnings.append(f"Класс {selector} не найден в справочнике ModusBI (может быть кастомным)")
        
        # Проверка на потенциально опасные свойства
        dangerous_patterns = [
            (r'position\s*:\s*fixed', "position: fixed может нарушить layout"),
            (r'z-index\s*:\s*\d{4,}', "Высокий z-index может перекрыть интерфейс"),
            (r'display\s*:\s*none', "display: none скроет элементы"),
        ]
        
        for pattern, message in dangerous_patterns:
            if re.search(pattern, css, re.IGNORECASE):
                warnings.append(message)
        
        is_valid = len(errors) == 0
        
        return {
            "valid": is_valid,
            "errors": errors,
            "warnings": warnings,
            "selectors_found": list(set(selectors)),
            "known_classes_used": known_classes_used,
            "hint": "Используйте get_css_classes() для просмотра всех доступных классов" if not known_classes_used else None
        }
