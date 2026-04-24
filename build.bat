@echo off
echo ========================================================
echo    Smart File Organizer AI - Automated Builder
echo ========================================================
echo.

echo [1/4] Cleaning previous builds...
if exist "dist" rmdir /s /q "dist"
if exist "build" rmdir /s /q "build"
if exist "frontend\dist" rmdir /s /q "frontend\dist"
if exist "frontend\dist-electron" rmdir /s /q "frontend\dist-electron"

echo.
echo [2/4] Packaging Python Backend (PyInstaller)...
call .venv\Scripts\activate.bat
pyinstaller --onefile --noconsole --name smart_organizer --hidden-import="uvicorn.logging" --hidden-import="uvicorn.loops" --hidden-import="uvicorn.loops.auto" --hidden-import="uvicorn.protocols" --hidden-import="uvicorn.protocols.http" --hidden-import="uvicorn.protocols.http.auto" --hidden-import="uvicorn.protocols.websockets" --hidden-import="uvicorn.protocols.websockets.auto" --hidden-import="uvicorn.lifespan" --hidden-import="uvicorn.lifespan.on" backend/main.py

if %ERRORLEVEL% neq 0 (
    echo.
    echo [ERROR] Backend build failed!
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo [3/4] Building Frontend and Packaging Desktop App (Electron Builder)...
cd frontend
call npm run build

if %ERRORLEVEL% neq 0 (
    echo.
    echo [ERROR] Electron Builder failed!
    cd ..
    pause
    exit /b %ERRORLEVEL%
)

cd ..
echo.
echo ========================================================
echo    Build Completed Successfully!
echo    Your installer is ready inside:
echo    E:\Project\smart-file-organizer\frontend\dist-electron
echo ========================================================
echo.
pause
