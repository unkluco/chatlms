@echo off
chcp 65001 >nul
cd /d "%~dp0"
title IUH LMS BLOG BOT

echo ==========================================
echo   IUH LMS BLOG BOT - TEST
echo ==========================================
echo.

set "VENV=%~dp0.venv"
set "VPY=%VENV%\Scripts\python.exe"

REM ==================================================
REM 1. Kiem tra virtual environment
REM ==================================================
if exist "%VPY%" (
    echo [OK] Da tim thay moi truong Python rieng:
    echo      %VENV%
) else (
    echo [SETUP] Chua co .venv - dang tao moi truong rieng...

    where python >nul 2>&1
    if not errorlevel 1 (
        python -m venv "%VENV%"
    ) else (
        where py >nul 2>&1
        if errorlevel 1 (
            echo [ERROR] Khong tim thay Python hoac py launcher.
            pause
            exit /b 1
        )
        py -m venv "%VENV%"
    )

    if not exist "%VPY%" (
        echo [ERROR] Tao .venv that bai.
        pause
        exit /b 1
    )

    echo [OK] Da tao xong .venv.
)

REM ==================================================
REM 2. Kiem tra Python trong .venv
REM ==================================================
"%VPY%" --version
if errorlevel 1 (
    echo [WARN] .venv bi loi. Dang tao lai...
    rmdir /s /q "%VENV%"

    where python >nul 2>&1
    if not errorlevel 1 (
        python -m venv "%VENV%"
    ) else (
        py -m venv "%VENV%"
    )

    if not exist "%VPY%" (
        echo [ERROR] Khong tao lai duoc .venv.
        pause
        exit /b 1
    )
)

REM ==================================================
REM 3. Kiem tra dependency
REM ==================================================
"%VPY%" -c "import playwright" >nul 2>&1
if errorlevel 1 (
    echo [SETUP] Chua co Playwright trong .venv.
    echo [SETUP] Dang cai Playwright CHI vao .venv...
    "%VPY%" -m pip install --upgrade pip
    "%VPY%" -m pip install playwright

    if errorlevel 1 (
        echo [ERROR] Cai Playwright that bai.
        pause
        exit /b 1
    )
) else (
    echo [OK] Playwright da co san trong .venv.
)

"%VPY%" -c "import groq" >nul 2>&1
if errorlevel 1 (
    echo [SETUP] Chua co Groq SDK trong .venv.
    echo [SETUP] Dang cai Groq SDK CHI vao .venv...
    "%VPY%" -m pip install groq

    if errorlevel 1 (
        echo [ERROR] Cai Groq SDK that bai.
        pause
        exit /b 1
    )
) else (
    echo [OK] Groq SDK da co san trong .venv.
)

echo.
echo ==========================================
echo [START] Khoi dong bot...
echo ==========================================
echo.

"%VPY%" lms_blog_bot.py

echo.
echo Bot da dung.
pause
