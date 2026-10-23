param(
    [string]$Python = (Join-Path $PSScriptRoot '.venv-desktop\Scripts\python.exe'),
    [string]$Compiler = '',
    [switch]$SkipInstaller
)
# Compiles the app and installer. Never launches either generated executable.
$ErrorActionPreference = 'Stop'
Push-Location $PSScriptRoot
try {
    if (-not (Test-Path -LiteralPath $Python)) { throw 'Create .venv-desktop and install requirements-build.txt first.' }
    $version = & $Python -c 'from desktop_support import APP_VERSION; print(APP_VERSION)'
    if ($LASTEXITCODE -ne 0 -or $version -notmatch '^\d+\.\d+\.\d+$') { throw 'Could not read application version.' }
    $targetMachine = & $Python -c "import platform, struct; print(platform.machine().lower(), struct.calcsize('P') * 8)"
    if ($LASTEXITCODE -ne 0 -or $targetMachine -notmatch '^(amd64|x86_64) 64$') { throw 'Build this release with Windows x64 Python.' }
    & $Python -c 'import tkinter; print(tkinter.TkVersion)'
    if ($LASTEXITCODE -ne 0) { throw 'Python must include Tcl/Tk support.' }
    if (-not (Test-Path -LiteralPath assets\app.ico)) { throw 'The committed assets/app.ico icon is missing.' }
    $dependencyList = & $Python -m pip list --format=freeze --disable-pip-version-check
    if ($LASTEXITCODE -ne 0) { throw 'Could not record build dependencies.' }
    $dependencyList | Set-Content -LiteralPath installer\BUILD-DEPENDENCIES.txt -Encoding UTF8
    & $Python -m PyInstaller --noconfirm --log-level WARN AntigravityDesktop.spec
    if ($LASTEXITCODE -ne 0) { throw 'Desktop build failed.' }
    if ($SkipInstaller) {
        Write-Host 'Folder bundle ready: dist\AntigravityDesktop'
        return
    }
    if (-not $Compiler) {
        $candidates = @(
            (Join-Path $PSScriptRoot '.build-tools\inno\ISCC.exe'),
            "${env:ProgramFiles}\Inno Setup 7\ISCC.exe",
            "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
            "${env:LOCALAPPDATA}\Programs\Inno Setup 7\ISCC.exe",
            "${env:LOCALAPPDATA}\Programs\Inno Setup 6\ISCC.exe"
        )
        $Compiler = $candidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
        if (-not $Compiler) {
            $isccCommand = Get-Command ISCC.exe -ErrorAction SilentlyContinue
            if ($isccCommand) { $Compiler = $isccCommand.Source }
        }
    }
    if (-not $Compiler) { throw 'Inno Setup compiler not found. Pass -Compiler <path to ISCC.exe>.' }
    & $Compiler "/Q" "/DMyAppVersion=$version" installer\windows.iss
    if ($LASTEXITCODE -ne 0) { throw 'Installer compilation failed.' }
    $setupFile = Join-Path $PSScriptRoot "release\AntigravityDesktop-Setup-$version-windows-x64.exe"
    if (-not (Test-Path -LiteralPath $setupFile)) { throw 'The expected installer was not produced.' }
    $checksum = Get-FileHash -LiteralPath $setupFile -Algorithm SHA256
    ($checksum.Hash.ToLowerInvariant() + '  ' + [IO.Path]::GetFileName($setupFile)) | Set-Content -LiteralPath release\SHA256SUMS.txt -Encoding Ascii
    Write-Host "Installer ready: $setupFile"
    Write-Host 'Neither the app nor its installer was launched. Functional validation is a separate release step.'
} finally {
    Pop-Location
}
