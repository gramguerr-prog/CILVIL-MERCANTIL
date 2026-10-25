@echo off
REM ============================================================
REM  Crea un icono del CRM en el Escritorio de Windows.
REM  Solo hay que ejecutarlo UNA VEZ.
REM ============================================================
cd /d "%~dp0"

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0crear_acceso_directo.ps1"

echo.
pause
