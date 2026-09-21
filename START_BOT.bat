@echo off
chcp 65001 >nul
cd /d "%~dp0"
title IUH LMS BLOG BOT

echo ==========================================
echo   IUH LMS BLOG BOT
echo ==========================================
echo.

set "VENV=%~dp0.venv"
set "VPY=%VENV%\Scripts\python.exe"

REM ==================================================
REM 1. Kiem tra .venv hien tai
REM ==================================================
if exist "%VPY%" (
    "%VPY%" -c "import sys; print(sys.version)" >nul 2>&1
    if not errorlevel 1 (
        echo [OK] Da tim thay .venv hop le:
        echo      %VENV%
        goto VENV_READY
    )

    echo [WARN] .venv ton tai nhung bi loi. Dang xoa de tao lai...
    rmdir /s /q "%VENV%"
)

REM ==================================================
REM 2. Tu dong tim Python va tao .venv
REM    Uu tien py launcher de tranh Microsoft Store alias
REM ==================================================
echo [SETUP] Chua co .venv hop le. Dang tim Python...

REM --- Thu py -3 ---
where py >nul 2>&1
if not errorlevel 1 (
    py -3 -c "import sys; print(sys.executable)" >nul 2>&1
    if not errorlevel 1 (
        echo [SETUP] Thu tao .venv bang: py -3
        py -3 -m venv "%VENV%"
        if exist "%VPY%" goto VENV_CREATED
        if exist "%VENV%" rmdir /s /q "%VENV%"
    )
)

REM --- Thu python ---
where python >nul 2>&1
if not errorlevel 1 (
    python -c "import sys; print(sys.executable)" >nul 2>&1
    if not errorlevel 1 (
        echo [SETUP] Thu tao .venv bang: python
        python -m venv "%VENV%"
        if exist "%VPY%" goto VENV_CREATED
        if exist "%VENV%" rmdir /s /q "%VENV%"
    )
)

REM --- Thu python3 ---
where python3 >nul 2>&1
if not errorlevel 1 (
    python3 -c "import sys; print(sys.executable)" >nul 2>&1
    if not errorlevel 1 (
        echo [SETUP] Thu tao .venv bang: python3
        python3 -m venv "%VENV%"
        if exist "%VPY%" goto VENV_CREATED
        if exist "%VENV%" rmdir /s /q "%VENV%"
    )
)

echo.
echo [ERROR] Khong tao duoc Python virtual environment.
echo.
echo Nguyen nhan thuong gap:
echo - Python chua duoc cai dung cach.
echo - Lenh python dang tro vao Microsoft Store alias.
echo - Ban Python bi thieu module venv/ensurepip.
echo.
echo Hay thu cac lenh sau trong CMD:
echo   py -3 --version
echo   python --version
echo   where python
echo   py -0p
echo.
pause
exit /b 1

:VENV_CREATED
echo [OK] Da tao xong .venv.

:VENV_READY
echo.
echo [OK] Python trong .venv:
"%VPY%" --version
if errorlevel 1 (
    echo [ERROR] Python trong .venv khong chay duoc.
    pause
    exit /b 1
)

REM ==================================================
REM 3. Dam bao pip san sang trong .venv
REM ==================================================
"%VPY%" -m pip --version >nul 2>&1
if errorlevel 1 (
    echo [SETUP] Dang khoi phuc pip trong .venv...
    "%VPY%" -m ensurepip --upgrade
    if errorlevel 1 (
        echo [ERROR] Khong khoi phuc duoc pip.
        pause
        exit /b 1
    )
)

REM ==================================================
REM 4. Kiem tra dependency
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

REM ==================================================
REM 5. Chay bot
REM ==================================================
echo.
echo ==========================================
echo [START] Khoi dong bot...
echo ==========================================
echo.

"%VPY%" lms_blog_bot.py

echo.
echo Bot da dung.
pause
