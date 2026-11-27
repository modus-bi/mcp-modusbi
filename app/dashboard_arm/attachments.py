"""Validate chat uploads and create a dataset through the Modus file import API."""

import base64
import csv
from datetime import date, datetime, time
from decimal import Decimal
from io import BytesIO, StringIO
from pathlib import Path
import re
import time as clock
from zipfile import BadZipFile, ZipFile
from uuid import UUID

import httpx
from openpyxl import load_workbook
from openpyxl.utils.exceptions import InvalidFileException


from xlsxwriter import Workbook


MAX_BYTES = 8 * 1024 * 1024
MAX_ROWS = 30_000
MAX_COLUMNS = 80
MAX_SHEETS = 20
MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


class AttachmentError(ValueError):
    """A message suitable for showing in the chat."""


def csv_value(value):
    text = value.strip()
    if not text:
        return None
    if re.fullmatch(r"-?(0|[1-9]\d*)", text) and len(text) < 16:
        return int(text)
    if re.fullmatch(r"-?(0|[1-9]\d*)[.,]\d+", text) and len(text) < 20:
        return float(Decimal(text.replace(",", ".")))
    for pattern, fmt in ((r"\d{4}-\d{2}-\d{2}", "%Y-%m-%d"), (r"\d{2}\.\d{2}\.\d{4}", "%d.%m.%Y")):
        if re.fullmatch(pattern, text):
            try:
                return datetime.strptime(text, fmt).date()
            except ValueError:
                break
    return text


def read_csv(data):
    for encoding in ("utf-8-sig", "cp1251"):
        try:
            text = data.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    else:
        raise AttachmentError("Не удалось прочитать кодировку CSV. Сохраните файл в UTF-8.")
    if "\x00" in text:
        raise AttachmentError("Сохраните CSV в UTF-8.")
    try:
        dialect = csv.Sniffer().sniff(text[:8192], delimiters=";,\t")
    except csv.Error:
        dialect = csv.excel
    reader = csv.reader(StringIO(text, newline=""), dialect, strict=True)
    try:
        raw = list(reader)
    except csv.Error:
        raise AttachmentError("В CSV нарушен формат строк или кавычек.") from None
    if not raw:
        return []
    first = next((index for index, row in enumerate(raw) if any(v.strip() for v in row)), len(raw))
    raw = raw[first:]
    return raw[:1] + [[csv_value(v) for v in row] for row in raw[1:]]


def table(name, rows):
    rows = [list(row) for row in rows if any(v is not None and v != "" for v in row)]
    if len(rows) < 2:
        return None
    width = max(len(row) for row in rows)
    if width > MAX_COLUMNS or len(rows) > MAX_ROWS + 1:
        raise AttachmentError(f"Лист «{name}» превышает {MAX_ROWS} строк или {MAX_COLUMNS} столбцов.")
    headers = rows.pop(0)
    while headers and (headers[-1] is None or headers[-1] == ""):
        headers.pop()
    if len(headers) < width:
        # CSV often has an empty delimiter at the end and Excel has formatted blank columns.
        width = max(len(headers), *(max((i+1 for i, v in enumerate(r) if v is not None and v != ""), default=0) for r in rows))
    headers = [str(value).strip() if value is not None else "" for value in headers]
    if len(headers) != width or not all(headers) or len({v.casefold() for v in headers}) != width:
        raise AttachmentError(f"На листе «{name}» заполните уникальные заголовки всех столбцов в первой строке.")
    rows = [row[:width] + [None] * max(0, width - len(row)) for row in rows]
    return {"name": name, "headers": headers, "rows": rows}


def read_file(name, data):
    if not 0 < len(data) <= MAX_BYTES:
        raise AttachmentError("Прикрепите файл Excel или CSV размером до 8 МБ.")
    suffix = Path(name).suffix.lower()
    if suffix == ".csv":
        candidate = table("CSV", read_csv(data))
        sheets = [candidate] if candidate else []
    elif suffix == ".xlsx":
        try:
            with ZipFile(BytesIO(data)) as archive:
                if sum(f.file_size for f in archive.infolist()) > 50 * 1024 * 1024:
                    raise AttachmentError("Размер распакованной книги превышает 50 МБ.")
            workbook = load_workbook(BytesIO(data), read_only=True, data_only=True, keep_links=False)
            try:
                if len(workbook.worksheets) > MAX_SHEETS:
                    raise AttachmentError(f"В книге допускается до {MAX_SHEETS} листов.")
                sheets = []
                for ws in workbook.worksheets:
                    if ws.sheet_state != "visible":
                        continue
                    if (ws.max_row or 0) > MAX_ROWS + 1 or (ws.max_column or 0) > MAX_COLUMNS:
                        raise AttachmentError(f"Лист «{ws.title}» превышает допустимый размер.")
                    item = table(ws.title, ws.iter_rows(values_only=True))
                    if item:
                        sheets.append(item)
            finally:
                workbook.close()
        except (BadZipFile, InvalidFileException, KeyError, OSError):
            raise AttachmentError("Не удалось прочитать книгу Excel. Проверьте формат .xlsx.") from None
    else:
        raise AttachmentError("Поддерживаются файлы .xlsx и .csv.")
    if not sheets:
        raise AttachmentError("В файле нет таблицы с заголовками и строками данных.")
    return sheets


def describe(sheets):
    def show(value):
        return str(value)[:140] if value is not None else None
    return [{"name": sheet["name"], "headers": sheet["headers"], "row_count": len(sheet["rows"]),
             "sample": [[show(v) for v in row] for row in sheet["rows"][:2]]} for sheet in sheets]


def canonical_xlsx(sheet):
    out = BytesIO()
    with Workbook(out, {"in_memory": True, "strings_to_formulas": False, "strings_to_urls": False}) as book:
        ws = book.add_worksheet("Data")
        fmt = book.add_format({"num_format": "yyyy-mm-dd hh:mm:ss"})
        ws.write_row(0, 0, sheet["headers"])
        for col in range(len(sheet["headers"])):
            values = [row[col] for row in sheet["rows"]]
            kinds = {type(v) for v in values if v is not None}
            date_col = bool(kinds) and kinds <= {date, datetime, time}
            numeric_col = bool(kinds) and kinds <= {int, float, Decimal}
            for row, value in enumerate(values, 1):
                if value is None:
                    continue
                if date_col:
                    ws.write_datetime(row, col, value, fmt)
                elif numeric_col:
                    ws.write_number(row, col, value)
                else:
                    ws.write_string(row, col, str(value))
    return out.getvalue()


def decode_upload(attachment):
    name = attachment.get("name")
    if not isinstance(name, str) or len(name) > 230 or "/" in name or "\\" in name:
        raise AttachmentError("Недопустимое имя файла.")
    try:
        data = base64.b64decode(attachment.get("data", ""), validate=True)
    except (ValueError, TypeError):
        raise AttachmentError("Не удалось получить файл. Прикрепите его ещё раз.") from None
    return name, data, read_file(name, data)


def import_table(token, portal, chat_id, sheet, attachment, checkpoint, datasource_id):
    """Use the portal's Excel loader with the configured datasource."""
    name = "xls_giga_" + UUID(chat_id).hex[:20]
    if attachment.get("selected_sheet") and attachment["selected_sheet"] != sheet["name"]:
        raise AttachmentError("Этот чат уже связан с другим листом. Для нового источника откройте новый чат.")
    attachment["selected_sheet"] = sheet["name"]
    binary = canonical_xlsx(sheet)
    with httpx.Client(base_url=portal, headers={"Authorization": "Bearer " + token}, timeout=70) as client:
        def call(resource, action, *, object_id=None, command_id=None, data=None):
            obj = {"name": resource, **({"id": object_id} if object_id else {})}
            command = {"name": action, **({"id": command_id} if command_id else {})}
            result = client.post("/v1/api/" + resource, json={
                "object": obj, "command": command, **({"data": data} if data else {}),
            })
            body = result.json()
            if result.status_code != 200 or body.get("status") != 200:
                raise AttachmentError(f"Modus BI не подтвердил шаг импорта {action} (HTTP {result.status_code}, статус {body.get('status')}).")
            return body.get("data") or []

        available = call("imports", "datasource.list")
        if not any(s.get("ID") == datasource_id for s in available):
            raise AttachmentError("Настроенный источник Modus BI недоступен для загрузки.")
        if (import_id := attachment.get("import_id")) is None:
            filename = name + ".xlsx"
            caption = f"Чат GigaChat · {attachment['name'][:150]} · {name.removeprefix('xls_giga_')}"
            created = [item for item in call("imports", "list")
                       if item.get("filename") == filename and item.get("caption") == caption]
            if not created:
                created = call("imports", "create", data=[{
                    "ID": None, "mimetype": MIME, "caption": caption,
                    "filename": filename, "filesize": len(binary),
                    "modified": int(clock.time() * 1000), "options": {"rowCount": 50},
                }])
            if len(created) != 1 or type(created[0].get("ID")) is not int:
                raise AttachmentError("Портал не вернул ID загрузки.")
            import_id = created[0]["ID"]
            attachment["import_id"] = import_id
            checkpoint()
        stored = call("imports", "get", object_id=import_id)
        for item in ((stored[0].get("content") or []) if stored else []):
            if item.get("tableName") == name and type(item.get("dataset")) is int and item["dataset"] > 0:
                return {"id": item["dataset"], "name": name, "rows": len(sheet["rows"]), "sheet": sheet["name"]}
        if attachment.get("load_pending"):
            raise AttachmentError("Статус предыдущей загрузки пока не подтверждён. Датасет повторно не создаётся.")
        loaded = client.post(f"/v1/api/imports/{import_id}", content=binary, headers={
            "Content-Type": MIME, "X-Requested-With": "XMLHttpRequest",
        })
        value = loaded.json()
        if loaded.status_code != 200 or not isinstance(value, list) or len(value) != 1:
            raise AttachmentError("Modus BI не принял файл для загрузки.")
        record = value[0]
        if len(record.get("content") or []) != 1:
            raise AttachmentError("Modus BI не распознал лист с данными.")
        target = record["content"][0]
        if len(target.get("cols", [])) != len(sheet["headers"]):
            raise AttachmentError("Число загруженных столбцов не совпадает с исходным файлом.")
        target.update(selected=1, headerRowIdx=1, tableRowFirst=2, tableRowLast=-1, tableName=name)
        for index, (column, label) in enumerate(zip(target["cols"], sheet["headers"]), 1):
            column.update(selected=1, fieldName=f"col_{index}", fieldAlias=label)
            if column["fieldType"] == "number":
                precision = max((max(0, -Decimal(str(row[index-1])).as_tuple().exponent)
                                 for row in sheet["rows"] if type(row[index-1]) in {int, float}), default=0)
                column.update(fieldLen=36, fieldPrecision=min(precision, 15))
        attachment["load_pending"] = True
        checkpoint()
        info = call("imports", "table.data.load", object_id=import_id, command_id=datasource_id, data=[record])
        saved = next((item for item in info[0].get("content", []) if item.get("tableName") == name), {}) if info else {}
        if type(saved.get("dataset")) is not int or saved["dataset"] <= 0 or saved.get("status") != "Loaded":
            raise AttachmentError("Modus BI не подтвердил создание датасета.")
        attachment.pop("load_pending", None)
        return {"id": saved["dataset"], "name": name, "rows": len(sheet["rows"]), "sheet": sheet["name"]}
