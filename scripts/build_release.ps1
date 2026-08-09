<#
.SYNOPSIS
    Builds Centurio's Windows release: `flet pack` (PyInstaller, one folder),
    then (if Inno Setup is installed) the CenturioSetup.exe installer.

.DESCRIPTION
    Runs the same version/metadata check, lint and test suite CI runs,
    fails fast if they don't pass, then produces dist\Centurio\Centurio.exe
    and — when ISCC.exe (Inno Setup 6) can be found — installer\Output\
    CenturioSetup.exe from installer\centurio.iss.

    One folder rather than one file on purpose: a one-file exe unpacks itself
    into %TEMP% on every start, which is what antivirus heuristics flag.

    Inno Setup is Windows-only, so this script only runs on Windows.

.PARAMETER SkipTests
    Skip the packaging-metadata check, ruff and pytest before building.
    CI already runs all three on every push; use this to iterate faster
    on a build-only change you already know is clean.

.PARAMETER SkipInstaller
    Stop after `flet pack` — don't look for Inno Setup or try
    to build the installer, even if ISCC.exe is on PATH.

.PARAMETER NoClean
    Keep whatever is already in build\ and installer\Output\ instead of
    clearing them first. Faster, but can leave stale files from a
    previous version mixed into the new one.

.EXAMPLE
    .\scripts\build_release.ps1
    Full release build: checks, build, installer.

.EXAMPLE
    .\scripts\build_release.ps1 -SkipTests -SkipInstaller
    Just the .exe, as fast as possible, for a local smoke test.
#>
[CmdletBinding()]
param(
    [switch]$SkipTests,
    [switch]$SkipInstaller,
    [switch]$NoClean
)

$ErrorActionPreference = 'Stop'

function Write-Step([string]$Text) {
    Write-Host ''
    Write-Host "== $Text ==" -ForegroundColor Cyan
}

function Write-Warn([string]$Text) {
    Write-Host $Text -ForegroundColor Yellow
}

function Fail([string]$Text) {
    Write-Host $Text -ForegroundColor Red
    exit 1
}

function Invoke-Checked([string]$Description, [scriptblock]$Command) {
    & $Command
    if ($LASTEXITCODE -ne 0) {
        Fail "$Description завершилось с кодом $LASTEXITCODE."
    }
}

if (-not $IsWindows -and $env:OS -ne 'Windows_NT') {
    Fail ("Сборка возможна только на Windows: установщик собирает Inno Setup, " +
          "а он работает исключительно там.")
}

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
$stopwatch = [System.Diagnostics.Stopwatch]::StartNew()

Write-Step 'Python и зависимости'
$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCmd) {
    Fail 'python не найден в PATH.'
}
Write-Host "Python: $(python --version)"

python -m pip show flet *>$null
if ($LASTEXITCODE -ne 0) {
    Write-Warn 'flet не установлен — ставлю зависимости из requirements.txt.'
    Invoke-Checked 'pip install -r requirements.txt' { python -m pip install -r requirements.txt }
}

if (-not $SkipTests) {
    python -m pip show pytest *>$null
    if ($LASTEXITCODE -ne 0) {
        Invoke-Checked 'pip install pytest ruff' { python -m pip install pytest ruff }
    }

    Write-Step 'Версия и метаданные'
    # app/__init__.py, pyproject.toml (version и build_version) и
    # installer/centurio.iss (MyAppVersion) обязаны совпадать — иначе
    # соберётся установщик с чужой версией в заголовке. test_packaging_metadata
    # уже это проверяет, так что не дублируем проверку здесь второй раз.
    Invoke-Checked 'проверка версии/метаданных' {
        python -m pytest -q -k test_packaging_metadata
    }

    Write-Step 'Линтер (ruff)'
    Invoke-Checked 'ruff' { python -m ruff check . }

    Write-Step 'Тесты'
    $previousCI = $env:CI
    $env:CI = '1'
    try {
        Invoke-Checked 'pytest' { python -m pytest -q }
    } finally {
        $env:CI = $previousCI
    }
} else {
    Write-Warn 'Пропускаю проверку версии, линтер и тесты (-SkipTests).'
}

$versionMatch = Select-String -Path (Join-Path $root 'app\__init__.py') `
    -Pattern '__version__\s*=\s*"([\d.]+)"'
if (-not $versionMatch) {
    Fail 'Не удалось прочитать версию из app\__init__.py.'
}
$version = $versionMatch.Matches[0].Groups[1].Value
Write-Host "Версия: $version"

if (-not $NoClean) {
    Write-Step 'Чистка предыдущей сборки'
    Remove-Item -Recurse -Force (Join-Path $root 'build') -ErrorAction SilentlyContinue
    Remove-Item -Recurse -Force (Join-Path $root 'dist') -ErrorAction SilentlyContinue
    Remove-Item -Recurse -Force (Join-Path $root 'installer\Output') -ErrorAction SilentlyContinue
}

Write-Step 'Сборка (flet pack)'
python -m pip show pyinstaller *>$null
if ($LASTEXITCODE -ne 0) {
    Invoke-Checked 'pip install pyinstaller' { python -m pip install pyinstaller }
}
Invoke-Checked 'flet pack' {
    flet pack main.py -y -D `
        --name Centurio `
        --icon assets/icon.png `
        --add-data "assets;assets" `
        --hidden-import pynput.keyboard._win32 pynput.mouse._win32 pystray._win32 `
        --product-name Centurio `
        --company-name Centurio `
        --product-version $version `
        --file-version "$version.0"
}

$exePath = Join-Path $root 'dist\Centurio\Centurio.exe'
if (-not (Test-Path $exePath)) {
    Fail "Ожидал файл $exePath после сборки, но его нет — сборка не удалась."
}
Write-Host "Собран: $exePath" -ForegroundColor Green

$installerExe = $null
if (-not $SkipInstaller) {
    Write-Step 'Установщик (Inno Setup)'
    $iscc = Get-Command ISCC.exe -ErrorAction SilentlyContinue
    if (-not $iscc) {
        $candidates = @(
            "$env:ProgramFiles\Inno Setup 6\ISCC.exe",
            "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe"
        )
        $found = $candidates | Where-Object { Test-Path $_ } | Select-Object -First 1
        if ($found) { $iscc = Get-Item $found }
    }
    if (-not $iscc) {
        Write-Warn ('Inno Setup (ISCC.exe) не найден — установщик не собран, только ' +
                    "$exePath.")
        Write-Warn ('Поставьте Inno Setup 6 (https://jrsoftware.org/isdl.php) или ' +
                    'запустите с -SkipInstaller, чтобы убрать это сообщение.')
    } else {
        Invoke-Checked 'ISCC.exe' { & $iscc.Source (Join-Path $root 'installer\centurio.iss') }
        $installerExe = Join-Path $root 'installer\Output\CenturioSetup.exe'
        if (-not (Test-Path $installerExe)) {
            Fail "Ожидал файл $installerExe после сборки установщика, но его нет."
        }
        Write-Host "Собран установщик: $installerExe" -ForegroundColor Green
    }
} else {
    Write-Warn 'Пропускаю сборку установщика (-SkipInstaller).'
}

$stopwatch.Stop()
Write-Step "Готово за $([int]$stopwatch.Elapsed.TotalSeconds) с"
Write-Host "Centurio v$version"
Write-Host "  exe:        $exePath"
if ($installerExe) {
    Write-Host "  установщик: $installerExe"
}
