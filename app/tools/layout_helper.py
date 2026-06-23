"""
Layout helper для автоматического позиционирования компонентов на дашборде.
"""

from typing import Any

from ..core.validation import sanitize_html


async def get_max_y_position(client, report_id: int) -> int:
    """
    Найти максимальную Y координату в отчете.

    Args:
        client: InstanceClient
        report_id: ID отчета

    Returns:
        Максимальная Y позиция (где можно добавить следующий компонент)
    """
    # Получить отчет
    response = await client.api_call("reports", "get", object_id=report_id)

    if response.get("status") != 200:
        return 0

    data = response.get("data", [])
    if not data:
        return 0

    report = data[0]
    grid = report.get("grid", {})
    layouts = grid.get("layouts", {})

    # Проверяем layout для "lg" (основной breakpoint)
    lg_layout = layouts.get("lg", [])

    max_y = 0
    for item in lg_layout:
        if isinstance(item, dict):
            item_bottom = item.get("y", 0) + item.get("h", 0)
            max_y = max(max_y, item_bottom)

    return max_y


def calculate_chart_text_pair_positions(
    current_max_y: int,
    chart_width: int = 12,
    text_width: int = 12,
    row_height: int = 16
) -> tuple[dict, dict]:
    """
    Вычислить позиции для пары: график слева + текстовый блок справа.

    Args:
        current_max_y: Текущая максимальная Y координата
        chart_width: Ширина графика (по умолчанию 12 из 24)
        text_width: Ширина текстового блока (по умолчанию 12 из 24)
        row_height: Высота строки (по умолчанию 16)

    Returns:
        (chart_position, text_position)

    Example:
        chart_pos, text_pos = calculate_chart_text_pair_positions(max_y=30, row_height=16)
        # chart_pos = {"x": 0, "y": 30, "w": 12, "h": 16}
        # text_pos  = {"x": 12, "y": 30, "w": 12, "h": 16}
    """
    chart_position = {
        "x": 0,
        "y": current_max_y,
        "w": chart_width,
        "h": row_height
    }

    text_position = {
        "x": chart_width,
        "y": current_max_y,
        "w": text_width,
        "h": row_height
    }

    return chart_position, text_position


def calculate_full_width_position(
    current_max_y: int,
    height: int = 16
) -> dict:
    """
    Вычислить позицию для компонента на всю ширину.

    Args:
        current_max_y: Текущая максимальная Y координата
        height: Высота компонента

    Returns:
        Position dict

    Example:
        pos = calculate_full_width_position(max_y=50, height=20)
        # pos = {"x": 0, "y": 50, "w": 24, "h": 20}
    """
    return {
        "x": 0,
        "y": current_max_y,
        "w": 24,
        "h": height
    }


def calculate_text_block_height(html_content: str) -> int:
    """
    Умное вычисление высоты для текстового блока.

    Анализирует HTML контент и оценивает необходимую высоту.

    Args:
        html_content: HTML контент текстового блока

    Returns:
        Рекомендуемая высота (от 18 до 30 единиц)

    Algorithm:
        - h1: +3 единицы
        - h2: +2.5 единицы
        - h3: +2 единицы
        - p:  +2 единицы
        - div: +1 единица
        - Минимум: 18 единиц
        - Максимум: 30 единиц
    """
    min_height = 18
    max_height = 30

    # Подсчет элементов
    h1_count = html_content.count('<h1')
    h2_count = html_content.count('<h2')
    h3_count = html_content.count('<h3')
    p_count = html_content.count('<p')
    div_count = html_content.count('<div')

    # Вычисление высоты
    height = min_height
    height += h1_count * 3
    height += h2_count * 2.5
    height += h3_count * 2
    height += p_count * 2
    height += div_count * 1

    # Ограничение диапазона
    height = max(min_height, min(max_height, int(height)))

    return height


async def add_chart_with_text_pair(
    client,
    report_id: int,
    chart_config: dict,
    text_html: str,
    text_title: str = "Вывод",
    row_height: int | None = None
) -> dict[str, Any]:
    """
    Добавить пару: график слева + текстовый блок с выводом справа.

    Автоматически вычисляет позиции для размещения компонентов рядом.

    Args:
        client: InstanceClient
        report_id: ID отчета
        chart_config: Конфигурация графика
            {
                "type": "HsBarAMchartsChart",
                "title": "Продажи по регионам",
                "dataset_id": 5,
                "category_field": "region",
                "value_field": "amount",
                "aggregation": "avg"
            }
        text_html: HTML контент для текстового блока
        text_title: Заголовок текстового блока
        row_height: Высота строки (если None - автоматически вычисляется)

    Returns:
        {
            "success": True,
            "chart_idx": "X",
            "text_idx": "Y",
            "y_position": Z,
            "row_height": H
        }

    Example:
        add_chart_with_text_pair(
            client,
            report_id=35,
            chart_config={
                "type": "HsBarAMchartsChart",
                "title": "Продажи по регионам",
                "dataset_id": 5,
                "category_field": "region",
                "value_field": "amount"
            },
            text_html="<div>Вывод по графику...</div>",
            row_height=16
        )
    """
    from .component_crud import _add_component
    from .text_block_helper import add_text_block_component

    # XSS: add_text_block_component санитизирует и сам, но режем и
    # здесь — чтобы calculate_text_block_height считал высоту уже по
    # итоговому HTML (вырезанный <script> не должен раздувать row_height).
    text_html = sanitize_html(text_html)
    text_title = sanitize_html(text_title)

    # 1. Найти максимальную Y позицию
    max_y = await get_max_y_position(client, report_id)

    # 2. Вычислить высоту если не указана
    if row_height is None:
        row_height = calculate_text_block_height(text_html)
        row_height = max(16, row_height)  # Минимум 16 для графика

    # 3. Вычислить позиции
    chart_pos, text_pos = calculate_chart_text_pair_positions(
        current_max_y=max_y,
        chart_width=12,
        text_width=12,
        row_height=row_height
    )

    # 4. Добавить график
    chart_result = await _add_component(
        client=client,
        report_id=report_id,
        component_type=chart_config.get("type", "HsBarAMchartsChart"),
        title=chart_config.get("title", "График"),
        value_field=chart_config.get("value_field", ""),
        dataset_id=chart_config.get("dataset_id"),
        category_field=chart_config.get("category_field", ""),
        aggregation=chart_config.get("aggregation", "max"),  # Safe default for pre-aggregated
        position=chart_pos
    )

    if not chart_result.get("success"):
        return {
            "success": False,
            "error": f"Failed to add chart: {chart_result.get('error')}",
            "step": "add_chart"
        }

    # 5. Добавить текстовый блок
    text_result = await add_text_block_component(
        client=client,
        report_id=report_id,
        title=text_title,
        text_content=text_html,
        position=text_pos
    )

    if not text_result.get("success"):
        return {
            "success": False,
            "error": f"Failed to add text block: {text_result.get('error')}",
            "step": "add_text"
        }

    return {
        "success": True,
        "message": "Chart and text block pair added successfully",
        "chart_idx": chart_result.get("component", {}).get("idx"),
        "text_idx": text_result.get("component", {}).get("idx"),
        "y_position": max_y,
        "row_height": row_height
    }
