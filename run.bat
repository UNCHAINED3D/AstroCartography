@echo off
REM ---------------------------------------------------------------------------
REM One-click launcher for the Astrocartography app.
REM
REM Builds the frontend into a static bundle and serves BOTH the API and the
REM UI from the FastAPI backend (port 8000). The Vite dev server is no longer
REM needed for normal use, which avoids serving the unminified bundle and gives
REM proper gzip + cache headers via GZipMiddleware.
REM
REM Requirements (run once if missing):
REM   backend:  python -m pip install -r backend\requirements.txt
REM   frontend: cd frontend && npm install
REM ---------------------------------------------------------------------------

setlocal
set "ROOT=%~dp0"
set "BACKEND=%ROOT%backend"
set "FRONTEND=%ROOT%frontend"

echo Building frontend (production bundle)...
pushd "%FRONTEND%"
call npm run build
if errorlevel 1 (
  echo Frontend build failed — serving from an existing dist/ if present.
)
popd

echo Starting Astrocartography backend + UI on http://localhost:8000
start "Astrocartography" cmd /k "cd /d "%BACKEND%" && python run.py"

echo.
echo Server launching. Open http://localhost:8000 when ready.
echo (The globe's /api calls are served from the same origin.)
endlocal
