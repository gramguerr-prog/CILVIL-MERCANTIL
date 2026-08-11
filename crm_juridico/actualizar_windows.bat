@echo off
REM ============================================================
REM  Actualizador del CRM Juridico (Windows)
REM  Descarga la ultima version y sobrescribe los archivos del
REM  programa EN ESTA MISMA CARPETA.
REM  Tu carpeta "data" (clientes, documentos, facturas) NO se toca.
REM ============================================================
setlocal
cd /d "%~dp0"

set "URL=https://github.com/gramguerr-prog/CILVIL-MERCANTIL/archive/refs/heads/claude/charming-hypatia-u2uMw.zip"
set "TMPDIR=%TEMP%\crm_actualizacion"

echo.
echo  Carpeta a actualizar: %CD%
echo.

if not exist "main.py" (
    echo  ERROR: este archivo no esta en la carpeta del programa.
    echo  Copialo dentro de la carpeta donde esta main.py y vuelve a ejecutarlo.
    pause
    exit /b 1
)

echo  [1/3] Descargando la ultima version...
if exist "%TMPDIR%" rmdir /s /q "%TMPDIR%"
mkdir "%TMPDIR%"

REM Windows 10/11 trae curl.exe, que es mas rapido. Si no esta, usa PowerShell.
where curl.exe >nul 2>&1
if %errorlevel%==0 (
    curl.exe -fsSL "%URL%" -o "%TMPDIR%\crm.zip"
) else (
    powershell -NoProfile -ExecutionPolicy Bypass -Command ^
        "$ProgressPreference='SilentlyContinue'; [Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri '%URL%' -OutFile '%TMPDIR%\crm.zip'"
)
if not exist "%TMPDIR%\crm.zip" goto error_red

echo  [2/3] Extrayendo...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "Expand-Archive -Path '%TMPDIR%\crm.zip' -DestinationPath '%TMPDIR%\extraido' -Force"

set "SRC="
for /d %%D in ("%TMPDIR%\extraido\*") do set "SRC=%%D\crm_juridico"
if not defined SRC goto error_zip
if not exist "%SRC%\main.py" goto error_zip

echo  [3/3] Actualizando archivos del programa...
robocopy "%SRC%" "%CD%" /E /XD data .venv __pycache__ /XF actualizar_windows.bat /NFL /NDL /NJH /NJS /NP >nul
if errorlevel 8 goto error_copia

rmdir /s /q "%TMPDIR%"
echo.
echo  ============================================
echo   ACTUALIZADO CORRECTAMENTE
echo   Tus datos siguen intactos en la carpeta data
echo  ============================================
echo.
echo  Ya puedes cerrar esta ventana y abrir el programa
echo  con run_windows.bat
echo.
pause
exit /b 0

:error_red
echo.
echo  ERROR: no se ha podido descargar. Revisa tu conexion a internet.
pause
exit /b 1

:error_zip
echo.
echo  ERROR: el archivo descargado no tiene el formato esperado.
pause
exit /b 1

:error_copia
echo.
echo  ERROR: no se han podido copiar los archivos.
echo  Cierra el programa si lo tienes abierto y vuelve a intentarlo.
pause
exit /b 1
