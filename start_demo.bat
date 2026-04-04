@echo off
echo =========================================================
echo 🌍 AIRAVAT 3.0: ENVIRONMENTAL SENTINEL DEMO BOOTSTRAPPER
echo =========================================================
echo.
echo [1/2] Spinning up FastAPI Machine Learning Backend...
start cmd /k "title FastAPI Backend (Logs) && echo Backend logs will appear here during simulation. && python -m uvicorn main:app --reload --port 8000"

echo Waiting 5 seconds for AI agents to load into memory...
timeout /t 5 /nobreak >nul

echo [2/2] Launching Streamlit Mission Control Dashboard...
start cmd /k "title Streamlit Frontend && python -m streamlit run simulation_app.py"

echo.
echo ✅ ALL SYSTEMS GO!
echo The dashboard will open in your browser automatically.
echo Watch the 'FastAPI Backend' window when you click 'INJECT ANOMALY'.
