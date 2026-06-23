---
name: create-presentation
description: Генерация HTML-презентаций на reveal.js из структурированного плана. Создаёт готовые слайды с mermaid-диаграммами, таблицами, кодовыми блоками, анимациями. Корпоративная тема Модус (голубые градиенты). Используйте когда нужно создать презентацию, сгенерировать слайды, оформить доклад в HTML.
license: MIT
metadata:
    skill-author: ModusBI Team
    version: "1.0"
    domain: presentation
---

# Create Presentation: Генерация HTML-презентаций

## Overview

Этот skill генерирует HTML-презентации на базе reveal.js:
- Из outline (от `/present-outline`) в готовые слайды
- Корпоративная тема Модус (голубые градиенты)
- Mermaid-диаграммы, таблицы, кодовые блоки
- Speaker notes для докладчика
- Экспорт в PDF через браузер (Ctrl+P)

**Результат:** HTML-файл, открываемый в любом браузере.

**Зависимости:** reveal.js и mermaid подключаются через CDN (нужен интернет).

---

## When to Use This Skill

Используй этот skill когда пользователь:

- Просит **"создать презентацию"** или **"сгенерировать слайды"**
- Хочет **"HTML презентацию"** для доклада
- Нужна **"презентация в reveal.js"**
- Есть готовый **outline** (от `/present-outline`) и нужно его оформить

**Не использовать если:**
- Нужен только план (используй `/present-outline`)
- Нужен PPTX (используй office-ppt MCP-сервер)

---

## Standard Workflow

### Шаг 1: Получить outline

Если outline уже есть (от `/present-outline`) — использовать его.
Если нет — сначала вызвать `/present-outline` для планирования.

### Шаг 2: Сгенерировать HTML

**Структура файла:**

```html
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>[Название презентации]</title>

    <!-- reveal.js CDN -->
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/reveal.js@5.1.0/dist/reveal.css">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/reveal.js@5.1.0/dist/theme/white.css">

    <!-- Корпоративная тема Модус -->
    <style>
        [ВСТАВИТЬ CSS ИЗ ТЕМЫ modus-theme]
    </style>
</head>
<body>

<div class="reveal">
<div class="slides">

    <!-- Слайд 1: Титульный -->
    <section>
        <h1>[Название]</h1>
        <h3>[Подзаголовок]</h3>
        <p>[Автор, дата]</p>
        <aside class="notes">Speaker notes...</aside>
    </section>

    <!-- Слайд 2: Контент -->
    <section>
        <h2>[Заголовок]</h2>
        <ul>
            <li>Пункт 1</li>
            <li>Пункт 2</li>
        </ul>
    </section>

    <!-- ... остальные слайды ... -->

</div>
</div>

<!-- reveal.js -->
<script src="https://cdn.jsdelivr.net/npm/reveal.js@5.1.0/dist/reveal.js"></script>
<!-- mermaid -->
<script src="https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.min.js"></script>

<script>
    mermaid.initialize({ startOnLoad: false, theme: 'default' });
    Reveal.initialize({
        hash: true,
        slideNumber: true,
        transition: 'slide',
        plugins: []
    }).then(() => {
        mermaid.run({ querySelector: '.mermaid' });
    });
</script>

</body>
</html>
```

### Шаг 3: Типы слайдов

#### Титульный слайд

```html
<section class="title-slide">
    <h1>Интеллектуальный помощник для BI и ETL</h1>
    <h3>Как ИИ помогает собирать, описывать и использовать данные</h3>
    <p style="margin-top: 40px; font-size: 0.8em; opacity: 0.8;">
        Компания «Модус» | Партнёрский семинар 1С | 2026
    </p>
</section>
```

#### Слайд с большой цифрой (stat)

```html
<section>
    <div style="display: flex; align-items: center; justify-content: center; height: 100%;">
        <div style="text-align: center;">
            <div style="font-size: 120px; font-weight: 700; color: #0d47a1;">80%</div>
            <div style="font-size: 28px; color: #546e7a; margin-top: 10px;">
                времени аналитика уходит<br>на подготовку данных
            </div>
        </div>
    </div>
    <aside class="notes">Шокирующий факт для hook...</aside>
</section>
```

#### Слайд с mermaid-диаграммой

```html
<section>
    <h2>Архитектура MCP</h2>
    <div class="mermaid" style="font-size: 0.7em;">
        flowchart LR
            LLM["LLM"] -->|MCP| S1["postgres-mcp"]
            LLM -->|MCP| S2["modusbi-mcp"]
            S1 --> DB["PostgreSQL"]
            S2 --> API["ModusBI API"]
    </div>
</section>
```

#### Слайд "До / После" (comparison)

```html
<section>
    <h2>MCP vs REST API</h2>
    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 30px;">
        <div style="background: #ffebee; padding: 20px; border-radius: 10px; border-left: 5px solid #c62828;">
            <h3 style="color: #c62828;">Без MCP</h3>
            <ul>
                <li>N x M интеграций</li>
                <li>Vendor lock-in</li>
                <li>Недели на интеграцию</li>
            </ul>
        </div>
        <div style="background: #e8f5e9; padding: 20px; border-radius: 10px; border-left: 5px solid #2e7d32;">
            <h3 style="color: #2e7d32;">С MCP</h3>
            <ul>
                <li>N + M компонентов</li>
                <li>Открытый стандарт</li>
                <li>Часы на подключение</li>
            </ul>
        </div>
    </div>
</section>
```

#### Слайд с таблицей

```html
<section>
    <h2>DQ-метрики справочника</h2>
    <table>
        <thead>
            <tr><th>Метрика</th><th>Значение</th><th>Целевой</th><th>Статус</th></tr>
        </thead>
        <tbody>
            <tr><td>Completeness</td><td>78%</td><td>95%</td><td style="color: #c62828;">FAIL</td></tr>
            <tr><td>Uniqueness</td><td>92%</td><td>99%</td><td style="color: #ff9800;">WARNING</td></tr>
            <tr><td>Validity</td><td>54%</td><td>90%</td><td style="color: #c62828;">FAIL</td></tr>
        </tbody>
    </table>
</section>
```

#### Слайд с кодом

```html
<section>
    <h2>MCP Server — 4 строки</h2>
    <pre><code class="language-python" data-trim>
from mcp.server.fastmcp import FastMCP
mcp = FastMCP("DQ Profiler")

@mcp.tool()
def check_completeness(table: str) -> dict:
    """Проверить полноту данных в таблице"""
    return db.query(f"SELECT COUNT(*), COUNT(inn) FROM {table}")

mcp.run()
    </code></pre>
</section>
```

#### Слайд LIVE DEMO

```html
<section data-background-color="#0d47a1">
    <div style="text-align: center; color: white;">
        <h1 style="color: white; font-size: 72px;">LIVE DEMO</h1>
        <h3 style="color: #bbdefb;">Профилирование качества данных</h3>
        <p style="color: #90caf9; margin-top: 20px;">3 минуты</p>
    </div>
</section>
```

#### Слайд CTA (Call to Action)

```html
<section>
    <h2>Попробуйте сами</h2>
    <div style="text-align: center; margin-top: 40px;">
        <p style="font-size: 24px;">Модус:Аналитический портал + ИИ</p>
        <p style="font-size: 18px; color: #546e7a;">your-portal.example.com | info@example.com</p>
    </div>
</section>
```

### Шаг 4: Сохранить файл

```
Путь: exports/{slug}_presentation.html
Пример: exports/ai_bi_etl_presentation.html
```

---

## Корпоративная тема Модус

### CSS тема (встроить в `<style>`)

```css
/* Modus Corporate Theme — Blue Gradients */
:root {
    --primary: #0d47a1;
    --primary-light: #1976d2;
    --accent: #42a5f5;
    --bg: #fafafa;
    --text: #1a237e;
    --text-light: #546e7a;
}

.reveal {
    font-family: 'Segoe UI', -apple-system, Arial, sans-serif;
    color: var(--text);
}

.reveal h1, .reveal h2, .reveal h3 {
    color: var(--primary);
    font-weight: 700;
}

.reveal h1 { font-size: 2.2em; }
.reveal h2 { font-size: 1.6em; }
.reveal h3 { font-size: 1.2em; color: var(--primary-light); }

/* Title slide */
.reveal .title-slide h1 {
    background: linear-gradient(135deg, var(--primary), var(--primary-light));
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    font-size: 2.5em;
}

/* Tables */
.reveal table {
    width: 90%;
    margin: 20px auto;
    border-collapse: separate;
    border-spacing: 0;
    border-radius: 8px;
    overflow: hidden;
    font-size: 0.7em;
}
.reveal table thead tr {
    background: linear-gradient(180deg, var(--primary-light), var(--primary));
    color: white;
}
.reveal table th { padding: 12px 16px; text-align: left; }
.reveal table td { padding: 10px 16px; border-bottom: 1px solid #e3f2fd; }
.reveal table tbody tr:nth-child(even) td { background: #e3f2fd; }

/* Code blocks */
.reveal pre {
    border-radius: 8px;
    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
    font-size: 0.55em;
}
.reveal pre code {
    padding: 20px;
    max-height: 500px;
}

/* Lists */
.reveal ul, .reveal ol {
    font-size: 0.85em;
    line-height: 1.8;
}
.reveal li {
    margin-bottom: 8px;
}

/* Slide number */
.reveal .slide-number {
    color: var(--primary);
    font-size: 14px;
}

/* Speaker notes indicator */
.reveal .speaker-notes-toggle {
    display: none;
}

/* Mermaid diagrams */
.mermaid {
    margin: 20px auto;
}

/* Footer */
.slide-footer {
    position: fixed;
    bottom: 10px;
    left: 20px;
    font-size: 12px;
    color: var(--text-light);
    opacity: 0.6;
}
```

---

## Validation Checklist

Перед сохранением проверить:

- [ ] HTML валиден (все теги закрыты)
- [ ] reveal.js CDN подключён (v5.1.0+)
- [ ] mermaid CDN подключён (v11+)
- [ ] Тема Модус встроена в `<style>`
- [ ] Все мermaid-диаграммы обёрнуты в `<div class="mermaid">`
- [ ] Speaker notes в `<aside class="notes">`
- [ ] Навигация работает (стрелки, пробел)
- [ ] Slide numbers включены
- [ ] Файл открывается в Chrome/Firefox

---

## Integration with Other Skills

- `/present-outline` → outline → `/create-presentation` → HTML файл
- `/demo-scenario` → демо-слайды с тегом `data-background-color`
- `/mcp-explainer` → контент для архитектурных слайдов
- `/data-storytelling` → narrative arc и визуальные паттерны

---

## Best Practices

1. **Не более 15-20 слайдов** для 15-минутного доклада
2. **Минимум текста** — ключевые фразы, не предложения
3. **Mermaid для архитектуры** — лучше чем статичные картинки
4. **Код крупно** — font-size не менее 0.55em для читаемости
5. **Контраст** — тёмный текст на светлом фоне для проектора
6. **Speaker notes** — основной текст доклада в `<aside class="notes">`
7. **Progressive disclosure** — используй фрагменты `class="fragment"` для поэтапного раскрытия
