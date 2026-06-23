---
name: component-deep-settings
description: Deeply analyze ALL config-panel settings of one ModusBI component — enumerate every control, map UI label → real JSON path → MCP slug, classify the relationship (linked/alias/mismatch/no-slug/undoc), write a per-component analysis file
allowed-tools: Read, Glob, Grep, Bash, mcp__playwright__browser_navigate, mcp__playwright__browser_snapshot, mcp__playwright__browser_take_screenshot, mcp__playwright__browser_click, mcp__playwright__browser_type, mcp__playwright__browser_fill_form, mcp__playwright__browser_hover, mcp__playwright__browser_drag, mcp__playwright__browser_select_option, mcp__playwright__browser_press_key, mcp__playwright__browser_evaluate, mcp__playwright__browser_wait_for, mcp__modusbi__report_operations, mcp__modusbi__component_crud
context: fork
user-invocable: true
---

Глубокий разбор **всех** настроек одного компонента ModusBI: для КАЖДОГО контрола
config-панели определить **UI-название → реальный JSON-путь → MCP-slug** и
**классифицировать связь**. Цель — научиться **читать и понимать любую настройку**:
что она меняет в JSON и можно ли её задать через MCP. **Фиксы не делаем** — только
анализ и фиксация. Механика добавления компонента — скилл `portal-component-probe`
(Live-факты). Доступ к порталу из `.env`: `${MODUSBI_URL}` + `${MODUSBI_E2E_LOGIN}`/`${MODUSBI_E2E_PASSWORD}`
(реальные значения в скилле НЕ хранятся; прочитай их перед логином, напр. `grep MODUSBI_ .env`).

## Три источника истины

| Точка | Что | Откуда |
|---|---|---|
| **A** = куда пишет ФРОНТ | реальный JSON-путь контрола | diff сырого `config` (change→save→**browser-fetch**, см. ниже) |
| **B** = есть ли MCP-slug | имя slug для `config_overrides` | `docs/architecture/components/slugs/by-type.md`, `component_crud(action="list_slugs")` |
| **C** = куда пишет MCP | JSON-путь, который реально пишет handler | `app/tools/config_schema.py` (SLUG_SCHEMA `json_path` + apply-handler) |

> ⚠️ **Ground-truth A — ТОЛЬКО browser-fetch, НЕ MCP `get`.** `report_operations(get)`
> и `component_crud(get)` отдают обработанный summary / 6-ключевой whitelist — **сырого
> `config` в них нет** (`component_crud.py:1006-1037`, `report_operations.py:_get_report_info`).
> Diff по ним почти ничего не видит — это была главная ошибка ранней версии метода.
> Сырой config (=A):
> ```js
> browser_evaluate(function=`async () => {
>   const t = JSON.parse(localStorage.getItem('hs_bi')).user.token;
>   const j = await (await fetch('/v1/api/reports/<ID>',{headers:{Authorization:'Bearer '+t},credentials:'include'})).json();
>   const rep = Array.isArray(j) ? j[0] : j;        // ответ — ГОЛЫЙ массив [report]
>   return JSON.stringify(rep.grid.components['<idx>'].config);
> }`)
> ```

**Связь определяется сравнением A и C** (НЕ slug-имени и json-пути!):

| Метка | Условие | Смысл |
|---|---|---|
| ✅ `linked` | есть slug, C == A, имя slug == путь | работает, имена совпадают |
| 🔵 `alias` | есть slug, C == A, но **имя slug ≠ JSON-путь** | **работает; ОБЯЗАТЕЛЬНО записать маппинг slug→JSON** |
| 🔴 `mismatch` | есть slug, **C ≠ A** | MCP пишет не туда → silent-ignore кандидат-баг |
| ⚪ `no-slug` | slug нет | через `config_overrides` не задать |
| 📄 `undoc-json` | A нет в SLUG_REFERENCE | пробел документации |

> 🔵 **alias — отмечать ВСЕГДА явно**: «slug `X` → JSON `Y`». Это не баг, но без
> записи маппинга настройку либо примут за баг, либо будут искать не тот ключ.
> Пример: `data.rowsLimit` → `config.rowsLimit`; `axes.categoryGrid` →
> `config.axes[categories].showgrid`.

## Процедура (на один компонент)

### Шаг 0. Подготовка
1. `report_operations(create, name="deep_<class>", caption="...", group_id=<TEST_GROUP_ID>)` → report_id.
   `<TEST_GROUP_ID>` — любая тестовая группа отчётов в песочнице (узнать: `reportgroup_operations(action="list")`).
2. Добавить компонент с минимумом данных через MCP (быстро):
   `component_crud(add, report_id, component_type="<Class>", title="deep", dataset_id=<DS_ID>, category_field="<dim>", value_field="<metric>", aggregation="sum")` — **`title=` обязателен**, без него add падает (поля под тип; для no-data типов — без data). `<DS_ID>` — любой датасет с одним измерением (категория) и одной числовой метрикой; `<dim>`/`<metric>` — их технические имена.
3. Браузер: открыть `/report/{id}` → login → конструктор → открыть настройку компонента 0
   (`.hsEditComponent` через JS-клик) → вкладка «Настройки компонента отображения».

### Шаг 1. ENUMERATE — перечислить ВСЕ контролы (сначала!)
**До любого маппинга** пройти все секции config-панели и выписать каждый контрол.
- Раскрыть каждую секцию/вкладку, **проскроллить** панель до конца.
- Заполнить чеклист в `UI_SETTINGS_CHECKLIST.md` (секция компонента): каждый контрол `[ ]`.
- **Привязывать контрол к СЕКЦИИ** (лейблы повторяются: «Сглаживание»/«Толщина»/«Размер»
  есть и в «Основной стиль», и в per-series «Стилизация»). Запись: `Секция → Контрол`.
- **Собирать `[title]`-атрибут** обёртки контрола — UI иногда отдаёт имя slug прямо
  (`chart.datarowCount`, `chart.borderWidth`) → подсказка для B. **Непостоянно** (на Pie
  отсутствует) — оппортунистически, не основной источник; основной B — grep `config_schema.py`.
- **Контейнер секций — `.hsChartSettings`** (правый drawer), секция `.hsSettingsSection.dd`,
  заголовок `.header > .sectionTitle`. НЕ `.hsComponentEditor` (там только Save/Cancel).
- **Рекомендуемый энумератор:** TreeWalker-дамп по `.hsChartSettings` в порядке документа
  (текст-листья + маркеры `<input>`/`[title]`/значения по секциям) — надёжнее, чем
  a11y-снапшот и чем привязка лейбл↔контрол. Скриншоты секций: `.playwright-mcp/<class>_settings_<N>.png`.
- **Условные контролы**: часть появляется только после выбора в dropdown (напр. donut →
  «Отображать итог») — пере-снять дамп секции после каждого переключения mode-dropdown.
- Цель: **ни одна настройка не пропущена**. Список контролов фиксируется ДО разбора.

### Шаг 2. MAP — определить JSON каждого контрола (ground truth A)
По секциям, малыми батчами (1–3 контрола):
1. baseline: **browser-fetch** сырого config (см. блок выше) → A0.
2. В UI изменить контрол(ы) на отличимое значение → «Сохранить» **компонента**
   (scope `.hsComponentEditor button`, проверить закрытие) → «Сохранить отчёт»
   (`button[title="Сохранить отчет"]`). Клик по контролу — JS по тексту лейбла,
   скоупленный по секции (см. `portal-component-probe` Live-факты v2).
3. **browser-fetch снова** → A1. Diff A0↔A1 → изменившийся путь = **A** для контрола.
4. Отметить контрол `[x]` в чеклисте (`[~]` если только ref, без diff).

### Шаг 3. Slug и связь (B, C)
Для каждого контрола с известным A:
1. Найти slug (B): `grep` в `app/tools/config_schema.py` по имени/категории, либо
   `docs/architecture/components/slugs/by-type.md`. Нет slug → ⚪ `no-slug`.
2. Найти куда пишет MCP (C): в `config_schema.py` посмотреть `json_path` slug'а И
   apply-handler секции (напр. `section=="axes"` маппит `grid→showgrid`;
   `section=="data"`→ top-level `cfg[prop]`; `section=="visuals"`→ `visuals[0][prop]`;
   `section=="style"`→ `styleCommons[prop]`).
3. Сравнить C и A → проставить связь по таблице выше.
4. A нет в SLUG_REFERENCE → 📄 `undoc-json`.

> **Золотой приём подтверждения 🔴 (рекомендуется для кандидатов-mismatch):** применить
> slug через MCP и посмотреть, КУДА он реально лёг — `component_crud(action="update",
> config_overrides={"<slug>":"<отличимое значение>"})` → `browser-fetch` config → проверить,
> в C-путь легло или в A-путь. Это прямое C-vs-A доказательство (сильнее, чем чтение кода).
> Сессии не конфликтуют (токен в localStorage переживает MCP-вызов; fetch сразу после, без ре-логина).
> Пример: `visuals.colorMin` → легло в `visuals[0].colorMin`, top-level `colorMin` не изменился → mismatch.

### Шаг 4. Записать результат
- **Per-component файл** `components/<Class>.md` по шаблону `components/_TEMPLATE.md`:
  заполнить таблицу UI↔JSON (колонки: UI-секция, UI-контрол, JSON(A), тип, MCP-slug(B),
  MCP пишет(C), Связь, Проверено, **vs <эталон>**) + секцию «Несоответствия» + вывод.
- **Чеклист** `UI_SETTINGS_CHECKLIST.md`: `[x]`/`[~]` по контролам, обновить прогресс-строку.
- **Реестр** `DISCREPANCIES.md`: добавить строки 🔴 (Sn), 🔵 alias (An — с явным маппингом
  slug→JSON), 📄 (Dn), ⚪ (Nn). Обновить сводку-счётчики.
- Если у тебя нет Write — верни всё текстом, родитель запишет.

**Находки, общие с уже разобранным похожим компонентом** (типичный случай — семейство
AMcharts: Bar/Line/Area/Pie делят оси, легенду, подписи, всплывашку):
- Если расхождение/алиас **идентичен** уже записанному → НЕ заводи новый номер: в файле
  пометь «общий паттерн, воспр. на <тип>)», в реестре лишь расширь столбец
  «Компонент». Колонка **vs <эталон>** (`same`/`new`) в таблице даёт мгновенную дельту
  и не раздувает реестр.
- Новый номер (S/A/D/N+1) — только для НОВОЙ, специфичной для типа находки.
- **shared-suspect:** если slug объявлен для НЕСКОЛЬКИХ типов, а mismatch найден на одном
  (как `stacking`) — пометь «проверить на остальных до фикса», не замыкай на один тип.

### Шаг 5. Откат
`report_operations(delete, report_id)` после выхода из браузера.

## Как искать C в коде (примеры)
```
grep -nE '"<категория>\.' app/tools/config_schema.py   # slug'и категории + json_path
sed -n '1010,1110p' app/tools/config_schema.py          # apply-handler по секциям
```
Ключевые секционные правила handler'а: `margin/outline/legend/labels/balloon` →
`config.<section>.<prop>`; `data` → top-level `config.<prop>`; `axes` → вложенный
`config.axes[type].<mapped>`; `visuals` → `config.visuals[0].<prop>`; `style` →
`config.styleCommons.<prop>`; `regimes` → `config.settings.<...>`.

## Правила
- **Сначала enumerate, потом map** — иначе пропустишь контролы.
- **`browser_snapshot` перед каждым действием**; для diff нужен **сохранённый** компонент.
- **alias всегда с явным маппингом** slug→JSON.
- **Не классифицируй mismatch без проверки C по коду** (иначе примешь alias за баг —
  типичная ошибка: оси выглядят как «расхождение», но это alias).
- **Фиксы не делаем** — 🔴 идут в DISCREPANCIES как кандидаты (Трек C).
- **Секции-массивы** (условное форматирование `rules[]`, drill-уровни): элемент добавляется
  кнопкой `.body button.MuiButton-root`, форма inline; элемент ложится в массив объектов
  (`config.rules[n].{prop}`). Связь по handler'у массива (напр. `rules.{n}.{prop}` + спец-
  обработка вложенных `cons["0"]`). Записывать структуру элемента целиком.
- **Quirk привязки значения**: на некоторых под-формах (rule condition value) UI-значение
  может не сохраняться (operator пишется, value — нет). Подтверждать структуру по
  operator+дефолт-болванке handler'а, не полагаться только на value-diff. Это фронт-quirk,
  НЕ MCP-баг — не путать с 🔴 mismatch.
- Сессии: браузер=`${MODUSBI_E2E_LOGIN}`, API=`mcp` — не конфликтуют; не чередовать без нужды.
- Не выдумывать: «контрол не пишет в config» / «slug не найден» — валидный результат.

## Выход
Заполненный `components/<Class>.md` + обновлённые `UI_SETTINGS_CHECKLIST.md` и
`DISCREPANCIES.md`. Резюме: всего контролов / разобрано / по меткам (✅🔵🔴⚪📄).
