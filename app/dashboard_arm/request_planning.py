"""Run the MCP request skill through the GigaChat client before write tools."""

import json


URI = "modus://skills/dashboard-request"
EDIT_TOOLS = {"giga_set_field_display", "giga_rename_component", "giga_update_kpi", "giga_select_filter"}


def edit_scope(plan):
    tool = plan.get("edit_tool")
    options = plan.get("field_options")
    fields = {v for v in options if isinstance(v, str)} & {"label", "order", "date_format"} if isinstance(options, list) else set()
    return tool if isinstance(tool, str) and tool in EDIT_TOOLS else None, fields


def read_skill(mcp):
    result = mcp.request("resources/read", {"uri": URI})
    skill = json.loads(result["contents"][0]["text"])
    if skill.get("version") != 1 or skill.get("function", {}).get("name") != "dashboard_request_plan":
        raise RuntimeError("Unsupported dashboard request skill")
    return skill


def build_plan(request, skill, context, history, state):
    function = skill["function"]
    attachment = state.get("attachment")
    facts = {"report_id": state["report_id"], "rules": state.get("rules", []),
             "pending_question": state.get("clarification")}
    if attachment:
        facts["attachment"] = {key: attachment[key] for key in ("name", "sheets", "selected_sheet") if key in attachment}
    if state.get("visual_context"):
        facts["last_image_observations"] = state["visual_context"]
    messages = [{"role": "system", "content": skill["instructions"] +
                 "\nПроверенный контекст: " + context["content"].partition("\nФактические схемы источников: ")[2] +
                 "\nСостояние диалога: " + json.dumps(facts, ensure_ascii=False)}] + list(history)
    for choice in ({"name": function["name"]}, "none"):
        if choice == "none":
            messages[0] = {**messages[0], "content": messages[0]["content"] +
                           "\nСлужебный вызов недоступен. Верни только JSON с полями status (ready, clarify или answer), "
                           "summary, question, choices, sheet, rules, edit_tool, field_options. В question укажи вопрос только при clarify."}
        response = request(messages, [function] if choice != "none" else [], choice)
        call = response.get("function_call") or {}
        payload = (response.get("content") or "").strip() if choice == "none" else call.get("arguments", {})
        if isinstance(payload, str) and payload.startswith("```json") and payload.endswith("```"):
            payload = payload[7:-3].strip()
        try:
            plan = json.loads(payload) if isinstance(payload, str) else payload
        except ValueError:
            plan = {}
        if (choice == "none" or call.get("name") == function["name"]) and isinstance(plan, dict) and plan.get("status") in {"ready", "clarify", "answer"}:
            if plan["status"] != "clarify" or isinstance(plan.get("question"), str) and plan["question"].strip():
                return plan
    return {"status": "clarify", "question": "Какой результат нужно показать в отчёте?", "fallback": True}


def message_choices(plan, limit=3):
    values = plan.get("choices") or []
    if not isinstance(values, list):
        return []
    return [item.strip()[:120] for item in values if isinstance(item, str) and item.strip()][:limit]
