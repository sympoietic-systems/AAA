@echo off
setlocal enabledelayedexpansion

echo =============================================================
echo   AAA - First-Time Local Setup (Windows)
echo =============================================================
echo.

:: 1. Check/Install uv
echo [1/5] Checking uv package manager ...
where uv >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo uv not found. Installing uv ...
    powershell -ExecutionPolicy Bypass -Command "irm https://astral.sh/uv/install.ps1 | iex"
    :: Add uv to current session PATH
    set "PATH=%USERPROFILE%\.local\bin;%PATH%"
    where uv >nul 2>&1
    if %ERRORLEVEL% neq 0 (
        echo [FAIL] uv installation failed. Install manually: https://docs.astral.sh/uv/
        exit /b 1
    )
    echo [OK] uv installed.
) else (
    echo [OK] uv already installed.
)
echo.

:: 2. Check/Install Python via uv
echo [2/5] Checking Python runtime (managed by uv) ...
:: uv will automatically fetch the correct python version based on .python-version or pyproject.toml
uv run python --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo uv is downloading/installing the required Python runtime...
    uv python install
)
for /f "tokens=2" %%v in ('uv run python --version 2^>^&1') do set PY_VER=%%v
echo Found Python !PY_VER! (managed by uv)
echo [OK] Python runtime is ready.
echo.

:: 3. Install Python dependencies
echo [3/5] Installing Python dependencies (uv sync) ...
uv sync
if %ERRORLEVEL% neq 0 (
    echo [FAIL] uv sync failed.
    exit /b 1
)
echo [OK] Python dependencies installed.
echo.

:: 4. Check/Install Node.js & frontend dependencies
echo [4/5] Checking frontend dependencies ...
where node >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [FAIL] Node.js not found. Please install Node.js LTS from nodejs.org
    exit /b 1
)
where npm >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [FAIL] npm not found. Please install Node.js LTS from nodejs.org
    exit /b 1
)

echo Installing frontend packages (npm install) ...
cd frontend
call npm install
cd ..
echo [OK] Frontend setup complete.
echo.

:: 5. Create directories & .env check
echo [5/5] Preparing runtime directories ...
if not exist "backend\data\backups" mkdir "backend\data\backups"
if not exist "backend\data\uploads\research" mkdir "backend\data\uploads\research"
echo [OK] data directories created.

if not exist ".env" (
    if exist ".env.example" (
        echo [!] No .env file found. Copying from .env.example ...
        copy .env.example .env
        echo [!] Please edit the .env file with your API keys.
    ) else (
        echo [!] No .env or .env.example found. Create .env manually with API keys.
    )
) else (
    echo [OK] .env file exists.
)
echo.

echo =============================================================
echo   Setup complete!
echo =============================================================
echo.
echo   Start backend:   scripts\run_backend.bat
echo   Start frontend:  scripts\run_frontend.bat
echo   Start all:       scripts\run_all.bat
echo.
echo   Backend API:     http://127.0.0.1:8499
echo   Frontend:        http://localhost:5173
echo =============================================================
pause
