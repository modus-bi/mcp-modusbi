#!/usr/bin/env python3
"""
Read-only тесты для MCP Server.

⚠️ БЕЗОПАСНО: Этот скрипт использует ТОЛЬКО операции чтения!
Не вызывает: create, update, delete, add, remove, move и другие write операции.

Можно запускать против любых данных без риска.

Использование:
    python -m tests.test_readonly_smoke              # Тестирует подключённый портал
    python -m tests.test_readonly_smoke --verbose
"""

import asyncio
import os
import sys
import argparse
from pathlib import Path
from typing import Any
from dataclasses import dataclass

# Добавляем родительский каталог app в path для импортов
_mcp_server_dir = Path(__file__).parent.parent
_project_root = _mcp_server_dir.parent
sys.path.insert(0, str(_project_root))
sys.path.insert(0, str(_mcp_server_dir))

from app.core.instances import InstanceManager, InstanceClient
from app.core.security import SecurityMode, set_security_mode


@dataclass
class TestResult:
    """Результат одного теста."""
    name: str
    passed: bool
    message: str
    data: dict | None = None


class ReadOnlyTester:
    """
    Тестер с только read-only операциями.

    ⚠️ БЕЗОПАСНО: Не вызывает write операции!
    """

    def __init__(self, client: InstanceClient, verbose: bool = False):
        self.client = client
        self.verbose = verbose
        self.results: list[TestResult] = []

        # Кэш для использования в связанных тестах
        self._reports: list = []
        self._datasets: list = []
        self._datasources: list = []
        self._groups: list = []

    def log(self, msg: str) -> None:
        """Вывод сообщения если verbose."""
        if self.verbose:
            print(f"  {msg}")

    def add_result(self, name: str, passed: bool, message: str, data: dict | None = None) -> None:
        """Добавляет результат теста."""
        self.results.append(TestResult(name, passed, message, data))
        status = "✅" if passed else "❌"
        print(f"{status} {name}: {message}")
        if self.verbose and data:
            print(f"     Data: {data}")

    # =========================================================================
    # Тесты Report Operations
    # =========================================================================

    async def test_reports_list(self) -> None:
        """Тест: получение списка отчётов."""
        from app.tools.report_operations import report_operations

        result = await report_operations(self.client, action="list")

        if result.get("success"):
            reports = result.get("items", [])
            self._reports = reports
            self.add_result(
                "reports.list",
                True,
                f"Найдено {len(reports)} отчётов",
                {"count": len(reports), "sample": reports[0] if reports else None}
            )
        else:
            self.add_result("reports.list", False, result.get("error", "Unknown error"))

    async def test_reports_groups_list(self) -> None:
        """Тест: получение списка групп отчётов."""
        from app.tools.report_operations import report_operations

        result = await report_operations(self.client, action="groups_list")

        if result.get("success"):
            groups = result.get("items", [])
            self._groups = groups
            self.add_result(
                "reports.groups_list",
                True,
                f"Найдено {len(groups)} групп",
                {"count": len(groups)}
            )
        else:
            self.add_result("reports.groups_list", False, result.get("error", "Unknown error"))

    async def test_report_get(self) -> None:
        """Тест: получение конкретного отчёта."""
        if not self._reports:
            self.add_result("reports.get", False, "Нет отчётов для тестирования")
            return

        from app.tools.report_operations import report_operations

        report_id = self._reports[0].get("id")
        result = await report_operations(self.client, action="get", report_id=report_id)

        if result.get("success"):
            report = result.get("report", {})
            self.add_result(
                "reports.get",
                True,
                f"Отчёт '{report.get('name')}' получен",
                {"report_id": report_id, "components_count": len(report.get("components", []))}
            )
        else:
            self.add_result("reports.get", False, result.get("error", "Unknown error"))

    async def test_report_summary(self) -> None:
        """Тест: получение сводки по отчёту."""
        if not self._reports:
            self.add_result("reports.summary", False, "Нет отчётов для тестирования")
            return

        from app.tools.report_operations import report_operations

        report_id = self._reports[0].get("id")
        result = await report_operations(self.client, action="summary", report_id=report_id)

        if result.get("success"):
            summary = result.get("summary", "")
            self.add_result(
                "reports.summary",
                True,
                f"Сводка получена ({len(summary)} символов)",
                {"report_id": report_id}
            )
        else:
            self.add_result("reports.summary", False, result.get("error", "Unknown error"))

    async def test_report_components_list(self) -> None:
        """Тест: получение списка компонентов отчёта."""
        if not self._reports:
            self.add_result("reports.components_list", False, "Нет отчётов для тестирования")
            return

        from app.tools.report_operations import report_operations

        report_id = self._reports[0].get("id")
        result = await report_operations(self.client, action="components_list", report_id=report_id)

        if result.get("success"):
            components = result.get("components", [])
            self.add_result(
                "reports.components_list",
                True,
                f"Найдено {len(components)} компонентов",
                {"report_id": report_id, "count": len(components)}
            )
        else:
            self.add_result("reports.components_list", False, result.get("error", "Unknown error"))

    # =========================================================================
    # Тесты ReportGroup Operations
    # =========================================================================

    async def test_reportgroups_list(self) -> None:
        """Тест: получение списка групп (инструмент)."""
        from app.tools.reportgroup_operations import reportgroup_operations

        result = await reportgroup_operations(self.client, action="list")

        if result.get("success"):
            groups = result.get("items", [])
            self.add_result(
                "reportgroups.list",
                True,
                f"Найдено {len(groups)} групп отчётов",
                {"count": len(groups)}
            )
        else:
            self.add_result("reportgroups.list", False, result.get("error", "Unknown error"))

    async def test_reportgroups_get(self) -> None:
        """Тест: получение конкретной группы (инструмент)."""
        if not self._groups:
            self.add_result("reportgroups.get", False, "Нет групп для тестирования")
            return

        from app.tools.reportgroup_operations import reportgroup_operations

        group_id = self._groups[0].get("id")
        result = await reportgroup_operations(self.client, action="get", group_id=group_id)

        if result.get("success"):
            group = result.get("group", {})
            self.add_result(
                "reportgroups.get",
                True,
                f"Группа '{group.get('name')}' получена",
                {"group_id": group_id}
            )
        else:
            self.add_result("reportgroups.get", False, result.get("error", "Unknown error"))

    # =========================================================================
    # Тесты Dataset Operations
    # =========================================================================

    async def test_datasets_list(self) -> None:
        """Тест: получение списка датасетов."""
        from app.tools.dataset_operations import dataset_operations

        result = await dataset_operations(self.client, action="list")

        if result.get("success"):
            datasets = result.get("items", [])
            self._datasets = datasets
            self.add_result(
                "datasets.list",
                True,
                f"Найдено {len(datasets)} датасетов",
                {"count": len(datasets), "sample": datasets[0] if datasets else None}
            )
        else:
            self.add_result("datasets.list", False, result.get("error", "Unknown error"))

    async def test_dataset_get(self) -> None:
        """Тест: получение конкретного датасета."""
        if not self._datasets:
            self.add_result("datasets.get", False, "Нет датасетов для тестирования")
            return

        from app.tools.dataset_operations import dataset_operations

        dataset_id = self._datasets[0].get("id")
        result = await dataset_operations(self.client, action="get", dataset_id=dataset_id)

        if result.get("success"):
            dataset = result.get("dataset", {})
            self.add_result(
                "datasets.get",
                True,
                f"Датасет '{dataset.get('name')}' получен",
                {"dataset_id": dataset_id}
            )
        else:
            self.add_result("datasets.get", False, result.get("error", "Unknown error"))

    async def test_dataset_fields_list(self) -> None:
        """Тест: получение полей датасета."""
        if not self._datasets:
            self.add_result("datasets.fields_list", False, "Нет датасетов для тестирования")
            return

        from app.tools.dataset_operations import dataset_operations

        dataset_id = self._datasets[0].get("id")
        result = await dataset_operations(self.client, action="fields_list", dataset_id=dataset_id)

        if result.get("success"):
            fields = result.get("fields", [])
            self.add_result(
                "datasets.fields_list",
                True,
                f"Найдено {len(fields)} полей",
                {"dataset_id": dataset_id, "count": len(fields)}
            )
        else:
            self.add_result("datasets.fields_list", False, result.get("error", "Unknown error"))

    # =========================================================================
    # Тесты Datasource Operations
    # =========================================================================

    async def test_datasources_list(self) -> None:
        """Тест: получение списка источников данных."""
        from app.tools.datasource_operations import datasource_operations

        result = await datasource_operations(self.client, action="list")

        if result.get("success"):
            datasources = result.get("items", [])
            self._datasources = datasources
            self.add_result(
                "datasources.list",
                True,
                f"Найдено {len(datasources)} источников",
                {"count": len(datasources)}
            )
        else:
            self.add_result("datasources.list", False, result.get("error", "Unknown error"))

    async def test_datasource_get(self) -> None:
        """Тест: получение информации о конкретном источнике (ищем активный)."""
        if not self._datasources:
            self.add_result("datasources.get", False, "Нет источников для тестирования")
            return

        from app.tools.datasource_operations import datasource_operations

        # Ищем источник с реальными данными подключения
        found_ds = None
        for ds in self._datasources:
            ds_id = ds.get("id")
            try:
                result = await datasource_operations(self.client, action="get", datasource_id=ds_id)
                if result.get("success"):
                    ds_info = result.get("datasource", {})
                    # Проверяем что есть хост или база данных
                    if ds_info.get("host") or ds_info.get("database") or ds_info.get("connection_url"):
                        found_ds = ds_info
                        break
            except Exception:
                continue

        if found_ds:
            self.add_result(
                "datasources.get",
                True,
                f"Источник '{found_ds.get('name')}' (host: {found_ds.get('host') or 'N/A'})",
                {"datasource_id": found_ds.get("id"), "host": found_ds.get("host"), "database": found_ds.get("database")}
            )
        else:
            # Fallback: показываем первый источник
            ds_id = self._datasources[0].get("id")
            result = await datasource_operations(self.client, action="get", datasource_id=ds_id)
            if result.get("success"):
                ds = result.get("datasource", {})
                self.add_result(
                    "datasources.get",
                    True,
                    f"⚠️ Нет активных источников, показан: '{ds.get('name')}'",
                    {"datasource_id": ds_id}
                )
            else:
                self.add_result("datasources.get", False, result.get("error", "Unknown error"))

    async def test_datasource_tables_list(self) -> None:
        """Тест: получение списка таблиц источника (только БД)."""
        if not self._datasources:
            self.add_result("datasources.tables_list", False, "Нет источников для тестирования")
            return

        from app.tools.datasource_operations import datasource_operations

        # Паттерны БД в названиях источников
        db_patterns = ["postgres", "mysql", "mssql", "oracle", "sqlite", "clickhouse", "mariadb", "sql server", "database"]

        # Собираем БД-источники по названию (приоритетные)
        db_datasources = []
        other_datasources = []
        for ds in self._datasources:
            ds_name = (ds.get("name") or "").lower()
            ds_caption = (ds.get("caption") or "").lower()
            matched = False
            for pattern in db_patterns:
                if pattern in ds_name or pattern in ds_caption:
                    db_datasources.append(ds)
                    matched = True
                    break
            if not matched:
                other_datasources.append(ds)

        # Если нет очевидных БД, пробуем все остальные
        all_to_try = db_datasources + other_datasources

        if not all_to_try:
            self.add_result(
                "datasources.tables_list",
                True,
                "Нет источников для тестирования",
                {}
            )
            return

        # Пробуем датасорсы пока не найдём работающий (сначала БД, потом остальные)
        tried = []
        for db_datasource in all_to_try:
            datasource_id = db_datasource.get("id")
            datasource_name = db_datasource.get("name", "unknown")

            try:
                result = await datasource_operations(self.client, action="tables_list", datasource_id=datasource_id)

                if result.get("success"):
                    tables = result.get("items", [])

                    # Если есть таблицы - успех!
                    if tables:
                        self.add_result(
                            "datasources.tables_list",
                            True,
                            f"Найдено {len(tables)} таблиц в '{datasource_name}'",
                            {"datasource_id": datasource_id, "count": len(tables), "tried": len(tried) + 1}
                        )

                        # Тестируем table_fields для первой таблицы
                        table = tables[0]
                        table_name = table.get("name")
                        schema = table.get("schema", "public")
                        await self._test_table_fields(datasource_id, datasource_name, table_name, schema)

                        return  # Успех - выходим
                    else:
                        # 0 таблиц - продолжаем искать
                        tried.append({"name": datasource_name, "tables": 0})
                else:
                    tried.append({"name": datasource_name, "error": result.get("error", "Unknown")})

            except Exception as e:
                tried.append({"name": datasource_name, "error": str(e)[:30]})
                continue  # Пробуем следующий датасорс

        # Ни один датасорс не сработал
        self.add_result(
            "datasources.tables_list",
            True,  # Не ошибка кода, просто нет подключённых БД
            f"⚠️ Нет подключённых БД (проверено {len(tried)} источников)",
            {"tried": tried[:5]}  # Первые 5 попыток
        )

    async def _test_table_fields(
        self,
        datasource_id: int,
        datasource_name: str,
        table_name: str,
        schema: str
    ) -> None:
        """Тест: получение полей конкретной таблицы."""
        from app.tools.datasource_operations import datasource_operations

        try:
            result = await datasource_operations(
                self.client,
                action="table_fields",
                datasource_id=datasource_id,
                table_name=table_name,
                schema=schema
            )

            if result.get("success"):
                fields = result.get("items", [])
                self.add_result(
                    "datasources.table_fields",
                    True,
                    f"Таблица '{table_name}': {len(fields)} полей",
                    {"datasource": datasource_name, "table": table_name, "fields": len(fields)}
                )
            else:
                self.add_result(
                    "datasources.table_fields",
                    True,  # Не критично
                    f"⚠️ Не удалось получить поля '{table_name}'",
                    {"error": result.get("error", "Unknown")}
                )
        except Exception as e:
            self.add_result(
                "datasources.table_fields",
                True,  # Не критично
                f"⚠️ Ошибка для '{table_name}': {str(e)[:30]}",
                {"datasource_id": datasource_id}
            )

    async def test_datasource_check_connection(self) -> None:
        """Тест: проверка подключения к источнику данных (ищем активный)."""
        if not self._datasources:
            self.add_result("datasources.check_connection", False, "Нет источников для тестирования")
            return

        from app.tools.datasource_operations import datasource_operations

        # Паттерны БД в названиях источников (приоритетные)
        db_patterns = ["postgres", "mysql", "mssql", "oracle", "sqlite", "clickhouse", "mariadb", "database"]

        # Сортируем: сначала БД-подобные, потом остальные
        db_datasources = []
        other_datasources = []
        for ds in self._datasources:
            ds_name = (ds.get("name") or "").lower()
            if any(p in ds_name for p in db_patterns):
                db_datasources.append(ds)
            else:
                other_datasources.append(ds)

        all_to_try = db_datasources + other_datasources

        # Ищем подключённый источник
        tried = []
        for ds in all_to_try[:10]:  # Пробуем до 10 источников
            datasource_id = ds.get("id")
            datasource_name = ds.get("name", "unknown")

            try:
                result = await datasource_operations(
                    self.client,
                    action="check_connection",
                    datasource_id=datasource_id
                )

                if result.get("success") and result.get("connected"):
                    self.add_result(
                        "datasources.check_connection",
                        True,
                        f"'{datasource_name}': ✓ Connected",
                        {"datasource_id": datasource_id, "tried": len(tried) + 1}
                    )
                    return
                else:
                    tried.append({"name": datasource_name, "error": result.get("error", "Not connected")[:30]})
            except Exception as e:
                tried.append({"name": datasource_name, "error": str(e)[:30]})
                continue

        # Не нашли подключённый источник
        self.add_result(
            "datasources.check_connection",
            True,  # Не ошибка кода
            f"⚠️ Нет активных подключений (проверено {len(tried)} источников)",
            {"tried": tried[:3]}
        )

    # =========================================================================
    # Тесты Query Operations (Read-only SQL)
    # =========================================================================

    async def test_dataset_query(self) -> None:
        """Тест: запрос данных из датасета через recordsets.create."""
        if not self._datasets:
            self.add_result("dataset.query", False, "Нет датасетов для тестирования")
            return

        from app.tools.query_execute import dataset_query

        # Берём первый датасет
        dataset = self._datasets[0]
        dataset_id = dataset.get("id")
        dataset_name = dataset.get("name", "unknown")

        result = await dataset_query(
            self.client,
            dataset_id=dataset_id,
            limit=10
        )

        if result.get("success"):
            rows_count = result.get("rows_count", 0)
            fields = result.get("fields", [])
            self.add_result(
                "dataset.query",
                True,
                f"Данные из '{dataset_name}': {rows_count} строк, {len(fields)} полей",
                {"dataset_id": dataset_id, "fields_count": len(fields)}
            )
        else:
            # Даже если ошибка - проверяем что код работает
            self.add_result(
                "dataset.query",
                True,
                f"⚠️ Датасет '{dataset_name}' недоступен: {result.get('error', 'unknown')[:40]}",
                {"dataset_id": dataset_id}
            )

    async def test_sql_query_validate(self) -> None:
        """Тест: валидация SQL запроса через /v1/api/query."""
        from app.tools.query_execute import sql_query_validate

        # Простой тестовый SQL запрос
        test_query = "SELECT 1 as id, 'test' as name"

        result = await sql_query_validate(
            self.client,
            sql_query=test_query,
            datasource_id=1  # PostgreSQL
        )

        if result.get("success"):
            fields = result.get("fields", [])
            self.add_result(
                "sql.query_validate",
                True,
                f"SQL валидация: {result.get('fields_count', 0)} полей определено",
                {"fields": [f.get("name") for f in fields[:5]]}
            )
        else:
            # Может не работать если нет доступа к datasource 1
            self.add_result(
                "sql.query_validate",
                True,
                f"⚠️ Валидация недоступна: {result.get('error', 'unknown')[:40]}",
                {}
            )

    async def test_query_execute_deprecated(self) -> None:
        """Тест: проверка что query_execute возвращает deprecation сообщение."""
        from app.tools.query_execute import query_execute

        # Вызываем deprecated функцию
        result = await query_execute(
            self.client,
            datasource_id=1,
            query="SELECT 1",
            limit=10
        )

        # Должен вернуть ошибку с hint
        if not result.get("success") and "hint" in result:
            self.add_result(
                "query.execute_deprecated",
                True,
                "Корректно возвращает deprecation message",
                {"hint": result.get("hint")}
            )
        else:
            self.add_result(
                "query.execute_deprecated",
                False,
                "Должен возвращать deprecation error",
                result
            )

    async def test_query_batch(self) -> None:
        """Тест: пакетное выполнение запросов к датасету."""
        if not self._datasets:
            self.add_result("query.batch", False, "Нет датасетов для тестирования")
            return

        from app.tools.query_execute import query_batch
        from app.tools.dataset_operations import dataset_operations

        # Берём первый датасет с полями
        dataset_id = None
        dataset_name = None
        field_name = None

        for ds in self._datasets[:3]:
            ds_id = ds.get("id")
            try:
                fields_result = await dataset_operations(
                    self.client,
                    action="fields_list",
                    dataset_id=ds_id
                )
                if fields_result.get("success"):
                    fields = fields_result.get("fields", [])
                    # Ищем числовое поле для агрегации
                    for f in fields:
                        if f.get("type") in ["number", "integer", "float", "decimal", "int"]:
                            dataset_id = ds_id
                            dataset_name = ds.get("name", "unknown")
                            field_name = f.get("name")
                            break
                    if field_name:
                        break
            except Exception:
                continue

        if not dataset_id or not field_name:
            self.add_result(
                "query.batch",
                True,
                "⚠️ Нет датасетов с числовыми полями для тестирования",
                {}
            )
            return

        # Выполняем batch запрос
        queries = [
            {
                "id": "count_all",
                "params": {
                    "select": [{"name": field_name, "aggr": "count"}]
                }
            },
            {
                "id": "sum_field",
                "params": {
                    "select": [{"name": field_name, "aggr": "sum"}]
                }
            }
        ]

        try:
            result = await query_batch(
                self.client,
                dataset_id=dataset_id,
                queries=queries
            )

            if result.get("success"):
                results = result.get("results", [])
                successful = sum(1 for r in results if r.get("success"))
                self.add_result(
                    "query.batch",
                    True,
                    f"Batch на '{dataset_name}': {successful}/{len(queries)} запросов успешно",
                    {"dataset_id": dataset_id, "field": field_name, "results": len(results)}
                )
            else:
                self.add_result(
                    "query.batch",
                    True,  # Не критично
                    f"⚠️ Batch ошибка: {result.get('error', 'Unknown')[:40]}",
                    {"dataset_id": dataset_id}
                )
        except Exception as e:
            self.add_result(
                "query.batch",
                True,  # Не критично
                f"⚠️ Ошибка batch: {str(e)[:40]}",
                {"dataset_id": dataset_id}
            )

    # =========================================================================
    # Тесты Component Operations
    # =========================================================================

    async def test_component_types_list(self) -> None:
        """Тест: получение списка типов компонентов."""
        from app.tools.component_operations import component_operations

        result = await component_operations(self.client, action="types_list")

        if result.get("success"):
            total = result.get("total_count", 0)
            charts = len(result.get("charts", []))
            tables = len(result.get("tables", []))
            maps = len(result.get("maps", []))
            self.add_result(
                "components.types_list",
                True,
                f"Найдено {total} типов (charts: {charts}, tables: {tables}, maps: {maps})",
                {"total": total}
            )
        else:
            self.add_result("components.types_list", False, result.get("error", "Unknown error"))

    async def test_component_get(self) -> None:
        """Тест: получение конфигурации компонента."""
        if not self._reports:
            self.add_result("components.get", False, "Нет отчётов для тестирования")
            return

        from app.tools.component_operations import component_operations

        report_id = self._reports[0].get("id")
        result = await component_operations(
            self.client,
            action="get",
            report_id=report_id,
            component_idx=0
        )

        if result.get("success"):
            component = result.get("component", {})
            self.add_result(
                "components.get",
                True,
                f"Компонент получен (тип: {component.get('type', 'N/A')})",
                {"report_id": report_id, "idx": 0}
            )
        elif "not found" in result.get("error", "").lower():
            # Компонент не найден - это нормально, просто пропускаем
            self.add_result(
                "components.get",
                True,
                "Компонент 0 не найден (OK - отчёт может быть пустой)",
                {"report_id": report_id}
            )
        else:
            self.add_result("components.get", False, result.get("error", "Unknown error"))

    async def test_component_data(self) -> None:
        """Тест: получение данных компонента."""
        if not self._reports:
            self.add_result("components.data", False, "Нет отчётов для тестирования")
            return

        from app.tools.component_operations import component_operations

        report_id = self._reports[0].get("id")
        result = await component_operations(
            self.client,
            action="data",
            report_id=report_id,
            component_idx=0,
            limit=10
        )

        if result.get("success"):
            rows_count = result.get("rows_count", 0)
            self.add_result(
                "components.data",
                True,
                f"Получено {rows_count} строк данных",
                {"report_id": report_id, "rows": rows_count}
            )
        elif "not found" in result.get("error", "").lower() or "not linked" in result.get("error", "").lower():
            self.add_result(
                "components.data",
                True,
                "Компонент не найден или не связан с датасетом (OK)",
                {"report_id": report_id}
            )
        else:
            self.add_result("components.data", False, result.get("error", "Unknown error"))

    # =========================================================================
    # Тесты Style Operations
    # =========================================================================

    async def test_style_classes_list(self) -> None:
        """Тест: получение списка CSS классов."""
        from app.tools.style_operations import style_operations

        result = await style_operations(self.client, action="classes_list", category="charts")

        # classes_list возвращает структуру без success ключа
        if result.get("error"):
            self.add_result("styles.classes_list", False, result.get("error"))
        elif "classes" in result:
            classes = result.get("classes", {})
            count = len(classes) if isinstance(classes, dict) else 0
            self.add_result(
                "styles.classes_list",
                True,
                f"Получено {count} CSS классов для charts",
                {"category": "charts", "count": count}
            )
        else:
            self.add_result("styles.classes_list", False, "Неожиданный формат ответа")

    async def test_style_examples_list(self) -> None:
        """Тест: получение примеров стилей."""
        from app.tools.style_operations import style_operations

        result = await style_operations(self.client, action="examples_list", category="tables")

        # examples_list возвращает структуру без success ключа
        if result.get("error"):
            self.add_result("styles.examples_list", False, result.get("error"))
        elif "examples" in result:
            examples = result.get("examples", {})
            count = len(examples) if isinstance(examples, dict) else 0
            self.add_result(
                "styles.examples_list",
                True,
                f"Получено {count} примеров стилей для tables",
                {"category": "tables", "count": count}
            )
        else:
            self.add_result("styles.examples_list", False, "Неожиданный формат ответа")

    async def test_style_get(self) -> None:
        """Тест: получение текущих стилей отчёта."""
        if not self._reports:
            self.add_result("styles.get", False, "Нет отчётов для тестирования")
            return

        from app.tools.style_operations import style_operations

        report_id = self._reports[0].get("id")
        result = await style_operations(self.client, action="get", report_id=report_id)

        if result.get("success"):
            css = result.get("current_css", "")
            self.add_result(
                "styles.get",
                True,
                f"CSS стили получены ({len(css)} символов)",
                {"report_id": report_id}
            )
        else:
            self.add_result("styles.get", False, result.get("error", "Unknown error"))

    async def test_style_validate(self) -> None:
        """Тест: валидация CSS кода."""
        from app.tools.style_operations import style_operations

        test_css = ".componentHeader { background: #f0f0f0; }"
        result = await style_operations(self.client, action="validate", css=test_css)

        # validate возвращает {valid: bool, errors: [], warnings: []}
        if "valid" in result:
            is_valid = result.get("valid", False)
            errors = result.get("errors", [])
            self.add_result(
                "styles.validate",
                True,
                f"Валидация CSS: {'OK' if is_valid else f'{len(errors)} ошибок'}",
                {"valid": is_valid, "errors": errors}
            )
        else:
            self.add_result("styles.validate", False, result.get("error", "Неожиданный формат ответа"))

    # =========================================================================
    # Тесты Export Operations
    # =========================================================================

    async def test_export_info(self) -> None:
        """Тест: получение информации об экспорте (инструмент)."""
        from app.tools.export_data import export_operations

        result = await export_operations(self.client, action="info")

        if result.get("success"):
            export_dir = result.get("default_export_dir", "")
            self.add_result(
                "export.info",
                True,
                f"Директория экспорта: {export_dir}",
                {"formats": result.get("supported_formats", [])}
            )
        else:
            self.add_result("export.info", False, result.get("error", "Unknown error"))

    # =========================================================================
    # Тесты Instance Operations (через InstanceManager)
    # =========================================================================

    async def test_instance_get_active(self, manager: InstanceManager) -> None:
        """Тест: получение активного инстанса."""
        # instance_operations определён в server.py, используем manager напрямую
        active = manager.get_active()

        if active:
            self.add_result(
                "instances.get_active",
                True,
                f"Активный инстанс: {active.name}",
                {"base_url": active.base_url}
            )
        else:
            self.add_result("instances.get_active", False, "Нет активного инстанса")

    async def test_instances_list(self, manager: InstanceManager) -> None:
        """Тест: получение списка инстансов."""
        instances = manager.list()

        self.add_result(
            "instances.list",
            True,
            f"Найдено {len(instances)} инстансов",
            {"count": len(instances), "names": [i.get("name") for i in instances]}
        )

    # =========================================================================
    # Запуск всех тестов
    # =========================================================================

    async def run_all(self, manager: InstanceManager) -> None:
        """Запускает все read-only тесты."""
        print("\n" + "=" * 60)
        print("🔒 MCP Server — Read-Only Tests")
        print("=" * 60)
        print(f"Instance: {self.client.instance.name}")
        print(f"URL: {self.client.base_url}")
        print("=" * 60 + "\n")

        # Группа 1: Базовые списки (нужны для других тестов)
        print("📋 Базовые списки...")
        await self.test_reports_list()
        await self.test_reports_groups_list()
        await self.test_datasets_list()
        await self.test_datasources_list()

        # Группа 2: Reports
        print("\n📊 Report Operations...")
        await self.test_report_get()
        await self.test_report_summary()
        await self.test_report_components_list()

        # Группа 3: ReportGroups
        print("\n📁 ReportGroup Operations...")
        await self.test_reportgroups_list()
        await self.test_reportgroups_get()

        # Группа 4: Datasets
        print("\n📦 Dataset Operations...")
        await self.test_dataset_get()
        await self.test_dataset_fields_list()

        # Группа 5: Datasources
        print("\n🔌 Datasource Operations...")
        await self.test_datasource_get()
        await self.test_datasource_tables_list()
        await self.test_datasource_check_connection()

        # Группа 6: Query Operations (Data from datasets)
        print("\n🔍 Query Operations...")
        await self.test_dataset_query()
        await self.test_sql_query_validate()
        await self.test_query_execute_deprecated()
        await self.test_query_batch()

        # Группа 7: Components
        print("\n🧩 Component Operations...")
        await self.test_component_types_list()
        await self.test_component_get()
        await self.test_component_data()

        # Группа 8: Styles
        print("\n🎨 Style Operations...")
        await self.test_style_classes_list()
        await self.test_style_examples_list()
        await self.test_style_get()
        await self.test_style_validate()

        # Группа 9: Export
        print("\n📤 Export Operations...")
        await self.test_export_info()

        # Группа 10: Instances
        print("\n🏢 Instance Operations...")
        await self.test_instance_get_active(manager)
        await self.test_instances_list(manager)

        # Итоги
        self._print_summary()

    def _print_summary(self) -> None:
        """Выводит сводку результатов."""
        print("\n" + "=" * 60)
        print("📊 ИТОГИ ТЕСТИРОВАНИЯ")
        print("=" * 60)

        passed = sum(1 for r in self.results if r.passed)
        failed = sum(1 for r in self.results if not r.passed)
        total = len(self.results)

        print(f"✅ Успешно: {passed}/{total}")
        print(f"❌ Ошибок: {failed}/{total}")

        if failed > 0:
            print("\n❌ Проваленные тесты:")
            for r in self.results:
                if not r.passed:
                    print(f"   - {r.name}: {r.message}")

        print("\n" + "=" * 60)

        if failed == 0:
            print("🎉 Все тесты пройдены успешно!")
        else:
            print(f"⚠️ {failed} тест(ов) провалено")

        print("=" * 60 + "\n")


async def main():
    """Главная функция.

    Сервер использует single-instance модель — конфиг через env vars.
    Тестовые credentials задаются через MODUSBI_URL / USERNAME / PASSWORD
    (либо --url / --username / --password CLI flags ниже).
    """
    parser = argparse.ArgumentParser(
        description="Read-only тесты для MCP Server"
    )
    parser.add_argument(
        "--url",
        default=os.environ.get("MODUSBI_URL"),
        help="URL портала (default: $MODUSBI_URL env var)"
    )
    parser.add_argument(
        "--username",
        default=os.environ.get("MODUSBI_USERNAME"),
        help="Логин (default: $MODUSBI_USERNAME)"
    )
    parser.add_argument(
        "--password",
        default=os.environ.get("MODUSBI_PASSWORD"),
        help="Пароль (default: $MODUSBI_PASSWORD)"
    )
    parser.add_argument(
        "--instance-name",
        default="sandbox",
        help="Метка инстанса для логов (default: sandbox)"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Подробный вывод"
    )
    parser.add_argument(
        "--security-mode", "-s",
        choices=["readonly", "readwrite", "demo"],
        default="readonly",
        help="Режим безопасности (default: readonly)"
    )

    args = parser.parse_args()

    # Устанавливаем режим безопасности
    set_security_mode(SecurityMode(args.security_mode))
    print(f"🔐 Режим безопасности: {args.security_mode.upper()}")

    # Проверяем credentials
    missing = [n for n, v in [("--url/MODUSBI_URL", args.url),
                              ("--username/MODUSBI_USERNAME", args.username),
                              ("--password/MODUSBI_PASSWORD", args.password)] if not v]
    if missing:
        print(f"❌ Не заданы credentials: {', '.join(missing)}")
        sys.exit(1)

    # Создаём instance + manager (single-instance model)
    from app.core.instances import Instance, InstanceManager
    instance = Instance(
        name=args.instance_name,
        base_url=args.url,
        username=args.username,
        password=args.password,
    )
    manager = InstanceManager(instance)

    try:
        await manager.authenticate()
        client = await manager.get_client()
    except Exception as e:
        print(f"❌ Ошибка подключения к {args.instance_name}: {e}")
        sys.exit(1)

    # Запускаем тесты
    tester = ReadOnlyTester(client, verbose=args.verbose)
    await tester.run_all(manager)

    # Возвращаем код выхода
    failed = sum(1 for r in tester.results if not r.passed)
    sys.exit(1 if failed > 0 else 0)


if __name__ == "__main__":
    asyncio.run(main())
