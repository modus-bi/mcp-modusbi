"""Зелёно-красная сводка + что чинить, из FINDINGS + прокидка статуса в таблицу миграции.
Регенерация: python3 scripts/gen_slug_fixes.py
"""
import re, json, os, sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parents[1]
_FINDINGS = _ROOT / 'docs/architecture/readiness/audit/FINDINGS.md'
if not _FINDINGS.exists():
    print('FINDINGS.md отсутствует (внутренний реестр аудита, в публичном репо не публикуется) — пропуск.')
    sys.exit(0)
F = _FINDINGS.read_text(encoding='utf-8')

# реестр: | ID | Комп | Симптом | Владелец | Корень | Статус |
rows = []
for line in F.splitlines():
    m = re.match(r'\|\s*([A-Z]+\d+\w*)\s*\|\s*([^|]*)\|\s*([^|]*)\|\s*([^|]*)\|\s*([^|]*)\|\s*([^|]*)\|', line)
    if not m: continue
    id_, comp, symp, owner, root, status = [x.strip() for x in m.groups()]
    if id_=='ID': continue
    slugs = re.findall(r'`([a-zA-Z][a-zA-Z0-9._]+(?:/[a-zA-Z0-9._]+)?)`', symp)
    rows.append({'id':id_,'comp':comp,'symptom':symp,'owner':owner,'root':root,'status':status,'slugs':slugs})

def has(s, *e): return any(x in s for x in e)
red   = [r for r in rows if has(r['status'],'🔴')]
green = [r for r in rows if has(r['status'],'🟢')]
yellow= [r for r in rows if has(r['status'],'🟡')]
mcp   = [r for r in rows if 'MCP' in r['owner']]
front = [r for r in rows if 'front' in r['owner'].lower()]
back  = [r for r in rows if 'back' in r['owner'].lower()]
mcp_red = [r for r in mcp if has(r['status'],'🔴','🟡')]

# статус по слагу (для таблицы миграции)
slug_status = {}
for r in rows:
    st = '🔴' if has(r['status'],'🔴') else ('🟡' if has(r['status'],'🟡') else ('🟢' if has(r['status'],'🟢') else ''))
    for sl in r['slugs']:
        for part in sl.split('/'):
            slug_status.setdefault(part, (st, r['id'], r['owner']))

ngreen=nred=0

os.makedirs('docs/architecture/components/slugs', exist_ok=True)
with open('docs/architecture/components/slugs/slug_fixes.md','w',encoding='utf-8') as o:
    o.write("# Слаги: зелёное/красное + что чинить (из аудита FINDINGS)\n\n")
    o.write(f"> Сгенерировано `scripts/gen_slug_fixes.py` из `docs/architecture/readiness/audit/FINDINGS.md`.\n")
    o.write(f"> ⚠️ Аудит ещё НЕ финализирован — gap-fill не закрыт (см. `_PROGRESS.md`), цифры могут вырасти.\n\n")
    o.write("## Светофор находок\n\n")
    o.write(f"- 🟢 работает: **{len(green)}**\n- 🔴 сломано/silent-ignore: **{len(red)}**\n- 🟡 под вопросом: **{len(yellow)}**\n\n")
    o.write(f"По владельцу: **MCP {len(mcp)}** (наши фиксы) · front {len(front)} · back {len(back)}.\n\n")
    o.write("## 🔴 ЧТО ЧИНИТЬ В MCP (owner=MCP, красное/жёлтое)\n\n")
    o.write("| ID | Компонент | Симптом | Корень (file:line) | Статус |\n|---|---|---|---|---|\n")
    for r in mcp_red:
        o.write(f"| {r['id']} | {r['comp']} | {r['symptom'][:90]} | {r['root'][:60]} | {r['status']} |\n")
    o.write("\n## Фронт/бэк (НЕ наши — в FINDINGS_FOR_DEVS)\n\n")
    o.write(f"front-находок: {len(front)}, back: {len(back)} — см. FINDINGS.md раздел «Фронт/бэк».\n\n")
    o.write("## Связь с таблицей миграции\n\n")
    o.write(f"В `slug_migration_table.json` статус 🟢/🔴 и finding — в колонках таблицы.\n")
    o.write(f"Помечено: 🟢 {ngreen} · 🔴 {nred} слагов (остальные — не было отдельной находки / ещё ⏳).\n")
print(f"OK: green {len(green)} / red {len(red)} / yellow {len(yellow)}; MCP-фиксов(red+yellow) {len(mcp_red)}; слагов помечено 🟢{ngreen}/🔴{nred}")
