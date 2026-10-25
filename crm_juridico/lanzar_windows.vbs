' ============================================================
'  Lanzador del CRM Juridico (Windows)
'  Abre el programa sin dejar una ventana negra de fondo.
'  La primera vez, si falta el entorno, muestra la instalacion.
' ============================================================
Option Explicit

Dim fso, sh, carpeta, pythonw, principal

Set fso = CreateObject("Scripting.FileSystemObject")
Set sh  = CreateObject("WScript.Shell")

carpeta = fso.GetParentFolderName(WScript.ScriptFullName)
sh.CurrentDirectory = carpeta

pythonw   = fso.BuildPath(carpeta, ".venv\Scripts\pythonw.exe")
principal = fso.BuildPath(carpeta, "main.py")

If Not fso.FileExists(principal) Then
    MsgBox "No se encuentra main.py en:" & vbCrLf & carpeta & vbCrLf & vbCrLf & _
           "Mueve este acceso directo a la carpeta del programa.", _
           vbCritical, "CRM Juridico"
    WScript.Quit 1
End If

If fso.FileExists(pythonw) Then
    ' Entorno ya preparado: arranque limpio, sin consola.
    sh.Run """" & pythonw & """ """ & principal & """", 0, False
Else
    ' Primera ejecucion: hace falta crear el entorno e instalar dependencias.
    ' Se muestra la ventana para que se vea el progreso y cualquier error.
    sh.Run """" & fso.BuildPath(carpeta, "run_windows.bat") & """", 1, False
End If
