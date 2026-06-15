@echo off
setlocal

chcp 65001 >nul
cd /d "%~dp0"

echo [Travel Assistant] Starting local services...
echo.

where docker >nul 2>nul
if errorlevel 1 (
    echo [WARN] Docker was not found. Milvus will not be started.
) else (
    echo [1/3] Starting Milvus with Docker Compose...
    docker compose -f docker-compose.milvus.yml up -d
    if errorlevel 1 (
        echo [WARN] Failed to start Milvus. Check Docker Desktop and docker-compose.milvus.yml.
    )
)

echo.
echo [2/3] Opening backend window...
if "%DASHSCOPE_API_KEY%"=="" (
    echo [WARN] DASHSCOPE_API_KEY is not set in system environment. Knowledge base embedding calls will fail.
)
where uv >nul 2>nul
if errorlevel 1 (
    echo [WARN] uv was not found in PATH. Backend window will show install guidance.
    start "Travel Assistant Backend" cmd /k "cd /d ""%~dp0"" && echo uv is required. Install uv first: https://docs.astral.sh/uv/getting-started/installation/ && echo. && pause"
) else (
    start "Travel Assistant Backend" cmd /k "cd /d ""%~dp0"" && uv sync && uv run uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000"
)

echo [3/3] Opening frontend window...
where npm >nul 2>nul
if errorlevel 1 (
    echo [WARN] npm was not found in PATH. Frontend window will show install guidance.
    start "Travel Assistant Frontend" cmd /k "cd /d ""%~dp0frontend"" && echo npm is required. Install Node.js first: https://nodejs.org/ && echo. && pause"
) else (
    start "Travel Assistant Frontend" cmd /k "cd /d ""%~dp0frontend"" && if not exist node_modules npm install && npm run dev"
)

echo.
echo Services are starting in separate windows.
echo Frontend: http://localhost:5173
echo Backend:  http://localhost:8000
echo Milvus:   http://localhost:19530
echo.
echo If this is the first knowledge-base run, sign in and call POST /api/knowledge/seed after backend starts.
timeout /t 3 /nobreak >nul

endlocal
