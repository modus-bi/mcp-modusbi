"""Tests for env-var-based configuration.

Verifies:
- Graceful error on missing required env vars (full + partial).
- P1: --security-ceiling × CLI mode 9-case matrix.
- P1: authenticate() failure during lifespan does not crash startup.

Run with:
    python -m app.tests.test_env_config
"""
import asyncio
import os
import subprocess
import sys
from contextlib import contextmanager


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


@contextmanager
def temp_env(updates: dict[str, str | None]):
    """Temporarily set/unset env vars; restore on exit."""
    saved = {k: os.environ.get(k) for k in updates}
    try:
        for k, v in updates.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        yield
    finally:
        for k, v in saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def test_missing_env_vars_full() -> None:
    """server fails fast if all 3 required env vars are missing."""
    section("все обязательные env vars отсутствуют")

    with temp_env({"MODUSBI_URL": None, "MODUSBI_USERNAME": None, "MODUSBI_PASSWORD": None}):
        # Запускаем сервер subprocess'ом и читаем stderr
        proc = subprocess.run(
            [sys.executable, "-m", "app.server", "--readonly"],
            input="",
            capture_output=True,
            text=True,
            timeout=10,
        )
        check("сервер падает при отсутствии env vars", proc.returncode != 0)
        # Сообщение об ошибке должно перечислить все 3 missing vars
        for var in ("MODUSBI_URL", "MODUSBI_USERNAME", "MODUSBI_PASSWORD"):
            check(
                f"stderr упоминает {var}",
                var in proc.stderr,
                detail=f"stderr={proc.stderr[:200]}",
            )


def test_missing_env_vars_partial() -> None:
    """server fails with specific missing var name when only some are set."""
    section("partial env vars")

    with temp_env({
        "MODUSBI_URL": "https://test.example/",
        "MODUSBI_USERNAME": None,
        "MODUSBI_PASSWORD": None,
    }):
        proc = subprocess.run(
            [sys.executable, "-m", "app.server", "--readonly"],
            input="",
            capture_output=True,
            text=True,
            timeout=10,
        )
        check("сервер падает при partial env vars", proc.returncode != 0)
        check(
            "stderr упоминает MODUSBI_USERNAME",
            "MODUSBI_USERNAME" in proc.stderr,
            detail=f"stderr={proc.stderr[:200]}",
        )
        check(
            "stderr упоминает MODUSBI_PASSWORD",
            "MODUSBI_PASSWORD" in proc.stderr,
            detail=f"stderr={proc.stderr[:200]}",
        )


def test_security_ceiling_matrix() -> None:
    """P1: --security-ceiling vs CLI mode (9-case matrix).

    strictness: readonly (2) > demo (1) > readwrite (0).
    Final mode = strictest of (CLI, ceiling).
    """
    section("P1 — security ceiling matrix (9 случаев)")

    cases = [
        ("readwrite", "readwrite", "readwrite"),
        ("readwrite", "demo", "demo"),
        ("readwrite", "readonly", "readonly"),
        ("demo", "readwrite", "demo"),
        ("demo", "demo", "demo"),
        ("demo", "readonly", "readonly"),
        ("readonly", "readwrite", "readonly"),
        ("readonly", "demo", "readonly"),
        ("readonly", "readonly", "readonly"),
    ]

    # Reset module-level security state in main process before each test
    # (we run in subprocess so each invocation is fresh)
    base_env = {
        "MODUSBI_URL": "https://nonexistent.invalid/",
        "MODUSBI_USERNAME": "test",
        "MODUSBI_PASSWORD": "test",
    }

    for cli_mode, ceiling, expected in cases:
        cli_flag = f"--{cli_mode}"
        # This test owns CLI mode resolution, not DNS/authentication. Stop at
        # the transport boundary so an unreachable test host cannot turn the
        # nine-case matrix into a network timeout (lifespan has separate tests).
        launch = "import app.server as s; s.mcp.run = lambda **kwargs: None; s.main()"
        proc = subprocess.run(
            [sys.executable, "-c", launch, cli_flag, "--security-ceiling", ceiling],
            env={**os.environ, **base_env},
            input="",
            capture_output=True,
            text=True,
            timeout=30,  # Cold Python/MCP imports on Windows can exceed 8 s.
        )
        # Transport is stubbed; verify the actual CLI's resolved mode log.
        # READONLY/READWRITE/DEMO logged in main()
        expected_log = expected.upper()
        check(
            f"CLI={cli_mode}, ceiling={ceiling} → {expected}",
            expected_log in proc.stderr.upper(),
            detail=f"stderr first 300: {proc.stderr[:300]}",
        )


def test_lifespan_authenticate_failure_continues() -> None:
    """P1: authenticate() failure during startup logs WARNING but doesn't kill server.

    The server should still register tools — failure surfaces only at first tool call.
    """
    section("P1 — auth failure не валит lifespan")

    with temp_env({
        "MODUSBI_URL": "https://nonexistent.invalid/",
        "MODUSBI_USERNAME": "test",
        "MODUSBI_PASSWORD": "test",
    }):
        # Запустим сервер на 2 секунды и проверим что не упал немедленно.
        proc = subprocess.Popen(
            [sys.executable, "-m", "app.server", "--readonly"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        try:
            # Дать время на lifespan + auth attempt
            try:
                proc.wait(timeout=2.5)
                # Если завершился — не должен с code 0 при auth failure (warning, не error)
                check(
                    "сервер не падает при auth failure (lifespan continues)",
                    proc.returncode is None or proc.returncode == 0,
                    detail=f"returncode={proc.returncode}",
                )
            except subprocess.TimeoutExpired:
                # Сервер живёт = успех (его остановим через kill)
                check("сервер запустился и работает несмотря на auth failure", True)
                proc.terminate()
                try:
                    proc.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    proc.kill()

            stderr_output = proc.stderr.read() if proc.stderr else ""
            check(
                "stderr содержит WARNING про auth failure",
                "Could not authenticate" in stderr_output or "WARNING" in stderr_output.upper(),
                detail=f"stderr first 300: {stderr_output[:300]}",
            )
        finally:
            if proc.poll() is None:
                proc.kill()


def test_url_validation() -> None:
    """URL format validation in lifespan + via _validate_modusbi_url helper."""
    section("P1 — MODUSBI_URL format validation")

    from app.server import _validate_modusbi_url
    import logging as _logging

    # Capture warnings from logger
    handler = _logging.handlers.MemoryHandler(capacity=100)
    handler.setLevel(_logging.WARNING)
    target_logger = _logging.getLogger("app.server")
    target_logger.addHandler(handler)

    # --- Valid cases (should not raise) ---
    valid_cases = [
        ("https://portal.example.com", "https://portal.example.com"),
        ("https://your-portal.example.com/", "https://your-portal.example.com"),  # trailing slash stripped
        ("  https://host  ", "https://host"),                            # whitespace stripped
        ("http://localhost:8000", "http://localhost:8000"),
        ("http://10.0.0.1", "http://10.0.0.1"),
        ("https://internal-host", "https://internal-host"),
        ("https://[::1]:8080", "https://[::1]:8080"),                    # IPv6
        ("https://тест.рф", "https://тест.рф"),                          # IDN/unicode (raw)
    ]
    for raw, expected in valid_cases:
        try:
            result = _validate_modusbi_url(raw)
            check(f"valid URL accepted: {raw!r} → {expected!r}",
                  result == expected, detail=f"got {result!r}")
        except RuntimeError as e:
            check(f"valid URL accepted: {raw!r}", False, detail=f"raised: {e}")

    # --- Invalid cases (should raise RuntimeError) ---
    invalid_cases = [
        ("portal.example.com", "scheme"),        # no scheme
        ("ftp://host", "scheme"),                # wrong scheme
        ("https://", "hostname"),                # no netloc
        ("", "empty"),                           # empty after strip
        ("   ", "empty"),                        # whitespace only
    ]
    for raw, expected_keyword in invalid_cases:
        try:
            _validate_modusbi_url(raw)
            check(f"invalid URL rejected: {raw!r}", False, detail="no raise")
        except RuntimeError as e:
            check(f"invalid URL rejected: {raw!r} (mentions '{expected_keyword}')",
                  expected_keyword in str(e).lower(),
                  detail=f"msg: {e}")

    # --- Path warning (should accept but warn) ---
    # Reset captured warnings
    target_logger.removeHandler(handler)
    handler = _logging.handlers.MemoryHandler(capacity=100)
    handler.setLevel(_logging.WARNING)
    target_logger.addHandler(handler)

    result = _validate_modusbi_url("https://host/api/v2")
    check("URL with path returns reconstruction with path",
          result == "https://host/api/v2", detail=f"got {result!r}")
    path_warned = any("contains a path" in r.getMessage() for r in handler.buffer)
    check("URL with path triggers warning log", path_warned)

    target_logger.removeHandler(handler)


def main() -> None:
    test_missing_env_vars_full()
    test_missing_env_vars_partial()
    test_security_ceiling_matrix()
    test_lifespan_authenticate_failure_continues()
    test_url_validation()

    print(f"\n===\nResult: {ok} OK, {fail} FAIL")
    sys.exit(0 if fail == 0 else 1)


if __name__ == "__main__":
    main()
