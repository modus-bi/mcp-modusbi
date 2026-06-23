"""Security mode enforcement tests.

Validates the claim documented in INSTALL.md and SERVER_INSTRUCTIONS:
`--readonly` blocks all write actions; `--security-ceiling readonly`
overrides any CLI write mode.

Without these tests, the readonly/ceiling promises are on trust.

Run:
    python -m app.tests.test_security_modes
"""
import sys

from app.core.security import (
    SecurityMode,
    READONLY_ACTIONS,
    READWRITE_ACTIONS,
    MODE_STRICTNESS,
    resolve_effective_mode,
    check_action,
    is_action_allowed,
    set_security_mode,
)
from app.core.exceptions import SecurityError


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


def main() -> None:
    section("READONLY mode blocks all READWRITE actions")
    set_security_mode(SecurityMode.READONLY)
    blocked_count = 0
    for action in READWRITE_ACTIONS:
        try:
            check_action(action)
            # If no exception — action was allowed, FAIL
            check(f"action={action!r} blocked in readonly", False,
                  detail="check_action() did not raise")
        except SecurityError as e:
            blocked_count += 1
            # Use check() (not bare assert) so a bad message doesn't abort the run.
            err = str(e)
            check(f"SecurityError mentions {action!r} or 'режим'",
                  action in err or "режим" in err.lower(),
                  detail=err[:80])
    check(f"all {len(READWRITE_ACTIONS)} write actions blocked in readonly",
          blocked_count == len(READWRITE_ACTIONS),
          detail=f"blocked {blocked_count}/{len(READWRITE_ACTIONS)}")

    section("READONLY mode allows READONLY actions")
    allowed_count = 0
    for action in READONLY_ACTIONS:
        try:
            check_action(action)
            allowed_count += 1
        except SecurityError:
            check(f"readonly action {action!r} should be allowed", False)
    check(f"all {len(READONLY_ACTIONS)} read actions allowed in readonly",
          allowed_count == len(READONLY_ACTIONS),
          detail=f"allowed {allowed_count}/{len(READONLY_ACTIONS)}")

    section("READWRITE mode allows everything")
    set_security_mode(SecurityMode.READWRITE)
    rw_blocked = 0
    for action in (READONLY_ACTIONS | READWRITE_ACTIONS):
        try:
            check_action(action)
        except SecurityError:
            rw_blocked += 1
    check("readwrite mode blocks nothing", rw_blocked == 0,
          detail=f"unexpectedly blocked {rw_blocked}")

    section("DEMO mode allows reads, blocks writes")
    set_security_mode(SecurityMode.DEMO)
    demo_blocks_writes = all(
        not is_action_allowed(a, SecurityMode.DEMO) for a in READWRITE_ACTIONS
    )
    demo_allows_reads = all(
        is_action_allowed(a, SecurityMode.DEMO) for a in READONLY_ACTIONS
    )
    check("DEMO blocks all writes", demo_blocks_writes)
    check("DEMO allows all reads", demo_allows_reads)

    section("Mode strictness ordering — readonly is strictest")
    # readonly > demo > readwrite — verifies that --security-ceiling readonly
    # always overrides any CLI flag at runtime. Imports the real resolver
    # from app.core.security so a regression in server.py's mode-resolution
    # would trip this matrix.
    check("MODE_STRICTNESS ranks readonly > demo > readwrite",
          MODE_STRICTNESS["readonly"] > MODE_STRICTNESS["demo"] > MODE_STRICTNESS["readwrite"],
          detail=str(MODE_STRICTNESS))
    matrix = [
        # (cli_mode, ceiling, expected_final)
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
    for cli, ceil, expected in matrix:
        final = resolve_effective_mode(cli, ceil)
        check(f"CLI={cli}, ceiling={ceil} → {expected}", final == expected,
              detail=f"got {final}")

    section("set_security_mode accepts both enum and str")
    set_security_mode(SecurityMode.READONLY)
    set_security_mode("readonly")
    set_security_mode("readwrite")
    set_security_mode("demo")
    check("set_security_mode accepts string aliases", True)

    set_security_mode(SecurityMode.READWRITE)  # restore default

    print(f"\n===\nResult: {ok} OK, {fail} FAIL")
    sys.exit(0 if fail == 0 else 1)


if __name__ == "__main__":
    main()
