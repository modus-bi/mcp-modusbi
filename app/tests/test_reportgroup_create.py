"""Regression: reportgroup create must send parent_group_id=null (not 0) for root.

Backend (ModusBI API) returns HTTP 500 when parent_group_id=0 is sent for a
root-level group. The MCP tool must normalise 0/None -> null. See.
"""
import asyncio
from app.tools.reportgroup_operations import _create_group, _update_group, _move_group


class FakeClient:
    """Captures the payload sent to api_call; returns a canned 200 response."""

    def __init__(self, current=None):
        self.sent = None
        self._current = current or {
            "ID": 7, "name": "old", "caption": "old",
            "parent_group_id": None, "menu": 1, "is_extended": 1, "options": {}, "def": 0,
        }

    async def api_call(self, object_name, command_name, object_id=None, data=None, retry=True):
        if command_name == "get":
            return {"status": 200, "data": [self._current]}
        self.sent = {"object": object_name, "command": command_name, "data": data}
        return {"status": 200, "data": [{
            "ID": 999, "name": "x", "caption": "x", "parent_group_id": None,
        }]}


def run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


def main() -> int:
    ok = fail = 0

    def check(label, cond):
        nonlocal ok, fail
        if cond:
            print(f"  [OK ] {label}"); ok += 1
        else:
            print(f"  ❌ {label}"); fail += 1

    print("=== reportgroup create/update/move: parent_group_id 0 -> null ===")

    # create, root (parent_id=0 default) -> must be None
    c = FakeClient(); run(_create_group(c, name="g", parent_id=0))
    check("create parent_id=0 -> parent_group_id is None",
          c.sent["data"][0]["parent_group_id"] is None)

    # create, nested (parent_id=20) -> preserved
    c = FakeClient(); run(_create_group(c, name="g", parent_id=20))
    check("create parent_id=20 -> parent_group_id == 20",
          c.sent["data"][0]["parent_group_id"] == 20)

    # update, explicit parent_id=0 -> None
    c = FakeClient(); run(_update_group(c, group_id=7, parent_id=0))
    check("update parent_id=0 -> parent_group_id is None",
          c.sent["data"][0]["parent_group_id"] is None)

    # move, parent_id=0 -> None
    c = FakeClient(); run(_move_group(c, group_id=7, parent_id=0))
    check("move parent_id=0 -> parent_group_id is None",
          c.sent["data"][0]["parent_group_id"] is None)

    print(f"\nResult: {ok} OK, {fail} FAIL")
    return fail


if __name__ == "__main__":
    import sys
    sys.exit(1 if main() else 0)
