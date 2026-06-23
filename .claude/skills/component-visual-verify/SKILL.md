---
name: component-visual-verify
description: End-to-end visual verification that MCP config_overrides slugs actually RENDER on a ModusBI component — create report+component via MCP, apply each slug, confirm the visual effect in the browser (screenshot + DOM/SVG signature), record per-slug pass/fail
allowed-tools: Read, Glob, Grep, Bash, mcp__playwright__browser_navigate, mcp__playwright__browser_snapshot, mcp__playwright__browser_take_screenshot, mcp__playwright__browser_click, mcp__playwright__browser_evaluate, mcp__playwright__browser_wait_for, mcp__modusbi__report_operations, mcp__modusbi__component_crud
context: fork
user-invocable: true
---

Сквозная **визуальная** верификация: применяем MCP-slug через `config_overrides` и подтверждаем,
что он **реально отобразился** на рендере компонента (а не только «лёг в нужный JSON-ключ»).
Цель — закрыть «не проверено визуально = не сделано».
**Это НЕ повтор `component-deep-settings`:** там мы выясняли, КУДА пишет slug (C) vs что читает
фронт (A). Здесь — **смотрим глазами/DOM, что фронт ОТРИСОВАЛ изменение**. Механика портала
(логин, конструктор, save) — скилл `portal-component-probe` (Live-факты). Доступ к порталу из `.env`:
`${MODUSBI_URL}` + `${MODUSBI_E2E_LOGIN}`/`${MODUSBI_E2E_PASSWORD}` (реальные значения в скилле НЕ
хранятся; прочитай их перед логином, напр. `grep MODUSBI_ .env`).

## Что подтверждаем

Для каждого проверяемого slug — **видимый признак изменения рендера**:
- легенда скрыта (`legend.visible:false`) → элемент легенды исчез из SVG;
- ширина столбцов (`visuals.columnWidth`) → `<rect>` стал шире;
- цвет (`bgColor`, base color) → атрибут `fill`/CSS изменился;
- ориентация (`orientation`) → оси поменялись местами;
- заголовок выкл (`showtitle:false`) → текст заголовка исчёз; и т.п.

Метка результата:
| Метка | Значение |
|---|---|
| ✅ rendered | визуальный эффект подтверждён (скриншот + DOM-признак) |
| 🔴 no-effect | slug применился в JSON (MCP success), но рендер НЕ изменился → реальный silent-ignore |
| ⚠️ ambiguous | эффект незаметен/неоднозначен на этих данных (нужна другая настройка теста) |
| ⚪ not-applicable | контрол требует данных/состояния, которых нет (отметить причину) |

> 🔴 здесь — **сильнее** кодового mismatch: это конечное доказательство, что пользователь не видит
> результат. ✅ здесь — конечное доказательство, что настройка реально работает у пользователя.

## Процедура (на один компонент)

### Шаг 0a. Pre-flight: браузер жив? (ОБЯЗАТЕЛЬНО, до MCP-setup)
Один `browser_navigate("${MODUSBI_URL}")`. Если ошибка
`Browser "<X>" is not installed` — **СТОП**: инфра-блокер, вернуть это родителю сразу
(не делать MCP-setup впустую). Браузер ставит оператор: `npx @playwright/mcp@latest install-browser
chromium` + рестарт MCP-клиента (после правок `.mcp.json` рестарт обязателен; running-канал может
отличаться от файла). Вся визуальная верификация требует рабочего Playwright-браузера.

### Шаг 0. Setup через MCP
1. `report_operations(create, name="vv_<class>", caption="...", group_id=<TEST_GROUP_ID>)` → report_id.
   `<TEST_GROUP_ID>` — тестовая группа в песочнице (`reportgroup_operations(action="list")`).
2. `component_crud(add, report_id, component_type="<Class>", title="vv", dataset_id=<DS_ID>,
   category_field="<dim>", value_field="<metric>", aggregation="sum")` (поля под тип). `<DS_ID>` —
   датасет с одним измерением и одной числовой метрикой; `<dim>`/`<metric>` — их технические имена.
3. Браузер: открыть `/report/{id}` (НЕ в конструкторе — нужен чистый рендер просмотра),
   login при необходимости, `browser_wait_for` пока компонент отрисуется (SVG/canvas/HTML).

### DOM-сигнатуры (КАНОН — откалибровано на amCharts 3.x / Bar)
Надёжные признаки (проверено живьём, не угадывать по классу `*grid*`):
- **Сетка (grid, картезиан bar/line):** счётчик `.amcharts-axis-grid` (НЕ `.amcharts-axis-tick` — то засечки, константа!).
- **Gauge (спидометр):** деления РЕАГИРУЮТ — `.amcharts-axis-tick` (крупные) и `.amcharts-axis-tick-minor` (мелкие)
  меняются от `grid.tickCount`/`grid.minorTickCount` (12→17, 40→65); подписи `.amcharts-axis-label`. ⚠️ `minorTickCount:0`
  = «авто» (вернёт baseline) — брать НЕнулевой контраст. Угол шкалы — `d` у `.amcharts-axis-line` + bandBox/arrowBox.
  outline gauge рисуется на `.hsChartContainer` (НЕ `.react-grid-item`). Зоны = `.amcharts-axis-band` paths.
  У line/area baseline часто БЕЗ сетки → проверять обратным включением (`grid:true`, false→true).
- **Толщина линии (line/area):** `getComputedStyle(path.amcharts-graph-stroke).strokeWidth` (attr=null!);
  **сглаживание (smoothing):** число `C`-команд в `path … d` (ломаная=0 → кривая=N); цвет линии — attr `stroke`.
- **Заголовок (showtitle):** HTML `.componentHeader`/`.titleText` ВНЕ svg → `getComputedStyle(el).display` (`block`↔`none`).
- **Фон (bgColor):** computed `backgroundColor` у `div.hsChartContainer` (НЕ svg `.amcharts-bg` — тот #FFF/opacity:0).
- **Рамка (outline.*):** часто рендерится как **`box-shadow` spread на `.react-grid-item.hsGridPanel`** (`rgb 0px 0px 0px Npx`),
  НЕ как CSS `border` и НЕ на `.hsChartContainer`! Проверять `getComputedStyle('.react-grid-item.hsGridPanel').boxShadow` + скриншот.
- **Столбцы/ориентация:** `g[class*=graph] rect` — `width`/`height` (вертикаль w≪h, горизонталь w≫h); число баров = `rect`.
- **Подписи значений (labels):** счётчик текст-нод подписей в graph-слое (0 → N).
- **Цвет серии:** `getAttribute('fill')` у первого графического `rect`/`path`.
- **Легенда:** наличие `[class*=legend]`; реверс/порядок при 1 серии НЕ виден → подкрепить browser-fetch config.
- **Pie пирог↔пончик (showDonut):** число `A`(arc)-команд в `path d` первой дольки `.amcharts-pie-slice` (пирог=1, пончик=2).
  **summFontSize/radius/labels.groupPercent** — масштабируются amCharts: брать КОНТРАСТНУЮ пару (28 vs 8), не абсолют.
  summFontSize виден ТОЛЬКО при summEnabled=true (+showDonut); labels.groupPercent — при switchControlNumberOfSegments=false.
- **balloon.* (всплывашка эфемерна по hover)** — НЕ ловить скриншотом; сразу browser-fetch config (Cap `fontSize` vs lc `fontsize`).
- **Заголовок может УДАЛЯТЬСЯ из DOM** (не display:none) при showtitle:false — надёжнее проверять наличие узла `.titleText`.
> Для не-amCharts (ECharts treemap/tilemap, Leaflet, GoJS, HTML-table) — подобрать признаки по их DOM
> (canvas/svg/таблица); метод тот же: измеримый признак до/после.
- **amCharts 5 (Stock и др. новые):** канон 3.x НЕ работает (`.amcharts-*` отсутствуют). Сигнатуры amCharts5:
  навигатор-скроллбар = `[role="scrollbar"]`/`[role="slider"]` (1↔0 / 3↔0); доп.ось/панель = счётчик `[role="region"]`
  в контейнере (1→2); кнопки зума = text-scan `1m/3m/6m/1y/ytd/max`; панель диапазона = счётчик `<input>` (0→2).
  Заголовок прячется схлопыванием → надёжно `!el.offsetParent` ИЛИ `getBoundingClientRect().width===0` (узел НЕ удаляется).
- **HTML-таблица (reactabular):** заголовок `.hsChartContainer .titleText` (СКОУПИТЬ по контейнеру — report-H1 тоже
  `.titleText`!); **итоги/подытоги** = наличие `tfoot` + text-scan `/подытог|итого/i` (НЕ счётчик `<tr>` — виртуализация
  меняет его 36/39/26!); фон ячейки/CF = `getComputedStyle(td).backgroundColor`; зебра = чередование bg строк.
- **ECharts treemap (HsTreeMap):** блоки = **цветные `<path>` с `fill`≠none** (НЕ `<rect>`! rect=1 фон); ≈2× числа
  категорий (fill-path + border-path на блок). Сдвиг от `margin` — bbox (minX/minY) цветных path. Tilemap — тоже SVG,
  но плитки=`<rect>`, ★спецгорода=`path.tile-star` с непустым `d` (N↔0), легенда-значения = HTML-ноды ВНЕ svg
  (text-scan по `.hsReport`, не `<text>`), fill плиток только computed; square↔hex **неразличимы** в DOM (только fetch `tiles.type`).
- **Leaflet (HsMapLeafletChart):** `.leaflet-container`(1=инициализ.), `.leaflet-tile`(N=тайлы подложки), `.leaflet-control`(zoom+attr≈3),
  `.leaflet-overlay-pane path`(полигоны choropleth), спиннер=`.lds-roller`(1=грузит/завис). ⚠️ **MCP-карта может НИКОГДА не
  отрисоваться** (вечный спиннер, 0 узлов) — ОБЯЗАТЕЛЕН pre-flight против заведомо рабочей прод-карты; если контроль рендерит,
  а тестовая нет — это находка (render-block), не повод подгонять. `performance.getEntriesByType('resource')` покажет, дошёл ли до data-query.
- **`.titleText` неоднозначен — их ДВА:** [0]=report-H1, [1]=заголовок компонента. Брать по индексу/порядку (querySelector вернёт H1).
- **Media (Iframe/ImagePanel):** Iframe = `<iframe>` + атрибут `src` (= config.frameUrl; фронт читает frameUrl, не link.name). ImagePanel
  картинка = `background-image: url(...)` (НЕ `<img>`-тег!), пусто = `/images/placeholder.png`. ⚠️ `bgColor` на media **системно
  не виден** (iframe/картинка перекрывают панель) — помечать ⚠️/⚪ заранее, не 🔴 каждый раз (config пишется верно, фронт silent-ignore).
- **Проверка КРАША / пустой config-панели** (бывает у media-типов и при битом `chartType`-гейте): в конструкторе force-click
  `document.querySelector('.hsEditComponent').click()` → замерить `.hsChartSettings` (`innerHTML.length`/`sectionCount`) ИЛИ для
  control-панелей `.verticalTabMenu.right` (`innerText.length`, `querySelectorAll('input,select').length`); 0 контролов = пусто/краш.
  Прочитать консоль (`browser_console_messages`) на `R.render`/`valueType undefined` — отличить фронт-краш рендера панели от chartType-гейта (панель пуста, потому что builder записал `chartType`, которого фронт-гейт не ждёт).
  Сравнить с заведомо рабочим типом (Iframe/Bar = 5+ секций). A/B chartType-гейта: live-PUT правильный chartType → reload → панель наполняется.
- ⚠️ **Держи `browser_evaluate`-функции КОРОТКИМИ** (1-3 признака, без длинных вложенных структур) и применяй slug
  ПО ОДНОМУ — длинные/сложные tool-вызовы ломают парсер модели (падения на complex JSON/CF). Сложное CF — через
  `component_styling(conditional_rule_add)`, не через длинный `config_overrides`.

### Шаг 1. Baseline
- `browser_take_screenshot(filename=".playwright-mcp/vv_<class>_0_base.png")` (viewport, не fullPage).
- Снять **DOM-сигнатуру** компонента через `browser_evaluate` — словарь измеримых признаков, напр.:
  ```js
  () => { const el = document.querySelector('.hsReport') || document.body;
    return { legend: !!el.querySelector('[class*="legend"]'),
             bars: el.querySelectorAll('rect').length,
             title: (el.querySelector('[class*="title"],text')||{}).textContent,
             bg: getComputedStyle(el.querySelector('[class*="hsGridPanel"],svg')||el).backgroundColor,
             firstBarFill: (el.querySelector('g[class*="graph"] rect, path[fill]')||{}).getAttribute?.('fill') }; }
  ```
  (Подобрать признаки под тип: легенда/оси/цвет/число элементов/текст заголовка.)

### Шаг 2. Применить slug и проверить эффект
По одному (или малыми батчами различимых эффектов):
1. Выбрать slug + **отличимое** значение (контраст к baseline: цвет ярко-красный, legend.visible:false,
   columnWidth огромный) + **ожидаемый визуальный признак**.
2. `component_crud(action="update", report_id, component_idx=0, config_overrides={"<slug>": <value>})` →
   проверить `slugs_applied` (если 0 — slug не прошёл валидацию, отметить ⚠️/🔴 на уровне MCP).
3. `browser_navigate` (reload отчёта) → `browser_wait_for` рендер.
4. `browser_take_screenshot(".playwright-mcp/vv_<class>_<n>_<slug>.png")` + снять ту же DOM-сигнатуру.
5. **Сравнить** baseline ↔ after по ожидаемому признаку:
   - признак изменился как ожидалось → ✅ rendered;
   - не изменился (а MCP success) → 🔴 no-effect (silent-ignore, конечное доказательство);
   - изменился непонятно/незаметно → ⚠️ (поменять значение/данные и повторить 1 раз).
6. Откатить значение (или применять независимые slug, чтобы не маскировать друг друга).

> **Батч-оптимизация:** можно применить НЕСКОЛЬКО slug с РАЗНЫМИ, не пересекающимися признаками
> за один update+reload, и проверить все признаки одним DOM-снимком. НЕ батчить slug, влияющие
> на один и тот же признак.

### Шаг 3. Сверка с кодовой классификацией
Сопоставить с кодовой классификацией контрола (метка из `component-deep-settings`:
✅linked / 🔵alias / 🔴mismatch по сравнению путей A↔C):
- ✅linked/🔵alias по коду **и** ✅rendered → полностью подтверждено (золото).
- 🔴mismatch по коду **и** 🔴no-effect → визуально подтверждённый баг (двойное доказательство).
- ✅linked по коду **но** 🔴no-effect → НОВОЕ: код пишет верно, а фронт всё равно не рендерит
  (более глубокая проблема — фиксировать отдельно!).

### Шаг 4. Откат
`report_operations(delete, report_id)` после выхода из браузера. Тестовые отчёты `vv_*` не оставлять.

## Значения slug — частые ловушки (из калибровки)
- **`orientation`** — enum **`["v","h"]`** (НЕ `"horizontal"`/`"vertical"`! последние → `slugs_applied:0`).
- **Серии/легенда** — задавать `series_field` при `add`, НЕ через `update` (update-add-series = no-op).
  Перед legend-кейсами убедиться, что серия реально есть (`get`/`data`), иначе legend-кейсы → ⚪.
- Контраст: `legend.visible:false`, `bgColor:"rgba(255,0,0,1)"`, `visuals.columnWidth:20` (НЕ 80 — это дефолт схемы, нет контраста!), `showtitle:false`.

## Правила
- Значения брать **контрастные** (иначе ⚠️). Скриншот viewport на каждый шаг.
- `slugs_applied:0` от MCP = slug не прошёл (тип/валидация) — это отдельная находка (не «фронт виноват»).
- Один признак = один slug за раз (или непересекающиеся в батче).
- Не выдумывать: «эффект не виден» — валидный результат 🔴/⚠️, фиксировать честно.
- Нет Write → вернуть таблицу текстом, родитель запишет.

## Выход
Таблица: `Компонент | slug | значение | ожидаемый признак | MCP slugs_applied | DOM-признак до→после | скриншот | метка ✅🔴⚠️⚪ | сверка с кодом`.
Резюме: сколько ✅/🔴/⚠️, особо — расхождения «код ✅ / визуально 🔴».
