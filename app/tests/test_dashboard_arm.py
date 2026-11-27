"""Exercise the ARM HTTP routes and real MCP dispatch with an isolated portal fixture."""
import asyncio
import base64
import json
from uuid import uuid4

import httpx
import pytest
from cryptography.fernet import Fernet
from mcp.server.fastmcp import FastMCP

from app.core.security import SecurityMode, get_security_mode, set_security_mode
from app.dashboard_arm import http
from app.tools.gigachat_profile import META
from app.tools.gigachat_tools import register_gigachat_tools
from app.tests.test_gigachat_profile import Portal


ORIGIN = "https://modus.example.test"
KEY = "shared-fixture-key-only-not-secret"
ADMIN = "administrator-fixture-key-only"
ROOT = "/api/dashboard-arm/dashboard-builder"


class GigaFixture:
    calls = []

    def __init__(self, credential, *args):
        self.credential = credential

    def request(self, method, path, **kwargs):
        self.calls.append(path)
        if path == "models":
            if self.credential.startswith("rejected"):
                raise RuntimeError("Test provider rejects key")
            return {"data": [{"id": "GigaChat-3-Pro"}, {"id": "GigaChat-3-Max"}]}
        assert method == "POST" and path == "chat/completions"
        data = kwargs["json"]
        tool = data["function_call"]
        if tool == {"name": "dashboard_request_plan"}:
            message = {"function_call": {"name": "dashboard_request_plan", "arguments": {"status": "ready", "summary": "Создать отчёт"}}}
        elif tool == {"name": "giga_set_field_display"}:
            args = json.loads(data["messages"][0]["content"].split("параметры: ", 1)[1])
            message = {"function_call": {"name": "giga_set_field_display", "arguments": args}}
        elif actions := [row for row in data["messages"] if row.get("role") == "function"]:
            if actions[-1]["name"] == "giga_create_report":
                report_id = json.loads(actions[-1]["content"])["report_id"]
                message = {"function_call": {"name": "giga_set_kpi", "arguments": {"report_id":report_id,
                    "dataset_id":1, "key":"facts", "title":"Факт", "metric":{"kind":"sum","field":"actual","label":"Факт"}}}}
            else:
                message = {"content": "Дашборд создан"}
        else:
            message = {"function_call": {"name": "giga_create_report", "arguments": {"name":"placeholder", "caption":"Рабочий отчёт", "group_id":42}}}
        return {"usage": {"total_tokens": 3}, "choices": [{"message": message}]}

    def close(self):
        pass


@pytest.fixture
async def arm(monkeypatch, tmp_path):
    old = get_security_mode()
    set_security_mode(SecurityMode.READWRITE)
    portal = Portal()
    portal.reports[77] = {"ID":77, "caption":"Архив", "deleted":1}
    mcp = FastMCP("shared-test")
    GigaFixture.calls = []
    monkeypatch.setattr(http, "GigaAPI", GigaFixture)
    for key, value in {"MODUSBI_ARM_ACCESS_KEY":KEY, "MODUSBI_ARM_ADMIN_KEY":ADMIN, "MODUSBI_ARM_ORIGIN":ORIGIN,
                       "MODUSBI_ARM_SECRET_KEY":Fernet.generate_key().decode(), "MODUSBI_ARM_DATA_DIR":str(tmp_path),
                       "MODUSBI_ARM_ID":"dashboard-builder", "MODUSBI_ARM_REPORT_GROUP":"1",
                       "MODUSBI_ARM_IMPORT_SOURCE":"0", "GIGACHAT_MODEL":"GigaChat-3-Pro", "GIGACHAT_CREDENTIALS":"fixture-provider-key"}.items():
        monkeypatch.setenv(key, value)

    async def get_client():
        return portal

    register_gigachat_tools(mcp, get_client)
    http.register_dashboard_arm(mcp, get_client)
    web = mcp.streamable_http_app()
    transport = httpx.ASGITransport(app=web)
    headers = {"Origin":ORIGIN, "X-Modus-ARM-Key":KEY}
    try:
        async with httpx.AsyncClient(transport=transport, base_url="http://test", headers=headers) as first, \
                httpx.AsyncClient(transport=transport, base_url="http://test", headers=headers) as second:
            yield portal, mcp, first, second, tmp_path
    finally:
        portal.db.close()
        set_security_mode(old)


async def finished(client, chat):
    for _ in range(120):
        response = await client.get(f"{ROOT}/chats/{chat}")
        assert response.status_code == 200
        state = response.json()
        if state["status"] != "working":
            return state
        await asyncio.sleep(.025)
    pytest.fail("ARM did not finish")


async def test_catalogue_uses_report_inventory_and_filters_deleted(arm):
    _, _, first, second, _ = arm
    response = await first.get(ROOT + "/chats")
    assert response.status_code == 200
    assert response.headers["Access-Control-Allow-Origin"] == ORIGIN
    assert response.json()["chats"] == [{"id":"report-42", "report_id":42, "title":"Fixture"}]
    assert response.json()["total_count"] == 1
    assert (await second.get(ROOT + "/chats/report-42")).json()["messages"] == []
    assert (await first.get(ROOT + "/chats/report-77")).status_code == 404
    assert (await first.get(ROOT + "/chats", headers={"X-Modus-ARM-Key":"bad"})).status_code == 403
    assert (await first.get(ROOT + "/chats", headers={"Origin":"https://invalid.example.test"})).status_code == 403
    assert (await first.get("/api/dashboard-arm/other-arm/chats")).status_code == 403
    assert (await first.options(ROOT + "/chats")).status_code == 204


async def test_two_connections_continue_one_dashboard_chat(arm):
    portal, mcp, first, second, _ = arm
    await mcp.call_tool("giga_set_table", {"report_id":42,"key":"customers","title":"Заказчики","dataset_id":1,
        "columns":[{"field":"customer","label":"Клиент","format":"text"},{"field":"actual","label":"Факт","format":"number"}]})
    page = ROOT + "/chats/report-42"
    before = portal.calls[("reports", "update")]
    assert (await first.post(page,json={"text":"Поменяй заголовок колонки «Факт»."})).status_code == 202
    state = await finished(second, "report-42")
    assert state["status"] == "clarifying", state
    assert state["messages"][-1]["text"] == "Как назвать столбец «Факт» в таблице «Заказчики»?"
    assert GigaFixture.calls == [] and portal.calls[("reports", "update")] == before
    assert (await second.post(page,json={"text":"Выполнено"})).status_code == 202
    shared = await finished(first, "report-42")
    assert shared["status"] == "idle" and shared["report_revision"] == 1, shared
    assert len(shared["messages"]) == 4 and shared["messages"][-1]["text"].endswith("«Выполнено».")
    assert portal.calls[("reports", "update")] == before + 1
    config = next(iter(portal.reports[42]["grid"]["components"].values()))["config"]
    assert next(iter(config[META]["field_display"].values()))["label"] == "Выполнено"


async def test_new_dashboard_moves_draft_history_to_report(arm):
    portal, _, first, second, _ = arm
    draft = str(uuid4())
    route = ROOT + "/chats/" + draft
    assert (await first.get(route)).json()["report_id"] is None
    assert (await first.post(route,json={"text":"Создай отчёт"})).status_code == 400
    result = await first.post(route,json={"text":"Создай отчёт", "dataset_id":1})
    assert result.status_code == 202, result.text
    created = await finished(first, draft)
    assert created["status"] == "idle" and created["report_id"] > 0, created
    id = created["report_id"]
    assert (await second.get(ROOT + "/chats")).json()["total_count"] == 2
    assert (await second.get(f"{ROOT}/chats/report-{id}")).json()["messages"] == created["messages"]
    assert portal.calls[("reports", "create")] == 1
    components = portal.reports[id]["grid"]["components"]
    assert next(iter(components.values()))["config"][META]["spec"]["metrics"][0]["field"] == "actual"


async def test_admin_key_update_is_protected_and_secret_is_encrypted(arm):
    _, _, first, second, tmp = arm
    values = {"credential":"fixture-secret-for-new-scope", "model":"GigaChat-3-Max", "scope":"GIGACHAT_API_B2B"}
    assert (await first.post(ROOT + "/settings",json=values)).status_code == 403
    response = await first.post(ROOT + "/settings",json=values,headers={"X-Modus-ARM-Admin":ADMIN})
    assert response.json() == {"gigachat":True,"model":"GigaChat-3-Max"}, response.text
    cipher = (tmp / "gigachat.enc").read_bytes()
    assert values["credential"].encode() not in cipher
    rejected = await first.post(ROOT + "/settings",json={**values,"credential":"rejected-fake-provider-credential"}, headers={"X-Modus-ARM-Admin":ADMIN})
    assert rejected.status_code == 422 and (tmp / "gigachat.enc").read_bytes() == cipher
    assert (await second.get(ROOT + "/status")).json()["model"] == "GigaChat-3-Max"


async def test_image_validation_keeps_original_history_on_failure(arm):
    _, _, first, _, _ = arm
    response = await first.post(ROOT + "/chats/report-42",json={"text":"Посмотри изображение", "image":{
        "name":"test.png", "data":base64.b64encode(b"not an image").decode()}})
    assert response.status_code == 400
    assert (await first.get(ROOT + "/chats/report-42")).json()["messages"] == []
