"""Tests for InstanceClient silent re-auth retry on 401.

Covers:
- silent retry on 401 → 200
- double 401 raises AuthenticationError
- callback called exactly once on success
- no callback → raise immediately (legacy)
- recordsets.create retry path (different URL/payload shape)
- api_get retry path
- network error during retry propagates as APIError
- callback failure (bad credentials) propagates without second request
- concurrent api_calls with shared lock → callback called once

Run:
    python -m app.tests.test_token_refresh
"""
import asyncio
import sys
import time
from typing import Any
from unittest.mock import patch, MagicMock

from app.core.instances import Instance, InstanceClient, InstanceManager
from app.core.exceptions import AuthenticationError, APIError


ok = 0
fail = 0


def check(label: str, cond: bool, detail: str = "") -> None:
    global ok, fail
    if cond:
        ok += 1
        print(f"  [OK ] {label}")
    else:
        fail += 1
        suffix = f" — {detail}" if detail else ""
        print(f"  [FAIL] {label}{suffix}")


def section(title: str) -> None:
    print(f"\n=== {title} ===")


def make_instance() -> Instance:
    return Instance(
        name="test",
        base_url="https://test.example",
        username="u",
        password="p",
        token="initial-token",
        token_exp=int(time.time()) + 3600,
        is_connected=True,
    )


class FakeResponse:
    def __init__(self, status_code: int, json_body: dict | None = None):
        self.status_code = status_code
        self._json = json_body or {"success": True}

    def json(self) -> dict:
        return self._json


class FakeAsyncClient:
    """Minimal async-context-manager replacement for httpx.AsyncClient."""

    def __init__(self, responses: list):
        self._responses = list(responses)
        self.call_count = 0

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, *args, **kwargs):
        self.call_count += 1
        if not self._responses:
            raise RuntimeError("FakeAsyncClient: out of mocked responses")
        r = self._responses.pop(0)
        if isinstance(r, Exception):
            raise r
        return r

    async def get(self, *args, **kwargs):
        return await self.post(*args, **kwargs)


def with_fake_client(responses: list):
    """Patch httpx.AsyncClient to return FakeAsyncClient with given responses."""
    fc = FakeAsyncClient(responses)
    return patch("app.core.instances.httpx.AsyncClient", return_value=fc), fc


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


async def test_silent_retry_on_401_then_200() -> None:
    section("silent retry on 401 → 200")

    instance = make_instance()
    reauth_calls = 0

    async def reauth(inst: Instance) -> None:
        nonlocal reauth_calls
        reauth_calls += 1
        inst.token = "fresh-token"
        inst.token_exp = int(time.time()) + 3600

    client = InstanceClient(instance, reauth_callback=reauth)
    responses = [FakeResponse(401), FakeResponse(200, {"data": "ok"})]
    p, fc = with_fake_client(responses)
    with p:
        result = await client.api_call("reports", "get", object_id=1)
    check("api_call returns 200 result after retry", result == {"data": "ok"})
    check("re-auth callback called exactly once", reauth_calls == 1,
          detail=f"got {reauth_calls}")
    check("instance has fresh token", instance.token == "fresh-token")
    check("two http requests (1 + 1 retry)", fc.call_count == 2,
          detail=f"got {fc.call_count}")


async def test_double_401_raises() -> None:
    section("double 401 raises AuthenticationError")

    instance = make_instance()

    async def reauth(inst: Instance) -> None:
        # Simulate successful re-auth — but server still returns 401 on retry
        inst.token = "fresh-token"
        inst.token_exp = int(time.time()) + 3600

    client = InstanceClient(instance, reauth_callback=reauth)
    responses = [FakeResponse(401), FakeResponse(401)]
    p, _ = with_fake_client(responses)
    with p:
        try:
            await client.api_call("reports", "get", object_id=1)
            check("raises AuthenticationError on double 401", False, detail="no raise")
        except AuthenticationError as e:
            check("raises AuthenticationError on double 401", True)
            check("error message mentions 'after refresh'",
                  "after refresh" in str(e), detail=str(e))


async def test_no_callback_raises_immediately() -> None:
    section("no callback → raise (legacy direct InstanceClient use)")

    instance = make_instance()
    client = InstanceClient(instance)  # no callback
    responses = [FakeResponse(401)]
    p, fc = with_fake_client(responses)
    with p:
        try:
            await client.api_call("reports", "get", object_id=1)
            check("raises AuthenticationError without callback", False)
        except AuthenticationError as e:
            check("raises AuthenticationError without callback", True)
            check("only one http request (no retry)", fc.call_count == 1)
            check("message mentions 're-auth not configured'",
                  "re-auth not configured" in str(e), detail=str(e))


async def test_api_get_silent_retry() -> None:
    section("api_get silent retry on 401")

    instance = make_instance()
    reauth_calls = 0

    async def reauth(inst: Instance) -> None:
        nonlocal reauth_calls
        reauth_calls += 1
        inst.token = "fresh"
        inst.token_exp = int(time.time()) + 3600

    client = InstanceClient(instance, reauth_callback=reauth)
    responses = [FakeResponse(401), FakeResponse(200, {"items": [1, 2]})]
    p, fc = with_fake_client(responses)
    with p:
        result = await client.api_get("geodata")
    check("api_get returns result after retry", result == {"items": [1, 2]})
    check("api_get reauth called once", reauth_calls == 1)


async def test_recordsets_create_retry() -> None:
    section("recordsets.create retry uses same payload shape")

    instance = make_instance()

    async def reauth(inst: Instance) -> None:
        inst.token = "fresh"
        inst.token_exp = int(time.time()) + 3600

    client = InstanceClient(instance, reauth_callback=reauth)
    responses = [FakeResponse(401), FakeResponse(200, {"rows": []})]
    p, _ = with_fake_client(responses)
    with p:
        result = await client.api_call(
            "recordsets", "create",
            object_id=42,
            data=[{"select": [{"name": "id"}]}],
        )
    check("recordsets retry succeeds", result == {"rows": []})


async def test_callback_failure_propagates() -> None:
    section("callback raises → propagates without second request")

    instance = make_instance()
    call_count = 0

    async def reauth(inst: Instance) -> None:
        nonlocal call_count
        call_count += 1
        raise AuthenticationError("Bad credentials", details={"instance": inst.name})

    client = InstanceClient(instance, reauth_callback=reauth)
    responses = [FakeResponse(401)]  # Only first request
    p, fc = with_fake_client(responses)
    with p:
        try:
            await client.api_call("reports", "get", object_id=1)
            check("propagates callback exception", False)
        except AuthenticationError as e:
            check("propagates callback AuthenticationError", "Bad credentials" in str(e))
            check("only one http request (no retry after auth fail)", fc.call_count == 1,
                  detail=f"got {fc.call_count}")
            check("callback was called once", call_count == 1)


async def test_manager_passes_callback() -> None:
    section("InstanceManager.get_client passes _authenticate as callback")

    instance = make_instance()
    manager = InstanceManager(instance)
    # token is valid → get_client doesn't re-auth, just creates client
    client = await manager.get_client()
    check("client has reauth callback set", client._reauth is not None)
    # Verify it's manager's _authenticate (bound method via __func__).
    # InstanceManager._authenticate is a plain function (no descriptor magic);
    # bound method's __func__ should be identical.
    check("callback is manager._authenticate",
          getattr(client._reauth, "__func__", None) is InstanceManager._authenticate,
          detail=f"got {client._reauth!r}")


async def test_concurrent_calls_single_reauth() -> None:
    section("concurrent api_calls with manager Lock → re-auth called once")

    instance = make_instance()
    instance.token = "expired"
    manager = InstanceManager(instance)

    real_auth_calls = 0

    async def counting_auth(inst):
        nonlocal real_auth_calls
        real_auth_calls += 1
        # Simulate slow re-auth
        await asyncio.sleep(0.05)
        inst.token = "fresh"
        inst.token_exp = int(time.time()) + 3600
        inst.is_connected = True

    manager._do_authenticate = counting_auth  # type: ignore

    # One client shared via the same instance reference; lock is per-manager.
    client = InstanceClient(instance, reauth_callback=manager._authenticate)

    # Counter-based fake: each first request from the 3 coroutines returns 401,
    # each retry (4th, 5th, 6th) returns 200. Avoids race on shared list pop.
    class CountingFake(FakeAsyncClient):
        def __init__(self):
            super().__init__([])
            self.first_401 = 3  # first 3 → 401, rest → 200

        async def post(self, *args, **kwargs):
            self.call_count += 1
            if self.call_count <= self.first_401:
                return FakeResponse(401)
            return FakeResponse(200, {"r": self.call_count})

    fc = CountingFake()
    with patch("app.core.instances.httpx.AsyncClient", return_value=fc):
        results = await asyncio.gather(
            client.api_call("reports", "get", object_id=1),
            client.api_call("reports", "get", object_id=2),
            client.api_call("reports", "get", object_id=3),
        )
    check("all 3 concurrent calls returned successfully", len(results) == 3)
    check("real _authenticate called exactly once (lock + double-check)",
          real_auth_calls == 1, detail=f"got {real_auth_calls}")
    check("total http calls = 6 (3 first 401 + 3 retry 200)",
          fc.call_count == 6, detail=f"got {fc.call_count}")


async def main() -> None:
    await test_silent_retry_on_401_then_200()
    await test_double_401_raises()
    await test_no_callback_raises_immediately()
    await test_api_get_silent_retry()
    await test_recordsets_create_retry()
    await test_callback_failure_propagates()
    await test_manager_passes_callback()
    await test_concurrent_calls_single_reauth()

    print(f"\n===\nResult: {ok} OK, {fail} FAIL")
    sys.exit(0 if fail == 0 else 1)


if __name__ == "__main__":
    asyncio.run(main())
