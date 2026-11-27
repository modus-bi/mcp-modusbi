"""Shared dashboard chat served by the existing MCP HTTP process."""
import asyncio
import json
import logging
import os
import re
import secrets
import sqlite3
from contextlib import closing
from pathlib import Path
from uuid import NAMESPACE_URL, UUID, uuid5

from cryptography.fernet import Fernet
from mcp.server.fastmcp.exceptions import ToolError
from starlette.requests import Request
from starlette.responses import FileResponse, JSONResponse, Response

from ..core.security import check_action
from ..tools.report_operations import _list_reports
from .attachments import AttachmentError, MAX_BYTES, decode_upload, describe
from .engine import Engine
from .photo import decode_photo
from .provider import GigaAPI, Ledger


log = logging.getLogger(__name__)
PREFIX = "/api/dashboard-arm/{arm}"


class ChatStore:
    def __init__(self, directory):
        self.directory = directory
        directory.mkdir(parents=True, exist_ok=True)
        self.db = directory / "chats.sqlite3"
        with closing(sqlite3.connect(self.db)) as conn, conn:
            conn.execute("CREATE TABLE IF NOT EXISTS chats (arm TEXT, id TEXT, report_id INTEGER, state TEXT NOT NULL, PRIMARY KEY (arm,id))")
            conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS chat_report ON chats (arm,report_id)")

    def load(self, arm, *, id=None, report_id=None):
        with closing(sqlite3.connect(self.db)) as conn:
            if report_id:
                row = conn.execute("SELECT state FROM chats WHERE arm=? AND report_id=?", (arm, report_id)).fetchone()
            else:
                row = conn.execute("SELECT state FROM chats WHERE arm=? AND id=?", (arm, id)).fetchone()
        return json.loads(row[0]) if row else None

    def save(self, state):
        with closing(sqlite3.connect(self.db)) as conn, conn:
            conn.execute("INSERT INTO chats VALUES(?,?,?,?) ON CONFLICT(arm,id) DO UPDATE SET report_id=excluded.report_id,state=excluded.state",
                         (state["arm"], state["id"], state["report_id"], json.dumps(state, ensure_ascii=False)))

    def file_path(self, state, name):
        return self.directory / "uploads" / state["arm"] / state["id"] / name

    def write(self, state, name, content):
        path = self.file_path(state, name)
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.with_suffix(path.suffix + ".tmp")
        temp.write_bytes(content)
        temp.replace(path)


class InternalMCP:
    """Call the registered tools on the MCP event loop from the generation worker."""

    def __init__(self, mcp, get_client):
        self.mcp = mcp
        self.get_client = get_client
        self.loop = asyncio.get_running_loop()

    def wait(self, operation):
        return asyncio.run_coroutine_threadsafe(operation, self.loop).result()

    def tools(self):
        return [tool.model_dump(by_alias=True) for tool in self.wait(self.mcp.list_tools())]

    def request(self, method, params):
        if method != "resources/read":
            raise ValueError("Only resource reads are supported")
        return {"contents": [{"text": item.content} for item in self.wait(self.mcp.read_resource(params["uri"]))]}

    def call(self, name, args):
        try:
            result = self.wait(self.mcp.call_tool(name, args))
            if isinstance(result, tuple):
                result = result[1]
            if not isinstance(result, dict):
                result = json.loads(result[0].text)
            return {"payload": result}
        except (ToolError, ValueError, TypeError, AttributeError, IndexError, RuntimeError) as error:
            log.warning("Dashboard tool %s failed (%s)", name, type(error).__name__)
            return {"isError": True, "payload": {"success": False}}

    def portal_client(self):
        return self.wait(self.get_client())


def chat_state(arm, id, report_id=None, title=None):
    return {"arm": arm, "id": id, "title": title, "report_id": report_id, "status": "idle", "messages": [],
            "requests": 0, "usage": Ledger().values, "seconds": 0, "tool_log": []}


def public(state, id):
    keys = ("title", "report_id", "report_revision", "status", "messages", "requests", "usage", "seconds", "progress")
    result = {"id": id, **{key: state[key] for key in keys if key in state}}
    if attachment := state.get("attachment"):
        result["attachment"] = {"name": attachment["name"], **({"dataset": attachment["dataset"]} if attachment.get("dataset") else {})}
    return result


async def body(request):
    limit = 2 * (4 * ((MAX_BYTES + 2) // 3)) + 32_768
    data = bytearray()
    async for chunk in request.stream():
        if len(data) + len(chunk) > limit:
            raise AttachmentError("Размер каждого вложения должен быть до 8 МБ.")
        data.extend(chunk)
    payload = json.loads(data)
    if not isinstance(payload, dict):
        raise ValueError("Ожидается объект запроса.")
    return payload


def register_dashboard_arm(mcp, get_client):
    arm = os.environ.get("MODUSBI_ARM_ID", "dashboard-builder")
    access_key = os.environ.get("MODUSBI_ARM_ACCESS_KEY", "")
    origins = set(filter(None, (os.environ.get("MODUSBI_ARM_ORIGIN", "").rstrip("/"),)))
    fallback = {"credential": os.environ.get("GIGACHAT_CREDENTIALS", ""),
                "model": os.environ.get("GIGACHAT_MODEL", "GigaChat-3-Pro"),
                "scope": os.environ.get("GIGACHAT_SCOPE", "GIGACHAT_API_PERS")}
    admin_key = os.environ.get("MODUSBI_ARM_ADMIN_KEY", "")
    encryption_key = os.environ.get("MODUSBI_ARM_SECRET_KEY", "")
    if bool(admin_key) != bool(encryption_key) or admin_key and (admin_key == access_key or len(admin_key) < 24):
        raise RuntimeError("Use a separate MODUSBI_ARM_ADMIN_KEY and set MODUSBI_ARM_SECRET_KEY for the GigaChat setup screen")
    vault = Fernet(encryption_key.encode()) if encryption_key else None
    group_id = int(os.environ.get("MODUSBI_ARM_REPORT_GROUP", "1"))
    datasource_id = int(os.environ.get("MODUSBI_ARM_IMPORT_SOURCE", "0"))
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,59}", arm) or len(access_key) < 24 or not origins or not (fallback["credential"] or vault) or group_id < 1 or datasource_id < 0:
        raise RuntimeError("Configure the ARM origin, access key and GigaChat connection before enabling dashboard chat")
    store = ChatStore(Path(os.environ.get("MODUSBI_ARM_DATA_DIR", "var/dashboard-arm")))
    secret_file = store.directory / "gigachat.enc"

    def connection():
        return json.loads(vault.decrypt(secret_file.read_bytes())) if vault and secret_file.is_file() else fallback

    def provider(settings=None):
        settings = connection() if settings is None else settings
        return GigaAPI(settings["credential"], settings["scope"], os.environ.get("GIGACHAT_CA_FILE"))

    engine = Engine(store, provider, datasource_id)
    jobs = {}
    submit_lock = asyncio.Lock()
    model_slot = asyncio.Lock()

    async def generate(state, settings):
        async with model_slot:
            await asyncio.to_thread(engine.execute, state, InternalMCP(mcp, get_client), lambda: provider(settings))

    def finish(id, task):
        jobs.pop(id, None)
        if not task.cancelled() and task.exception():
            log.error("Dashboard chat worker failed (%s)", type(task.exception()).__name__)

    async def reports(client):
        check_action("list")
        result = await _list_reports(client, limit=0)
        if not result.get("success"):
            raise RuntimeError("Report inventory failed")
        return {item["id"]: item for item in result["items"] if type(item.get("id")) is int and item["id"]>0 and not item["deleted"]}

    async def datasets(client):
        check_action("list")
        result = await client.api_call("datasets", "list")
        if result.get("status") != 200:
            raise RuntimeError("Dataset inventory failed")
        return {str(row["ID"]): row.get("caption") or row.get("name") or str(row["ID"]) for row in result["data"] if row.get("ID")}

    def headers(request):
        origin = request.headers.get("Origin")
        return {"Cache-Control": "no-store", "Vary": "Origin", **({"Access-Control-Allow-Origin": origin} if origin in origins else {})}

    def reply(request, payload, code=200):
        return JSONResponse(payload, status_code=code, headers=headers(request))

    def authorized(request):
        return (request.path_params["arm"] == arm and request.headers.get("Origin") in (None, *origins)
                and secrets.compare_digest(request.headers.get("X-Modus-ARM-Key", "").encode(), access_key.encode()))

    async def options(request):
        if request.path_params["arm"] != arm or request.headers.get("Origin") not in origins:
            return Response(status_code=403)
        return Response(status_code=204, headers={**headers(request), "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, X-Modus-ARM-Key, X-Modus-ARM-Admin"})

    async def check_provider(settings):
        def verify_provider():
            api = provider(settings)
            try:
                return settings["model"] in {row.get("id") for row in api.request("GET", "models").get("data", [])}
            finally:
                api.close()

        try:
            async with model_slot:
                return await asyncio.to_thread(verify_provider)
        except Exception:
            return False

    async def entry(request):
        client = await get_client()
        kind = request.url.path.rsplit('/', 1)[-1]
        if kind == "datasets":
            entries = await datasets(client)
            return reply(request, {"datasets": [{"id": int(id), "title": title} for id, title in entries.items()]})
        catalogue = await reports(client)
        settings = connection()
        if kind == "status":
            giga = bool(settings["credential"]) and await check_provider(settings)
            return reply(request, {"mcp": True, "gigachat": giga, "model": settings["model"], "total_count": len(catalogue), "uploads": bool(datasource_id)})
        return reply(request, {"chats": [{"id": f"report-{id}", "report_id": id, "title": item.get("caption") or item.get("name") or str(id)}
            for id, item in catalogue.items()], "total_count": len(catalogue), "uploads": bool(datasource_id), "model": settings["model"], "can_configure": vault is not None})

    async def configure(request):
        supplied = request.headers.get("X-Modus-ARM-Admin", "")
        if not vault or not secrets.compare_digest(supplied.encode(), admin_key.encode()):
            return reply(request, {"error": "Настройку GigaChat выполняет администратор АРМ."}, 403)
        values = await body(request)
        settings = {name: values.get(name, "") for name in fallback}
        if (not isinstance(settings["credential"], str) or not 20 <= len(settings["credential"].strip()) <= 2048
                or not isinstance(settings["model"], str) or not re.fullmatch(r"[A-Za-z0-9_.-]{1,80}", settings["model"])
                or settings["scope"] not in ("GIGACHAT_API_PERS", "GIGACHAT_API_B2B", "GIGACHAT_API_CORP")):
            return reply(request, {"error": "Проверьте ключ, модель и тип доступа GigaChat."}, 400)
        if not await check_provider(settings):
            return reply(request, {"error": "GigaChat не подтвердил ключ и модель. Предыдущее подключение сохранено."}, 422)
        temp = secret_file.with_suffix(".tmp")
        temp.write_bytes(vault.encrypt(json.dumps(settings).encode()))
        temp.replace(secret_file)
        return reply(request, {"gigachat": True, "model": settings["model"]})

    async def load_chat(client, id):
        if match := re.fullmatch(r"report-([1-9][0-9]{0,14})", id):
            report_id = int(match[1])
            item = (await reports(client)).get(report_id)
            if not item:
                return None
            state = store.load(arm, report_id=report_id)
            if not state:
                state = chat_state(arm, str(uuid5(NAMESPACE_URL, f"{arm}/report/{report_id}")), report_id)
            state["title"] = item.get("caption") or item.get("name") or str(report_id)
            return state
        try:
            id = str(UUID(id))
        except ValueError:
            return None
        state = store.load(arm, id=id) or chat_state(arm, id)
        if state["report_id"] and state["report_id"] not in await reports(client):
            return None
        return state

    async def post(request, client, state):
        settings = connection()
        if not settings["credential"]:
            return reply(request, {"error": "Администратор АРМ должен настроить GigaChat."}, 503)
        payload = await body(request)
        text = payload.get("text", "")
        if not isinstance(text, str) or len(text) > 2500:
            return reply(request, {"error": "Введите текст до 2500 символов."}, 400)
        upload, photo = payload.get("attachment"), payload.get("image")
        if upload is not None and not isinstance(upload, dict):
            return reply(request, {"error": "Прикрепите Excel или CSV заново."}, 400)
        if upload and (state["report_id"] or (state.get("attachment") or {}).get("import_id") or not datasource_id):
            return reply(request, {"error": "Для импорта начните новый дашборд и проверьте настройку источника загрузки."}, 400)
        decoded = await asyncio.to_thread(decode_upload, upload) if upload else None
        image = await asyncio.to_thread(decode_photo, photo) if photo else None
        if not (text.strip() or decoded or image):
            return reply(request, {"error": "Введите запрос или добавьте вложение."}, 400)

        if state["report_id"]:
            raw = await client.api_call("reports", "get", object_id=state["report_id"])
            if raw.get("status") != 200 or not raw.get("data"):
                return reply(request, {"error": "Не удалось прочитать отчёт."}, 404)
            report = raw["data"][0]
            state["datasets"] = {f["datasetId"]: f.get("datasetName") or str(f["datasetId"])
                for c in report.get("grid", {}).get("components", {}).values()
                for axis in c.get("config", {}).get("axes", []) for f in axis.get("fields", []) if f.get("datasetId")}
        elif not (decoded or state.get("attachment")):
            selected = payload.get("dataset_id")
            if selected is not None:
                available = await datasets(client)
                if type(selected) is not int or str(selected) not in available:
                    return reply(request, {"error": "Выберите доступный датасет."}, 400)
                state["datasets"] = {selected: available[str(selected)]}
            if not state.get("datasets"):
                return reply(request, {"error": "Для нового дашборда выберите датасет или приложите Excel/CSV."}, 400)

        if decoded:
            name, binary, sheets = decoded
            state["attachment"] = {"name": name, "sheets": describe(sheets)}
            state.pop("clarification", None)
            store.write(state, "source" + Path(name).suffix.lower(), binary)
        message = {"role": "user", "text": text.strip() or "Учитывай вложение при создании дашборда."}
        if decoded:
            message["attachment"] = decoded[0]
        if image:
            image_id = len(state["messages"])
            store.write(state, f"image-{image_id}.jpg", image[1])
            message["image"] = {"id": image_id, "name": image[0]}
        state["messages"].append(message)
        state.update(status="working", group_id=group_id, model=settings["model"])
        store.save(state)
        task = asyncio.create_task(generate(state, settings))
        jobs[state["id"]] = task
        task.add_done_callback(lambda done: finish(state["id"], done))
        return reply(request, public(state, request.path_params["chat"]), 202)

    async def dispatch(request: Request):
        if request.method == "OPTIONS":
            return await options(request)
        if not authorized(request):
            return reply(request, {"error": "Проверьте адрес и ключ подключения АРМ."}, 403)
        try:
            if request.method == "POST" and not request.path_params.get("chat") and request.url.path.endswith("/settings"):
                return await configure(request)
            if not (id := request.path_params.get("chat")):
                return await entry(request)
            client = await get_client()
            async with submit_lock:
                state = await load_chat(client, id)
                if state is None:
                    return reply(request, {"error": "Дашборд или чат недоступен."}, 404)
                if image := request.path_params.get("image"):
                    if image.isdecimal() and any(m.get("image", {}).get("id") == int(image) for m in state["messages"]):
                        path = store.file_path(state, f"image-{int(image)}.jpg")
                        if path.is_file():
                            return FileResponse(path, media_type="image/jpeg", headers=headers(request))
                    return reply(request, {"error": "Снимок недоступен."}, 404)
                if state["status"] == "working" and state["id"] not in jobs:
                    state["status"] = "error"
                    state["messages"].append({"role":"error", "text":"Запрос прерван. Продолжите по сохранённому отчёту."})
                    store.save(state)
                if request.method == "POST":
                    if state["id"] in jobs:
                        return reply(request, {"error": "Коллега уже запустил запрос по этому дашборду."}, 409)
                    return await post(request, client, state)
                return reply(request, public(state, id))
        except (AttachmentError, ValueError) as error:
            return reply(request, {"error": str(error) if isinstance(error, AttachmentError) else "Проверьте формат запроса."}, 400)
        except Exception as error:
            log.warning("Dashboard ARM request failed (%s)", type(error).__name__)
            return reply(request, {"error": "MCP не смог выполнить запрос к рабочему месту."}, 502)

    for path, methods in {"/status": ["GET"], "/settings": ["POST"], "/datasets": ["GET"], "/chats": ["GET"],
                          "/chats/{chat}": ["GET", "POST"], "/chats/{chat}/images/{image}": ["GET"]}.items():
        mcp.custom_route(PREFIX + path, methods=[*methods, "OPTIONS"], include_in_schema=False)(dispatch)

    async def close():
        if jobs:
            await asyncio.gather(*jobs.values(), return_exceptions=True)

    return close
