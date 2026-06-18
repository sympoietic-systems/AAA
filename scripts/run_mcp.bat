@echo off
cd /d "%~dp0.."
REM Point to online instance — override for local dev:
REM set AAA_API_BASE=http://localhost:8499/api
set AAA_API_BASE=http://aaa.sokaris.link/api
uv run python backend\mcp_server.py
