#!/usr/bin/env python3
"""
Cross-platform build script for ModusBI MCP Server.

Produces a single-file binary in a versioned, per-OS folder:
    dist/<version>/<os>-<arch>/modusbi-mcp-server[.exe]
plus a <binary>.sha256 checksum next to it.

<version> is read from app/__init__.py (__version__) — the single source of
truth. Binaries are git-ignored and distributed via GitHub Releases (tag
v<version>); PyInstaller cannot cross-compile, so each OS/arch is built on
its own platform (or a matching CI runner).

Usage (from build/ directory):
    python build.py              # Build for current platform
    python build.py --clean      # Clean build artifacts before building
    python build.py --check      # Only check dependencies, don't build
"""

import argparse
import hashlib
import platform
import re
import shutil
import subprocess
import sys
from pathlib import Path


# build/ directory (where this script lives)
DEPLOY_DIR = Path(__file__).parent.resolve()
# repo root (one level up from build/)
REPO_ROOT = DEPLOY_DIR.parent
# app/ package root
APP_ROOT = REPO_ROOT / "app"

DIST_DIR = DEPLOY_DIR / "dist"
BUILD_DIR = DEPLOY_DIR / "build"
VENV_DIR = DEPLOY_DIR / ".venv-build"

BINARY_BASENAME = "modusbi-mcp-server"


def read_version() -> str:
    """Read __version__ from app/__init__.py (single source of truth)."""
    init = (APP_ROOT / "__init__.py").read_text(encoding="utf-8")
    m = re.search(r'__version__\s*=\s*["\']([^"\']+)["\']', init)
    if not m:
        print("ERROR: __version__ not found in app/__init__.py")
        sys.exit(1)
    return m.group(1)


def platform_tag() -> str:
    """Return '<os>-<arch>', e.g. linux-x86_64, windows-x86_64, darwin-arm64."""
    os_map = {"Linux": "linux", "Windows": "windows", "Darwin": "darwin"}
    os_name = os_map.get(platform.system(), platform.system().lower())
    arch = platform.machine().lower()
    arch = {"amd64": "x86_64", "x86_64": "x86_64",
            "aarch64": "arm64", "arm64": "arm64"}.get(arch, arch)
    return f"{os_name}-{arch}"


def binary_name() -> str:
    return BINARY_BASENAME + (".exe" if platform.system() == "Windows" else "")


def run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
    """Run a command and print it."""
    print(f"  > {' '.join(cmd)}")
    return subprocess.run(cmd, check=True, **kwargs)


def get_python() -> str:
    """Get the path to the Python executable in the build venv."""
    if platform.system() == "Windows":
        return str(VENV_DIR / "Scripts" / "python.exe")
    return str(VENV_DIR / "bin" / "python")


def check_python_version():
    """Ensure Python 3.10+ is available."""
    major, minor = sys.version_info[:2]
    if major < 3 or minor < 10:
        print(f"ERROR: Python 3.10+ required, found {major}.{minor}")
        sys.exit(1)
    print(f"  Python {major}.{minor}.{sys.version_info.micro}")


def create_venv():
    """Create a build virtual environment."""
    if VENV_DIR.exists():
        print("  Build venv already exists, reusing...")
        return
    print("  Creating build virtual environment...")
    run([sys.executable, "-m", "venv", str(VENV_DIR)])


def install_deps():
    """Install all dependencies into the build venv."""
    # Use `python -m pip` (not the pip executable): on Windows pip cannot
    # upgrade itself while running as pip.exe — the running executable is
    # locked, and pip errors out ("To modify pip, please run ... -m pip").
    python = get_python()
    run([python, "-m", "pip", "install", "--quiet", "--upgrade", "pip"])
    run([python, "-m", "pip", "install", "--quiet", "-r", str(REPO_ROOT / "requirements.txt")])
    run([python, "-m", "pip", "install", "--quiet", "-r", str(DEPLOY_DIR / "requirements-build.txt")])


def sha256_file(path: Path) -> str:
    """Compute the SHA-256 hex digest of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def build_binary() -> Path:
    """Run PyInstaller to create the binary in a versioned, per-OS folder."""
    python = get_python()
    spec_file = str(DEPLOY_DIR / "modusbi_mcp.spec")

    version = read_version()
    out_dir = DIST_DIR / version / platform_tag()

    run([python, "-m", "PyInstaller", "--clean", "--noconfirm",
         "--distpath", str(out_dir),
         "--workpath", str(BUILD_DIR),
         spec_file])

    binary_path = out_dir / binary_name()
    if not binary_path.exists():
        print(f"\nERROR: Expected binary not found at {binary_path}")
        sys.exit(1)

    if platform.system() != "Windows":
        binary_path.chmod(0o755)

    # Write a checksum next to the binary for download verification.
    digest = sha256_file(binary_path)
    checksum_path = binary_path.with_name(binary_path.name + ".sha256")
    checksum_path.write_text(f"{digest}  {binary_path.name}\n", encoding="utf-8")

    size_mb = binary_path.stat().st_size / (1024 * 1024)
    print(f"\n  Version: {version}")
    print(f"  Binary:  {binary_path}")
    print(f"  SHA256:  {digest}")
    print(f"  Size:    {size_mb:.1f} MB")
    print(f"  OS:      {platform.system()} {platform.machine()}")

    return binary_path


def clean():
    """Remove build artifacts."""
    for d in [BUILD_DIR, DIST_DIR]:
        if d.exists():
            print(f"  Removing {d}...")
            shutil.rmtree(d)
    print("  Clean complete.")


def main():
    parser = argparse.ArgumentParser(description="Build ModusBI MCP Server binary")
    parser.add_argument("--clean", action="store_true", help="Clean artifacts before building")
    parser.add_argument("--check", action="store_true", help="Only check dependencies")
    args = parser.parse_args()

    system = platform.system()
    print("=" * 50)
    print(f"  ModusBI MCP Server {read_version()} — {system} Build")
    print("=" * 50)

    print("\n[1/4] Checking Python...")
    check_python_version()

    if args.clean:
        print("\n[*] Cleaning previous build artifacts...")
        clean()

    if args.check:
        print("\n[2/4] Creating venv...")
        create_venv()
        print("\n[3/4] Checking dependencies...")
        install_deps()
        print("\n  All dependencies OK.")
        return

    print("\n[2/4] Creating build environment...")
    create_venv()

    print("\n[3/4] Installing dependencies...")
    install_deps()

    print("\n[4/4] Building binary...")
    binary_path = build_binary()

    # Cleanup build dir (keep dist)
    if BUILD_DIR.exists():
        shutil.rmtree(BUILD_DIR)

    print("\n" + "=" * 50)
    print("  BUILD SUCCESSFUL")
    print("=" * 50)
    print(f"\n  Test: {binary_path} --help")
    print(f"  Run:  {binary_path} --transport stdio\n")


if __name__ == "__main__":
    main()
