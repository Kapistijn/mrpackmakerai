' MrPackMaker installer launcher (beta 1.5.2)
' Double-click this file to run the PowerShell installer in a visible window.
' It simply shells out to install.ps1 with an execution-policy bypass scoped to
' this single run (nothing is changed system-wide).

Option Explicit

Dim shell, fso, scriptDir, psCommand
Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

' Folder this .vbs lives in.
scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)

' Build the PowerShell command. Quotes are doubled for VBScript escaping.
psCommand = "powershell -NoProfile -ExecutionPolicy Bypass -File """ & scriptDir & "\install.ps1"""

' 1 = normal visible window, True = wait for it to finish.
shell.Run psCommand, 1, True
