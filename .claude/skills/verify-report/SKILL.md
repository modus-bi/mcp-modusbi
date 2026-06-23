---
name: verify-report
description: Детальная верификация отчёта ModusBI — проверка фильтров, layout, данных, сортировки, alias, стилей. API + браузер.
license: MIT
metadata:
    skill-author: ModusBI Team
    version: "1.0"
    domain: business-intelligence
    mcp-servers: modusbi, playwright
user-invocable: true
---

# Verify Report: Детальная верификация отчёта

## Когда использовать

- После создания отчёта через create-* скиллы
- При жалобах на "не работает фильтр", "поехала верстка", "нет данных"
- Для регулярного QA дашбордов

---

## Фаза 1: API-проверка (без браузера!)

### 1.1 Получить структуру

```
report_operations(action="components_list", report_id=N)
```

> Сервер `mcp__modusbi__*` уже подключён к нужному порталу (через `MODUSBI_URL`
> env var в `.mcp.json`). Если нужен другой портал — настрой отдельный
> `mcpServers` entry с другими env vars (см. INSTALL.md «Multiple portals»).

**Чеклист структуры:**
- [ ] Количество компонентов совпадает с ожидаемым
- [ ] Типы компонентов правильные (barChart, table, FilterControlPanel, etc.)
- [ ] Все компоненты имеют заголовки (caption != "")

### 1.2 Проверить layout (КРИТИЧНО!)

Для каждого компонента проверить `position: {x, y, w, h}`:

```
report_operations(action="components_list", report_id=N)
```

**Чеклист layout:**
- [ ] Нет перекрытий: на `lg` breakpoint компоненты в одной строке не превышают w=48 суммарно
- [ ] На `hd` breakpoint ширина строки не превышает w=60
- [ ] Нет перекрытий по вертикали: y_next >= y_current + h_current
- [ ] Фильтры ВЫШЕ data-компонентов (y фильтров < y данных)
- [ ] Subheader (если есть) на y=0, фильтры на y=2 (не y=0!)
- [ ] Full-width компоненты (таблицы, графики) имеют w=48; half-width пары — w=24+w=24

### 1.3 Проверить фильтры (КРИТИЧНО!)

Для каждого FilterControlPanel:

```
component_filters(action="filter_fields_list", report_id=N, component_idx=X)
```

**Чеклист фильтров:**
- [ ] **type="string"** (НЕ "number"!) — number рендерит слайдер вместо dropdown
- [ ] **alias на русском** (НЕ английское имя поля!) — "Район" а не "region"
- [ ] **dataset_id указан** — без него фильтр пустой
- [ ] **global=true** — иначе фильтр не связан с другими компонентами

### 1.4 Проверить filter_field_add на data-компонентах (КРИТИЧНО!)

**Правило:** filter_field_add нужен на FilterControlPanel (чтобы показать dropdown) И на КАЖДОМ data-компоненте (чтобы данные реагировали на фильтр). Если filter_field_add есть только на FilterControlPanel — фильтр показывает значения, но данные НЕ меняются.

Для КАЖДОГО FilterControlPanel получить список его фильтров:
```
component_filters(action="filter_fields_list", report_id=N, component_idx=FILTER_IDX)
# Запомнить: value_field и alias каждого поля
```

Затем для КАЖДОГО data-компонента (графики, таблицы, KPI, карты — НЕ FilterControlPanel):
```
component_filters(action="filter_fields_list", report_id=N, component_idx=DATA_IDX)
# Проверить что присутствуют поля из FilterControlPanel
```

**Чеклист для КАЖДОГО data-компонента:**
- [ ] Присутствуют filter fields для ВСЕХ полей из ВСЕХ FilterControlPanel
- [ ] alias точно совпадает с alias из FilterControlPanel (регистр важен!)
- [ ] field_type="string" (не "number")
- [ ] dataset_id указан

**Быстрый скрипт проверки:**
```
# Получить все компоненты с типами
report_operations(action="components_list", report_id=N)
# Для каждого НЕ-FilterControlPanel компонента вызвать:
component_filters(action="filter_fields_list", report_id=N, component_idx=X)
# Если ответ пустой — FAIL! filter_field_add отсутствует
```

### 1.5 Проверить global_filters

```
report_operations(action="global_filters_list", report_id=N)
```

**Чеклист:**
- [ ] Количество global_filters == количество полей фильтров
- [ ] Нет orphan фильтров (старые, не привязанные)
- [ ] Имена фильтров = alias из filter_field_add (русские!)

### 1.6 Проверить данные компонентов (КРИТИЧНО — по КАЖДОМУ!)

Пройти `component_crud(action="data")` по КАЖДОМУ data-компоненту отдельно (не выборочно!):

```
component_crud(action="data", report_id=N, component_idx=X)
```

**Чеклист данных:**
- [ ] rows_count > 0 для каждого data-компонента
- [ ] 🔴 **Ответ НЕ содержит `"message": "Component not linked to dataset"`** — это = **бесконечная
      загрузка (спиннер)** в браузере. Частая причина: `update` с `value_field`/`category_field` БЕЗ
      `dataset_id` отвязывает датасет. Фикс: повторить `update` с `dataset_id`.
- [ ] 🔴 **Ответ НЕ ошибка** (`{success:false}` / HTTP 400/500). ⚠️ Для КАРТ: HTTP 400 на data — это
      РЕАЛЬНАЯ ошибка SQL, НЕ «квирк». Типовая причина — `category_field="region,lat,lng"` (через запятую)
      → `group by "region,lat,lng"` → «column does not exist». Фикс: `category_field="region"` + geokeys.
- [ ] Нет null/undefined в данных; числа в правильном формате

### 1.7 Проверить стилизацию фильтров

```
component_crud(action="get", report_id=N, component_idx=X)
# Проверить config: outline.enabled, bgColor, margin
```

**Чеклист стилей:**
- [ ] outline.enabled = true
- [ ] outline.width = 1
- [ ] outline.color = "rgba(179,179,179,1)"
- [ ] bgColor = "rgba(255,255,255,1)"
- [ ] margin.l = 5, margin.r = 5

### 1.8 Проверить сортировку графиков

**Чеклист сортировки:**
- [ ] Рейтинговые bar chart отсортированы по значению (desc)
- [ ] Таблицы отсортированы по ключевой метрике
- [ ] Comparison chart отсортирован по current_period desc

### 1.9 Проверить field_titles таблиц

```
component_crud(action="get", report_id=N, component_idx=TABLE_IDX)
```

**Чеклист:**
- [ ] Все столбцы имеют русские заголовки (field_titles заданы)
- [ ] aggregation="none" и value_fields_type="string" для таблиц

---

## Фаза 2: Браузерная проверка

**ВАЖНО:** Сначала ВСЕ API операции, потом логин в браузере! API switch сбрасывает сессию.

### 2.1 Логин

⚠️ Сначала прочитай креды из gitignored `.env`: `grep MODUSBI_ .env` (или Read .env) →
подставь реальные `MODUSBI_E2E_LOGIN`/`MODUSBI_E2E_PASSWORD`. НЕ инлайнь и НЕ печатай пароль.

```
browser_navigate(url="${MODUSBI_URL}/report/{ID}")
browser_snapshot()  # найти ref полей
browser_type(ref="{login_ref}", text="${MODUSBI_E2E_LOGIN}")
browser_type(ref="{password_ref}", text="${MODUSBI_E2E_PASSWORD}")
browser_click(ref="{войти_ref}")
browser_wait_for(text=["название отчёта"], timeout=15000)
```

### 2.2 Визуальная проверка верхней части

```
browser_take_screenshot()
```

**Чеклист:**
- [ ] Заголовок отчёта отображается
- [ ] Фильтры видны как DROPDOWN (не слайдер!)
- [ ] Фильтры с русскими подписями
- [ ] KPI карточки отображают числа (не 0, не NaN)
- [ ] Графики рендерятся (canvas/SVG видны)

### 2.3 Проверка на undefined/NaN + error-попапы + бесконечную загрузку (КРИТИЧНО!)

⚠️ Подождать рендер (4-5с), потом сканировать. Проверять НЕ только undefined/NaN, но и **error-попапы**
(«Ошибка выполнения запроса», `pq:`, `does not exist`, «Драйвер») и **спиннеры** (компонент висит в загрузке):

```
browser_evaluate(function="async () => {
  await new Promise(r => setTimeout(r, 5000));  // дождаться данных
  const body = document.body.innerText;
  const issues = [];
  // 1. Артефакты данных
  ['undefined','NaN'].forEach(t => { if (body.includes(t)) issues.push('FOUND: '+t); });
  // 2. Error-попапы / тосты выполнения запроса (главное, что пропускают!)
  const errs = body.match(/Ошибка выполнения|does not exist|pq:|Драйвер|column \"/gi);
  if (errs) issues.push('ERROR POPUP: ' + [...new Set(errs)].join(', '));
  // 3. Бесконечная загрузка
  if (/не привязан|Component not linked/i.test(body)) issues.push('NOT LINKED (спиннер)');
  const spinners = document.querySelectorAll('[class*=spinner], .rt-loading, [class*=Loading]').length;
  if (spinners) issues.push('SPINNERS: ' + spinners);
  return issues.length ? issues : 'CLEAN';
}")
# FAIL при любом ERROR POPUP / NOT LINKED / SPINNERS — это ровно те дефекты,
# что не видны по наличию canvas/svg, но ломают отчёт для пользователя.
```

### 2.4 Подсчёт компонентов

```
browser_evaluate(function="() => {
  const items = document.querySelectorAll('.react-grid-item');
  return Array.from(items).map((el, i) => ({
    idx: i,
    title: el.querySelector('.hs-chart-header__title')?.textContent || '',
    hasCanvas: !!el.querySelector('canvas'),
    hasSvg: !!el.querySelector('svg'),
    height: el.offsetHeight
  }));
}")
```

**Чеклист:**
- [ ] Количество .react-grid-item совпадает с API
- [ ] Все компоненты имеют высоту > 0 (не скрыты)

### 2.5 Проверка фильтров в браузере

```
browser_snapshot()
# Найти combobox элементы — должны показывать русский alias
# Проверить что это combobox (dropdown), а не slider
```

**Чеклист:**
- [ ] Фильтры отображаются как combobox (не input[type=range])
- [ ] Подписи на русском ("Район: Все", "Категория: Все")
- [ ] При клике открывается dropdown со значениями

### 2.6 Тест фильтрации (ОБЯЗАТЕЛЬНО для каждого фильтра)

**ВАЖНО:** `browser_click(ref=...)` НЕ работает с React combobox — CDP-клик не триггерит React synthetic events. Используй `browser_evaluate` с `dispatchEvent`:

**Для каждого FilterControlPanel:**

```
# 1. Открыть dropdown через JS (CDP click не работает с React!)
browser_evaluate(function="() => {
  const combos = document.querySelectorAll('[role=\"combobox\"]');
  // Найти нужный combobox по ariaLabel или тексту
  const target = Array.from(combos).find(c => c.getAttribute('aria-label') === 'Регион');
  if (!target) return 'NOT FOUND';
  ['mousedown','mouseup','click'].forEach(ev =>
    target.dispatchEvent(new MouseEvent(ev, {bubbles:true, cancelable:true, view:window}))
  );
  return new Promise(r => setTimeout(() => {
    const opts = document.querySelectorAll('.r-ss-dropdown-option');
    r({ opened: opts.length > 0, options: Array.from(opts).map(o=>o.innerText) });
  }, 300));
}")
# PASS: opened=true, options=[список значений из датасета]
# FAIL: opened=false, options=[] — фильтр пустой

# 2. Кликнуть на значение и проверить фильтрацию
browser_evaluate(function="() => {
  const options = document.querySelectorAll('.r-ss-dropdown-option');
  if (!options.length) return 'NO OPTIONS';
  const first = options[0];
  const value = first.innerText;
  ['mousedown','mouseup','click'].forEach(ev =>
    first.dispatchEvent(new MouseEvent(ev, {bubbles:true, cancelable:true, view:window}))
  );
  return new Promise(r => setTimeout(() => {
    const combos = document.querySelectorAll('[role=\"combobox\"]');
    const combo = Array.from(combos).find(c => c.getAttribute('aria-label') === 'Регион');
    const newValue = combo?.innerText || '';
    const rows = document.querySelectorAll('tbody tr, .rt-tr-group');
    r({ selected: value, comboText: newValue, tableRows: rows.length });
  }, 1000));
}")
# PASS: comboText содержит выбранное значение, tableRows < исходного количества
```

**Чеклист для каждого фильтра:**
- [ ] Dropdown открывается (не слайдер!)
- [ ] Список содержит значения из датасета (не пустой)
- [ ] После выбора значения количество строк в таблице/данных УМЕНЬШАЕТСЯ
- [ ] Фильтр применяется ко ВСЕМ data-компонентам (KPI, графики, таблица)

### 2.7 Прокрутка и нижняя часть

```
browser_evaluate(function="() => {
  const el = document.querySelector('.hsReport');
  if (el) { el.scrollTop = el.scrollHeight; return 'ok'; }
  return 'not found';
}")
# Подождать рендер
browser_evaluate(function="() => new Promise(r => setTimeout(r, 2000)).then(() => 'waited 2s')")
browser_take_screenshot()
```

---

## Фаза 3: Исправление найденных проблем

### 3.1 Фильтр type="number" → "string"

```
# 1. Удалить старый фильтр
component_filters(action="filter_field_remove", report_id=N, component_idx=X, value_field="field_name")

# 2. Добавить с правильным типом
component_filters(action="filter_field_add", report_id=N, component_idx=X,
  value_field="field_name", alias="Русское название", field_type="string", dataset_id=DS)

# 3. Повторить для КАЖДОГО data-компонента (не только FilterControlPanel!)
```

### 3.2 Layout перекрытие

```
# Пересчитать y для всех компонентов:
# Subheader: y=0, h=2
# Фильтры: y=2, h=2
# KPI: y=4, h=3
# Графики: y=7, h=8
# Таблица: y=15, h=8

component_crud(action="layout_update", report_id=N, component_idx=X, x=0, y=NEW_Y, w=48, h=H)
```

### 3.3 Отсутствующий фильтр

```
# 1. Добавить FilterControlPanel
component_crud(action="add", report_id=N, component_type="HsFilterControlPanel",
  title="Фильтры", value_field="field_name", dataset_id=DS, x=0, y=0, w=48, h=2)

# 2. Пересоздать filter field с правильным типом (см. 3.1)
# 3. Добавить filter fields на ВСЕ data-компоненты
# 4. Сдвинуть остальные компоненты вниз (+2 по y)
```

### 3.4 Нет сортировки

```
component_styling(action="field_sort_set", report_id=N, component_idx=X,
  value_field="metric_field", config_overrides={"order": "desc"})
```

### 3.5 filter_field_add отсутствует на data-компонентах

**Симптом:** Фильтр показывает dropdown со значениями, но данные в графиках/таблицах НЕ меняются при выборе.

```
# Получить список фильтров из FilterControlPanel
component_filters(action="filter_fields_list", report_id=N, component_idx=FILTER_IDX)
# Запомнить: value_field, alias, dataset_id для каждого поля

# Добавить filter_field_add на КАЖДЫЙ data-компонент
# DATA_IDXS = все компоненты кроме FilterControlPanel
for data_idx in DATA_IDXS:
  component_filters(action="filter_field_add", report_id=N, component_idx=data_idx,
    value_field="field_name", alias="Русский алиас", field_type="string", dataset_id=DS)

# Проверить что global_filters обновился
report_operations(action="global_filters_list", report_id=N)
```

**ВАЖНО:** alias в filter_field_add на data-компонентах должен ТОЧНО совпадать с alias на FilterControlPanel!

---

## Формат отчёта верификации

```
## Верификация Report #{ID} — "{Название}"

### Фаза 1: API

| Проверка | Результат | Проблема |
|----------|-----------|----------|
| Структура (N компонентов) | OK/FAIL | описание |
| Layout (перекрытия) | OK/FAIL | idx=X и idx=Y на y=0 |
| Фильтры (type/alias) | OK/FAIL | idx=X type=number |
| Фильтры на data-comp | OK/FAIL | idx=X нет filter axis — фильтр не применяется! |
| Global filters | OK/FAIL | orphan: "old_filter" |
| Данные (rows>0 по КАЖДОМУ) | OK/FAIL | idx=X rows=0 |
| Привязка к датасету | OK/FAIL | idx=X "Component not linked" → спиннер! |
| Ошибки выполнения (data) | OK/FAIL | idx=X HTTP 400: column "..." does not exist |
| Стили фильтров | OK/FAIL | нет outline |
| Сортировка | OK/FAIL | bar chart unsorted |
| field_titles | OK/FAIL | английские названия |

### Фаза 2: Браузер

| Проверка | Результат | Проблема |
|----------|-----------|----------|
| Рендер | OK/FAIL | — |
| undefined/NaN | CLEAN/FAIL | FOUND: NaN |
| Error-попапы / спиннеры | CLEAN/FAIL | ERROR POPUP: does not exist / NOT LINKED |
| Фильтры dropdown | OK/FAIL | слайдер вместо dropdown |
| Русские подписи | OK/FAIL | "region" вместо "Район" |
| Фильтрация работает | OK/FAIL | данные не меняются |
| Layout визуально | OK/FAIL | перекрытие компонентов |

### Исправления

1. [idx=X] описание фикса — результат
2. [idx=Y] описание фикса — результат

### Итог: PASS / FAIL (N issues fixed)
```

---

## Типичные ошибки (lessons learned)

1. **filter_field_add без field_type="string"** → default "number" → слайдер вместо dropdown
2. **filter_field_add без alias** → английское имя поля в UI
3. **filter_field_add только на FilterControlPanel** → global filter создан, но data-компоненты НЕ реагируют (нужен filter field на КАЖДОМ)
4. **Subheader и фильтры на y=0** → перекрытие, "поехала вёрстка"
5. **scaffold создаёт компоненты, но filter placeholder "value"** → нужно удалить и добавить реальные поля
6. **Нет field_sort_set на рейтинговых графиках** → данные в произвольном порядке
7. **aggregation="none" для графиков** → GROUP BY error, нужно "sum"
8. **category_field=DATE для BarChart** → не рендерится, нужно TO_CHAR в SQL
9. **Dropdown скрывается за компонентами** → react-grid-layout создаёт stacking contexts через CSS transform; API position.zIndex НЕ транслируется в CSS. Фикс: `style_operations(css=".react-grid-item:has(.hsFilterControlPanel) { z-index: 100 !important; }")` — добавлять в КАЖДЫЙ отчёт с фильтрами
10. **`update value_field`/`category_field` БЕЗ `dataset_id`** → компонент может потерять привязку («Component not linked» = бесконечный спиннер). При апдейте полей ВСЕГДА передавать `dataset_id`. *(В коде есть fallback на datasetId из полей оси — но на старых сборках/edge-кейсах проверяй data по каждому компоненту.)*
11. **Карта: `category_field="region,lat,lng"` через запятую** → SQL `group by "region,lat,lng"` → «column does not exist» (error-попап, data HTTP 400). Для карты: `category_field="region"` (ОДНО поле) + координаты через `map_set_geokeys(latfield, lonfield)`. **HTTP 400 на data-карте — это РЕАЛЬНАЯ ошибка, не «квирк»: всегда открывать карту в браузере и смотреть на error-попап.**
