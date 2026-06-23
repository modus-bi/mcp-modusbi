---
name: add-navigation-panel
description: Добавляет навигационную панель между отчётами тремя способами — HsTabsPanel (нативный), HsTextBlock (HTML/CSS), или стилизация TabsPanel через CSS. Паттерн — gradient blue nav bar с подсветкой активной вкладки.
license: MIT
metadata:
    skill-author: ModusBI Team
    version: "1.0"
    domain: business-intelligence
    mcp-servers: modusbi
user-invocable: true
---

# Add Navigation Panel: Навигация между отчётами

## Три способа навигации

| Способ | Когда использовать | Контроль стиля |
|--------|-------------------|---------------|
| **A. HsTabsPanel** | Нативный компонент, передача фильтров, sendRequest | Ограниченный (bgColor, fillColor кнопок) |
| **B. HsTextBlock HTML** | Полный контроль — градиент, hover, активная вкладка | Полный (inline CSS) |
| **C. CSS-стилизация TabsPanel** | Нативный TabsPanel + кастомный стиль через style_operations | Средний |

**Пример набора отчётов** (подставьте свои `report_id`): 101 (KPI), 102 (Участники), 103 (Факторный), 104 (Рейтинг), 105 (Геоаналитика), 106 (Сравнение)

---

## Способ A: HsTabsPanel (нативный компонент)

### Когда использовать
- Нужна передача текущих фильтров при переходе (`noDrillOut: false`)
- Нужен `sendRequest` — вызов внешнего API по кнопке
- Простой дашборд, без сложной стилизации

### Шаги

```
# 1. Добавить TabsPanel (idx будет последним)
mcp__modusbi__component_crud(action="add",
  report_id=<ID>,
  component_type="HsTabsPanel",
  title="Навигация",
  x=0, y=0, w=48, h=3
)
# component_idx = <N> (запомнить)

# 2. Убрать showtitle (панель без заголовка)
mcp__modusbi__component_crud(action="update", report_id=<ID>, component_idx=<N>,
  config_overrides={"showtitle": false, "bgColor": "rgba(21,101,192,1)"}
)

# 3. Добавить кнопки (tabs_button_add)
# Активная страница: fillColor синий, color белый
mcp__modusbi__component_axes(action="tabs_button_add", report_id=<ID>, component_idx=<N>,
  title="KPI",
  config_overrides={
    "link": "/report/103",
    "fill_color": "rgba(255,255,255,0.15)",  # светлее = активная
    "text_color": "rgba(255,255,255,1)",
    "link_target": "_self"
  }
)
mcp__modusbi__component_axes(action="tabs_button_add", report_id=<ID>, component_idx=<N>,
  title="Участники",
  config_overrides={
    "link": "/report/104",
    "fill_color": "rgba(255,255,255,0)",    # прозрачный = неактивная
    "text_color": "rgba(255,255,255,1)",
    "link_target": "_self"
  }
)
# Повторить для каждой вкладки...

# 4. Проверить кнопки
mcp__modusbi__component_axes(action="tabs_button_list", report_id=<ID>, component_idx=<N>
)

# 5. Переместить на y=0 (до всех остальных компонентов)
mcp__modusbi__component_crud(action="layout_update", report_id=<ID>, component_idx=<N>,
  x=0, y=0, w=48, h=3
)
# Сдвинуть остальные компоненты вниз на 3:
# layout_update(component_idx=K, y=old_y+3) для каждого
```

### Параметры tabs_button_add

| Параметр | Описание | Пример |
|----------|----------|--------|
| `title` | Текст кнопки | `"KPI"` |
| `config_overrides.link` | URL отчёта | `"/report/103"` |
| `config_overrides.fill_color` | Фон кнопки (RGBA) | `"rgba(255,255,255,0.2)"` |
| `config_overrides.text_color` | Цвет текста | `"rgba(255,255,255,1)"` |
| `config_overrides.link_target` | `"_self"` или `"_blank"` | `"_self"` |

### Паттерн передачи фильтров (noDrillOut)
```
# При добавлении кнопки — фильтры передаются по умолчанию (noDrillOut=false)
# Чтобы НЕ передавать фильтры при переходе — нужно редактировать config напрямую
# (noDrillOut: true)
```

---

## Способ B: HsTextBlock с HTML (полный контроль стиля)

### Когда использовать
- Нужен градиентный фон, hover-эффекты, активная вкладка другим цветом
- Кастомный брендинг (логотип + кнопки)
- Паттерн: gradient blue nav bar с подсветкой активной вкладки

### Шаблон HTML (gradient blue)

```html
<div style="background: linear-gradient(135deg, #0d47a1, #1565c0, #1976d2);
            display: flex; align-items: center; height: 100%;
            padding: 0 16px; gap: 4px; box-sizing: border-box;">

  <!-- Логотип / Название -->
  <div style="color: white; font-weight: 700; font-size: 14px;
              padding: 6px 12px; margin-right: 8px; white-space: nowrap;">
    ДТП СПб
  </div>

  <!-- Кнопки навигации -->
  <!-- АКТИВНАЯ вкладка (текущий отчёт) -->
  <a href="/report/103" style="
    background: rgba(255,255,255,0.25); color: white;
    padding: 6px 14px; border-radius: 4px; text-decoration: none;
    font-size: 13px; font-weight: 600; white-space: nowrap;">
    KPI
  </a>

  <!-- Неактивные вкладки -->
  <a href="/report/104" style="
    background: transparent; color: rgba(255,255,255,0.85);
    padding: 6px 14px; border-radius: 4px; text-decoration: none;
    font-size: 13px; white-space: nowrap;">
    Участники
  </a>
  <a href="/report/105" style="
    background: transparent; color: rgba(255,255,255,0.85);
    padding: 6px 14px; border-radius: 4px; text-decoration: none;
    font-size: 13px; white-space: nowrap;">
    Факторный анализ
  </a>
  <a href="/report/106" style="
    background: transparent; color: rgba(255,255,255,0.85);
    padding: 6px 14px; border-radius: 4px; text-decoration: none;
    font-size: 13px; white-space: nowrap;">
    Рейтинг
  </a>
  <a href="/report/107" style="
    background: transparent; color: rgba(255,255,255,0.85);
    padding: 6px 14px; border-radius: 4px; text-decoration: none;
    font-size: 13px; white-space: nowrap;">
    Геоаналитика
  </a>
  <a href="/report/108" style="
    background: transparent; color: rgba(255,255,255,0.85);
    padding: 6px 14px; border-radius: 4px; text-decoration: none;
    font-size: 13px; white-space: nowrap;">
    Сравнение
  </a>
</div>
```

### Шаги добавления

```
# 1. Добавить TextBlock
mcp__modusbi__component_crud(action="add",
  report_id=<ID>,
  component_type="HsTextBlock",
  title="Навигация",
  text_content="<div style='background: linear-gradient(135deg, #0d47a1, #1565c0, #1976d2); ...'> ... </div>",
  x=0, y=0, w=48, h=3
)

# 2. Обновить config (убрать заголовок, убрать padding)
mcp__modusbi__component_crud(action="update", report_id=<ID>, component_idx=<N>,
  config_overrides={
    "showtitle": false,
    "margin.l": 0, "margin.r": 0, "margin.t": 0, "margin.b": 0,
    "outline.enabled": false
  }
)

# 3. Для КАЖДОГО отчёта в наборе — добавить навигацию с нужной активной вкладкой
# В HTML текущего отчёта: активная кнопка имеет background: rgba(255,255,255,0.25)
# Остальные: background: transparent

# 4. Сдвинуть остальные компоненты ниже
# Для каждого компонента K с y_old: layout_update(y=y_old+3)
```

### Варианты цветовых схем

```
# Blue Gradient (рекомендуемый паттерн)
background: linear-gradient(135deg, #0d47a1, #1565c0, #1976d2)

# Dark (тёмная тема)
background: linear-gradient(135deg, #1a1a2e, #16213e, #0f3460)

# Green
background: linear-gradient(135deg, #1b5e20, #2e7d32, #388e3c)

# Neutral Grey
background: linear-gradient(135deg, #37474f, #455a64, #546e7a)
```

---

## Способ C: CSS-стилизация нативного TabsPanel

### Когда использовать
- Уже есть HsTabsPanel, нужно добавить градиент и стиль
- Минимум изменений кода

```
# Получить текущий CSS
mcp__modusbi__style_operations(action="get", report_id=<ID>)

# Добавить CSS для TabsPanel
# ВАЖНО: реальные DOM-классы рендера TabsPanel — .hsTabsPanel (строчная!) и .hsTab (кнопки)
# (.hsTabsPanel с заглавной — это имя ТИПА компонента, в DOM его нет → :has() не сматчится)
# НЕ используй .tabsPanel или .tabsPanel button — эти классы НЕ существуют!
mcp__modusbi__style_operations(action="update", report_id=<ID>, css="""
  /* Текущий CSS... */

  /* z-index для nav panel */
  .react-grid-item:has(.hsTabsPanel) { z-index: 200 !important; }

  /* Градиентный фон для TabsPanel */
  .hsGridPanel:has(.hsTabsPanel) {
    background: linear-gradient(135deg, #0d47a1, #1565c0, #1976d2) !important;
    border-radius: 0 !important;
    border: none !important;
  }

  /* Прозрачный фон для внутренних обёрток */
  .hsGridPanel:has(.hsTabsPanel) .hsGridPanelContainer,
  .hsGridPanel:has(.hsTabsPanel) .inner,
  .hsGridPanel:has(.hsTabsPanel) .hsTabsPanel,
  .hsGridPanel:has(.hsTabsPanel) .hsTabsPanel {
    background: transparent !important;
  }

  /* Кнопки — базовый стиль (.hsTab — правильный класс!) */
  .hsTab {
    background: transparent !important;
    color: rgba(255,255,255,0.85) !important;
    border: none !important;
    font-size: 13px !important;
    padding: 6px 14px !important;
    border-radius: 4px !important;
    transition: background 0.2s ease !important;
    font-weight: 400 !important;
    cursor: pointer !important;
  }

  /* Hover */
  .hsTab:hover {
    background: rgba(255,255,255,0.15) !important;
    color: white !important;
  }

  /* Активная кнопка (.hsTab.active — правильный класс!) */
  .hsTab.active {
    background: rgba(255,255,255,0.25) !important;
    color: white !important;
    font-weight: 600 !important;
  }
""")
```

---

## Workflow: добавить nav bar в группу отчётов

```
# Типичный сценарий: 6 отчётов, нужна единая навигация

# Шаг 1: Определить report_id каждого отчёта (подставьте свои ID)
reports = {
  "KPI": 101,
  "Участники": 102,
  "Факторный анализ": 103,
  "Рейтинг": 104,
  "Геоаналитика": 105,
  "Сравнение": 106
}

# Шаг 2: Для каждого отчёта — создать HTML nav с АКТИВНОЙ нужной вкладкой
# В каждом отчёте одна кнопка имеет background: rgba(255,255,255,0.25)

# Шаг 3: Добавить TextBlock (y=0) + сдвинуть остальные на +3

# Шаг 4: Проверить layout — TextBlock y=0, w=48, h=3
mcp__modusbi__component_crud(action="layout_update", report_id=<ID>, component_idx=<N>,
  x=0, y=0, w=48, h=3
)

# Шаг 5: z-index для TextBlock (чтобы nav был поверх)
# В CSS:
.react-grid-item:has(.textBlock) { z-index: 50; }
# НО: для nav это не нужно — он y=0, выше всех по позиции
```

---

## Удаление кнопки из TabsPanel

```
# Получить список кнопок
mcp__modusbi__component_axes(action="tabs_button_list", report_id=<ID>, component_idx=<N>
)
# Вернёт: [{index: 0, label: "KPI", link: ...}, {index: 1, ...}]

# Удалить кнопку по индексу
mcp__modusbi__component_axes(action="tabs_button_delete", report_id=<ID>, component_idx=<N>,
  field_index=2  # индекс кнопки в массиве
)
```

---

## Checklist

- [ ] Выбран способ: A (TabsPanel) / B (TextBlock HTML) / C (CSS TabsPanel)
- [ ] **A**: TabsPanel добавлен, bgColor задан, кнопки добавлены через tabs_button_add
- [ ] **C**: Используй `.hsTabsPanel` и `.hsTab` (НЕ `.tabsPanel button`!) — реальные CSS-классы
- [ ] **B**: TextBlock добавлен, HTML с градиентом, активная вкладка выделена
- [ ] **B**: margin.l/r/t/b=0, showtitle=false, outline.enabled=false
- [ ] Компонент на y=0, x=0, w=48, h=3 (full-width)
- [ ] Все остальные компоненты сдвинуты на +3 по Y
- [ ] Для группы отчётов: в каждом отчёте активная вкладка = текущий отчёт
- [ ] Проверка в браузере: ссылки работают, hover виден, активная вкладка выделена

---

## ARGUMENTS

Список отчётов для навигации (report_id → название): указать в аргументах.
Способ: A (TabsPanel), B (TextBlock HTML), C (CSS).
Активный отчёт: report_id текущего отчёта (для выделения активной вкладки).
Цветовая схема: blue (default) / dark / green / grey.
