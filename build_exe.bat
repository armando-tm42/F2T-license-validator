@echo off
title Compilador de F2T Administrador de licencias
echo ========================================================
echo   Compilando F2T Administrador de licencias a EXE
echo ========================================================
echo.

:: 1. Detectar entorno de Windows (.venv-win o Python del sistema)
:: Nota: No usamos .venv porque contiene los binarios de Linux/WSL
set PYTHON_CMD=
set PYINSTALLER_CMD=

if exist .venv-win\Scripts\python.exe (
    echo [INFO] Detectado entorno virtual de Windows: .venv-win
    set PYTHON_CMD=.venv-win\Scripts\python.exe
    set PYINSTALLER_CMD=.venv-win\Scripts\pyinstaller.exe
) else (
    python --version >nul 2>&1
    if %errorlevel% equ 0 (
        echo [INFO] Usando Python del sistema en Windows.
        set PYTHON_CMD=python
        set PYINSTALLER_CMD=pyinstaller
    ) else (
        echo [ERROR] No se encontro Python ni .venv-win en Windows.
        echo Por favor instala Python para Windows o instala uv:
        echo   powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
        echo   uv venv .venv-win
        pause
        exit /b 1
    )
)

:: 2. Verificar dependencias necesarias del proyecto y PyInstaller
echo [1/4] Verificando dependencias en Windows (incluyendo Pillow y PyInstaller)...
%PYTHON_CMD% -c "import PyQt6, sqlalchemy, cryptography, bcrypt, dotenv, infisical_sdk, psycopg2, alembic, PyInstaller, PIL" >nul 2>&1
if %errorlevel% neq 0 (
    echo [INFO] Instalando dependencias necesarias en Windows...
    where uv >nul 2>&1
    if %errorlevel% equ 0 (
        if exist .venv-win (
            echo Usando uv con .venv-win...
            uv pip install -e . --python .venv-win
            uv pip install pyinstaller pillow --python .venv-win
        ) else (
            echo Usando uv en Windows...
            uv pip install --system -e .
            uv pip install --system pyinstaller pillow
        )
    ) else (
        echo Usando pip en Windows...
        %PYTHON_CMD% -m pip install --upgrade pip
        %PYTHON_CMD% -m pip install -e .
        %PYTHON_CMD% -m pip install pyinstaller pillow
    )
)

:: 3. Asegurar que el icono sea un archivo ICO genuino de Windows multi-resolucion
echo [2/4] Verificando y normalizando formato de icono de Windows...
%PYTHON_CMD% -c "from PIL import Image; p='src/license_validator/gui/assets/app_icon.ico'; img=Image.open(p); img.save(p, format='ICO', sizes=[(16,16),(24,24),(32,32),(48,48),(64,64),(128,128),(256,256)])" >nul 2>&1

:: 4. Limpiar compilaciones anteriores
echo [3/4] Limpiando carpetas previas...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

:: 5. Compilar con PyInstaller usando la especificacion optimizada
echo [4/4] Empaquetando aplicacion con icono y recursos visuales...
if exist .venv-win\Scripts\pyinstaller.exe (
    .venv-win\Scripts\pyinstaller.exe --clean f2t_licencias.spec
) else (
    %PYTHON_CMD% -m PyInstaller --clean f2t_licencias.spec
)

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Ocurrio un error durante la compilacion.
    pause
    exit /b 1
)

:: 5. Copiar archivo .env y clave publica a la carpeta final
if exist .env (
    copy /y .env dist\F2T-Licencias\.env >nul
) else (
    copy /y .env.example dist\F2T-Licencias\.env >nul
)
if exist public.pem (
    copy /y public.pem dist\F2T-Licencias\public.pem >nul
)

:: 6. Validar integridad del ejecutable generado
for %%I in ("dist\F2T-Licencias\F2T-Licencias.exe") do set EXE_SIZE=%%~zI
if %EXE_SIZE% lss 1000000 (
    echo [ERROR] El ejecutable en dist\F2T-Licencias\F2T-Licencias.exe parece incompleto (%EXE_SIZE% bytes).
    pause
    exit /b 1
)

echo.
echo ========================================================
echo  [EXITO] Compilacion completada satisfactoriamente!
echo ========================================================
echo.
echo La aplicacion empaquetada esta lista en:
echo   dist\F2T-Licencias\F2T-Licencias.exe
echo.
echo Puedes probarla ejecutando ese archivo directamente.
echo Para generar el instalador final de Windows (Setup.exe),
echo compila el archivo 'installer_inno.iss' con Inno Setup.
echo.
pause
