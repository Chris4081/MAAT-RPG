$ErrorActionPreference = "Stop"

$BaseDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $BaseDir

function Get-PythonSpec {
    $candidates = @(
        @{ Cmd = "py"; Args = @("-3.12") },
        @{ Cmd = "py"; Args = @("-3.11") },
        @{ Cmd = "python3.12"; Args = @() },
        @{ Cmd = "python3.11"; Args = @() },
        @{ Cmd = "python"; Args = @() }
    )

    foreach ($candidate in $candidates) {
        if (-not (Get-Command $candidate.Cmd -ErrorAction SilentlyContinue)) {
            continue
        }
        try {
            & $candidate.Cmd @($candidate.Args + @("--version")) *> $null
            return $candidate
        } catch {
            continue
        }
    }

    return $null
}

function Invoke-SelectedPython {
    param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Args)
    & $script:PythonSpec.Cmd @($script:PythonSpec.Args + $Args)
}

$script:PythonSpec = Get-PythonSpec
if (-not $script:PythonSpec) {
    Write-Host "❌ No suitable Python interpreter found."
    Write-Host "👉 Please install Python 3.11 or 3.12."
    exit 1
}

$DetectPathsPy = @"
import os
import sys
base_dir = r'''$BaseDir'''
if base_dir not in sys.path:
    sys.path.insert(0, base_dir)
from shared.core.maat_paths import get_app_support_dir
print(get_app_support_dir())
"@

$AppSupportDir = if ($env:MAAT_APP_SUPPORT_DIR) {
    $env:MAAT_APP_SUPPORT_DIR
} else {
    (Invoke-SelectedPython "-c" $DetectPathsPy).Trim()
}

$env:MAAT_APP_SUPPORT_DIR = $AppSupportDir
$env:MAAT_DATA_DIR = Join-Path $AppSupportDir "data"
$env:MAAT_MODELS_DIR = Join-Path $AppSupportDir "models"
$env:MAAT_LOGS_DIR = Join-Path $AppSupportDir "logs"
$env:MAAT_CACHE_DIR = Join-Path $AppSupportDir "cache"
$env:MAAT_SAVES_DIR = Join-Path $AppSupportDir "saves"
$env:MAAT_STATE_DIR = Join-Path $AppSupportDir "state"

$EnvDir = Join-Path $AppSupportDir "mos-env"
$VenvPython = Join-Path $EnvDir "Scripts\python.exe"

Write-Host "🌿 MAAT-RPG is starting..."
Write-Host "📁 App support: $AppSupportDir"

if (-not (Test-Path $VenvPython)) {
    Write-Host "⚠️ No Windows installation was found yet."
    Write-Host "👉 Running setup.ps1 first..."
    & (Join-Path $BaseDir "setup.ps1")
    exit $LASTEXITCODE
}

$DiagPy = @"
import importlib.util
import platform
import sys
print(f'   Python: {sys.version.split()[0]}')
print(f'   Architecture: {platform.machine()}')
required = {
    'colorama': importlib.util.find_spec('colorama') is not None,
    'yaml': importlib.util.find_spec('yaml') is not None,
    'requests': importlib.util.find_spec('requests') is not None,
}
for name, ok in required.items():
    print(f'   {name}: {"ok" if ok else "missing"}')
    if not ok:
        raise SystemExit(1)
llama_ok = importlib.util.find_spec('llama_cpp') is not None
print(f'   llama_cpp: {"ok" if llama_ok else "missing"}')
if not llama_ok:
    print('❌ No usable llama.cpp backend found.')
    raise SystemExit(1)
"@

& $VenvPython "-c" $DiagPy
& $VenvPython (Join-Path $BaseDir "maatki.py")
