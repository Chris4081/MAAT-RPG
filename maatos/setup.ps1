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
$ReqFile = Join-Path $BaseDir "requirements.base.txt"

New-Item -ItemType Directory -Force -Path $AppSupportDir | Out-Null

Write-Host "🌿 MAAT-RPG Windows Setup"
Write-Host "-------------------------"
Write-Host "📁 App support: $AppSupportDir"
Write-Host ("🐍 Python: " + ((Invoke-SelectedPython "--version") | Out-String).Trim())

if (-not (Get-Command cmake -ErrorAction SilentlyContinue)) {
    Write-Host "⚠️ cmake was not found. llama-cpp-python may fail to build."
}
if (-not (Get-Command ffplay -ErrorAction SilentlyContinue)) {
    Write-Host "⚠️ ffplay was not found. Music will remain silent on Windows without ffmpeg."
}

$VersionCheckPy = @"
import sys
major, minor = sys.version_info[:2]
if (major, minor) < (3, 10):
    print('❌ Python 3.10 or newer is required.')
    raise SystemExit(1)
if (major, minor) not in ((3, 11), (3, 12)):
    if (major, minor) >= (3, 13):
        print('⚠️ Recommended: Python 3.11 or 3.12. Python 3.13 may fail during dependency installation (for example scipy).')
    else:
        print(f'⚠️ Recommended: Python 3.11 or 3.12. Current interpreter: {major}.{minor}')
print(f'✅ Python version ok: {major}.{minor}')
"@
Invoke-SelectedPython "-c" $VersionCheckPy

if (-not (Test-Path $EnvDir)) {
    Write-Host "📦 Creating virtual environment..."
    Invoke-SelectedPython "-m" "venv" $EnvDir
}

$VenvPython = Join-Path $EnvDir "Scripts\python.exe"
if (-not (Test-Path $VenvPython)) {
    Write-Host "❌ The virtual environment is incomplete:"
    Write-Host "   $EnvDir"
    exit 1
}

& $VenvPython -m pip install --upgrade pip setuptools wheel
& $VenvPython -m pip install -r $ReqFile

Write-Host "🧠 Optional: checking FAISS support..."
try {
    & $VenvPython -m pip install "faiss-cpu==1.13.2"
    Write-Host "✅ FAISS installed."
} catch {
    Write-Host "⚠️ FAISS could not be installed. Memory v5/v6 will use the NumPy fallback."
}

$DiagPy = @"
import importlib.util
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
    print('⚠️ llama_cpp is missing. Please make sure Visual Studio Build Tools and cmake are installed.')
"@
& $VenvPython "-c" $DiagPy

Write-Host "✅ Windows setup finished."
Write-Host "👉 Starting MAAT-RPG..."
& (Join-Path $BaseDir "start.ps1")
