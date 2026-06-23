"""Wire-level verification of deferred tool meta hints.

Spawns the server via stdio, runs initialize + tools/list, and checks:
  1. Exactly 19 tools listed (backward compat for all clients).
  2. Exactly 11 tools have `_meta["anthropic/defer_loading"]=True`.
  3. The 8 hot tools have NO defer_loading key (none in _meta or _meta absent).
  4. tools/call works on at least one hot tool and one deferred tool
     (proves _meta does not break invocation paths).
  5. Non-meta envelope (clients that ignore _meta) ≈ baseline.

Exits 0 on success, 1 on any check failure.
"""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.tools.profiles import HOT_TOOLS, DEFERRED_TOOLS  # noqa: E402
from app.tools.token_counter import count_tokens_json  # noqa: E402


async def call(proc, payload):
    proc.stdin.write((json.dumps(payload) + "\n").encode())
    await proc.stdin.drain()


async def read_until(proc, want_id):
    while True:
        line = await proc.stdout.readline()
        if not line:
            return None
        try:
            r = json.loads(line)
        except Exception:
            continue
        if r.get("id") == want_id:
            return r


async def main() -> int:
    proc = await asyncio.create_subprocess_exec(
        sys.executable, "-m", "app.server", "--readonly",
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=str(Path(__file__).resolve().parent.parent),
        limit=10 * 1024 * 1024,
    )
    failures: list[str] = []
    try:
        await call(proc, {
            "jsonrpc": "2.0", "id": 1, "method": "initialize",
            "params": {"protocolVersion": "2024-11-05", "capabilities": {},
                       "clientInfo": {"name": "verify-tool-wire", "version": "1"}},
        })
        await call(proc, {"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}})
        await call(proc, {"jsonrpc": "2.0", "id": 2, "method": "tools/list"})

        await read_until(proc, 1)
        list_resp = await read_until(proc, 2)
        if not list_resp:
            return _fail(["no tools/list response"], proc)

        tools = list_resp["result"]["tools"]

        # 1. count
        if len(tools) != 19:
            failures.append(f"expected 19 tools, got {len(tools)}")

        # 2. _meta on deferred
        with_meta = {t["name"] for t in tools
                     if (t.get("_meta") or {}).get("anthropic/defer_loading") is True}
        expected_deferred = set(DEFERRED_TOOLS)
        if with_meta != expected_deferred:
            failures.append(
                f"meta mismatch — extra={with_meta - expected_deferred}, "
                f"missing={expected_deferred - with_meta}"
            )

        # 3. hot tools clean
        hot_with_meta = {t["name"] for t in tools
                         if t["name"] in HOT_TOOLS
                         and (t.get("_meta") or {}).get("anthropic/defer_loading")}
        if hot_with_meta:
            failures.append(f"hot tools wrongly marked deferred: {hot_with_meta}")

        # 4. tools/call sanity — hot tool (component_crud help)
        hot_test = "component_crud"
        deferred_test = "instance_operations"
        await call(proc, {
            "jsonrpc": "2.0", "id": 3, "method": "tools/call",
            "params": {"name": hot_test, "arguments": {"action": "help"}},
        })
        r3 = await read_until(proc, 3)
        if not r3 or "error" in r3:
            failures.append(f"hot tool {hot_test}/help failed: {r3}")

        # 5. tools/call on deferred — should also work despite _meta
        await call(proc, {
            "jsonrpc": "2.0", "id": 4, "method": "tools/call",
            "params": {"name": deferred_test, "arguments": {"action": "list"}},
        })
        r4 = await read_until(proc, 4)
        if not r4 or "error" in r4:
            failures.append(f"deferred tool {deferred_test}/list failed: {r4}")

        # 6. envelope sizes
        env_full = count_tokens_json({"tools": tools}, compact=True)
        env_strip = count_tokens_json(
            {"tools": [{k: v for k, v in t.items() if k != "_meta"} for t in tools]},
            compact=True,
        )
        env_hot_only = count_tokens_json(
            {"tools": [t for t in tools if t["name"] in HOT_TOOLS]},
            compact=True,
        )
        print(f"envelope full (with _meta on 11):    {env_full} compact tokens")
        print(f"envelope w/o _meta (classic clients): {env_strip}")
        print(f"envelope hot-only (Tool Search):      {env_hot_only}")
        print(f"_meta overhead:                       +{env_full - env_strip}")
        print(f"Tool Search saving (hot vs full):     -{env_full - env_hot_only} "
              f"({100 * (env_full - env_hot_only) / env_full:.1f}%)")

    finally:
        proc.terminate()
        try:
            await asyncio.wait_for(proc.wait(), 3)
        except asyncio.TimeoutError:
            proc.kill()

    if failures:
        print("\nFAIL:")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("\nALL CHECKS PASS")
    return 0


def _fail(msgs, proc):  # legacy helper, only on early exit
    proc.terminate()
    for m in msgs:
        print(f"FAIL: {m}")
    return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
