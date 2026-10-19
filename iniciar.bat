@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Creando entorno virtual...
    py -3.13 -m venv .venv 2>nul
    if errorlevel 1 py -3.12 -m venv .venv 2>nul
    if errorlevel 1 py -3.11 -m venv .venv
    if errorlevel 1 (
        echo.
        echo No se pudo crear el entorno. Instala Python 3.11, 3.12 o 3.13.
        pause
        exit /b 1
    )
)

call ".venv\Scripts\activate.bat"

echo Instalando dependencias...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if errorlevel 1 goto error

echo Instalando Chromium para Playwright...
python -m playwright install chromium
if errorlevel 1 goto error

echo.
echo Ejecutando Book Data Extractor Pro...
python main.py %*
echo.
echo Proceso terminado.
pause
exit /b 0

:error
echo.
echo Ocurrio un error. Revisa los mensajes de arriba.
pause
exit /b 1
