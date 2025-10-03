@echo off
echo ===============================================
echo    Django Scholarship Portal - Quick Start
echo ===============================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.9+ from https://python.org
    pause
    exit /b 1
)

echo [1/8] Python version check...
python --version

REM Check if virtual environment exists
if not exist "venv" (
    echo [2/8] Creating virtual environment...
    python -m venv venv
) else (
    echo [2/8] Virtual environment already exists
)

echo [3/8] Activating virtual environment...
call venv\Scripts\activate.bat

echo [4/8] Upgrading pip...
python -m pip install --upgrade pip

echo [5/8] Installing dependencies...
pip install -r requirements.txt

REM Check if .env exists
if not exist ".env" (
    echo [6/8] Creating environment file...
    copy .env.example .env
    echo.
    echo IMPORTANT: Please edit .env file with your database credentials
    echo Default database settings:
    echo   - Database: scholarship_portal_db
    echo   - User: root
    echo   - Password: (set your MySQL password)
    echo.
) else (
    echo [6/8] Environment file already exists
)

echo [7/8] Running database migrations...
python manage.py migrate

echo [8/8] Creating superuser...
echo Please create an admin user:
python manage.py createsuperuser

echo.
echo ===============================================
echo           Setup Complete!
echo ===============================================
echo.
echo Your Django Scholarship Portal is ready!
echo.
echo To start the development server:
echo   python manage.py runserver
echo.
echo Then visit: http://127.0.0.1:8000
echo Admin panel: http://127.0.0.1:8000/admin
echo.
echo For background tasks, run in separate terminals:
echo   celery -A scholarship_portal worker -l info
echo   celery -A scholarship_portal beat -l info
echo.
echo ===============================================

pause
