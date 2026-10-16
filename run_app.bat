@echo off
title F2T Administrador de licencias
echo ========================================================
echo       Iniciando F2T Administrador de licencias
echo ========================================================
echo.

:: Detectar entorno virtual de Windows (.venv-win) o Python de Windows
set PYTHON_CMD=

if exist .venv-win\Scripts\python.exe (
    echo [INFO] Usando entorno virtual de Windows: .venv-win
    set PYTHON_CMD=.venv-win\Scripts\python.exe
) else (
    python --version >nul 2>&1
    if %errorlevel% equ 0 (
        set PYTHON_CMD=python
    ) else (
        echo [ERROR] Python no esta instalado o no se encuentra en el PATH de Windows.
        echo Por favor instala Python o crea el entorno con: uv venv .venv-win
        pause
        exit /b 1
    )
)

:: Verificar e instalar dependencias si faltan
echo Comprobando dependencias en Windows...
%PYTHON_CMD% -c "import PyQt6, sqlalchemy, cryptography, bcrypt, dotenv, infisical_sdk, psycopg2, alembic, PIL" >nul 2>&1
if %errorlevel% neq 0 (
    echo Instalando dependencias necesarias en Windows...
    where uv >nul 2>&1
    if %errorlevel% equ 0 (
        if exist .venv-win (
            uv pip install -e . --python .venv-win
        ) else (
            uv pip install --system -e .
        )
    ) else (
        %PYTHON_CMD% -m pip install -e .
    )
)

:: Ejecutar la aplicacion
echo Iniciando interfaz grafica...
%PYTHON_CMD% src\license_validator\main.py
if %errorlevel% neq 0 (
    echo.
    echo [AVISO] La aplicacion se cerro con codigo de error %errorlevel%.
    pause
)
