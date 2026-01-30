@echo off
REM Setup Windows Task Scheduler for Daily Data Update
REM Run this script as Administrator

echo ============================================
echo  Sector Rotation System - Scheduler Setup
echo ============================================
echo.

REM Get the script directory
set SCRIPT_DIR=%~dp0
set PROJECT_DIR=%SCRIPT_DIR%..

REM Check for admin privileges
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: This script requires Administrator privileges.
    echo Please right-click and select "Run as administrator"
    pause
    exit /b 1
)

echo Project directory: %PROJECT_DIR%
echo.

REM Create the scheduled task
echo Creating scheduled task "SectorRotation_DailyUpdate"...
echo This will run daily at 6:00 PM (after market close)
echo.

schtasks /create /tn "SectorRotation_DailyUpdate" ^
    /tr "python \"%PROJECT_DIR%\scripts\daily_update.py\"" ^
    /sc daily ^
    /st 18:00 ^
    /f ^
    /rl highest

if %errorlevel% equ 0 (
    echo.
    echo SUCCESS: Task created successfully!
    echo.
    echo The daily update will run at 6:00 PM every day.
    echo.
    schtasks /query /tn "SectorRotation_DailyUpdate" /v /fo list
) else (
    echo.
    echo ERROR: Failed to create scheduled task.
    echo Please check the error message above.
)

echo.
echo ============================================
echo  To manually run the update now:
echo  python scripts\daily_update.py
echo ============================================
echo.

pause
