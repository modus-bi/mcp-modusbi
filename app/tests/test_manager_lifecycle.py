"""Tests for InstanceManager lifecycle:
- Shared httpx client lazy-init
- aclose() idempotent
- Lifespan finally calls aclose

Run:
    python -m app.tests.test_manager_lifecycle
"""
import asyncio
import sys
import time
import httpx

from app.core.instances import Instance, InstanceManager


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


async def test_http_client_lazy_init() -> None:
    section("shared httpx client lazy-init")

    instance = make_instance()
    manager = InstanceManager(instance)
    check("manager._http is None initially", manager._http is None)

    client1 = await manager._http_client()
    check("first call creates AsyncClient", isinstance(client1, httpx.AsyncClient))
    check("manager._http stored", manager._http is client1)

    client2 = await manager._http_client()
    check("second call returns same instance", client2 is client1)

    await manager.aclose()


async def test_aclose_idempotent() -> None:
    section("aclose() idempotent")

    instance = make_instance()
    manager = InstanceManager(instance)
    await manager._http_client()  # init

    await manager.aclose()
    check("first aclose succeeds; _http is None", manager._http is None)

    # Idempotent — second close doesn't raise
    try:
        await manager.aclose()
        check("second aclose() doesn't raise", True)
    except Exception as e:
        check("second aclose() doesn't raise", False, detail=str(e))


async def test_aclose_then_reuse() -> None:
    section("aclose() then new request creates new pool")

    instance = make_instance()
    manager = InstanceManager(instance)

    client1 = await manager._http_client()
    await manager.aclose()
    check("after aclose, _http is None", manager._http is None)

    client2 = await manager._http_client()
    check("new pool created after aclose", isinstance(client2, httpx.AsyncClient))
    check("new pool != old pool", client2 is not client1)

    await manager.aclose()


async def test_concurrent_lazy_init() -> None:
    section("concurrent _http_client() returns same client")

    instance = make_instance()
    manager = InstanceManager(instance)

    # 5 concurrent corouтines — all should get the same instance
    results = await asyncio.gather(
        manager._http_client(),
        manager._http_client(),
        manager._http_client(),
        manager._http_client(),
        manager._http_client(),
    )
    first = results[0]
    check("all 5 concurrent calls return same client",
          all(r is first for r in results))

    await manager.aclose()


async def test_get_client_passes_http_pool() -> None:
    section("get_client() passes shared http_client to InstanceClient")

    instance = make_instance()
    manager = InstanceManager(instance)

    ic = await manager.get_client()
    check("InstanceClient has http_client", ic._http is not None)
    check("InstanceClient http_client is manager's pool", ic._http is await manager._http_client())

    await manager.aclose()


async def test_legacy_instance_client_no_pool() -> None:
    section("legacy InstanceClient(instance) without http_client uses per-call")

    from app.core.instances import InstanceClient
    instance = make_instance()

    client = InstanceClient(instance)
    check("legacy client has _http=None", client._http is None)
    check("legacy client has _reauth=None", client._reauth is None)


async def main() -> None:
    await test_http_client_lazy_init()
    await test_aclose_idempotent()
    await test_aclose_then_reuse()
    await test_concurrent_lazy_init()
    await test_get_client_passes_http_pool()
    await test_legacy_instance_client_no_pool()

    print(f"\n===\nResult: {ok} OK, {fail} FAIL")
    sys.exit(0 if fail == 0 else 1)


if __name__ == "__main__":
    asyncio.run(main())
