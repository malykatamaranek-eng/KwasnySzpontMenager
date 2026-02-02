@echo off
REM Setup script for KWASNY LOG MANAGER (Windows)

echo ============================================
echo KWASNY LOG MANAGER - Setup
echo ============================================

REM Check Python version
echo.
echo Checking Python version...
python --version

REM Create virtual environment
echo.
echo Creating virtual environment...
python -m venv venv
echo Virtual environment created
echo To activate: venv\Scripts\activate

REM Install dependencies
echo.
echo Installing dependencies...
pip install -r requirements.txt

REM Install Playwright browsers
echo.
echo Installing Playwright browsers...
playwright install chromium

REM Create necessary directories
echo.
echo Creating directories...
if not exist data mkdir data
if not exist logs mkdir logs
if not exist reports mkdir reports

REM Check for config files
echo.
echo Checking configuration files...
if not exist config\proxies.txt (
    echo   WARNING: config\proxies.txt not found
    echo            Copy config\proxies.txt.example and add your proxies
)

if not exist config\accounts.txt (
    echo   WARNING: config\accounts.txt not found
    echo            Copy config\accounts.txt.example and add your accounts
)

echo.
echo Setup complete!
echo.
echo Next steps:
echo 1. Copy and configure config files:
echo    copy config\proxies.txt.example config\proxies.txt
echo    copy config\accounts.txt.example config\accounts.txt
echo 2. Edit the config files with your data
echo 3. Run the application:
echo    python -m src.gui.admin_panel  (GUI)
echo    python -m src.main             (CLI)

pause
