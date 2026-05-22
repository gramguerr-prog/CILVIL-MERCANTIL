@echo off
REM Arranque del CRM en Windows.
REM Si no existe el entorno virtual, lo crea e instala dependencias.

cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Creando entorno virtual...
    py -3 -m venv .venv
    if errorlevel 1 (
        echo No se ha podido crear el entorno virtual. Instala Python 3.10+ desde https://www.python.org/downloads/
        pause
        exit /b 1
    )
    call ".venv\Scripts\activate.bat"
    pip install --upgrade pip
    pip install -r requirements.txt
) else (
    call ".venv\Scripts\activate.bat"
)

python main.py
