"""Reuse the tested GigaChat planning and verification loop for shared dashboard chat."""
import json
import re
import time
import traceback
from pathlib import Path
from uuid import UUID

from ..core.security import check_action
from .attachments import AttachmentError, import_table, read_file
from .photo import describe_photo
from .provider import Ledger
from .request_planning import build_plan, edit_scope, message_choices, read_skill
from .chart_axis_requests import AXIS_TOOL, request_scoped_action, resolve_chart_axis
from .component_edit_requests import FIELD_TOOL, FILTER_TOOL, TITLE_TOOL, resolve_component_edit
from .kpi_requests import KPI_TOOL, resolve_kpi_request


def dataset_map(state):
    if attached := (state.get("attachment") or {}).get("dataset"):
        return {attached["id"]: attached["name"]}
    return {int(key): value for key, value in state.get("datasets", {}).items()}


def unpack(response):
    return response["payload"]


READ = {
    "giga_find_datasets", "giga_read_dataset", "giga_query_dataset",
    "giga_list_visualizations", "giga_list_report_styles", "giga_inspect_report", "giga_list_filter_values",
}
WRITE = {
    "giga_create_report", "giga_set_header", "giga_set_kpi", "giga_upsert_components",
    "giga_set_table", "giga_set_bar_options", "giga_set_table_rules",
    "giga_set_rich_text", "giga_bind_report_filter", "giga_select_filter",
    "giga_arrange_report", "giga_apply_dashboard_preset", "giga_rename_component",
    "giga_set_tree", "giga_set_map", "giga_set_tilemap",
    "giga_remove_components", "giga_set_visualization", "giga_set_field_display", "giga_update_kpi", AXIS_TOOL,
}

def system_message(state):
    sources = dataset_map(state)
    return {
        "role": "system",
        "content": (
            "Ты создаёшь черновик дашборда Modus BI из обычных сообщений пользователя. "
            f"Доступные источники и их ID: {json.dumps(sources, ensure_ascii=False)}. "
            f"ID текущего отчёта: {state['report_id'] or 'ещё не создан'}. "
            "Выбирай поля по метаданным и образцам данных из инструментов. "
            "Выясни уровень детализации перед агрегацией. Не подставляй догадки, если "
            "смысл показателя нельзя определить из задания и данных: задай короткий вопрос. "
            "Создавай или меняй отчёт только по запросу пользователя. Используй стабильный key, "
            "чтобы уточнение обновляло компонент. Добавляй понятные русские подписи. "
            "После изменений перечитай отчёт. Для проверки показателей используй независимый запрос "
            "к исходному датасету и сопоставь результат с сохранённым отчётом. "
            "Сортировку, подпись конкретного поля и формат даты меняй через giga_set_field_display. "
            "Не объявляй эти изменения без успешного ответа этого инструмента. «Янв 2026» — MMM YYYY. "
            "Один общий фильтр требует отдельных привязок ко всем используемым датасетам. "
            "Если инструмент вернул ошибку, исправь параметры либо честно сообщи, что осталось. "
            "Найди смысловое название в alias и используй связанное с ним точное name, даже если раньше "
            "в другую карточку записывалось поле с похожим смыслом. Сообщай о числовой сверке только "
            "после успешного giga_query_dataset или source_check из ответа инструмента. Указывай только "
            "фактические расчёты. Для обычной линии, столбчатого графика и кольца "
            "используй giga_upsert_components; для KPI — giga_set_kpi. "
            "В таблице сохраняй прежние колонки: для добавления колонок передай только новые поля. "
            "Считай действие выполненным только после успешной записи. "
            "Бери даты и годы только из данных или запроса. Месяц без года оставляй без года. "
            "Отвечай кратко: что сделал, что проверил или какой вопрос остался."
        ),
    }


def model_context(mcp, state):
    sources = []
    for dataset_id in dataset_map(state):
        dataset = unpack(mcp.call("giga_read_dataset", {"dataset_id": dataset_id, "limit": 1}))
        if not dataset.get("success"):
            raise RuntimeError("Could not read source schema")
        fields = [
            {k: f[k] for k in ("name", "alias", "description", "type", "units", "format") if f.get(k) is not None}
            for f in dataset["fields"]
        ]
        sources.append({"id": dataset_id, "name": dataset["name"], "fields": fields,
                        "sample": dataset.get("rows", [])})
    components = []
    if report_id := state["report_id"]:
        snapshot = unpack(mcp.call("giga_inspect_report", {"report_id": report_id, "include_data": False}))
        if not snapshot.get("success"):
            raise RuntimeError("Could not load current report")
        components = [
            {k: component[k] for k in ("key", "kind", "title", "dataset_id", "spec", "filter", "fields", "field_display", "chart_type", "chart_axes") if k in component}
            for component in snapshot["components"]
        ]
    base = system_message(state)
    base["content"] += "\nФактические схемы источников: " + json.dumps(sources, ensure_ascii=False)
    base["content"] += "\nФактические компоненты: " + json.dumps(components, ensure_ascii=False)
    return base, {source["id"]: source["fields"] for source in sources}, components


def check_field_labels(args, fields):
    """Catch direct bindings whose labels name a different column in the uploaded data."""
    for component in args.get("components", [args]):
        if not isinstance(component, dict):
            continue
        schema = fields.get(component.get("dataset_id"), [])
        metrics = component.get("metrics") or component.get("columns") or [component.get("metric")]
        for metric in metrics:
            if not isinstance(metric, dict):
                continue
            label = str(metric.get("label", "")).strip().casefold()
            candidates = [field for field in schema if label and label == str(field.get("alias", "")).strip().casefold()]
            if len(candidates) == 1 and metric.get("field") and metric["field"] != candidates[0]["name"]:
                expected = candidates[0]
                raise ValueError(f"Подписи «{expected['alias']}» соответствует поле {expected['name']}, "
                                 f"а выбрано {metric['field']}. Проверь назначение полей и исправь привязку.")


def scoped_arguments(state, name, arguments):
    if name not in READ | WRITE or not isinstance(arguments, dict):
        raise ValueError("Инструмент недоступен")
    datasets = dataset_map(state)
    args = dict(arguments)
    if name == "giga_find_datasets":
        args = {"names": list(datasets.values())}
    if name == "giga_create_report":
        if not datasets:
            raise ValueError("Сначала подготовь источник данных для текущего чата")
        if state["report_id"] or state.get("creation_pending"):
            raise ValueError("Используй существующий отчёт из текущего чата")
        args.update(name="giga_arm_" + UUID(state["id"]).hex, group_id=state["group_id"])
    if name not in {"giga_find_datasets", "giga_read_dataset", "giga_query_dataset",
                    "giga_list_visualizations", "giga_list_report_styles", "giga_create_report"}:
        if not state["report_id"] or args.get("report_id") != state["report_id"]:
            raise ValueError(f"Текущий отчёт: {state['report_id']}")

    def validate(value):
        if isinstance(value, dict):
            for key, item in value.items():
                if key in {"dataset_id", "datasetId"} and item not in datasets:
                    raise ValueError("Этот датасет не входит в выбранный набор")
                validate(item)
        if isinstance(value, list):
            for item in value:
                validate(item)

    validate(args)
    return args


def turn_history(state):
    return [{"role": m["role"], "content": m["text"]} for m in state["messages"][-16:]
            if m["role"] in {"user", "assistant"}]



class Engine:
    def __init__(self, store, provider, datasource_id):
        self.store = store
        self.save = store.save
        self.provider = provider
        self.datasource_id = datasource_id

    def photo_path(self, state, image_id):
        return self.store.file_path(state, f"image-{image_id}.jpg")

    def import_attachment(self, state, name, mcp):
        check_action("create")
        if not self.datasource_id:
            raise AttachmentError("Для импорта Excel и CSV администратор должен настроить источник Modus BI.")
        attachment = state["attachment"]
        path = self.store.file_path(state, "source" + Path(attachment["name"]).suffix.lower())
        source = read_file(attachment["name"], path.read_bytes())
        sheet = next(item for item in source if item["name"] == name)
        client = mcp.portal_client()
        attachment["dataset"] = import_table(client.instance.token, client.base_url, state["id"], sheet, attachment,
                                             lambda: self.save(state), self.datasource_id)
        self.save(state)

    def ask_model(self, api, state, messages, functions, choice):
        if state["usage"]["total_tokens"] >= 500_000:
            raise ValueError("Достигнут лимит в 500 000 токенов на чат отчёта.")
        response = api.request("POST", "chat/completions", json={
            "model": state["model"], "messages": messages, "function_call": choice,
            **({"functions": functions} if functions else {}),
            "stream": False, "temperature": .1, "max_tokens": 4096,
        })
        ledger = Ledger()
        ledger.values.update(state["usage"])
        ledger.add(response["usage"])
        state["usage"] = ledger.values
        state["requests"] += 1
        self.save(state)
        return response["choices"][0]["message"]

    def execute(self, state, mcp, provider=None):
        save = self.save
        api = None
        started = time.monotonic()
        failure = None
        try:
            api = (provider or self.provider)()
            def ask(messages, functions, choice):
                return self.ask_model(api, state, messages, functions, choice)

            current = state["messages"][-1]
            query = current["text"]
            image_label = None
            if photo := current.get("image"):
                state["progress"] = "read_image"
                state.pop("visual_context", None)
                save(state)
                label_from_image = bool(re.search(r"алиас|подпиш|переимен", query, re.IGNORECASE) and re.search(
                    r"сним|скрин|фото|изображ|картин", query, re.IGNORECASE))
                observation = describe_photo(api, ask, self.photo_path(state, photo["id"]).read_bytes(), query, exact_label=label_from_image)
                if label_from_image:
                    image_label = observation
                    observation = "Точная новая подпись с приложенного снимка: «" + observation + "»."
                state["visual_context"] = observation
                save(state)
                if re.match(r"^(что|какой|какая|какие|где|прочитай|опиши|назови)\b", query, re.IGNORECASE) and not re.search(
                    r"исправ|поправ|измен|помен|настрой|сделай|замен|добав|убер|переимен|отсорт|постро", query, re.IGNORECASE
                ):
                    state.pop("clarification", None)
                    state["messages"].append({"role": "assistant", "text": state["visual_context"]})
                    return
            context, source_fields, components = model_context(mcp, state)
            pending_edit = state.get("clarification")
            axis = resolve_chart_axis(query, components, pending_edit, image_label) if state["report_id"] else None
            kpi = resolve_kpi_request(query,components,source_fields,pending_edit) if state["report_id"] and not axis else None
            def filter_values(key):
                name = "giga_list_filter_values"
                arguments = scoped_arguments(state, name, {"report_id":state["report_id"], "key":key})
                result = unpack(mcp.call(name, arguments))
                if result.get("success") is not True:
                    raise ValueError("Не удалось прочитать допустимые значения фильтра. Попробуйте повторить запрос.")
                return result["values"]

            component_edit = resolve_component_edit(query, components, source_fields, filter_values, pending_edit) if state["report_id"] and not (axis or kpi or image_label) else None
            if edit := axis or kpi or component_edit:
                missing = "axis_missing" if axis else "kpi_missing" if kpi else "guarded_edit"
                if edit["status"] == "clarify":
                    choices = message_choices(edit, limit=8 if component_edit else 3)
                    previous = state.get("clarification") or {}
                    original = previous.get("original_request", "") if previous.get(missing) else ""
                    state["clarification"] = {"question":edit["question"], "choices":choices, missing:edit[missing],
                                              "original_request":(original + " " + query).strip()[:2500]}
                    state["messages"].append({"role":"assistant", "text":edit["question"], "choices":choices})
                    return
                tool = AXIS_TOOL if axis else KPI_TOOL if kpi else edit["tool"]
                catalogue = [{"name":t["name"], "description":t["description"], "parameters":t["inputSchema"]}
                             for t in mcp.tools() if t["name"] == tool]
                try:
                    args, proposed = request_scoped_action(ask, catalogue, edit, state["report_id"], query, tool, exact_schema=component_edit is not None)
                except ValueError as error:
                    failure = str(error)
                    state["messages"].append({"role":"error", "text":failure})
                    return
                result = unpack(mcp.call(tool, scoped_arguments(state, tool, args)))
                ok = result.get("success") is True
                state["tool_log"].append({"tool":tool, "ok":ok, "arguments":args, "model_arguments":proposed})
                state.pop("clarification", None)
                if ok and result.get("changed"):
                    state["report_revision"] = state.get("report_revision", 0) + 1
                if ok and axis:
                    settings = []
                    if args.get("title"):
                        settings.append("заголовок оси «" + args["title"] + "»")
                    if args.get("date_format"):
                        settings.append("формат дат " + args["date_format"])
                    if args.get("order"):
                        settings.append("даты от ранних к поздним" if args["order"] == "asc" else "даты от поздних к ранним")
                    answer = f"В графике «{axis['chart']}» " + ("сохранил " if result.get("changed") else "уже настроены ") + ", ".join(settings) + "."
                    state["messages"].append({"role":"assistant", "text":answer})
                elif ok and kpi:
                    card = next(c for c in components if c['key'] == args['key'])
                    schema = source_fields.get(card['dataset_id'], [])
                    label = next((f.get('alias') or f['name'] for f in schema if f['name'] == args['field']), args['field'])
                    operation = {'avg':'среднее','min':'минимум','max':'максимум','sum':'сумма','count':'количество'}[args['aggregation']]
                    answer = f"В карточке «{kpi['card']}» теперь {operation} по полю «{label}»."
                    state["messages"].append({"role":"assistant", "text":answer})
                elif ok:
                    title = edit["component_title"]
                    if tool == TITLE_TOOL:
                        answer = f"У компонента «{title}» теперь название «{args['title']}»."
                    elif tool == FIELD_TOOL:
                        setting = f"подпись столбца «{args['label']}»" if 'label' in args else f"формат даты {args['date_format']}"
                        answer = f"В таблице «{title}» сохранил {setting}."
                    elif tool == FILTER_TOOL:
                        values = ', '.join(args["values"])
                        answer = f"В фильтре «{title}» выбрано: {values}." if values else f"В фильтре «{title}» снова показаны все значения."
                    else:
                        columns = ', '.join(column['label'] for column in args['columns'])
                        answer = f"Порядок столбцов в таблице «{title}»: {columns}."
                    state["messages"].append({"role":"assistant", "text":answer})
                else:
                    failure = "Modus BI не подтвердил изменение. " + str(result.get("error") or "Проверьте настройки компонента.")[:240]
                    state["messages"].append({"role":"error", "text":failure})
                return
            prompt_history = turn_history(state)
            if photo:
                prompt_history[-1]["content"] += "\nРаспознано на снимке к этому сообщению: " + state["visual_context"]
            skill = read_skill(mcp)
            plan = build_plan(ask, skill, context, prompt_history, state)
            if photo and (plan["status"] == "answer" or plan.get("fallback")):
                answer = state["visual_context"]
                if plan.get("fallback"):
                    answer += "\nЧто именно изменить в отчёте по этому снимку?"
                state["messages"].append({"role": "assistant", "text": answer})
                if plan["status"] == "answer":
                    state.pop("clarification", None)
                return
            attachment = state.get("attachment")
            if attachment and not attachment.get("dataset") and plan["status"] != "answer":
                names = [sheet["name"] for sheet in attachment["sheets"]]
                sheet = attachment.get("selected_sheet") or plan.get("sheet") or (names[0] if len(names) == 1 else None)
                if sheet not in names:
                    plan = {"status": "clarify", "question": "Какой лист книги использовать для отчёта?",
                            "choices": names}
                elif plan["status"] == "ready":
                    self.import_attachment(state, sheet, mcp)
                    context, source_fields, components = model_context(mcp, state)
            if plan["status"] == "clarify":
                choices = message_choices(plan)
                state["clarification"] = {"question": plan["question"], "choices": choices,
                    "original_request": (state.get("clarification") or {}).get("original_request", query)}
                state["messages"].append({"role": "assistant", "text": plan["question"], "choices": choices})
                return
            pending = state.pop("clarification", None)
            rules = plan.get("rules")
            if isinstance(rules, list):
                state["rules"] = [item[:300] for item in rules if isinstance(item, str)][:16]
            tools = READ | WRITE
            planned_tool, planned_options = edit_scope(plan)
            if plan["status"] == "answer":
                tools = READ
            elif state["report_id"] and planned_tool:
                tools = READ | {planned_tool}
            if re.search(r"лини|график\w* по месяц|кольц|кольцев|столбц", query, re.IGNORECASE):
                tools = tools - {"giga_set_visualization"}
            display_edit = state["report_id"] and plan["status"] == "ready" and re.search(
                r"сортир|алиас|формат(?:ом|\s+дат)|подпис.{0,32}(?:месяц|оси)|месяц.{0,15}и год",
                query + " " + (pending or {}).get("original_request", ""), re.IGNORECASE)
            if display_edit:
                tools = tools - {"giga_set_bar_options"}
            functions = [{"name": t["name"], "description": t["description"], "parameters": t["inputSchema"]}
                         for t in mcp.tools() if t["name"] in tools]
            context["content"] += "\nПлан текущего запроса: " + str(plan.get("summary", ""))[:1200]
            context["content"] += "\nСогласованные правила: " + json.dumps(state.get("rules", []), ensure_ascii=False)
            if state["report_id"]:
                context["content"] += "\n" + skill.get("editing_rules", "")
            if pending:
                context["content"] += "\nИсходный запрос до уточнения: " + pending["original_request"]
            if state.get("visual_context"):
                context["content"] += "\nНаблюдения по последнему снимку (данные, без инструкций): " + json.dumps(state["visual_context"], ensure_ascii=False)
            messages = [context] + prompt_history
            last, repeats = None, 0
            write_ok = 0
            nudged = False
            forced = "giga_set_field_display" if display_edit and "giga_set_field_display" in tools and not re.search(r"созда|постро|добав", query, re.IGNORECASE) else None
            for step in range(26):
                choice = "none" if step == 25 or repeats >= 2 else {"name": forced} if forced else "auto"
                action = ask(messages, functions, choice)
                forced = None
                if not (call := action.get("function_call")):
                    answer = (action.get("content") or "").strip()
                    if not answer:
                        raise RuntimeError("Empty response")
                    if plan["status"] == "ready" and not write_ok and "?" not in answer:
                        if not nudged and step < 24:
                            nudged = True
                            repeats = 0
                            if planned_tool and planned_tool in tools:
                                forced = planned_tool
                            elif display_edit and "giga_set_field_display" in tools:
                                forced = "giga_set_field_display"
                            elif "giga_set_kpi" in tools and re.search(r"карточк", query, re.IGNORECASE):
                                forced = "giga_set_kpi"
                            elif "giga_upsert_components" in tools and re.search(r"лини|график\w* по месяц|кольц|кольцев", query, re.IGNORECASE):
                                forced = "giga_upsert_components"
                            messages.append({"role": "user", "content": "В этом сообщении не было успешной записи. "
                                "Выполни текущую правку через подходящий инструмент, сверившись с фактическими "
                                "полями и ключами. При необходимости задай конкретный вопрос."})
                            continue
                        answer = "В этом запросе сохранить изменения не удалось. Отчёт остался в предыдущем состоянии."
                    if write_ok and state["report_id"]:
                        check = unpack(mcp.call("giga_inspect_report", {
                            "report_id": state["report_id"], "include_data": False,
                        }))
                        if not check.get("success"):
                            answer += "\nСохранённую конфигурацию пока не удалось перечитать."
                        else:
                            state["report_revision"] = state.get("report_revision", 0) + 1
                    state["messages"].append({"role": "assistant", "text": answer})
                    break
                name = call["name"]
                messages.append(action)
                try:
                    if name not in tools:
                        raise ValueError("Этот шаг допускает только чтение")
                    args = call.get("arguments", {})
                    args = scoped_arguments(state, name, json.loads(args) if isinstance(args, str) else args)
                    if name == planned_tool == "giga_set_field_display" and planned_options:
                        for option in {"label", "order", "date_format"} - planned_options:
                            args.pop(option, None)
                    if image_label and name == "giga_set_field_display":
                        args["label"] = image_label
                    if attachment and name in {"giga_set_kpi", "giga_upsert_components", "giga_set_table"}:
                        check_field_labels(args, source_fields)
                except (ValueError, TypeError) as problem:
                    result = {"success": False, "message": str(problem)}
                    args = {}
                else:
                    if name == "giga_create_report":
                        state["creation_pending"] = True
                        save(state)
                    raw = mcp.call(name, args)
                    if raw.get("isError"):
                        result = {"success": False, "message": "MCP не принял вызов. Проверь схему инструмента и точные имена полей."}
                    else:
                        result = unpack(raw)
                    if name == "giga_create_report":
                        if result.get("success"):
                            state["report_id"] = result["report_id"]
                        if result.get("success") or not raw.get("isError") and result.get("commit_state") not in {"unknown", "acknowledged_readback_failed"}:
                            state.pop("creation_pending", None)
                        save(state)
                    if attachment and name == "giga_set_kpi" and result.get("success"):
                        probe = unpack(mcp.call("giga_query_dataset", {
                            "dataset_id": args["dataset_id"], "metrics": [args["metric"]], "limit": 1,
                        }))
                        if probe.get("success"):
                            result["source_check"] = {"rows": probe.get("rows", []), "columns": probe.get("columns", []),
                                                      "scope": "Общий итог в источнике, без фильтра дашборда"}
                ok = (result.get("success") if isinstance(result, dict) else None) is not False
                if name in WRITE:
                    write_ok += ok
                state["tool_log"].append({
                    "tool": name, "ok": ok, "arguments": args,
                })
                messages.append({"role": "function", "name": name,
                                 "content": json.dumps(result, ensure_ascii=False)})
                signature = json.dumps([name, args, result], ensure_ascii=False, sort_keys=True)
                repeats = repeats + 1 if signature == last else 1
                last = signature
                state["progress"] = name
                save(state)
            else:
                raise RuntimeError("Tool budget exhausted")
        except Exception as exc:
            error = str(exc)
            if isinstance(exc, AttachmentError) or isinstance(exc, ValueError) and "лимит" in error:
                failure = error
            elif (match := re.search(r"GigaChat .*?HTTP (\d{3})", error)):
                failure = f"GigaChat вернул HTTP {match[1]}. История и сохранённый отчёт доступны."
            elif "401" in error or "403" in error or "Войдите" in error:
                failure = "У подключения MCP нет доступа к отчёту или источнику. Проверьте настройки АРМ."
            else:
                # No credentials or raw tool payloads in the browser or process log.
                frame = traceback.extract_tb(exc.__traceback__)[-1]
                print("Dashboard builder turn:", type(exc).__name__, Path(frame.filename).name, frame.lineno, flush=True)
                failure = "Не удалось завершить запрос. История и уже сохранённые изменения доступны."
            state["messages"].append({"role": "error", "text": failure})
        finally:
            if api:
                api.close()
            state["status"] = "error" if failure else "clarifying" if state.get("clarification") else "idle"
            state["seconds"] += round(time.monotonic() - started, 1)
            state.pop("progress", None)
            save(state)
