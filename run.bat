@echo off
title ROADVISION AI - Intelligent Road Infrastructure Platform
color 0B

echo ======================================================================
echo   ROADVISION AI - Intelligent Road Damage Intelligence Platform
echo   "Detect Road Damage. Predict Risk. Prioritize Smarter Repairs."
echo ======================================================================
echo.

:: Step 1: Check Python installation
echo [1/5] Checking Python environment...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in system PATH.
    echo Please install Python 3.10+ and add it to your PATH.
    pause
    exit /b 1
)
python --version

:: Step 2: Install / verify dependencies
echo.
echo [2/5] Verifying dependencies...
pip install -r requirements.txt --quiet

:: Step 3: Check / download model weights
echo.
echo [3/5] Verifying AI model weights...
if not exist "models\primary\roadvision_rdd2022_yolov8m.pt" (
    echo Downloading primary RDD2022 model weights...
    python scripts\download_model.py
) else (
    echo Primary model weights verified in models\primary\
)

:: Step 4: Seed demo data if database does not exist
echo.
echo [4/5] Initializing database and demo records...
if not exist "data\roadvision.db" (
    python scripts\seed_demo_data.py
)

:: Step 5: Start the application
echo.
echo [5/5] Launching ROADVISION AI platform...
echo.
echo ======================================================================
echo   Application Running Locally:
echo   - Web Dashboard: http://127.0.0.1:8000/
echo   - Interactive API: http://127.0.0.1:8000/docs
echo ======================================================================
echo.

python run_server.py
pause
