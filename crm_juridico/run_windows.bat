@echo off
REM Arranque del CRM en Windows.
REM Si no existe el entorno virtual, lo crea e instala dependencias.
REM Si algo falla, la ventana NO se cierra: muestra el error.

cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Creando entorno virtual...
    py -3 -m venv .venv
    if errorlevel 1 (
        echo.
        echo ERROR: no se ha podido crear el entorno virtual.
        echo Necesitas Python 3.10 o superior instalado.
        echo Descarga: https://www.python.org/downloads/windows/
        echo Durante la instalacion marca "Add Python to PATH".
        pause
        exit /b 1
    )
    call ".venv\Scripts\activate.bat"
    python -m pip install --upgrade pip
    python -m pip install -r requirements.txt
    if errorlevel 1 (
        echo.
        echo ERROR: no se han podido instalar las dependencias.
        pause
        exit /b 1
    )
) else (
    call ".venv\Scripts\activate.bat"
)

python main.py
if errorlevel 1 (
    echo.
    echo ===================================================
    echo  La aplicacion se ha cerrado con un error.
    echo  Revisa el mensaje de arriba.
    echo ===================================================
    pause
    exit /b 1
)
