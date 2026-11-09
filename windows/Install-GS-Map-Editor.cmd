@echo off
rem GS Map Editor for Windows. Double-click to install or update.
rem The editor runs inside WSL (Ubuntu), which is how the game's source builds
rem on Windows; it opens in your browser. Everything below is PowerShell.
powershell -NoProfile -ExecutionPolicy Bypass -Command "$s = Get-Content -LiteralPath '%~f0' -Raw; iex (($s -split '\r?\n#POWERSHELL\r?\n', 2)[1])"
echo.
pause
exit /b
#POWERSHELL
$ErrorActionPreference = 'Stop'
$Tag = '@TAG@'            # the release this installer came with
$Distro = 'Ubuntu'
$env:WSL_UTF8 = '1'       # wsl.exe answers in UTF-16 otherwise
$Raw = "https://raw.githubusercontent.com/TRosenvall/GS-Map-Editor/$Tag/windows/setup-in-wsl.sh"

function Say($text) { Write-Host ''; Write-Host $text -ForegroundColor Cyan }

Say "GS Map Editor $Tag for Windows"
Write-Host 'This installs the editor inside Ubuntu (WSL), Windows'' built-in Linux.'
Write-Host 'The first time, it can take 10 minutes and a restart.'

function Distros {
    if (-not (Get-Command wsl.exe -ErrorAction SilentlyContinue)) { return @() }
    # Error text, when WSL is off, never equals a distribution's name. Windows
    # PowerShell turns a native command's error output into a stopping error
    # under 'Stop', so this one call carries on.
    $ErrorActionPreference = 'Continue'
    return (& wsl.exe --list --quiet 2>$null) -split "`r?`n" | ForEach-Object { $_.Trim([char]0, ' ') } | Where-Object { $_ }
}

# 1-2. WSL and Ubuntu. One command installs whichever is missing; it needs
# administrator rights, may need a restart, and Ubuntu's first start asks for
# a username and password (the next step asks for that password).
if ((Distros) -notcontains $Distro) {
    Say 'Steps 1-2 of 3: installing WSL and Ubuntu (Windows asks for permission)'
    Write-Host 'If Ubuntu asks, choose a username and a password (typing the password shows nothing; that''s normal).'
    Write-Host 'When you see a prompt ending in $, type exit and press Enter.'
    Start-Process wsl.exe -ArgumentList '--install', '-d', $Distro -Verb RunAs -Wait
    if ((Distros) -notcontains $Distro) {
        Say 'Almost there. Restart Windows if it asked you to, open Ubuntu from the Start menu once to finish'
        Write-Host 'setting it up (choose a username and password), then double-click this installer again.'
        return
    }
}

# 3. The editor inside Ubuntu, then shortcuts that start it.
Say 'Step 3 of 3: installing the editor inside Ubuntu (asks for your Ubuntu password)'
& wsl.exe -d $Distro -- bash -c "curl -fsSL '$Raw' | bash -s '$Tag'"
if ($LASTEXITCODE -ne 0) {
    Say 'That didn''t finish. Check your internet connection, then run this installer again.'
    Write-Host 'If it keeps failing, please report it at https://github.com/TRosenvall/GS-Map-Editor/issues'
    return
}

$shell = New-Object -ComObject WScript.Shell
foreach ($folder in @([Environment]::GetFolderPath('Programs'), [Environment]::GetFolderPath('Desktop'))) {
    $link = $shell.CreateShortcut((Join-Path $folder 'GS Map Editor.lnk'))
    $link.TargetPath = "$env:WINDIR\System32\wsl.exe"
    $link.Arguments = "-d $Distro --exec bash -lc ""exec ~/.local/bin/gs-map-editor"""
    $link.Description = 'Make your own version of Golden Sun: The Broken Seal'
    $link.Save()
}

if (-not (Test-Path "$env:ProgramFiles\mGBA\mGBA.exe")) {
    Say 'To play your changes you also need mGBA, a free emulator: https://mgba.io/downloads.html (the Windows installer).'
}
Say 'Done. Open "GS Map Editor" from the Start menu or your desktop.'
Write-Host 'It opens in your browser, with a small window that keeps it running: close that window to stop the editor.'
Write-Host 'The first time, the editor walks you through downloading and building the game (about 15 minutes).'
