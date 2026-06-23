#!/usr/bin/env python3
"""Frontend version sync: сверка MCP-схемы слагов с исходниками фронта конкретной версии.

Использование:
    python scripts/frontend_version_sync.py --src <frontend_src_dir> --version <X.Y.Z>
    python scripts/frontend_version_sync.py --src docs/FRONTEND/bi_react-develop --version 3.15.3

Что делает:
  1. Извлекает render-контракт версии: какие config-ключи читают адаптеры (src/adaptors/**,
     SpecGenerator+plugins; без ConfigEditor-панели и вендорной либы).
  2. Сверяет с SLUG_SCHEMA: для каждого слага — читает ли рендер его json-ключ.
  3. Пишет docs/architecture/readiness/audit/render_contract_<version>.json.
  4. Diff с предыдущей синхронизированной версией (новые/пропавшие читаемые ключи).
  5. Обновляет docs/architecture/readiness/audit/frontend_support.json (реестр проверенных версий).

Упрощает переход между версиями фронта и фиксирует, против какой версии выверена MCP-схема.
"""
import argparse
import json
import re
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/architecture/readiness/audit"


def render_files(src_root):
    adapt = Path(src_root) / "src/adaptors"
    files = []
    for p in adapt.rglob("*.js"):
        s = str(p).replace("\\", "/")
        if "/amcharts3/amcharts/" in s or "ConfigEditor" in s or ".spec." in s:
            continue
        files.append(p)
    return files


def leaf_of(path):
    if not path:
        return ""
    seg = re.split(r"[.\[\]]+", path.split(" ")[0].strip("]"))
    return seg[-1] if seg else ""


def build_contract(src_root):
    table = json.loads((ROOT / "docs/architecture/components/slugs/slug-table.json").read_text(encoding="utf-8"))["rows"]
    files = render_files(src_root)
    blob = "\n".join(p.read_text(encoding="utf-8", errors="ignore") for p in files)
    contract = {}
    for r in table:
        slug = r["slug"]
        leaf = leaf_of(r.get("effective") or r.get("json") or "")
        if not leaf or len(leaf) < 3:
            contract[slug] = "n/a"
            continue
        if re.search(r"\b(config|cfg)\." + re.escape(leaf) + r"\b", blob):
            contract[slug] = "render-reads"
        elif re.search(r"\b" + re.escape(leaf) + r"\b", blob):
            contract[slug] = "present"
        else:
            contract[slug] = "absent"
    return contract, len(files)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True, help="каталог исходников фронта")
    ap.add_argument("--version", required=True, help="версия фронта, напр. 3.15.3")
    ap.add_argument("--today", default=None, help="дата YYYY-MM-DD (по умолч. сегодня)")
    args = ap.parse_args()

    src = ROOT / args.src if not Path(args.src).is_absolute() else Path(args.src)
    if not (src / "src/adaptors").exists():
        raise SystemExit(f"нет src/adaptors в {src} — это исходники фронта?")

    contract, nfiles = build_contract(src)
    today = args.today or date.today().isoformat()
    counts = {}
    for v in contract.values():
        counts[v] = counts.get(v, 0) + 1

    cur = {"version": args.version, "synced": today, "src": args.src,
           "render_files": nfiles, "counts": counts, "contract": contract}
    cur_path = OUT / f"render_contract_{args.version}.json"

    # diff с предыдущей версией из реестра
    support_path = OUT / "frontend_support.json"
    support = json.loads(support_path.read_text(encoding="utf-8")) if support_path.exists() else {"versions": {}}
    prev_ver = None
    for v in sorted(support.get("versions", {})):
        if v != args.version:
            prev_ver = v
    diff = {}
    prev_file = OUT / f"render_contract_{prev_ver}.json" if prev_ver else None
    if prev_file and prev_file.exists():
        prev = json.loads(prev_file.read_text(encoding="utf-8"))["contract"]
        changed = {s: [prev.get(s), contract.get(s)] for s in contract
                   if prev.get(s) != contract.get(s)}
        diff = {"from": prev_ver, "changed": changed}

    cur["diff_from_prev"] = diff
    cur_path.write_text(json.dumps(cur, ensure_ascii=False, indent=1), encoding="utf-8")

    support.setdefault("versions", {})[args.version] = {
        "synced": today, "src": args.src, "render_files": nfiles,
        "counts": counts, "changed_vs_prev": len(diff.get("changed", {})) if diff else None,
    }
    support["latest_verified"] = sorted(support["versions"])[-1]
    support_path.write_text(json.dumps(support, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"version {args.version}: render-файлов {nfiles}, контракт {len(contract)} слагов")
    print(f"  {counts}")
    if diff:
        print(f"  diff vs {prev_ver}: изменено {len(diff['changed'])} слагов")
        for s, (a, b) in list(diff["changed"].items())[:15]:
            print(f"    {s}: {a} → {b}")
    print(f"→ {cur_path.name}, обновлён frontend_support.json")


if __name__ == "__main__":
    main()
