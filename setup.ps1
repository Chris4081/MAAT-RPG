$BaseDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Target = Join-Path $BaseDir "maatos\setup.ps1"

if (-not (Test-Path $Target)) {
    Write-Host "❌ MAAT-RPG setup script not found:"
    Write-Host "   $Target"
    exit 1
}

& $Target @args
