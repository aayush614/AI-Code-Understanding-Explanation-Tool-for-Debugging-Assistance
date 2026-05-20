@echo off
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo ERROR: Could not find .venv\Scripts\python.exe
    echo Current folder: %cd%
    echo.
    echo Open a terminal in this folder and create/activate your virtual environment first.
    pause
    exit /b 1
)

echo Starting AI_code_understanding.py with Streamlit...
echo.
echo When Streamlit finishes starting, open this URL:
echo http://127.0.0.1:8510
echo.
echo Keep this window open while using the app.
echo.

start "" cmd /c "timeout /t 8 > nul && start http://127.0.0.1:8510"
".venv\Scripts\python.exe" -m streamlit run AI_code_understanding.py --server.port 8510 --server.address 127.0.0.1 --server.headless true

echo.
echo Streamlit stopped or failed to start.
pause
