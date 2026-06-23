@echo off
REM Build ModusBI MCP Server — Windows binary.
REM Thin wrapper around build.py (single source of build logic + versioned layout:
REM dist\<version>\<os>-<arch>\modusbi-mcp-server.exe + .sha256).
cd /d "%~dp0"
python build.py %*
