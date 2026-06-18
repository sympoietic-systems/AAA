@echo off
title Autopoietic Agentic Assemblage Launcher
cd /d "%~dp0"

echo =========================================================
echo   Starting Autopoietic Agentic Assemblage (AAA) Services
echo =========================================================
echo.

echo [1/3] Starting Backend Server...
start "AAA Backend" cmd /k "call run_backend.bat"

echo [2/3] Starting MCP Server...
start "AAA MCP Server" cmd /k "call run_mcp.bat"

echo [3/3] Starting Frontend Dev Server...
start "AAA Frontend" cmd /k "call run_frontend.bat"

echo.
echo =========================================================
echo   All components launched in separate windows!
echo   - Frontend: http://localhost:5173
echo   - Backend API: http://127.0.0.1:8499
echo.
echo   Keep this launcher open to easily monitor services, or
echo   press any key to exit this launcher window (services
echo   will remain running).
echo =========================================================
pause > nul
