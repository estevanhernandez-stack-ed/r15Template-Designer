$WshShell = New-Object -comObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut("C:\Users\estev\Desktop\R15 Template Designer.lnk")
$Shortcut.TargetPath = "C:\Users\estev\Documents\626Labs\roblox\dist\win-unpacked\R15 Template Designer.exe"
$Shortcut.WorkingDirectory = "C:\Users\estev\Documents\626Labs\roblox\dist\win-unpacked"
$Shortcut.Save()
