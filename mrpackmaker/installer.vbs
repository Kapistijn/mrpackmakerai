' MrPackMaker installer launcher (beta 1.6.0)
' Double-click this file to run the PowerShell installer in a visible window.
' The installer engine lives in scripts\install.ps1 to keep the root clean.
' Execution policy is bypassed for this single run only (nothing system-wide).

Option Explicit

Dim shell, fso, scriptDir, psCommand
Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

' Folder this .vbs lives in (the project root).
scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)

' Build the PowerShell command. Quotes are doubled for VBScript escaping.
psCommand = "powershell -NoProfile -ExecutionPolicy Bypass -File """ & scriptDir & "\scripts\install.ps1"""

' 1 = normal visible window, True = wait for it to finish.
shell.Run psCommand, 1, True
