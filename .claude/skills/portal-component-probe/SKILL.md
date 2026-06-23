---
name: portal-component-probe
description: Probe ModusBI portal UI for a component — find it in the add-palette, drag-add it, open config, compare with docs, record readiness
allowed-tools: Read, Glob, Grep, mcp__playwright__browser_navigate, mcp__playwright__browser_snapshot, mcp__playwright__browser_take_screenshot, mcp__playwright__browser_click, mcp__playwright__browser_type, mcp__playwright__browser_fill_form, mcp__playwright__browser_hover, mcp__playwright__browser_drag, mcp__playwright__browser_select_option, mcp__playwright__browser_press_key, mcp__playwright__browser_evaluate, mcp__playwright__browser_wait_for
context: fork
user-invocable: true
---

Проверка одного компонента ModusBI **через UI портала**: есть ли он в палитре
добавления, добавляется ли drag-and-drop, открывается ли настройка, совпадают ли
контролы с документацией. Результат — строка готовности компонента
(палитра / drag-add / config-панель / сверка с докой / вердикт).

> **Движок — Playwright MCP** (`mcp__playwright__browser_*`): лучше эмулирует
> drag-and-drop (`browser_drag`). Требует подключённого сервера `playwright` в
> `.mcp.json` (после перезапуска клиента). Снапшот возвращает элементы с `ref=...`;
> ⚠️ это значение передаётся в параметр **`target=`** (НЕ `ref=`!): `browser_click(element="...", target=<ref>)`;
> для `browser_drag` — `startTarget`/`endTarget` (+ `startElement`/`endElement` описания).

## Доступ

> Учётные данные — из `.env` (см. `.env.example`); прочитай перед логином. В скилле — только имена переменных.

| Поле | Переменная (.env) |
|------|----------|
| URL | `${MODUSBI_URL}` |
| Login | `${MODUSBI_E2E_LOGIN}` |
| Password | `${MODUSBI_E2E_PASSWORD}` |
| Тестовый отчёт | создать/выбрать пустой на sandbox, открыть в режиме редактирования |

> Браузер логинится как `${MODUSBI_E2E_LOGIN}` (E2E-учётка); MCP-сервер работает под
> API-юзером портала. Чтобы сессии не конфликтовали — **не чередуй** браузер и
> `mcp__modusbi__*` без необходимости.

## Главный принцип

**Всегда `browser_snapshot` перед каждым действием** — `ref` валиден только в рамках
последнего снапшота. На canvas/SVG — обычный скриншот (без fullPage).

## Процедура (один компонент)

### 0. Логин и режим редактирования
```
browser_navigate(url="${MODUSBI_URL}/report/{TEST_REPORT_ID}")
browser_snapshot()                       # найти ref полей логина
browser_fill_form(fields=[
  {name:"Логин", type:"textbox", ref:<ref>, value:"${MODUSBI_E2E_LOGIN}"},
  {name:"Пароль", type:"textbox", ref:<ref>, value:"${MODUSBI_E2E_PASSWORD}"}
])
browser_click(element="кнопка Войти", target=<ref>)
browser_wait_for(text="<имя тестового отчёта>")
# войти в режим редактирования (кнопка «Редактировать»/карандаш) — найти в снапшоте
```

### 1. Открыть палитру компонентов
```
browser_snapshot()
browser_click(element="Добавить компонент / +", target=<ref>)
browser_snapshot()                       # видна палитра со списком типов
browser_take_screenshot()                # зафиксировать состав палитры
```
> Точные ref/название кнопки — в разделе «Реальный flow портала» ниже.

### 2. Найти пункт компонента в палитре
В свежем снапшоте найти пункт по **русскому названию** (из доки компонента,
напр. «Столбчатая диаграмма» для `HsBarAMchartsChart`).
- Найден → «В палитре UI?» = **да**.
- Не найден (проскроллить палитру, проверить категории/поиск) → **нет** →
  кандидат в 🔴 blocker; зафиксировать и перейти к следующему.

### 3. Добавить компонент (drag-and-drop — основное действие)
```
browser_snapshot()                       # ref пункта палитры и ref целевой ячейки сетки
browser_drag(
  startElement="пункт палитры <название>", startTarget=<ref>,
  endElement="ячейка сетки", endTarget=<ref>     # контейнер .react-grid-layout / .hsReport
)
browser_snapshot(); browser_take_screenshot()   # проверить, что компонент появился
```
**Если нативный `browser_drag` не сработал** (часть DnD-реализаций требует HTML5
событий) — fallback через эмуляцию событий:
```
browser_evaluate(function="() => {
  const src = document.querySelector('<селектор пункта палитры>');
  const dst = document.querySelector('.react-grid-layout') || document.querySelector('.hsReport');
  if (!src || !dst) return 'missing';
  const dt = new DataTransfer();
  const fire = (el,type) => el.dispatchEvent(new DragEvent(type,{bubbles:true,cancelable:true,dataTransfer:dt}));
  fire(src,'dragstart'); fire(dst,'dragenter'); fire(dst,'dragover'); fire(dst,'drop'); fire(src,'dragend');
  return 'dnd-fired';
}")
```
- нативный drag сработал → «Drag-add?» = **да**.
- только клик/двойной клик добавляет → **да (click)** + заметка-находка.
- не добавляется никак → **нет** → 🔴.

### 4. Открыть панель настройки
```
browser_snapshot()
browser_click(element="шестерёнка / двойной клик по компоненту", target=<ref>)
browser_snapshot(); browser_take_screenshot()   # панель настройки
```
«Config-панель?» = да/нет.

### 5. Сверка контролов с документацией
```
Read docs/architecture/components/reference/<name>.md           # напр. barChart.md
Read docs/architecture/components/slugs/by-type.md    # релевантные slug-категории
```
Сопоставить: какие настройки из доки **видны в UI-панели**, каких нет, какие в UI
лишние. «UI ↔ docs» = совпадает / частично (перечислить расхождения).

### 6. Записать строку готовности
```
| <Класс> | <Рус> | <палитра?> | <drag-add?> | <config?> | <UI↔docs> | <MCP?> | <вердикт> | <заметки> |
```
Вердикт: ✅ stable · 🟡 partial · 🔴 blocker · ⚪ skip.

### 7. Откат
Удалить добавленный компонент через UI (контекстное меню → удалить); по
завершении прогона — удалить тестовый отчёт `report_operations(delete)` **после**
выхода из браузера. Не оставлять мусор на sandbox.

## Глубокий разбор настроек (UI ↔ JSON)

Цель: по компоненту пройти **все** контролы config-панели и для каждого знать
**реальный JSON-ключ**, на который он влияет.

**Реальный JSON** = `report.grid.components[idx].config`. Slug'и
(`app/tools/config_schema.py`, напр. `legend.visible`, `margin.l`) — точечные пути
в этом config. Привязка полей — `config.axes[]`.

> Детальная процедура глубокого разбора — отдельный скилл `component-deep-settings`
> (enumerate→map→classify→write, три источника истины A/B/C). Здесь — только
> механика получения ground-truth A.

**⚠️ ground truth A берётся НЕ из MCP `get`!** `report_operations(get)` и
`component_crud(get)` возвращают только обработанный summary / 6-ключевой whitelist —
**сырого `config` в них нет** (`component_crud.py:1006-1037`, `report_operations.py:_get_report_info`).
Diff по ним почти ничего не видит. **Сырой config — только browser-fetch:**
```js
browser_evaluate(function=`async () => {
  const t = JSON.parse(localStorage.getItem('hs_bi')).user.token;
  const r = await fetch('/v1/api/reports/<ID>', {headers:{Authorization:'Bearer '+t}, credentials:'include'});
  const j = await r.json();
  const rep = Array.isArray(j) ? j[0] : j;          // ответ — ГОЛЫЙ массив [report]
  return JSON.stringify(rep.grid.components['<idx>'].config);   // = A
}`)
```
**Метод change→save→fetch→diff (на 1–3 контрола):**
1. baseline: fetch выше → config A0.
2. В UI изменить контрол(ы) → «Сохранить» (компонент, scope `.hsComponentEditor`) →
   «Сохранить отчёт» (`button[title="Сохранить отчет"]`).
3. fetch снова → A1. **Diff A0↔A1** → изменившийся путь = JSON контрола (A).
4. Сверить со `SLUG_REFERENCE.md` / handler в `config_schema.py` (тип/значения/default).

**Быстрый путь:** для очевидных секций (легенда/отступы/рамка/подписи/оси) брать
slug-категорию из SLUG_REFERENCE сразу (`ref`), подтверждая 1–2 контрола диффом.

## Обработка ошибок
- Элемент не найден → `browser_snapshot` заново, до 3 попыток.
- Долгая загрузка графика → `browser_wait_for(time=3)`.
- При любой ошибке — `browser_take_screenshot` текущего состояния в отчёт.
- «Отмена» в настройке → confirm-диалог «Отменить изменение настроек?» → жать «Да».
- Конфликт title (напр. «Таблица»/«Таблица сводная») → точное совпадение (exact).

## Реальный flow портала (Playwright MCP)

**Реальный flow добавления компонента (НЕ «палитра→сетка», а через конструктор):**

1. **Войти в конструктор**: кнопка `button "Перейти в режим конструктора"`
   (видна в режиме просмотра). После этого появляется панель редактирования и
   сетка с контейнерами.
2. **Сетка**: контейнер пустой = `div.noComponent` с текстом «Компонент
   отображения не задан». На контейнере (hover) тулбар:
   - `div.hsEditComponent` (title «Настроить элемент отображения N») — открыть настройку;
   - `div.hsDeleteComponent`-подобный (title «Удалить контейнер N») — удалить.
   - Добавить новый контейнер — кнопка `button "Add"`.
3. **⚠️ Оверлей перехватывает клик**: `div.noComponent` лежит поверх иконок
   тулбара → обычный `browser_click` по шестерёнке падает (TimeoutError,
   «intercepts pointer events»). **Force-click через JS**:
   `browser_evaluate(function="() => { document.querySelector('.hsEditComponent').click(); return 'ok'; }")`.
   (Для конкретного контейнера — выбрать нужный `.hsEditComponent` по индексу.)
4. **Палитра типов**: открывается панель `«Выбор типа отображения»` — `list` из
   ~32 пунктов `generic [title="<Русское название>"]` (напр. title «Диаграмма
   столбчатая»). Это и есть «есть ли компонент в UI»: один снапшот палитры даёт
   presence сразу для ВСЕХ типов.
5. **Выбор типа = DRAG**, не клик! Клик/двойной клик по пункту НЕ выбирает тип.
   Перетащить пункт типа на зону превью «Компонент отображения не задан»:
   `browser_drag(startTarget="<ref пункта типа>", endTarget="<ref зоны превью>")`.
   **Нативный `browser_drag` работает** — после него в превью рендерится график
   (SVG/canvas). Это и есть «частое drag-and-drop действие».
6. **Привязка данных = DRAG полей**: слева список «Поля набора данных»
   (`generic [title="<имя поля>"]`, напр. «Значение», «Регион»). Поля
   перетаскиваются на оси компонента (вкладка «Настройки компонента отображения»,
   `button` ref ~e170). Тот же `browser_drag(поле → ось)`.
7. **Сохранение**: `button "Сохранить"` в шапке настройки → затем
   `button "Сохранить отчет"`. Для зонда сохранять НЕ обязательно.
8. **Сверка с docs**: вкладка «Настройки компонента отображения» содержит UI-контролы;
   сверять с `docs/architecture/components/reference/<name>.md` + `SLUG_REFERENCE.md`.

**Итого для таблицы готовности:** «В палитре UI?» берётся из шага 4 (один снапшот
даёт presence для ВСЕХ типов). «Drag-add?» = шаг 5 (drag типа). Привязка/настройка
— шаги 6–8.

**Логин (подтверждено):** `browser_fill_form` по textbox «Логин»/«Пароль» →
`browser_click` по `button "Войти Войти"`. Снапшот логина даёт refs полей.

## Факты config-панели (глубокий разбор)

Применять при работе с панелью настройки компонента.

0. **Карта контейнеров config-панели (КРИТИЧНО — частая ошибка scope):**
   - **`.hsComponentEditor`** = весь popup-редактор (`hsPopupWindow hsComponentEditor`):
     панель полей данных + drawer настроек + кнопки Save/Cancel. Слишком широкий scope —
     тянет шум (поля/кнопки). Для **Save** брать его кнопки (`.hsComponentEditor button`).
   - **Контролы настроек живут в ВЛОЖЕННОМ drawer `.hsChartSettings`** (внутри `.hsSettingsDrawer`).
     Секция = `.hsSettingsSection.dd`; заголовок = `.header > .sectionTitle`; раскрытие = клик по `.header`.
   - **Все поиски контролов/лейблов — скоупить по `.hsChartSettings`** (или конкретной
     `.hsSettingsSection`), НЕ по `.hsComponentEditor`. Подтверждено на Pie и Table.
1. **Оверлей перехватывает клик по шестерёнке/тоглам/чекбоксам**
   (`browser_click(ref)` → «header intercepts pointer events»).
   **Клик по контролу через JS по тексту лейбла**, скоупленный по СЕКЦИИ:
   ```js
   browser_evaluate(function=`() => {
     const sec = [...document.querySelectorAll('.hsChartSettings .hsSettingsSection')]
       .find(s => s.querySelector('.sectionTitle')?.textContent.trim()==='<Секция>');
     const lab = [...sec.querySelectorAll('*')]
       .find(e => e.children.length===0 && e.textContent.trim()==='<Текст лейбла>');
     const box = lab.closest('label,div').querySelector('input[type=checkbox]');
     box.click(); return box.checked;
   }`)
   ```
2. **Чекбоксы — ТОЛЬКО `checkbox.click()`** (native value-setter НЕ работает для
   `type=checkbox`, React не регистрирует toggle — частая тихая потеря). **Слайдеры/числовые/
   текст** — нативный value-setter + dispatch `input`+`change`. НЕ смешивать в одном батче
   подходы: checkbox→`.click()`, text/range→value-setter.
   ```js
   const set = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype,'value').set;
   set.call(inp, '6'); inp.dispatchEvent(new Event('input',{bubbles:true}));
   inp.dispatchEvent(new Event('change',{bubbles:true}));
   ```
3. **Сохранение — строго со scope!** Глобальный поиск «Сохранить» матчит не ту кнопку
   (отчёт vs редактор) и модалка остаётся открытой. Жать **сначала** Save редактора —
   `.hsComponentEditor button` с текстом «Сохранить»; проверить закрытие
   (`!document.querySelector('.hsComponentEditor')`); **потом** `button[title="Сохранить отчет"]`.
4. **⚠️ Первый чекбокс секции — часто её enable-тогл, а НЕ нужный контрол** (лейбл = имя
   секции, напр. в «Легенда» index 0 = «Легенда» вкл, index 1 = «Реверс»). **Перечислять
   ВСЕ чекбоксы секции с их лейблами** (фильтруя слова-состояния Вкл/Выкл/Да/Нет) и матчить
   по тексту — не брать слепо первый. И всегда скоупить по секции (лейблы повторяются:
   «Сглаживание»/«Толщина»/«Размер» есть и в «Основной стиль», и в per-series «Стилизация»).
5. **Dropdown'ы — react-super-select**: обёртка `.r-ss-wrap.settingsMultiselect`,
   открыть кликом по `.r-ss-trigger`, опции — `.r-ss-dropdown-option`, выбрать кликом по
   нужной опции. Так задаются «Шаблон», «Положение», «Вид диаграммы», «Формат даты».
6. **Условно-отрисованные контролы**: часть появляется только после выбора в dropdown
   (напр. «Отображать итог»/«Шрифт итога» — лишь после «Вид диаграммы»→«Бублик»).
   После каждого переключения mode-dropdown **пере-снять дамп секции**, иначе enumerate неполон.
7. **Имя slug в `title`/`hintslug`-атрибутах — НЕнадёжно**: на Bar/Line бывает
   `title="chart.datarowCount"`; на Table у кнопок/инпутов есть `hintslug` (напр.
   `chart.rules.createRule`, `chart.borderWidth`) — это help-tooltip-анкеры, БОГАЧЕ `title`,
   но НЕ override-slug'и. На Pie title-slug отсутствовал. Собирать оба оппортунистически,
   НЕ как основной источник B — основной B всё равно grep по `config_schema.py`.
8. **`component_crud(add)` требует `title=`** — без него падает.
9. **Секции-массивы (Условное форматирование `rules[]`, Дрилл-уровни, и т.п.):**
   enumerate показывает пустую секцию (только subheader). Sub-form рендерится **inline
   только после клика add-кнопки** — это `.body button.MuiButton-root` ВНУТРИ секции
   (НЕ div-лейбл subheader: клик по нему холостой). После клика **пере-снять дамп секции**.
   Правило ложится в массив (`config.rules[]`), элемент — объект с props (см. `component-deep-settings`).

**Рекомендуемый энумератор (TreeWalker, упорядоченный дамп):** надёжнее привязки
лейбл↔контрол — обойти `.hsChartSettings` в порядке документа, эмитя текст-листья и маркеры
`<input>`/`[title]`/`[hintslug]`/текущие значения по секциям. Даёт пары лейбл→контрол в визуальном порядке.

**Эффективный паттерн (подтв. на Table):** изменить МНОГО контролов одним батчем → один
Save → один fetch+diff. Масштабируется (11 контролов в 6 секциях за 1 diff) — экономит save/fetch-циклы.

**⚠️ Путь скриншотов/дампов:** `browser_take_screenshot`/`browser_evaluate(filename=...)`
сохраняют **относительно cwd** (корень репозитория), а не в `.playwright-mcp/`. **Всегда
передавай явный префикс** `filename=".playwright-mcp/<class>_<N>.png"`, иначе файлы спиллят
в корень репо. НЕ коммить эти артефакты.

**⚠️ Пустая config-панель у MCP-созданного компонента** (`.hsChartSettings` отсутствует,
0 секций, но график рендерится): вероятно **builder пишет `config.chartType`, которого фронт
не ждёт** (пример: builder пишет `"bubbleChart"`, фронт ждёт `"bubble"`). Диагностика:
browser-fetch config → сверь `config.chartType` с ожиданием фронта (doc / рабочий пример).
Обход для продолжения разбора: JS-патч `chartType` → **PUT** `/v1/api/reports/<ID>`
(`body=JSON.stringify([rep])`, статус 200) → reload → панель появится. Зафиксируй как кандидат-баг builder.
