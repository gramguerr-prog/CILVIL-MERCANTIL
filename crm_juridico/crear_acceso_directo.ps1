# ============================================================
#  Crea el acceso directo del CRM en el Escritorio de Windows.
#  Lo invoca crear_acceso_directo_windows.bat
# ============================================================

$carpeta = $PSScriptRoot
$lanzador = Join-Path $carpeta 'lanzar_windows.vbs'

if (-not (Test-Path (Join-Path $carpeta 'main.py'))) {
    Write-Host ''
    Write-Host '  ERROR: esta carpeta no es la del programa (falta main.py).' -ForegroundColor Red
    exit 1
}
if (-not (Test-Path $lanzador)) {
    Write-Host ''
    Write-Host '  ERROR: falta lanzar_windows.vbs. Actualiza el programa.' -ForegroundColor Red
    exit 1
}

$shell = New-Object -ComObject WScript.Shell
$escritorio = $shell.SpecialFolders('Desktop')
if ([string]::IsNullOrEmpty($escritorio)) {
    $escritorio = Join-Path $env:USERPROFILE 'Desktop'
}

$destino = Join-Path $escritorio 'CRM Juridico.lnk'
$acceso = $shell.CreateShortcut($destino)
$acceso.TargetPath       = Join-Path $env:WINDIR 'System32\wscript.exe'
$acceso.Arguments        = '"' + $lanzador + '"'
$acceso.WorkingDirectory = $carpeta
$acceso.Description      = 'CRM Juridico - gestion del despacho'

$icono = Join-Path $carpeta 'recursos\crm.ico'
if (Test-Path $icono) {
    $acceso.IconLocation = $icono
}
$acceso.Save()

Write-Host ''
Write-Host '  ============================================' -ForegroundColor Green
Write-Host '   ACCESO DIRECTO CREADO EN EL ESCRITORIO' -ForegroundColor Green
Write-Host '  ============================================' -ForegroundColor Green
Write-Host ''
Write-Host "   $destino"
Write-Host ''
Write-Host '   Ya puedes abrir el CRM con doble clic en el icono.'
Write-Host ''
