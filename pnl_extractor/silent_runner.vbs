Set WShell = CreateObject("WScript.Shell")
WShell.CurrentDirectory = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)
' Run detached (0 = Hide Window, False = Don't wait for completion)
WShell.Run "run_extractor.bat", 0, False
