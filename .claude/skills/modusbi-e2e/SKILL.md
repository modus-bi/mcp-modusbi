---
name: modusbi-e2e
description: E2E browser test — ModusBI portal (login, reports, components, visual check)
allowed-tools: Read, Glob, Grep, mcp__playwright__browser_navigate, mcp__playwright__browser_take_screenshot, mcp__playwright__browser_click, mcp__playwright__browser_type, mcp__playwright__browser_hover, mcp__playwright__browser_evaluate, mcp__playwright__browser_wait_for, mcp__playwright__browser_snapshot, mcp__playwright__browser_press_key, mcp__modusbi__instance_operations, mcp__modusbi__component_crud, mcp__modusbi__component_filters, mcp__modusbi__component_axes, mcp__modusbi__component_styling, mcp__modusbi__report_operations
context: fork
user-invocable: true
---

E2E тестирование ModusBI портала через Playwright MCP.

## Credentials

> Значения берутся из `.env` (см. `.env.example`). Прочитай их перед логином
> (напр. `Read .env` / `grep MODUSBI_ .env`). Реальные значения НЕ хранятся в скилле.

| Поле | Переменная (.env) |
|------|----------|
| URL | `${MODUSBI_URL}` |
| Login | `${MODUSBI_E2E_LOGIN}` |
| Password | `${MODUSBI_E2E_PASSWORD}` |

## Quick Login — пошагово

```
1. browser_navigate(url="${MODUSBI_URL}/report/{ID}")
2. browser_snapshot()  — найти ref полей Логин, Пароль, кнопки Войти
3. browser_type(ref="{login_field_ref}", text="${MODUSBI_E2E_LOGIN}")
4. browser_type(ref="{password_field_ref}", text="${MODUSBI_E2E_PASSWORD}")
5. browser_click(ref="{войти_button_ref}")
6. browser_wait_for(text=["название отчёта"], timeout=15000)
7. browser_take_screenshot()
```

### Типичные uid login-формы

Форма логина стабильна, но uid меняются при каждой загрузке. Паттерн:
- `textbox "Логин"` — поле логина
- `textbox "Пароль"` — поле пароля
- `button "Войти Войти"` — кнопка входа (description="Аналитический портал")

**ВСЕГДА делай browser_snapshot() перед fill/click** чтобы получить актуальные uid.

## Критические правила E2E

### 1. Одна сессия на логин
ModusBI допускает только ОДНУ активную сессию на пользователя.
- Если логинишься в браузере — API токен **сбрасывается**
- При следующем API-вызове сервер автоматически перезайдёт (получит новый токен) и браузерная сессия снова **сбросится**
- **Решение**: сначала сделай все API операции, потом логинься в браузере для визуальной проверки

### 2. Скриншоты графиков
- Canvas/SVG графики **НЕ рендерятся** в `fullPage: true` скриншотах
- **Используй viewport screenshot** (без fullPage) — он корректно захватывает графики
- Для нижних компонентов: прокрути контейнер `.hsReport`, потом screenshot

### 3. Прокрутка отчёта
Отчёт рендерится в контейнере `.hsReport`, а не в body. Стандартный `window.scrollTo` НЕ работает.

```javascript
// Прокрутка до конца отчёта
browser_evaluate(function="() => {
  const el = document.querySelector('.hsReport');
  if (el) { el.scrollTop = el.scrollHeight; return 'ok'; }
  return 'not found';
}")

// Прокрутка к конкретному компоненту (по индексу)
browser_evaluate(function="() => {
  const items = document.querySelectorAll('.react-grid-item');
  const target = items[{IDX}];
  if (target) { target.scrollIntoView({behavior: 'instant'}); return 'ok'; }
  return 'not found';
}")
```

### 4. Ожидание загрузки
- После логина: `browser_wait_for(text=["название отчёта"], timeout=15000)`
- После навигации: `browser_wait_for(text=["ожидаемый текст"], timeout=10000)`
- Графики рендерятся ~2-3 сек после появления DOM, делай паузу через browser_evaluate:
```javascript
browser_evaluate(function="() => new Promise(r => setTimeout(r, 3000)).then(() => 'waited 3s')")
```

### 5. Порядок действий при проверке отчёта

```
1. API: report_operations(action="get", report_id=N)           — проверить метаданные
2. API: component_crud(action="get", report_id=N, component_idx=0..K) — проверить конфиги
3. BROWSER: browser_navigate → login → browser_wait_for → screenshot     — визуальная проверка
```

(сервер уже авторизован к нужному порталу через `MODUSBI_URL` env var)

**НЕ чередуй** API и браузер — каждое переключение сбрасывает сессию!

### 6. Проверка данных компонента
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

### 7. Проверка "undefined" и пустых значений
```
browser_evaluate(function="() => {
  const texts = document.body.innerText;
  const issues = [];
  if (texts.includes('undefined')) issues.push('FOUND: undefined');
  if (texts.includes('NaN')) issues.push('FOUND: NaN');
  if (texts.includes('null')) issues.push('FOUND: null text');
  return issues.length ? issues : 'CLEAN';
}")
```

## Чеклист E2E для отчёта

### Фаза 1: API-проверка (без браузера)
- [ ] `report_operations(action="get", report_id=N)` — title, components count
- [ ] Для каждого компонента: `component_crud(action="get", ...)` — type, fields, config
- [ ] Для каждого компонента: `component_crud(action="data", ...)` — rows_count > 0

### Фаза 2: Браузерная проверка
- [ ] browser_navigate → URL отчёта
- [ ] browser_snapshot → найти ref login-полей
- [ ] fill логин + пароль → click Войти
- [ ] browser_wait_for → заголовок отчёта
- [ ] browser_take_screenshot → верхняя часть
- [ ] browser_evaluate → проверка на "undefined", "NaN"
- [ ] browser_evaluate → подсчёт .react-grid-item (совпадает с API)
- [ ] browser_evaluate → прокрутка .hsReport вниз
- [ ] browser_take_screenshot → нижняя часть
- [ ] Визуальная оценка: цвета, легенды, лейблы осей

## Формат отчёта

```
## ModusBI E2E Report — Report #{ID}

### Результат: PASS / FAIL

| Компонент | idx | Тип | API Data | Browser Render | Проблемы |
|-----------|-----|-----|----------|----------------|----------|
| Title 1   | 0   | bar | OK (N rows) | OK | — |
| Title 2   | 1   | line | OK (N rows) | OK | — |
| ...

### API Tests: N/N PASS
### Visual Tests: N/N PASS

### Ошибки (если есть)
- [idx=X] описание + скриншот

### Скриншоты
- viewport-top.png
- viewport-bottom.png
```
