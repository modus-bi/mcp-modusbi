"""Unit tests for mask_sensitive() helper from app/core/exceptions.py.

Run:
    python -m app.tests.test_mask_sensitive
"""
import sys

from app.core.exceptions import mask_sensitive


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
    section("Go runtime patterns")
    out = mask_sensitive("goroutine 12 [running]: at /srv/app/internal/pkg/foo.go:421 +0x1a")
    check("goroutine masked", "goroutine 12" not in out, detail=out)
    check("file path masked", "foo.go" not in out, detail=out)

    out = mask_sensitive("called from /home/user/app/handler.go:99")
    check("plain go path masked", "handler.go" not in out, detail=out)

    section("PostgreSQL patterns")
    out = mask_sensitive('pq: relation "hs_dashboard_xyz" does not exist')
    check("pq: prefix stripped", not out.startswith("pq:"), detail=out)
    check("relation name masked", "hs_dashboard_xyz" not in out, detail=out)

    out = mask_sensitive("constraint fk_user_id_fkey violated")
    check("constraint name masked", "fk_user_id_fkey" not in out, detail=out)

    out = mask_sensitive('Invalid schema "public"')
    check("schema name masked (acceptable false-positive)", "public" not in out, detail=out)

    section("None / empty input")
    check("None passthrough", mask_sensitive(None) is None)
    check("empty string passthrough", mask_sensitive("") == "")

    section("Non-sensitive content preserved")
    out = mask_sensitive("HTTP 404")
    check("plain HTTP errors not masked", out == "HTTP 404", detail=out)

    out = mask_sensitive("Validation failed: missing field 'name'")
    check("validation messages preserved", "missing field" in out, detail=out)

    section("Idempotent — masking twice == once")
    once = mask_sensitive("goroutine 1 [running]: at file.go:42")
    twice = mask_sensitive(once)
    check("idempotent", once == twice, detail=f"once={once!r} twice={twice!r}")

    print(f"\n===\nResult: {ok} OK, {fail} FAIL")
    sys.exit(0 if fail == 0 else 1)


if __name__ == "__main__":
    main()
