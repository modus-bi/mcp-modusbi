# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for ModusBI MCP Server.

Usage (from build/ directory):
    pyinstaller modusbi_mcp.spec

Builds a single-file executable that includes:
- All Python source code (app/) — промпты инлайн в app/prompts.py

Configuration is read from env vars at runtime (MODUSBI_URL, USERNAME,
PASSWORD) — see INSTALL.md.
"""

import os
import sys
from pathlib import Path

block_cipher = None

# build/ directory (where this spec lives)
DEPLOY_DIR = os.path.dirname(os.path.abspath(SPEC))
# repo root (one level up from build/)
REPO_ROOT = os.path.dirname(DEPLOY_DIR)
# app/ package root
APP_ROOT = os.path.join(REPO_ROOT, 'app')

a = Analysis(
    [os.path.join(DEPLOY_DIR, 'entry_point.py')],
    pathex=[REPO_ROOT],  # repo root so `from app.xxx` imports work
    binaries=[],
    datas=[(os.path.join(APP_ROOT, 'tools', 'tilemap_regions.json'), 'app/tools')],
    hiddenimports=[
        'app',
        'app.server',
        'app.prompts',
        'app.core',
        'app.core.instances',
        'app.core.security',
        'app.core.exceptions',
        'app.tools',
        # Tool modules registered with @mcp.tool()
        'app.tools.report_operations',
        'app.tools.report_template',
        'app.tools.component_operations',  # dispatcher used by 4 split tools
        'app.tools.component_crud',
        'app.tools.component_axes',
        'app.tools.component_filters',
        'app.tools.dataset_operations',
        'app.tools.datasource_operations',
        'app.tools.query_execute',
        'app.tools.style_operations',
        'app.tools.batch_operations',
        'app.tools.export_data',
        'app.tools.security_operations',
        'app.tools.reportgroup_operations',
        # Shared helpers
        'app.tools.action_types',
        'app.tools.builders',
        'app.tools.config_presets',
        'app.tools.config_schema',
        'app.tools.css_schema',
        'app.tools.help_texts',
        'app.tools.layout_helper',
        'app.tools.param_docs',
        'app.tools.schemas',
        'app.tools.text_block_helper',
        # schema slim + deferred meta classification
        'app.tools.profiles',
        'app.tools.schema_slim',
        # Third-party
        'mcp',
        'mcp.server',
        'mcp.server.fastmcp',
        'httpx',
        'pydantic',
        'anyio',
        'anyio._backends',
        'anyio._backends._asyncio',
        'starlette',
        'starlette.applications',
        'starlette.routing',
        'uvicorn',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'matplotlib',
        'numpy',
        'pandas',
        'scipy',
        'PIL',
        'cv2',
        'torch',
        'tensorflow',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='modusbi-mcp-server',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
